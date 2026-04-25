from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.utils import timezone

from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class AdminEmailLogItem:
    id: int
    tenant_id: str
    status: str
    source_event: str
    intent_key: str
    audience: str
    recipient_type: str
    recipient_email: str
    title: str
    created_at: object


def list_admin_email_logs(
    *,
    tenant_id: int | str,
    status: str | None = None,
    stale_hours: int = 0,
    limit: int = 25,
) -> list[AdminEmailLogItem]:
    normalized_tenant_id = str(tenant_id or "").strip()
    if not normalized_tenant_id:
        return []
    safe_limit = max(1, min(int(limit or 25), 100))
    queryset = EmailLog.objects.filter(tenant_id=normalized_tenant_id).order_by("-created_at", "-id")
    normalized_status = str(status or "").strip()
    if normalized_status:
        queryset = queryset.filter(status=normalized_status)
    safe_stale_hours = max(0, int(stale_hours or 0))
    if safe_stale_hours:
        cutoff = timezone.now() - timedelta(hours=safe_stale_hours)
        queryset = queryset.filter(updated_at__lt=cutoff)
    return [
        AdminEmailLogItem(
            id=log.id,
            tenant_id=str(log.tenant_id),
            status=log.status,
            source_event=log.source_event,
            intent_key=log.intent_key,
            audience=log.audience,
            recipient_type=log.recipient_type,
            recipient_email=log.recipient_email,
            title=log.title,
            created_at=log.created_at,
        )
        for log in queryset[:safe_limit]
    ]
