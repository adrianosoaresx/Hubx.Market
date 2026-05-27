from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_local_secret_parser_removal_queries import owner_mfa_local_secret_parser_removal_queries


class Command(BaseCommand):
    help = "Revisa se o parser local/plain TOTP MFA owner/admin pode ser removido."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_local_secret_parser_removal_queries.get_review()
        status = str(result["status"]).upper()
        totals = result["sweep"]["totals"]
        self.stdout.write(
            f"[{status}] result={result['result']} allow_local_plain={result['allow_local_plain']} "
            f"tenants={result['sweep']['tenant_count']} local_plain={totals['local_plain_count']} "
            f"external_reference={totals['external_reference_count']} missing={totals['missing_count']}"
        )
        for decision in result["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for surface in result["parser_surfaces"]:
            self.stdout.write(f"parser_surface={surface}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for step in result["removal_plan"]:
            self.stdout.write(f"removal_plan={step}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
