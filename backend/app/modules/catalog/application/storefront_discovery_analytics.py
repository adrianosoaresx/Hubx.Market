from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.conf import settings
from django.utils.crypto import salted_hmac

from app.modules.catalog.models import StorefrontDiscoveryEventLog
from app.modules.tenants.models import Tenant


DISCOVERY_EVENT_NAMES = {
    "catalog.discovery_viewed",
    "catalog.search_performed",
    "catalog.facets_applied",
    "catalog.sort_changed",
    "catalog.product_card_clicked",
    "catalog.product_detail_viewed",
    "catalog.pdp_cta_intent",
}

DISCOVERY_EVENT_PAYLOAD_KEYS = {
    "query",
    "category",
    "availability",
    "offer",
    "price_min",
    "price_max",
    "quick_filter",
    "sort",
    "result_count",
    "page",
    "product_id",
    "product_slug",
    "cta_intent",
    "cta_result",
    "quantity",
    "variant_sku",
}


@dataclass(frozen=True)
class StorefrontDiscoveryEvent:
    name: str
    payload: dict[str, object]


class StorefrontDiscoveryAnalyticsPublisher(Protocol):
    def publish(self, event: StorefrontDiscoveryEvent) -> None:
        ...


class NoopStorefrontDiscoveryAnalyticsPublisher:
    def publish(self, event: StorefrontDiscoveryEvent) -> None:
        return None


class DjangoStorefrontDiscoveryEventLogPublisher:
    def publish(self, event: StorefrontDiscoveryEvent) -> None:
        if event.name not in DISCOVERY_EVENT_NAMES:
            return
        tenant_id = event.payload.get("tenant_id")
        if not tenant_id:
            return

        session_key = _safe_text(event.payload.get("session_key"))
        path = _safe_text(event.payload.get("path"))
        payload = {
            key: value
            for key, value in event.payload.items()
            if key in DISCOVERY_EVENT_PAYLOAD_KEYS and value not in {"", None}
        }

        StorefrontDiscoveryEventLog.objects.create(
            tenant_id=tenant_id,
            event_name=event.name,
            session_key_hash=_session_key_hash(session_key),
            path=path,
            payload=payload,
        )


def _safe_text(value: object) -> str:
    return str(value or "").strip()


def _session_key_hash(session_key: str) -> str:
    if not session_key:
        return ""
    return salted_hmac("storefront_discovery_session", session_key).hexdigest()


def _base_payload(
    *,
    tenant_id: int | str | None,
    session_key: str,
    path: str,
    query: str = "",
    category: str = "",
    availability: str = "",
    offer: bool = False,
    price_min: str = "",
    price_max: str = "",
    quick_filter: str = "",
    sort: str = "recommended",
    result_count: int = 0,
    page: int = 1,
) -> dict[str, object]:
    return {
        "tenant_id": tenant_id,
        "session_key": _safe_text(session_key),
        "path": _safe_text(path),
        "query": _safe_text(query),
        "category": _safe_text(category),
        "availability": _safe_text(availability),
        "offer": bool(offer),
        "price_min": _safe_text(price_min),
        "price_max": _safe_text(price_max),
        "quick_filter": _safe_text(quick_filter),
        "sort": _safe_text(sort) or "recommended",
        "result_count": int(result_count),
        "page": int(page),
    }


@dataclass
class StorefrontDiscoveryAnalyticsService:
    publisher: StorefrontDiscoveryAnalyticsPublisher

    def _publish(self, name: str, payload: dict[str, object]) -> None:
        if not payload.get("tenant_id"):
            return
        if _is_demo_tenant_id(payload.get("tenant_id")):
            return
        try:
            self.publisher.publish(StorefrontDiscoveryEvent(name=name, payload=payload))
        except Exception:
            return

    def record_listing_view(
        self,
        *,
        tenant_id: int | str | None,
        session_key: str,
        path: str,
        query: str = "",
        category: str = "",
        availability: str = "",
        offer: bool = False,
        price_min: str = "",
        price_max: str = "",
        quick_filter: str = "",
        sort: str = "recommended",
        result_count: int = 0,
        page: int = 1,
    ) -> None:
        payload = _base_payload(
            tenant_id=tenant_id,
            session_key=session_key,
            path=path,
            query=query,
            category=category,
            availability=availability,
            offer=offer,
            price_min=price_min,
            price_max=price_max,
            quick_filter=quick_filter,
            sort=sort,
            result_count=result_count,
            page=page,
        )
        self._publish("catalog.discovery_viewed", payload)
        if payload["query"]:
            self._publish("catalog.search_performed", payload)
        if payload["category"] or payload["availability"] or payload["offer"] or payload["price_min"] or payload["price_max"] or payload["quick_filter"]:
            self._publish("catalog.facets_applied", payload)
        if payload["sort"] != "recommended":
            self._publish("catalog.sort_changed", payload)

    def record_product_detail_view(
        self,
        *,
        tenant_id: int | str | None,
        session_key: str,
        path: str,
        product_id: int | str | None,
        product_slug: str,
    ) -> None:
        payload = {
            "tenant_id": tenant_id,
            "session_key": _safe_text(session_key),
            "path": _safe_text(path),
            "product_id": product_id,
            "product_slug": _safe_text(product_slug),
        }
        self._publish("catalog.product_detail_viewed", payload)

    def record_pdp_cta_intent(
        self,
        *,
        tenant_id: int | str | None,
        session_key: str,
        path: str,
        product_id: int | str | None,
        product_slug: str,
        cta_intent: str,
        cta_result: str,
        quantity: int = 1,
        variant_sku: str = "",
    ) -> None:
        payload = {
            "tenant_id": tenant_id,
            "session_key": _safe_text(session_key),
            "path": _safe_text(path),
            "product_id": product_id,
            "product_slug": _safe_text(product_slug),
            "cta_intent": _safe_text(cta_intent),
            "cta_result": _safe_text(cta_result),
            "quantity": int(quantity),
            "variant_sku": _safe_text(variant_sku),
        }
        self._publish("catalog.pdp_cta_intent", payload)


storefront_discovery_analytics = StorefrontDiscoveryAnalyticsService(
    publisher=DjangoStorefrontDiscoveryEventLogPublisher()
)


def _is_demo_tenant_id(tenant_id: object) -> bool:
    try:
        normalized_tenant_id = int(tenant_id)
    except (TypeError, ValueError):
        return False
    demo_subdomain = str(getattr(settings, "HUBX_MARKET_DEMO_TENANT_SUBDOMAIN", "hubx-demo") or "hubx-demo").strip().lower()
    return Tenant.objects.filter(id=normalized_tenant_id, subdomain=demo_subdomain, is_active=True).exists()
