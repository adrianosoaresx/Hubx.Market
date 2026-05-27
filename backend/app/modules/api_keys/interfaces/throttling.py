from __future__ import annotations

from rest_framework.throttling import BaseThrottle

from app.modules.api_keys.application.api_key_quota_enforcement import api_key_quota_enforcement
from app.modules.api_keys.application.api_key_rate_limit import api_key_rate_limit


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _ip_address(request) -> str | None:
    value = _string(getattr(request, "META", {}).get("REMOTE_ADDR", ""), limit=64)
    return value or None


class ApiKeyRateLimitThrottle(BaseThrottle):
    def __init__(self) -> None:
        self.retry_after_seconds = 0

    def allow_request(self, request, view) -> bool:
        auth = getattr(request, "auth", None) or {}
        endpoint = _string(
            getattr(view, "api_key_rate_limit_endpoint", "") or getattr(request, "path", ""),
            limit=120,
        )
        decision = api_key_rate_limit.check_allowed(
            rate_limit_key=auth.get("rate_limit_key"),
            endpoint=endpoint,
            tenant_id=auth.get("tenant_id"),
            api_key_id=auth.get("api_key_id"),
            prefix=auth.get("prefix"),
            limit=getattr(view, "api_key_rate_limit", None),
            window_seconds=getattr(view, "api_key_rate_limit_window_seconds", None),
            request_id=_string(getattr(request, "headers", {}).get("X-Request-ID", ""), limit=120),
            ip_address=_ip_address(request),
        )
        self.retry_after_seconds = decision.retry_after_seconds
        setattr(request, "api_key_rate_limit_decision", decision)
        if not decision.allowed:
            return False

        quota_decision = api_key_quota_enforcement.check_allowed(
            tenant_id=auth.get("tenant_id"),
            api_key_id=auth.get("api_key_id"),
            endpoint=endpoint,
            prefix=auth.get("prefix"),
            request_id=_string(getattr(request, "headers", {}).get("X-Request-ID", ""), limit=120),
            ip_address=_ip_address(request),
        )
        self.retry_after_seconds = quota_decision.retry_after_seconds
        setattr(request, "api_key_quota_decision", quota_decision)
        return quota_decision.allowed

    def wait(self) -> int:
        return self.retry_after_seconds
