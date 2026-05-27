from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_local_secret_retirement_execution_queries import owner_mfa_local_secret_retirement_execution_queries


class Command(BaseCommand):
    help = "Captura evidência before/after para ativar aposentadoria do fallback local/plain TOTP MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--phase", dest="phase", choices=("before", "after"), default="before")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_local_secret_retirement_execution_queries.get_evidence(
            tenant_id=options["tenant_id"],
            phase=options["phase"],
        )
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(
            f"[{status}] result={result['result']} phase={result['phase']} retirement={result['retirement_result']} "
            f"current={result['setting_current']} expected={result['setting_expected']}"
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
        for evidence in result["evidence"]:
            self.stdout.write(f"evidence={evidence}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        for track in result["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
