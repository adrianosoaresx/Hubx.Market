from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.ops_rbac_production_activation_evidence_queries import (
    ops_rbac_production_activation_evidence_queries,
)


class Command(BaseCommand):
    help = "Captura pacote de evidência para ativação production do RBAC granular em /ops/."

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
            default="production",
            help="Rótulo do ambiente anexado ao pacote de evidência.",
        )
        parser.add_argument(
            "--allow-email-dry-run",
            action="store_true",
            help="Não exige provider de e-mail pronto para entrega real.",
        )
        parser.add_argument(
            "--allow-notification-failures",
            action="store_true",
            help="Não bloqueia quando há EmailLog failed no tenant.",
        )
        parser.add_argument(
            "--block-on-pending-delivery",
            action="store_true",
            help="Bloqueia quando há EmailLog planned/requested no tenant.",
        )
        parser.add_argument("--fail-on-blockers", action="store_true", help="Retorna erro quando houver blockers.")

    def handle(self, *args, **options):
        tenant_id = str(options.get("tenant_id") or "").strip()
        expect_gate = str(options.get("expect_gate") or "enabled")
        evidence = ops_rbac_production_activation_evidence_queries.get_evidence(
            tenant_id=tenant_id,
            expected_gate_state=expect_gate,
            environment_label=str(options.get("environment") or "production"),
            require_email_delivery=not bool(options.get("allow_email_dry_run")),
            block_on_notification_failures=not bool(options.get("allow_notification_failures")),
            block_on_pending_delivery=bool(options.get("block_on_pending_delivery")),
        )
        status = "READY" if evidence["ready"] else "BLOCKED"
        blocker_label = ",".join(evidence["blockers"]) if evidence["blockers"] else "none"
        rollout = evidence["rollout"]
        rbac = evidence["rbac"]
        preflight = rollout["preflight"]
        provider = preflight["notification_provider"]

        self.stdout.write(
            self.style.SUCCESS(
                f"[{status}] environment={evidence['environment_label']} "
                f"expected_gate={evidence['expected_gate_state']} "
                f"gate_enabled={str(rbac['gate_enabled']).lower()} "
                f"tenants={rbac['tenant_count']} blocked_tenants={rbac['blocked_tenant_count']} "
                f"email_dry_run={str(provider.dry_run).lower()} "
                f"email_can_deliver={str(provider.can_attempt_real_delivery).lower()} "
                f"blockers={blocker_label}"
            )
        )
        self.stdout.write(f"command.rollout={self._rollout_command(tenant_id, expect_gate, options)}")
        self.stdout.write(f"command.rbac={self._rbac_command(tenant_id, expect_gate)}")
        self.stdout.write(
            f"result.rollout={rollout['result']} ready={str(rollout['ready']).lower()} "
            f"blockers={','.join(rollout['blockers']) if rollout['blockers'] else 'none'}"
        )
        self.stdout.write(
            f"result.rbac={rbac['result']} ready={str(rbac['ready']).lower()} "
            f"blockers={','.join(rbac['blockers']) if rbac['blockers'] else 'none'}"
        )
        for item in rollout["tenants"]:
            notifications = item["notifications"]
            notification_blockers = ",".join(item["notification_blockers"]) if item["notification_blockers"] else "none"
            self.stdout.write(
                f"tenant_id={item['tenant_id']} slug={item['tenant_slug']} "
                f"notification_blockers={notification_blockers} "
                f"email_total={notifications.total} email_failed={notifications.failed}"
            )
        for step in evidence["manual_checks"]:
            self.stdout.write(f"manual_check.{step.key}=action:{step.action}; expected:{step.expected}")
        for index, step in enumerate(evidence["rollback_steps"], start=1):
            self.stdout.write(f"rollback.{index}={step}")

        if options.get("fail_on_blockers") and not evidence["ready"]:
            raise CommandError("Ops RBAC production activation evidence blocked.")

    def _rollout_command(self, tenant_id: str, expect_gate: str, options: dict[str, object]) -> str:
        parts = ["python manage.py ops_gate_production_rollout"]
        if tenant_id:
            parts.append(f"--tenant-id={tenant_id}")
        parts.append(f"--expect-gate={expect_gate}")
        if options.get("allow_email_dry_run"):
            parts.append("--allow-email-dry-run")
        if options.get("allow_notification_failures"):
            parts.append("--allow-notification-failures")
        if options.get("block_on_pending_delivery"):
            parts.append("--block-on-pending-delivery")
        parts.append("--fail-on-blockers")
        return " ".join(parts)

    def _rbac_command(self, tenant_id: str, expect_gate: str) -> str:
        parts = ["python manage.py ops_rbac_production_readiness"]
        if tenant_id:
            parts.append(f"--tenant-id={tenant_id}")
        parts.append(f"--expect-gate={expect_gate}")
        parts.append("--fail-on-blockers")
        return " ".join(parts)
