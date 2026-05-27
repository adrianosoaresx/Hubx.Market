from __future__ import annotations

import time
from dataclasses import dataclass
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache

from app.modules.api_keys.application.api_key_public_endpoint_metrics import api_key_public_endpoint_metrics
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _cache_fragment(value: object) -> str:
    return sha256(_string(value, limit=255).lower().encode("utf-8")).hexdigest()[:32]


def _positive_int(value: object, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(parsed, 1)


@dataclass(frozen=True)
class ApiKeyRateLimitDecision:
    allowed: bool
    reason: str
    count: int
    limit: int
    window_seconds: int
    retry_after_seconds: int


@dataclass
class ApiKeyRateLimitService:
    def check_allowed(
        self,
        *,
        rate_limit_key: object,
        endpoint: object,
        tenant_id: int | str | None,
        api_key_id: int | str | None = None,
        prefix: object = "",
        limit: int | None = None,
        window_seconds: int | None = None,
        request_id: object = "",
        ip_address: str | None = None,
    ) -> ApiKeyRateLimitDecision:
        resolved_limit = _positive_int(limit, default=self.default_limit) if limit is not None else self.default_limit
        resolved_window = (
            _positive_int(window_seconds, default=self.default_window_seconds)
            if window_seconds is not None
            else self.default_window_seconds
        )
        normalized_rate_limit_key = _string(rate_limit_key, limit=180)
        normalized_endpoint = _string(endpoint, limit=120)
        if not normalized_rate_limit_key or not normalized_endpoint:
            return self._denied(
                reason="api-key-rate-limit-identity-missing",
                count=0,
                limit=resolved_limit,
                window_seconds=resolved_window,
                retry_after_seconds=resolved_window,
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                prefix=prefix,
                endpoint=normalized_endpoint,
                request_id=request_id,
                ip_address=ip_address,
            )

        cache_key = self._cache_key(
            rate_limit_key=normalized_rate_limit_key,
            endpoint=normalized_endpoint,
            window_seconds=resolved_window,
        )
        retry_after_seconds = self._retry_after_seconds(window_seconds=resolved_window)
        try:
            cache.add(cache_key, 0, timeout=resolved_window)
            count = int(cache.incr(cache_key))
        except Exception:
            return self._denied(
                reason="api-key-rate-limit-cache-unavailable",
                count=0,
                limit=resolved_limit,
                window_seconds=resolved_window,
                retry_after_seconds=retry_after_seconds,
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                prefix=prefix,
                endpoint=normalized_endpoint,
                request_id=request_id,
                ip_address=ip_address,
            )

        if count > resolved_limit:
            return self._denied(
                reason="api-key-rate-limited",
                count=count,
                limit=resolved_limit,
                window_seconds=resolved_window,
                retry_after_seconds=retry_after_seconds,
                tenant_id=tenant_id,
                api_key_id=api_key_id,
                prefix=prefix,
                endpoint=normalized_endpoint,
                request_id=request_id,
                ip_address=ip_address,
            )
        return ApiKeyRateLimitDecision(
            allowed=True,
            reason="api-key-rate-limit-allowed",
            count=count,
            limit=resolved_limit,
            window_seconds=resolved_window,
            retry_after_seconds=0,
        )

    @property
    def default_limit(self) -> int:
        return _positive_int(getattr(settings, "API_KEYS_RATE_LIMIT_DEFAULT_LIMIT", 120), default=120)

    @property
    def default_window_seconds(self) -> int:
        return _positive_int(getattr(settings, "API_KEYS_RATE_LIMIT_DEFAULT_WINDOW_SECONDS", 60), default=60)

    def _cache_key(self, *, rate_limit_key: str, endpoint: str, window_seconds: int) -> str:
        window = int(time.time() // window_seconds)
        return f"api-key-rate-limit:{_cache_fragment(rate_limit_key)}:{_cache_fragment(endpoint)}:{window}"

    def _retry_after_seconds(self, *, window_seconds: int) -> int:
        elapsed = int(time.time()) % window_seconds
        return max(window_seconds - elapsed, 1)

    def _denied(
        self,
        *,
        reason: str,
        count: int,
        limit: int,
        window_seconds: int,
        retry_after_seconds: int,
        tenant_id: int | str | None,
        api_key_id: int | str | None,
        prefix: object,
        endpoint: str,
        request_id: object,
        ip_address: str | None,
    ) -> ApiKeyRateLimitDecision:
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="api_keys",
            action="api_key.rate_limited",
            entity_type="ApiKey",
            entity_id=str(api_key_id or ""),
            actor_label="api_key",
            summary=f"API key excedeu limite: {_string(reason, limit=80)}",
            metadata={
                "reason": _string(reason, limit=80),
                "key_id": str(api_key_id or ""),
                "prefix": _string(prefix, limit=24),
                "endpoint": _string(endpoint, limit=120),
                "count": count,
                "limit": limit,
                "window_seconds": window_seconds,
                "retry_after_seconds": retry_after_seconds,
            },
            request_id=_string(request_id, limit=120),
            ip_address=ip_address,
        )
        api_key_public_endpoint_metrics.record_rate_limited(
            tenant_id=tenant_id or "",
            endpoint=endpoint,
            prefix=prefix,
        )
        return ApiKeyRateLimitDecision(
            allowed=False,
            reason=reason,
            count=count,
            limit=limit,
            window_seconds=window_seconds,
            retry_after_seconds=retry_after_seconds,
        )


api_key_rate_limit = ApiKeyRateLimitService()
