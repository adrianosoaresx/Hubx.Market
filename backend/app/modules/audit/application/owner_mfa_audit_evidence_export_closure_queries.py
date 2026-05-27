from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.owner_mfa_audit_evidence_export_execution_queries import (
    owner_mfa_audit_evidence_export_execution_queries,
)


@dataclass(frozen=True)
class OwnerMfaAuditEvidenceExportClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class OwnerMfaAuditEvidenceExportClosureQueryService:
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
        residual_risks_accepted: bool = False,
    ) -> dict[str, object]:
        export = owner_mfa_audit_evidence_export_execution_queries.export(
            tenant_id=tenant_id,
            since=since,
            until=until,
            limit=limit,
            output_format=output_format,
            expected_actions_confirmed=expected_actions_confirmed,
            export_scope_documented=export_scope_documented,
            redaction_reviewed=redaction_reviewed,
            recipient_approved=recipient_approved,
        )
        closure_signals = {
            "artifact_delivered": bool(artifact_delivered),
            "retention_owner_confirmed": bool(retention_owner_confirmed),
            "storage_decision_recorded": bool(storage_decision_recorded),
            "residual_risks_accepted": bool(residual_risks_accepted),
        }
        blockers = self._blockers(export=export, closure_signals=closure_signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"owner-mfa-audit-evidence-export-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "tenant_id": str(tenant_id or "").strip(),
            "format": str(output_format or "jsonl").strip().lower(),
            "export_count": export.get("count", 0) if export["result"] == "owner-mfa-audit-evidence-exported" else 0,
            "mfa_actions": export.get("mfa_actions", ()),
            "export": self._export_summary(export=export),
            "closure_signals": closure_signals,
            "decisions": self._decisions(export=export, closure_signals=closure_signals, status=status),
            "blockers": blockers,
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(status=status),
        }

    def _export_summary(self, *, export: dict[str, object]) -> dict[str, object]:
        return {
            "result": export["result"],
            "ready": bool(export.get("ready")),
            "count": export.get("count", 0),
            "format": export.get("format", ""),
            "module": export.get("module", ""),
        }

    def _blockers(
        self,
        *,
        export: dict[str, object],
        closure_signals: dict[str, bool],
    ) -> tuple[str, ...]:
        blockers: list[str] = []
        if export["result"] != "owner-mfa-audit-evidence-exported":
            blockers.append(f"export:{export['result']}")
            blockers.extend(f"export:{blocker}" for blocker in export.get("blockers", ()))
        if export.get("count", 0) == 0:
            blockers.append("export:empty")
        if not closure_signals["artifact_delivered"]:
            blockers.append("closure:artifact-not-delivered")
        if not closure_signals["retention_owner_confirmed"]:
            blockers.append("closure:retention-owner-not-confirmed")
        if not closure_signals["storage_decision_recorded"]:
            blockers.append("closure:storage-decision-not-recorded")
        if not closure_signals["residual_risks_accepted"]:
            blockers.append("closure:residual-risks-not-accepted")
        return tuple(dict.fromkeys(blockers))

    def _decisions(
        self,
        *,
        export: dict[str, object],
        closure_signals: dict[str, bool],
        status: str,
    ) -> tuple[OwnerMfaAuditEvidenceExportClosureDecision, ...]:
        return (
            OwnerMfaAuditEvidenceExportClosureDecision(
                key="export-artifact",
                status="ready" if export["result"] == "owner-mfa-audit-evidence-exported" else "blocked",
                summary="closure exige export MFA gerado pelo command dedicado",
            ),
            OwnerMfaAuditEvidenceExportClosureDecision(
                key="artifact-delivery",
                status="ready" if closure_signals["artifact_delivered"] else "blocked",
                summary="artefato precisa ter sido entregue ao destinatário aprovado",
            ),
            OwnerMfaAuditEvidenceExportClosureDecision(
                key="retention",
                status="ready" if closure_signals["retention_owner_confirmed"] else "blocked",
                summary="responsável por retenção do artefato precisa estar definido",
            ),
            OwnerMfaAuditEvidenceExportClosureDecision(
                key="storage",
                status="recorded" if closure_signals["storage_decision_recorded"] else "blocked",
                summary="decisão de storage/assinatura futura precisa estar registrada",
            ),
            OwnerMfaAuditEvidenceExportClosureDecision(
                key="classification",
                status=status,
                summary="classificação final fecha ou bloqueia a trilha de export MFA",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "artefato exportado ainda não é assinado nem armazenado automaticamente",
            "retenção e compartilhamento dependem de processo operacional externo",
            "metadata segue fora do export; evidência profunda exige review separada",
            "platform-scope e export cross-tenant continuam fora do recorte",
        )

    def _next_tracks(self, *, status: str) -> tuple[str, ...]:
        if status == "ready":
            return (
                "Owner MFA Audit Evidence Storage/Signature Review",
                "Owner MFA Track Closure Review",
            )
        return (
            "Owner MFA Audit Evidence Export Execution",
            "Owner MFA Audit Evidence Export Closure Review",
        )


owner_mfa_audit_evidence_export_closure_queries = OwnerMfaAuditEvidenceExportClosureQueryService()
