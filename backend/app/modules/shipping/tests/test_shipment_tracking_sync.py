from dataclasses import dataclass

from django.test import TestCase

from app.modules.accounts.models import OwnerUser
from app.modules.customers.models import Customer
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.shipping.application.shipment_tracking_sync import shipment_tracking_sync
from app.modules.shipping.application.shipping_provider_contracts import TrackingSnapshot
from app.modules.shipping.models import Shipment, ShipmentStatusHistory
from app.modules.tenants.models import Tenant


@dataclass
class StubTrackingProviderGateway:
    snapshot: TrackingSnapshot

    def get_tracking_snapshot(self, *, tenant_id, order_number):
        return self.snapshot


class ShipmentTrackingSyncTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Polling", slug="loja-polling", subdomain="loja-polling")
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-polling",
            full_name="Cliente Polling",
            email="cliente.polling@example.com",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.polling@example.com",
            full_name="Owner Polling",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9911",
            customer_name="Cliente Polling",
            customer_email="cliente.polling@example.com",
        )

    def test_sync_tracking_snapshot_marks_shipment_sent(self):
        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=self.tenant.id,
            order_number="9911",
            provider_gateway=StubTrackingProviderGateway(
                TrackingSnapshot(
                    tracking_code="BR9911",
                    tracking_url="https://tracking.example/BR9911",
                    carrier_name="Correios",
                    provider_status="posted",
                    normalized_status="in_transit",
                    status_label="Em trânsito",
                )
            ),
        )

        shipment = Shipment.objects.get(order=self.order)
        self.assertEqual(result, "tracking-sync-sent")
        self.assertEqual(shipment.status, Shipment.Status.SENT)
        self.assertEqual(shipment.tracking_code, "BR9911")
        self.assertTrue(ShipmentStatusHistory.objects.filter(shipment=shipment, event_type="shipment_sent").exists())
        self.assertTrue(EmailLog.objects.filter(source_event="shipment.sent", intent_key="customer.shipment.sent").exists())

    def test_sync_tracking_snapshot_marks_direct_delivery_and_publishes_events(self):
        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=self.tenant.id,
            order_number="9911",
            provider_gateway=StubTrackingProviderGateway(
                TrackingSnapshot(
                    tracking_code="BR9911",
                    tracking_url="",
                    carrier_name="Correios",
                    provider_status="delivered",
                    normalized_status="delivered",
                    status_label="Entregue",
                    terminal=True,
                )
            ),
        )

        shipment = Shipment.objects.get(order=self.order)
        self.assertEqual(result, "tracking-sync-delivered")
        self.assertEqual(shipment.status, Shipment.Status.DELIVERED)
        self.assertTrue(ShipmentStatusHistory.objects.filter(shipment=shipment, event_type="shipment_sent").exists())
        self.assertTrue(ShipmentStatusHistory.objects.filter(shipment=shipment, event_type="shipment_delivered").exists())
        self.assertTrue(EmailLog.objects.filter(source_event="shipment.sent", intent_key="customer.shipment.sent").exists())
        self.assertTrue(EmailLog.objects.filter(source_event="shipment.delivered", intent_key="customer.shipment.delivered").exists())
        self.assertTrue(EmailLog.objects.filter(source_event="shipment.delivered", intent_key="owner.shipment.delivered").exists())

    def test_sync_tracking_snapshot_updates_tracking_without_status_transition(self):
        shipment = Shipment.objects.create(tenant=self.tenant, order=self.order, status=Shipment.Status.SENT)

        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=self.tenant.id,
            order_number="9911",
            provider_gateway=StubTrackingProviderGateway(
                TrackingSnapshot(
                    tracking_code="BR9911",
                    tracking_url="",
                    carrier_name="Correios",
                    provider_status="sent",
                    normalized_status="in_transit",
                    status_label="Em trânsito",
                )
            ),
        )

        shipment.refresh_from_db()
        self.assertEqual(result, "tracking-sync-updated")
        self.assertEqual(shipment.status, Shipment.Status.SENT)
        self.assertEqual(shipment.tracking_code, "BR9911")
        self.assertTrue(ShipmentStatusHistory.objects.filter(shipment=shipment, event_type="shipment_tracking_synced").exists())
        self.assertEqual(EmailLog.objects.filter(source_event="shipment.sent").count(), 0)

    def test_sync_tracking_snapshot_does_not_cross_tenants(self):
        other_tenant = Tenant.objects.create(name="Outra Polling", slug="outra-polling", subdomain="outra-polling")

        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=other_tenant.id,
            order_number="9911",
            provider_gateway=StubTrackingProviderGateway(
                TrackingSnapshot(
                    tracking_code="BR9911",
                    tracking_url="",
                    carrier_name="Correios",
                    provider_status="posted",
                    normalized_status="in_transit",
                    status_label="Em trânsito",
                )
            ),
        )

        self.assertEqual(result, "tracking-sync-order-not-found")
        self.assertEqual(Shipment.objects.filter(tenant=other_tenant).count(), 0)

    def test_sync_tracking_snapshot_ignores_unavailable_snapshot(self):
        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=self.tenant.id,
            order_number="9911",
            provider_gateway=StubTrackingProviderGateway(
                TrackingSnapshot(
                    tracking_code="",
                    tracking_url="",
                    carrier_name="",
                    provider_status="missing",
                    normalized_status="missing",
                    status_label="Sem shipment",
                )
            ),
        )

        self.assertEqual(result, "tracking-sync-unavailable")
        self.assertFalse(Shipment.objects.filter(order=self.order).exists())

    def test_sync_tracking_snapshot_records_provider_error_history(self):
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9911",
        )

        result = shipment_tracking_sync.sync_tracking_snapshot(
            tenant_id=self.tenant.id,
            order_number="9911",
            provider_gateway=StubTrackingProviderGateway(
                TrackingSnapshot(
                    tracking_code="BR9911",
                    tracking_url="",
                    carrier_name="Correios",
                    provider_status="sent",
                    normalized_status="in_transit",
                    status_label="Em trânsito",
                    provider_error_code="transport_error",
                    provider_error_message="TimeoutError",
                    provider_http_status=504,
                    provider_latency_ms=3000,
                )
            ),
        )

        shipment = Shipment.objects.get(order=self.order)
        history = ShipmentStatusHistory.objects.get(
            shipment=shipment,
            event_type="shipment_tracking_provider_failed",
        )
        self.assertEqual(result, "tracking-sync-provider-error")
        self.assertIn("transport_error", history.description)
        self.assertIn("HTTP 504", history.description)
        self.assertIn("3000ms", history.description)
