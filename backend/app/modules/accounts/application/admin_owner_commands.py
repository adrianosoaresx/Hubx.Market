from __future__ import annotations

from dataclasses import dataclass

from django.db import connection

from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, ROLE_PERMISSIONS, admin_permissions
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _email(value: object) -> str:
    return _string(value, limit=254).lower()


def _boolean(value: object, *, default: bool = False) -> bool:
    if value in (True, False):
        return bool(value)
    normalized = str(value or "").strip().lower()
    if normalized in {"1", "true", "on", "yes", "sim"}:
        return True
    if normalized in {"0", "false", "off", "no", "nao", "não"}:
        return False
    return default


class DjangoOrmAdminOwnerCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts.models import OwnerUser
            from app.modules.tenants.models import Tenant
        except Exception:
            self.owner_model = None
            self.tenant_model = None
            return
        self.owner_model = OwnerUser
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {self.owner_model._meta.db_table, self.tenant_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def get_tenant(self, *, tenant_id: int | str | None):
        if not self.is_ready():
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return None
        return self.tenant_model._default_manager.filter(pk=normalized_tenant_id).first()

    def get_owner(self, *, tenant_id: int | str, owner_id: int | str):
        if self.owner_model is None:
            return None
        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_owner_id = str(owner_id or "").strip()
        if not normalized_tenant_id or not normalized_owner_id:
            return None
        try:
            return self.owner_model._default_manager.filter(id=normalized_owner_id, tenant_id=normalized_tenant_id).first()
        except Exception:
            return None

    def email_exists(self, *, tenant_id: int | str, email: str, exclude_owner_id: int | str | None = None) -> bool:
        if self.owner_model is None:
            return False
        queryset = self.owner_model._default_manager.filter(tenant_id=tenant_id, email__iexact=email)
        if exclude_owner_id:
            queryset = queryset.exclude(pk=exclude_owner_id)
        return queryset.exists()

    def create_owner(self, *, tenant, values: dict[str, object]):
        return self.owner_model._default_manager.create(tenant=tenant, **values)


@dataclass
class AdminOwnerCommandService:
    repository: DjangoOrmAdminOwnerCommandRepository

    def create_owner(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-permission-denied", "errors": {"__all__": "Permissão insuficiente para gerenciar owners."}}
        tenant = self.repository.get_tenant(tenant_id=tenant_id)
        if tenant is None:
            return {"result": "owner-tenant-required", "errors": {"__all__": "Tenant obrigatório para criar owner."}}
        values, errors = self._validated_values(tenant_id=tenant.id, payload=payload)
        if errors:
            return {"result": "owner-invalid", "errors": errors}
        owner = self.repository.create_owner(tenant=tenant, values=values)
        self._record_owner_event(
            owner=owner,
            action="owner.created",
            summary=f"Owner {owner.email} criado",
            actor_label=actor_label,
        )
        return {"result": "owner-created", "owner": {"id": owner.id, "email": owner.email}}

    def update_owner_access(
        self,
        *,
        tenant_id: int | str | None,
        owner_id: int | str,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return {"result": "owner-permission-denied", "errors": {"__all__": "Permissão insuficiente para gerenciar owners."}}
        owner = self.repository.get_owner(tenant_id=tenant_id or "", owner_id=owner_id)
        if owner is None:
            return {"result": "owner-not-found", "errors": {"__all__": "Owner não encontrado neste tenant."}}
        values, errors = self._validated_values(tenant_id=tenant_id or "", payload=payload, current_owner_id=owner.id)
        if errors:
            return {"result": "owner-invalid", "errors": errors}
        changed_fields = []
        for field_name, value in values.items():
            if getattr(owner, field_name) != value:
                setattr(owner, field_name, value)
                changed_fields.append(field_name)
        if not changed_fields:
            return {"result": "owner-unchanged", "owner": {"id": owner.id, "email": owner.email}}
        owner.save(update_fields=[*changed_fields, "updated_at"])
        self._record_owner_event(
            owner=owner,
            action="owner.access_updated",
            summary=f"Acesso do owner {owner.email} atualizado",
            actor_label=actor_label,
        )
        return {"result": "owner-updated", "owner": {"id": owner.id, "email": owner.email}}

    def set_notification_preference(
        self,
        *,
        tenant_id: int | str,
        owner_id: int | str,
        receives_notifications: bool,
        actor_label: str = "",
        actor_role: str = "",
    ) -> str:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_OWNERS_MANAGE)
        if not permission.allowed:
            return "owner-permission-denied"
        owner = self.repository.get_owner(tenant_id=tenant_id, owner_id=owner_id)
        if owner is None:
            return "owner-not-found"
        if bool(owner.receives_notifications) == bool(receives_notifications):
            return "owner-notifications-unchanged"
        owner.receives_notifications = bool(receives_notifications)
        owner.save(update_fields=("receives_notifications", "updated_at"))
        self._record_owner_event(
            owner=owner,
            action="owner.access_updated",
            summary=f"Notificações do owner {owner.email} atualizadas",
            actor_label=actor_label,
        )
        return "owner-notifications-enabled" if receives_notifications else "owner-notifications-disabled"

    def _validated_values(
        self,
        *,
        tenant_id: int | str,
        payload: dict[str, object],
        current_owner_id: int | None = None,
    ) -> tuple[dict[str, object], dict[str, str]]:
        email = _email(payload.get("email"))
        full_name = _string(payload.get("full_name"), limit=150)
        role = _string(payload.get("role"), limit=64).lower().replace("-", "_") or "viewer"
        is_active = _boolean(payload.get("is_active"), default=False)
        receives_notifications = _boolean(payload.get("receives_notifications"), default=False)
        errors: dict[str, str] = {}

        if not email or "@" not in email:
            errors["email"] = "Informe um e-mail válido para o owner."
        if role not in ROLE_PERMISSIONS:
            errors["role"] = "Papel administrativo inválido."
        if email and self.repository.email_exists(tenant_id=tenant_id, email=email, exclude_owner_id=current_owner_id):
            errors["email"] = "Já existe um owner com este e-mail neste tenant."

        return (
            {
                "email": email,
                "full_name": full_name,
                "role": role,
                "is_active": is_active,
                "receives_notifications": receives_notifications,
            },
            errors,
        )

    def _record_owner_event(self, *, owner, action: str, summary: str, actor_label: str = "") -> None:
        audit_log_commands.record_event(
            tenant_id=owner.tenant_id,
            module="accounts",
            action=action,
            entity_type="OwnerUser",
            entity_id=str(owner.id),
            actor_label=actor_label,
            summary=summary,
            metadata={
                "email": owner.email,
                "role": owner.role,
                "is_active": owner.is_active,
                "receives_notifications": owner.receives_notifications,
            },
        )


admin_owner_commands = AdminOwnerCommandService(repository=DjangoOrmAdminOwnerCommandRepository())
