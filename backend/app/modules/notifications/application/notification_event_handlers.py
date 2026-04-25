from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.notifications.application.notification_dispatch_envelopes import (
    build_notification_dispatch_envelope,
)
from app.modules.notifications.application.notification_dispatch_resolver import (
    resolve_notification_dispatch_previews,
)
from app.modules.notifications.application.notification_log_writer import (
    EmailLogWriteResult,
    record_email_log_from_envelope,
)
from app.modules.notifications.application.notification_owner_recipient_resolver import (
    resolve_owner_recipient_targets,
)
from app.modules.notifications.application.notification_recipient_targets import (
    build_customer_recipient_target,
)


class NotificationEventRepository(Protocol):
    def get_order_by_number(self, *, tenant_id: int | str, order_number: str):
        ...


class DjangoOrmNotificationEventRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
        except Exception:
            self.order_model = None
            return
        self.order_model = Order

    def get_order_by_number(self, *, tenant_id: int | str, order_number: str):
        if self.order_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_number = str(order_number or "").lstrip("#").strip()
        if not normalized_tenant_id or not normalized_order_number:
            return None
        try:
            return (
                self.order_model._default_manager.select_related("customer")
                .filter(tenant_id=normalized_tenant_id, number=normalized_order_number)
                .first()
            )
        except Exception:
            return None


@dataclass
class NotificationEventHandlerService:
    repository: NotificationEventRepository

    def record_customer_order_event_email_logs(
        self,
        *,
        tenant_id: int | str,
        source_event: str,
        order_number: str,
    ) -> list[EmailLogWriteResult]:
        order = self.repository.get_order_by_number(
            tenant_id=tenant_id,
            order_number=order_number,
        )
        if order is None:
            return []

        customer = getattr(order, "customer", None)
        customer_id = getattr(order, "customer_id", None)
        customer_email = str(getattr(customer, "email", "") or getattr(order, "customer_email", "") or "").strip()
        customer_name = str(getattr(customer, "full_name", "") or getattr(order, "customer_name", "") or "").strip()
        if not customer_id or not customer_email:
            return []

        previews = resolve_notification_dispatch_previews(
            source_event=source_event,
            tenant_id=tenant_id,
            entity_type="order",
            entity_id=getattr(order, "id", ""),
            audience="customer",
        )
        recipient = build_customer_recipient_target(
            tenant_id=tenant_id,
            customer_id=customer_id,
            email=customer_email,
            display_name=customer_name,
        )
        if recipient is None:
            return []

        results: list[EmailLogWriteResult] = []
        for preview in previews:
            envelope = build_notification_dispatch_envelope(preview=preview, recipient=recipient)
            if envelope is None:
                continue
            results.append(record_email_log_from_envelope(envelope=envelope))
        return results

    def record_owner_order_event_email_logs(
        self,
        *,
        tenant_id: int | str,
        source_event: str,
        order_number: str,
    ) -> list[EmailLogWriteResult]:
        order = self.repository.get_order_by_number(
            tenant_id=tenant_id,
            order_number=order_number,
        )
        if order is None:
            return []

        previews = resolve_notification_dispatch_previews(
            source_event=source_event,
            tenant_id=tenant_id,
            entity_type="order",
            entity_id=getattr(order, "id", ""),
            audience="owner",
        )
        if not previews:
            return []

        results: list[EmailLogWriteResult] = []
        for recipient in resolve_owner_recipient_targets(tenant_id=tenant_id):
            for preview in previews:
                envelope = build_notification_dispatch_envelope(preview=preview, recipient=recipient)
                if envelope is None:
                    continue
                results.append(record_email_log_from_envelope(envelope=envelope))
        return results


notification_event_handlers = NotificationEventHandlerService(
    repository=DjangoOrmNotificationEventRepository(),
)
