from __future__ import annotations

from celery import shared_task

from app.modules.shipping.application.shipment_tracking_sync import shipment_tracking_sync
from app.modules.shipping.application.shipping_provider_settings import shipping_provider_settings
from app.modules.shipping.models import Shipment


@shared_task(name="shipping.sync_shipment_tracking")
def sync_shipment_tracking_task(*, tenant_id: int | str, order_number: str) -> str:
    provider_gateway = shipping_provider_settings.get_gateway_for_tenant(tenant_id=tenant_id)
    return shipment_tracking_sync.sync_tracking_snapshot(
        tenant_id=tenant_id,
        order_number=order_number,
        provider_gateway=provider_gateway,
    )


@shared_task(name="shipping.sync_pending_shipments_tracking")
def sync_pending_shipments_tracking_task(*, tenant_id: int | str = "", limit: int = 100) -> dict[str, int]:
    normalized_tenant_id = str(tenant_id or "").strip()
    safe_limit = max(1, min(int(limit or 100), 250))
    queryset = (
        Shipment.objects.select_related("order")
        .filter(status__in=[Shipment.Status.CREATED, Shipment.Status.SENT])
        .order_by("tenant_id", "id")
    )
    if normalized_tenant_id:
        queryset = queryset.filter(tenant_id=normalized_tenant_id)

    counters: dict[str, int] = {}
    gateways_by_tenant: dict[str, object] = {}
    for shipment in queryset[:safe_limit]:
        shipment_tenant_id = str(shipment.tenant_id)
        if shipment_tenant_id not in gateways_by_tenant:
            gateways_by_tenant[shipment_tenant_id] = shipping_provider_settings.get_gateway_for_tenant(tenant_id=shipment_tenant_id)
        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=shipment_tenant_id,
            order_number=shipment.order.number,
            provider_gateway=gateways_by_tenant[shipment_tenant_id],
        )
        counters[result] = counters.get(result, 0) + 1
    return counters
