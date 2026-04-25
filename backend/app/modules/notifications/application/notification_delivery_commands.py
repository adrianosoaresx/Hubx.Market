from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.application.notification_log_status_commands import (
    mark_email_log_failed,
    mark_email_log_requested,
    mark_email_log_sent,
    mark_email_log_skipped,
)
from app.modules.notifications.infrastructure.email_delivery import EmailDeliveryAdapter
from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class EmailDeliveryCommandResult:
    result: str
    log: EmailLog | None


class EmailDeliveryCommandService:
    def __init__(self, *, adapter: EmailDeliveryAdapter | None = None) -> None:
        self.adapter = adapter or EmailDeliveryAdapter()

    def process_email_log(self, *, tenant_id: int | str, log_id: int | str) -> EmailDeliveryCommandResult:
        log = mark_email_log_requested(tenant_id=tenant_id, log_id=log_id)
        if log is None:
            return EmailDeliveryCommandResult(result="email-log-unavailable", log=None)
        if log.status not in {EmailLog.Status.REQUESTED, EmailLog.Status.SENT, EmailLog.Status.FAILED, EmailLog.Status.SKIPPED}:
            return EmailDeliveryCommandResult(result="email-log-not-processable", log=log)
        if log.status in {EmailLog.Status.SENT, EmailLog.Status.FAILED, EmailLog.Status.SKIPPED}:
            return EmailDeliveryCommandResult(result=f"email-log-{log.status}", log=log)

        delivery_result = self.adapter.deliver(log=log)
        if delivery_result.status == "sent":
            updated_log = mark_email_log_sent(tenant_id=tenant_id, log_id=log.id)
            return EmailDeliveryCommandResult(result="email-log-sent", log=updated_log)
        if delivery_result.status == "dry-run":
            updated_log = mark_email_log_skipped(
                tenant_id=tenant_id,
                log_id=log.id,
                reason=delivery_result.message,
            )
            return EmailDeliveryCommandResult(result="email-log-dry-run", log=updated_log)

        updated_log = mark_email_log_failed(
            tenant_id=tenant_id,
            log_id=log.id,
            error=delivery_result.message,
        )
        return EmailDeliveryCommandResult(result="email-log-failed", log=updated_log)


email_delivery_commands = EmailDeliveryCommandService()
