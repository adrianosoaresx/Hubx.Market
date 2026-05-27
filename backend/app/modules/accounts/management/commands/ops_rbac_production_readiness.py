from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_rbac_production_readiness_queries import ops_rbac_production_readiness_queries


class Command(BaseCommand):
    help = "Gera evidência Go/No-Go para ativação de RBAC granular em /ops/."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Limita a evidência a um tenant específico.")
        parser.add_argument(
            "--expect-gate",
            dest="expect_gate",
            default="enabled",
            choices=["any", "enabled", "disabled"],
            help="Estado esperado do gate /ops/ para a evidência.",
        )
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando houver blockers.")

    def handle(self, *args, **options):
        evidence = ops_rbac_production_readiness_queries.get_readiness(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            expected_gate_state=str(options.get("expect_gate") or "enabled"),
        )
        status = "READY" if evidence["ready"] else "BLOCKED"
        blocker_label = ",".join(evidence["blockers"]) if evidence["blockers"] else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] gate_enabled={str(evidence['gate_enabled']).lower()} "
                f"expected_gate={evidence['expected_gate_state']} tenants={evidence['tenant_count']} "
                f"blocked_tenants={evidence['blocked_tenant_count']} blockers={blocker_label}"
            )
        )
        self.stdout.write(f"required_permissions={','.join(evidence['required_permissions'])}")
        for tenant in evidence["tenants"]:
            blocker_label = ",".join(tenant.blockers) if tenant.blockers else "none"
            self.stdout.write(
                f"tenant_id={tenant.tenant_id} slug={tenant.tenant_slug} ready={str(tenant.ready).lower()} "
                f"active_owners={tenant.active_owner_count} full_admin_count={tenant.full_admin_count} "
                f"blockers={blocker_label}"
            )
            self._write_values("unknown_roles", tenant.unknown_roles)
            self._write_values("full_admin_missing_user_emails", tenant.full_admin_missing_user_emails)
            self._write_values("full_admin_inactive_user_emails", tenant.full_admin_inactive_user_emails)
            self._write_values("full_admin_duplicate_user_emails", tenant.full_admin_duplicate_user_emails)

        if options.get("fail_on_blockers") and not evidence["ready"]:
            raise CommandError("Ops RBAC production readiness blocked.")

    def _write_values(self, label: str, values: tuple[str, ...]) -> None:
        if values:
            self.stdout.write(f"  {label}={','.join(values)}")
