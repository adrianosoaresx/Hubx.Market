from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription


def _money(value: object) -> Decimal:
    try:
        return max(Decimal(str(value or "0.00")), Decimal("0.00"))
    except Exception:
        return Decimal("0.00")


@dataclass(frozen=True)
class CommercialTerms:
    plan_id: int | None
    plan_code: str
    plan_name: str
    billing_model: str
    platform_fee_percent: Decimal
    minimum_monthly_fee: Decimal
    product_limit: int
    monthly_paid_order_limit: int
    requires_hubx_checkout: bool
    requires_billing_method: bool

    @property
    def has_product_limit(self) -> bool:
        return self.product_limit > 0

    @property
    def has_monthly_paid_order_limit(self) -> bool:
        return self.monthly_paid_order_limit > 0

    @property
    def has_platform_fee(self) -> bool:
        return self.platform_fee_percent > Decimal("0.00")


def _empty_terms() -> CommercialTerms:
    return CommercialTerms(
        plan_id=None,
        plan_code="",
        plan_name="",
        billing_model=SubscriptionPlan.BillingModel.CUSTOM,
        platform_fee_percent=Decimal("0.00"),
        minimum_monthly_fee=Decimal("0.00"),
        product_limit=0,
        monthly_paid_order_limit=0,
        requires_hubx_checkout=False,
        requires_billing_method=False,
    )


def _terms_from_plan(plan: SubscriptionPlan) -> CommercialTerms:
    return CommercialTerms(
        plan_id=plan.id,
        plan_code=str(plan.code or ""),
        plan_name=str(plan.name or ""),
        billing_model=str(plan.billing_model or ""),
        platform_fee_percent=_money(plan.platform_fee_percent),
        minimum_monthly_fee=_money(plan.minimum_monthly_fee),
        product_limit=int(plan.product_limit or 0),
        monthly_paid_order_limit=int(plan.monthly_paid_order_limit or 0),
        requires_hubx_checkout=bool(plan.requires_hubx_checkout),
        requires_billing_method=bool(plan.requires_billing_method),
    )


def get_tenant_commercial_terms(*, tenant_id: int | str | None) -> CommercialTerms:
    if not tenant_id:
        return _empty_terms()
    subscription = (
        TenantSubscription.objects.select_related("plan")
        .filter(
            tenant_id=tenant_id,
            status__in=[
                TenantSubscription.Status.TRIALING,
                TenantSubscription.Status.ACTIVE,
                TenantSubscription.Status.PAST_DUE,
                TenantSubscription.Status.SUSPENDED,
            ],
        )
        .first()
    )
    if subscription is None:
        return _empty_terms()
    return _terms_from_plan(subscription.plan)


def get_plan_commercial_terms(*, plan_code: str) -> CommercialTerms:
    plan = SubscriptionPlan.objects.filter(code=str(plan_code or "").strip().lower()).first()
    if plan is None:
        return _empty_terms()
    return _terms_from_plan(plan)
