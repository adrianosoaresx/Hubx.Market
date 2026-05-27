from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.audit_evidence_export_queries import audit_evidence_export_queries


@dataclass(frozen=True)
class AuditEvidenceClosureDecision:
    key: str
    status: str
    summary: str


@dataclass
class AuditEvidenceClosureQueryService:
    def get_closure(
        self,
        *,
        tenant_id: int | str | None = None,
        allow_platform_scope: bool = False,
    ) -> dict[str, object]:
        sample = audit_evidence_export_queries.export(
            tenant_id=tenant_id,
            allow_platform_scope=allow_platform_scope,
            limit=1,
            output_format="jsonl",
        )
        blockers: list[str] = []
        if sample["result"] != "audit-evidence-exported":
            blockers.append(str(sample["result"]))

        decisions = self._decisions(sample=sample)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"audit-evidence-closure-{status}",
            "ready": not blockers,
            "status": status,
            "blockers": tuple(blockers),
            "tenant_id": str(tenant_id or "").strip(),
            "platform_scope": bool(allow_platform_scope and not tenant_id),
            "sample_count": sample.get("count", 0) if sample["result"] == "audit-evidence-exported" else 0,
            "decisions": decisions,
            "residual_risks": self._residual_risks(),
            "next_tracks": self._next_tracks(),
        }

    def _decisions(self, *, sample: dict[str, object]) -> tuple[AuditEvidenceClosureDecision, ...]:
        export_status = "ready" if sample["result"] == "audit-evidence-exported" else "blocked"
        return (
            AuditEvidenceClosureDecision(
                key="command-export",
                status=export_status,
                summary="export read-only JSONL/CSV existe para tenant-scope e platform-scope explícito",
            ),
            AuditEvidenceClosureDecision(
                key="admin-surface",
                status="ready",
                summary="/ops/audit/export/ entrega JSONL tenant-scoped e herda gate audit.view",
            ),
            AuditEvidenceClosureDecision(
                key="artifact-storage",
                status="out-of-scope",
                summary="assinatura, storage externo e retenção de artefatos ficam fora deste recorte",
            ),
        )

    def _residual_risks(self) -> tuple[str, ...]:
        return (
            "export HTTP ainda não possui filtros avançados de período/formato",
            "artefatos exportados não são assinados nem armazenados automaticamente",
            "redaction avançado de metadata ainda depende do opt-in conservador",
            "export cross-tenant agregado permanece bloqueado por desenho",
        )

    def _next_tracks(self) -> tuple[str, ...]:
        return (
            "Platform Owner MFA/SSO Review",
            "Platform Admin Permission Matrix Persistence Review",
            "Platform Operations Dashboard Review",
        )


audit_evidence_closure_queries = AuditEvidenceClosureQueryService()
