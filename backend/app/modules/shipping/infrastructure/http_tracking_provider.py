from __future__ import annotations

import json
import time
from dataclasses import dataclass
from dataclasses import replace
from typing import Callable
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.modules.shipping.application.shipping_provider_contracts import (
    TrackingSnapshot,
    manual_shipment_provider_gateway,
)
from app.modules.shipping.application.tracking_status_normalizer import normalize_tracking_status


@dataclass(frozen=True)
class TrackingTransportResult:
    payload: object
    status_code: int | None = None


TrackingTransport = Callable[[str, dict[str, str], float], dict[str, object] | TrackingTransportResult]


def parse_tracking_provider_payload(
    payload: dict[str, object],
    *,
    fallback: TrackingSnapshot,
    provider_http_status: int | None = None,
    provider_latency_ms: int | None = None,
) -> TrackingSnapshot:
    raw_status = str(payload.get("status") or payload.get("provider_status") or fallback.provider_status or "")
    normalized_status = normalize_tracking_status(raw_status)
    tracking_code = str(payload.get("tracking_code") or fallback.tracking_code or "")
    tracking_url = str(payload.get("tracking_url") or fallback.tracking_url or "")
    carrier_name = str(payload.get("carrier_name") or payload.get("carrier") or fallback.carrier_name or "")
    return TrackingSnapshot(
        tracking_code=tracking_code,
        tracking_url=tracking_url,
        carrier_name=carrier_name,
        provider_status=raw_status or fallback.provider_status,
        normalized_status=normalized_status.value,
        status_label=normalized_status.label,
        terminal=normalized_status.terminal,
        provider_http_status=provider_http_status,
        provider_latency_ms=provider_latency_ms,
    )


def urllib_tracking_transport(url: str, headers: dict[str, str], timeout: float) -> TrackingTransportResult:
    request = Request(url, headers=headers, method="GET")
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return TrackingTransportResult(
            payload=payload,
            status_code=getattr(response, "status", None),
        )


@dataclass
class HttpTrackingProviderGateway:
    base_url: str
    token: str = ""
    timeout_seconds: float = 3.0
    transport: TrackingTransport = urllib_tracking_transport

    def get_tracking_snapshot(self, *, tenant_id: int | str, order_number: str) -> TrackingSnapshot:
        fallback = manual_shipment_provider_gateway.get_tracking_snapshot(
            tenant_id=tenant_id,
            order_number=order_number,
        )
        if not fallback.tracking_code:
            return fallback
        endpoint = self._tracking_endpoint(fallback.tracking_code)
        headers = {"Accept": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        started_at = time.perf_counter()
        try:
            result = self.transport(endpoint, headers, self.timeout_seconds)
        except Exception as exc:
            return replace(
                fallback,
                provider_error_code="transport_error",
                provider_error_message=exc.__class__.__name__,
                provider_latency_ms=self._elapsed_ms(started_at),
            )
        provider_latency_ms = self._elapsed_ms(started_at)
        payload, provider_http_status = self._coerce_transport_result(result)
        if not isinstance(payload, dict):
            return replace(
                fallback,
                provider_error_code="invalid_payload",
                provider_error_message="Provider payload is not an object.",
                provider_http_status=provider_http_status,
                provider_latency_ms=provider_latency_ms,
            )
        return parse_tracking_provider_payload(
            payload,
            fallback=fallback,
            provider_http_status=provider_http_status,
            provider_latency_ms=provider_latency_ms,
        )

    def _tracking_endpoint(self, tracking_code: str) -> str:
        return f"{self.base_url.rstrip('/')}/tracking/{quote(str(tracking_code or '').strip())}"

    def _coerce_transport_result(self, result: object) -> tuple[object, int | None]:
        if isinstance(result, TrackingTransportResult):
            return result.payload, result.status_code
        return result, None

    def _elapsed_ms(self, started_at: float) -> int:
        return max(0, int((time.perf_counter() - started_at) * 1000))
