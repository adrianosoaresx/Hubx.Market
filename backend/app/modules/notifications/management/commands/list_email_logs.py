from django.core.management.base import BaseCommand

from app.modules.notifications.application.notification_admin_queries import list_admin_email_logs


class Command(BaseCommand):
    help = "List tenant-scoped notification email logs for operations."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--status", dest="status", default="")
        parser.add_argument("--stale-hours", dest="stale_hours", type=int, default=0)
        parser.add_argument("--limit", dest="limit", type=int, default=25)

    def handle(self, *args, **options):
        items = list_admin_email_logs(
            tenant_id=options["tenant_id"],
            status=options.get("status") or None,
            stale_hours=options.get("stale_hours") or 0,
            limit=options.get("limit") or 25,
        )
        for item in items:
            self.stdout.write(
                f"id={item.id} status={item.status} event={item.source_event} "
                f"intent={item.intent_key} audience={item.audience} recipient={item.recipient_email}"
            )
        self.stdout.write(self.style.SUCCESS(f"Listed {len(items)} email log(s)."))
