from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_enrollment_queries import owner_mfa_enrollment_queries


class Command(BaseCommand):
    help = "Lista readiness de enrollment MFA dos owners/admins de um tenant."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Tenant alvo.")
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando houver owners sem MFA verificado.")

    def handle(self, *args, **options):
        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=str(options.get("tenant_id") or "").strip())
        status = "READY" if result["ready"] else "BLOCKED"
        blockers = ",".join(result["blockers"]) if result["blockers"] else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] owners={result.get('owner_count', 0)} enrolled={result.get('enrolled_owner_count', 0)} blockers={blockers}"
            )
        )
        for owner in result["owners"]:
            self.stdout.write(
                f"owner_id={owner.owner_id} email={owner.email} role={owner.role} enrolled={str(owner.enrolled).lower()} "
                f"active_factors={owner.active_factor_count} verified_factors={owner.verified_factor_count}"
            )
        if options.get("fail_on_blockers") and not result["ready"]:
            raise CommandError("Owner MFA enrollment readiness blocked.")
