from __future__ import annotations

from django.conf import settings
from django.http import Http404
from rest_framework.response import Response
from rest_framework.views import APIView

from app.modules.api_keys.application.api_key_public_endpoint_metrics import api_key_public_endpoint_metrics
from app.modules.api_keys.interfaces.authentication import ApiKeyAuthentication, HasApiKeyScope
from app.modules.api_keys.interfaces.throttling import ApiKeyRateLimitThrottle
from app.modules.catalog.application.public_catalog_api_queries import public_catalog_api_queries


class PublicCatalogProductsApiView(APIView):
    authentication_classes = (ApiKeyAuthentication,)
    permission_classes = (HasApiKeyScope,)
    throttle_classes = (ApiKeyRateLimitThrottle,)
    required_api_key_scope = "read:catalog"
    api_key_rate_limit_endpoint = "catalog.products.list"
    api_key_rate_limit = getattr(settings, "API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT", None)
    api_key_rate_limit_window_seconds = getattr(
        settings,
        "API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT_WINDOW_SECONDS",
        None,
    )

    def get(self, request):
        if not getattr(settings, "API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED", False):
            raise Http404("Endpoint not enabled")
        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        if not tenant_id:
            raise Http404("Tenant not found")
        payload = public_catalog_api_queries.list_products(
            tenant_id=tenant_id,
            page=request.query_params.get("page"),
            page_size=request.query_params.get("page_size"),
        )
        api_key_public_endpoint_metrics.record_request(
            tenant_id=tenant_id,
            endpoint=self.api_key_rate_limit_endpoint,
            result="success",
        )
        return Response(payload)


class PublicCatalogProductDetailApiView(APIView):
    authentication_classes = (ApiKeyAuthentication,)
    permission_classes = (HasApiKeyScope,)
    throttle_classes = (ApiKeyRateLimitThrottle,)
    required_api_key_scope = "read:catalog"
    api_key_rate_limit_endpoint = "catalog.products.detail"
    api_key_rate_limit = getattr(settings, "API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT", None)
    api_key_rate_limit_window_seconds = getattr(
        settings,
        "API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT_WINDOW_SECONDS",
        None,
    )

    def get(self, request, slug: str):
        if not getattr(settings, "API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED", False):
            raise Http404("Endpoint not enabled")
        tenant = getattr(request, "tenant", None)
        tenant_id = getattr(tenant, "id", None)
        if not tenant_id:
            raise Http404("Tenant not found")
        payload = public_catalog_api_queries.get_product_detail(
            tenant_id=tenant_id,
            slug=slug,
        )
        if payload["product"] is None:
            raise Http404("Product not found")
        api_key_public_endpoint_metrics.record_request(
            tenant_id=tenant_id,
            endpoint=self.api_key_rate_limit_endpoint,
            result="success",
        )
        return Response(payload)
