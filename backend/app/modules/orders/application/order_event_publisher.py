from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class OrderEventSubscriber(Protocol):
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


class NotificationOrderEventSubscriber:
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
class OrderEventPublisher:
    subscriber: OrderEventSubscriber

    def publish_order_created(self, *, tenant_id: int | str, order_number: str) -> int:
        customer_results = self.subscriber.record_customer_order_event_email_logs(
            tenant_id=tenant_id,
            source_event="order.created",
            order_number=order_number,
        )
        owner_results = self.subscriber.record_owner_order_event_email_logs(
            tenant_id=tenant_id,
            source_event="order.created",
            order_number=order_number,
        )
        return len(customer_results) + len(owner_results)


order_event_publisher = OrderEventPublisher(subscriber=NotificationOrderEventSubscriber())
