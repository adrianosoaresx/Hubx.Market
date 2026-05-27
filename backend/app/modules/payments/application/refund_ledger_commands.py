from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone


def _string(value: object) -> str:
    return str(value or "").strip()


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


def _order_is_paid(order) -> bool:
    status = _string(getattr(order, "status", "")).lower()
    payment_status = _string(getattr(order, "payment_status", "")).lower()
    return status == "paid" or "confirm" in payment_status or "pago" in payment_status


class DjangoOrmPaymentRefundLedgerRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
            from app.modules.payments.models import PaymentAttempt, PaymentRefund
        except Exception:
            self.order_model = None
            self.payment_attempt_model = None
            self.payment_refund_model = None
            return
        self.order_model = Order
        self.payment_attempt_model = PaymentAttempt
        self.payment_refund_model = PaymentRefund

    def get_order(self, *, tenant_id: int | None, order_number: str):
        if self.order_model is None or not tenant_id:
            return None
        normalized_order_number = _string(order_number).lstrip("#")
        return (
            self.order_model._default_manager.filter(tenant_id=tenant_id, number=normalized_order_number)
            .select_related("tenant")
            .first()
        )

    def get_existing_refund(self, *, tenant_id: int | None, idempotency_key: str):
        if self.payment_refund_model is None or not tenant_id or not _string(idempotency_key):
            return None
        return (
            self.payment_refund_model._default_manager.filter(
                tenant_id=tenant_id,
                idempotency_key=_string(idempotency_key),
            )
            .select_related("order", "payment_attempt")
            .first()
        )

    def get_latest_paid_attempt(self, *, order_id: int):
        if self.payment_attempt_model is None or not order_id:
            return None
        return (
            self.payment_attempt_model._default_manager.filter(
                order_id=order_id,
                status=self.payment_attempt_model.Status.PAID,
            )
            .order_by("-paid_at", "-updated_at", "-id")
            .first()
        )

    def create_refund(
        self,
        *,
        tenant,
        order,
        payment_attempt,
        idempotency_key: str,
        status: str,
        amount: Decimal,
        currency_code: str,
        provider_code: str,
        external_reference: str,
        reason_code: str,
        blockers: list[str],
        metadata: dict[str, object],
    ):
        if self.payment_refund_model is None:
            return None
        return self.payment_refund_model._default_manager.create(
            tenant=tenant,
            order=order,
            payment_attempt=payment_attempt,
            idempotency_key=_string(idempotency_key),
            status=status,
            amount=amount,
            currency_code=_string(currency_code) or "BRL",
            provider_code=_string(provider_code),
            external_reference=_string(external_reference),
            reason_code=_string(reason_code),
            blockers=blockers,
            metadata=metadata,
            requested_at=timezone.now(),
        )


@dataclass
class PaymentRefundLedgerCommandService:
    repository: DjangoOrmPaymentRefundLedgerRepository

    def request_refund_intent(
        self,
        *,
        tenant_id: int | None,
        order_number: str,
        idempotency_key: str,
        amount: object | None = None,
        reason_code: str = "",
    ) -> tuple[str, object | None]:
        normalized_idempotency_key = _string(idempotency_key)
        if not tenant_id:
            return "refund-intent-blocked", None
        if not normalized_idempotency_key:
            return "refund-intent-blocked", None

        existing_refund = self.repository.get_existing_refund(
            tenant_id=tenant_id,
            idempotency_key=normalized_idempotency_key,
        )
        if existing_refund is not None:
            return "refund-intent-ready", existing_refund

        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "refund-intent-unavailable", None

        paid_attempt = self.repository.get_latest_paid_attempt(order_id=int(order.id))
        requested_amount = _money(amount if amount is not None else getattr(order, "total", "0.00"))
        order_total = _money(getattr(order, "total", "0.00"))
        blockers: list[str] = []

        if not _order_is_paid(order):
            blockers.append("order-not-paid")
        if _string(getattr(order, "status", "")).lower() == "canceled":
            blockers.append("order-already-canceled")
        if _string(getattr(order, "status", "")).lower() == "shipped":
            blockers.append("order-already-shipped")
        if getattr(order, "inventory_finalized_at", None):
            blockers.append("inventory-finalized")
        if paid_attempt is None:
            blockers.append("paid-attempt-missing")
        elif not _string(getattr(paid_attempt, "external_reference", "")):
            blockers.append("external-reference-missing")
        if requested_amount <= Decimal("0.00"):
            blockers.append("refund-amount-invalid")
        if order_total > Decimal("0.00") and requested_amount > order_total:
            blockers.append("refund-amount-exceeds-order-total")

        status = (
            self.repository.payment_refund_model.Status.BLOCKED
            if blockers
            else self.repository.payment_refund_model.Status.REQUESTED
        )
        metadata = {
            "order_number": _string(getattr(order, "number", "")),
            "payment_reference": _string(getattr(order, "payment_reference", "")),
            "contract_version": "refund-ledger-v1",
            "provider_call": "not-executed",
        }

        try:
            with transaction.atomic():
                refund = self.repository.create_refund(
                    tenant=getattr(order, "tenant", None),
                    order=order,
                    payment_attempt=paid_attempt,
                    idempotency_key=normalized_idempotency_key,
                    status=status,
                    amount=requested_amount,
                    currency_code=_string(getattr(paid_attempt, "currency_code", "")) if paid_attempt else "BRL",
                    provider_code=_string(getattr(paid_attempt, "provider_code", "")) if paid_attempt else "",
                    external_reference=_string(getattr(paid_attempt, "external_reference", "")) if paid_attempt else "",
                    reason_code=reason_code,
                    blockers=blockers,
                    metadata=metadata,
                )
        except IntegrityError:
            refund = self.repository.get_existing_refund(
                tenant_id=tenant_id,
                idempotency_key=normalized_idempotency_key,
            )
            if refund is not None:
                return "refund-intent-ready", refund
            raise

        if blockers:
            return "refund-intent-blocked", refund
        return "refund-intent-ready", refund


payment_refund_ledger_commands = PaymentRefundLedgerCommandService(
    repository=DjangoOrmPaymentRefundLedgerRepository(),
)
