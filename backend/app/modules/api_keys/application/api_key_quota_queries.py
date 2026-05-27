from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.utils import timezone

from app.modules.api_keys.models import ApiKeyQuota, ApiKeyQuotaUsage


def _window_start(*, window_seconds: int):
    current_time = timezone.now()
    timestamp = int(current_time.timestamp())
    window_timestamp = timestamp - (timestamp % max(int(window_seconds), 1))
    return datetime.fromtimestamp(window_timestamp, tz=timezone.get_current_timezone())


@dataclass
class ApiKeyQuotaQueryService:
    def list_quotas(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        if not tenant_id:
            return []
        quotas = (
            ApiKeyQuota.objects.select_related("api_key")
            .filter(tenant_id=tenant_id)
            .order_by("api_key__name", "endpoint", "id")
        )
        rows: list[dict[str, object]] = []
        for quota in quotas:
            current_usage = self._current_usage(quota=quota)
            rows.append(
                {
                    "id": quota.id,
                    "api_key_id": quota.api_key_id,
                    "api_key_name": quota.api_key.name,
                    "prefix": quota.api_key.prefix,
                    "endpoint": quota.endpoint,
                    "scope": quota.scope,
                    "status": quota.status,
                    "status_label": quota.get_status_display(),
                    "limit": quota.limit,
                    "window_seconds": quota.window_seconds,
                    "window_label": self._window_label(window_seconds=quota.window_seconds),
                    "current_usage": current_usage,
                    "usage_label": f"{current_usage}/{quota.limit}",
                    "updated_at": quota.updated_at.strftime("%Y-%m-%d %H:%M"),
                }
            )
        return rows

    def _current_usage(self, *, quota: ApiKeyQuota) -> int:
        window_start = _window_start(window_seconds=quota.window_seconds)
        usage = ApiKeyQuotaUsage.objects.filter(
            tenant_id=quota.tenant_id,
            api_key_id=quota.api_key_id,
            endpoint=quota.endpoint,
            window_start=window_start,
            window_seconds=quota.window_seconds,
        ).first()
        return int(usage.count if usage else 0)

    def _window_label(self, *, window_seconds: int) -> str:
        if window_seconds == 86400:
            return "Diária"
        if window_seconds == 3600:
            return "Horária"
        return f"{window_seconds}s"


api_key_quota_queries = ApiKeyQuotaQueryService()
