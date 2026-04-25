from __future__ import annotations

from celery import shared_task

from app.modules.notifications.application.notification_delivery_commands import email_delivery_commands
from app.modules.notifications.models import EmailLog


@shared_task(name="notifications.process_email_log")
def process_email_log_task(*, tenant_id: int | str, log_id: int | str) -> str:
    result = email_delivery_commands.process_email_log(tenant_id=tenant_id, log_id=log_id)
    return result.result


@shared_task(name="notifications.process_planned_email_logs")
def process_planned_email_logs_task(*, tenant_id: int | str, limit: int = 25) -> dict[str, int]:
    normalized_tenant_id = str(tenant_id or "").strip()
    safe_limit = max(1, min(int(limit or 25), 100))
    if not normalized_tenant_id:
        return {"email-log-unavailable": 0}

    logs = list(
        EmailLog.objects.filter(
            tenant_id=normalized_tenant_id,
            status=EmailLog.Status.PLANNED,
        ).order_by("created_at", "id")[:safe_limit]
    )
    counters: dict[str, int] = {}
    for log in logs:
        result = email_delivery_commands.process_email_log(tenant_id=normalized_tenant_id, log_id=log.id)
        counters[result.result] = counters.get(result.result, 0) + 1
    return counters
