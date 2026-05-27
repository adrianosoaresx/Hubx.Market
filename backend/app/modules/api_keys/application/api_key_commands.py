from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Protocol

from django.contrib.auth.hashers import make_password
from django.db import connection
from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands


DEFAULT_SCOPES = ("read:orders",)


def _string(value: object, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _scopes(value: object) -> list[str]:
    if isinstance(value, str):
        candidates = value.replace(";", ",").split(",")
    elif isinstance(value, (list, tuple, set)):
        candidates = value
    else:
        candidates = DEFAULT_SCOPES
    scopes = []
    for candidate in candidates:
        scope = _string(candidate, limit=80)
        if scope and scope not in scopes:
            scopes.append(scope)
    return scopes or list(DEFAULT_SCOPES)


class ApiKeyCommandRepository(Protocol):
    def create_key(
        self,
        *,
        tenant_id: int | str | None,
        name: object,
        scopes: object = None,
        owner_id: int | str | None = None,
        actor_label: object = "",
    ) -> dict[str, object]:
        ...

    def revoke_key(
        self,
        *,
        tenant_id: int | str | None,
        key_id: int | str | None,
        actor_label: object = "",
    ) -> dict[str, object]:
        ...


class DjangoOrmApiKeyCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts.models import OwnerUser
            from app.modules.api_keys.models import ApiKey
            from app.modules.tenants.models import Tenant
        except Exception:
            self.api_key_model = None
            self.owner_model = None
            self.tenant_model = None
            return
        self.api_key_model = ApiKey
        self.owner_model = OwnerUser
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.api_key_model._meta.db_table,
                self.tenant_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def create_key(
        self,
        *,
        tenant_id: int | str | None,
        name: object,
        scopes: object = None,
        owner_id: int | str | None = None,
        actor_label: object = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "api-key-unavailable", "errors": {"__all__": "API keys indisponíveis."}}
        tenant = self._tenant(tenant_id=tenant_id)
        if tenant is None:
            return {"result": "api-key-tenant-required", "errors": {"__all__": "Tenant obrigatório."}}
        key_name = _string(name, limit=120)
        if not key_name:
            return {"result": "api-key-invalid", "errors": {"name": "Informe o nome da chave."}}
        owner = self._owner(tenant_id=tenant.id, owner_id=owner_id)
        secret = self._new_secret()
        prefix = secret[:18]
        api_key = self.api_key_model._default_manager.create(
            tenant=tenant,
            owner=owner,
            name=key_name,
            prefix=prefix,
            key_hash=make_password(secret),
            scopes=_scopes(scopes),
            created_by_label=_string(actor_label, limit=180),
        )
        audit_log_commands.record_event(
            tenant_id=tenant.id,
            module="api_keys",
            action="api_key.created",
            entity_type="ApiKey",
            entity_id=str(api_key.id),
            actor_label=_string(actor_label, limit=180),
            summary=f"API key {api_key.name} criada",
            metadata={"key_id": api_key.id, "prefix": api_key.prefix, "scopes": ",".join(api_key.scopes)},
        )
        return {
            "result": "api-key-created",
            "api_key": {
                "id": api_key.id,
                "name": api_key.name,
                "prefix": api_key.prefix,
                "scopes": tuple(api_key.scopes),
                "status": api_key.status,
            },
            "secret": secret,
        }

    def revoke_key(
        self,
        *,
        tenant_id: int | str | None,
        key_id: int | str | None,
        actor_label: object = "",
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "api-key-unavailable", "errors": {"__all__": "API keys indisponíveis."}}
        tenant = self._tenant(tenant_id=tenant_id)
        if tenant is None:
            return {"result": "api-key-tenant-required", "errors": {"__all__": "Tenant obrigatório."}}
        api_key = self.api_key_model._default_manager.filter(pk=key_id, tenant=tenant).first()
        if api_key is None:
            return {"result": "api-key-not-found", "errors": {"__all__": "Chave não encontrada neste tenant."}}
        if api_key.status == self.api_key_model.Status.REVOKED:
            return {"result": "api-key-already-revoked", "api_key": {"id": api_key.id, "status": api_key.status}}
        api_key.status = self.api_key_model.Status.REVOKED
        api_key.revoked_at = timezone.now()
        api_key.revoked_by_label = _string(actor_label, limit=180)
        api_key.save(update_fields=("status", "revoked_at", "revoked_by_label", "updated_at"))
        audit_log_commands.record_event(
            tenant_id=tenant.id,
            module="api_keys",
            action="api_key.revoked",
            entity_type="ApiKey",
            entity_id=str(api_key.id),
            actor_label=_string(actor_label, limit=180),
            summary=f"API key {api_key.name} revogada",
            metadata={"key_id": api_key.id, "prefix": api_key.prefix},
        )
        return {"result": "api-key-revoked", "api_key": {"id": api_key.id, "status": api_key.status}}

    def _tenant(self, *, tenant_id: int | str | None):
        if not tenant_id:
            return None
        return self.tenant_model._default_manager.filter(pk=tenant_id).first()

    def _owner(self, *, tenant_id: int | str, owner_id: int | str | None):
        if not owner_id:
            return None
        return self.owner_model._default_manager.filter(pk=owner_id, tenant_id=tenant_id).first()

    def _new_secret(self) -> str:
        return f"hbx_{secrets.token_urlsafe(32)}"


@dataclass
class ApiKeyCommandService:
    repository: ApiKeyCommandRepository

    def create_key(
        self,
        *,
        tenant_id: int | str | None,
        name: object,
        scopes: object = None,
        owner_id: int | str | None = None,
        actor_label: object = "",
    ) -> dict[str, object]:
        return self.repository.create_key(
            tenant_id=tenant_id,
            name=name,
            scopes=scopes,
            owner_id=owner_id,
            actor_label=actor_label,
        )

    def revoke_key(
        self,
        *,
        tenant_id: int | str | None,
        key_id: int | str | None,
        actor_label: object = "",
    ) -> dict[str, object]:
        return self.repository.revoke_key(
            tenant_id=tenant_id,
            key_id=key_id,
            actor_label=actor_label,
        )


api_key_commands = ApiKeyCommandService(repository=DjangoOrmApiKeyCommandRepository())
