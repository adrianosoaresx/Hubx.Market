from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection
from django.utils import timezone


def _string(value: object) -> str:
    return str(value or "").strip()


def _format_datetime(value: object) -> str:
    if not value:
        return "-"
    try:
        return timezone.localtime(value).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(value)


class AdminAuditLogReadRepository(Protocol):
    def list_logs(self, *, tenant_id: int | str | None, allow_platform_scope: bool = False) -> list[object]:
        ...


class DjangoOrmAdminAuditLogRepository:
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

    def list_logs(self, *, tenant_id: int | str | None, allow_platform_scope: bool = False) -> list[object]:
        if not self.is_ready():
            return []
        if tenant_id:
            queryset = self.audit_log_model._default_manager.filter(tenant_id=tenant_id)
        elif allow_platform_scope:
            queryset = self.audit_log_model._default_manager.filter(tenant__isnull=True)
        else:
            return []
        return list(queryset.order_by("-created_at", "-id")[:200])


@dataclass
class AdminAuditLogQueryService:
    repository: AdminAuditLogReadRepository

    def list_logs(
        self,
        *,
        tenant_id: int | str | None,
        module: str = "",
        action: str = "",
        search: str = "",
        allow_platform_scope: bool = False,
    ) -> list[dict[str, object]]:
        logs = self.repository.list_logs(tenant_id=tenant_id, allow_platform_scope=allow_platform_scope)
        module_value = _string(module).lower()
        action_value = _string(action).lower()
        search_value = _string(search).lower()
        if module_value:
            logs = [log for log in logs if _string(getattr(log, "module", "")).lower() == module_value]
        if action_value:
            logs = [log for log in logs if _string(getattr(log, "action", "")).lower() == action_value]
        if search_value:
            logs = [
                log
                for log in logs
                if search_value in _string(getattr(log, "summary", "")).lower()
                or search_value in _string(getattr(log, "entity_type", "")).lower()
                or search_value in _string(getattr(log, "entity_id", "")).lower()
                or search_value in _string(getattr(log, "actor_label", "")).lower()
            ]
        return [
            {
                "id": log.id,
                "module": _string(log.module),
                "action": _string(log.action),
                "entity": f"{_string(log.entity_type) or '-'} #{_string(log.entity_id) or '-'}",
                "actor_label": _string(log.actor_label) or "Sistema",
                "summary": _string(log.summary) or "Evento auditável registrado",
                "created_at": _format_datetime(log.created_at),
            }
            for log in logs
        ]


admin_audit_log_queries = AdminAuditLogQueryService(repository=DjangoOrmAdminAuditLogRepository())
