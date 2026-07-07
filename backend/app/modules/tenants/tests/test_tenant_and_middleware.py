from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.db import IntegrityError
from django.db import transaction
from django.urls import path

from config.settings.base import _allowed_hosts_from_env
from app.modules.tenants.models import Tenant


def tenant_probe_view(request):
    tenant = getattr(request, "tenant", None)
    source = getattr(request, "tenant_resolution_source", "")
    return HttpResponse(f"{tenant.subdomain}:{source}" if tenant else "none")


def write_probe_view(request):
    return HttpResponse("write-ok")


urlpatterns = [
    path("tenant-probe/", tenant_probe_view),
    path("write-probe/", write_probe_view),
    path("ops/probe/", write_probe_view),
    path("accounts/logout/", write_probe_view),
]


@override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market")
class TenantModelTests(TestCase):
    def test_create_tenant(self):
        t = Tenant.objects.create(name="Loja X", slug="lojax", subdomain="lojax")
        self.assertIsNotNone(t.id)
        self.assertEqual(str(t), "Loja X (lojax)")

    def test_unique_slug_and_subdomain(self):
        Tenant.objects.create(name="Loja X", slug="lojax", subdomain="lojax")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tenant.objects.create(name="Outra", slug="lojax", subdomain="outra")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Tenant.objects.create(name="Outra 2", slug="outra2", subdomain="lojax")


@override_settings(
    HUBX_MARKET_ROOT_DOMAIN="hubx.market",
    ALLOWED_HOSTS=[".hubx.market", ".localhost", "localhost", "testserver", "shop.example.com", "unknown.example.com"],
    ROOT_URLCONF="app.modules.tenants.tests.test_tenant_and_middleware",
)
class TenantMiddlewareTests(TestCase):
    def test_debug_allowed_hosts_env_includes_localhost_subdomains(self):
        hosts = _allowed_hosts_from_env("localhost,127.0.0.1,testserver", debug=True)

        self.assertIn(".localhost", hosts)
        self.assertIn("localhost", hosts)
        self.assertIn("127.0.0.1", hosts)

    def test_resolves_valid_tenant_and_injects_request_tenant(self):
        Tenant.objects.create(name="Loja X", slug="lojax", subdomain="lojax")
        response = self.client.get("/tenant-probe/", HTTP_HOST="lojax.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "lojax:subdomain")

    def test_ignores_reserved_host_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="www.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_ignores_root_domain_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_ignores_app_subdomain_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="app.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_ignores_api_subdomain_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="api.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_ignores_docs_subdomain_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="docs.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_ignores_cdn_subdomain_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="cdn.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_returns_404_when_tenant_missing(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="ghost.hubx.market")
        self.assertEqual(response.status_code, 404)

    def test_maintenance_tenant_blocks_storefront_paths(self):
        Tenant.objects.create(name="Loja Em Setup", slug="setup", subdomain="setup", maintenance_mode=True)

        response = self.client.get("/tenant-probe/", HTTP_HOST="setup.hubx.market")

        self.assertEqual(response.status_code, 503)
        self.assertIn("manutencao inicial", response.content.decode())

    def test_maintenance_tenant_allows_owner_admin_paths(self):
        Tenant.objects.create(name="Loja Em Setup", slug="setup", subdomain="setup", maintenance_mode=True)

        response = self.client.get("/ops/probe/", HTTP_HOST="setup.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "write-ok")

    def test_localhost_is_ignored_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="localhost:8000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    def test_localhost_subdomain_resolves_tenant_for_demo_dev_hosts(self):
        Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo")

        response = self.client.get("/tenant-probe/", HTTP_HOST="hubx-demo.localhost:8002")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "hubx-demo:subdomain")

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_demo_tenant_blocks_write_paths_as_read_only(self):
        Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo")

        response = self.client.post("/write-probe/", HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 403)
        self.assertIn("Demo somente leitura", response.content.decode())

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_demo_tenant_allows_session_paths(self):
        Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo")

        response = self.client.post("/accounts/logout/", HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "write-ok")

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_non_demo_tenant_allows_write_paths(self):
        Tenant.objects.create(name="Loja X", slug="lojax", subdomain="lojax")

        response = self.client.post("/write-probe/", HTTP_HOST="lojax.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "write-ok")

    def test_custom_domain_configured_on_tenant_is_still_ignored_until_supported(self):
        Tenant.objects.create(
            name="Loja Custom",
            slug="loja-custom",
            subdomain="lojacustom",
            custom_domain="shop.example.com",
            is_active=True,
        )

        response = self.client.get("/tenant-probe/", HTTP_HOST="shop.example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    @override_settings(HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True)
    def test_custom_domain_resolves_active_tenant_when_feature_enabled(self):
        Tenant.objects.create(
            name="Loja Custom Runtime",
            slug="loja-custom-runtime",
            subdomain="lojacustomruntime",
            custom_domain="shop.example.com",
            is_active=True,
        )

        response = self.client.get("/tenant-probe/", HTTP_HOST="shop.example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "lojacustomruntime:custom_domain")

    @override_settings(HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True)
    def test_custom_domain_blocks_maintenance_tenant_storefront_paths(self):
        Tenant.objects.create(
            name="Loja Custom Runtime",
            slug="loja-custom-runtime",
            subdomain="lojacustomruntime",
            custom_domain="shop.example.com",
            is_active=True,
            maintenance_mode=True,
        )

        response = self.client.get("/tenant-probe/", HTTP_HOST="shop.example.com")

        self.assertEqual(response.status_code, 503)
        self.assertIn("manutencao inicial", response.content.decode())

    @override_settings(HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True)
    def test_custom_domain_resolver_ignores_inactive_tenant(self):
        Tenant.objects.create(
            name="Loja Custom Inativa",
            slug="loja-custom-inativa",
            subdomain="lojacustominativa",
            custom_domain="shop.example.com",
            is_active=False,
        )

        response = self.client.get("/tenant-probe/", HTTP_HOST="shop.example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    @override_settings(HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True)
    def test_custom_domain_resolver_keeps_safe_miss_without_global_fallback(self):
        Tenant.objects.create(name="Outra Loja", slug="outra-loja", subdomain="outra-loja")

        response = self.client.get("/tenant-probe/", HTTP_HOST="unknown.example.com")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")
