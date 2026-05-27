from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_gate_readiness_queries import ops_gate_readiness_queries


class Command(BaseCommand):
    help = "Valida se tenants ativos têm owners ativos com usuários Django antes de ativar o gate de /ops/."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-id",
            dest="tenant_id",
            default="",
            help="Limita a validação a um tenant específico.",
        )
        parser.add_argument(
            "--fail-on-blockers",
            action="store_true",
            help="Retorna erro quando existir tenant bloqueando a ativação.",
        )

    def handle(self, *args, **options):
        result = ops_gate_readiness_queries.get_readiness(tenant_id=str(options.get("tenant_id") or "").strip())
        ready = bool(result["ready"])
        status = "READY" if ready else "BLOCKED"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] tenants={result['tenant_count']} blocked_tenants={result['blocked_tenant_count']}"
            )
        )

        for tenant in result["tenants"]:
            blocker_label = ",".join(tenant.blockers) if tenant.blockers else "none"
            self.stdout.write(
                f"tenant_id={tenant.tenant_id} slug={tenant.tenant_slug} subdomain={tenant.subdomain} "
                f"ready={str(tenant.ready).lower()} active_owners={tenant.active_owners} "
                f"owners_with_user={tenant.owners_with_user} blockers={blocker_label}"
            )
            self._write_emails("missing_user_emails", tenant.missing_user_emails)
            self._write_emails("inactive_user_emails", tenant.inactive_user_emails)
            self._write_emails("duplicate_user_emails", tenant.duplicate_user_emails)

        if options.get("fail_on_blockers") and not ready:
            raise CommandError("Ops auth gate readiness blocked.")

    def _write_emails(self, label: str, emails: tuple[str, ...]) -> None:
        if emails:
            self.stdout.write(f"  {label}={','.join(emails)}")
