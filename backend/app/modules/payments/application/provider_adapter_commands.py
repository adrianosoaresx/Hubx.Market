from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from app.modules.payments.application.gateway_bootstrap_commands import gateway_bootstrap_commands
from app.modules.payments.application.payment_attempt_commands import _append_timeline_event
from app.modules.payments.domain.provider_rollout import decide_provider_rollout
from app.modules.payments.infrastructure.alert_signal_metrics import record_payment_alert_signal
from app.modules.payments.infrastructure.provider_adapters import (
    ProviderAdapterError,
    ProviderIntentResponse,
    get_provider_adapter,
)


def _string(value: object) -> str:
    return str(value or "").strip()


logger = logging.getLogger(__name__)


class ProviderAdapterRepository(Protocol):
    def get_attempt(self, *, tenant_id: int | None, attempt_key: str):
        ...

    def save_attempt(self, attempt) -> None:
        ...


class DjangoOrmProviderAdapterRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.payment_attempt_model = None
            return
        self.payment_attempt_model = PaymentAttempt

    def get_attempt(self, *, tenant_id: int | None, attempt_key: str):
        if self.payment_attempt_model is None or not _string(attempt_key):
            return None
        try:
            queryset = (
                self.payment_attempt_model._default_manager.select_related("tenant", "order")
                .prefetch_related("order__items")
                .filter(attempt_key=_string(attempt_key))
            )
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.first()
        except Exception:
            return None

    def save_attempt(self, attempt) -> None:
        attempt.save()


