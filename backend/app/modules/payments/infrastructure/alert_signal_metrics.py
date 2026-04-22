from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.utils import timezone


logger = logging.getLogger(__name__)

_CACHE_PREFIX = "payments:alert-signal"
KNOWN_PAYMENT_ALERT_SIGNALS = (
    "provider_intent.failed",
    "hosted_redirect.unavailable",
    "webhook.invalid_signature",
    "webhook.tenant_unavailable",
    "provider_rollout.blocked",
    "payment_confirmation.stock_conflict",
)


def _string(value: object) -> str:
    return str(value or "").strip()


def _signal_key(signal_code: str, suffix: str) -> str:
    return f"{_CACHE_PREFIX}:{_string(signal_code).lower()}:{suffix}"


def _increment_counter(cache_key: str) -> int:
    try:
        cache.add(cache_key, 0, timeout=None)
        return int(cache.incr(cache_key))
    except Exception:
        current_value = int(cache.get(cache_key, 0) or 0) + 1
        cache.set(cache_key, current_value, timeout=None)
        return current_value


def record_payment_alert_signal(
    signal_code: str,
    *,
    tenant_id: int | None = None,
    order_number: str = "",
    attempt_key: str = "",
    provider_code: str = "",
    reason_code: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_signal = _string(signal_code).lower()
    if not normalized_signal:
        return {}

    count = _increment_counter(_signal_key(normalized_signal, "count"))
    snapshot = {
        "signal_code": normalized_signal,
        "count": count,
        "last_at": timezone.now().isoformat(),
        "tenant_id": tenant_id,
        "order_number": _string(order_number),
        "attempt_key": _string(attempt_key),
        "provider_code": _string(provider_code),
        "reason_code": _string(reason_code),
        "metadata": dict(metadata or {}),
    }
    cache.set(_signal_key(normalized_signal, "last"), snapshot, timeout=None)
    logger.warning(
        "payments.alert_signal.raised",
        extra={
            "signal_code": normalized_signal,
            "signal_count": count,
            "tenant_id": tenant_id,
            "order_number": _string(order_number),
            "attempt_key": _string(attempt_key),
            "provider_code": _string(provider_code),
            "reason_code": _string(reason_code),
        },
    )
    return snapshot


def get_payment_alert_signal_snapshot(signal_code: str) -> dict[str, Any]:
    normalized_signal = _string(signal_code).lower()
    if not normalized_signal:
        return {}
    snapshot = dict(cache.get(_signal_key(normalized_signal, "last")) or {})
    if not snapshot:
        count = int(cache.get(_signal_key(normalized_signal, "count"), 0) or 0)
        return {
            "signal_code": normalized_signal,
            "count": count,
            "last_at": "",
            "tenant_id": None,
            "order_number": "",
            "attempt_key": "",
            "provider_code": "",
            "reason_code": "",
            "metadata": {},
        }
    snapshot["count"] = int(cache.get(_signal_key(normalized_signal, "count"), snapshot.get("count", 0)) or 0)
    return snapshot


def list_payment_alert_signal_snapshots() -> list[dict[str, Any]]:
    return [get_payment_alert_signal_snapshot(signal_code) for signal_code in KNOWN_PAYMENT_ALERT_SIGNALS]


def reset_payment_alert_signal(signal_code: str) -> None:
    normalized_signal = _string(signal_code).lower()
    if not normalized_signal:
        return
    cache.delete_many(
        [
            _signal_key(normalized_signal, "count"),
            _signal_key(normalized_signal, "last"),
        ]
    )
