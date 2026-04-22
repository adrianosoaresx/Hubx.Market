from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.utils import timezone

from app.modules.payments.application.payment_attempt_commands import _append_timeline_event


def _string(value: object) -> str:
    return str(value or "").strip()


def _decimal_string(value: object) -> str:
    try:
        return format(Decimal(str(value or "0.00")), ".2f")
    except Exception:
        return "0.00"


logger = logging.getLogger(__name__)


class GatewayBootstrapRepository(Protocol):
    def get_pending_attempt(self, *, tenant_id: int | None, attempt_key: str):
        ...

    def save_attempt(self, attempt) -> None:
        ...


class DjangoOrmGatewayBootstrapRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.payment_attempt_model = None
            return
        self.payment_attempt_model = PaymentAttempt

    def get_pending_attempt(self, *, tenant_id: int | None, attempt_key: str):
        if self.payment_attempt_model is None or not _string(attempt_key):
            return None
        try:
            queryset = self.payment_attempt_model._default_manager.select_related("tenant", "order").filter(
                attempt_key=_string(attempt_key),
                status=self.payment_attempt_model.Status.PENDING,
            )
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.first()
        except Exception:
            return None

    def save_attempt(self, attempt) -> None:
        attempt.save()


@dataclass(frozen=True)
class GatewayBootstrapContract:
    provider_code: str
    provider_label: str
    provider_request_key: str
    payment_attempt_key: str
    order_number: str
    amount: str
    currency_code: str
    customer_name: str
    customer_email: str
    metadata: dict[str, object]


@dataclass
class GatewayBootstrapCommandService:
    repository: GatewayBootstrapRepository

    def build_contract(
        self,
        *,
        tenant_id: int | None,
        attempt_key: str,
    ) -> tuple[str, GatewayBootstrapContract | None]:
        if not tenant_id:
            logger.warning(
                "payments.gateway_bootstrap.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": _string(attempt_key),
                },
            )
            return "gateway-bootstrap-unavailable", None

        attempt = self.repository.get_pending_attempt(tenant_id=tenant_id, attempt_key=attempt_key)
        if attempt is None:
            return "gateway-bootstrap-unavailable", None

        provider_code = _string(getattr(attempt, "provider_code", "") or getattr(attempt, "payment_method_code", "") or "payment")
        provider_label = _string(getattr(attempt, "provider_label", "") or "Gateway externo")
        provider_request_key = _string(getattr(attempt, "provider_request_key", ""))
        if not provider_request_key:
            provider_request_key = f"payatt-{_string(getattr(attempt, 'attempt_key', ''))}"
            attempt.provider_request_key = provider_request_key
            attempt.bootstrapped_at = getattr(attempt, "bootstrapped_at", None) or timezone.now()
            metadata = dict(getattr(attempt, "metadata", {}) or {})
            attempt.metadata = _append_timeline_event(
                metadata=metadata,
                code="gateway_bootstrapped",
                title="Tentativa preparada para o provider",
                description="A tentativa recebeu a chave idempotente usada para abrir a cobrança externa com segurança.",
                level="info",
            )
            self.repository.save_attempt(attempt)

        order = getattr(attempt, "order", None)
        tenant = getattr(attempt, "tenant", None)
        contract = GatewayBootstrapContract(
            provider_code=provider_code,
            provider_label=provider_label,
            provider_request_key=provider_request_key,
            payment_attempt_key=_string(getattr(attempt, "attempt_key", "")),
            order_number=_string(getattr(order, "number", "")),
            amount=_decimal_string(getattr(attempt, "amount", "0.00")),
            currency_code=_string(getattr(attempt, "currency_code", "") or "BRL"),
            customer_name=_string(getattr(order, "customer_name", "")),
            customer_email=_string(getattr(order, "customer_email", "")),
            metadata={
                "tenant_slug": _string(getattr(tenant, "slug", "")),
                "tenant_subdomain": _string(getattr(tenant, "subdomain", "")),
                "order_number": _string(getattr(order, "number", "")),
                "payment_attempt_key": _string(getattr(attempt, "attempt_key", "")),
            },
        )
        return "gateway-bootstrap-ready", contract


gateway_bootstrap_commands = GatewayBootstrapCommandService(
    repository=DjangoOrmGatewayBootstrapRepository(),
)
