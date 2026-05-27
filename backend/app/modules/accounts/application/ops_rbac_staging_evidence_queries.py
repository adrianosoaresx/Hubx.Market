from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.ops_gate_activation_preflight_queries import ops_gate_activation_preflight_queries
from app.modules.accounts.application.ops_rbac_production_readiness_queries import ops_rbac_production_readiness_queries


@dataclass(frozen=True)
class OpsRbacManualEvidenceStep:
    key: str
    action: str
    expected: str


@dataclass
class OpsRbacStagingEvidenceQueryService:
    def get_evidence(
        self,
        *,
        tenant_id: int | str | None = None,
        expected_gate_state: str = "enabled",
        environment_label: str = "staging",
        require_email_delivery: bool = False,
    ) -> dict[str, object]:
        preflight = ops_gate_activation_preflight_queries.get_preflight(
            tenant_id=tenant_id,
            expected_gate_state=expected_gate_state,
            require_email_delivery=require_email_delivery,
        )
        rbac = ops_rbac_production_readiness_queries.get_readiness(
            tenant_id=tenant_id,
            expected_gate_state=expected_gate_state,
        )
        blockers: list[str] = []
        if not preflight["ready"]:
            blockers.extend(f"preflight:{blocker}" for blocker in preflight["blockers"])
        if not rbac["ready"]:
            blockers.extend(f"rbac:{blocker}" for blocker in rbac["blockers"])

        return {
            "result": "ops-rbac-staging-evidence-ready" if not blockers else "ops-rbac-staging-evidence-blocked",
            "ready": not blockers,
            "blockers": tuple(blockers),
            "environment_label": str(environment_label or "staging").strip() or "staging",
            "expected_gate_state": expected_gate_state,
            "tenant_id": str(tenant_id or "").strip(),
            "preflight": preflight,
            "rbac": rbac,
            "manual_checks": self._manual_checks(),
            "rollback_steps": self._rollback_steps(),
        }

    def _manual_checks(self) -> tuple[OpsRbacManualEvidenceStep, ...]:
        return (
            OpsRbacManualEvidenceStep(
                key="owner-dashboard",
                action="login como owner/admin ativo no subdomínio do tenant e abrir /ops/",
                expected="HTTP 200 e cockpit visível",
            ),
            OpsRbacManualEvidenceStep(
                key="permitted-route",
                action="abrir uma rota /ops/ permitida pela role testada",
                expected="HTTP 200 sem evento owner.ops_permission_denied",
            ),
            OpsRbacManualEvidenceStep(
                key="forbidden-route",
                action="abrir /ops/owners/ com role sem owners.manage",
                expected="HTTP 403 e AuditLog owner.ops_permission_denied",
            ),
        )

    def _rollback_steps(self) -> tuple[str, ...]:
        return (
            "setar HUBX_OPS_AUTH_GATE_ENFORCED=0",
            "redeploy/restart dos processos web",
            "rodar ops_rbac_staging_activation_evidence --expect-gate=disabled",
            "confirmar /ops/ acessível para owner/admin ativo",
        )


ops_rbac_staging_evidence_queries = OpsRbacStagingEvidenceQueryService()
