from __future__ import annotations

from dataclasses import dataclass


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


class DjangoOrmAdminOrderCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders import models as order_models
        except Exception:
            self.order_model = None
            self.history_model = None
            return
        self.order_model = getattr(order_models, "Order", None)
        self.history_model = getattr(order_models, "OrderStatusHistory", None)

    def get_order(self, order_number: str):
        if self.order_model is None:
            return None
        try:
            return self.order_model._default_manager.filter(number=order_number.lstrip("#")).first()
        except Exception:
            return None

    def save(self, order) -> None:
        order.save()

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

    def cancel_order(self, *, order_number: str) -> tuple[bool, str]:
        order = self.repository.get_order(order_number)
        if order is None:
            return False, "order-not-found"
        current_status = str(getattr(order, "status", "") or "")
        if current_status == "canceled":
            return False, "order-already-canceled"
        if current_status == "shipped":
            return False, "order-cancel-blocked"
        order.status = "canceled"
        self.repository.save(order)
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
        return True, "order-canceled"

    def update_order_status(self, *, order_number: str, status: str) -> tuple[bool, str]:
        if status not in {option["value"] for option in ORDER_STATUS_OPTIONS}:
            return False, "order-status-invalid"
        order = self.repository.get_order(order_number)
        if order is None:
            return False, "order-not-found"
        previous_status = str(getattr(order, "status", "") or "")
        if previous_status == status:
            return False, "order-status-unchanged"
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

    def update_fulfillment_status(self, *, order_number: str, fulfillment_status: str) -> tuple[bool, str]:
        option = next((item for item in FULFILLMENT_STATUS_OPTIONS if item["value"] == fulfillment_status), None)
        if option is None:
            return False, "fulfillment-status-invalid"
        order = self.repository.get_order(order_number)
        if order is None:
            return False, "order-not-found"
        previous_label = str(getattr(order, "fulfillment_status_label", "") or "Indefinido")
        if previous_label == str(option["label"]):
            return False, "fulfillment-status-unchanged"
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
