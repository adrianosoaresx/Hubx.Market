from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.db.models import Count, Q, Sum
from django.utils import timezone


STATUS_OPTIONS = [
    {"value": "", "label": "Todos"},
    {"value": "active", "label": "Ativo"},
    {"value": "inactive", "label": "Inativo"},
]

COUPON_STATUS_OPTIONS = [
    {"value": "active", "label": "Ativo"},
    {"value": "inactive", "label": "Inativo"},
]

DISCOUNT_TYPE_OPTIONS = [
    {"value": "percent", "label": "Percentual"},
    {"value": "fixed", "label": "Valor fixo"},
]


def _format_decimal(value: object) -> str:
    try:
        return f"{Decimal(str(value or '0.00')):.2f}"
    except Exception:
        return "0.00"


def _format_money(value: object) -> str:
    return f"R$ {_format_decimal(value).replace('.', ',')}"


def _format_datetime(value: object) -> str:
    if not value:
        return "Sem limite"
    try:
        local_value = timezone.localtime(value)
        return local_value.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(value)


class AdminCouponReadRepository(Protocol):
    def list_coupons(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        ...


class DjangoOrmAdminCouponRepository:
    def __init__(self) -> None:
        try:
            from app.modules.coupons.models import Coupon, CouponRedemption
        except Exception:
            self.coupon_model = None
            self.redemption_model = None
            return
        self.coupon_model = Coupon
        self.redemption_model = CouponRedemption

    def is_ready(self) -> bool:
        try:
            table_names = {self.coupon_model._meta.db_table}
            if self.redemption_model is not None:
                table_names.add(self.redemption_model._meta.db_table)
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def list_coupons(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        if not tenant_id or not self.is_ready():
            return []
        coupons = self.coupon_model._default_manager.filter(tenant_id=tenant_id).order_by("code")
        coupons = coupons.annotate(
            active_redemption_count=Count(
                "redemptions",
                filter=Q(redemptions__tenant_id=tenant_id, redemptions__status=self.redemption_model.Status.APPLIED),
            ),
            active_redemption_discount_total=Sum(
                "redemptions__discount_total_snapshot",
                filter=Q(redemptions__tenant_id=tenant_id, redemptions__status=self.redemption_model.Status.APPLIED),
            ),
            reversed_redemption_count=Count(
                "redemptions",
                filter=Q(redemptions__tenant_id=tenant_id, redemptions__status=self.redemption_model.Status.REVERSED),
            ),
            reversed_redemption_discount_total=Sum(
                "redemptions__discount_total_snapshot",
                filter=Q(redemptions__tenant_id=tenant_id, redemptions__status=self.redemption_model.Status.REVERSED),
            ),
        )
        return [
            {
                "id": coupon.id,
                "code": coupon.code,
                "name": coupon.name or "Cupom sem nome",
                "status": coupon.status,
                "status_label": coupon.get_status_display(),
                "discount_type": coupon.discount_type,
                "discount_type_label": coupon.get_discount_type_display(),
                "discount_value": _format_decimal(coupon.discount_value),
                "discount_label": (
                    f"{_format_decimal(coupon.discount_value)}%"
                    if coupon.discount_type == self.coupon_model.DiscountType.PERCENT
                    else f"R$ {_format_decimal(coupon.discount_value).replace('.', ',')}"
                ),
                "validity_label": f"{_format_datetime(coupon.starts_at)} → {_format_datetime(coupon.ends_at)}",
                **self._redemption_visibility(coupon),
                "updated_at": _format_datetime(coupon.updated_at),
            }
            for coupon in coupons
        ]

    @staticmethod
    def _redemption_visibility(coupon: object) -> dict[str, object]:
        active_count = int(getattr(coupon, "active_redemption_count", 0) or 0)
        reversed_count = int(getattr(coupon, "reversed_redemption_count", 0) or 0)
        active_total = _format_money(getattr(coupon, "active_redemption_discount_total", None))
        reversed_total = _format_money(getattr(coupon, "reversed_redemption_discount_total", None))
        if active_count > 0:
            label = f"{active_count} uso(s) ativos · {active_total} em descontos"
            if reversed_count > 0:
                label = f"{label} · {reversed_count} reversão(ões)"
        elif reversed_count > 0:
            label = f"Nenhum uso ativo · {reversed_count} reversão(ões)"
        else:
            label = "Nenhum uso registrado"
        return {
            "active_redemption_count": active_count,
            "active_redemption_discount_total": active_total,
            "reversed_redemption_count": reversed_count,
            "reversed_redemption_discount_total": reversed_total,
            "redemption_count": active_count,
            "redemption_discount_total": active_total,
            "redemption_label": label,
        }


@dataclass
class AdminCouponQueryService:
    repository: AdminCouponReadRepository

    def list_coupons(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        return self.repository.list_coupons(tenant_id=tenant_id)

    def get_form_initial(self) -> dict[str, object]:
        return {
            "code": "",
            "name": "",
            "status_selected": "active",
            "discount_type_selected": "percent",
            "discount_value": "",
            "starts_at": "",
            "ends_at": "",
        }


admin_coupon_queries = AdminCouponQueryService(repository=DjangoOrmAdminCouponRepository())
