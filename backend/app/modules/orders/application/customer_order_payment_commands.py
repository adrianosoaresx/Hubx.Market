from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone


def _extract_variant_sku(order_item) -> str:
    explicit_sku = str(getattr(order_item, "variant_sku", "") or "").strip()
    if explicit_sku:
        return explicit_sku
    meta = str(getattr(order_item, "meta", "") or "").strip()
    if meta.upper().startswith("SKU "):
        return meta[4:].strip()
    return ""


class DjangoOrmCustomerOrderPaymentCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders import models as order_models
            from app.modules.catalog import models as catalog_models
        except Exception:
            self.order_model = None
            self.history_model = None
            self.variant_model = None
            return
        self.order_model = getattr(order_models, "Order", None)
        self.history_model = getattr(order_models, "OrderStatusHistory", None)
        self.variant_model = getattr(catalog_models, "ProductVariant", None)

    def get_order_for_customer(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ):
        if self.order_model is None or not tenant_id:
            return None
        normalized_order_number = str(order_number or "").lstrip("#")
        normalized_email = str(email or "").strip()
        try:
            if customer_id and hasattr(self.order_model, "customer_id"):
                order = (
                    self.order_model._default_manager.filter(
                        tenant_id=tenant_id,
                        customer_id=customer_id,
                        number=normalized_order_number,
                    )
                    .prefetch_related("items")
                    .first()
                )
                if order is not None:
                    return order
            if not normalized_email:
                return None
            return (
                self.order_model._default_manager.filter(
                    tenant_id=tenant_id,
                    customer_email=normalized_email,
                    number=normalized_order_number,
                )
                .prefetch_related("items")
                .first()
            )
        except Exception:
            return None

    def save_order(self, order) -> None:
        order.save()

    def get_variant_for_update(self, *, tenant_id: int, sku: str):
        if self.variant_model is None or not tenant_id or not sku:
            return None
        try:
            return (
                self.variant_model._default_manager.select_for_update().select_related("product")
                .filter(product__tenant_id=tenant_id, sku=sku)
                .first()
            )
        except Exception:
            return None

    def create_history_entry(
        self,
        *,
        order,
        event_type: str,
        source_type: str,
        source_label: str,
        actor_label: str,
        title: str,
        description: str,
        badge_label: str,
        badge_variant: str,
    ) -> None:
        if self.history_model is None:
            return
        try:
            self.history_model._default_manager.create(
                order=order,
                event_type=event_type,
                source_type=source_type,
                source_label=source_label,
                actor_label=actor_label,
                title=title,
                description=description,
                badge_label=badge_label,
                badge_variant=badge_variant,
            )
        except Exception:
            return


@dataclass
class CustomerOrderPaymentCommandService:
    repository: DjangoOrmCustomerOrderPaymentCommandRepository

    def _validate_inventory_consistency(self, *, order) -> str | None:
        for item in list(getattr(order, "items", []).all()):
            variant_sku = _extract_variant_sku(item)
            if not variant_sku:
                return "payment-confirmation-inventory-link-missing"
            variant = self.repository.get_variant_for_update(tenant_id=getattr(order, "tenant_id", None), sku=variant_sku)
            if variant is None:
                return "payment-confirmation-inventory-unavailable"
            product = getattr(variant, "product", None)
            if product is None or not bool(getattr(product, "is_active", False)) or str(getattr(product, "status", "")) != "active":
                return "payment-confirmation-inventory-unavailable"
            if not bool(getattr(variant, "track_inventory", True)) or bool(getattr(variant, "allow_backorder", False)):
                continue
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            free_stock = max(
                int(getattr(variant, "stock", 0) or 0) - int(getattr(variant, "reserved_stock", 0) or 0),
                0,
            )
            if free_stock < quantity:
                return "payment-confirmation-stock-conflict"
        return None

    def _apply_inventory_reservation(self, *, order) -> int:
        reserved_items = 0
        if getattr(order, "inventory_reserved_at", None):
            return reserved_items
        for item in list(getattr(order, "items", []).all()):
            variant_sku = _extract_variant_sku(item)
            if not variant_sku:
                continue
            variant = self.repository.get_variant_for_update(tenant_id=getattr(order, "tenant_id", None), sku=variant_sku)
            if variant is None or not bool(getattr(variant, "track_inventory", True)):
                continue
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            variant.stock = max(0, int(getattr(variant, "stock", 0) or 0) - quantity)
            variant.reserved_stock = int(getattr(variant, "reserved_stock", 0) or 0) + quantity
            variant.save(update_fields=["stock", "reserved_stock", "updated_at"])
            reserved_items += quantity
        if reserved_items > 0:
            order.inventory_reserved_at = timezone.now()
        return reserved_items

    def confirm_internal_payment(
        self,
        *,
        tenant_id: int | None,
        customer_id: int | None,
        email: str,
        order_number: str,
    ) -> str:
        order = self.repository.get_order_for_customer(
            tenant_id=tenant_id,
            customer_id=customer_id,
            email=email,
            order_number=order_number,
        )
        if order is None:
            return "payment-confirmation-unavailable"

        current_status = str(getattr(order, "status", "") or "")
        current_payment_status = str(getattr(order, "payment_status", "") or "")
        if current_status == "paid" or "confirm" in current_payment_status.lower():
            return "payment-already-confirmed"
        if current_status in {"canceled", "shipped"}:
            return "payment-confirmation-blocked"

        with transaction.atomic():
            inventory_result = self._validate_inventory_consistency(order=order)
            if inventory_result is not None:
                return inventory_result
            reserved_items = self._apply_inventory_reservation(order=order)
            order.status = "paid"
            order.payment_status = "Confirmado internamente"
            order.fulfillment_status_label = "Separando itens"
            order.fulfillment_status_variant = "info"
            order.shipping_status = "Preparando envio"
            order.notes_content = (
                "Pagamento confirmado internamente. "
                "O pedido já pode seguir para separação e próximas atualizações de envio."
            )
            self.repository.save_order(order)
            if reserved_items > 0:
                self.repository.create_history_entry(
                    order=order,
                    event_type="inventory_reserved_after_payment",
                    source_type="checkout_progression",
                    source_label="Checkout / Pedido",
                    actor_label="Sistema",
                    title="Estoque reservado após pagamento",
                    description=(
                        f"O pagamento confirmado aplicou baixa operacional para {reserved_items} unidade(s) "
                        "ligadas às variantes persistidas do pedido."
                    ),
                    badge_label="Estoque",
                    badge_variant="info",
                )
            self.repository.create_history_entry(
                order=order,
                event_type="payment_confirmed_internally",
                source_type="checkout_progression",
                source_label="Checkout / Pedido",
                actor_label="Cliente",
                title="Pagamento confirmado internamente",
                description=(
                    "A confirmação interna do pagamento desbloqueou a preparação do pedido, "
                    "sem depender de gateway externo nesta etapa."
                ),
                badge_label="Pagamento",
                badge_variant="paid",
            )
        return "payment-confirmed"


customer_order_payment_commands = CustomerOrderPaymentCommandService(
    repository=DjangoOrmCustomerOrderPaymentCommandRepository(),
)
