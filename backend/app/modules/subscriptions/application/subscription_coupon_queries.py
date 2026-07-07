from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from django.db import connection
from django.utils import timezone


def normalize_subscription_coupon_code(value: object) -> str:
    return str(value or "").strip().upper()[:64]


def _money(value: object) -> Decimal:
    try:
        return max(Decimal(str(value or "0.00")), Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal("0.00")


def _response(
    *,
    result: str,
    coupon_code: str = "",
    plan_code: str = "",
    monthly_price: Decimal | str = "0.00",
    discount_type: str = "",
    discount_value: Decimal | str = "0.00",
    discount_total: Decimal | str = "0.00",
    effective_monthly_price: Decimal | str = "0.00",
    reason: str = "",
    message: str = "",
) -> dict[str, object]:
    monthly = _money(monthly_price)
    discount = _money(discount_total)
    effective = _money(effective_monthly_price if str(effective_monthly_price or "") else monthly - discount)
    payload = {
        "result": result,
        "coupon_code": coupon_code,
        "plan_code": plan_code,
        "monthly_price": f"{monthly:.2f}",
        "discount_type": discount_type,
        "discount_value": f"{_money(discount_value):.2f}",
        "discount_total": f"{discount:.2f}",
        "effective_monthly_price": f"{effective:.2f}",
        "reason": reason or result,
        "message": message,
    }
    payload["promotion_snapshot"] = (
        {
            "coupon_code": coupon_code,
            "plan_code": plan_code,
            "monthly_price": payload["monthly_price"],
            "discount_type": discount_type,
            "discount_value": payload["discount_value"],
            "discount_total": payload["discount_total"],
            "effective_monthly_price": payload["effective_monthly_price"],
            "validation_result": result,
            "source": "subscriptions",
        }
        if result == "subscription-coupon-valid"
        else {}
    )
    return payload


class SubscriptionCouponReadRepository(Protocol):
    def validate_plan_coupon(self, *, plan_code: object, coupon_code: object) -> dict[str, object]:
        ...


class DjangoOrmSubscriptionCouponRepository:
    def __init__(self) -> None:
        try:
            from app.modules.subscriptions.models import SubscriptionCoupon, SubscriptionPlan
        except Exception:
            self.coupon_model = None
            self.plan_model = None
            return
        self.coupon_model = SubscriptionCoupon
        self.plan_model = SubscriptionPlan

    def is_ready(self) -> bool:
        try:
            table_names = {self.coupon_model._meta.db_table, self.plan_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def _discount_total(self, *, coupon, monthly_price: Decimal) -> Decimal:
        value = _money(getattr(coupon, "discount_value", Decimal("0.00")))
        discount_type = str(getattr(coupon, "discount_type", "") or "")
        if discount_type == self.coupon_model.DiscountType.PERCENT:
            if value > Decimal("100.00"):
                return Decimal("0.00")
            discount = (monthly_price * value / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        elif discount_type == self.coupon_model.DiscountType.FIXED:
            discount = value
        else:
            return Decimal("0.00")
        return min(max(discount, Decimal("0.00")), monthly_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def validate_plan_coupon(self, *, plan_code: object, coupon_code: object) -> dict[str, object]:
        normalized_plan = str(plan_code or "").strip().lower()[:80]
        normalized_coupon = normalize_subscription_coupon_code(coupon_code)
        if not self.is_ready():
            return _response(
                result="subscription-coupon-unavailable",
                coupon_code=normalized_coupon,
                plan_code=normalized_plan,
                reason="subscription-coupon-engine-not-ready",
                message="Validação de cupom SaaS indisponível no momento.",
            )
        plan = self.plan_model._default_manager.filter(code=normalized_plan, status=self.plan_model.Status.ACTIVE).first()
        if plan is None:
            return _response(
                result="subscription-coupon-invalid",
                coupon_code=normalized_coupon,
                plan_code=normalized_plan,
                reason="subscription-plan-not-found",
                message="Selecione um plano ativo antes de aplicar o cupom.",
            )
        monthly_price = _money(getattr(plan, "monthly_price", Decimal("0.00")))
        if not normalized_coupon:
            return _response(
                result="subscription-coupon-invalid",
                plan_code=plan.code,
                monthly_price=monthly_price,
                effective_monthly_price=monthly_price,
                reason="subscription-coupon-code-required",
                message="Informe um código de cupom para validar.",
            )

        coupon = self.coupon_model._default_manager.filter(code=normalized_coupon).select_related("plan").first()
        if coupon is None or str(getattr(coupon, "status", "") or "") != self.coupon_model.Status.ACTIVE:
            return _response(
                result="subscription-coupon-invalid",
                coupon_code=normalized_coupon,
                plan_code=plan.code,
                monthly_price=monthly_price,
                effective_monthly_price=monthly_price,
                reason="subscription-coupon-invalid",
                message="Cupom SaaS inválido para este plano.",
            )
        if coupon.plan_id and coupon.plan_id != plan.id:
            return _response(
                result="subscription-coupon-not-applicable",
                coupon_code=normalized_coupon,
                plan_code=plan.code,
                monthly_price=monthly_price,
                effective_monthly_price=monthly_price,
                reason="subscription-coupon-plan-mismatch",
                message="Cupom SaaS não aplicável ao plano selecionado.",
            )

        now = timezone.now()
        if (coupon.starts_at and coupon.starts_at > now) or (coupon.ends_at and coupon.ends_at < now):
            return _response(
                result="subscription-coupon-expired",
                coupon_code=normalized_coupon,
                plan_code=plan.code,
                monthly_price=monthly_price,
                effective_monthly_price=monthly_price,
                reason="subscription-coupon-expired",
                message="Cupom SaaS fora da janela de validade.",
            )

        discount_total = self._discount_total(coupon=coupon, monthly_price=monthly_price)
        if discount_total <= 0:
            return _response(
                result="subscription-coupon-invalid",
                coupon_code=normalized_coupon,
                plan_code=plan.code,
                monthly_price=monthly_price,
                effective_monthly_price=monthly_price,
                reason="subscription-coupon-invalid-discount",
                message="Cupom SaaS sem desconto válido para este plano.",
            )
        effective_price = (monthly_price - discount_total).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return _response(
            result="subscription-coupon-valid",
            coupon_code=normalized_coupon,
            plan_code=plan.code,
            monthly_price=monthly_price,
            discount_type=coupon.discount_type,
            discount_value=coupon.discount_value,
            discount_total=discount_total,
            effective_monthly_price=effective_price,
            reason="subscription-coupon-valid",
            message="Cupom SaaS aplicado ao plano.",
        )


@dataclass
class SubscriptionCouponQueryService:
    repository: SubscriptionCouponReadRepository

    def validate_plan_coupon(self, *, plan_code: object, coupon_code: object) -> dict[str, object]:
        return self.repository.validate_plan_coupon(plan_code=plan_code, coupon_code=coupon_code)


subscription_coupon_queries = SubscriptionCouponQueryService(repository=DjangoOrmSubscriptionCouponRepository())
