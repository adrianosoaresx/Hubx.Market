from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_local_secret_retirement_queries import owner_mfa_local_secret_retirement_queries


class Command(BaseCommand):
    help = "Avalia se o fallback local/plain de TOTP MFA owner/admin pode ser aposentado."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_local_secret_retirement_queries.get_readiness(tenant_id=options["tenant_id"])
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(
            f"[{status}] result={result['result']} storage={result['storage_result']} "
            f"target={result['setting_target']}"
        )
        self.stdout.write(
            "counts "
            f"local_plain={result['local_plain_count']} "
            f"external_reference={result['external_reference_count']} "
            f"missing={result['missing_count']}"
        )
        for item in result["items"]:
            self.stdout.write(
                f"factor id={item.factor_id} owner={item.owner_email} storage={item.storage_mode} ready={item.ready} result={item.result}"
            )
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for step in result["runbook"]:
            self.stdout.write(f"runbook={step}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
