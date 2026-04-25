from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from app.modules.shipping.application.shipping_event_publisher import shipping_event_publisher
from app.modules.shipping.models import Shipment, ShipmentStatusHistory


class DjangoOrmShipmentCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
        except Exception:
            self.order_model = None
            return
        self.order_model = Order

    def get_order(self, *, tenant_id: int | str, order_number: str):
        if self.order_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_number = str(order_number or "").strip().lstrip("#")
        if not normalized_tenant_id or not normalized_order_number:
            return None
        try:
            return self.order_model._default_manager.filter(
                tenant_id=normalized_tenant_id,
                number=normalized_order_number,
            ).first()
        except Exception:
            return None


@dataclass
class ShipmentCommandService:
    repository: DjangoOrmShipmentCommandRepository

    def _create_history_entry(
        self,
        *,
        shipment: Shipment,
        event_type: str,
        title: str,
        description: str,
    ) -> None:
        ShipmentStatusHistory.objects.create(
            shipment=shipment,
            tenant_id=shipment.tenant_id,
            event_type=event_type,
            source_type="application_command",
            source_label="Shipping Commands",
            actor_label="Operação interna",
            title=title,
            description=description,
        )

    def mark_shipment_sent(
        self,
        *,
        tenant_id: int | str,
        order_number: str,
        tracking_code: str = "",
        tracking_url: str = "",
        carrier_name: str = "",
    ) -> str:
        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "shipment-order-not-found"
        shipment, _ = Shipment.objects.get_or_create(
            tenant_id=tenant_id,
            order=order,
            defaults={
                "tracking_code": str(tracking_code or "").strip(),
                "tracking_url": str(tracking_url or "").strip(),
                "carrier_name": str(carrier_name or "").strip(),
            },
        )
        if shipment.status in {Shipment.Status.SENT, Shipment.Status.DELIVERED}:
            return "shipment-sent-already-recorded"
        shipment.status = Shipment.Status.SENT
        shipment.tracking_code = str(tracking_code or shipment.tracking_code or "").strip()
        shipment.tracking_url = str(tracking_url or shipment.tracking_url or "").strip()
        shipment.carrier_name = str(carrier_name or shipment.carrier_name or "").strip()
        shipment.sent_at = shipment.sent_at or timezone.now()
        shipment.save(update_fields=("status", "tracking_code", "tracking_url", "carrier_name", "sent_at", "updated_at"))
        self._create_history_entry(
            shipment=shipment,
            event_type="shipment_sent",
            title="Shipment enviado",
            description="Remessa marcada como enviada a partir do comando operacional de shipping.",
        )
        shipping_event_publisher.publish_shipment_sent(tenant_id=tenant_id, order_number=order.number)
        return "shipment-sent"

    def mark_shipment_delivered(
        self,
        *,
        tenant_id: int | str,
        order_number: str,
    ) -> str:
        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "shipment-order-not-found"
        shipment = Shipment.objects.filter(tenant_id=tenant_id, order=order).first()
        if shipment is None:
            return "shipment-not-found"
        if shipment.status == Shipment.Status.DELIVERED:
            return "shipment-delivered-already-recorded"
        if shipment.status != Shipment.Status.SENT:
            return "shipment-delivery-blocked"
        shipment.status = Shipment.Status.DELIVERED
        shipment.delivered_at = shipment.delivered_at or timezone.now()
        shipment.save(update_fields=("status", "delivered_at", "updated_at"))
        self._create_history_entry(
            shipment=shipment,
            event_type="shipment_delivered",
            title="Shipment entregue",
            description="Remessa marcada como entregue a partir do comando operacional de shipping.",
        )
        shipping_event_publisher.publish_shipment_delivered(tenant_id=tenant_id, order_number=order.number)
        return "shipment-delivered"


shipment_commands = ShipmentCommandService(repository=DjangoOrmShipmentCommandRepository())
