from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection


def _empty_payload(*, reason: str) -> dict[str, object]:
    return {"result": reason, "cart": None}


def _safe_decimal(value: object) -> Decimal:
    try:
        return Decimal(str(value or "0.00"))
    except Exception:
        return Decimal("0.00")


class CartCheckoutReadRepository(Protocol):
    def get_checkout_payload(self, *, tenant_id: int | str | None, session_key: str = "") -> dict[str, object]:
        ...


class DjangoOrmCartCheckoutRepository:
    def __init__(self) -> None:
        try:
            from app.modules.cart.models import Cart
        except Exception:
            self.cart_model = None
            return
        self.cart_model = Cart

    def is_ready(self) -> bool:
        if self.cart_model is None:
            return False
        try:
            table_names = {
                self.cart_model._meta.db_table,
                self.cart_model._meta.get_field("items").related_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def get_checkout_payload(self, *, tenant_id: int | str | None, session_key: str = "") -> dict[str, object]:
        if not tenant_id:
            return _empty_payload(reason="cart-tenant-required")
        normalized_session_key = str(session_key or "").strip()
        if not normalized_session_key:
            return _empty_payload(reason="cart-owner-required")
        if not self.is_ready():
            return _empty_payload(reason="cart-unavailable")

        cart = (
            self.cart_model._default_manager.prefetch_related("items")
            .filter(
                tenant_id=tenant_id,
                session_key=normalized_session_key,
                status=self.cart_model.Status.ACTIVE,
            )
            .order_by("-updated_at", "-id")
            .first()
        )
        if cart is None:
            return _empty_payload(reason="cart-not-found")

        items = list(cart.items.all())
        if not items:
            return _empty_payload(reason="cart-empty")

        coupon_code = str(getattr(cart, "coupon_code", "") or "").strip().upper()
        discount_total = _safe_decimal(getattr(cart, "discount_total", "0.00"))
        promotion_snapshot = {}
        if coupon_code and discount_total > 0:
            promotion_snapshot = {
                "coupon_code": coupon_code,
                "discount_total": f"{discount_total:.2f}",
                "source": "cart",
                "validation_result": "coupon-valid",
            }

        return {
            "result": "cart-checkout-ready",
            "cart": {
                "id": cart.id,
                "tenant_id": cart.tenant_id,
                "subtotal": str(cart.subtotal),
                "discount_total": str(cart.discount_total),
                "total": str(cart.total),
                "coupon_code": coupon_code if promotion_snapshot else "",
                "promotion_snapshot": promotion_snapshot,
                "items": [
                    {
                        "title": item.product_name,
                        "subtitle": item.variant_label,
                        "meta": f"SKU {item.variant_sku}" if item.variant_sku else item.product_slug,
                        "variant_sku": item.variant_sku,
                        "image_url": item.image_url,
                        "image_alt": item.image_alt,
                        "price": str(item.price_snapshot),
                        "compare_price": str(item.compare_price_snapshot) if item.compare_price_snapshot else "",
                        "quantity": item.quantity,
                        "sort_order": item.sort_order,
                    }
                    for item in items
                ],
            },
        }


@dataclass
class CartCheckoutQueryService:
    repository: CartCheckoutReadRepository

    def get_checkout_payload(self, *, tenant_id: int | str | None, session_key: str = "") -> dict[str, object]:
        return self.repository.get_checkout_payload(tenant_id=tenant_id, session_key=session_key)


cart_checkout_queries = CartCheckoutQueryService(repository=DjangoOrmCartCheckoutRepository())
