from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def _string(value: object) -> str:
    return str(value or "").strip()


def _money(value: object) -> str:
    try:
        return f"{Decimal(str(value or '0.00')):.2f}"
    except Exception:
        return "0.00"


def _order_is_paid(order) -> bool:
    status = _string(getattr(order, "status", "")).lower()
    payment_status = _string(getattr(order, "payment_status", "")).lower()
    return status == "paid" or "confirm" in payment_status or "pago" in payment_status


class DjangoOrmPaymentRefundReadinessRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
            from app.modules.payments.models import PaymentAttempt
        except Exception:
            self.order_model = None
            self.payment_attempt_model = None
            return
        self.order_model = Order
        self.payment_attempt_model = PaymentAttempt

    def list_orders(self, *, tenant_id: int | None, limit: int = 250):
        if self.order_model is None or not tenant_id:
            return []
        return list(
            self.order_model._default_manager.filter(tenant_id=tenant_id)
            .order_by("-updated_at", "-id")
            .prefetch_related("payment_attempts")[:limit]
        )


@dataclass
class PaymentRefundReadinessQueryService:
    repository: DjangoOrmPaymentRefundReadinessRepository

    def list_refund_candidates(self, *, tenant_id: int | None, limit: int = 250) -> list[dict[str, object]]:
        candidates: list[dict[str, object]] = []
        for order in self.repository.list_orders(tenant_id=tenant_id, limit=limit):
            attempts = list(getattr(order, "payment_attempts", []).all())
            paid_attempts = [attempt for attempt in attempts if _string(getattr(attempt, "status", "")).lower() == "paid"]
            latest_paid_attempt = sorted(paid_attempts, key=lambda attempt: getattr(attempt, "updated_at", None), reverse=True)[0] if paid_attempts else None
            blockers: list[str] = []

            if not _order_is_paid(order):
                blockers.append("order-not-paid")
            if _string(getattr(order, "status", "")).lower() == "canceled":
                blockers.append("order-already-canceled")
            if _string(getattr(order, "status", "")).lower() == "shipped":
                blockers.append("order-already-shipped")
            if getattr(order, "inventory_finalized_at", None):
                blockers.append("inventory-finalized")
            if latest_paid_attempt is None:
                blockers.append("paid-attempt-missing")
            elif not _string(getattr(latest_paid_attempt, "external_reference", "")):
                blockers.append("external-reference-missing")

            readiness = "ready" if not blockers else "blocked"
            candidates.append(
                {
                    "tenant_id": getattr(order, "tenant_id", tenant_id),
                    "order_number": _string(getattr(order, "number", "")),
                    "order_status": _string(getattr(order, "status", "")),
                    "payment_status": _string(getattr(order, "payment_status", "")),
                    "payment_reference": _string(getattr(order, "payment_reference", "")),
                    "amount": _money(getattr(order, "total", "0.00")),
                    "attempt_key": _string(getattr(latest_paid_attempt, "attempt_key", "")) if latest_paid_attempt else "",
                    "external_reference": _string(getattr(latest_paid_attempt, "external_reference", "")) if latest_paid_attempt else "",
                    "readiness": readiness,
                    "blockers": blockers,
                }
            )
        return candidates


payment_refund_readiness_queries = PaymentRefundReadinessQueryService(
    repository=DjangoOrmPaymentRefundReadinessRepository(),
)
