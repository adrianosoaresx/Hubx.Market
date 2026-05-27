from __future__ import annotations

from dataclasses import dataclass

from app.modules.catalog.models import StorefrontDiscoveryEventLog


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@dataclass
class StorefrontConversionInsightsQueryService:
    def baseline(self, *, tenant_id: int | str | None) -> dict[str, object]:
        events = self._events(tenant_id=tenant_id)
        counts: dict[str, int] = {}
        for event in events:
            counts[event.event_name] = counts.get(event.event_name, 0) + 1
        listing_views = counts.get("catalog.discovery_viewed", 0)
        pdp_views = counts.get("catalog.product_detail_viewed", 0)
        cta_intents = counts.get("catalog.pdp_cta_intent", 0)
        successful_ctas = sum(
            1
            for event in events
            if event.event_name == "catalog.pdp_cta_intent"
            and _string((event.payload or {}).get("cta_result")) in {"cart-item-added", "cart-item-added-idempotent", "checkout-activated"}
        )
        return {
            "tenant_id": _string(tenant_id, limit=40),
            "total_events": len(events),
            "event_counts": counts,
            "listing_views": listing_views,
            "pdp_views": pdp_views,
            "cta_intents": cta_intents,
            "successful_ctas": successful_ctas,
            "pdp_view_rate": self._ratio(pdp_views, listing_views),
            "cta_success_rate": self._ratio(successful_ctas, cta_intents),
        }

    def pdp_funnel(self, *, tenant_id: int | str | None) -> dict[str, object]:
        product_stats: dict[str, dict[str, int]] = {}
        for event in self._events(tenant_id=tenant_id):
            payload = event.payload or {}
            product_slug = _string(payload.get("product_slug"), limit=120)
            if not product_slug:
                continue
            stats = product_stats.setdefault(product_slug, {"pdp_views": 0, "cta_intents": 0, "successful_ctas": 0, "unavailable_ctas": 0})
            if event.event_name == "catalog.product_detail_viewed":
                stats["pdp_views"] += 1
            if event.event_name == "catalog.pdp_cta_intent":
                stats["cta_intents"] += 1
                result = _string(payload.get("cta_result"), limit=80)
                if result in {"cart-item-added", "cart-item-added-idempotent", "checkout-activated"}:
                    stats["successful_ctas"] += 1
                if result in {"unavailable", "cart-item-stock-unavailable", "cart-item-stock-conflict"}:
                    stats["unavailable_ctas"] += 1
        return {"products": product_stats}

    def search_facet_dropoff(self, *, tenant_id: int | str | None) -> dict[str, object]:
        zero_result_events = []
        for event in self._events(tenant_id=tenant_id):
            if event.event_name not in {"catalog.search_performed", "catalog.facets_applied"}:
                continue
            payload = event.payload or {}
            if _safe_int(payload.get("result_count")) == 0:
                zero_result_events.append(
                    {
                        "event_name": event.event_name,
                        "query": _string(payload.get("query"), limit=120),
                        "category": _string(payload.get("category"), limit=120),
                        "availability": _string(payload.get("availability"), limit=80),
                        "sort": _string(payload.get("sort"), limit=80),
                    }
                )
        return {
            "zero_result_count": len(zero_result_events),
            "zero_result_events": zero_result_events[:20],
        }

    def product_priority_deltas(self, *, tenant_id: int | str | None) -> dict[str, int]:
        funnel = self.pdp_funnel(tenant_id=tenant_id)["products"]
        deltas: dict[str, int] = {}
        for product_slug, stats in funnel.items():
            delta = (
                stats["pdp_views"] * 5
                + stats["successful_ctas"] * 40
                - stats["unavailable_ctas"] * 25
            )
            if delta:
                deltas[product_slug] = max(min(delta, 160), -120)
        return deltas

    def apply_product_card_priority_experiment(
        self,
        *,
        tenant_id: int | str | None,
        products: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        deltas = self.product_priority_deltas(tenant_id=tenant_id)
        enriched = []
        for product in products:
            item = dict(product)
            product_slug = _string(item.get("slug"), limit=120)
            delta = deltas.get(product_slug, 0)
            base_score = _safe_int(item.get("discovery_rank_score"))
            item["conversion_experiment_delta"] = delta
            item["conversion_experiment_key"] = "product_card_priority_v1" if delta else ""
            item["discovery_rank_score"] = base_score + delta
            if delta > 0:
                item["discovery_rank_reason"] = f'{item.get("discovery_rank_reason", "produto relevante")} · priorizado por sinais recentes de conversão'
            enriched.append(item)
        return sorted(
            enriched,
            key=lambda product: (
                -_safe_int(product.get("discovery_rank_score")),
                _string(product.get("name")).lower(),
            ),
        )

    def _events(self, *, tenant_id: int | str | None) -> list[StorefrontDiscoveryEventLog]:
        if not tenant_id:
            return []
        return list(
            StorefrontDiscoveryEventLog.objects.filter(tenant_id=tenant_id).order_by("-occurred_at", "-id")[:1000]
        )

    def _ratio(self, numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return round(numerator / denominator, 4)


storefront_conversion_insights = StorefrontConversionInsightsQueryService()
