from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.payments.models import PlatformFeeLedger
from app.modules.subscriptions.application.commercial_terms import CommercialTerms, get_tenant_commercial_terms
from app.modules.subscriptions.models import SubscriptionPlan


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _money(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _fee_amount(*, basis_amount: object, percent: object) -> Decimal:
    basis = _money(basis_amount)
    try:
        rate = Decimal(str(percent or "0.00"))
    except Exception:
        rate = Decimal("0.00")
    return (basis * rate / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _month_bounds(reference_at=None) -> tuple[object, object]:
    now = reference_at or timezone.now()
    period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    return period_start, period_end


def _attempt_has_split_requested(attempt) -> bool:
    metadata = dict(getattr(attempt, "metadata", {}) or {})
    provider_intent = dict(metadata.get("provider_intent") or {})
    payload_snapshot = dict(provider_intent.get("payload_snapshot") or {})
    request = dict(payload_snapshot.get("request") or {})
    payment_payload = dict(request.get("payment") or {})
    return bool(payment_payload.get("splits"))


class DjangoOrmPlatformFeeLedgerRepository:
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

    def get_order(self, *, tenant_id: int | None, order_number: str):
        if self.order_model is None or not tenant_id:
            return None
        return (
            self.order_model._default_manager.filter(
                tenant_id=tenant_id,
                number=str(order_number or "").strip().lstrip("#"),
            )
            .select_related("tenant")
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

    def paid_order_fee_sum(self, *, tenant_id: int, period_start, period_end) -> Decimal:
        rows = PlatformFeeLedger.objects.filter(
            tenant_id=tenant_id,
            kind=PlatformFeeLedger.Kind.ORDER_TAKE_RATE,
        ).filter(
            Q(
                billing_period_start__gte=period_start,
                billing_period_start__lt=period_end,
            )
            | Q(
                billing_period_start__isnull=True,
                created_at__gte=period_start,
                created_at__lt=period_end,
            )
        ).exclude(status=PlatformFeeLedger.Status.CANCELED)
        return _money(sum((entry.fee_amount for entry in rows), Decimal("0.00")))

    def paid_order_count(self, *, tenant_id: int, period_start, period_end) -> int:
        if self.order_model is None:
            return 0
        return self.order_model._default_manager.filter(
            tenant_id=tenant_id,
            status="paid",
            payment_confirmed_at__gte=period_start,
            payment_confirmed_at__lt=period_end,
        ).count()


@dataclass
class PlatformFeeLedgerCommandService:
    repository: DjangoOrmPlatformFeeLedgerRepository

    def record_paid_order_fee(
        self,
        *,
        tenant_id: int | None,
        order_number: str,
        payment_attempt=None,
        actor_label: str = "payments-webhook",
    ) -> tuple[str, PlatformFeeLedger | None]:
        if not tenant_id:
            return "platform-fee-unavailable", None
        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "platform-fee-unavailable", None
        terms = get_tenant_commercial_terms(tenant_id=tenant_id)
        if not terms.has_platform_fee:
            return "platform-fee-not-applicable", None
        attempt = payment_attempt or self.repository.get_latest_paid_attempt(order_id=int(order.id))
        basis_amount = _money(getattr(order, "total", "0.00"))
        fee_amount = _fee_amount(basis_amount=basis_amount, percent=terms.platform_fee_percent)
        if fee_amount <= Decimal("0.00"):
            return "platform-fee-not-applicable", None
        period_start, period_end = _month_bounds(getattr(order, "payment_confirmed_at", None))
        split_requested = _attempt_has_split_requested(attempt)
        status = PlatformFeeLedger.Status.SPLIT_REQUESTED if split_requested else PlatformFeeLedger.Status.PENDING_COLLECTION
        provider_code = _string(getattr(attempt, "provider_code", ""), limit=64)
        provider_reference = _string(getattr(attempt, "external_reference", ""), limit=120)
        ledger_key = f"order:{int(order.id)}:platform-fee"
        overage_metadata: dict[str, object] = {}
        if terms.has_monthly_paid_order_limit:
            paid_count = self.repository.paid_order_count(
                tenant_id=int(tenant_id),
                period_start=period_start,
                period_end=period_end,
            )
            if paid_count > terms.monthly_paid_order_limit:
                overage_metadata = {
                    "commercial_overage": True,
                    "monthly_paid_order_limit": terms.monthly_paid_order_limit,
                    "monthly_paid_order_count": paid_count,
                    "overage_count": paid_count - terms.monthly_paid_order_limit,
                }

        with transaction.atomic():
            ledger, created = PlatformFeeLedger.objects.get_or_create(
                ledger_key=ledger_key,
                defaults={
                    "tenant_id": tenant_id,
                    "order": order,
                    "payment_attempt": attempt,
                    "kind": PlatformFeeLedger.Kind.ORDER_TAKE_RATE,
                    "status": status,
                    **self._snapshot_fields(terms),
                    "billing_period_start": period_start,
                    "billing_period_end": period_end,
                    "basis_amount": basis_amount,
                    "fee_amount": fee_amount,
                    "currency_code": _string(getattr(order, "currency_code", ""), limit=8) or "BRL",
                    "provider_code": provider_code,
                    "provider_payment_reference": provider_reference,
                    "metadata": {
                        "order_number": str(getattr(order, "number", "") or ""),
                        "split_requested": split_requested,
                        "collection_mode": "asaas_split" if split_requested else "ledger_pending_collection",
                        **overage_metadata,
                    },
                },
            )
            if created:
                self._record_audit(
                    ledger=ledger,
                    action="platform_fee.order_recorded",
                    actor_label=actor_label,
                    summary=f"Taxa Hubx registrada para pedido {getattr(order, 'number', '')}.",
                )
                if overage_metadata:
                    self._record_audit(
                        ledger=ledger,
                        action="platform_fee.order_limit_overage_recorded",
                        actor_label=actor_label,
                        summary="Pedido pago acima do limite mensal registrado para tratativa comercial.",
                    )
        return ("platform-fee-created" if created else "platform-fee-existing"), ledger

    def mark_refund_adjustment_required(
        self,
        *,
        tenant_id: int | None,
        order_id: int | None,
        refund_key: str,
        actor_label: str = "payments-refund",
    ) -> tuple[str, PlatformFeeLedger | None]:
        if not tenant_id or not order_id:
            return "platform-fee-adjustment-unavailable", None
        ledger = PlatformFeeLedger.objects.filter(
            tenant_id=tenant_id,
            order_id=order_id,
            kind=PlatformFeeLedger.Kind.ORDER_TAKE_RATE,
        ).first()
        if ledger is None:
            return "platform-fee-adjustment-unavailable", None
        if ledger.status != PlatformFeeLedger.Status.ADJUSTMENT_REQUIRED:
            metadata = dict(ledger.metadata or {})
            refunds = list(metadata.get("refund_adjustments") or [])
            refunds.append({"refund_key": _string(refund_key), "marked_at": timezone.now().isoformat()})
            metadata["refund_adjustments"] = refunds[-12:]
            ledger.status = PlatformFeeLedger.Status.ADJUSTMENT_REQUIRED
            ledger.metadata = metadata
            ledger.save(update_fields=["status", "metadata", "updated_at"])
            self._record_audit(
                ledger=ledger,
                action="platform_fee.adjustment_required",
                actor_label=actor_label,
                summary="Taxa Hubx marcada para ajuste após refund ou chargeback.",
            )
        return "platform-fee-adjustment-required", ledger

    def mark_order_adjustment_required(
        self,
        *,
        tenant_id: int | None,
        order_number: str,
        reason_code: str,
        actor_label: str = "payments-webhook",
    ) -> tuple[str, PlatformFeeLedger | None]:
        if not tenant_id:
            return "platform-fee-adjustment-unavailable", None
        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "platform-fee-adjustment-unavailable", None
        ledger = PlatformFeeLedger.objects.filter(
            tenant_id=tenant_id,
            order=order,
            kind=PlatformFeeLedger.Kind.ORDER_TAKE_RATE,
        ).first()
        if ledger is None:
            return "platform-fee-adjustment-unavailable", None
        metadata = dict(ledger.metadata or {})
        adjustments = list(metadata.get("payment_adjustments") or [])
        adjustments.append({"reason_code": _string(reason_code), "marked_at": timezone.now().isoformat()})
        metadata["payment_adjustments"] = adjustments[-12:]
        ledger.status = PlatformFeeLedger.Status.ADJUSTMENT_REQUIRED
        ledger.metadata = metadata
        ledger.save(update_fields=["status", "metadata", "updated_at"])
        self._record_audit(
            ledger=ledger,
            action="platform_fee.adjustment_required",
            actor_label=actor_label,
            summary="Taxa Hubx marcada para ajuste após falha externa em pedido já pago.",
        )
        return "platform-fee-adjustment-required", ledger

    def close_minimum_commitment_period(
        self,
        *,
        tenant_id: int | None,
        reference_at=None,
        actor_label: str = "platform-fee-monthly-close",
    ) -> tuple[str, PlatformFeeLedger | None]:
        if not tenant_id:
            return "platform-fee-minimum-unavailable", None
        terms = get_tenant_commercial_terms(tenant_id=tenant_id)
        if terms.billing_model != SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT:
            return "platform-fee-minimum-not-applicable", None
        period_start, period_end = _month_bounds(reference_at)
        collected_amount = self.repository.paid_order_fee_sum(
            tenant_id=int(tenant_id),
            period_start=period_start,
            period_end=period_end,
        )
        minimum_fee = _money(terms.minimum_monthly_fee)
        difference = max(minimum_fee - collected_amount, Decimal("0.00"))
        ledger_key = f"minimum:{tenant_id}:{period_start.date().isoformat()}"
        existing = PlatformFeeLedger.objects.filter(ledger_key=ledger_key).first()
        if existing is not None:
            return "platform-fee-minimum-existing", existing
        if difference <= Decimal("0.00"):
            return "platform-fee-minimum-satisfied", None
        ledger = PlatformFeeLedger.objects.create(
            tenant_id=tenant_id,
            ledger_key=ledger_key,
            kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT,
            status=PlatformFeeLedger.Status.PENDING_COLLECTION,
            **self._snapshot_fields(terms),
            billing_period_start=period_start,
            billing_period_end=period_end,
            basis_amount=collected_amount,
            fee_amount=difference,
            currency_code="BRL",
            provider_code="asaas",
            metadata={
                "minimum_monthly_fee": f"{minimum_fee:.2f}",
                "period_order_fee_total": f"{collected_amount:.2f}",
                "collection_mode": "asaas_complementary_charge_pending",
                "provider_call": "not-executed",
            },
        )
        self._record_audit(
            ledger=ledger,
            action="platform_fee.minimum_adjustment_created",
            actor_label=actor_label,
            summary="Complemento mensal Pro criado para cobrança complementar.",
        )
        return "platform-fee-minimum-created", ledger

    @staticmethod
    def _snapshot_fields(terms: CommercialTerms) -> dict[str, object]:
        return {
            "plan_code_snapshot": terms.plan_code,
            "billing_model_snapshot": terms.billing_model,
            "platform_fee_percent_snapshot": terms.platform_fee_percent,
            "minimum_monthly_fee_snapshot": terms.minimum_monthly_fee,
        }

    @staticmethod
    def _record_audit(*, ledger: PlatformFeeLedger, action: str, actor_label: str, summary: str) -> None:
        audit_log_commands.record_event(
            tenant_id=ledger.tenant_id,
            module="payments",
            action=action,
            entity_type="PlatformFeeLedger",
            entity_id=str(ledger.id),
            actor_label=_string(actor_label),
            summary=summary,
            metadata={
                "ledger_key": ledger.ledger_key,
                "kind": ledger.kind,
                "status": ledger.status,
                "plan_code": ledger.plan_code_snapshot,
                "basis_amount": str(ledger.basis_amount),
                "fee_amount": str(ledger.fee_amount),
            },
        )


platform_fee_ledger_commands = PlatformFeeLedgerCommandService(
    repository=DjangoOrmPlatformFeeLedgerRepository(),
)
