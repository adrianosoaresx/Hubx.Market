from __future__ import annotations

from dataclasses import dataclass


def _string(value: object) -> str:
    return str(value or "").strip()


def _money(value: object) -> str:
    try:
        return f"{value:.2f}"
    except Exception:
        return "0.00"


class DjangoOrmPaymentRefundLedgerQueryRepository:
    def __init__(self) -> None:
        try:
            from app.modules.payments.models import PaymentRefund
        except Exception:
            self.payment_refund_model = None
            return
        self.payment_refund_model = PaymentRefund

    def list_refunds(self, *, tenant_id: int | None, status: str = "", limit: int = 250):
        if self.payment_refund_model is None or not tenant_id:
            return []
        queryset = (
            self.payment_refund_model._default_manager.filter(tenant_id=tenant_id)
            .select_related("order", "payment_attempt")
            .order_by("-created_at", "-id")
        )
        normalized_status = _string(status).lower()
        valid_statuses = {choice[0] for choice in self.payment_refund_model.Status.choices}
        if normalized_status in valid_statuses:
            queryset = queryset.filter(status=normalized_status)
        return list(queryset[:limit])


@dataclass
class PaymentRefundLedgerQueryService:
    repository: DjangoOrmPaymentRefundLedgerQueryRepository

    def list_refunds(self, *, tenant_id: int | None, status: str = "", limit: int = 250) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for refund in self.repository.list_refunds(tenant_id=tenant_id, status=status, limit=limit):
            order = getattr(refund, "order", None)
            attempt = getattr(refund, "payment_attempt", None)
            rows.append(
                {
                    "refund_key": _string(getattr(refund, "refund_key", "")),
                    "idempotency_key": _string(getattr(refund, "idempotency_key", "")),
                    "tenant_id": getattr(refund, "tenant_id", tenant_id),
                    "status": _string(getattr(refund, "status", "")),
                    "amount": _money(getattr(refund, "amount", "0.00")),
                    "currency_code": _string(getattr(refund, "currency_code", "")) or "BRL",
                    "order_number": _string(getattr(order, "number", "")),
                    "attempt_key": _string(getattr(attempt, "attempt_key", "")),
                    "external_reference": _string(getattr(refund, "external_reference", "")),
                    "provider_code": _string(getattr(refund, "provider_code", "")),
                    "provider_refund_reference": _string(getattr(refund, "provider_refund_reference", "")),
                    "reason_code": _string(getattr(refund, "reason_code", "")),
                    "blockers": list(getattr(refund, "blockers", []) or []),
                    "requested_at": getattr(refund, "requested_at", None),
                    "created_at": getattr(refund, "created_at", None),
                }
            )
        return rows


payment_refund_ledger_queries = PaymentRefundLedgerQueryService(
    repository=DjangoOrmPaymentRefundLedgerQueryRepository(),
)
