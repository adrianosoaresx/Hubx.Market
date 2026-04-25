from django.test import TestCase

from app.modules.orders.models import Order
from app.modules.shipping.application.shipping_provider_contracts import TrackingSnapshot
from app.modules.shipping.infrastructure.http_tracking_provider import (
    HttpTrackingProviderGateway,
    TrackingTransportResult,
    parse_tracking_provider_payload,
)
from app.modules.shipping.models import Shipment
from app.modules.tenants.models import Tenant


class HttpTrackingProviderTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja HTTP Tracking", slug="loja-http-tracking", subdomain="loja-http-tracking")
        self.order = Order.objects.create(tenant=self.tenant, number="9941", customer_email="http-tracking@example.com")
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9941",
            tracking_url="https://tracking.local/BR9941",
            carrier_name="Correios",
        )

    def test_parse_tracking_provider_payload_normalizes_external_status(self):
        fallback = TrackingSnapshot(
            tracking_code="BR9941",
            tracking_url="https://tracking.local/BR9941",
            carrier_name="Correios",
            provider_status="sent",
            normalized_status="in_transit",
            status_label="Em trânsito",
        )

        snapshot = parse_tracking_provider_payload(
            {
                "tracking_code": "BR9941",
                "tracking_url": "https://provider.example/BR9941",
                "carrier": "Provider Carrier",
                "status": "delivered",
            },
            fallback=fallback,
        )

        self.assertEqual(snapshot.normalized_status, "delivered")
        self.assertEqual(snapshot.status_label, "Entregue")
        self.assertTrue(snapshot.terminal)
        self.assertEqual(snapshot.tracking_url, "https://provider.example/BR9941")
        self.assertEqual(snapshot.carrier_name, "Provider Carrier")

    def test_http_gateway_uses_transport_and_authorization_header(self):
        calls = []

        def fake_transport(url, headers, timeout):
            calls.append((url, headers, timeout))
            return TrackingTransportResult(
                payload={"status": "delivered", "tracking_code": "BR9941"},
                status_code=200,
            )

        gateway = HttpTrackingProviderGateway(
            base_url="https://provider.example",
            token="secret-token",
            timeout_seconds=1.5,
            transport=fake_transport,
        )

        snapshot = gateway.get_tracking_snapshot(tenant_id=self.tenant.id, order_number="9941")

        self.assertEqual(snapshot.normalized_status, "delivered")
        self.assertEqual(snapshot.provider_http_status, 200)
        self.assertIsNotNone(snapshot.provider_latency_ms)
        self.assertEqual(calls[0][0], "https://provider.example/tracking/BR9941")
        self.assertEqual(calls[0][1]["Authorization"], "Bearer secret-token")
        self.assertEqual(calls[0][2], 1.5)

    def test_http_gateway_falls_back_to_manual_snapshot_on_transport_failure(self):
        def failing_transport(url, headers, timeout):
            raise TimeoutError("provider timeout")

        gateway = HttpTrackingProviderGateway(
            base_url="https://provider.example",
            transport=failing_transport,
        )

        snapshot = gateway.get_tracking_snapshot(tenant_id=self.tenant.id, order_number="9941")

        self.assertEqual(snapshot.tracking_code, "BR9941")
        self.assertEqual(snapshot.normalized_status, "in_transit")
        self.assertEqual(snapshot.status_label, "Em trânsito")
        self.assertEqual(snapshot.provider_error_code, "transport_error")
        self.assertEqual(snapshot.provider_error_message, "TimeoutError")

    def test_http_gateway_marks_invalid_payload_as_provider_error(self):
        def invalid_transport(url, headers, timeout):
            return ["invalid"]

        gateway = HttpTrackingProviderGateway(
            base_url="https://provider.example",
            transport=invalid_transport,
        )

        snapshot = gateway.get_tracking_snapshot(tenant_id=self.tenant.id, order_number="9941")

        self.assertEqual(snapshot.tracking_code, "BR9941")
        self.assertEqual(snapshot.provider_error_code, "invalid_payload")
        self.assertIsNotNone(snapshot.provider_latency_ms)
