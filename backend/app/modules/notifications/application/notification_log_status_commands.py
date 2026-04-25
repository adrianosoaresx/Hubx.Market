from __future__ import annotations

from django.utils import timezone

from app.modules.notifications.models import EmailLog


def mark_email_log_requested(*, tenant_id: int | str, log_id: int | str) -> EmailLog | None:
    log = _get_email_log(tenant_id=tenant_id, log_id=log_id)
    if log is None or log.status != EmailLog.Status.PLANNED:
        return log

    log.status = EmailLog.Status.REQUESTED
    log.requested_at = timezone.now()
    log.save(update_fields=("status", "requested_at", "updated_at"))
    return log


def mark_email_log_sent(*, tenant_id: int | str, log_id: int | str) -> EmailLog | None:
    log = _get_email_log(tenant_id=tenant_id, log_id=log_id)
    if log is None or log.status not in {EmailLog.Status.PLANNED, EmailLog.Status.REQUESTED}:
        return log

    log.status = EmailLog.Status.SENT
    log.sent_at = timezone.now()
    log.last_error = ""
    log.save(update_fields=("status", "sent_at", "last_error", "updated_at"))
    return log


def mark_email_log_failed(*, tenant_id: int | str, log_id: int | str, error: str = "") -> EmailLog | None:
    log = _get_email_log(tenant_id=tenant_id, log_id=log_id)
    if log is None or log.status == EmailLog.Status.SENT:
        return log

    log.status = EmailLog.Status.FAILED
    log.failed_at = timezone.now()
    log.last_error = str(error or "").strip()
    log.save(update_fields=("status", "failed_at", "last_error", "updated_at"))
    return log


def mark_email_log_skipped(*, tenant_id: int | str, log_id: int | str, reason: str = "") -> EmailLog | None:
    log = _get_email_log(tenant_id=tenant_id, log_id=log_id)
    if log is None or log.status in {EmailLog.Status.SENT, EmailLog.Status.FAILED}:
        return log

    log.status = EmailLog.Status.SKIPPED
    log.last_error = str(reason or "").strip()
    log.save(update_fields=("status", "last_error", "updated_at"))
    return log


def _get_email_log(*, tenant_id: int | str, log_id: int | str) -> EmailLog | None:
    normalized_tenant_id = str(tenant_id or "").strip()
    normalized_log_id = str(log_id or "").strip()
    if not normalized_tenant_id or not normalized_log_id:
        return None
    try:
        return EmailLog.objects.get(id=normalized_log_id, tenant_id=normalized_tenant_id)
    except EmailLog.DoesNotExist:
        return None
