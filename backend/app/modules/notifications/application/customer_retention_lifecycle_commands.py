from __future__ import annotations

from dataclasses import dataclass

from app.modules.newsletter.models import NewsletterSubscriber
from app.modules.notifications.application.notification_dispatch_envelopes import NotificationDispatchEnvelope
from app.modules.notifications.application.notification_intent_catalog import build_idempotency_key, get_notification_intent
from app.modules.notifications.application.notification_log_writer import record_email_log_from_envelope
from app.modules.orders.models import Order


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class CustomerRetentionLifecycleCommandService:
    def plan_post_purchase_follow_up(
        self,
        *,
        tenant_id: int | str | None,
        order_id: int | str | None,
    ) -> dict[str, object]:
        if not tenant_id:
            return {"result": "retention-lifecycle-tenant-required", "errors": {"tenant_id": "required"}}
        if not order_id:
            return {"result": "retention-lifecycle-order-required", "errors": {"order_id": "required"}}

        order = Order.objects.filter(pk=order_id, tenant_id=tenant_id).first()
        if order is None:
            return {"result": "retention-lifecycle-order-not-found", "errors": {"order_id": "not-found"}}
        if order.status not in {Order.Status.PAID, Order.Status.SHIPPED}:
            return {"result": "retention-lifecycle-order-not-eligible", "order": {"id": order.id, "status": order.status}}

        recipient_email = _string(order.customer_email, limit=254).lower()
        if not recipient_email:
            return {"result": "retention-lifecycle-recipient-missing", "errors": {"email": "missing"}}

        subscriber = NewsletterSubscriber.objects.filter(
            tenant_id=tenant_id,
            email__iexact=recipient_email,
        ).first()
        if subscriber is None:
            return {"result": "retention-lifecycle-not-subscribed", "order": {"id": order.id}}
        if subscriber.status != NewsletterSubscriber.Status.SUBSCRIBED:
            return {"result": "retention-lifecycle-opted-out", "subscriber": {"id": subscriber.id, "status": subscriber.status}}

        intent = get_notification_intent("customer.post_purchase.follow_up")
        if intent is None:
            return {"result": "retention-lifecycle-intent-unavailable", "errors": {"intent": "missing"}}

        idempotency_key = build_idempotency_key(
            intent=intent,
            tenant_id=tenant_id,
            entity_type="order",
            entity_id=order.id,
        )
        envelope = NotificationDispatchEnvelope(
            tenant_id=str(tenant_id),
            source_event=intent.source_event,
            entity_type="order",
            entity_id=str(order.id),
            audience=intent.audience,
            channel=intent.channel,
            intent_key=intent.intent_key,
            idempotency_key=idempotency_key,
            recipient_delivery_key=f"{idempotency_key}:newsletter_subscriber:{subscriber.id}",
            recipient_type="newsletter_subscriber",
            recipient_id=str(subscriber.id),
            recipient_email=subscriber.email,
            recipient_display_name=_string(subscriber.name, limit=150) or _string(order.customer_name, limit=150),
            title=intent.title,
            description=intent.description,
            cta_label=intent.cta_label,
            cta_target=intent.cta_target,
        )
        write_result = record_email_log_from_envelope(envelope=envelope)
        return {
            "result": "retention-lifecycle-planned" if write_result.created else "retention-lifecycle-already-planned",
            "email_log": {
                "id": write_result.log.id,
                "tenant_id": write_result.log.tenant_id,
                "intent_key": write_result.log.intent_key,
                "status": write_result.log.status,
            },
        }


customer_retention_lifecycle_commands = CustomerRetentionLifecycleCommandService()
