from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.shipping.models import ShippingProviderSettings, ShippingProviderSettingsHistory
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class AdminProviderSettingsViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Provider UI", slug="loja-provider-ui", subdomain="loja-provider-ui")

    def test_admin_provider_settings_view_renders_manual_fallback(self):
        response = self.client.get(
            reverse("shipping:admin-shipping-provider"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Provider de tracking")
        self.assertContains(response, "Manual/local")
        self.assertContains(response, "Salvar provider")

    def test_admin_provider_settings_action_upserts_http_settings_for_tenant(self):
        response = self.client.post(
            reverse("shipping:admin-shipping-provider-update"),
            data={
                "provider_name": "http",
                "base_url": "https://provider.example",
                "api_token": "secret-token",
                "timeout_seconds": "2.50",
                "is_active": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/provider/?result=provider-settings-updated", fetch_redirect_response=False)
        settings = ShippingProviderSettings.objects.get(tenant=self.tenant)
        self.assertEqual(settings.provider_name, "http")
        self.assertEqual(settings.base_url, "https://provider.example")
        self.assertEqual(settings.api_token, "secret-token")
        self.assertEqual(str(settings.timeout_seconds), "2.50")
        self.assertTrue(settings.is_active)
        history = ShippingProviderSettingsHistory.objects.get(settings=settings)
        self.assertEqual(history.event_type, "provider_settings_updated")
        self.assertEqual(history.source_label, "Shipping Provider Settings")

    def test_admin_provider_settings_view_masks_existing_token(self):
        ShippingProviderSettings.objects.create(
            tenant=self.tenant,
            provider_name="http",
            base_url="https://provider.example",
            api_token="secret-token",
            is_active=True,
        )

        response = self.client.get(
            reverse("shipping:admin-shipping-provider"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertContains(response, "Configurado")
        self.assertContains(response, "Token já configurado")
        self.assertNotContains(response, "secret-token")

    def test_admin_provider_settings_action_preserves_existing_token_when_blank(self):
        ShippingProviderSettings.objects.create(
            tenant=self.tenant,
            provider_name="http",
            base_url="https://old-provider.example",
            api_token="secret-token",
            is_active=True,
        )

        response = self.client.post(
            reverse("shipping:admin-shipping-provider-update"),
            data={
                "provider_name": "http",
                "base_url": "https://provider.example",
                "api_token": "",
                "timeout_seconds": "2.50",
                "is_active": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/provider/?result=provider-settings-updated", fetch_redirect_response=False)
        settings = ShippingProviderSettings.objects.get(tenant=self.tenant)
        self.assertEqual(settings.base_url, "https://provider.example")
        self.assertEqual(settings.api_token, "secret-token")

    def test_admin_provider_settings_view_renders_history_summary(self):
        settings = ShippingProviderSettings.objects.create(
            tenant=self.tenant,
            provider_name="http",
            base_url="https://provider.example",
            is_active=True,
        )
        ShippingProviderSettingsHistory.objects.create(
            tenant=self.tenant,
            settings=settings,
            event_type="provider_settings_updated",
            title="Provider atualizado",
            source_label="Shipping Provider Settings",
        )

        response = self.client.get(
            reverse("shipping:admin-shipping-provider"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertContains(response, "Histórico")
        self.assertContains(response, "Provider atualizado")

    def test_admin_provider_settings_action_requires_base_url_when_http_active(self):
        response = self.client.post(
            reverse("shipping:admin-shipping-provider-update"),
            data={
                "provider_name": "http",
                "base_url": "",
                "timeout_seconds": "2.50",
                "is_active": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/provider/?result=provider-settings-base-url-required", fetch_redirect_response=False)
        self.assertFalse(ShippingProviderSettings.objects.filter(tenant=self.tenant).exists())

    def test_admin_provider_settings_action_does_not_cross_tenants(self):
        other_tenant = Tenant.objects.create(name="Outra Provider UI", slug="outra-provider-ui", subdomain="outra-provider-ui")

        response = self.client.post(
            reverse("shipping:admin-shipping-provider-update"),
            data={
                "provider_name": "http",
                "base_url": "https://provider.example",
                "timeout_seconds": "2.50",
                "is_active": "1",
            },
            HTTP_HOST=f"{other_tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/provider/?result=provider-settings-updated", fetch_redirect_response=False)
        self.assertFalse(ShippingProviderSettings.objects.filter(tenant=self.tenant).exists())
        self.assertTrue(ShippingProviderSettings.objects.filter(tenant=other_tenant).exists())
