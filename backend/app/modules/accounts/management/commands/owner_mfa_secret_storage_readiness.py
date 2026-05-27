from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_secret_storage_readiness_queries import owner_mfa_secret_storage_readiness_queries


class Command(BaseCommand):
    help = "Avalia storage de segredos TOTP MFA owner/admin sem migrar segredo."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=options["tenant_id"])
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(
            f"[{status}] result={result['result']} allow_local_plain={result.get('allow_local_plain')}"
        )
        self.stdout.write(
            "counts "
            f"local_plain={result.get('local_plain_count', 0)} "
            f"external_reference={result.get('external_reference_count', 0)} "
            f"missing={result.get('missing_count', 0)}"
        )
        for item in result["items"]:
            self.stdout.write(
                f"factor id={item.factor_id} owner={item.owner_email} storage={item.storage_mode} ready={item.ready} result={item.result}"
            )
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
