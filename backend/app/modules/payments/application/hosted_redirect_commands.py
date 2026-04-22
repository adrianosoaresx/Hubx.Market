from __future__ import annotations

import logging
from dataclasses import dataclass

from app.modules.payments.application.payment_attempt_commands import _append_timeline_event
from app.modules.payments.application.provider_adapter_commands import provider_adapter_commands
from app.modules.payments.infrastructure.alert_signal_metrics import record_payment_alert_signal


logger = logging.getLogger(__name__)


class DjangoOrmHostedRedirectRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.payment_attempt_model = None
            return
        self.payment_attempt_model = PaymentAttempt

    def get_attempt(self, *, tenant_id: int | None, attempt_key: str):
        if self.payment_attempt_model is None or not str(attempt_key or "").strip():
            return None
        try:
            queryset = self.payment_attempt_model._default_manager.filter(attempt_key=str(attempt_key).strip())
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.first()
        except Exception:
            return None

    def save_attempt(self, attempt) -> None:
        attempt.save()


@dataclass
class HostedRedirectCommandService:
    repository: DjangoOrmHostedRedirectRepository

    def resolve_redirect_url(
        self,
        *,
        tenant_id: int | None,
        attempt_key: str,
    ) -> tuple[str, str | None]:
        if not tenant_id:
            logger.warning(
                "payments.hosted_redirect.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": str(attempt_key or ""),
                },
            )
            return "hosted-payment-unavailable", None

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=tenant_id,
            attempt_key=attempt_key,
        )
        if result != "provider-intent-ready" or response is None:
            attempt = self.repository.get_attempt(tenant_id=tenant_id, attempt_key=attempt_key)
            if attempt is not None:
                metadata = dict(getattr(attempt, "metadata", {}) or {})
                attempt.metadata = _append_timeline_event(
                    metadata=metadata,
                    code="hosted_redirect_unavailable",
                    title="Checkout hospedado indisponível",
                    description="A tentativa não conseguiu abrir o ambiente hospedado do provider nesta etapa.",
                    level="warning",
                )
                self.repository.save_attempt(attempt)
            record_payment_alert_signal(
                "hosted_redirect.unavailable",
                tenant_id=tenant_id,
                attempt_key=str(attempt_key or ""),
                reason_code=result,
            )
            logger.warning(
                "payments.hosted_redirect.unavailable",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": str(attempt_key or ""),
                    "provider_result": result,
                },
            )
            return "hosted-payment-unavailable", None
        logger.info(
            "payments.hosted_redirect.ready",
            extra={
                "tenant_id": tenant_id,
                "attempt_key": str(attempt_key or ""),
                "provider_code": response.provider_code,
                "external_reference": response.external_reference,
            },
        )
        attempt = self.repository.get_attempt(tenant_id=tenant_id, attempt_key=attempt_key)
        if attempt is not None:
            metadata = dict(getattr(attempt, "metadata", {}) or {})
            attempt.metadata = _append_timeline_event(
                metadata=metadata,
                code="hosted_redirect_opened",
                title="Checkout hospedado aberto",
                description="A pessoa foi direcionada para o ambiente hospedado do provider.",
                level="info",
            )
            self.repository.save_attempt(attempt)
        return "hosted-payment-ready", str(response.action_url or "")


hosted_redirect_commands = HostedRedirectCommandService(
    repository=DjangoOrmHostedRedirectRepository(),
)
