from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection

from app.modules.subscriptions.models import SubscriptionCoupon, SubscriptionPlan


STATUS_OPTIONS = (
    {"value": "", "label": "Todos os status"},
    {"value": SubscriptionCoupon.Status.ACTIVE, "label": "Ativos"},
    {"value": SubscriptionCoupon.Status.INACTIVE, "label": "Inativos"},
)

COUPON_STATUS_OPTIONS = (
    {"value": SubscriptionCoupon.Status.ACTIVE, "label": "Ativo"},
    {"value": SubscriptionCoupon.Status.INACTIVE, "label": "Inativo"},
)

DISCOUNT_TYPE_OPTIONS = (
    {"value": SubscriptionCoupon.DiscountType.PERCENT, "label": "Percentual"},
    {"value": SubscriptionCoupon.DiscountType.FIXED, "label": "Valor fixo"},
)


def _format_decimal(value: object) -> str:
    try:
        return f"{Decimal(str(value or '0.00')):.2f}".replace(".", ",")
    except Exception:
        return "0,00"


def _format_money(value: object) -> str:
    return f"R$ {_format_decimal(value)}"


def _validity_label(coupon: SubscriptionCoupon) -> str:
    starts_at = coupon.starts_at.strftime("%d/%m/%Y %H:%M") if coupon.starts_at else ""
    ends_at = coupon.ends_at.strftime("%d/%m/%Y %H:%M") if coupon.ends_at else ""
    if starts_at and ends_at:
        return f"{starts_at} até {ends_at}"
    if starts_at:
        return f"A partir de {starts_at}"
    if ends_at:
        return f"Até {ends_at}"
    return "Sem janela"


class SubscriptionCouponReadRepository(Protocol):
    def list_coupons(self) -> list[dict[str, object]]:
        ...

    def list_plan_options(self) -> list[dict[str, str]]:
        ...


class DjangoOrmSubscriptionCouponAdminRepository:
    def is_ready(self) -> bool:
        try:
            table_names = {SubscriptionCoupon._meta.db_table, SubscriptionPlan._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def list_coupons(self) -> list[dict[str, object]]:
        if not self.is_ready():
            return []
        return [self._serialize(coupon) for coupon in SubscriptionCoupon.objects.select_related("plan").order_by("code")]

    def list_plan_options(self) -> list[dict[str, str]]:
        if not self.is_ready():
            return [{"value": "", "label": "Todos os planos"}]
        options = [{"value": "", "label": "Todos os planos"}]
        options.extend(
            {
                "value": plan.code,
                "label": f"{plan.name} ({plan.code})",
            }
            for plan in SubscriptionPlan.objects.order_by("monthly_price", "code")
        )
        return options

    def _serialize(self, coupon: SubscriptionCoupon) -> dict[str, object]:
        discount_label = (
            f"{_format_decimal(coupon.discount_value)}%"
            if coupon.discount_type == SubscriptionCoupon.DiscountType.PERCENT
            else _format_money(coupon.discount_value)
        )
        return {
            "id": coupon.id,
            "code": coupon.code,
            "name": coupon.name or "Cupom SaaS sem nome",
            "status": coupon.status,
            "status_label": coupon.get_status_display(),
            "discount_type": coupon.discount_type,
            "discount_type_label": coupon.get_discount_type_display(),
            "discount_value": _format_decimal(coupon.discount_value),
            "discount_label": discount_label,
            "plan_code": coupon.plan.code if coupon.plan_id else "",
            "plan_label": f"{coupon.plan.name} ({coupon.plan.code})" if coupon.plan_id else "Todos os planos",
            "validity_label": _validity_label(coupon),
            "created_at": coupon.created_at.strftime("%d/%m/%Y %H:%M"),
            "updated_at": coupon.updated_at.strftime("%d/%m/%Y %H:%M"),
        }


@dataclass
class SubscriptionCouponAdminQueryService:
    repository: SubscriptionCouponReadRepository

    def list_coupons(self) -> list[dict[str, object]]:
        return self.repository.list_coupons()

    def list_plan_options(self) -> list[dict[str, str]]:
        return self.repository.list_plan_options()

    def get_form_initial(self) -> dict[str, object]:
        return {
            "code": "",
            "name": "",
            "status_selected": SubscriptionCoupon.Status.ACTIVE,
            "discount_type_selected": SubscriptionCoupon.DiscountType.PERCENT,
            "discount_value": "",
            "plan_code_selected": "",
            "starts_at": "",
            "ends_at": "",
        }


subscription_coupon_admin_queries = SubscriptionCouponAdminQueryService(repository=DjangoOrmSubscriptionCouponAdminRepository())
