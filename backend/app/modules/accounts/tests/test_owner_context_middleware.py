from django.contrib.auth.models import User
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path

from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


def owner_probe_view(request):
    owner_user = getattr(request, "owner_user", None)
    if owner_user is None:
        return HttpResponse("none")
    return HttpResponse(f"{owner_user.email}:{owner_user.role}")


urlpatterns = [
    path("ops/owner-probe/", owner_probe_view),
    path("ops/platform/onboarding/probe/", owner_probe_view),
    path("accounts/owner-probe/", owner_probe_view),
]


@override_settings(
    HUBX_MARKET_ROOT_DOMAIN="hubx.market",
    ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
    HUBX_OPS_AUTH_GATE_ENFORCED=False,
    ROOT_URLCONF="app.modules.accounts.tests.test_owner_context_middleware",
)
class OwnerContextMiddlewareTests(TestCase):
    def setUp(self):
        self.platform_tenant = Tenant.objects.create(name="Hubx Platform", slug="platform-system", subdomain="platform-system")
        self.tenant = Tenant.objects.create(name="Loja Owner Context", slug="loja-owner-context", subdomain="loja-owner-context")
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def test_resolves_active_owner_for_ops_surface(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.context@hubx.market",
            role="admin",
            is_active=True,
        )
        user = User.objects.create_user(username="owner-context", email="owner.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/ops/owner-probe/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "owner.context@hubx.market:admin")

    def test_does_not_resolve_owner_outside_ops_surface(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.context@hubx.market",
            role="admin",
            is_active=True,
        )
        user = User.objects.create_user(username="owner-context", email="owner.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/accounts/owner-probe/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_resolves_platform_owner_on_central_host(self):
        OwnerUser.objects.create(
            tenant=self.platform_tenant,
            email="platform.context@hubx.market",
            role="owner",
            is_active=True,
        )
        user = User.objects.create_user(username="platform-context", email="platform.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/ops/platform/onboarding/probe/", HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "platform.context@hubx.market:owner")

    @override_settings(
        HUBX_MARKET_ROOT_DOMAIN="hubx.market",
        ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
    )
    def test_store_owner_on_central_host_is_not_platform_owner(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="store.context@hubx.market",
            role="owner",
            is_active=True,
        )
        user = User.objects.create_user(username="store-context", email="store.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/ops/platform/onboarding/probe/", HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 403)

    @override_settings(
        HUBX_MARKET_ROOT_DOMAIN="hubx.market",
        ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
    )
    def test_platform_surface_is_not_served_from_store_host(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.context@hubx.market",
            role="owner",
            is_active=True,
        )
        user = User.objects.create_user(username="owner-context-platform", email="owner.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/ops/platform/onboarding/probe/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 403)

    @override_settings(
        HUBX_MARKET_ROOT_DOMAIN="hubx.market",
        ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
    )
    def test_platform_gate_denies_non_platform_role_without_tenant_host(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="viewer.context@hubx.market",
            role="viewer",
            is_active=True,
        )
        user = User.objects.create_user(username="viewer-context", email="viewer.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/ops/platform/onboarding/probe/", HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 403)

    def test_ignores_inactive_or_cross_tenant_owner(self):
        other_tenant = Tenant.objects.create(name="Outra Owner Context", slug="outra-owner-context", subdomain="outra-owner-context")
        OwnerUser.objects.create(
            tenant=other_tenant,
            email="owner.context@hubx.market",
            role="owner",
            is_active=True,
        )
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="inactive.context@hubx.market",
            role="owner",
            is_active=False,
        )
        user = User.objects.create_user(username="inactive-context", email="inactive.context@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get("/ops/owner-probe/", HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), "none")
