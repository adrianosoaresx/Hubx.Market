from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.utils import timezone


OWNER_SESSION_KIND_KEY = "hubx_owner_session_kind"
OWNER_SESSION_REMEMBERED_KEY = "hubx_owner_session_remembered"
OWNER_SESSION_EXPIRES_AT_KEY = "hubx_owner_session_expires_at"


@dataclass(frozen=True)
class OwnerSessionPolicyResult:
    expiry_seconds: int
    remembered: bool
    expires_at: str


def _setting_seconds(name: str, default: int) -> int:
    value = int(getattr(settings, name, default))
    return max(value, 60)


def apply_owner_session_policy(request, *, remember_me: bool) -> OwnerSessionPolicyResult:
    expiry_seconds = (
        _setting_seconds("OWNER_SESSION_REMEMBER_SECONDS", 12 * 60 * 60)
        if remember_me
        else _setting_seconds("OWNER_SESSION_IDLE_SECONDS", 2 * 60 * 60)
    )
    expires_at = timezone.now() + timezone.timedelta(seconds=expiry_seconds)
    request.session.set_expiry(expiry_seconds)
    request.session[OWNER_SESSION_KIND_KEY] = "owner"
    request.session[OWNER_SESSION_REMEMBERED_KEY] = bool(remember_me)
    request.session[OWNER_SESSION_EXPIRES_AT_KEY] = expires_at.isoformat()
    return OwnerSessionPolicyResult(
        expiry_seconds=expiry_seconds,
        remembered=bool(remember_me),
        expires_at=expires_at.isoformat(),
    )
