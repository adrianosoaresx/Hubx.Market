from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.application.notification_cta_resolver import resolve_notification_cta
from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class RenderedNotificationMessage:
    subject: str
    plain_text: str
    cta_url: str


def render_email_log_message(*, log: EmailLog) -> RenderedNotificationMessage:
    cta = resolve_notification_cta(
        tenant_id=log.tenant_id,
        cta_label=log.cta_label,
        cta_target=log.cta_target,
        entity_type=log.entity_type,
        entity_id=log.entity_id,
    )
    lines = [str(log.description or "").strip()]
    cta_url = ""
    if cta is not None:
        cta_url = cta.url
        lines.extend(["", f"{cta.label}: {cta.url}".strip(": ")])

    return RenderedNotificationMessage(
        subject=str(log.title or "").strip(),
        plain_text="\n".join(line for line in lines if line is not None).strip(),
        cta_url=cta_url,
    )
