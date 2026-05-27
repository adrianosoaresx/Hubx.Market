from __future__ import annotations

import json
from dataclasses import dataclass

from app.modules.audit.application.audit_evidence_export_queries import audit_evidence_export_queries


@dataclass(frozen=True)
class OwnerMfaAuditEvidenceExportReviewDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaAuditEvidenceExportReviewQueryService:
    def get_review(
        self,
        *,
        tenant_id: int | str | None,
        since: object = "",
        until: object = "",
        expected_actions_confirmed: bool = False,
        export_scope_documented: bool = False,
        redaction_reviewed: bool = False,
        recipient_approved: bool = False,
    ) -> dict[str, object]:
        sample = audit_evidence_export_queries.export(
            tenant_id=tenant_id,
            module="accounts",
            since=since,
            until=until,
            limit=200,
            output_format="jsonl",
            include_metadata=False,
        )
        actions = self._actions(sample=sample)
        mfa_actions = tuple(action for action in actions if "mfa" in action.lower())
        signals = {
            "tenant_scope_valid": sample["result"] == "audit-evidence-exported" and bool(tenant_id),
            "mfa_events_present": bool(mfa_actions),
            "expected_actions_confirmed": bool(expected_actions_confirmed),
            "export_scope_documented": bool(export_scope_documented),
            "redaction_reviewed": bool(redaction_reviewed),
            "recipient_approved": bool(recipient_approved),
        }
        blockers = self._blockers(sample=sample, signals=signals)
        status = self._status(signals=signals, blockers=blockers)
        return {
            "result": f"owner-mfa-audit-evidence-export-review-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "module": "accounts",
            "sample_count": sample.get("count", 0) if sample["result"] == "audit-evidence-exported" else 0,
            "mfa_event_count": len(mfa_actions),
            "mfa_actions": mfa_actions,
            "signals": signals,
            "decisions": self._decisions(signals=signals, status=status),
            "blockers": blockers,
            "export_contract": self._export_contract(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _actions(self, *, sample: dict[str, object]) -> tuple[str, ...]:
        if sample["result"] != "audit-evidence-exported":
            return ()
        content = str(sample.get("content") or "")
        actions: list[str] = []
        for line in content.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            action = str(row.get("action") or "").strip()
            if action:
                actions.append(action)
        return tuple(dict.fromkeys(actions))

    def _status(self, *, signals: dict[str, bool], blockers: tuple[str, ...]) -> str:
        if blockers:
            return "blocked"
        if all(signals.values()):
            return "ready"
        return "watch"

    def _blockers(self, *, sample: dict[str, object], signals: dict[str, bool]) -> tuple[str, ...]:
        blockers: list[str] = []
        if sample["result"] != "audit-evidence-exported":
            blockers.append(str(sample["result"]))
        if not signals["tenant_scope_valid"]:
            blockers.append("tenant-scope-required")
        if not signals["mfa_events_present"]:
            blockers.append("evidence:no-mfa-events")
        if not signals["expected_actions_confirmed"]:
            blockers.append("review:expected-actions-not-confirmed")
        if not signals["export_scope_documented"]:
            blockers.append("review:export-scope-not-documented")
        if not signals["redaction_reviewed"]:
            blockers.append("review:redaction-not-reviewed")
        if not signals["recipient_approved"]:
            blockers.append("review:recipient-not-approved")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaAuditEvidenceExportReviewDecision, ...]:
        return (
            OwnerMfaAuditEvidenceExportReviewDecision(
                key="tenant-scope",
                status="ready" if signals["tenant_scope_valid"] else "blocked",
                summary="export MFA owner/admin deve ser tenant-scoped e não platform-scope",
            ),
            OwnerMfaAuditEvidenceExportReviewDecision(
                key="mfa-events",
                status="ready" if signals["mfa_events_present"] else "blocked",
                summary="amostra precisa conter eventos MFA em AuditLog antes da execution",
            ),
            OwnerMfaAuditEvidenceExportReviewDecision(
                key="redaction",
                status="ready" if signals["redaction_reviewed"] else "blocked",
                summary="metadata sensível não deve entrar no export por padrão",
            ),
            OwnerMfaAuditEvidenceExportReviewDecision(
                key="recipient",
                status="ready" if signals["recipient_approved"] else "blocked",
                summary="destinatário/uso da evidência deve estar aprovado antes do export",
            ),
            OwnerMfaAuditEvidenceExportReviewDecision(
                key="classification",
                status=status,
                summary="classificação decide se a export execution pode seguir",
            ),
        )

    def _export_contract(self) -> tuple[str, ...]:
        return (
            "usar `audit_evidence_export_queries` como exportador canônico",
            "filtrar `module=accounts` e tenant_id explícito",
            "manter `include_metadata=False` salvo revisão separada",
            "não gerar arquivo assinado nem storage externo nesta review",
            "não consultar tabelas internas de accounts para montar evidência",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Audit Evidence Export Execution",
                "Audit Evidence Closure Review",
            )
        return (
            "Owner MFA Audit Instrumentation Gap Review",
            "Owner MFA Audit Evidence Export Review",
        )


owner_mfa_audit_evidence_export_review_queries = OwnerMfaAuditEvidenceExportReviewQueryService()
