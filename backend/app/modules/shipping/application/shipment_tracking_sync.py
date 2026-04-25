from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone

from app.modules.shipping.application.shipping_event_publisher import shipping_event_publisher
from app.modules.shipping.application.shipping_provider_contracts import (
    ShippingProviderGateway,
    manual_shipment_provider_gateway,
)
from app.modules.shipping.models import Shipment, ShipmentStatusHistory


class DjangoOrmShipmentTrackingSyncRepository:
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
class ShipmentTrackingSyncService:
    repository: DjangoOrmShipmentTrackingSyncRepository
    provider_gateway: ShippingProviderGateway

    def sync_tracking_snapshot(
        self,
        *,
        tenant_id: int | str,
        order_number: str,
        provider_gateway: ShippingProviderGateway | None = None,
    ) -> str:
        order = self.repository.get_order(tenant_id=tenant_id, order_number=order_number)
        if order is None:
            return "tracking-sync-order-not-found"

        gateway = provider_gateway or self.provider_gateway
        snapshot = gateway.get_tracking_snapshot(tenant_id=tenant_id, order_number=order.number)
        if snapshot.normalized_status in {"missing", "unknown"} and not snapshot.has_tracking:
            return "tracking-sync-unavailable"

        shipment, created = Shipment.objects.get_or_create(tenant_id=tenant_id, order=order)
        changed_fields = self._apply_tracking_fields(shipment=shipment, snapshot=snapshot)
        if snapshot.has_provider_error:
            if changed_fields:
                shipment.save(update_fields=tuple(changed_fields) + ("updated_at",))
            self._create_history_entry(
                shipment=shipment,
                event_type="shipment_tracking_provider_failed",
                title="Falha no provider de tracking",
                description=self._provider_error_description(snapshot=snapshot),
                snapshot=snapshot,
            )
            return "tracking-sync-provider-error"

        transition_result = self._apply_status_transition(
            shipment=shipment,
            snapshot=snapshot,
            order_number=str(order.number),
            tenant_id=tenant_id,
        )

        if changed_fields and transition_result == "tracking-sync-unchanged":
            shipment.save(update_fields=tuple(changed_fields) + ("updated_at",))
            self._create_history_entry(
                shipment=shipment,
                event_type="shipment_tracking_synced",
                title="Tracking sincronizado",
                description="Dados de rastreio atualizados a partir do provider de shipping.",
                snapshot=snapshot,
            )
            return "tracking-sync-updated"

        if created and transition_result == "tracking-sync-unchanged":
            self._create_history_entry(
                shipment=shipment,
                event_type="shipment_created_from_tracking",
                title="Shipment criado por tracking",
                description="Remessa criada a partir de snapshot disponível no provider de shipping.",
                snapshot=snapshot,
            )
            return "tracking-sync-created"

        return transition_result

    def _apply_tracking_fields(self, *, shipment: Shipment, snapshot) -> list[str]:
        changed_fields: list[str] = []
        for field_name, value in (
            ("tracking_code", snapshot.tracking_code),
            ("tracking_url", snapshot.tracking_url),
            ("carrier_name", snapshot.carrier_name),
        ):
            normalized_value = str(value or "").strip()
            if normalized_value and getattr(shipment, field_name) != normalized_value:
                setattr(shipment, field_name, normalized_value)
                changed_fields.append(field_name)
        return changed_fields

    def _apply_status_transition(self, *, shipment: Shipment, snapshot, order_number: str, tenant_id: int | str) -> str:
        if shipment.status == Shipment.Status.DELIVERED:
            return "tracking-sync-unchanged"
        if snapshot.normalized_status == "delivered":
            if shipment.status != Shipment.Status.SENT:
                shipment.status = Shipment.Status.SENT
                shipment.sent_at = shipment.sent_at or timezone.now()
                shipment.save(update_fields=("status", "tracking_code", "tracking_url", "carrier_name", "sent_at", "updated_at"))
                self._create_history_entry(
                    shipment=shipment,
                    event_type="shipment_sent",
                    title="Shipment enviado",
                    description="Remessa marcada como enviada a partir de snapshot do provider de shipping.",
                    snapshot=snapshot,
                )
                shipping_event_publisher.publish_shipment_sent(tenant_id=tenant_id, order_number=order_number)
            shipment.status = Shipment.Status.DELIVERED
            shipment.delivered_at = shipment.delivered_at or timezone.now()
            shipment.save(update_fields=("status", "tracking_code", "tracking_url", "carrier_name", "delivered_at", "updated_at"))
            self._create_history_entry(
                shipment=shipment,
                event_type="shipment_delivered",
                title="Shipment entregue",
                description="Remessa marcada como entregue a partir de snapshot do provider de shipping.",
                snapshot=snapshot,
            )
            shipping_event_publisher.publish_shipment_delivered(tenant_id=tenant_id, order_number=order_number)
            return "tracking-sync-delivered"
        if snapshot.normalized_status == "in_transit" and shipment.status == Shipment.Status.CREATED:
            shipment.status = Shipment.Status.SENT
            shipment.sent_at = shipment.sent_at or timezone.now()
            shipment.save(update_fields=("status", "tracking_code", "tracking_url", "carrier_name", "sent_at", "updated_at"))
            self._create_history_entry(
                shipment=shipment,
                event_type="shipment_sent",
                title="Shipment enviado",
                description="Remessa marcada como enviada a partir de snapshot do provider de shipping.",
                snapshot=snapshot,
            )
            shipping_event_publisher.publish_shipment_sent(tenant_id=tenant_id, order_number=order_number)
            return "tracking-sync-sent"
        if snapshot.normalized_status == "canceled" and shipment.status != Shipment.Status.CANCELED:
            shipment.status = Shipment.Status.CANCELED
            shipment.save(update_fields=("status", "tracking_code", "tracking_url", "carrier_name", "updated_at"))
            self._create_history_entry(
                shipment=shipment,
                event_type="shipment_canceled",
                title="Shipment cancelado",
                description="Remessa marcada como cancelada a partir de snapshot do provider de shipping.",
                snapshot=snapshot,
            )
            return "tracking-sync-canceled"
        return "tracking-sync-unchanged"

    def _create_history_entry(
        self,
        *,
        shipment: Shipment,
        event_type: str,
        title: str,
        description: str,
        snapshot=None,
    ) -> None:
        provider_http_status = getattr(snapshot, "provider_http_status", None)
        provider_latency_ms = getattr(snapshot, "provider_latency_ms", None)
        ShipmentStatusHistory.objects.create(
            shipment=shipment,
            tenant_id=shipment.tenant_id,
            event_type=event_type,
            source_type="provider_sync",
            source_label="Shipping Provider Sync",
            actor_label="Provider polling",
            title=title,
            description=description,
            provider_http_status=provider_http_status,
            provider_latency_ms=provider_latency_ms,
        )

    def _provider_error_description(self, *, snapshot) -> str:
        error_code = str(snapshot.provider_error_code or "provider_error").strip()
        error_message = str(snapshot.provider_error_message or "").strip()
        details = []
        if snapshot.provider_http_status is not None:
            details.append(f"HTTP {snapshot.provider_http_status}")
        if snapshot.provider_latency_ms is not None:
            details.append(f"{snapshot.provider_latency_ms}ms")
        suffix = f" [{', '.join(details)}]" if details else ""
        if error_message:
            return f"Provider de shipping falhou durante sync de tracking ({error_code}: {error_message}){suffix}."
        return f"Provider de shipping falhou durante sync de tracking ({error_code}){suffix}."


shipment_tracking_sync = ShipmentTrackingSyncService(
    repository=DjangoOrmShipmentTrackingSyncRepository(),
    provider_gateway=manual_shipment_provider_gateway,
)
