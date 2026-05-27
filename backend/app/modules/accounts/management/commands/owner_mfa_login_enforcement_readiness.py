from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_login_enforcement_readiness_queries import owner_mfa_login_enforcement_readiness_queries


class Command(BaseCommand):
    help = "Avalia readiness para enforcement MFA no login owner/admin sem ativar enforcement."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_login_enforcement_readiness_queries.get_readiness(tenant_id=options["tenant_id"])
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(f"[{status}] result={result['result']} mfa_required={result['mfa_required']}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for check in result["manual_checks"]:
            self.stdout.write(f"manual_check={check}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
