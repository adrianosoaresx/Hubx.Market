from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class ShippingEventSubscriber(Protocol):
    def record_customer_order_event_email_logs(
        self,
        *,
        tenant_id: int | str,
        source_event: str,
        order_number: str,
    ) -> list[object]:
        ...

    def record_owner_order_event_email_logs(
        self,
        *,
        tenant_id: int | str,
        source_event: str,
        order_number: str,
    ) -> list[object]:
        ...


class NotificationShippingEventSubscriber:
    def __init__(self) -> None:
        try:
            from app.modules.notifications.application.notification_event_handlers import notification_event_handlers
        except Exception:
            self.handlers = None
            return
        self.handlers = notification_event_handlers

    def record_customer_order_event_email_logs(
        self,
        *,
        tenant_id: int | str,
        source_event: str,
        order_number: str,
    ) -> list[object]:
        if self.handlers is None:
            return []
        return self.handlers.record_customer_order_event_email_logs(
            tenant_id=tenant_id,
            source_event=source_event,
            order_number=order_number,
        )

    def record_owner_order_event_email_logs(
        self,
        *,
        tenant_id: int | str,
        source_event: str,
        order_number: str,
    ) -> list[object]:
        if self.handlers is None:
            return []
        return self.handlers.record_owner_order_event_email_logs(
            tenant_id=tenant_id,
            source_event=source_event,
            order_number=order_number,
        )


@dataclass
class ShippingEventPublisher:
    subscriber: ShippingEventSubscriber

    def publish_shipment_sent(self, *, tenant_id: int | str, order_number: str) -> int:
        return self._publish_order_shipping_event(
            tenant_id=tenant_id,
            order_number=order_number,
            source_event="shipment.sent",
        )

    def publish_shipment_delivered(self, *, tenant_id: int | str, order_number: str) -> int:
        return self._publish_order_shipping_event(
            tenant_id=tenant_id,
            order_number=order_number,
            source_event="shipment.delivered",
        )

    def _publish_order_shipping_event(self, *, tenant_id: int | str, order_number: str, source_event: str) -> int:
        customer_results = self.subscriber.record_customer_order_event_email_logs(
            tenant_id=tenant_id,
            source_event=source_event,
            order_number=order_number,
        )
        owner_results = self.subscriber.record_owner_order_event_email_logs(
            tenant_id=tenant_id,
            source_event=source_event,
            order_number=order_number,
        )
        return len(customer_results) + len(owner_results)


shipping_event_publisher = ShippingEventPublisher(subscriber=NotificationShippingEventSubscriber())
