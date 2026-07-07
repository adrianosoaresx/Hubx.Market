from __future__ import annotations

from dataclasses import dataclass


class DjangoOrmShipmentLabelRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
        except Exception:
            self.order_model = None
            return
        self.order_model = Order

    def get_label(self, *, tenant_id: int | str | None, order_number: object) -> dict[str, str] | None:
        if self.order_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_number = str(order_number or "").strip().lstrip("#")
        if not normalized_tenant_id or not normalized_order_number:
            return None
        order = (
            self.order_model._default_manager.filter(
                tenant_id=normalized_tenant_id,
                number=normalized_order_number,
            )
            .select_related("tenant")
            .first()
        )
        if order is None:
            return None
        try:
            shipment = order.shipment
        except Exception:
            return None
        if not getattr(shipment, "label_code", ""):
            return None
        return {
            "store_name": str(getattr(order.tenant, "name", "") or ""),
            "order_number": str(order.number),
            "customer_name": str(order.customer_name or ""),
            "customer_email": str(order.customer_email or ""),
            "shipping_address": str(order.shipping_address_summary or ""),
            "carrier_name": str(shipment.carrier_name or "Operação logística"),
            "tracking_code": str(shipment.tracking_code or ""),
            "label_code": str(shipment.label_code),
            "label_created_at": shipment.label_created_at.strftime("%d/%m/%Y %H:%M")
            if shipment.label_created_at
            else "",
        }


@dataclass
class ShipmentLabelQueryService:
    repository: DjangoOrmShipmentLabelRepository

    def get_label(self, *, tenant_id: int | str | None, order_number: object) -> dict[str, str] | None:
        return self.repository.get_label(tenant_id=tenant_id, order_number=order_number)


shipment_label_queries = ShipmentLabelQueryService(repository=DjangoOrmShipmentLabelRepository())
