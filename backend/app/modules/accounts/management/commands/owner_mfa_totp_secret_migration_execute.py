from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_totp_secret_migration_commands import owner_mfa_totp_secret_migration_commands


class Command(BaseCommand):
    help = "Executa migração controlada de segredo TOTP MFA owner/admin de local/plain para ref:<path>."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--factor-id", dest="factor_id", required=True)
        parser.add_argument("--reference-prefix", dest="reference_prefix", default="owners")
        parser.add_argument("--actor-label", dest="actor_label", default="system")
        parser.add_argument("--actor-role", dest="actor_role", default="owner")
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_totp_secret_migration_commands.migrate_factor(
            tenant_id=options["tenant_id"],
            factor_id=options["factor_id"],
            reference_prefix=options["reference_prefix"],
            dry_run=not options["execute"],
            actor_label=options["actor_label"],
            actor_role=options["actor_role"],
        )
        status = "OK" if not result.errors else "BLOCKED"
        mode = "DRY-RUN" if result.dry_run else "EXECUTE"
        self.stdout.write(
            f"[{status}] mode={mode} result={result.result} factor={result.factor_id or ''} "
            f"owner={result.owner_email} storage={result.current_storage_mode} target_ref={result.target_reference}"
        )
        for field, message in result.errors.items():
            self.stdout.write(f"error={field}:{message}")
        if options["fail_on_errors"] and result.errors:
            raise CommandError(result.errors)
