from django.test import TestCase

from app.modules.orders.models import Order
from app.modules.shipping.application.shipping_provider_contracts import manual_shipment_provider_gateway
from app.modules.shipping.application.tracking_status_normalizer import normalize_tracking_status
from app.modules.shipping.models import Shipment
from app.modules.tenants.models import Tenant


class ShippingProviderContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Provider", slug="loja-provider", subdomain="loja-provider")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9901",
            customer_email="provider@example.com",
        )

    def test_manual_provider_returns_tracking_snapshot_for_tenant_shipment(self):
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9901",
            tracking_url="https://tracking.example/BR9901",
            carrier_name="Correios",
        )

        snapshot = manual_shipment_provider_gateway.get_tracking_snapshot(
            tenant_id=self.tenant.id,
            order_number="9901",
        )

        self.assertTrue(snapshot.has_tracking)
        self.assertEqual(snapshot.tracking_code, "BR9901")
        self.assertEqual(snapshot.tracking_url, "https://tracking.example/BR9901")
        self.assertEqual(snapshot.carrier_name, "Correios")
        self.assertEqual(snapshot.provider_status, Shipment.Status.SENT)
        self.assertEqual(snapshot.normalized_status, "in_transit")
        self.assertEqual(snapshot.status_label, "Em trânsito")
        self.assertFalse(snapshot.terminal)

    def test_manual_provider_does_not_cross_tenants(self):
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9901",
        )
        other_tenant = Tenant.objects.create(name="Outra Provider", slug="outra-provider", subdomain="outra-provider")

        snapshot = manual_shipment_provider_gateway.get_tracking_snapshot(
            tenant_id=other_tenant.id,
            order_number="9901",
        )

        self.assertFalse(snapshot.has_tracking)
        self.assertEqual(snapshot.provider_status, "missing")
        self.assertEqual(snapshot.normalized_status, "missing")
        self.assertEqual(snapshot.status_label, "Sem shipment")

    def test_tracking_status_normalizer_maps_external_vocab_to_internal_vocab(self):
        self.assertEqual(normalize_tracking_status("posted").value, "in_transit")
        self.assertEqual(normalize_tracking_status("delivered").value, "delivered")
        self.assertTrue(normalize_tracking_status("delivered").terminal)
        self.assertEqual(normalize_tracking_status("carrier_weird_state").value, "unknown")
