from __future__ import annotations

from dataclasses import dataclass

from django.db import connection


def _format_datetime(value) -> str:
    if not value:
        return "Nunca"
    try:
        return value.strftime("%d/%m/%Y %H:%M")
    except Exception:
        return str(value)


class DjangoOrmAdminApiKeyRepository:
    def __init__(self) -> None:
        try:
            from app.modules.api_keys.models import ApiKey
        except Exception:
            self.api_key_model = None
            return
        self.api_key_model = ApiKey

    def is_ready(self) -> bool:
        if self.api_key_model is None:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
            return self.api_key_model._meta.db_table in tables
        except Exception:
            return False

    def list_keys(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        if not tenant_id or not self.is_ready():
            return []
        queryset = (
            self.api_key_model._default_manager.filter(tenant_id=tenant_id)
            .select_related("owner")
            .prefetch_related("quotas")
            .order_by("-created_at", "-id")
        )
        return [self._serialize(api_key) for api_key in queryset]

    def _serialize(self, api_key) -> dict[str, object]:
        quotas = list(getattr(api_key, "quotas", []).all())
        active_quotas = [quota for quota in quotas if str(getattr(quota, "status", "") or "") == "active"]
        scopes = list(getattr(api_key, "scopes", []) or [])
        return {
            "id": api_key.id,
            "name": api_key.name,
            "prefix": api_key.prefix,
            "status": api_key.status,
            "status_label": api_key.get_status_display(),
            "scopes_label": ", ".join(scopes) if scopes else "Sem escopos",
            "owner_label": (
                getattr(getattr(api_key, "owner", None), "email", "")
                or api_key.created_by_label
                or "Sem owner"
            ),
            "last_used_at": _format_datetime(api_key.last_used_at),
            "created_at": _format_datetime(api_key.created_at),
            "revoked_at": _format_datetime(api_key.revoked_at) if api_key.revoked_at else "",
            "quota_label": f"{len(active_quotas)} quota(s) ativa(s)" if quotas else "Sem quota configurada",
            "can_revoke": api_key.status == self.api_key_model.Status.ACTIVE,
        }


@dataclass
class AdminApiKeyQueryService:
    repository: DjangoOrmAdminApiKeyRepository

    def list_keys(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        return self.repository.list_keys(tenant_id=tenant_id)


admin_api_key_queries = AdminApiKeyQueryService(repository=DjangoOrmAdminApiKeyRepository())
