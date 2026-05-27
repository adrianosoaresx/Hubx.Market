from __future__ import annotations


def classify_notification_failure(error: object) -> str:
    normalized = str(error or "").strip().lower()
    if not normalized:
        return "unknown"
    if any(token in normalized for token in ("bounce", "bounced", "mailbox", "recipient rejected", "invalid recipient")):
        return "bounce"
    if any(token in normalized for token in ("rate limit", "throttle", "too many")):
        return "provider-rate-limited"
    if any(token in normalized for token in ("timeout", "temporarily", "unavailable", "connection", "offline")):
        return "provider-unavailable"
    if any(token in normalized for token in ("auth", "credential", "permission", "denied")):
        return "provider-authentication"
    return "provider-error"
