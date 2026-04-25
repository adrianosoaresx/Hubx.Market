from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db.models import Avg, Count

from app.modules.shipping.models import Shipment, ShipmentStatusHistory


def _string(value: object) -> str:
    return str(value or "").strip()


class ShippingMetricsRepository(Protocol):
    def list_shipment_status_counts(self) -> list[dict[str, object]]:
        ...

    def list_history_event_counts(self) -> list[dict[str, object]]:
        ...

    def list_provider_http_status_counts(self) -> list[dict[str, object]]:
        ...

    def list_provider_latency_averages(self) -> list[dict[str, object]]:
        ...


class DjangoOrmShippingMetricsRepository:
    def list_shipment_status_counts(self) -> list[dict[str, object]]:
        return list(
            Shipment.objects.values("tenant_id", "status")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "status")
        )

    def list_history_event_counts(self) -> list[dict[str, object]]:
        return list(
            ShipmentStatusHistory.objects.values("tenant_id", "event_type")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "event_type")
        )

    def list_provider_http_status_counts(self) -> list[dict[str, object]]:
        return list(
            ShipmentStatusHistory.objects.exclude(provider_http_status__isnull=True)
            .values("tenant_id", "provider_http_status")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "provider_http_status")
        )

    def list_provider_latency_averages(self) -> list[dict[str, object]]:
        return list(
            ShipmentStatusHistory.objects.exclude(provider_latency_ms__isnull=True)
            .values("tenant_id", "event_type")
            .annotate(latency_ms=Avg("provider_latency_ms"))
            .order_by("tenant_id", "event_type")
        )


@dataclass
class ShippingMetricsQueryService:
    repository: ShippingMetricsRepository

    def export_prometheus_metrics(self) -> str:
        lines = [
            "# HELP hubx_shipping_shipment_total Total de shipments por tenant e status.",
            "# TYPE hubx_shipping_shipment_total gauge",
        ]
        for row in self.repository.list_shipment_status_counts():
            tenant_id = _string(row.get("tenant_id"))
            status = _string(row.get("status"))
            count = int(row.get("count", 0) or 0)
            lines.append(f'hubx_shipping_shipment_total{{tenant_id="{tenant_id}",status="{status}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_shipping_history_event_total Total de eventos de histórico de shipping por tenant e tipo.",
                "# TYPE hubx_shipping_history_event_total counter",
            ]
        )
        for row in self.repository.list_history_event_counts():
            tenant_id = _string(row.get("tenant_id"))
            event_type = _string(row.get("event_type"))
            count = int(row.get("count", 0) or 0)
            lines.append(f'hubx_shipping_history_event_total{{tenant_id="{tenant_id}",event_type="{event_type}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_shipping_provider_http_status_total Total de respostas HTTP do provider por tenant e status.",
                "# TYPE hubx_shipping_provider_http_status_total counter",
            ]
        )
        for row in self.repository.list_provider_http_status_counts():
            tenant_id = _string(row.get("tenant_id"))
            http_status = _string(row.get("provider_http_status"))
            count = int(row.get("count", 0) or 0)
            lines.append(f'hubx_shipping_provider_http_status_total{{tenant_id="{tenant_id}",http_status="{http_status}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_shipping_provider_latency_ms_avg Latência média do provider de shipping por tenant e evento.",
                "# TYPE hubx_shipping_provider_latency_ms_avg gauge",
            ]
        )
        for row in self.repository.list_provider_latency_averages():
            tenant_id = _string(row.get("tenant_id"))
            event_type = _string(row.get("event_type"))
            latency_ms = float(row.get("latency_ms", 0) or 0)
            lines.append(f'hubx_shipping_provider_latency_ms_avg{{tenant_id="{tenant_id}",event_type="{event_type}"}} {latency_ms:.2f}')
        return "\n".join(lines) + "\n"


shipping_metrics_queries = ShippingMetricsQueryService(repository=DjangoOrmShippingMetricsRepository())
