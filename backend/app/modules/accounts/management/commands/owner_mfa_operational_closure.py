from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_operational_closure_queries import owner_mfa_operational_closure_queries


class Command(BaseCommand):
    help = "Fecha pacote operacional de MFA owner/admin sem aplicar enforcement no login."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_operational_closure_queries.get_closure(tenant_id=options["tenant_id"])
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(f"[{status}] result={result['result']}")
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision['key']} status={decision['status']} summary={decision['summary']}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for risk in result["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
