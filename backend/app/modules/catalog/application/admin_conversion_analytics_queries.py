from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count
from django.utils import timezone

from app.modules.catalog.models import StorefrontDiscoveryEventLog


EVENT_LABELS = {
    "catalog.discovery_viewed": "Listagem vista",
    "catalog.search_performed": "Busca realizada",
    "catalog.facets_applied": "Filtro/facet aplicado",
    "catalog.sort_changed": "Ordenação alterada",
    "catalog.product_detail_viewed": "PDP visto",
    "catalog.pdp_cta_intent": "CTA do PDP",
}


def _event_label(event_name: str) -> str:
    return EVENT_LABELS.get(event_name, event_name)


def _format_timestamp(value) -> str:
    if not value:
        return ""
    local_value = timezone.localtime(value)
    return local_value.strftime("%d/%m/%Y às %H:%M")


def _payload_summary(payload: dict[str, object]) -> str:
    parts = []
    if payload.get("query"):
        parts.append(f'busca “{payload["query"]}”')
    if payload.get("category"):
        parts.append(f'categoria {payload["category"]}')
    if payload.get("availability"):
        parts.append(f'disponibilidade {payload["availability"]}')
    if payload.get("offer"):
        parts.append("somente ofertas")
    if payload.get("sort"):
        parts.append(f'ordenação {payload["sort"]}')
    if payload.get("result_count") is not None:
        parts.append(f'{payload["result_count"]} resultado(s)')
    if payload.get("product_slug"):
        parts.append(f'produto {payload["product_slug"]}')
    if payload.get("cta_intent"):
        parts.append(f'CTA {payload["cta_intent"]}')
    if payload.get("cta_result"):
        parts.append(f'resultado {payload["cta_result"]}')
    if payload.get("variant_sku"):
        parts.append(f'SKU {payload["variant_sku"]}')
    return " · ".join(parts) or "Evento sem detalhes públicos adicionais."


@dataclass
class AdminConversionAnalyticsQueryService:
    def _queryset(self, *, tenant_id: int | str | None):
        if not tenant_id:
            return StorefrontDiscoveryEventLog.objects.none()
        return StorefrontDiscoveryEventLog.objects.filter(tenant_id=tenant_id)

    def event_options(self, *, tenant_id: int | str | None) -> list[dict[str, str]]:
        event_names = (
            self._queryset(tenant_id=tenant_id)
            .order_by("event_name")
            .values_list("event_name", flat=True)
            .distinct()
        )
        return [{"value": event_name, "label": _event_label(event_name)} for event_name in event_names]

    def summary(self, *, tenant_id: int | str | None, event_name: str = "") -> dict[str, object]:
        queryset = self._queryset(tenant_id=tenant_id)
        event_name = str(event_name or "").strip()
        filtered_queryset = queryset.filter(event_name=event_name) if event_name else queryset
        counters = [
            {
                "event_name": item["event_name"],
                "label": _event_label(item["event_name"]),
                "count": item["count"],
            }
            for item in queryset.values("event_name").annotate(count=Count("id")).order_by("event_name")
        ]
        recent_events = [
            {
                "event_name": event.event_name,
                "label": _event_label(event.event_name),
                "path": event.path,
                "payload_summary": _payload_summary(event.payload or {}),
                "occurred_at": _format_timestamp(event.occurred_at),
            }
            for event in filtered_queryset.order_by("-occurred_at", "-id")[:20]
        ]
        return {
            "total_count": queryset.count(),
            "filtered_count": filtered_queryset.count(),
            "counters": counters,
            "recent_events": recent_events,
            "event_selected": event_name,
        }


admin_conversion_analytics_queries = AdminConversionAnalyticsQueryService()
