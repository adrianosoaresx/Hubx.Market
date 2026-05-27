from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from django.db import connection, transaction

from app.modules.coupons.application.coupon_validation_queries import (
    coupon_validation_queries,
    normalize_coupon_code,
)


def _safe_decimal(value: object, default: str = "0.00") -> Decimal:
    try:
        return Decimal(str(value or default)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return Decimal(default)


def _safe_quantity(value: object) -> int:
    try:
        return max(1, int(value or 1))
    except Exception:
        return 1


def _normalize_session_key(value: object) -> str:
    return str(value or "").strip()


def _normalize_coupon_code(value: object) -> str:
    return normalize_coupon_code(value)


def _normalize_idempotency_key(value: object) -> str:
    return str(value or "").strip()[:120]


class CartCommandRepository(Protocol):
    def get_or_create_active_cart(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
        customer_id: int | str | None = None,
    ) -> dict[str, object]:
        ...

    def add_item(
        self,
        *,
        tenant_id: int | str,
        product: dict[str, object],
        quantity: int = 1,
        session_key: str = "",
        customer_id: int | str | None = None,
        idempotency_key: str = "",
    ) -> dict[str, object]:
        ...

    def update_quantity(self, *, tenant_id: int | str, cart_id: int, item_id: int, quantity: int) -> dict[str, object]:
        ...

    def remove_item(self, *, tenant_id: int | str, cart_id: int, item_id: int) -> dict[str, object]:
        ...

    def apply_coupon_intent(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
        coupon_code: str = "",
    ) -> dict[str, object]:
        ...

    def remove_coupon_intent(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
    ) -> dict[str, object]:
        ...

    def mark_converted(
        self,
        *,
        tenant_id: int | str,
        cart_id: int,
        checkout_session_key: str,
    ) -> dict[str, object]:
        ...


class DjangoOrmCartCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.cart import models as cart_models
            from app.modules.tenants.models import Tenant
            from app.modules.customers.models import Customer
            from app.modules.catalog.models import Product, ProductVariant
        except Exception:
            self.cart_model = None
            self.item_model = None
            self.mutation_model = None
            self.tenant_model = None
            self.customer_model = None
            self.product_model = None
            self.product_variant_model = None
            return

        self.cart_model = getattr(cart_models, "Cart", None)
        self.item_model = getattr(cart_models, "CartItem", None)
        self.mutation_model = getattr(cart_models, "CartMutation", None)
        self.tenant_model = Tenant
        self.customer_model = Customer
        self.product_model = Product
        self.product_variant_model = ProductVariant

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.cart_model._meta.db_table,
                self.item_model._meta.db_table,
                self.mutation_model._meta.db_table,
                self.tenant_model._meta.db_table,
                self.product_variant_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def _serialize_cart(self, cart) -> dict[str, object]:
        try:
            items = list(cart.items.all())
        except Exception:
            items = []
        return {
            "id": cart.id,
            "tenant_id": cart.tenant_id,
            "customer_id": cart.customer_id,
            "session_key": cart.session_key,
            "status": cart.status,
            "currency": cart.currency,
            "subtotal": str(cart.subtotal),
            "discount_total": str(cart.discount_total),
            "total": str(cart.total),
            "coupon_code": cart.coupon_code,
            "items": [
                {
                    "id": item.id,
                    "product_slug": item.product_slug,
                    "product_name": item.product_name,
                    "variant_sku": item.variant_sku,
                    "variant_label": item.variant_label,
                    "price_snapshot": str(item.price_snapshot),
                    "compare_price_snapshot": str(item.compare_price_snapshot or ""),
                    "quantity": item.quantity,
                }
                for item in items
            ],
        }

    def _get_tenant(self, tenant_id: int | str):
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return None
        try:
            return self.tenant_model._default_manager.filter(pk=normalized_tenant_id).first()
        except Exception:
            return None

    def _get_customer(self, *, tenant_id: int | str, customer_id: int | str | None):
        normalized_customer_id = str(customer_id or "").strip()
        if not normalized_customer_id:
            return None
        try:
            return self.customer_model._default_manager.filter(pk=normalized_customer_id, tenant_id=tenant_id).first()
        except Exception:
            return None

    def _get_product(self, *, tenant_id: int | str, product: dict[str, object]):
        product_id = str(product.get("product_id") or product.get("id") or "").strip()
        product_slug = str(product.get("slug") or product.get("product_slug") or "").strip()
        try:
            queryset = self.product_model._default_manager.filter(tenant_id=tenant_id)
            if product_id:
                return queryset.filter(pk=product_id).first()
            if product_slug:
                return queryset.filter(slug=product_slug).first()
        except Exception:
            return None
        return None

    def _get_variant(self, *, tenant_id: int | str, variant_sku: str):
        normalized_sku = str(variant_sku or "").strip()
        if not normalized_sku:
            return None
        try:
            return (
                self.product_variant_model._default_manager.select_related("product")
                .filter(product__tenant_id=tenant_id, sku=normalized_sku)
                .first()
            )
        except Exception:
            return None

    def _stock_guard_result(
        self,
        *,
        tenant_id: int | str,
        variant_sku: str,
        requested_quantity: int,
    ) -> dict[str, object] | None:
        variant = self._get_variant(tenant_id=tenant_id, variant_sku=variant_sku)
        if variant is None:
            return {
                "result": "cart-item-stock-unavailable",
                "variant_sku": variant_sku,
                "requested_quantity": requested_quantity,
                "available_quantity": 0,
            }
        product = getattr(variant, "product", None)
        if product is None or not getattr(product, "is_active", False):
            return {
                "result": "cart-item-stock-unavailable",
                "variant_sku": variant_sku,
                "requested_quantity": requested_quantity,
                "available_quantity": 0,
            }
        product_status = str(getattr(product, "status", "") or "")
        active_status = str(getattr(getattr(self.product_model, "Status", object), "ACTIVE", "active"))
        if product_status and product_status != active_status:
            return {
                "result": "cart-item-stock-unavailable",
                "variant_sku": variant_sku,
                "requested_quantity": requested_quantity,
                "available_quantity": 0,
            }
        if not getattr(variant, "track_inventory", True) or getattr(variant, "allow_backorder", False):
            return None
        available_quantity = max(int(getattr(variant, "stock", 0) or 0) - int(getattr(variant, "reserved_stock", 0) or 0), 0)
        if requested_quantity <= available_quantity:
            return None
        result = "cart-item-stock-unavailable" if available_quantity <= 0 else "cart-item-stock-conflict"
        return {
            "result": result,
            "variant_sku": variant_sku,
            "requested_quantity": requested_quantity,
            "available_quantity": available_quantity,
        }

    def _cart_queryset(self, *, tenant_id: int | str, session_key: str, customer_id: int | str | None):
        queryset = self.cart_model._default_manager.filter(tenant_id=tenant_id, status=self.cart_model.Status.ACTIVE)
        if customer_id:
            return queryset.filter(customer_id=customer_id)
        return queryset.filter(session_key=session_key)

    def _recalculate_totals(self, cart) -> None:
        items = list(self.item_model._default_manager.filter(cart=cart))
        subtotal = sum(
            (_safe_decimal(item.price_snapshot) * _safe_quantity(item.quantity) for item in items),
            Decimal("0.00"),
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        discount_total = _safe_decimal(cart.discount_total)
        total = max(subtotal - discount_total, Decimal("0.00")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        cart.subtotal = subtotal
        cart.discount_total = discount_total
        cart.total = total

    def _cart_coupon_snapshot(self, cart) -> dict[str, object]:
        items = list(self.item_model._default_manager.filter(cart=cart).order_by("sort_order", "id"))
        return {
            "cart_id": cart.id,
            "subtotal": str(cart.subtotal),
            "items": [
                {
                    "product_id": item.product_id,
                    "product_slug": item.product_slug,
                    "variant_sku": item.variant_sku,
                    "quantity": item.quantity,
                    "price_snapshot": str(item.price_snapshot),
                }
                for item in items
            ],
        }

    def get_or_create_active_cart(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
        customer_id: int | str | None = None,
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        tenant = self._get_tenant(tenant_id)
        if tenant is None:
            return {"result": "cart-tenant-required"}
        normalized_session_key = _normalize_session_key(session_key)
        customer = self._get_customer(tenant_id=tenant.id, customer_id=customer_id)
        if customer is None and not normalized_session_key:
            return {"result": "cart-owner-required"}

        with transaction.atomic():
            cart = self._cart_queryset(
                tenant_id=tenant.id,
                session_key=normalized_session_key,
                customer_id=getattr(customer, "id", None),
            ).first()
            created = False
            if cart is None:
                cart = self.cart_model._default_manager.create(
                    tenant=tenant,
                    customer=customer,
                    session_key="" if customer else normalized_session_key,
                    status=self.cart_model.Status.ACTIVE,
                    currency="BRL",
                )
                created = True
        return {"result": "cart-created" if created else "cart-found", "cart": self._serialize_cart(cart)}

    def add_item(
        self,
        *,
        tenant_id: int | str,
        product: dict[str, object],
        quantity: int = 1,
        session_key: str = "",
        customer_id: int | str | None = None,
        idempotency_key: str = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        cart_result = self.get_or_create_active_cart(tenant_id=tenant_id, session_key=session_key, customer_id=customer_id)
        if "cart" not in cart_result:
            return cart_result
        cart_id = int(cart_result["cart"]["id"])
        product_tenant_id = str(product.get("tenant_id") or tenant_id or "").strip()
        if str(product_tenant_id) != str(tenant_id):
            return {"result": "cart-product-cross-tenant"}

        product_model = self._get_product(tenant_id=tenant_id, product=product)
        variant_sku = str(product.get("sku") or product.get("variant_sku") or "").strip()
        if not variant_sku:
            return {"result": "cart-item-variant-required"}
        normalized_idempotency_key = _normalize_idempotency_key(idempotency_key)

        with transaction.atomic():
            cart = self.cart_model._default_manager.select_for_update().filter(pk=cart_id, tenant_id=tenant_id).first()
            if cart is None:
                return {"result": "cart-not-found"}
            if normalized_idempotency_key:
                existing_mutation = (
                    self.mutation_model._default_manager.select_for_update()
                    .filter(
                        tenant_id=tenant_id,
                        cart=cart,
                        mutation_key=normalized_idempotency_key,
                        mutation_type=self.mutation_model.MutationType.ADD_ITEM,
                    )
                    .first()
                )
                if existing_mutation is not None:
                    snapshot = dict(getattr(existing_mutation, "result_snapshot", {}) or {})
                    if snapshot:
                        return {
                            **snapshot,
                            "result": "cart-item-added-idempotent",
                            "idempotency_key": normalized_idempotency_key,
                        }
            existing_item = (
                self.item_model._default_manager.select_for_update()
                .filter(cart=cart, variant_sku=variant_sku)
                .first()
            )
            item_quantity = _safe_quantity(quantity)
            existing_quantity = _safe_quantity(existing_item.quantity) if existing_item is not None else 0
            requested_quantity = existing_quantity + item_quantity
            stock_guard = self._stock_guard_result(
                tenant_id=tenant_id,
                variant_sku=variant_sku,
                requested_quantity=requested_quantity,
            )
            if stock_guard is not None:
                return {**stock_guard, "cart": self._serialize_cart(cart)}
            price = _safe_decimal(product.get("price"))
            compare_price = _safe_decimal(product.get("compare_price"), default="0.00")
            if existing_item is not None:
                existing_item.product = product_model
                existing_item.product_slug = str(product.get("slug") or product.get("product_slug") or "")
                existing_item.product_name = str(product.get("name") or product.get("product_name") or "Produto")
                existing_item.variant_label = str(product.get("effective_variant_label") or product.get("variant_label") or "")
                existing_item.image_url = str(product.get("main_image_url") or product.get("image_url") or "")
                existing_item.image_alt = str(product.get("main_image_alt") or product.get("image_alt") or product.get("name") or "")
                existing_item.price_snapshot = price
                existing_item.compare_price_snapshot = compare_price if compare_price > 0 else None
                existing_item.quantity = requested_quantity
                existing_item.save()
            else:
                next_sort = (
                    max(
                        (
                            int(value or 0)
                            for value in self.item_model._default_manager.filter(cart=cart).values_list("sort_order", flat=True)
                        ),
                        default=0,
                    )
                    + 1
                )
                self.item_model._default_manager.create(
                    cart=cart,
                    product=product_model,
                    product_slug=str(product.get("slug") or product.get("product_slug") or ""),
                    product_name=str(product.get("name") or product.get("product_name") or "Produto"),
                    variant_sku=variant_sku,
                    variant_label=str(product.get("effective_variant_label") or product.get("variant_label") or ""),
                    image_url=str(product.get("main_image_url") or product.get("image_url") or ""),
                    image_alt=str(product.get("main_image_alt") or product.get("image_alt") or product.get("name") or ""),
                    price_snapshot=price,
                    compare_price_snapshot=compare_price if compare_price > 0 else None,
                    quantity=item_quantity,
                    sort_order=next_sort,
                )
            self._recalculate_totals(cart)
            cart.save(update_fields=["subtotal", "discount_total", "total", "updated_at"])
            cart_snapshot = self._serialize_cart(cart)
            result = {"result": "cart-item-added", "cart": cart_snapshot}
            if normalized_idempotency_key:
                self.mutation_model._default_manager.create(
                    tenant_id=tenant_id,
                    cart=cart,
                    mutation_key=normalized_idempotency_key,
                    mutation_type=self.mutation_model.MutationType.ADD_ITEM,
                    result_snapshot=result,
                )
        cart.refresh_from_db()
        return result

    def update_quantity(self, *, tenant_id: int | str, cart_id: int, item_id: int, quantity: int) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        with transaction.atomic():
            cart = self.cart_model._default_manager.select_for_update().filter(
                pk=cart_id,
                tenant_id=tenant_id,
                status=self.cart_model.Status.ACTIVE,
            ).first()
            if cart is None:
                return {"result": "cart-not-found"}
            item = self.item_model._default_manager.select_for_update().filter(cart=cart, pk=item_id).first()
            if item is None:
                return {"result": "cart-item-not-found"}
            requested_quantity = _safe_quantity(quantity)
            stock_guard = self._stock_guard_result(
                tenant_id=tenant_id,
                variant_sku=item.variant_sku,
                requested_quantity=requested_quantity,
            )
            if stock_guard is not None:
                return {**stock_guard, "cart": self._serialize_cart(cart)}
            item.quantity = requested_quantity
            item.save(update_fields=["quantity", "updated_at"])
            self._recalculate_totals(cart)
            cart.save(update_fields=["subtotal", "discount_total", "total", "updated_at"])
        return {"result": "cart-item-updated", "cart": self._serialize_cart(cart)}

    def remove_item(self, *, tenant_id: int | str, cart_id: int, item_id: int) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        with transaction.atomic():
            cart = self.cart_model._default_manager.select_for_update().filter(
                pk=cart_id,
                tenant_id=tenant_id,
                status=self.cart_model.Status.ACTIVE,
            ).first()
            if cart is None:
                return {"result": "cart-not-found"}
            item = self.item_model._default_manager.select_for_update().filter(cart=cart, pk=item_id).first()
            if item is None:
                return {"result": "cart-item-not-found"}
            item.delete()
            self._recalculate_totals(cart)
        cart.save(update_fields=["subtotal", "discount_total", "total", "updated_at"])
        return {"result": "cart-item-removed", "cart": self._serialize_cart(cart)}

    def apply_coupon_intent(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
        coupon_code: str = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        normalized_code = _normalize_coupon_code(coupon_code)
        if not normalized_code:
            return {"result": "cart-coupon-code-required"}
        cart_result = self.get_or_create_active_cart(tenant_id=tenant_id, session_key=session_key)
        if "cart" not in cart_result:
            return cart_result
        cart = self.cart_model._default_manager.filter(
            pk=cart_result["cart"]["id"],
            tenant_id=tenant_id,
            status=self.cart_model.Status.ACTIVE,
        ).first()
        if cart is None:
            return {"result": "cart-not-found"}
        validation = coupon_validation_queries.validate_cart_coupon(
            tenant_id=tenant_id,
            coupon_code=normalized_code,
            cart_snapshot=self._cart_coupon_snapshot(cart),
        )
        cart.coupon_code = normalized_code
        if validation.get("result") == "coupon-valid":
            cart.discount_total = _safe_decimal(validation.get("discount_total"), default="0.00")
        else:
            cart.discount_total = Decimal("0.00")
        self._recalculate_totals(cart)
        cart.save(update_fields=["coupon_code", "discount_total", "subtotal", "total", "updated_at"])
        result = "cart-coupon-applied" if validation.get("result") == "coupon-valid" else "cart-coupon-validation-unavailable"
        return {
            "result": result,
            "cart": self._serialize_cart(cart),
            "coupon_validation": validation,
            "message": validation.get(
                "message",
                "Validação promocional ainda não está ativa para esta loja. O cupom foi salvo como intenção, sem desconto aplicado.",
            ),
        }

    def remove_coupon_intent(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        normalized_session_key = _normalize_session_key(session_key)
        if not tenant_id:
            return {"result": "cart-tenant-required"}
        if not normalized_session_key:
            return {"result": "cart-owner-required"}
        cart = self.cart_model._default_manager.filter(
            tenant_id=tenant_id,
            session_key=normalized_session_key,
            status=self.cart_model.Status.ACTIVE,
        ).first()
        if cart is None:
            return {"result": "cart-not-found"}
        cart.coupon_code = ""
        cart.discount_total = Decimal("0.00")
        self._recalculate_totals(cart)
        cart.save(update_fields=["coupon_code", "discount_total", "subtotal", "total", "updated_at"])
        return {
            "result": "cart-coupon-removed",
            "cart": self._serialize_cart(cart),
            "message": "Cupom removido do carrinho.",
        }

    def mark_converted(
        self,
        *,
        tenant_id: int | str,
        cart_id: int,
        checkout_session_key: str,
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "cart-unavailable"}
        normalized_key = str(checkout_session_key or "").strip()
        if not normalized_key:
            return {"result": "cart-checkout-session-required"}
        cart = self.cart_model._default_manager.filter(
            pk=cart_id,
            tenant_id=tenant_id,
            status=self.cart_model.Status.ACTIVE,
        ).first()
        if cart is None:
            return {"result": "cart-not-found"}
        cart.status = self.cart_model.Status.CONVERTED
        cart.converted_checkout_session_key = normalized_key
        cart.save(update_fields=["status", "converted_checkout_session_key", "updated_at"])
        return {"result": "cart-converted", "cart": self._serialize_cart(cart)}


@dataclass
class CartCommandService:
    repository: CartCommandRepository

    def get_or_create_active_cart(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
        customer_id: int | str | None = None,
    ) -> dict[str, object]:
        return self.repository.get_or_create_active_cart(
            tenant_id=tenant_id,
            session_key=session_key,
            customer_id=customer_id,
        )

    def add_item(
        self,
        *,
        tenant_id: int | str,
        product: dict[str, object],
        quantity: int = 1,
        session_key: str = "",
        customer_id: int | str | None = None,
        idempotency_key: str = "",
    ) -> dict[str, object]:
        return self.repository.add_item(
            tenant_id=tenant_id,
            product=product,
            quantity=quantity,
            session_key=session_key,
            customer_id=customer_id,
            idempotency_key=idempotency_key,
        )

    def update_quantity(self, *, tenant_id: int | str, cart_id: int, item_id: int, quantity: int) -> dict[str, object]:
        return self.repository.update_quantity(tenant_id=tenant_id, cart_id=cart_id, item_id=item_id, quantity=quantity)

    def remove_item(self, *, tenant_id: int | str, cart_id: int, item_id: int) -> dict[str, object]:
        return self.repository.remove_item(tenant_id=tenant_id, cart_id=cart_id, item_id=item_id)

    def apply_coupon_intent(
        self,
        *,
        tenant_id: int | str,
        session_key: str = "",
        coupon_code: str = "",
    ) -> dict[str, object]:
        return self.repository.apply_coupon_intent(
            tenant_id=tenant_id,
            session_key=session_key,
            coupon_code=coupon_code,
        )

    def remove_coupon_intent(self, *, tenant_id: int | str, session_key: str = "") -> dict[str, object]:
        return self.repository.remove_coupon_intent(tenant_id=tenant_id, session_key=session_key)

    def mark_converted(
        self,
        *,
        tenant_id: int | str,
        cart_id: int,
        checkout_session_key: str,
    ) -> dict[str, object]:
        return self.repository.mark_converted(
            tenant_id=tenant_id,
            cart_id=cart_id,
            checkout_session_key=checkout_session_key,
        )


cart_commands = CartCommandService(repository=DjangoOrmCartCommandRepository())
