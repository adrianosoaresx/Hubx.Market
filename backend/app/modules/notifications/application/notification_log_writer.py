from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from app.modules.notifications.application.notification_dispatch_envelopes import NotificationDispatchEnvelope
from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class EmailLogWriteResult:
    log: EmailLog
    created: bool


def record_email_log_from_envelope(*, envelope: NotificationDispatchEnvelope) -> EmailLogWriteResult:
    with transaction.atomic():
        log, created = EmailLog.objects.get_or_create(
            recipient_delivery_key=envelope.recipient_delivery_key,
            defaults={
                "tenant_id": envelope.tenant_id,
                "source_event": envelope.source_event,
                "intent_key": envelope.intent_key,
                "audience": envelope.audience,
                "channel": envelope.channel,
                "entity_type": envelope.entity_type,
                "entity_id": envelope.entity_id,
                "idempotency_key": envelope.idempotency_key,
                "recipient_type": envelope.recipient_type,
                "recipient_id": envelope.recipient_id,
                "recipient_email": envelope.recipient_email,
                "recipient_display_name": envelope.recipient_display_name,
                "title": envelope.title,
                "description": envelope.description,
                "cta_label": envelope.cta_label,
                "cta_target": envelope.cta_target,
            },
        )
    return EmailLogWriteResult(log=log, created=created)
