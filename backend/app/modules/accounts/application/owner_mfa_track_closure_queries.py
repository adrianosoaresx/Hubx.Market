from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.owner_mfa_audit_evidence_export_closure_queries import (
    owner_mfa_audit_evidence_export_closure_queries,
)


@dataclass(frozen=True)
class OwnerMfaTrackClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaTrackClosureQueryService:
    def get_closure(
        self,
        *,
        tenant_id: int | str | None,
        since: object = "",
        until: object = "",
        limit: int = 500,
        output_format: str = "jsonl",
        expected_actions_confirmed: bool = False,
        export_scope_documented: bool = False,
        redaction_reviewed: bool = False,
        recipient_approved: bool = False,
        artifact_delivered: bool = False,
        retention_owner_confirmed: bool = False,
        storage_decision_recorded: bool = False,
        audit_residual_risks_accepted: bool = False,
        mfa_track_decision_recorded: bool = False,
        rollout_state_documented: bool = False,
        support_handoff_completed: bool = False,
        next_roi_decision_recorded: bool = False,
        track_residual_risks_accepted: bool = False,
    ) -> dict[str, object]:
        audit_closure = owner_mfa_audit_evidence_export_closure_queries.get_closure(
            tenant_id=tenant_id,
            since=since,
            until=until,
            limit=limit,
            output_format=output_format,
            expected_actions_confirmed=expected_actions_confirmed,
            export_scope_documented=export_scope_documented,
            redaction_reviewed=redaction_reviewed,
            recipient_approved=recipient_approved,
            artifact_delivered=artifact_delivered,
            retention_owner_confirmed=retention_owner_confirmed,
            storage_decision_recorded=storage_decision_recorded,
            residual_risks_accepted=audit_residual_risks_accepted,
        )
        closure_signals = {
            "mfa_track_decision_recorded": bool(mfa_track_decision_recorded),
            "rollout_state_documented": bool(rollout_state_documented),
            "support_handoff_completed": bool(support_handoff_completed),
            "next_roi_decision_recorded": bool(next_roi_decision_recorded),
            "track_residual_risks_accepted": bool(track_residual_risks_accepted),
        }
        blockers = self._blockers(audit_closure=audit_closure, closure_signals=closure_signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"owner-mfa-track-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "audit_closure": self._audit_summary(audit_closure=audit_closure),
            "closure_signals": closure_signals,
            "decisions": self._decisions(audit_closure=audit_closure, closure_signals=closure_signals, status=status),
            "blockers": blockers,
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _audit_summary(self, *, audit_closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": audit_closure["result"],
            "ready": bool(audit_closure["ready"]),
            "export_count": audit_closure["export_count"],
            "mfa_actions": audit_closure["mfa_actions"],
        }

    def _blockers(
        self,
        *,
        audit_closure: dict[str, object],
        closure_signals: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not audit_closure["ready"]:
            blockers.append(f"audit:{audit_closure['result']}")
            blockers.extend(f"audit:{blocker}" for blocker in audit_closure["blockers"])
        if not closure_signals["mfa_track_decision_recorded"]:
            blockers.append("track:mfa-track-decision-not-recorded")
        if not closure_signals["rollout_state_documented"]:
            blockers.append("track:rollout-state-not-documented")
        if not closure_signals["support_handoff_completed"]:
            blockers.append("track:support-handoff-not-completed")
        if not closure_signals["next_roi_decision_recorded"]:
            blockers.append("track:next-roi-decision-not-recorded")
        if not closure_signals["track_residual_risks_accepted"]:
            blockers.append("track:residual-risks-not-accepted")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        audit_closure: dict[str, object],
        closure_signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaTrackClosureDecision, ...]:
        return (
            OwnerMfaTrackClosureDecision(
                key="audit-evidence",
                status="ready" if audit_closure["ready"] else "blocked",
                summary="trilha MFA só fecha quando evidência auditável MFA está encerrada",
            ),
            OwnerMfaTrackClosureDecision(
                key="rollout-state",
                status="ready" if closure_signals["rollout_state_documented"] else "blocked",
                summary="estado final de rollout/enforcement/rollback precisa estar documentado",
            ),
            OwnerMfaTrackClosureDecision(
                key="support-handoff",
                status="ready" if closure_signals["support_handoff_completed"] else "blocked",
                summary="suporte precisa saber como operar recovery, bypass e incidentes MFA",
            ),
            OwnerMfaTrackClosureDecision(
                key="next-roi",
                status="ready" if closure_signals["next_roi_decision_recorded"] else "blocked",
                summary="próximo ROI precisa estar decidido antes de iniciar nova trilha",
            ),
            OwnerMfaTrackClosureDecision(
                key="classification",
                status=status,
                summary="classificação final fecha ou bloqueia a abordagem MFA atual",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "MFA owner/admin ainda depende de operação correta de recovery e suporte",
            "novos tenants ainda precisam seguir evidence própria antes de rollout completo",
            "storage/assinatura de evidência auditável permanece trilha opcional futura",
            "mudanças em providers externos devem voltar ao ciclo review/evidence/monitoring",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Security ROI Re-Selection Review",
                "Owner MFA Audit Evidence Storage/Signature Review",
                "Owner MFA Hashicorp Vault Next Tenant Expansion Review",
            )
        return (
            "Owner MFA Audit Evidence Export Closure Review",
            "Owner MFA Track Closure Review",
        )


owner_mfa_track_closure_queries = OwnerMfaTrackClosureQueryService()
