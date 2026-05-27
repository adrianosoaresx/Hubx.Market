from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_provider_health_queries import owner_mfa_provider_health_queries


class Command(BaseCommand):
    help = "Monitora saúde do provider externo de segredos TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-critical", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_provider_health_queries.get_health(tenant_id=options["tenant_id"])
        self.stdout.write(
            f"[{result['status']}] result={result['result']} provider={result['provider']} storage={result['storage_result']}"
        )
        self.stdout.write(
            "counts "
            f"external_reference={result['external_reference_count']} "
            f"external_unresolved={result['external_reference_unresolved_count']} "
            f"local_plain={result['local_plain_count']} "
            f"missing={result['missing_count']}"
        )
        for item in result["items"]:
            self.stdout.write(
                f"factor id={item.factor_id} owner={item.owner_email} storage={item.storage_mode} ready={item.ready} result={item.result}"
            )
        for signal in result["signals"]:
            self.stdout.write(f"signal={signal}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for step in result["runbook"]:
            self.stdout.write(f"runbook={step}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_critical"] and result["status"] == "CRITICAL":
            raise CommandError(result["blockers"] or result["signals"])
