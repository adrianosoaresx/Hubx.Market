from __future__ import annotations

from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.catalog.interfaces.public_api_views import PublicCatalogProductsApiView
from app.modules.tenants.models import Tenant


@override_settings(
    API_KEYS_OBSERVABILITY_TOKEN="api-keys-metrics-token",
    API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED=True,
    API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED=True,
    ALLOWED_HOSTS=[".hubx.market", "testserver"],
)
class ApiKeyPublicEndpointMetricsTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.previous_rate_limit = PublicCatalogProductsApiView.api_key_rate_limit
        self.previous_rate_limit_window = PublicCatalogProductsApiView.api_key_rate_limit_window_seconds
        self.tenant = Tenant.objects.create(name="Metrics Tenant", slug="metrics-tenant", subdomain="metrics-tenant")
        self.other_tenant = Tenant.objects.create(
            name="Other Metrics Tenant",
            slug="other-metrics-tenant",
            subdomain="other-metrics-tenant",
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.catalog_url = reverse("catalog_public_api:products-list")
        self.metrics_url = reverse("api_keys:public-endpoint-metrics")
        self.key = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Metrics catalog integration",
            scopes=["read:catalog"],
        )

    def tearDown(self):
        PublicCatalogProductsApiView.api_key_rate_limit = self.previous_rate_limit
        PublicCatalogProductsApiView.api_key_rate_limit_window_seconds = self.previous_rate_limit_window
        cache.clear()

    def test_metrics_endpoint_exports_success_auth_failure_rate_limit_and_enabled_state(self):
        PublicCatalogProductsApiView.api_key_rate_limit = 1
        PublicCatalogProductsApiView.api_key_rate_limit_window_seconds = 60
        other_key = api_key_commands.create_key(
            tenant_id=self.other_tenant.id,
            name="Other metrics catalog integration",
            scopes=["read:catalog"],
        )

        success = self._catalog_get(secret=self.key["secret"])
        limited = self._catalog_get(secret=self.key["secret"])
        auth_failed = self._catalog_get(secret=other_key["secret"])
        metrics = self.client.get(
            self.metrics_url,
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="api-keys-metrics-token",
        )

        self.assertEqual(success.status_code, 200)
        self.assertEqual(limited.status_code, 429)
        self.assertEqual(auth_failed.status_code, 401)
        self.assertEqual(metrics.status_code, 200)
        payload = metrics.content.decode()
        self.assertIn("hubx_api_key_public_request_total", payload)
        self.assertIn(
            f'hubx_api_key_public_request_total{{tenant_id="{self.tenant.id}",endpoint="catalog.products.list",result="success"}} 1',
            payload,
        )
        self.assertIn(
            f'hubx_api_key_rate_limited_total{{tenant_id="{self.tenant.id}",endpoint="catalog.products.list",prefix="{self.key["api_key"]["prefix"]}"}} 1',
            payload,
        )
        self.assertIn("hubx_api_key_auth_failure_total", payload)
        self.assertIn('endpoint="/api/v1/catalog/products/"', payload)
        self.assertIn('hubx_api_key_public_endpoint_enabled{endpoint="catalog.products.list"} 1', payload)
        self.assertIn('hubx_api_key_public_endpoint_enabled{endpoint="catalog.products.detail"} 1', payload)
        self.assertNotIn(self.key["secret"], payload)
        self.assertNotIn("key_hash", payload)
        self.assertNotIn("Authorization", payload)

    def test_metrics_endpoint_requires_observability_token_not_api_key(self):
        forbidden = self.client.get(self.metrics_url)
        api_key_attempt = self.client.get(self.metrics_url, HTTP_AUTHORIZATION=f"Bearer {self.key['secret']}")
        allowed = self.client.get(self.metrics_url, HTTP_AUTHORIZATION="Bearer api-keys-metrics-token")

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(api_key_attempt.status_code, 403)
        self.assertEqual(allowed.status_code, 200)

    @override_settings(API_KEYS_OBSERVABILITY_TOKEN="")
    def test_metrics_endpoint_is_hidden_without_token(self):
        response = self.client.get(self.metrics_url, HTTP_X_HUBX_OBSERVABILITY_TOKEN="api-keys-metrics-token")

        self.assertEqual(response.status_code, 404)

    def _catalog_get(self, *, secret: str):
        return self.client.get(
            self.catalog_url,
            HTTP_HOST=self.host,
            HTTP_AUTHORIZATION=f"Bearer {secret}",
        )
