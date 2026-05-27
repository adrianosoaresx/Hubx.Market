from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from io import StringIO
from typing import Protocol

from django.db import connection
from django.utils import timezone
from django.utils.dateparse import parse_datetime


def _string(value: object) -> str:
    return str(value or "").strip()


def _parse_datetime(value: object):
    raw = _string(value)
    if not raw:
        return None
    parsed = parse_datetime(raw)
    if parsed is None:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


class AuditEvidenceExportRepository(Protocol):
    def list_logs(
        self,
        *,
        tenant_id: int | str | None,
        allow_platform_scope: bool,
        module: str,
        action: str,
        since,
        until,
        limit: int,
    ) -> list[object]:
        ...


class DjangoOrmAuditEvidenceExportRepository:
    def __init__(self) -> None:
        try:
            from app.modules.audit.models import AuditLog
        except Exception:
            self.audit_log_model = None
            return
        self.audit_log_model = AuditLog

    def is_ready(self) -> bool:
        try:
            table_name = self.audit_log_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                return table_name in set(connection.introspection.table_names(cursor))
        except Exception:
            return False

    def list_logs(
        self,
        *,
        tenant_id: int | str | None,
        allow_platform_scope: bool,
        module: str,
        action: str,
        since,
        until,
        limit: int,
    ) -> list[object]:
        if not self.is_ready():
            return []
        if tenant_id:
            queryset = self.audit_log_model._default_manager.filter(tenant_id=tenant_id)
        elif allow_platform_scope:
            queryset = self.audit_log_model._default_manager.filter(tenant__isnull=True)
        else:
            return []
        if module:
            queryset = queryset.filter(module=module)
        if action:
            queryset = queryset.filter(action=action)
        if since:
            queryset = queryset.filter(created_at__gte=since)
        if until:
            queryset = queryset.filter(created_at__lte=until)
        return list(queryset.order_by("created_at", "id")[:limit])


@dataclass
class AuditEvidenceExportQueryService:
    repository: AuditEvidenceExportRepository

    def export(
        self,
        *,
        tenant_id: int | str | None,
        allow_platform_scope: bool = False,
        module: object = "",
        action: object = "",
        since: object = "",
        until: object = "",
        limit: int = 500,
        output_format: str = "jsonl",
        include_metadata: bool = False,
    ) -> dict[str, object]:
        safe_limit = min(max(int(limit or 500), 1), 5000)
        parsed_since = _parse_datetime(since)
        parsed_until = _parse_datetime(until)
        format_value = _string(output_format).lower() or "jsonl"
        if format_value not in {"jsonl", "csv"}:
            return {"result": "audit-evidence-export-invalid", "errors": {"format": "Formato deve ser jsonl ou csv."}}
        if not tenant_id and not allow_platform_scope:
            return {
                "result": "audit-evidence-export-tenant-required",
                "errors": {"tenant_id": "tenant_id é obrigatório salvo platform-scope explícito."},
            }
        logs = self.repository.list_logs(
            tenant_id=tenant_id,
            allow_platform_scope=allow_platform_scope,
            module=_string(module),
            action=_string(action),
            since=parsed_since,
            until=parsed_until,
            limit=safe_limit,
        )
        rows = [self._serialize_log(log, include_metadata=include_metadata) for log in logs]
        return {
            "result": "audit-evidence-exported",
            "count": len(rows),
            "tenant_id": _string(tenant_id),
            "platform_scope": bool(allow_platform_scope and not tenant_id),
            "format": format_value,
            "content": self._render(rows, output_format=format_value),
        }

    def _serialize_log(self, log: object, *, include_metadata: bool) -> dict[str, object]:
        created_at = getattr(log, "created_at", None)
        row = {
            "id": getattr(log, "id", None),
            "tenant_id": getattr(log, "tenant_id", None),
            "module": _string(getattr(log, "module", "")),
            "action": _string(getattr(log, "action", "")),
            "entity_type": _string(getattr(log, "entity_type", "")),
            "entity_id": _string(getattr(log, "entity_id", "")),
            "actor_label": _string(getattr(log, "actor_label", "")),
            "summary": _string(getattr(log, "summary", "")),
            "request_id": _string(getattr(log, "request_id", "")),
            "created_at": created_at.isoformat() if created_at else "",
        }
        if include_metadata:
            row["metadata"] = getattr(log, "metadata", {}) or {}
        return row

    def _render(self, rows: list[dict[str, object]], *, output_format: str) -> str:
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


audit_evidence_export_queries = AuditEvidenceExportQueryService(repository=DjangoOrmAuditEvidenceExportRepository())
