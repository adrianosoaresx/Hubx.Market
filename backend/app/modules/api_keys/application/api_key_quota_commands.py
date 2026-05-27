from __future__ import annotations

from dataclasses import dataclass

from app.modules.api_keys.models import ApiKey, ApiKeyQuota
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, 1)


@dataclass
class ApiKeyQuotaCommandService:
    def upsert_quota(
        self,
        *,
        tenant_id: int | str | None,
        api_key_id: int | str | None,
        endpoint: object,
        limit: object = 10000,
        window_seconds: object = 86400,
        scope: object = "read:catalog",
        status: object = ApiKeyQuota.Status.ACTIVE,
        actor_label: object = "",
    ) -> dict[str, object]:
        normalized_endpoint = _string(endpoint, limit=120)
        normalized_scope = _string(scope, limit=80) or "read:catalog"
        normalized_status = _string(status, limit=16) or ApiKeyQuota.Status.ACTIVE
        if not tenant_id:
            return {"result": "api-key-quota-tenant-required", "errors": {"tenant_id": "required"}}
        if not api_key_id:
            return {"result": "api-key-quota-api-key-required", "errors": {"api_key_id": "required"}}
        if not normalized_endpoint:
            return {"result": "api-key-quota-invalid", "errors": {"endpoint": "required"}}
        if normalized_status not in ApiKeyQuota.Status.values:
            return {"result": "api-key-quota-invalid", "errors": {"status": "invalid"}}

        api_key = ApiKey.objects.filter(pk=api_key_id, tenant_id=tenant_id).first()
        if api_key is None:
            return {"result": "api-key-quota-api-key-not-found", "errors": {"api_key_id": "not-found"}}

        resolved_limit = _positive_int(limit, default=10000)
        resolved_window = _positive_int(window_seconds, default=86400)
        quota, created = ApiKeyQuota.objects.update_or_create(
            tenant_id=tenant_id,
            api_key=api_key,
            endpoint=normalized_endpoint,
            defaults={
                "scope": normalized_scope,
                "limit": resolved_limit,
                "window_seconds": resolved_window,
                "status": normalized_status,
                "updated_by_label": _string(actor_label, limit=180),
            },
        )
        if created and not quota.created_by_label:
            quota.created_by_label = _string(actor_label, limit=180)
            quota.save(update_fields=("created_by_label",))

        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="api_keys",
            action="api_key.quota_upserted",
            entity_type="ApiKeyQuota",
            entity_id=str(quota.id),
            actor_label=_string(actor_label, limit=180),
            summary=f"Quota de API key atualizada para {normalized_endpoint}",
            metadata={
                "api_key_id": str(api_key.id),
                "prefix": api_key.prefix,
                "endpoint": normalized_endpoint,
                "scope": normalized_scope,
                "limit": resolved_limit,
                "window_seconds": resolved_window,
                "status": normalized_status,
            },
        )
        return {
            "result": "api-key-quota-created" if created else "api-key-quota-updated",
            "quota": self._serialize(quota=quota),
        }

    def _serialize(self, *, quota: ApiKeyQuota) -> dict[str, object]:
        return {
            "id": quota.id,
            "tenant_id": quota.tenant_id,
            "api_key_id": quota.api_key_id,
            "endpoint": quota.endpoint,
            "scope": quota.scope,
            "limit": quota.limit,
            "window_seconds": quota.window_seconds,
            "status": quota.status,
        }

api_key_quota_commands = ApiKeyQuotaCommandService()
