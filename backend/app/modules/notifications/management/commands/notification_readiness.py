from django.core.management.base import BaseCommand

from app.modules.notifications.application.notification_readiness_queries import (
    get_notification_readiness_snapshot,
)


class Command(BaseCommand):
    help = "Report tenant-scoped notification delivery readiness counters."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)

    def handle(self, *args, **options):
        snapshot = get_notification_readiness_snapshot(tenant_id=options["tenant_id"])
        self.stdout.write(
            self.style.SUCCESS(
                "tenant={tenant_id} total={total} planned={planned} requested={requested} "
                "sent={sent} failed={failed} skipped={skipped} pending={pending} failures={failures}".format(
                    tenant_id=snapshot.tenant_id,
                    total=snapshot.total,
                    planned=snapshot.planned,
                    requested=snapshot.requested,
                    sent=snapshot.sent,
                    failed=snapshot.failed,
                    skipped=snapshot.skipped,
                    pending=str(snapshot.has_pending_delivery).lower(),
                    failures=str(snapshot.has_failures).lower(),
                )
            )
        )
