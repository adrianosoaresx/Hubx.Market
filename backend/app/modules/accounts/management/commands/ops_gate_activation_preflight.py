from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_gate_activation_preflight_queries import ops_gate_activation_preflight_queries


class Command(BaseCommand):
    help = "Executa preflight para ativação controlada do gate /ops/ em staging/produção."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Limita o preflight a um tenant específico.")
        parser.add_argument(
            "--expect-gate",
            dest="expect_gate",
            default="any",
            choices=["any", "enabled", "disabled"],
            help="Valida o estado esperado de HUBX_OPS_AUTH_GATE_ENFORCED.",
        )
        parser.add_argument(
            "--require-email-delivery",
            action="store_true",
            help="Exige provider de e-mail pronto para entrega real.",
        )
        parser.add_argument(
            "--fail-on-blockers",
            action="store_true",
            help="Retorna erro quando o preflight encontrar blockers.",
        )

    def handle(self, *args, **options):
        result = ops_gate_activation_preflight_queries.get_preflight(
            tenant_id=str(options.get("tenant_id") or "").strip(),
            expected_gate_state=str(options.get("expect_gate") or "any"),
            require_email_delivery=bool(options.get("require_email_delivery")),
        )
        status = "READY" if result["ready"] else "BLOCKED"
        provider = result["notification_provider"]
        readiness = result["readiness"]
        blocker_label = ",".join(result["blockers"]) if result["blockers"] else "none"
        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] gate_enabled={str(result['gate_enabled']).lower()} "
                f"expected_gate={result['expected_gate_state']} blockers={blocker_label} "
                f"tenants={readiness['tenant_count']} blocked_tenants={readiness['blocked_tenant_count']} "
                f"email_dry_run={str(provider.dry_run).lower()} email_can_deliver={str(provider.can_attempt_real_delivery).lower()}"
            )
        )

        for tenant in readiness["tenants"]:
            tenant_blockers = ",".join(tenant.blockers) if tenant.blockers else "none"
            self.stdout.write(
                f"tenant_id={tenant.tenant_id} slug={tenant.tenant_slug} ready={str(tenant.ready).lower()} "
                f"active_owners={tenant.active_owners} owners_with_user={tenant.owners_with_user} blockers={tenant_blockers}"
            )

        if provider.blockers:
            self.stdout.write(f"notification_provider_blockers={','.join(provider.blockers)}")

        if options.get("fail_on_blockers") and not result["ready"]:
            raise CommandError("Ops gate activation preflight blocked.")
