from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from app.modules.coupons.application.coupon_validation_queries import normalize_coupon_code


def _safe_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00")).quantize(Decimal("0.01"))
    except Exception:
        return Decimal("0.00")


class CouponRedemptionCommandRepository(Protocol):
    def record_order_coupon_redemption(self, *, tenant_id: int | str | None, order_number: str) -> dict[str, object]:
        ...

    def reverse_order_coupon_redemption(
        self,
        *,
        tenant_id: int | str | None,
        order_number: str,
        source_type: str = "admin_action",
        source_label: str = "Admin Orders",
    ) -> dict[str, object]:
        ...


class DjangoOrmCouponRedemptionCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.coupons.models import Coupon, CouponRedemption
            from app.modules.orders.models import Order
        except Exception:
            self.coupon_model = None
            self.redemption_model = None
            self.order_model = None
            return
        self.coupon_model = Coupon
        self.redemption_model = CouponRedemption
        self.order_model = Order

    def is_ready(self) -> bool:
        models = [self.coupon_model, self.redemption_model, self.order_model]
        if any(model is None for model in models):
            return False
        try:
            table_names = {model._meta.db_table for model in models}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def _get_order(self, *, tenant_id: int | str | None, order_number: str):
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_number = str(order_number or "").strip().lstrip("#")
        if not normalized_tenant_id or not normalized_order_number or self.order_model is None:
            return None
        try:
            return (
                self.order_model._default_manager.select_related("customer")
                .filter(tenant_id=normalized_tenant_id, number=normalized_order_number)
                .first()
            )
        except Exception:
            return None

    def record_order_coupon_redemption(self, *, tenant_id: int | str | None, order_number: str) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "coupon-redemption-unavailable", "redemption_id": None}

        order = self._get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return {"result": "coupon-redemption-order-not-found", "redemption_id": None}

        coupon_code = normalize_coupon_code(getattr(order, "coupon_code", ""))
        discount_total = _safe_decimal(getattr(order, "discount_total", Decimal("0.00")))
        promotion_snapshot = dict(getattr(order, "promotion_snapshot", {}) or {})
        if not coupon_code or discount_total <= 0 or not promotion_snapshot:
            return {"result": "coupon-redemption-skipped-no-coupon", "redemption_id": None}

        coupon = self.coupon_model._default_manager.filter(tenant_id=tenant_id, code=coupon_code).first()
        defaults = {
            "coupon": coupon,
            "customer_id": getattr(order, "customer_id", None),
            "discount_total_snapshot": discount_total,
            "promotion_snapshot": promotion_snapshot,
            "status": self.redemption_model.Status.APPLIED,
            "source_type": "application_command",
            "source_label": "Coupon Redemption Commands",
        }
        try:
            with transaction.atomic():
                redemption, created = self.redemption_model._default_manager.get_or_create(
                    tenant_id=tenant_id,
                    order=order,
                    coupon_code_snapshot=coupon_code,
                    defaults=defaults,
                )
        except IntegrityError:
            redemption = self.redemption_model._default_manager.filter(
                tenant_id=tenant_id,
                order=order,
                coupon_code_snapshot=coupon_code,
            ).first()
            if redemption is None:
                return {"result": "coupon-redemption-unavailable", "redemption_id": None}
            created = False

        return {
            "result": "coupon-redemption-recorded" if created else "coupon-redemption-already-recorded",
            "redemption_id": getattr(redemption, "id", None),
        }

    def reverse_order_coupon_redemption(
        self,
        *,
        tenant_id: int | str | None,
        order_number: str,
        source_type: str = "admin_action",
        source_label: str = "Admin Orders",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "coupon-redemption-reversal-unavailable", "redemption_ids": []}

        order = self._get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return {"result": "coupon-redemption-order-not-found", "redemption_ids": []}

        redemptions = list(
            self.redemption_model._default_manager.filter(
                tenant_id=tenant_id,
                order=order,
            )
        )
        if not redemptions:
            return {"result": "coupon-redemption-not-found", "redemption_ids": []}

        applied_redemptions = [
            redemption
            for redemption in redemptions
            if str(getattr(redemption, "status", "") or "") == self.redemption_model.Status.APPLIED
        ]
        if not applied_redemptions:
            return {
                "result": "coupon-redemption-already-reversed",
                "redemption_ids": [getattr(redemption, "id", None) for redemption in redemptions],
            }

        reversed_at = timezone.now()
        redemption_ids = [getattr(redemption, "id", None) for redemption in applied_redemptions]
        self.redemption_model._default_manager.filter(id__in=redemption_ids).update(
            status=self.redemption_model.Status.REVERSED,
            reversed_at=reversed_at,
            source_type=str(source_type or "admin_action").strip()[:64],
            source_label=str(source_label or "Admin Orders").strip()[:120],
        )
        return {"result": "coupon-redemption-reversed", "redemption_ids": redemption_ids}


@dataclass
class CouponRedemptionCommandService:
    repository: CouponRedemptionCommandRepository

    def record_order_coupon_redemption(self, *, tenant_id: int | str | None, order_number: str) -> dict[str, object]:
        return self.repository.record_order_coupon_redemption(tenant_id=tenant_id, order_number=order_number)

    def reverse_order_coupon_redemption(
        self,
        *,
        tenant_id: int | str | None,
        order_number: str,
        source_type: str = "admin_action",
        source_label: str = "Admin Orders",
    ) -> dict[str, object]:
        return self.repository.reverse_order_coupon_redemption(
            tenant_id=tenant_id,
            order_number=order_number,
            source_type=source_type,
            source_label=source_label,
        )


coupon_redemption_commands = CouponRedemptionCommandService(repository=DjangoOrmCouponRedemptionCommandRepository())
