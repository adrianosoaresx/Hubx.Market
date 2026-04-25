from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.mail import send_mail

from app.modules.notifications.application.notification_message_renderer import render_email_log_message
from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class EmailDeliveryResult:
    status: str
    message: str


class EmailDeliveryAdapter:
    def deliver(self, *, log: EmailLog) -> EmailDeliveryResult:
        dry_run = bool(getattr(settings, "NOTIFICATIONS_EMAIL_DRY_RUN", True))
        if dry_run:
            return EmailDeliveryResult(status="dry-run", message="Email delivery skipped by dry-run mode.")

        from_email = str(getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip()
        if not from_email:
            return EmailDeliveryResult(status="failed", message="DEFAULT_FROM_EMAIL is not configured.")

        rendered = render_email_log_message(log=log)
        sent_count = send_mail(
            subject=rendered.subject,
            message=rendered.plain_text,
            from_email=from_email,
            recipient_list=[str(log.recipient_email or "").strip()],
            fail_silently=False,
        )
        if sent_count < 1:
            return EmailDeliveryResult(status="failed", message="Email backend did not report a sent message.")
        return EmailDeliveryResult(status="sent", message="Email backend accepted the message.")
