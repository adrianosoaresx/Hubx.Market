from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TrackingStatus:
    value: str
    label: str
    terminal: bool = False


TRACKING_STATUS_MISSING = TrackingStatus(value="missing", label="Sem shipment")
TRACKING_STATUS_CREATED = TrackingStatus(value="created", label="Criado")
TRACKING_STATUS_IN_TRANSIT = TrackingStatus(value="in_transit", label="Em trânsito")
TRACKING_STATUS_DELIVERED = TrackingStatus(value="delivered", label="Entregue", terminal=True)
TRACKING_STATUS_CANCELED = TrackingStatus(value="canceled", label="Cancelado", terminal=True)
TRACKING_STATUS_UNKNOWN = TrackingStatus(value="unknown", label="Status externo não mapeado")


_STATUS_MAP = {
    "": TRACKING_STATUS_MISSING,
    "missing": TRACKING_STATUS_MISSING,
    "created": TRACKING_STATUS_CREATED,
    "pending": TRACKING_STATUS_CREATED,
    "posted": TRACKING_STATUS_IN_TRANSIT,
    "sent": TRACKING_STATUS_IN_TRANSIT,
    "shipped": TRACKING_STATUS_IN_TRANSIT,
    "in_transit": TRACKING_STATUS_IN_TRANSIT,
    "in-transit": TRACKING_STATUS_IN_TRANSIT,
    "delivered": TRACKING_STATUS_DELIVERED,
    "done": TRACKING_STATUS_DELIVERED,
    "canceled": TRACKING_STATUS_CANCELED,
    "cancelled": TRACKING_STATUS_CANCELED,
}


def normalize_tracking_status(raw_status: str) -> TrackingStatus:
    normalized = str(raw_status or "").strip().lower().replace(" ", "_")
    return _STATUS_MAP.get(normalized, TRACKING_STATUS_UNKNOWN)
