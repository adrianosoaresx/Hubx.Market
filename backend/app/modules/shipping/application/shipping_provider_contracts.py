from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.shipping.application.tracking_status_normalizer import normalize_tracking_status


@dataclass(frozen=True)
class TrackingSnapshot:
    tracking_code: str
    tracking_url: str
    carrier_name: str
    provider_status: str
    normalized_status: str
    status_label: str
    terminal: bool = False
    provider_error_code: str = ""
    provider_error_message: str = ""
    provider_http_status: int | None = None
    provider_latency_ms: int | None = None

    @property
    def has_tracking(self) -> bool:
        return bool(self.tracking_code or self.tracking_url or self.carrier_name)

    @property
    def has_provider_error(self) -> bool:
        return bool(self.provider_error_code)


class ShippingProviderGateway(Protocol):
    def get_tracking_snapshot(
        self,
        *,
        tenant_id: int | str,
        order_number: str,
    ) -> TrackingSnapshot:
        ...


class ManualShipmentProviderGateway:
    def get_tracking_snapshot(
        self,
        *,
        tenant_id: int | str,
        order_number: str,
    ) -> TrackingSnapshot:
        try:
            from app.modules.shipping.models import Shipment
        except Exception:
            return self._missing_snapshot()

        normalized_tenant_id = str(tenant_id or "").strip()
        normalized_order_number = str(order_number or "").strip().lstrip("#")
        if not normalized_tenant_id or not normalized_order_number:
            return self._missing_snapshot()

        shipment = (
            Shipment.objects.filter(
                tenant_id=normalized_tenant_id,
                order__number=normalized_order_number,
            )
            .select_related("order")
            .first()
        )
        if shipment is None:
            return self._missing_snapshot()
        normalized_status = normalize_tracking_status(str(shipment.status or ""))

        return TrackingSnapshot(
            tracking_code=str(shipment.tracking_code or ""),
            tracking_url=str(shipment.tracking_url or ""),
            carrier_name=str(shipment.carrier_name or ""),
            provider_status=str(shipment.status or ""),
            normalized_status=normalized_status.value,
            status_label=normalized_status.label,
            terminal=normalized_status.terminal,
        )

    def _missing_snapshot(self) -> TrackingSnapshot:
        normalized_status = normalize_tracking_status("missing")
        return TrackingSnapshot(
            tracking_code="",
            tracking_url="",
            carrier_name="",
            provider_status="missing",
            normalized_status=normalized_status.value,
            status_label=normalized_status.label,
            terminal=normalized_status.terminal,
        )


manual_shipment_provider_gateway = ManualShipmentProviderGateway()
