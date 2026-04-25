from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.orders.models import Order
from app.modules.shipping.application.shipping_metrics_queries import shipping_metrics_queries
from app.modules.shipping.models import Shipment, ShipmentStatusHistory
from app.modules.tenants.models import Tenant


class ShippingMetricsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Shipping Metrics", slug="loja-shipping-metrics", subdomain="loja-shipping-metrics")
        self.order = Order.objects.create(tenant=self.tenant, number="9961", customer_email="shipping.metrics@example.com")
        self.shipment = Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9961",
        )
        ShipmentStatusHistory.objects.create(
            tenant=self.tenant,
            shipment=self.shipment,
            event_type="shipment_tracking_synced",
            title="Tracking sincronizado",
            provider_http_status=200,
            provider_latency_ms=125,
        )

    def test_shipping_metrics_export_prometheus_payload(self):
        payload = shipping_metrics_queries.export_prometheus_metrics()

        self.assertIn("hubx_shipping_shipment_total", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",status="sent"', payload)
        self.assertIn("hubx_shipping_history_event_total", payload)
        self.assertIn('event_type="shipment_tracking_synced"', payload)
        self.assertIn("hubx_shipping_provider_http_status_total", payload)
        self.assertIn('http_status="200"', payload)
        self.assertIn("hubx_shipping_provider_latency_ms_avg", payload)
        self.assertIn("125.00", payload)

    @override_settings(SHIPPING_OBSERVABILITY_TOKEN="shipping-token")
    def test_shipping_metrics_view_returns_prometheus_payload_with_token(self):
        response = self.client.get(
            reverse("shipping:shipping-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="shipping-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])
        self.assertContains(response, "hubx_shipping_shipment_total")

    @override_settings(SHIPPING_OBSERVABILITY_TOKEN="shipping-token")
    def test_shipping_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("shipping:shipping-metrics"))

        self.assertEqual(response.status_code, 403)

    @override_settings(SHIPPING_OBSERVABILITY_TOKEN="", NOTIFICATIONS_OBSERVABILITY_TOKEN="")
    def test_shipping_metrics_view_is_not_found_without_configured_token(self):
        response = self.client.get(reverse("shipping:shipping-metrics"))

        self.assertEqual(response.status_code, 404)
