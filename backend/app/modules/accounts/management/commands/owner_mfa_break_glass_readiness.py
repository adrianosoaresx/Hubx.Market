from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_break_glass_readiness_queries import owner_mfa_break_glass_readiness_queries


class Command(BaseCommand):
    help = "Avalia readiness de break-glass MFA owner/admin sem alterar login."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_break_glass_readiness_queries.get_readiness(tenant_id=options["tenant_id"])
        status = "READY" if result["ready"] else "BLOCKED"
        self.stdout.write(f"[{status}] result={result['result']} enabled={result['enabled']}")
        for email in result["configured_emails"]:
            self.stdout.write(f"configured_email={email}")
        for account in result["accounts"]:
            self.stdout.write(f"active_account={account}")
        for blocker in result["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        if options["fail_on_blockers"] and result["blockers"]:
            raise CommandError(result["blockers"])
