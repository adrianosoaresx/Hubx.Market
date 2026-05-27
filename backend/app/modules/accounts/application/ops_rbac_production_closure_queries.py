from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.ops_rbac_post_production_monitoring_queries import (
    ops_rbac_post_production_monitoring_queries,
)
from app.modules.accounts.application.ops_rbac_production_activation_evidence_queries import (
    ops_rbac_production_activation_evidence_queries,
)


@dataclass(frozen=True)
class OpsRbacProductionClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OpsRbacProductionClosureQueryService:
    def get_closure(
        self,
        *,
        tenant_id: int | str | None = None,
        expected_gate_state: str = "enabled",
        window_minutes: int = 30,
        require_email_delivery: bool = True,
        block_on_notification_failures: bool = True,
    ) -> dict[str, object]:
        activation = ops_rbac_production_activation_evidence_queries.get_evidence(
            tenant_id=tenant_id,
            expected_gate_state=expected_gate_state,
            environment_label="production",
            require_email_delivery=require_email_delivery,
            block_on_notification_failures=block_on_notification_failures,
        )
        monitoring = ops_rbac_post_production_monitoring_queries.get_snapshot(
            tenant_id=tenant_id,
            window_minutes=window_minutes,
        )
        decisions = self._decisions(activation=activation, monitoring=monitoring)
        blockers: list[str] = []
        if not activation["ready"]:
            blockers.extend(f"activation:{blocker}" for blocker in activation["blockers"])
        if monitoring["status"] == "rollback":
            blockers.extend(f"monitoring:{signal.key}" for signal in monitoring["rollback_signals"])

        status = "ready"
        if monitoring["status"] == "watch":
            status = "watch"
        if blockers:
            status = "blocked"

        return {
            "result": f"ops-rbac-production-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "expected_gate_state": expected_gate_state,
            "window_minutes": monitoring["window_minutes"],
            "activation": activation,
            "monitoring": monitoring,
            "decisions": decisions,
            "blockers": tuple(blockers),
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(),
        }

    def _decisions(
        self,
        *,
        activation: dict[str, object],
        monitoring: dict[str, object],
    ) -> tuple[OpsRbacProductionClosureDecision, ...]:
        return (
            OpsRbacProductionClosureDecision(
                key="activation-evidence",
                status="ready" if activation["ready"] else "blocked",
                summary="readiness, rollout, RBAC matrix e rollback estão cobertos por evidência agregada",
            ),
            OpsRbacProductionClosureDecision(
                key="post-production-monitoring",
                status=str(monitoring["status"]),
                summary="sinais recentes classificam operação como healthy, watch ou rollback",
            ),
            OpsRbacProductionClosureDecision(
                key="automatic-rollback",
                status="out-of-scope",
                summary="rollback permanece decisão operacional explícita, não automação do command",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "execução real ainda depende de janela operacional e operadores com acesso ao ambiente",
            "roles continuam em matriz de código, não em permission model editável",
            "MFA/SSO owner/admin permanece fora deste recorte",
            "dashboards Grafana dedicados podem evoluir depois sobre métricas já expostas",
        )

    def _next_tracks(self) -> tuple[str, ...]:
        return (
            "Platform Owner MFA/SSO Review",
            "Platform Admin Permission Matrix Persistence Review",
            "Platform Audit Evidence Export Review",
        )


ops_rbac_production_closure_queries = OpsRbacProductionClosureQueryService()
