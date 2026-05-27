from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import StringIO

from app.modules.audit.application.audit_evidence_export_queries import audit_evidence_export_queries
from app.modules.audit.application.owner_mfa_audit_evidence_export_review_queries import (
    owner_mfa_audit_evidence_export_review_queries,
)


@dataclass
class OwnerMfaAuditEvidenceExportExecutionQueryService:
    def export(
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
    ) -> dict[str, object]:
        review = owner_mfa_audit_evidence_export_review_queries.get_review(
            tenant_id=tenant_id,
            since=since,
            until=until,
            expected_actions_confirmed=expected_actions_confirmed,
            export_scope_documented=export_scope_documented,
            redaction_reviewed=redaction_reviewed,
            recipient_approved=recipient_approved,
        )
        format_value = str(output_format or "jsonl").strip().lower()
        if format_value not in {"jsonl", "csv"}:
            return {
                "result": "owner-mfa-audit-evidence-export-invalid",
                "ready": False,
                "status": "blocked",
                "errors": {"format": "Formato deve ser jsonl ou csv."},
                "review": review,
            }
        if not review["ready"]:
            return {
                "result": "owner-mfa-audit-evidence-export-blocked",
                "ready": False,
                "status": "blocked",
                "tenant_id": review["tenant_id"],
                "review": review,
                "blockers": review["blockers"],
                "content": "",
            }

        export = audit_evidence_export_queries.export(
            tenant_id=tenant_id,
            module="accounts",
            since=since,
            until=until,
            limit=limit,
            output_format="jsonl",
            include_metadata=False,
        )
        if export["result"] != "audit-evidence-exported":
            return {
                "result": "owner-mfa-audit-evidence-export-failed",
                "ready": False,
                "status": "blocked",
                "tenant_id": review["tenant_id"],
                "review": review,
                "blockers": (str(export["result"]),),
                "content": "",
            }
        rows = self._mfa_rows(content=str(export["content"] or ""))
        return {
            "result": "owner-mfa-audit-evidence-exported",
            "ready": True,
            "status": "exported",
            "tenant_id": review["tenant_id"],
            "module": "accounts",
            "format": format_value,
            "count": len(rows),
            "mfa_actions": tuple(dict.fromkeys(str(row.get("action") or "") for row in rows)),
            "review": review,
            "content": self._render(rows=rows, output_format=format_value),
        }

    def _mfa_rows(self, *, content: str) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for line in content.splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "mfa" in str(row.get("action") or "").lower():
                row.pop("metadata", None)
                rows.append(row)
        return rows

    def _render(self, *, rows: list[dict[str, object]], output_format: str) -> str:
        if output_format == "jsonl":
            return "\n".join(json.dumps(row, sort_keys=True, default=str) for row in rows)
        fieldnames = [
            "id",
            "tenant_id",
            "module",
            "action",
            "entity_type",
            "entity_id",
            "actor_label",
            "summary",
            "request_id",
            "created_at",
        ]
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue().strip()


owner_mfa_audit_evidence_export_execution_queries = OwnerMfaAuditEvidenceExportExecutionQueryService()
