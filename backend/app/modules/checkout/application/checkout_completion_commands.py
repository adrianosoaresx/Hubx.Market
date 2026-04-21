from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from django.db import connection, transaction

from app.modules.checkout.application.checkout_activation_commands import _safe_decimal


def _combine_customer_name(first_name: str, last_name: str) -> str:
    return " ".join(part for part in [str(first_name or "").strip(), str(last_name or "").strip()] if part).strip()


def _combine_shipping_address(*, address_line_1: str, address_line_2: str, city: str, state: str, zip_code: str) -> str:
    parts = [str(address_line_1 or "").strip()]
    if str(address_line_2 or "").strip():
        parts.append(str(address_line_2 or "").strip())
    location = " · ".join(part for part in [str(city or "").strip(), str(state or "").strip()] if part)
    if location:
        parts.append(location)
    if str(zip_code or "").strip():
        parts.append(f"CEP {str(zip_code).strip()}")
    return " · ".join(part for part in parts if part)


def _extract_variant_sku(item) -> str:
    explicit_sku = str(getattr(item, "variant_sku", "") or "").strip()
    if explicit_sku:
        return explicit_sku
    meta = str(getattr(item, "meta", "") or "").strip()
    if meta.upper().startswith("SKU "):
        return meta[4:].strip()
    return ""


class CheckoutCompletionRepository(Protocol):
    def complete_checkout(self, *, session_key: str) -> tuple[str, str | None]:
        ...


