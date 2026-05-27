from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache


REQUEST_RESULTS = ("success", "auth_failed", "rate_limited", "quota_exceeded")
PUBLIC_ENDPOINT_FLAGS = (
    ("catalog.products.list", "API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED"),
    ("catalog.products.detail", "API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED"),
)


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _label(value: object) -> str:
    return _string(value, limit=120).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "_")


def _metric_key(metric: str, *parts: object) -> str:
    normalized = ":".join(_string(part, limit=120).replace(":", "_") for part in parts)
    return f"api-key-public-metrics:{metric}:{normalized}"


def _increment(cache_key: str) -> int:
    try:
        cache.add(cache_key, 0, timeout=None)
        return int(cache.incr(cache_key))
    except Exception:
        current_value = int(cache.get(cache_key, 0) or 0) + 1
        cache.set(cache_key, current_value, timeout=None)
        return current_value


@dataclass
class ApiKeyPublicEndpointMetricsService:
    def record_request(self, *, tenant_id: object, endpoint: object, result: object) -> None:
        normalized_result = _string(result, limit=40) or "unknown"
        if normalized_result not in REQUEST_RESULTS:
            normalized_result = "unknown"
        _increment(_metric_key("request", tenant_id, endpoint, normalized_result))

    def record_auth_failure(self, *, tenant_id: object, endpoint: object, reason: object) -> None:
        normalized_reason = _string(reason, limit=80) or "unknown"
        _increment(_metric_key("auth_failure", tenant_id, endpoint, normalized_reason))
        self.record_request(tenant_id=tenant_id, endpoint=endpoint, result="auth_failed")

    def record_rate_limited(self, *, tenant_id: object, endpoint: object, prefix: object) -> None:
        _increment(_metric_key("rate_limited", tenant_id, endpoint, prefix))
        self.record_request(tenant_id=tenant_id, endpoint=endpoint, result="rate_limited")

    def record_quota_exceeded(self, *, tenant_id: object, endpoint: object, prefix: object) -> None:
        _increment(_metric_key("quota_exceeded", tenant_id, endpoint, prefix))
        self.record_request(tenant_id=tenant_id, endpoint=endpoint, result="quota_exceeded")

    def export_prometheus_metrics(self) -> str:
        lines = [
            "# HELP hubx_api_key_public_request_total Total de requests em endpoints públicos por API key.",
            "# TYPE hubx_api_key_public_request_total counter",
        ]
        for key in sorted(self._keys("request")):
            _, tenant_id, endpoint, result = self._split_key(key, expected_parts=4)
            lines.append(
                f'hubx_api_key_public_request_total{{tenant_id="{_label(tenant_id)}",endpoint="{_label(endpoint)}",result="{_label(result)}"}} '
                f"{int(cache.get(key, 0) or 0)}"
            )

        lines.extend(
            [
                "# HELP hubx_api_key_auth_failure_total Total de falhas de autenticação em endpoints públicos por API key.",
                "# TYPE hubx_api_key_auth_failure_total counter",
            ]
        )
        for key in sorted(self._keys("auth_failure")):
            _, tenant_id, endpoint, reason = self._split_key(key, expected_parts=4)
            lines.append(
                f'hubx_api_key_auth_failure_total{{tenant_id="{_label(tenant_id)}",endpoint="{_label(endpoint)}",reason="{_label(reason)}"}} '
                f"{int(cache.get(key, 0) or 0)}"
            )

        lines.extend(
            [
                "# HELP hubx_api_key_rate_limited_total Total de requests limitadas em endpoints públicos por API key.",
                "# TYPE hubx_api_key_rate_limited_total counter",
            ]
        )
        for key in sorted(self._keys("rate_limited")):
            _, tenant_id, endpoint, prefix = self._split_key(key, expected_parts=4)
            lines.append(
                f'hubx_api_key_rate_limited_total{{tenant_id="{_label(tenant_id)}",endpoint="{_label(endpoint)}",prefix="{_label(prefix)}"}} '
                f"{int(cache.get(key, 0) or 0)}"
            )

        lines.extend(
            [
                "# HELP hubx_api_key_quota_exceeded_total Total de requests bloqueadas por quota comercial em endpoints públicos por API key.",
                "# TYPE hubx_api_key_quota_exceeded_total counter",
            ]
        )
        for key in sorted(self._keys("quota_exceeded")):
            _, tenant_id, endpoint, prefix = self._split_key(key, expected_parts=4)
            lines.append(
                f'hubx_api_key_quota_exceeded_total{{tenant_id="{_label(tenant_id)}",endpoint="{_label(endpoint)}",prefix="{_label(prefix)}"}} '
                f"{int(cache.get(key, 0) or 0)}"
            )

        lines.extend(
            [
                "# HELP hubx_api_key_public_endpoint_enabled Estado operacional de endpoints públicos por API key.",
                "# TYPE hubx_api_key_public_endpoint_enabled gauge",
            ]
        )
        for endpoint, setting_name in PUBLIC_ENDPOINT_FLAGS:
            enabled = 1 if getattr(settings, setting_name, False) else 0
            lines.append(f'hubx_api_key_public_endpoint_enabled{{endpoint="{_label(endpoint)}"}} {enabled}')
        return "\n".join(lines) + "\n"

    def _keys(self, metric: str) -> list[str]:
        try:
            raw_cache = getattr(cache, "_cache", {})
            keys = [str(key) for key in raw_cache.keys()]
        except Exception:
            keys = []
        prefix = f":1:{_metric_key(metric)}"
        fallback_prefix = _metric_key(metric)
        return [
            key.removeprefix(":1:")
            for key in keys
            if key.startswith(prefix) or key.startswith(fallback_prefix)
        ]

    def _split_key(self, key: str, *, expected_parts: int) -> tuple[str, ...]:
        parts = ["", *key.split(":")[2:]]
        if len(parts) < expected_parts:
            return tuple(parts + [""] * (expected_parts - len(parts)))
        return tuple(parts[:expected_parts])


api_key_public_endpoint_metrics = ApiKeyPublicEndpointMetricsService()
