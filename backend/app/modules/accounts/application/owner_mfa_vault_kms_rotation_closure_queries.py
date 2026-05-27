from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_vault_kms_post_rotation_monitoring_queries import (
    owner_mfa_vault_kms_post_rotation_monitoring_queries,
)


@dataclass(frozen=True)
class OwnerMfaVaultKmsRotationClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaVaultKmsRotationClosureQueryService:
    def get_closure(
        self,
        *,
        rotation_closure_decision_recorded: bool = False,
        rotation_evidence_archived: bool = False,
        closure_residual_risks_accepted: bool = False,
        expansion_resume_plan_documented: bool = False,
        rollback_window_closed_or_extended: bool = False,
        closure_audit_evidence_ready: bool = False,
        **monitoring_kwargs,
    ) -> dict[str, object]:
        monitoring = owner_mfa_vault_kms_post_rotation_monitoring_queries.get_review(**monitoring_kwargs)
        closure_signals = {
            "rotation_closure_decision_recorded": bool(rotation_closure_decision_recorded),
            "rotation_evidence_archived": bool(rotation_evidence_archived),
            "closure_residual_risks_accepted": bool(closure_residual_risks_accepted),
            "expansion_resume_plan_documented": bool(expansion_resume_plan_documented),
            "rollback_window_closed_or_extended": bool(rollback_window_closed_or_extended),
            "closure_audit_evidence_ready": bool(closure_audit_evidence_ready),
        }
        blockers = self._blockers(monitoring=monitoring, closure_signals=closure_signals)
        status = self._status(monitoring=monitoring, blockers=blockers)
        return {
            "result": f"owner-mfa-vault-kms-rotation-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "canary_tenant_id": monitoring["canary_tenant_id"],
            "current_target_tenant_id": monitoring["current_target_tenant_id"],
            "target_provider": "hashicorp-vault",
            "monitoring": monitoring,
            "closure_signals": closure_signals,
            "decisions": self._decisions(monitoring=monitoring, closure_signals=closure_signals, status=status),
            "blockers": blockers,
            "residual_risks": self._residual_risks(),
            "resume_guardrails": self._resume_guardrails(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _status(self, *, monitoring: dict[str, object], blockers: tuple[str, ...]) -> str:
        if monitoring["status"] == "rollback":
            return "rollback"
        if monitoring["status"] == "watch":
            return "watch"
        if blockers:
            return "blocked"
        if monitoring["status"] == "healthy":
            return "ready"
        return "blocked"

    def _blockers(
        self,
        *,
        monitoring: dict[str, object],
        closure_signals: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if monitoring["status"] == "rollback":
            blockers.append("monitoring:rollback-signal-present")
        elif monitoring["status"] != "healthy":
            blockers.append(f"monitoring:{monitoring['status']}")
        for blocker in monitoring["blockers"]:
            blockers.append(f"monitoring:{blocker}")
        if not closure_signals["rotation_closure_decision_recorded"]:
            blockers.append("closure:rotation-closure-decision-not-recorded")
        if not closure_signals["rotation_evidence_archived"]:
            blockers.append("closure:rotation-evidence-not-archived")
        if not closure_signals["closure_residual_risks_accepted"]:
            blockers.append("closure:residual-risks-not-accepted")
        if not closure_signals["expansion_resume_plan_documented"]:
            blockers.append("closure:expansion-resume-plan-not-documented")
        if not closure_signals["rollback_window_closed_or_extended"]:
            blockers.append("closure:rollback-window-not-closed-or-extended")
        if not closure_signals["closure_audit_evidence_ready"]:
            blockers.append("closure:audit-evidence-not-ready")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        monitoring: dict[str, object],
        closure_signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaVaultKmsRotationClosureDecision, ...]:
        return (
            OwnerMfaVaultKmsRotationClosureDecision(
                key="post-rotation-monitoring",
                status=str(monitoring["status"]),
                summary="closure só pode fechar quando o monitoramento pós-rotação estiver healthy",
            ),
            OwnerMfaVaultKmsRotationClosureDecision(
                key="evidence-archive",
                status="ready" if closure_signals["rotation_evidence_archived"] else "blocked",
                summary="evidência de rotação e monitoramento precisa estar arquivada antes do encerramento",
            ),
            OwnerMfaVaultKmsRotationClosureDecision(
                key="residual-risks",
                status="accepted" if closure_signals["closure_residual_risks_accepted"] else "blocked",
                summary="riscos residuais precisam ser aceitos explicitamente",
            ),
            OwnerMfaVaultKmsRotationClosureDecision(
                key="expansion-resume",
                status="ready" if closure_signals["expansion_resume_plan_documented"] else "blocked",
                summary="retomada de expansão precisa de plano documentado; closure não expande tenants",
            ),
            OwnerMfaVaultKmsRotationClosureDecision(
                key="classification",
                status=status,
                summary="classificação final decide se a rotação pode ser encerrada",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "Hashicorp Vault continua sendo dependência crítica para MFA owner/admin",
            "rollback operacional permanece externo ao command",
            "expansão pós-rotação ainda exige evidence própria por target tenant",
            "auditoria formal pode exigir export posterior em trilha dedicada",
        )

    def _resume_guardrails(self) -> tuple[str, ...]:
        return (
            "não retomar expansão sem closure READY",
            "executar próximo tenant por review/evidence/monitoring próprios",
            "não reutilizar evidence de rotação como evidência de expansão",
            "manter rollback window coerente com a próxima janela operacional",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Audit Evidence Export Review",
                "Owner MFA Hashicorp Vault Next Tenant Expansion Review",
            )
        if status == "rollback":
            return (
                "Owner MFA Vault/KMS Rotation Rollback Evidence",
                "Owner MFA Vault/KMS Rotation Runbook Review",
            )
        return (
            "Owner MFA Vault/KMS Extended Post-Rotation Monitoring Evidence",
            "Owner MFA Vault/KMS Rotation Closure Review",
        )


owner_mfa_vault_kms_rotation_closure_queries = OwnerMfaVaultKmsRotationClosureQueryService()