class DjangoOrmCheckoutCompletionRepository:
    def __init__(self) -> None:
        try:
            from app.modules.checkout import models as checkout_models
            from app.modules.orders import models as order_models
            from app.modules.catalog import models as catalog_models
        except Exception:
            self.session_model = None
            self.order_model = None
            self.order_item_model = None
            self.order_history_model = None
            self.variant_model = None
            return
        self.session_model = getattr(checkout_models, "CheckoutSession", None)
        self.order_model = getattr(order_models, "Order", None)
        self.order_item_model = getattr(order_models, "OrderItem", None)
        self.order_history_model = getattr(order_models, "OrderStatusHistory", None)
        self.variant_model = getattr(catalog_models, "ProductVariant", None)

    def is_ready(self) -> bool:
        models = [self.session_model, self.order_model, self.order_item_model, self.variant_model]
        if any(model is None for model in models):
            return False
        table_names: set[str] = set()
        try:
            for model in models:
                table_names.add(model._meta.db_table)
            if self.order_history_model is not None:
                table_names.add(self.order_history_model._meta.db_table)
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def _get_variant(self, *, tenant_id: int, sku: str):
        if self.variant_model is None or not tenant_id or not sku:
            return None
        try:
            return (
                self.variant_model._default_manager.select_related("product")
                .filter(product__tenant_id=tenant_id, sku=sku)
                .first()
            )
        except Exception:
            return None

    def _validate_inventory_consistency(self, *, session, items: list[object]) -> str | None:
        for item in items:
            variant_sku = _extract_variant_sku(item)
            if not variant_sku:
                return "checkout-completion-inventory-link-missing"
            variant = self._get_variant(tenant_id=int(session.tenant_id), sku=variant_sku)
            if variant is None:
                return "checkout-completion-inventory-unavailable"
            product = getattr(variant, "product", None)
            if product is None or not bool(getattr(product, "is_active", False)) or str(getattr(product, "status", "")) != "active":
                return "checkout-completion-inventory-unavailable"
            if not bool(getattr(variant, "track_inventory", True)):
                continue
            if bool(getattr(variant, "allow_backorder", False)):
                continue
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            free_stock = max(
                int(getattr(variant, "stock", 0) or 0) - int(getattr(variant, "reserved_stock", 0) or 0),
                0,
            )
            if free_stock < quantity:
                return "checkout-completion-stock-conflict"
        return None

    def complete_checkout(self, *, session_key: str) -> tuple[str, str | None]:
        if not self.is_ready() or not session_key:
            return "checkout-completion-unavailable", None

        try:
            session = (
                self.session_model._default_manager.filter(session_key=session_key, status="open")
                .prefetch_related("items")
                .first()
            )
        except Exception:
            return "checkout-completion-unavailable", None

        if session is None:
            return "checkout-completion-unavailable", None

        items = list(getattr(session, "items").all())
        has_shipping_address = all(
            [
                str(getattr(session, "first_name", "") or "").strip(),
                str(getattr(session, "last_name", "") or "").strip(),
                str(getattr(session, "address_line_1", "") or "").strip(),
                str(getattr(session, "city", "") or "").strip(),
                str(getattr(session, "state", "") or "").strip(),
                str(getattr(session, "zip_code", "") or "").strip(),
            ]
        )
        has_shipping_method = bool(str(getattr(session, "shipping_method_selected", "") or "").strip())
        has_payment_method = bool(str(getattr(session, "payment_method_selected", "") or "").strip())
        accepted_terms = bool(getattr(session, "accept_terms", False))
        if not items or not has_shipping_address or not has_shipping_method or not has_payment_method or not accepted_terms:
            return "checkout-completion-blocked", None
        inventory_result = self._validate_inventory_consistency(session=session, items=items)
        if inventory_result is not None:
            return inventory_result, None

        with transaction.atomic():
            order_number = self._next_order_number(tenant_id=int(session.tenant_id))
            order = self.order_model._default_manager.create(
                tenant=session.tenant,
                number=order_number,
                status="pending",
                customer_name=_combine_customer_name(session.first_name, session.last_name),
                customer_email=str(getattr(session, "email", "") or "").strip(),
                customer_phone=str(getattr(session, "phone", "") or "").strip(),
                fulfillment_status_label="Aguardando pagamento",
                fulfillment_status_variant="warning",
                payment_status="Pagamento pendente",
                shipping_status="Aguardando confirmação",
                shipping_address_summary=_combine_shipping_address(
                    address_line_1=str(getattr(session, "address_line_1", "") or ""),
                    address_line_2=str(getattr(session, "address_line_2", "") or ""),
                    city=str(getattr(session, "city", "") or ""),
                    state=str(getattr(session, "state", "") or ""),
                    zip_code=str(getattr(session, "zip_code", "") or ""),
                ),
                notes_content="Pedido iniciado a partir da revisão do checkout. Aguardando evolução do fluxo de pagamento.",
                subtotal=_safe_decimal(getattr(session, "subtotal", Decimal("0.00"))),
                shipping_total=_safe_decimal(getattr(session, "shipping_total", Decimal("0.00"))),
                discount_total=_safe_decimal(getattr(session, "discount_total", Decimal("0.00"))),
                total=_safe_decimal(getattr(session, "grand_total", Decimal("0.00"))),
                installments_summary=str(getattr(session, "installments_summary", "") or ""),
            )
            for index, item in enumerate(items, start=1):
                self.order_item_model._default_manager.create(
                    order=order,
                    title=str(getattr(item, "title", "") or ""),
                    subtitle=str(getattr(item, "subtitle", "") or ""),
                    meta=str(getattr(item, "meta", "") or ""),
                    variant_sku=_extract_variant_sku(item),
                    price_snapshot=_safe_decimal(getattr(item, "price", Decimal("0.00"))),
                    quantity=int(getattr(item, "quantity", 1) or 1),
                    quantity_readonly=bool(getattr(item, "quantity_readonly", True)),
                    sort_order=index,
                )
            if self.order_history_model is not None:
                self.order_history_model._default_manager.create(
                    order=order,
                    event_type="checkout_completed",
                    source_type="checkout_flow",
                    source_label="Checkout",
                    actor_label="Cliente",
                    title="Pedido iniciado no checkout",
                    description="O pedido foi persistido a partir da etapa de revisão, aguardando a próxima evolução do pagamento.",
                    badge_label="Checkout",
                    badge_variant="info",
                )
            session.status = "completed"
            session.save(update_fields=["status", "updated_at"])
        return "checkout-completed", order_number

    def _next_order_number(self, *, tenant_id: int) -> str:
        existing_numbers = list(
            self.order_model._default_manager.filter(tenant_id=tenant_id).values_list("number", flat=True)
        )
        numeric_values = []
        for value in existing_numbers:
            stripped = str(value or "").strip().lstrip("#")
            if stripped.isdigit():
                numeric_values.append(int(stripped))
        next_value = (max(numeric_values) + 1) if numeric_values else 1001
        return str(next_value)


@dataclass
class CheckoutCompletionCommandService:
    repository: CheckoutCompletionRepository

    def complete_checkout(self, *, session_key: str) -> tuple[str, str | None]:
        return self.repository.complete_checkout(session_key=session_key)


checkout_completion_commands = CheckoutCompletionCommandService(
    repository=DjangoOrmCheckoutCompletionRepository(),
)
