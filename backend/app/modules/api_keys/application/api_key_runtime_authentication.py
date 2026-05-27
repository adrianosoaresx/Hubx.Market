from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.contrib.auth.hashers import check_password
from django.db import connection
from django.utils import timezone

from app.modules.audit.application.audit_log_commands import audit_log_commands


API_KEY_PREFIX_LENGTH = 18


def _string(value: object, *, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _bearer_secret(authorization_header: object) -> str:
    header = str(authorization_header or "").strip()
    scheme, separator, credential = header.partition(" ")
    if not separator or scheme.lower() != "bearer":
        return ""
    return credential.strip()


def _safe_prefix(secret: str) -> str:
    if len(secret) < API_KEY_PREFIX_LENGTH:
        return ""
    return secret[:API_KEY_PREFIX_LENGTH]


class ApiKeyRuntimeAuthenticationRepository(Protocol):
    def authenticate(
        self,
        *,
        tenant_id: int | str | None,
        authorization_header: object,
        required_scope: object = "",
        request_id: object = "",
        ip_address: str | None = None,
    ) -> dict[str, object]:
        ...


class DjangoOrmApiKeyRuntimeAuthenticationRepository:
    def __init__(self) -> None:
        try:
            from app.modules.api_keys.models import ApiKey
            from app.modules.tenants.models import Tenant
        except Exception:
            self.api_key_model = None
            self.tenant_model = None
            return
        self.api_key_model = ApiKey
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

    def authenticate(
        self,
        *,
        tenant_id: int | str | None,
        authorization_header: object,
        required_scope: object = "",
        request_id: object = "",
        ip_address: str | None = None,
    ) -> dict[str, object]:
        if not self.is_ready():
            return {"result": "api-key-auth-unavailable", "authenticated": False}
        tenant = self._tenant(tenant_id=tenant_id)
        if tenant is None:
            return {"result": "api-key-auth-tenant-required", "authenticated": False}

        secret = _bearer_secret(authorization_header)
        prefix = _safe_prefix(secret)
        if not secret or not prefix:
            self._record_failure(
                tenant_id=tenant.id,
                prefix=prefix,
                reason="invalid-header",
                request_id=request_id,
                ip_address=ip_address,
            )
            return {"result": "api-key-auth-invalid", "authenticated": False}

        api_key = self.api_key_model._default_manager.filter(tenant=tenant, prefix=prefix).first()
        if api_key is None:
            self._record_failure(
                tenant_id=tenant.id,
                prefix=prefix,
                reason="not-found",
                request_id=request_id,
                ip_address=ip_address,
            )
            return {"result": "api-key-auth-invalid", "authenticated": False}

        if api_key.status != self.api_key_model.Status.ACTIVE:
            self._record_failure(
                tenant_id=tenant.id,
                api_key_id=api_key.id,
                prefix=prefix,
                reason="inactive",
                request_id=request_id,
                ip_address=ip_address,
            )
            return {
                "result": "api-key-auth-revoked",
                "authenticated": False,
                "api_key": {"id": api_key.id, "prefix": api_key.prefix, "status": api_key.status},
            }

        if not check_password(secret, api_key.key_hash):
            self._record_failure(
                tenant_id=tenant.id,
                api_key_id=api_key.id,
                prefix=prefix,
                reason="hash-mismatch",
                request_id=request_id,
                ip_address=ip_address,
            )
            return {"result": "api-key-auth-invalid", "authenticated": False}

        scope = _string(required_scope, limit=80)
        if scope and scope not in set(api_key.scopes or []):
            self._record_failure(
                tenant_id=tenant.id,
                api_key_id=api_key.id,
                prefix=prefix,
                reason="scope-denied",
                request_id=request_id,
                ip_address=ip_address,
                metadata={"required_scope": scope},
            )
            return {
                "result": "api-key-auth-scope-denied",
                "authenticated": False,
                "api_key": {"id": api_key.id, "prefix": api_key.prefix, "status": api_key.status},
            }

        api_key.last_used_at = timezone.now()
        api_key.save(update_fields=("last_used_at", "updated_at"))
        return {
            "result": "api-key-authenticated",
            "authenticated": True,
            "api_key": {
                "id": api_key.id,
                "tenant_id": tenant.id,
                "prefix": api_key.prefix,
                "scopes": tuple(api_key.scopes or []),
                "status": api_key.status,
            },
            "rate_limit_key": f"tenant:{tenant.id}:api_key:{api_key.prefix}",
        }

    def _tenant(self, *, tenant_id: int | str | None):
        if not tenant_id:
            return None
        return self.tenant_model._default_manager.filter(pk=tenant_id).first()

    def _record_failure(
        self,
        *,
        tenant_id: int | str,
        prefix: str,
        reason: str,
        request_id: object = "",
        ip_address: str | None = None,
        api_key_id: int | str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> None:
        safe_metadata = {
            "reason": _string(reason, limit=80),
            "prefix": _string(prefix, limit=API_KEY_PREFIX_LENGTH),
        }
        if api_key_id:
            safe_metadata["key_id"] = api_key_id
        safe_metadata.update(metadata or {})
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="api_keys",
            action="api_key.auth_failed",
            entity_type="ApiKey",
            entity_id=str(api_key_id or ""),
            actor_label="api_key",
            summary=f"Falha de autenticação por API key: {safe_metadata['reason']}",
            metadata=safe_metadata,
            request_id=_string(request_id, limit=120),
            ip_address=ip_address,
        )


@dataclass
class ApiKeyRuntimeAuthenticationService:
    repository: ApiKeyRuntimeAuthenticationRepository

    def authenticate(
        self,
        *,
        tenant_id: int | str | None,
        authorization_header: object,
        required_scope: object = "",
        request_id: object = "",
        ip_address: str | None = None,
    ) -> dict[str, object]:
        return self.repository.authenticate(
            tenant_id=tenant_id,
            authorization_header=authorization_header,
            required_scope=required_scope,
            request_id=request_id,
            ip_address=ip_address,
        )


api_key_runtime_authentication = ApiKeyRuntimeAuthenticationService(
    repository=DjangoOrmApiKeyRuntimeAuthenticationRepository()
)
