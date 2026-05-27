from __future__ import annotations

from django.core.cache import cache
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from django.test import TestCase

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.models import ApiKey
from app.modules.audit.models import AuditLog
from app.modules.catalog.interfaces.public_api_views import PublicCatalogProductsApiView
from app.modules.catalog.models import Product, ProductImage, ProductVariant
from app.modules.tenants.models import Tenant


@override_settings(
    API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED=True,
    API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED=True,
    ALLOWED_HOSTS=[".hubx.market", "testserver"],
)
class PublicCatalogApiTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.previous_rate_limit = PublicCatalogProductsApiView.api_key_rate_limit
        self.previous_rate_limit_window = PublicCatalogProductsApiView.api_key_rate_limit_window_seconds
        from app.modules.catalog.interfaces.public_api_views import PublicCatalogProductDetailApiView

        self.previous_detail_rate_limit = PublicCatalogProductDetailApiView.api_key_rate_limit
        self.previous_detail_rate_limit_window = PublicCatalogProductDetailApiView.api_key_rate_limit_window_seconds
        self.tenant = Tenant.objects.create(name="API Catalog", slug="api-catalog", subdomain="api-catalog")
        self.other_tenant = Tenant.objects.create(name="Other API Catalog", slug="other-api-catalog", subdomain="other-api-catalog")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.url = reverse("catalog_public_api:products-list")
        self.key = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Catalog integration",
            scopes=["read:catalog"],
        )

    def tearDown(self):
        PublicCatalogProductsApiView.api_key_rate_limit = self.previous_rate_limit
        PublicCatalogProductsApiView.api_key_rate_limit_window_seconds = self.previous_rate_limit_window
        from app.modules.catalog.interfaces.public_api_views import PublicCatalogProductDetailApiView

        PublicCatalogProductDetailApiView.api_key_rate_limit = self.previous_detail_rate_limit
        PublicCatalogProductDetailApiView.api_key_rate_limit_window_seconds = self.previous_detail_rate_limit_window
        cache.clear()

    def test_lists_only_active_products_for_current_tenant(self):
        active_product = self._product(
            tenant=self.tenant,
            name="Tênis Público",
            slug="tenis-publico",
            status=Product.Status.ACTIVE,
            is_active=True,
            is_featured=True,
        )
        ProductVariant.objects.create(product=active_product, sku="TENIS-PUBLICO-42", price="129.90", stock=8, is_default=True)
        ProductImage.objects.create(product=active_product, image_url="https://cdn.example.com/tenis.jpg", alt_text="Tênis", is_primary=True)
        inactive_product = self._product(
            tenant=self.tenant,
            name="Produto Inativo",
            slug="produto-inativo",
            status=Product.Status.INACTIVE,
            is_active=False,
        )
        ProductVariant.objects.create(product=inactive_product, sku="INATIVO-1", price="10.00", stock=10)
        other_product = self._product(
            tenant=self.other_tenant,
            name="Produto Outro Tenant",
            slug="produto-outro-tenant",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(product=other_product, sku="OUTRO-1", price="20.00", stock=10)

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"], "public-catalog-products-listed")
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(len(response.data["results"]), 1)
        item = response.data["results"][0]
        self.assertEqual(item["slug"], "tenis-publico")
        self.assertEqual(item["price"], "129.90")
        self.assertEqual(item["availability"], "in_stock")
        self.assertEqual(item["primary_image"]["url"], "https://cdn.example.com/tenis.jpg")
        self.assertNotIn("tenant_id", item)
        self.assertNotIn("stock", item)
        self.assertIsNotNone(ApiKey.objects.get(pk=self.key["api_key"]["id"]).last_used_at)

    def test_empty_tenant_returns_empty_payload_without_fixture_fallback(self):
        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["results"], [])

    def test_rejects_key_without_read_catalog_scope(self):
        key = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Orders integration",
            scopes=["read:orders"],
        )

        response = self._get(secret=key["secret"])

        self.assertEqual(response.status_code, 403)

    def test_rejects_cross_tenant_key(self):
        other_key = api_key_commands.create_key(
            tenant_id=self.other_tenant.id,
            name="Other catalog integration",
            scopes=["read:catalog"],
        )

        response = self._get(secret=other_key["secret"])

        self.assertEqual(response.status_code, 401)

    def test_caps_page_size(self):
        for index in range(55):
            product = self._product(
                tenant=self.tenant,
                name=f"Produto {index:02d}",
                slug=f"produto-{index:02d}",
                status=Product.Status.ACTIVE,
                is_active=True,
            )
            ProductVariant.objects.create(product=product, sku=f"PROD-{index:02d}", price="10.00", stock=10)

        response = self._get(query={"page_size": "999"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 55)
        self.assertEqual(response.data["page_size"], 50)
        self.assertEqual(len(response.data["results"]), 50)

    @override_settings(API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED=False)
    def test_endpoint_is_hidden_when_rollout_flag_is_disabled(self):
        response = self._get()

        self.assertEqual(response.status_code, 404)

    def test_rate_limits_by_api_key_and_endpoint_with_retry_after(self):
        PublicCatalogProductsApiView.api_key_rate_limit = 2
        PublicCatalogProductsApiView.api_key_rate_limit_window_seconds = 60

        first_response = self._get()
        second_response = self._get()
        limited_response = self._get()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(limited_response.status_code, 429)
        self.assertIn("Retry-After", limited_response)
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.rate_limited")
        self.assertEqual(audit_log.entity_id, str(self.key["api_key"]["id"]))
        self.assertEqual(audit_log.metadata["endpoint"], "catalog.products.list")
        self.assertEqual(audit_log.metadata["limit"], 2)
        self.assertEqual(audit_log.metadata["window_seconds"], 60)
        self.assertNotIn("secret", str(audit_log.metadata).lower())
        self.assertNotIn("key_hash", str(audit_log.metadata).lower())
        self.assertNotIn(self.key["secret"], str(audit_log.metadata))

    def test_rate_limit_isolated_by_api_key(self):
        PublicCatalogProductsApiView.api_key_rate_limit = 1
        PublicCatalogProductsApiView.api_key_rate_limit_window_seconds = 60
        other_key = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Second catalog integration",
            scopes=["read:catalog"],
        )

        first_key_response = self._get()
        second_key_response = self._get(secret=other_key["secret"])
        limited_first_key_response = self._get()

        self.assertEqual(first_key_response.status_code, 200)
        self.assertEqual(second_key_response.status_code, 200)
        self.assertEqual(limited_first_key_response.status_code, 429)

    def test_product_detail_returns_safe_public_payload_for_current_tenant(self):
        product = self._product(
            tenant=self.tenant,
            name="Tênis Detalhe",
            slug="tenis-detalhe",
            status=Product.Status.ACTIVE,
            is_active=True,
            is_featured=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="TENIS-DETALHE-41",
            price="199.90",
            compare_price="249.90",
            stock=3,
            is_default=True,
        )
        ProductVariant.objects.create(product=product, sku="TENIS-DETALHE-42", price="209.90", stock=0)
        ProductImage.objects.create(product=product, image_url="https://cdn.example.com/detail-1.jpg", alt_text="Detalhe 1", is_primary=True)
        ProductImage.objects.create(product=product, image_url="https://cdn.example.com/detail-2.jpg", alt_text="Detalhe 2", position=2)

        response = self._get_detail(slug="tenis-detalhe")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["result"], "public-catalog-product-retrieved")
        item = response.data["product"]
        self.assertEqual(item["slug"], "tenis-detalhe")
        self.assertEqual(item["price"], "199.90")
        self.assertEqual(item["availability"], "low_stock")
        self.assertEqual(len(item["images"]), 2)
        self.assertEqual(len(item["variants"]), 2)
        self.assertEqual(item["variants"][0]["availability"], "low_stock")
        self.assertNotIn("tenant_id", item)
        self.assertNotIn("stock", item)
        self.assertNotIn("stock", item["variants"][0])
        self.assertNotIn("reserved_stock", item["variants"][0])

    def test_product_detail_hides_other_tenant_and_inactive_products(self):
        other_product = self._product(
            tenant=self.other_tenant,
            name="Produto Outro Tenant",
            slug="produto-privado",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(product=other_product, sku="OUTRO-DETALHE", price="20.00", stock=10)
        inactive_product = self._product(
            tenant=self.tenant,
            name="Produto Inativo",
            slug="produto-inativo",
            status=Product.Status.INACTIVE,
            is_active=False,
        )
        ProductVariant.objects.create(product=inactive_product, sku="INATIVO-DETALHE", price="10.00", stock=10)

        other_response = self._get_detail(slug="produto-privado")
        inactive_response = self._get_detail(slug="produto-inativo")

        self.assertEqual(other_response.status_code, 404)
        self.assertEqual(inactive_response.status_code, 404)

    def test_product_detail_rejects_key_without_read_catalog_scope(self):
        product = self._product(
            tenant=self.tenant,
            name="Produto Escopo",
            slug="produto-escopo",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(product=product, sku="ESCOPO-1", price="10.00", stock=10)
        key = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Orders integration",
            scopes=["read:orders"],
        )

        response = self._get_detail(slug="produto-escopo", secret=key["secret"])

        self.assertEqual(response.status_code, 403)

    @override_settings(API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED=False)
    def test_product_detail_is_hidden_when_rollout_flag_is_disabled(self):
        response = self._get_detail(slug="qualquer-produto")

        self.assertEqual(response.status_code, 404)

    def test_product_detail_rate_limits_by_api_key_and_endpoint(self):
        from app.modules.catalog.interfaces.public_api_views import PublicCatalogProductDetailApiView

        PublicCatalogProductDetailApiView.api_key_rate_limit = 1
        PublicCatalogProductDetailApiView.api_key_rate_limit_window_seconds = 60
        product = self._product(
            tenant=self.tenant,
            name="Produto Rate",
            slug="produto-rate",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(product=product, sku="RATE-1", price="10.00", stock=10)

        first_response = self._get_detail(slug="produto-rate")
        limited_response = self._get_detail(slug="produto-rate")

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(limited_response.status_code, 429)
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.rate_limited", metadata__endpoint="catalog.products.detail")
        self.assertEqual(audit_log.metadata["limit"], 1)
        self.assertNotIn("secret", str(audit_log.metadata).lower())
        self.assertNotIn("key_hash", str(audit_log.metadata).lower())

    def _product(
        self,
        *,
        tenant: Tenant,
        name: str,
        slug: str,
        status: str,
        is_active: bool,
        is_featured: bool = False,
    ) -> Product:
        return Product.objects.create(
            tenant=tenant,
            name=name,
            slug=slug,
            description="Descrição pública segura",
            brand_name="Hubx",
            category_label="Calçados",
            status=status,
            is_active=is_active,
            is_featured=is_featured,
        )

    def _get(self, *, secret: str | None = None, query: dict[str, str] | None = None):
        return self.client.get(
            self.url,
            data=query or {},
            HTTP_HOST=self.host,
            HTTP_AUTHORIZATION=f"Bearer {secret or self.key['secret']}",
        )

    def _get_detail(self, *, slug: str, secret: str | None = None):
        return self.client.get(
            reverse("catalog_public_api:products-detail", kwargs={"slug": slug}),
            HTTP_HOST=self.host,
            HTTP_AUTHORIZATION=f"Bearer {secret or self.key['secret']}",
        )
