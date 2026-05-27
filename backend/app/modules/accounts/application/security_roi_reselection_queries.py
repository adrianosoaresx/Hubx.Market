from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.owner_mfa_track_closure_queries import owner_mfa_track_closure_queries


@dataclass(frozen=True)
class SecurityRoiCandidate:
    key: str
    score: int
    recommended_track: str
    rationale: str


@dataclass(frozen=True)
class SecurityRoiDecision:
    key: str
    status: str
    summary: str


@dataclass
class SecurityRoiReselectionQueryService:
    def get_review(
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
        evidence_storage_signature_required: bool = False,
        next_tenant_expansion_ready: bool = False,
        session_policy_gap_confirmed: bool = False,
        api_key_surface_active: bool = False,
        security_backlog_pause_preferred: bool = False,
    ) -> dict[str, object]:
        mfa_closure = owner_mfa_track_closure_queries.get_closure(
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
            audit_residual_risks_accepted=audit_residual_risks_accepted,
            mfa_track_decision_recorded=mfa_track_decision_recorded,
            rollout_state_documented=rollout_state_documented,
            support_handoff_completed=support_handoff_completed,
            next_roi_decision_recorded=next_roi_decision_recorded,
            track_residual_risks_accepted=track_residual_risks_accepted,
        )
        candidates = self._candidates(
            evidence_storage_signature_required=evidence_storage_signature_required,
            next_tenant_expansion_ready=next_tenant_expansion_ready,
            session_policy_gap_confirmed=session_policy_gap_confirmed,
            api_key_surface_active=api_key_surface_active,
            security_backlog_pause_preferred=security_backlog_pause_preferred,
        )
        blockers = self._blockers(mfa_closure=mfa_closure, candidates=candidates)
        recommendation = max(candidates, key=lambda candidate: candidate.score)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"security-roi-reselection-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "mfa_track_closure": self._closure_summary(mfa_closure=mfa_closure),
            "candidates": candidates,
            "recommendation": recommendation,
            "decisions": self._decisions(
                mfa_closure=mfa_closure,
                recommendation=recommendation,
                status=status,
            ),
            "blockers": blockers,
            "next_tracks": self._next_tracks(status=status, recommendation=recommendation),
        }

    def _candidates(
        self,
        *,
        evidence_storage_signature_required: bool,
        next_tenant_expansion_ready: bool,
        session_policy_gap_confirmed: bool,
        api_key_surface_active: bool,
        security_backlog_pause_preferred: bool,
    ) -> tuple[SecurityRoiCandidate, ...]:
        return (
            SecurityRoiCandidate(
                key="api-key-governance",
                score=80 if api_key_surface_active else 10,
                recommended_track="API Key Governance Foundation Review",
                rationale="API keys são superfície de acesso programático e merecem priorização quando já houver uso ativo",
            ),
            SecurityRoiCandidate(
                key="platform-session-policy",
                score=75 if session_policy_gap_confirmed else 12,
                recommended_track="Platform Owner Session Policy Hardening Review",
                rationale="sessões owner/admin reduzem risco direto de takeover quando política ainda tem lacuna confirmada",
            ),
            SecurityRoiCandidate(
                key="mfa-evidence-storage-signature",
                score=70 if evidence_storage_signature_required else 15,
                recommended_track="Owner MFA Audit Evidence Storage/Signature Review",
                rationale="assinatura/storage aumenta valor auditorial quando evidência precisa circular fora do processo local",
            ),
            SecurityRoiCandidate(
                key="vault-next-tenant-expansion",
                score=65 if next_tenant_expansion_ready else 20,
                recommended_track="Owner MFA Hashicorp Vault Next Tenant Expansion Review",
                rationale="expandir Vault/KMS aumenta cobertura real, mas só deve vencer ROI quando próximo tenant está pronto",
            ),
            SecurityRoiCandidate(
                key="security-backlog-pause",
                score=60 if security_backlog_pause_preferred else 5,
                recommended_track="System ROI Re-Selection Review",
                rationale="pausar security é válido quando os riscos restantes têm ROI menor que produto/operação",
            ),
        )

    def _closure_summary(self, *, mfa_closure: dict[str, object]) -> dict[str, object]:
        return {
            "result": mfa_closure["result"],
            "ready": bool(mfa_closure["ready"]),
            "tenant_id": mfa_closure["tenant_id"],
            "audit_result": mfa_closure["audit_closure"]["result"],
        }

    def _blockers(
        self,
        *,
        mfa_closure: dict[str, object],
        candidates: tuple[SecurityRoiCandidate, ...],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if not mfa_closure["ready"]:
            blockers.append(f"mfa:{mfa_closure['result']}")
            blockers.extend(f"mfa:{blocker}" for blocker in mfa_closure["blockers"])
        if max(candidate.score for candidate in candidates) < 50:
            blockers.append("roi:no-security-candidate-above-threshold")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        mfa_closure: dict[str, object],
        recommendation: SecurityRoiCandidate,
        status: str,
    ) -> tuple[SecurityRoiDecision, ...]:
        return (
            SecurityRoiDecision(
                key="mfa-track-closure",
                status="ready" if mfa_closure["ready"] else "blocked",
                summary="re-selection só segue quando a trilha MFA/Vault/Audit está fechada",
            ),
            SecurityRoiDecision(
                key="recommended-track",
                status=recommendation.key,
                summary=recommendation.rationale,
            ),
            SecurityRoiDecision(
                key="classification",
                status=status,
                summary="classificação decide se há próximo ROI de segurança claro",
            ),
        )

    def _next_tracks(self, *, status: str, recommendation: SecurityRoiCandidate) -> tuple[str, ...]:
        if status == "ready":
            return (recommendation.recommended_track,)
        return (
            "Owner MFA Track Closure Review",
            "System ROI Re-Selection Review",
        )


security_roi_reselection_queries = SecurityRoiReselectionQueryService()
