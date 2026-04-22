from __future__ import annotations

import logging
from dataclasses import dataclass

from django.utils import timezone

from app.modules.payments.application.payment_attempt_commands import _append_timeline_event

def _string(value: object) -> str:
    return str(value or "").strip()


logger = logging.getLogger(__name__)


class DjangoOrmHostedReturnRepository:
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
            queryset = self.payment_attempt_model._default_manager.select_related("tenant", "order").filter(
                attempt_key=_string(attempt_key)
            )
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.first()
        except Exception:
            return None

    def save_attempt(self, attempt) -> None:
        attempt.save()


@dataclass
class HostedReturnCommandService:
    repository: DjangoOrmHostedReturnRepository

    def register_return(
        self,
        *,
        tenant_id: int | None,
        attempt_key: str,
        status_hint: str,
        payment_reference: str,
        provider_label: str,
    ) -> str:
        if not tenant_id:
            logger.warning(
                "payments.hosted_return.unavailable.missing_tenant",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": _string(attempt_key),
                },
            )
            return "hosted-payment-unavailable"

        attempt = self.repository.get_attempt(tenant_id=tenant_id, attempt_key=attempt_key)
        if attempt is None:
            logger.warning(
                "payments.hosted_return.unavailable",
                extra={
                    "tenant_id": tenant_id,
                    "attempt_key": _string(attempt_key),
                },
            )
            return "hosted-payment-unavailable"

        normalized_status = _string(status_hint).lower()
        normalized_reference = _string(payment_reference)
        normalized_provider = _string(provider_label)
        metadata = dict(getattr(attempt, "metadata", {}) or {})
        metadata["provider_return"] = {
            "status_hint": normalized_status or "returned",
            "provider_label": normalized_provider or _string(getattr(attempt, "provider_label", "")),
            "payment_reference": normalized_reference,
            "returned_at": timezone.now().isoformat(),
        }
        attempt.metadata = _append_timeline_event(
            metadata=metadata,
            code="hosted_return_received",
            title="Retorno hospedado recebido",
            description="O provider devolveu a navegação para o produto com um hint de status do pagamento.",
            level="info" if normalized_status not in {"failed", "failure", "error", "canceled", "cancelled"} else "warning",
        )
        if normalized_reference and not _string(getattr(attempt, "external_reference", "")):
            attempt.external_reference = normalized_reference
        self.repository.save_attempt(attempt)
        logger.info(
            "payments.hosted_return.recorded",
            extra={
                "tenant_id": getattr(attempt, "tenant_id", tenant_id),
                "order_number": str(getattr(getattr(attempt, "order", None), "number", "") or ""),
                "attempt_key": str(getattr(attempt, "attempt_key", "") or attempt_key),
                "status_hint": normalized_status or "returned",
            },
        )

        if normalized_status in {"paid", "succeeded", "success", "authorized"}:
            return "hosted-payment-return-pending-verification"
        if normalized_status in {"failed", "failure", "error", "canceled", "cancelled"}:
            return "hosted-payment-return-failed"
        return "hosted-payment-returned"


hosted_return_commands = HostedReturnCommandService(
    repository=DjangoOrmHostedReturnRepository(),
)
