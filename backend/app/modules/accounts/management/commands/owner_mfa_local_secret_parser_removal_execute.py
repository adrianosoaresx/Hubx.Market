from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_local_secret_parser_removal_execution_queries import (
    owner_mfa_local_secret_parser_removal_execution_queries,
)


class Command(BaseCommand):
    help = "Captura evidência da execução de remoção do parser local/plain TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_local_secret_parser_removal_execution_queries.get_evidence()
        status = str(result["status"]).upper()
        local_probe = result["local_probe"]
        legacy_probe = result["legacy_probe"]
        self.stdout.write(
            f"[{status}] result={result['result']} review={result['review']['status']} "
            f"local_probe={local_probe['storage_mode']} legacy_probe={legacy_probe['storage_mode']}"
        )
        self.stdout.write(
            f"probe local_ready={local_probe['ready']} local_secret_returned={local_probe['secret_returned']} "
            f"legacy_ready={legacy_probe['ready']} legacy_secret_returned={legacy_probe['secret_returned']}"
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
