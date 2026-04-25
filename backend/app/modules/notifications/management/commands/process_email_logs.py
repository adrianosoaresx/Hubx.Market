from django.conf import settings
from django.core.management.base import BaseCommand

from app.modules.notifications.application.notification_delivery_commands import email_delivery_commands
from app.modules.notifications.models import EmailLog


class Command(BaseCommand):
    help = "Process planned notification email logs in a tenant-scoped, dry-run-safe batch."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--limit", dest="limit", type=int, default=None)

    def handle(self, *args, **options):
        tenant_id = str(options["tenant_id"] or "").strip()
        limit = options.get("limit") or int(getattr(settings, "NOTIFICATIONS_EMAIL_BATCH_SIZE", 25))
        limit = max(1, min(int(limit), 100))

        logs = list(
            EmailLog.objects.filter(
                tenant_id=tenant_id,
                status=EmailLog.Status.PLANNED,
            ).order_by("created_at", "id")[:limit]
        )

        counters: dict[str, int] = {}
        for log in logs:
            result = email_delivery_commands.process_email_log(
                tenant_id=tenant_id,
                log_id=log.id,
            )
            counters[result.result] = counters.get(result.result, 0) + 1

        summary = ", ".join(f"{key}={value}" for key, value in sorted(counters.items())) or "no-op"
        self.stdout.write(
            self.style.SUCCESS(
                f"Processed {len(logs)} email log(s) for tenant {tenant_id}: {summary}"
            )
        )
