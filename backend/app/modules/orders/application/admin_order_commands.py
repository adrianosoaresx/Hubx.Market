from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from app.modules.coupons.application.coupon_redemption_commands import coupon_redemption_commands


ORDER_STATUS_OPTIONS = [
    {"value": "paid", "label": "Pago"},
    {"value": "pending", "label": "Pendente"},
    {"value": "shipped", "label": "Enviado"},
    {"value": "canceled", "label": "Cancelado"},
]

FULFILLMENT_STATUS_OPTIONS = [
    {"value": "awaiting-payment", "label": "Aguardando pagamento", "variant": "warning"},
    {"value": "picking", "label": "Separando itens", "variant": "info"},
    {"value": "in-transit", "label": "Em trânsito", "variant": "shipped"},
    {"value": "completed", "label": "Concluído", "variant": "success"},
    {"value": "canceled", "label": "Cancelado", "variant": "danger"},
]


def _extract_variant_sku(order_item) -> str:
    explicit_sku = str(getattr(order_item, "variant_sku", "") or "").strip()
    if explicit_sku:
        return explicit_sku
    meta = str(getattr(order_item, "meta", "") or "").strip()
    if meta.upper().startswith("SKU "):
        return meta[4:].strip()
    return ""


class DjangoOrmAdminOrderCommandRepository:
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

    def get_order(self, order_number: str, *, tenant_id: int | None = None):
        if self.order_model is None:
            return None
        try:
            queryset = self.order_model._default_manager.filter(number=order_number.lstrip("#"))
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            return queryset.first()
        except Exception:
            return None

    def save(self, order) -> None:
        order.save()

    def get_variant_for_update(self, *, tenant_id: int | None, sku: str):
        if self.variant_model is None or not tenant_id or not sku:
            return None
        try:
            return (
                self.variant_model._default_manager.select_related("product").select_for_update()
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
        source_type: str = "",
        source_label: str = "",
        actor_label: str = "",
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
class AdminOrderCommandService:
    repository: DjangoOrmAdminOrderCommandRepository

    @staticmethod
    def _normalized_actor_label(actor_label: str = "") -> str:
        normalized = str(actor_label or "").strip()
        return normalized or "Operação interna"

    def _active_inventory_exception_code(self, *, order) -> str:
        if (
            getattr(order, "inventory_reserved_at", None)
            or getattr(order, "inventory_recovered_at", None)
            or getattr(order, "inventory_finalized_at", None)
        ):
            return ""
        order_status = str(getattr(order, "status", "") or "")
        if order_status in {"canceled", "shipped"}:
            return ""
        items = list(getattr(order, "items", []).all())
        linked_items = []
        for item in items:
            variant_sku = _extract_variant_sku(item)
            if variant_sku:
                linked_items.append((item, variant_sku))
        if not linked_items:
            return "inventory-link-missing"
        for item, variant_sku in linked_items:
            variant = self.repository.get_variant_for_update(tenant_id=getattr(order, "tenant_id", None), sku=variant_sku)
            if variant is None:
                return "inventory-variant-missing"
            product = getattr(variant, "product", None)
            if product is None or not bool(getattr(product, "is_active", False)) or str(getattr(product, "status", "") or "") != "active":
                return "inventory-variant-unavailable"
            if not bool(getattr(variant, "track_inventory", True)) or bool(getattr(variant, "allow_backorder", False)):
                continue
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            free_stock = max(
                int(getattr(variant, "stock", 0) or 0) - int(getattr(variant, "reserved_stock", 0) or 0),
                0,
            )
            if free_stock < quantity:
                return "inventory-stock-conflict"
        return ""

    def _finalize_inventory(self, *, order) -> int:
        finalized_items = 0
        if (
            not getattr(order, "inventory_reserved_at", None)
            or getattr(order, "inventory_recovered_at", None)
            or getattr(order, "inventory_finalized_at", None)
        ):
            return finalized_items
        for item in list(getattr(order, "items", []).all()):
            variant_sku = _extract_variant_sku(item)
            if not variant_sku:
                continue
            variant = self.repository.get_variant_for_update(tenant_id=getattr(order, "tenant_id", None), sku=variant_sku)
            if variant is None or not bool(getattr(variant, "track_inventory", True)):
                continue
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            current_reserved = int(getattr(variant, "reserved_stock", 0) or 0)
            if current_reserved <= 0:
                continue
            finalized_quantity = min(current_reserved, quantity)
            variant.reserved_stock = max(0, current_reserved - finalized_quantity)
            variant.save(update_fields=["reserved_stock", "updated_at"])
            finalized_items += finalized_quantity
        if finalized_items > 0:
            order.inventory_finalized_at = timezone.now()
        return finalized_items

    def _recover_inventory(self, *, order) -> int:
        recovered_items = 0
        if (
            not getattr(order, "inventory_reserved_at", None)
            or getattr(order, "inventory_recovered_at", None)
            or getattr(order, "inventory_finalized_at", None)
        ):
            return recovered_items
        for item in list(getattr(order, "items", []).all()):
            variant_sku = _extract_variant_sku(item)
            if not variant_sku:
                continue
            variant = self.repository.get_variant_for_update(tenant_id=getattr(order, "tenant_id", None), sku=variant_sku)
            if variant is None or not bool(getattr(variant, "track_inventory", True)):
                continue
            quantity = max(1, int(getattr(item, "quantity", 1) or 1))
            current_reserved = int(getattr(variant, "reserved_stock", 0) or 0)
            if current_reserved <= 0:
                continue
            recovered_quantity = min(current_reserved, quantity)
            variant.reserved_stock = max(0, current_reserved - recovered_quantity)
            variant.stock = int(getattr(variant, "stock", 0) or 0) + recovered_quantity
            variant.save(update_fields=["stock", "reserved_stock", "updated_at"])
            recovered_items += recovered_quantity
        if recovered_items > 0:
            order.inventory_recovered_at = timezone.now()
        return recovered_items

    def _mark_shipment_sent(self, *, order) -> str:
        try:
            from app.modules.shipping.application.shipment_commands import shipment_commands
        except Exception:
            return "shipment-command-unavailable"
        return shipment_commands.mark_shipment_sent(
            tenant_id=getattr(order, "tenant_id", None),
            order_number=str(getattr(order, "number", "") or ""),
        )

    def _mark_shipment_delivered(self, *, order) -> str:
        try:
            from app.modules.shipping.application.shipment_commands import shipment_commands
        except Exception:
            return "shipment-command-unavailable"
        delivery_result = shipment_commands.mark_shipment_delivered(
            tenant_id=getattr(order, "tenant_id", None),
            order_number=str(getattr(order, "number", "") or ""),
        )
        if delivery_result in {"shipment-not-found", "shipment-delivery-blocked"}:
            sent_result = self._mark_shipment_sent(order=order)
            if sent_result in {"shipment-sent", "shipment-sent-already-recorded"}:
                delivery_result = shipment_commands.mark_shipment_delivered(
                    tenant_id=getattr(order, "tenant_id", None),
                    order_number=str(getattr(order, "number", "") or ""),
                )
        return delivery_result

    def complete_delivery(self, *, order_number: str, tenant_id: int | None = None) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        current_status = str(getattr(order, "status", "") or "")
        current_fulfillment_label = str(getattr(order, "fulfillment_status_label", "") or "")
        current_shipping_status = str(getattr(order, "shipping_status", "") or "")

        if current_status == "canceled":
            return False, "delivery-completion-blocked"
        if current_fulfillment_label == "Concluído" and current_shipping_status == "Entregue":
            return False, "delivery-already-completed"
        if current_status != "shipped" or current_fulfillment_label != "Em trânsito" or current_shipping_status != "Em trânsito":
            return False, "delivery-completion-blocked"

        with transaction.atomic():
            finalized_items = self._finalize_inventory(order=order)
            order.fulfillment_status_label = "Concluído"
            order.fulfillment_status_variant = "success"
            order.shipping_status = "Entregue"
            self.repository.save(order)
            if finalized_items > 0:
                self.repository.create_history_entry(
                    order=order,
                    event_type="inventory_finalized_after_delivery",
                    source_type="admin_action",
                    source_label="Admin Orders",
                    actor_label="Operação interna",
                    title="Estoque finalizado na entrega",
                    description=(
                        f"A entrega confirmou o consumo final de {finalized_items} unidade(s), "
                        "encerrando a reserva operacional ligada ao pedido."
                    ),
                    badge_label="Estoque",
                    badge_variant="success",
                )
            self.repository.create_history_entry(
                order=order,
                event_type="delivery_completed",
                source_type="admin_action",
                source_label="Admin Orders",
                actor_label="Operação interna",
                title="Entrega confirmada",
                description="Pedido marcado como entregue e encerrado operacionalmente após trânsito concluído.",
                badge_label="Entrega",
                badge_variant="success",
            )
            self._mark_shipment_delivered(order=order)
        return True, "delivery-completed"

    def start_shipping(self, *, order_number: str, tenant_id: int | None = None) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        current_status = str(getattr(order, "status", "") or "")
        current_payment_status = str(getattr(order, "payment_status", "") or "")
        current_fulfillment_label = str(getattr(order, "fulfillment_status_label", "") or "")
        current_shipping_status = str(getattr(order, "shipping_status", "") or "")

        if current_status in {"canceled", "shipped"}:
            return False, "shipping-start-blocked"
        if current_status != "paid" or "confirm" not in current_payment_status.lower():
            return False, "shipping-start-blocked"
        if current_fulfillment_label != "Separando itens" and current_shipping_status != "Preparando envio":
            return False, "shipping-start-blocked"
        if current_shipping_status == "Em trânsito" and current_fulfillment_label == "Em trânsito":
            return False, "shipping-already-started"

        order.status = "shipped"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.shipping_status = "Em trânsito"
        self.repository.save(order)
        self.repository.create_history_entry(
            order=order,
            event_type="shipping_started",
            source_type="admin_action",
            source_label="Admin Orders",
            actor_label="Operação interna",
            title="Envio iniciado",
            description="Pedido liberado para trânsito após separação concluída e expedição iniciada.",
            badge_label="Transporte",
            badge_variant="shipped",
        )
        self._mark_shipment_sent(order=order)
        return True, "shipping-started"

    def start_fulfillment(self, *, order_number: str, tenant_id: int | None = None) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        current_status = str(getattr(order, "status", "") or "")
        current_payment_status = str(getattr(order, "payment_status", "") or "")
        current_fulfillment_label = str(getattr(order, "fulfillment_status_label", "") or "")
        current_shipping_status = str(getattr(order, "shipping_status", "") or "")

        if current_status in {"canceled", "shipped"}:
            return False, "fulfillment-start-blocked"
        if current_status != "paid" or "confirm" not in current_payment_status.lower():
            return False, "fulfillment-start-blocked"
        if current_fulfillment_label == "Separando itens" and current_shipping_status == "Preparando envio":
            return False, "fulfillment-already-started"

        order.fulfillment_status_label = "Separando itens"
        order.fulfillment_status_variant = "info"
        order.shipping_status = "Preparando envio"
        self.repository.save(order)
        self.repository.create_history_entry(
            order=order,
            event_type="fulfillment_started",
            source_type="admin_action",
            source_label="Admin Orders",
            actor_label="Operação interna",
            title="Preparação iniciada",
            description="Pedido liberado para separação e preparação de envio após confirmação do pagamento.",
            badge_label="Expedição",
            badge_variant="info",
        )
        return True, "fulfillment-started"

    def cancel_order(self, *, order_number: str, tenant_id: int | None = None) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        current_status = str(getattr(order, "status", "") or "")
        if current_status == "canceled":
            return False, "order-already-canceled"
        if current_status == "shipped":
            return False, "order-cancel-blocked"
        with transaction.atomic():
            recovered_items = self._recover_inventory(order=order)
            order.status = "canceled"
            self.repository.save(order)
            if recovered_items > 0:
                self.repository.create_history_entry(
                    order=order,
                    event_type="inventory_recovered_after_cancel",
                    source_type="admin_action",
                    source_label="Admin Orders",
                    actor_label="Operação interna",
                    title="Estoque devolvido após cancelamento",
                    description=(
                        f"Cancelamento devolveu {recovered_items} unidade(s) ao estoque operacional das variantes ligadas ao pedido."
                    ),
                    badge_label="Estoque",
                    badge_variant="success",
                )
            self.repository.create_history_entry(
                order=order,
                event_type="order_canceled",
                source_type="admin_action",
                source_label="Admin Orders",
                actor_label="Operação interna",
                title="Pedido cancelado",
                description=f"Pedido cancelado a partir do status {self._order_status_label(current_status)}.",
                badge_label="Cancelamento",
                badge_variant="danger",
            )
            coupon_redemption_commands.reverse_order_coupon_redemption(
                tenant_id=tenant_id or getattr(order, "tenant_id", None),
                order_number=str(getattr(order, "number", "") or ""),
                source_type="admin_action",
                source_label="Admin Orders",
            )
        return True, "order-canceled"

    def mark_inventory_exception_under_review(
        self,
        *,
        order_number: str,
        actor_label: str = "",
        tenant_id: int | None = None,
    ) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        normalized_actor = self._normalized_actor_label(actor_label)
        with transaction.atomic():
            exception_code = self._active_inventory_exception_code(order=order)
            if not exception_code:
                return False, "inventory-exception-review-unavailable"
            if getattr(order, "inventory_exception_under_review_at", None) and not getattr(order, "inventory_exception_resolved_at", None):
                return False, "inventory-exception-already-under-review"
            order.inventory_exception_under_review_at = timezone.now()
            order.inventory_exception_resolved_at = None
            order.inventory_exception_owner_label = normalized_actor
            self.repository.save(order)
            self.repository.create_history_entry(
                order=order,
                event_type="inventory_exception_marked_under_review",
                source_type="admin_action",
                source_label="Admin Orders",
                actor_label=normalized_actor,
                title="Exceção de estoque em revisão",
                description=f"Pedido sinalizado para tratamento manual enquanto a exceção de estoque permanece ativa. Responsável atual: {normalized_actor}.",
                badge_label="Estoque",
                badge_variant="warning",
            )
        return True, "inventory-exception-under-review"

    def mark_inventory_exception_resolved(
        self,
        *,
        order_number: str,
        actor_label: str = "",
        tenant_id: int | None = None,
    ) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        normalized_actor = self._normalized_actor_label(actor_label)
        with transaction.atomic():
            exception_code = self._active_inventory_exception_code(order=order)
            if exception_code:
                return False, "inventory-exception-still-active"
            if not getattr(order, "inventory_exception_under_review_at", None):
                return False, "inventory-exception-resolution-unavailable"
            if getattr(order, "inventory_exception_resolved_at", None):
                return False, "inventory-exception-already-resolved"
            order.inventory_exception_resolved_at = timezone.now()
            if not str(getattr(order, "inventory_exception_owner_label", "") or "").strip():
                order.inventory_exception_owner_label = normalized_actor
            self.repository.save(order)
            self.repository.create_history_entry(
                order=order,
                event_type="inventory_exception_marked_resolved",
                source_type="admin_action",
                source_label="Admin Orders",
                actor_label=normalized_actor,
                title="Exceção de estoque resolvida",
                description=(
                    "Tratamento manual concluído após normalização do vínculo ou do saldo operacional do pedido. "
                    f"Fechamento registrado por {normalized_actor}."
                ),
                badge_label="Estoque",
                badge_variant="success",
            )
        return True, "inventory-exception-resolved"

    def reassign_inventory_exception_owner(
        self,
        *,
        order_number: str,
        actor_label: str = "",
        tenant_id: int | None = None,
    ) -> tuple[bool, str]:
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        normalized_actor = self._normalized_actor_label(actor_label)
        with transaction.atomic():
            exception_code = self._active_inventory_exception_code(order=order)
            under_review = bool(getattr(order, "inventory_exception_under_review_at", None))
            resolved = bool(getattr(order, "inventory_exception_resolved_at", None))
            if (not exception_code and not under_review) or resolved:
                return False, "inventory-exception-reassignment-unavailable"
            current_owner = str(getattr(order, "inventory_exception_owner_label", "") or "").strip()
            if current_owner == normalized_actor:
                return False, "inventory-exception-owner-already-assigned"

            previous_owner = current_owner or "Sem responsável"
            order.inventory_exception_owner_label = normalized_actor
            self.repository.save(order)
            self.repository.create_history_entry(
                order=order,
                event_type="inventory_exception_owner_reassigned",
                source_type="admin_action",
                source_label="Admin Orders",
                actor_label=normalized_actor,
                title="Responsável da exceção atualizado",
                description=(
                    f"Responsável da exceção alterado de {previous_owner} para {normalized_actor} "
                    "para continuar o tratamento manual."
                ),
                badge_label="Owner",
                badge_variant="info",
            )
        return True, "inventory-exception-owner-reassigned"

    def bulk_mark_inventory_exception_under_review(
        self,
        *,
        order_numbers: list[str],
        actor_label: str = "",
        tenant_id: int | None = None,
    ) -> tuple[bool, str]:
        changed = 0
        for order_number in order_numbers:
            success, result = self.mark_inventory_exception_under_review(
                order_number=order_number,
                actor_label=actor_label,
                tenant_id=tenant_id,
            )
            if success and result == "inventory-exception-under-review":
                changed += 1
        if changed <= 0:
            return False, "bulk-inventory-exception-under-review-no-change"
        return True, "bulk-inventory-exception-under-review"

    def bulk_mark_inventory_exception_resolved(
        self,
        *,
        order_numbers: list[str],
        actor_label: str = "",
        tenant_id: int | None = None,
    ) -> tuple[bool, str]:
        changed = 0
        for order_number in order_numbers:
            success, result = self.mark_inventory_exception_resolved(
                order_number=order_number,
                actor_label=actor_label,
                tenant_id=tenant_id,
            )
            if success and result == "inventory-exception-resolved":
                changed += 1
        if changed <= 0:
            return False, "bulk-inventory-exception-resolved-no-change"
        return True, "bulk-inventory-exception-resolved"

    def update_order_status(self, *, order_number: str, status: str, tenant_id: int | None = None) -> tuple[bool, str]:
        if status not in {option["value"] for option in ORDER_STATUS_OPTIONS}:
            return False, "order-status-invalid"
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        previous_status = str(getattr(order, "status", "") or "")
        if previous_status == status:
            return False, "order-status-unchanged"
        if getattr(order, "inventory_finalized_at", None):
            return False, "order-status-finalized-blocked"
        if previous_status == "canceled":
            return False, "order-status-canceled-blocked"
        if previous_status == "shipped" and status != "shipped":
            return False, "order-status-shipped-blocked"
        order.status = status
        self.repository.save(order)
        self.repository.create_history_entry(
            order=order,
            event_type="order_status_updated",
            source_type="admin_action",
            source_label="Admin Orders",
            actor_label="Operação interna",
            title="Status do pedido atualizado",
            description=(
                f"Status alterado de {self._order_status_label(previous_status)} para {self._order_status_label(status)}."
            ),
            badge_label="Pedido",
            badge_variant=status if status in {"paid", "shipped"} else "warning" if status == "pending" else "danger",
        )
        return True, "order-status-updated"

    def update_fulfillment_status(
        self,
        *,
        order_number: str,
        fulfillment_status: str,
        tenant_id: int | None = None,
    ) -> tuple[bool, str]:
        option = next((item for item in FULFILLMENT_STATUS_OPTIONS if item["value"] == fulfillment_status), None)
        if option is None:
            return False, "fulfillment-status-invalid"
        order = self.repository.get_order(order_number, tenant_id=tenant_id)
        if order is None:
            return False, "order-not-found"
        previous_label = str(getattr(order, "fulfillment_status_label", "") or "Indefinido")
        if previous_label == str(option["label"]):
            return False, "fulfillment-status-unchanged"
        if getattr(order, "inventory_finalized_at", None):
            return False, "fulfillment-status-finalized-blocked"
        if str(getattr(order, "status", "") or "") == "canceled" and str(option["label"]) != "Cancelado":
            return False, "fulfillment-status-canceled-blocked"
        order.fulfillment_status_label = str(option["label"])
        order.fulfillment_status_variant = str(option["variant"])
        self.repository.save(order)
        self.repository.create_history_entry(
            order=order,
            event_type="fulfillment_status_updated",
            source_type="admin_action",
            source_label="Admin Orders",
            actor_label="Operação interna",
            title="Status operacional atualizado",
            description=f"Operação alterada de {previous_label} para {option['label']}.",
            badge_label="Operação",
            badge_variant=str(option["variant"]),
        )
        return True, "fulfillment-status-updated"

    @staticmethod
    def _order_status_label(value: str) -> str:
        mapping = {option["value"]: option["label"] for option in ORDER_STATUS_OPTIONS}
        return mapping.get(value, "Indefinido")


admin_order_commands = AdminOrderCommandService(
    repository=DjangoOrmAdminOrderCommandRepository(),
)
