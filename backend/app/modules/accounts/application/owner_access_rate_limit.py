from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from django.conf import settings
from django.core.cache import cache


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _cache_fragment(value: object) -> str:
    return sha256(_string(value, limit=255).lower().encode("utf-8")).hexdigest()[:32]


@dataclass(frozen=True)
class OwnerAccessRateLimitDecision:
    allowed: bool
    reason: str
    attempts: int
    max_attempts: int
    retry_after_seconds: int


@dataclass
class OwnerAccessRateLimitService:
    def check_login_allowed(self, *, tenant_id: int | str | None, login: object, ip_address: object) -> OwnerAccessRateLimitDecision:
        lock_key = self._lock_key(tenant_id=tenant_id, login=login, ip_address=ip_address)
        if cache.get(lock_key):
            return OwnerAccessRateLimitDecision(
                allowed=False,
                reason="owner-login-rate-limited",
                attempts=self._current_attempts(tenant_id=tenant_id, login=login, ip_address=ip_address),
                max_attempts=self.max_attempts,
                retry_after_seconds=self.lockout_seconds,
            )
        return OwnerAccessRateLimitDecision(
            allowed=True,
            reason="owner-login-allowed",
            attempts=self._current_attempts(tenant_id=tenant_id, login=login, ip_address=ip_address),
            max_attempts=self.max_attempts,
            retry_after_seconds=0,
        )

    def record_login_failure(self, *, tenant_id: int | str | None, login: object, ip_address: object) -> OwnerAccessRateLimitDecision:
        attempts_key = self._attempts_key(tenant_id=tenant_id, login=login, ip_address=ip_address)
        try:
            cache.add(attempts_key, 0, timeout=self.window_seconds)
            attempts = cache.incr(attempts_key)
        except Exception:
            attempts = int(cache.get(attempts_key) or 0) + 1
            cache.set(attempts_key, attempts, timeout=self.window_seconds)

        if attempts >= self.max_attempts:
            cache.set(
                self._lock_key(tenant_id=tenant_id, login=login, ip_address=ip_address),
                "1",
                timeout=self.lockout_seconds,
            )
            return OwnerAccessRateLimitDecision(
                allowed=False,
                reason="owner-login-rate-limited",
                attempts=attempts,
                max_attempts=self.max_attempts,
                retry_after_seconds=self.lockout_seconds,
            )
        return OwnerAccessRateLimitDecision(
            allowed=True,
            reason="owner-login-failure-recorded",
            attempts=attempts,
            max_attempts=self.max_attempts,
            retry_after_seconds=0,
        )

    def clear_login_failures(self, *, tenant_id: int | str | None, login: object, ip_address: object) -> None:
        cache.delete(self._attempts_key(tenant_id=tenant_id, login=login, ip_address=ip_address))
        cache.delete(self._lock_key(tenant_id=tenant_id, login=login, ip_address=ip_address))

    @property
    def max_attempts(self) -> int:
        return max(int(getattr(settings, "OWNER_LOGIN_RATE_LIMIT_MAX_ATTEMPTS", 5) or 5), 1)

    @property
    def window_seconds(self) -> int:
        return max(int(getattr(settings, "OWNER_LOGIN_RATE_LIMIT_WINDOW_SECONDS", 900) or 900), 1)

    @property
    def lockout_seconds(self) -> int:
        return max(int(getattr(settings, "OWNER_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS", 900) or 900), 1)

    def _current_attempts(self, *, tenant_id: int | str | None, login: object, ip_address: object) -> int:
        return int(cache.get(self._attempts_key(tenant_id=tenant_id, login=login, ip_address=ip_address)) or 0)

    def _attempts_key(self, *, tenant_id: int | str | None, login: object, ip_address: object) -> str:
        return f"owner-login-attempts:{_cache_fragment(tenant_id)}:{_cache_fragment(login)}:{_cache_fragment(ip_address)}"

    def _lock_key(self, *, tenant_id: int | str | None, login: object, ip_address: object) -> str:
        return f"owner-login-lock:{_cache_fragment(tenant_id)}:{_cache_fragment(login)}:{_cache_fragment(ip_address)}"


owner_access_rate_limit = OwnerAccessRateLimitService()
