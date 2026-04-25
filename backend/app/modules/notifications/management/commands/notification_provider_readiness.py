from django.core.management.base import BaseCommand

from app.modules.notifications.application.notification_provider_readiness import (
    get_notification_provider_readiness,
)


class Command(BaseCommand):
    help = "Report notification provider readiness before disabling dry-run."

    def handle(self, *args, **options):
        readiness = get_notification_provider_readiness()
        blockers = ",".join(readiness.blockers) if readiness.blockers else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"dry_run={str(readiness.dry_run).lower()} backend={readiness.backend or '-'} "
                f"from_email={readiness.from_email or '-'} can_attempt_real_delivery="
                f"{str(readiness.can_attempt_real_delivery).lower()} blockers={blockers}"
            )
        )
