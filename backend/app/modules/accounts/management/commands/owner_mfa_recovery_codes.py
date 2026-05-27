from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_recovery_code_commands import owner_mfa_recovery_code_commands


class Command(BaseCommand):
    help = "Gera recovery codes MFA owner/admin com armazenamento apenas em hash."

    def add_arguments(self, parser):
        parser.add_argument("operation", choices=["generate"])
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--owner-id", dest="owner_id", required=True)
        parser.add_argument("--count", dest="count", type=int, default=8)
        parser.add_argument("--actor-label", dest="actor_label", default="")
        parser.add_argument("--actor-role", dest="actor_role", default="owner")
        parser.add_argument("--fail-on-errors", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=options["tenant_id"],
            owner_id=options["owner_id"],
            count=options["count"],
            actor_label=options["actor_label"],
            actor_role=options["actor_role"],
        )
        status = "OK" if "errors" not in result else "ERROR"
        self.stdout.write(self.style.SUCCESS(f"[{status}] result={result['result']} count={result.get('count', 0)}"))
        for code in result.get("codes", ()):
            self.stdout.write(f"recovery_code={code}")
        if options.get("fail_on_errors") and "errors" in result:
            raise CommandError(result["errors"])
