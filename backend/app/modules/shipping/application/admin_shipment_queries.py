from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Q

from app.modules.shipping.application.shipping_provider_contracts import manual_shipment_provider_gateway


@dataclass(frozen=True)
class AdminShipmentItem:
    order_number: str
    customer_email: str
    order_status: str
    shipping_status: str
    shipment_status: str
    tracking_code: str
    carrier_name: str
    label_status: str
    label_code: str
    label_url: str
    history_summary: tuple[str, ...]
    updated_at: str


class DjangoOrmAdminShipmentQueryRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders.models import Order
        except Exception:
            self.order_model = None
            return
        self.order_model = Order

    def list_shipments(self, *, tenant_id: int | str, search: str = "") -> list[AdminShipmentItem]:
        if self.order_model is None:
            return []
        normalized_tenant_id = str(tenant_id or "").strip()
        if not normalized_tenant_id:
            return []
        queryset = self.order_model._default_manager.filter(tenant_id=normalized_tenant_id).order_by("-created_at", "-id")
        normalized_search = str(search or "").strip().lstrip("#")
        if normalized_search:
            queryset = queryset.filter(
                Q(number__icontains=normalized_search)
                | Q(customer_email__icontains=normalized_search)
                | Q(customer_name__icontains=normalized_search)
            )
        items = []
        for order in queryset[:200]:
            shipment = self._resolve_shipment(order)
            history_summary = self._build_history_summary(shipment)
            tracking_snapshot = manual_shipment_provider_gateway.get_tracking_snapshot(
                tenant_id=normalized_tenant_id,
                order_number=str(order.number),
            )
            items.append(
                AdminShipmentItem(
                    order_number=str(order.number),
                    customer_email=str(order.customer_email or ""),
                    order_status=str(order.status or ""),
                    shipping_status=str(order.shipping_status or ""),
                    shipment_status=tracking_snapshot.normalized_status,
                    tracking_code=tracking_snapshot.tracking_code,
                    carrier_name=tracking_snapshot.carrier_name,
                    label_status=str(getattr(shipment, "label_status", "") or "missing"),
                    label_code=str(getattr(shipment, "label_code", "") or ""),
                    label_url=str(getattr(shipment, "label_url", "") or ""),
                    history_summary=history_summary,
                    updated_at=order.updated_at.strftime("%d/%m/%Y %H:%M") if getattr(order, "updated_at", None) else "",
                )
            )
        return items

    def _resolve_shipment(self, order):
        try:
            return order.shipment
        except Exception:
            return None

    def _build_history_summary(self, shipment) -> tuple[str, ...]:
        if shipment is None:
            return ()
        try:
            history_entries = shipment.history_entries.all()[:3]
        except Exception:
            return ()
        return tuple(
            f"{entry.title} · {entry.created_at.strftime('%d/%m/%Y %H:%M')}"
            for entry in history_entries
        )


@dataclass
class AdminShipmentQueryService:
    repository: DjangoOrmAdminShipmentQueryRepository

    def list_shipments(self, *, tenant_id: int | str, search: str = "") -> list[AdminShipmentItem]:
        return self.repository.list_shipments(tenant_id=tenant_id, search=search)


admin_shipment_queries = AdminShipmentQueryService(repository=DjangoOrmAdminShipmentQueryRepository())
