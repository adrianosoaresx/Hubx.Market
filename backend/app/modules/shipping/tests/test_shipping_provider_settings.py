from django.test import TestCase

from app.modules.shipping.application.shipping_provider_contracts import ManualShipmentProviderGateway
from app.modules.shipping.application.shipping_provider_settings import shipping_provider_settings
from app.modules.shipping.infrastructure.http_tracking_provider import HttpTrackingProviderGateway
from app.modules.shipping.models import ShippingProviderSettings
from app.modules.tenants.models import Tenant


class ShippingProviderSettingsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Provider Settings", slug="loja-provider-settings", subdomain="loja-provider-settings")

    def test_provider_settings_default_to_manual_gateway_when_missing(self):
        gateway = shipping_provider_settings.get_gateway_for_tenant(tenant_id=self.tenant.id)

        self.assertIsInstance(gateway, ManualShipmentProviderGateway)

    def test_provider_settings_default_to_manual_gateway_when_inactive(self):
        ShippingProviderSettings.objects.create(
            tenant=self.tenant,
            provider_name="http",
            base_url="https://provider.example",
            is_active=False,
        )

        gateway = shipping_provider_settings.get_gateway_for_tenant(tenant_id=self.tenant.id)

        self.assertIsInstance(gateway, ManualShipmentProviderGateway)

    def test_provider_settings_return_http_gateway_when_active_and_configured(self):
        ShippingProviderSettings.objects.create(
            tenant=self.tenant,
            provider_name="http",
            base_url="https://provider.example",
            api_token="secret-token",
            timeout_seconds="2.50",
            is_active=True,
        )

        gateway = shipping_provider_settings.get_gateway_for_tenant(tenant_id=self.tenant.id)

        self.assertIsInstance(gateway, HttpTrackingProviderGateway)
        self.assertEqual(gateway.base_url, "https://provider.example")
        self.assertEqual(gateway.token, "secret-token")
        self.assertEqual(gateway.timeout_seconds, 2.5)
