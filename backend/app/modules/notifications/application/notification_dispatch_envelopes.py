from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.application.notification_dispatch_resolver import NotificationDispatchPreview
from app.modules.notifications.application.notification_recipient_targets import NotificationRecipientTarget


@dataclass(frozen=True)
class NotificationDispatchEnvelope:
    tenant_id: str
    source_event: str
    entity_type: str
    entity_id: str
    audience: str
    channel: str
    intent_key: str
    idempotency_key: str
    recipient_delivery_key: str
    recipient_type: str
    recipient_id: str
    recipient_email: str
    recipient_display_name: str
    title: str
    description: str
    cta_label: str
    cta_target: str


def build_notification_dispatch_envelope(
    *,
    preview: NotificationDispatchPreview,
    recipient: NotificationRecipientTarget,
) -> NotificationDispatchEnvelope | None:
    if preview.tenant_id != recipient.tenant_id:
        return None
    if preview.audience != recipient.audience:
        return None
    if not recipient.is_deliverable:
        return None

    return NotificationDispatchEnvelope(
        tenant_id=preview.tenant_id,
        source_event=preview.source_event,
        entity_type=preview.entity_type,
        entity_id=preview.entity_id,
        audience=preview.audience,
        channel=preview.channel,
        intent_key=preview.intent_key,
        idempotency_key=preview.idempotency_key,
        recipient_delivery_key=_build_recipient_delivery_key(
            idempotency_key=preview.idempotency_key,
            recipient=recipient,
        ),
        recipient_type=recipient.recipient_type,
        recipient_id=recipient.recipient_id,
        recipient_email=recipient.email,
        recipient_display_name=recipient.display_name,
        title=preview.title,
        description=preview.description,
        cta_label=preview.cta_label,
        cta_target=preview.cta_target,
    )


def _build_recipient_delivery_key(
    *,
    idempotency_key: str,
    recipient: NotificationRecipientTarget,
) -> str:
    return f"{idempotency_key}:{recipient.recipient_type}:{recipient.recipient_id}"
