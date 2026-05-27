from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_totp_secret_migration_plan_queries import owner_mfa_totp_secret_migration_plan_queries


class Command(BaseCommand):
    help = "Gera plano seguro para migrar segredos TOTP MFA owner/admin de local/plain para ref:<path>."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--reference-prefix", dest="reference_prefix", default="owners")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_totp_secret_migration_plan_queries.get_plan(
            tenant_id=options["tenant_id"],
            reference_prefix=options["reference_prefix"],
        )
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(
            f"[{status}] result={result['result']} migrate={result.get('migrate_count', 0)} "
            f"external={result.get('already_external_count', 0)} missing={result.get('missing_count', 0)}"
        )
        for candidate in result["candidates"]:
            self.stdout.write(
                "candidate "
                f"factor={candidate.factor_id} owner={candidate.owner_email} "
                f"storage={candidate.current_storage_mode} action={candidate.action} "
                f"target_ref={candidate.target_reference}"
            )
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for step in result["runbook"]:
            self.stdout.write(f"runbook={step}")
        for rollback in result["rollback"]:
            self.stdout.write(f"rollback={rollback}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
