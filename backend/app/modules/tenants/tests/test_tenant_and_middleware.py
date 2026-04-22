from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.db import IntegrityError
from django.db import transaction
from django.urls import path

from app.modules.tenants.models import Tenant


def tenant_probe_view(request):
    tenant = getattr(request, "tenant", None)
    return HttpResponse(tenant.subdomain if tenant else "none")


urlpatterns = [
    path("tenant-probe/", tenant_probe_view),
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
    ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver", "shop.example.com"],
    ROOT_URLCONF="app.modules.tenants.tests.test_tenant_and_middleware",
)
class TenantMiddlewareTests(TestCase):
    def test_resolves_valid_tenant_and_injects_request_tenant(self):
        Tenant.objects.create(name="Loja X", slug="lojax", subdomain="lojax")
        response = self.client.get("/tenant-probe/", HTTP_HOST="lojax.hubx.market")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "lojax")

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

    def test_localhost_is_ignored_and_sets_tenant_none(self):
        response = self.client.get("/tenant-probe/", HTTP_HOST="localhost:8000")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

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
