from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.ops_gate_production_rollout_queries import ops_gate_production_rollout_queries
from app.modules.accounts.application.ops_rbac_production_readiness_queries import ops_rbac_production_readiness_queries


@dataclass(frozen=True)
class OpsRbacProductionManualEvidenceStep:
    key: str
    action: str
    expected: str


@dataclass
class OpsRbacProductionActivationEvidenceQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None = None,
        expected_gate_state: str = "enabled",
        environment_label: str = "production",
        require_email_delivery: bool = True,
        block_on_notification_failures: bool = True,
        block_on_pending_delivery: bool = False,
    ) -> dict[str, object]:
        rollout = ops_gate_production_rollout_queries.get_rollout_evidence(
            tenant_id=tenant_id,
            expected_gate_state=expected_gate_state,
            require_email_delivery=require_email_delivery,
            block_on_notification_failures=block_on_notification_failures,
            block_on_pending_delivery=block_on_pending_delivery,
        )
        rbac = ops_rbac_production_readiness_queries.get_readiness(
            tenant_id=tenant_id,
            expected_gate_state=expected_gate_state,
        )
        blockers: list[str] = []
        if not rollout["ready"]:
            blockers.extend(f"rollout:{blocker}" for blocker in rollout["blockers"])
        if not rbac["ready"]:
            blockers.extend(f"rbac:{blocker}" for blocker in rbac["blockers"])

        return {
            "result": "ops-rbac-production-activation-ready" if not blockers else "ops-rbac-production-activation-blocked",
            "ready": not blockers,
            "blockers": tuple(blockers),
            "environment_label": str(environment_label or "production").strip() or "production",
            "expected_gate_state": expected_gate_state,
            "tenant_id": str(tenant_id or "").strip(),
            "rollout": rollout,
            "rbac": rbac,
            "manual_checks": self._manual_checks(),
            "rollback_steps": self._rollback_steps(),
        }

    def _manual_checks(self) -> tuple[OpsRbacProductionManualEvidenceStep, ...]:
        return (
            OpsRbacProductionManualEvidenceStep(
                key="owner-dashboard",
                action="login como owner/admin real no subdomínio do tenant e abrir /ops/",
                expected="HTTP 200 e cockpit carregado sem erro",
            ),
            OpsRbacProductionManualEvidenceStep(
                key="permitted-route",
                action="abrir uma rota /ops/ permitida pela role validada",
                expected="HTTP 200 e nenhuma negação nova para a rota",
            ),
            OpsRbacProductionManualEvidenceStep(
                key="forbidden-route",
                action="abrir uma rota /ops/ proibida para role limitada",
                expected="HTTP 403 e AuditLog owner.ops_permission_denied",
            ),
            OpsRbacProductionManualEvidenceStep(
                key="owner-access-metrics",
                action="consultar métricas owner access após o teste proibido",
                expected="contador owner.ops_permission_denied visível para o tenant",
            ),
        )

    def _rollback_steps(self) -> tuple[str, ...]:
        return (
            "setar HUBX_OPS_AUTH_GATE_ENFORCED=0",
            "redeploy/restart dos processos web de produção",
            "rodar ops_rbac_production_activation_evidence --expect-gate=disabled",
            "confirmar /ops/ acessível para owner/admin real",
            "registrar rollback e blockers no change log",
        )


ops_rbac_production_activation_evidence_queries = OpsRbacProductionActivationEvidenceQueryService()
