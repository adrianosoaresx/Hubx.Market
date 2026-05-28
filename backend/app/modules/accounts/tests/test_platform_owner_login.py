from django.contrib.auth.models import User
from django.test import TestCase, override_settings

from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


@override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class PlatformOwnerLoginTests(TestCase):
    def setUp(self):
        self.platform_tenant = Tenant.objects.create(name="Hubx Platform", slug="platform-system", subdomain="platform-system")
        self.tenant = Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo")
        OwnerUser.objects.create(
            tenant=self.platform_tenant,
            email="platform.owner@hubx.market",
            role="owner",
            is_active=True,
        )
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="store.owner@hubx.market",
            role="owner",
            is_active=True,
        )
        User.objects.create_user(
            username="platform.owner@hubx.market",
            email="platform.owner@hubx.market",
            password="secret",
        )
        User.objects.create_user(
            username="store.owner@hubx.market",
            email="store.owner@hubx.market",
            password="secret",
        )

    def test_platform_owner_can_login_from_central_host_to_onboarding(self):
        response = self.client.post(
            "/accounts/login/?next=/ops/platform/onboarding/",
            {"login": "platform.owner@hubx.market", "password": "secret"},
            HTTP_HOST="hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ops/platform/onboarding/")

    def test_platform_owner_without_next_goes_to_platform_tenants(self):
        response = self.client.post(
            "/accounts/login/",
            {"login": "platform.owner@hubx.market", "password": "secret"},
            HTTP_HOST="hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ops/platform/tenants/")

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_platform_owner_central_ops_redirects_to_platform_tenants(self):
        self.client.login(username="platform.owner@hubx.market", password="secret")

        response = self.client.get("/ops/", HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ops/platform/tenants/")

    def test_store_owner_login_from_central_host_redirects_to_owned_store(self):
        response = self.client.post(
            "/accounts/login/",
            {"login": "store.owner@hubx.market", "password": "secret"},
            HTTP_HOST="hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://hubx-demo.hubx.market/ops/")

    @override_settings(HUBX_MARKET_PUBLIC_PORT="8002")
    def test_store_owner_local_login_redirect_preserves_public_port(self):
        response = self.client.post(
            "/accounts/login/",
            {"login": "store.owner@hubx.market", "password": "secret"},
            HTTP_HOST="hubx.market:8002",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://hubx-demo.hubx.market:8002/ops/")

    @override_settings(
        HUBX_MARKET_ROOT_DOMAIN="localhost",
        HUBX_MARKET_PUBLIC_PORT="8002",
        ALLOWED_HOSTS=[".localhost", "localhost", "testserver"],
    )
    def test_store_owner_localhost_login_redirect_uses_localhost_subdomain(self):
        response = self.client.post(
            "/accounts/login/",
            {"login": "store.owner@hubx.market", "password": "secret"},
            HTTP_HOST="localhost:8002",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://hubx-demo.localhost:8002/ops/")

    def test_multi_store_non_platform_owner_goes_to_store_selection(self):
        other_tenant = Tenant.objects.create(name="Outra Loja", slug="outra-loja", subdomain="outra-loja")
        OwnerUser.objects.create(
            tenant=other_tenant,
            email="store.owner@hubx.market",
            role="owner",
            is_active=True,
        )

        response = self.client.post(
            "/accounts/login/",
            {"login": "store.owner@hubx.market", "password": "secret"},
            HTTP_HOST="hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/accounts/select-store/")
