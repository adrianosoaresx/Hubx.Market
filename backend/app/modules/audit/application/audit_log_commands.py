from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection


ALLOWED_METADATA_TYPES = (str, int, float, bool, type(None))


def _string(value: object, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _safe_metadata(metadata: object) -> dict[str, object]:
    if not isinstance(metadata, dict):
        return {}
    safe: dict[str, object] = {}
    for key, value in metadata.items():
        safe_key = _string(key, limit=80)
        if not safe_key:
            continue
        if isinstance(value, ALLOWED_METADATA_TYPES):
            safe[safe_key] = value
        else:
            safe[safe_key] = _string(value, limit=240)
    return safe


class AuditLogWriteRepository(Protocol):
    def record_event(
        self,
        *,
        tenant_id: int | str | None,
        module: str,
        action: str,
        entity_type: str = "",
        entity_id: str = "",
        actor_label: str = "",
        summary: str = "",
        metadata: dict[str, object] | None = None,
        request_id: str = "",
        ip_address: str | None = None,
        allow_platform_scope: bool = False,
    ) -> dict[str, object]:
        ...


class DjangoOrmAuditLogWriteRepository:
    def __init__(self) -> None:
        try:
            from app.modules.audit.models import AuditLog
            from app.modules.tenants.models import Tenant
        except Exception:
            self.audit_log_model = None
            self.tenant_model = None
            return
        self.audit_log_model = AuditLog
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {self.audit_log_model._meta.db_table, self.tenant_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def record_event(
        self,
        *,
        tenant_id: int | str | None,
        module: str,
        action: str,
        entity_type: str = "",
        entity_id: str = "",
        actor_label: str = "",
        summary: str = "",
        metadata: dict[str, object] | None = None,
        request_id: str = "",
        ip_address: str | None = None,
        allow_platform_scope: bool = False,
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "audit-unavailable", "errors": {"__all__": "Audit log indisponível."}}
        if not _string(module, limit=80):
            return {"result": "audit-invalid", "errors": {"module": "Módulo obrigatório para auditoria."}}
        if not _string(action, limit=120):
            return {"result": "audit-invalid", "errors": {"action": "Ação obrigatória para auditoria."}}

        tenant = None
        if tenant_id:
            tenant = self.tenant_model._default_manager.filter(pk=tenant_id).first()
            if tenant is None:
                return {"result": "audit-tenant-required", "errors": {"__all__": "Tenant obrigatório para auditoria."}}
        elif not allow_platform_scope:
            return {"result": "audit-tenant-required", "errors": {"__all__": "Tenant obrigatório para auditoria."}}

        audit_log = self.audit_log_model._default_manager.create(
            tenant=tenant,
            module=_string(module, limit=80),
            action=_string(action, limit=120),
            entity_type=_string(entity_type, limit=120),
            entity_id=_string(entity_id, limit=120),
            actor_label=_string(actor_label, limit=180),
            summary=_string(summary, limit=240),
            metadata=_safe_metadata(metadata or {}),
            request_id=_string(request_id, limit=120),
            ip_address=ip_address or None,
        )
        return {"result": "audit-recorded", "audit_log": {"id": audit_log.id}}


@dataclass
class AuditLogCommandService:
    repository: AuditLogWriteRepository

    def record_event(
        self,
        *,
        tenant_id: int | str | None,
        module: object,
        action: object,
        entity_type: object = "",
        entity_id: object = "",
        actor_label: object = "",
        summary: object = "",
        metadata: dict[str, object] | None = None,
        request_id: object = "",
        ip_address: str | None = None,
        allow_platform_scope: bool = False,
    ) -> dict[str, object]:
        return self.repository.record_event(
            tenant_id=tenant_id,
            module=_string(module, limit=80),
            action=_string(action, limit=120),
            entity_type=_string(entity_type, limit=120),
            entity_id=_string(entity_id, limit=120),
            actor_label=_string(actor_label, limit=180),
            summary=_string(summary, limit=240),
            metadata=_safe_metadata(metadata or {}),
            request_id=_string(request_id, limit=120),
            ip_address=ip_address,
            allow_platform_scope=allow_platform_scope,
        )


audit_log_commands = AuditLogCommandService(repository=DjangoOrmAuditLogWriteRepository())
