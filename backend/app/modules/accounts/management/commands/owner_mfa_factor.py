from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_challenge_commands import owner_mfa_challenge_commands
from app.modules.accounts.application.owner_mfa_enrollment_commands import owner_mfa_enrollment_commands


class Command(BaseCommand):
    help = "Registra, verifica ou desativa fator MFA owner/admin de forma auditável."

    def add_arguments(self, parser):
        parser.add_argument("operation", choices=["register", "verify", "deactivate"])
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--owner-id", dest="owner_id", default="")
        parser.add_argument("--factor-id", dest="factor_id", default="")
        parser.add_argument("--factor-type", dest="factor_type", default="totp")
        parser.add_argument("--provider-key", dest="provider_key", default="internal")
        parser.add_argument("--label", dest="label", default="")
        parser.add_argument("--secret-reference", dest="secret_reference", default="")
        parser.add_argument("--challenge", dest="challenge", default="")
        parser.add_argument("--actor-label", dest="actor_label", default="")
        parser.add_argument("--actor-role", dest="actor_role", default="owner")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        if options["operation"] == "register":
            result = owner_mfa_enrollment_commands.register_factor(
                tenant_id=options["tenant_id"],
                owner_id=options["owner_id"],
                factor_type=options["factor_type"],
                provider_key=options["provider_key"],
                label=options["label"],
                secret_reference=options["secret_reference"],
                actor_label=options["actor_label"],
                actor_role=options["actor_role"],
            )
        elif options["operation"] == "deactivate":
            result = owner_mfa_enrollment_commands.deactivate_factor(
                tenant_id=options["tenant_id"],
                factor_id=options["factor_id"],
                actor_label=options["actor_label"],
                actor_role=options["actor_role"],
            )
        else:
            result = owner_mfa_challenge_commands.verify_factor(
                tenant_id=options["tenant_id"],
                factor_id=options["factor_id"],
                challenge=options["challenge"],
                actor_label=options["actor_label"],
                actor_role=options["actor_role"],
            )
        status = "OK" if "errors" not in result else "ERROR"
        self.stdout.write(self.style.SUCCESS(f"[{status}] result={result['result']}"))
        if options.get("fail_on_errors") and "errors" in result:
            raise CommandError(result["errors"])
