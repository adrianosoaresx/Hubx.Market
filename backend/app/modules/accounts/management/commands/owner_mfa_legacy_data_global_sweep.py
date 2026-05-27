from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_legacy_data_global_sweep_queries import owner_mfa_legacy_data_global_sweep_queries


class Command(BaseCommand):
    help = "Varre globalmente fatores TOTP MFA owner/admin ainda dependentes de dados locais/legados."

    def add_arguments(self, parser):
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_legacy_data_global_sweep_queries.get_sweep()
        status = str(result["status"]).upper()
        totals = result["totals"]
        self.stdout.write(
            f"[{status}] result={result['result']} tenants={result['tenant_count']} "
            f"local_plain={totals['local_plain_count']} external_reference={totals['external_reference_count']} "
            f"missing={totals['missing_count']} blocked_tenants={totals['blocked_tenant_count']}"
        )
        for summary in result["tenant_summaries"]:
            self.stdout.write(
                f"tenant id={summary.tenant_id} status={summary.status} local_plain={summary.local_plain_count} "
                f"external_reference={summary.external_reference_count} missing={summary.missing_count}"
            )
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for risk in result["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
