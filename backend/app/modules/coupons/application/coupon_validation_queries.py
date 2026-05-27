from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from django.db import connection
from django.utils import timezone


def normalize_coupon_code(value: object) -> str:
    return str(value or "").strip().upper()[:64]


def _safe_decimal(value: object, default: str = "0.00") -> Decimal:
    try:
        return Decimal(str(value or default)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal(default)


def _unavailable_response(*, coupon_code: str, reason: str, message: str) -> dict[str, str]:
    return {
        "result": "coupon-unavailable",
        "coupon_code": coupon_code,
        "discount_total": "0.00",
        "message": message,
        "reason": reason,
    }


def _response(
    *,
    result: str,
    coupon_code: str,
    discount_total: Decimal | str = "0.00",
    message: str,
    reason: str = "",
) -> dict[str, str]:
    return {
        "result": result,
        "coupon_code": coupon_code,
        "discount_total": f"{_safe_decimal(discount_total):.2f}",
        "message": message,
        "reason": reason,
    }


class CouponValidationReadRepository(Protocol):
    def validate_cart_coupon(
        self,
        *,
        tenant_id: int | str | None,
        coupon_code: str,
        cart_snapshot: dict[str, object],
    ) -> dict[str, str]:
        ...


class DjangoOrmCouponValidationRepository:
    def __init__(self) -> None:
        try:
            from app.modules.coupons.models import Coupon
        except Exception:
            self.coupon_model = None
            return
        self.coupon_model = Coupon

    def is_ready(self) -> bool:
        try:
            table_name = self.coupon_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_name in tables

    def _base_validation(
        self,
        *,
        tenant_id: int | str | None,
        coupon_code: str,
        cart_snapshot: dict[str, object],
    ) -> tuple[str, Decimal, list[object], dict[str, str] | None]:
        normalized_code = normalize_coupon_code(coupon_code)
        if not tenant_id:
            return normalized_code, Decimal("0.00"), [], _unavailable_response(
                coupon_code=normalized_code,
                reason="tenant-required",
                message="Não foi possível validar cupom sem uma loja ativa.",
            )
        if not normalized_code:
            return normalized_code, Decimal("0.00"), [], _unavailable_response(
                coupon_code="",
                reason="coupon-code-required",
                message="Informe um código de cupom para validar.",
            )

        subtotal = _safe_decimal(cart_snapshot.get("subtotal") if isinstance(cart_snapshot, dict) else None)
        items = list(cart_snapshot.get("items") or []) if isinstance(cart_snapshot, dict) else []
        if subtotal <= 0 or not items:
            return normalized_code, subtotal, items, _unavailable_response(
                coupon_code=normalized_code,
                reason="cart-snapshot-required",
                message="O carrinho precisa de itens para validar um cupom.",
            )
        return normalized_code, subtotal, items, None

    def _discount_total(self, *, coupon, subtotal: Decimal) -> Decimal:
        discount_value = _safe_decimal(getattr(coupon, "discount_value", Decimal("0.00")))
        discount_type = str(getattr(coupon, "discount_type", "") or "")
        if discount_type == self.coupon_model.DiscountType.PERCENT:
            discount = (subtotal * discount_value / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        elif discount_type == self.coupon_model.DiscountType.FIXED:
            discount = discount_value
        else:
            return Decimal("0.00")
        return min(max(discount, Decimal("0.00")), subtotal).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def validate_cart_coupon(
        self,
        *,
        tenant_id: int | str | None,
        coupon_code: str,
        cart_snapshot: dict[str, object],
    ) -> dict[str, str]:
        normalized_code, subtotal, _items, early_response = self._base_validation(
            tenant_id=tenant_id,
            coupon_code=coupon_code,
            cart_snapshot=cart_snapshot,
        )
        if early_response is not None:
            return early_response
        if not self.is_ready():
            return _unavailable_response(
                coupon_code=normalized_code,
                reason="coupon-engine-not-configured",
                message="Validação promocional ainda não está ativa para esta loja. O cupom foi salvo como intenção, sem desconto aplicado.",
            )

        coupon = self.coupon_model._default_manager.filter(tenant_id=tenant_id, code=normalized_code).first()
        if coupon is None or str(getattr(coupon, "status", "") or "") != self.coupon_model.Status.ACTIVE:
            return _response(
                result="coupon-invalid",
                coupon_code=normalized_code,
                message="Cupom inválido para esta loja.",
                reason="coupon-invalid",
            )

        now = timezone.now()
        starts_at = getattr(coupon, "starts_at", None)
        ends_at = getattr(coupon, "ends_at", None)
        if (starts_at and starts_at > now) or (ends_at and ends_at <= now):
            return _response(
                result="coupon-expired",
                coupon_code=normalized_code,
                message="Cupom fora do período de validade.",
                reason="coupon-expired",
            )

        discount_total = self._discount_total(coupon=coupon, subtotal=subtotal)
        if discount_total <= 0:
            return _response(
                result="coupon-invalid",
                coupon_code=normalized_code,
                message="Cupom inválido para esta loja.",
                reason="coupon-invalid-discount",
            )

        return _response(
            result="coupon-valid",
            coupon_code=normalized_code,
            discount_total=discount_total,
            message="Cupom aplicado ao carrinho.",
            reason="coupon-valid",
        )


@dataclass
class CouponValidationQueryService:
    repository: CouponValidationReadRepository

    def validate_cart_coupon(
        self,
        *,
        tenant_id: int | str | None,
        coupon_code: str,
        cart_snapshot: dict[str, object],
    ) -> dict[str, str]:
        return self.repository.validate_cart_coupon(
            tenant_id=tenant_id,
            coupon_code=coupon_code,
            cart_snapshot=cart_snapshot,
        )


coupon_validation_queries = CouponValidationQueryService(repository=DjangoOrmCouponValidationRepository())
