from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from app.modules.api_keys.application.api_key_public_endpoint_metrics import api_key_public_endpoint_metrics
from app.modules.api_keys.models import ApiKeyQuota, ApiKeyQuotaUsage
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass(frozen=True)
class ApiKeyQuotaDecision:
    allowed: bool
    reason: str
    count: int
    limit: int
    window_seconds: int
    retry_after_seconds: int
    quota_id: int | None = None


@dataclass
class ApiKeyQuotaEnforcementService:
    def check_allowed(
        self,
        *,
        tenant_id: int | str | None,
        api_key_id: int | str | None,
        endpoint: object,
        prefix: object = "",
        request_id: object = "",
        ip_address: str | None = None,
        now: datetime | None = None,
    ) -> ApiKeyQuotaDecision:
        normalized_endpoint = _string(endpoint, limit=120)
        if not tenant_id or not api_key_id or not normalized_endpoint:
            return ApiKeyQuotaDecision(
                allowed=True,
                reason="api-key-quota-not-applicable",
                count=0,
                limit=0,
                window_seconds=0,
                retry_after_seconds=0,
            )

        quota = (
            ApiKeyQuota.objects.filter(
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                endpoint=normalized_endpoint,
                status=ApiKeyQuota.Status.ACTIVE,
            )
            .order_by("id")
            .first()
        )
        if quota is None:
            return ApiKeyQuotaDecision(
                allowed=True,
                reason="api-key-quota-not-configured",
                count=0,
                limit=0,
                window_seconds=0,
                retry_after_seconds=0,
            )

        current_time = now or timezone.now()
        window_start = self._window_start(current_time=current_time, window_seconds=quota.window_seconds)
        retry_after_seconds = self._retry_after_seconds(current_time=current_time, window_seconds=quota.window_seconds)
        with transaction.atomic():
            usage, _ = ApiKeyQuotaUsage.objects.select_for_update().get_or_create(
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                endpoint=normalized_endpoint,
                window_start=window_start,
                window_seconds=quota.window_seconds,
                defaults={"quota": quota, "count": 0},
            )
            if usage.quota_id != quota.id:
                usage.quota = quota
            usage.count += 1
            usage.save(update_fields=("quota", "count", "updated_at"))
            count = usage.count

        if count > quota.limit:
            self._record_quota_exceeded(
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                quota=quota,
                count=count,
                prefix=prefix,
                request_id=request_id,
                ip_address=ip_address,
                retry_after_seconds=retry_after_seconds,
            )
            return ApiKeyQuotaDecision(
                allowed=False,
                reason="api-key-quota-exceeded",
                count=count,
                limit=quota.limit,
                window_seconds=quota.window_seconds,
                retry_after_seconds=retry_after_seconds,
                quota_id=quota.id,
            )

        return ApiKeyQuotaDecision(
            allowed=True,
            reason="api-key-quota-allowed",
            count=count,
            limit=quota.limit,
            window_seconds=quota.window_seconds,
            retry_after_seconds=0,
            quota_id=quota.id,
        )

    def _window_start(self, *, current_time: datetime, window_seconds: int) -> datetime:
        timestamp = int(current_time.timestamp())
        window_timestamp = timestamp - (timestamp % max(int(window_seconds), 1))
        return datetime.fromtimestamp(window_timestamp, tz=timezone.get_current_timezone())

    def _retry_after_seconds(self, *, current_time: datetime, window_seconds: int) -> int:
        elapsed = int(current_time.timestamp()) % max(int(window_seconds), 1)
        return max(int(window_seconds) - elapsed, 1)

    def _record_quota_exceeded(
        self,
        *,
        tenant_id: int | str | None,
        api_key_id: int | str | None,
        quota: ApiKeyQuota,
        count: int,
        prefix: object,
        request_id: object,
        ip_address: str | None,
        retry_after_seconds: int,
    ) -> None:
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="api_keys",
            action="api_key.quota_exceeded",
            entity_type="ApiKeyQuota",
            entity_id=str(quota.id),
            actor_label="api_key",
            summary=f"API key excedeu quota comercial: {_string(quota.endpoint, limit=80)}",
            metadata={
                "api_key_id": str(api_key_id or ""),
                "quota_id": str(quota.id),
                "prefix": _string(prefix, limit=24),
                "endpoint": quota.endpoint,
                "count": count,
                "limit": quota.limit,
                "window_seconds": quota.window_seconds,
                "retry_after_seconds": retry_after_seconds,
            },
            request_id=_string(request_id, limit=120),
            ip_address=ip_address,
        )
        api_key_public_endpoint_metrics.record_quota_exceeded(
            tenant_id=tenant_id or "",
            endpoint=quota.endpoint,
            prefix=prefix,
        )


api_key_quota_enforcement = ApiKeyQuotaEnforcementService()
