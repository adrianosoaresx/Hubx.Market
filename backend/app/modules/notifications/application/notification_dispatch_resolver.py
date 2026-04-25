from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.application.notification_intent_catalog import (
    NotificationIntent,
    build_idempotency_key,
    list_notification_intents,
)


@dataclass(frozen=True)
class NotificationDispatchPreview:
    source_event: str
    tenant_id: str
    entity_type: str
    entity_id: str
    audience: str
    channel: str
    intent_key: str
    idempotency_key: str
    title: str
    description: str
    cta_label: str
    cta_target: str


def resolve_notification_dispatch_previews(
    *,
    source_event: str,
    tenant_id: int | str,
    entity_type: str,
    entity_id: int | str,
    audience: str | None = None,
) -> list[NotificationDispatchPreview]:
    normalized_event = str(source_event or "").strip()
    normalized_tenant_id = str(tenant_id or "").strip()
    normalized_entity_type = str(entity_type or "").strip()
    normalized_entity_id = str(entity_id or "").strip()
    normalized_audience = str(audience or "").strip()

    if not normalized_event or not normalized_tenant_id or not normalized_entity_type or not normalized_entity_id:
        return []

    intents = list_notification_intents(source_event=normalized_event)
    if normalized_audience:
        intents = [intent for intent in intents if intent.audience == normalized_audience]

    return [
        _build_dispatch_preview(
            intent=intent,
            tenant_id=normalized_tenant_id,
            entity_type=normalized_entity_type,
            entity_id=normalized_entity_id,
        )
        for intent in intents
    ]


def _build_dispatch_preview(
    *,
    intent: NotificationIntent,
    tenant_id: str,
    entity_type: str,
    entity_id: str,
) -> NotificationDispatchPreview:
    return NotificationDispatchPreview(
        source_event=intent.source_event,
        tenant_id=tenant_id,
        entity_type=entity_type,
        entity_id=entity_id,
        audience=intent.audience,
        channel=intent.channel,
        intent_key=intent.intent_key,
        idempotency_key=build_idempotency_key(
            intent=intent,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
        ),
        title=intent.title,
        description=intent.description,
        cta_label=intent.cta_label,
        cta_target=intent.cta_target,
    )
