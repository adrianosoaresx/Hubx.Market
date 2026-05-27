from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_rbac_staging_evidence_queries import ops_rbac_staging_evidence_queries


class Command(BaseCommand):
    help = "Captura pacote de evidência para ativação staging do RBAC granular em /ops/."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", default="", help="Limita a evidência a um tenant específico.")
        parser.add_argument(
            "--expect-gate",
            dest="expect_gate",
            default="enabled",
            choices=["any", "enabled", "disabled"],
            help="Estado esperado de HUBX_OPS_AUTH_GATE_ENFORCED para a captura.",
        )
        parser.add_argument(
            "--environment",
            dest="environment",
            default="staging",
            help="Rótulo do ambiente anexado ao pacote de evidência.",
        )
        parser.add_argument(
            "--require-email-delivery",
            action="store_true",
            help="Exige provider de e-mail pronto para entrega real.",
        )
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando houver blockers.")

    def handle(self, *args, **options):
        tenant_id = str(options.get("tenant_id") or "").strip()
        expect_gate = str(options.get("expect_gate") or "enabled")
        evidence = ops_rbac_staging_evidence_queries.get_evidence(
            tenant_id=tenant_id,
            expected_gate_state=expect_gate,
            environment_label=str(options.get("environment") or "staging"),
            require_email_delivery=bool(options.get("require_email_delivery")),
        )
        status = "READY" if evidence["ready"] else "BLOCKED"
        blocker_label = ",".join(evidence["blockers"]) if evidence["blockers"] else "none"
        preflight = evidence["preflight"]
        rbac = evidence["rbac"]

        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] environment={evidence['environment_label']} "
                f"expected_gate={evidence['expected_gate_state']} "
                f"gate_enabled={str(rbac['gate_enabled']).lower()} "
                f"tenants={rbac['tenant_count']} blocked_tenants={rbac['blocked_tenant_count']} "
                f"blockers={blocker_label}"
            )
        )
        self.stdout.write(f"command.preflight={self._preflight_command(tenant_id, expect_gate, options)}")
        self.stdout.write(f"command.rbac={self._rbac_command(tenant_id, expect_gate)}")
        self.stdout.write(
            f"result.preflight={preflight['result']} ready={str(preflight['ready']).lower()} "
            f"blockers={','.join(preflight['blockers']) if preflight['blockers'] else 'none'}"
        )
        self.stdout.write(
            f"result.rbac={rbac['result']} ready={str(rbac['ready']).lower()} "
            f"blockers={','.join(rbac['blockers']) if rbac['blockers'] else 'none'}"
        )
        for step in evidence["manual_checks"]:
            self.stdout.write(f"manual_check.{step.key}=action:{step.action}; expected:{step.expected}")
        for index, step in enumerate(evidence["rollback_steps"], start=1):
            self.stdout.write(f"rollback.{index}={step}")

        if options.get("fail_on_blockers") and not evidence["ready"]:
            raise CommandError("Ops RBAC staging activation evidence blocked.")

    def _preflight_command(self, tenant_id: str, expect_gate: str, options: dict[str, object]) -> str:
        parts = ["python manage.py ops_gate_activation_preflight"]
        if tenant_id:
            parts.append(f"--tenant-id={tenant_id}")
        parts.append(f"--expect-gate={expect_gate}")
        if options.get("require_email_delivery"):
            parts.append("--require-email-delivery")
        parts.append("--fail-on-blockers")
        return " ".join(parts)

    def _rbac_command(self, tenant_id: str, expect_gate: str) -> str:
        parts = ["python manage.py ops_rbac_production_readiness"]
        if tenant_id:
            parts.append(f"--tenant-id={tenant_id}")
        parts.append(f"--expect-gate={expect_gate}")
        parts.append("--fail-on-blockers")
        return " ".join(parts)