@dataclass
class ProviderAdapterCommandService:
    repository: ProviderAdapterRepository

    def create_external_intent(
        self,
        *,
        tenant_id: int | None,
        attempt_key: str,
    ) -> tuple[str, ProviderIntentResponse | None]:
        if not tenant_id:
            logger.warning(
                "payments.provider_intent.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": _string(attempt_key),
                },
            )
            return "provider-intent-unavailable", None

        bootstrap_result, contract = gateway_bootstrap_commands.build_contract(
            tenant_id=tenant_id,
            attempt_key=attempt_key,
        )
        if bootstrap_result != "gateway-bootstrap-ready" or contract is None:
            logger.warning(
                "payments.provider_intent.unavailable.bootstrap",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": _string(attempt_key),
                    "bootstrap_result": bootstrap_result,
                },
            )
            return "provider-intent-unavailable", None

        attempt = self.repository.get_attempt(tenant_id=tenant_id, attempt_key=attempt_key)
        if attempt is None or str(getattr(attempt, "status", "") or "") != "pending":
            logger.warning(
                "payments.provider_intent.unavailable.attempt",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": _string(attempt_key),
                    "attempt_found": attempt is not None,
                    "attempt_status": str(getattr(attempt, "status", "") or ""),
                },
            )
            return "provider-intent-unavailable", None

        existing_intent = dict(dict(getattr(attempt, "metadata", {}) or {}).get("provider_intent") or {})
        existing_action_url = _string(existing_intent.get("action_url"))
        existing_external_reference = _string(getattr(attempt, "external_reference", "") or existing_intent.get("external_reference"))
        if existing_action_url and existing_external_reference:
            logger.info(
                "payments.provider_intent.reused",
                extra={
                    "tenant_id": getattr(attempt, "tenant_id", tenant_id),
                    "order_number": str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                    "attempt_key": str(getattr(attempt, "attempt_key", "") or attempt_key),
                    "provider_code": _string(existing_intent.get("provider_code") or contract.provider_code),
                },
            )
            return "provider-intent-ready", ProviderIntentResponse(
                provider_code=_string(existing_intent.get("provider_code") or contract.provider_code),
                provider_label=_string(existing_intent.get("provider_label") or contract.provider_label),
                external_reference=existing_external_reference,
                action_url=existing_action_url,
                payload_snapshot=dict(existing_intent.get("payload_snapshot") or {}),
            )

        rollout = decide_provider_rollout(provider_code=contract.provider_code, tenant=getattr(attempt, "tenant", None))
        if not rollout.allow_real_provider and rollout.fallback_mode == "block":
            metadata = dict(getattr(attempt, "metadata", {}) or {})
            metadata["provider_rollout"] = {
                "rollout_mode": rollout.rollout_mode,
                "fallback_mode": rollout.fallback_mode,
                "reason_code": rollout.reason_code,
                "real_provider_active": False,
            }
            attempt.metadata = _append_timeline_event(
                metadata=metadata,
                code="provider_rollout_blocked",
                title="Provider real indisponível para este rollout",
                description="A tentativa ficou fora do rollout controlado e não abriu checkout externo nesta etapa.",
                level="warning",
            )
            self.repository.save_attempt(attempt)
            record_payment_alert_signal(
                "provider_rollout.blocked",
                tenant_id=getattr(attempt, "tenant_id", tenant_id),
                order_number=str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                attempt_key=str(getattr(attempt, "attempt_key", "") or attempt_key),
                provider_code=contract.provider_code,
                reason_code=rollout.reason_code,
                metadata={
                    "rollout_mode": rollout.rollout_mode,
                    "fallback_mode": rollout.fallback_mode,
                },
            )
            logger.warning(
                "payments.provider_intent.blocked.rollout",
                extra={
                    "tenant_id": getattr(attempt, "tenant_id", tenant_id),
                    "order_number": str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                    "attempt_key": str(getattr(attempt, "attempt_key", "") or attempt_key),
                    "provider_code": contract.provider_code,
                    "rollout_mode": rollout.rollout_mode,
                    "reason_code": rollout.reason_code,
                },
            )
            return "provider-intent-unavailable", None

        adapter = get_provider_adapter(provider_code=contract.provider_code, tenant=getattr(attempt, "tenant", None))
        try:
            response = adapter.create_intent(contract=contract, attempt=attempt)
        except ProviderAdapterError as exc:
            metadata = dict(getattr(attempt, "metadata", {}) or {})
            metadata["provider_intent_failure"] = {
                "provider_code": contract.provider_code,
                "reason_code": str(exc),
            }
            attempt.metadata = _append_timeline_event(
                metadata=metadata,
                code="provider_intent_failed",
                title="Falha ao criar checkout externo",
                description="O provider não conseguiu abrir a intenção externa de pagamento nesta tentativa.",
                level="error",
            )
            self.repository.save_attempt(attempt)
            record_payment_alert_signal(
                "provider_intent.failed",
                tenant_id=getattr(attempt, "tenant_id", tenant_id),
                order_number=str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                attempt_key=str(getattr(attempt, "attempt_key", "") or attempt_key),
                provider_code=contract.provider_code,
                reason_code=str(exc),
            )
            logger.exception(
                "payments.provider_intent.failed",
                extra={
                    "tenant_id": getattr(attempt, "tenant_id", tenant_id),
                    "order_number": str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                    "attempt_key": str(getattr(attempt, "attempt_key", "") or attempt_key),
                    "provider_code": contract.provider_code,
                    "error_code": str(exc),
                },
            )
            return "provider-intent-unavailable", None

        metadata = dict(getattr(attempt, "metadata", {}) or {})
        metadata["provider_rollout"] = {
            "rollout_mode": rollout.rollout_mode,
            "fallback_mode": rollout.fallback_mode,
            "reason_code": rollout.reason_code,
            "real_provider_active": rollout.allow_real_provider,
        }
        metadata["provider_intent"] = {
            "provider_code": response.provider_code,
            "provider_label": response.provider_label,
            "provider_request_key": contract.provider_request_key,
            "external_reference": response.external_reference,
            "action_url": response.action_url,
            "payload_snapshot": dict(response.payload_snapshot),
        }
        attempt.metadata = _append_timeline_event(
            metadata=metadata,
            code="provider_intent_created" if rollout.allow_real_provider else "provider_intent_fallback",
            title="Link de pagamento criado" if rollout.allow_real_provider else "Fallback lite de pagamento aplicado",
            description=(
                "O provider devolveu uma URL hospedada para continuar o pagamento."
                if rollout.allow_real_provider
                else "A tentativa ficou fora do rollout real e seguiu com o adapter lite como fallback operacional."
            ),
            level="info" if rollout.allow_real_provider else "warning",
        )
        if not _string(getattr(attempt, "external_reference", "")):
            attempt.external_reference = response.external_reference
        self.repository.save_attempt(attempt)
        logger.info(
            "payments.provider_intent.created",
            extra={
                "tenant_id": getattr(attempt, "tenant_id", tenant_id),
                "order_number": str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                "attempt_key": str(getattr(attempt, "attempt_key", "") or attempt_key),
                "provider_code": response.provider_code,
                "external_reference": response.external_reference,
            },
        )
        return "provider-intent-ready", response


provider_adapter_commands = ProviderAdapterCommandService(
    repository=DjangoOrmProviderAdapterRepository(),
)
