from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_local_secret_code_retirement_execution_queries import (
    owner_mfa_local_secret_code_retirement_execution_queries,
)


class Command(BaseCommand):
    help = "Captura evidência da execution de aposentadoria do default local/plain TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_local_secret_code_retirement_execution_queries.get_evidence(tenant_id=options["tenant_id"])
        status = str(result["status"]).upper()
        self.stdout.write(
            f"[{status}] result={result['result']} tenant_id={result['tenant_id']} "
            f"allow_local_plain={result['allow_local_plain']}"
        )
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
