from django.test import TestCase

from app.modules.accounts.models import OwnerUser
from app.modules.customers.models import Customer
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.shipping.application.shipment_commands import shipment_commands
from app.modules.shipping.models import Shipment, ShipmentStatusHistory
from app.modules.tenants.models import Tenant


class ShipmentCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Ship Cmd", slug="loja-ship-cmd", subdomain="loja-ship-cmd")
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-ship",
            full_name="Cliente Ship",
            email="cliente.ship@example.com",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.ship@example.com",
            full_name="Owner Ship",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="8001",
            customer_name="Cliente Ship",
            customer_email="cliente.ship@example.com",
        )

    def test_mark_shipment_sent_creates_shipment_and_customer_notification_log(self):
        result = shipment_commands.mark_shipment_sent(
            tenant_id=self.tenant.id,
            order_number="8001",
            tracking_code="BR123",
            carrier_name="Correios",
            actor_role="owner",
        )

        shipment = Shipment.objects.get(order=self.order)
        self.assertEqual(result, "shipment-sent")
        self.assertEqual(shipment.status, Shipment.Status.SENT)
        self.assertEqual(shipment.tracking_code, "BR123")
        history = ShipmentStatusHistory.objects.get(shipment=shipment, event_type="shipment_sent")
        self.assertEqual(history.tenant, self.tenant)
        self.assertEqual(history.source_label, "Shipping Commands")
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="shipment.sent",
                intent_key="customer.shipment.sent",
                recipient_id=str(self.customer.id),
            ).exists()
        )

    def test_mark_shipment_delivered_updates_shipment_and_notification_logs(self):
        shipment_commands.mark_shipment_sent(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")
        EmailLog.objects.all().delete()

        result = shipment_commands.mark_shipment_delivered(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")

        shipment = Shipment.objects.get(order=self.order)
        self.assertEqual(result, "shipment-delivered")
        self.assertEqual(shipment.status, Shipment.Status.DELIVERED)
        history = ShipmentStatusHistory.objects.get(shipment=shipment, event_type="shipment_delivered")
        self.assertEqual(history.tenant, self.tenant)
        self.assertEqual(history.actor_label, "Operação interna")
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="shipment.delivered",
                intent_key="customer.shipment.delivered",
                recipient_id=str(self.customer.id),
            ).exists()
        )
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="shipment.delivered",
                intent_key="owner.shipment.delivered",
                recipient_id=str(self.owner.id),
            ).exists()
        )

    def test_shipment_sent_is_idempotent(self):
        first = shipment_commands.mark_shipment_sent(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")
        second = shipment_commands.mark_shipment_sent(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")

        self.assertEqual(first, "shipment-sent")
        self.assertEqual(second, "shipment-sent-already-recorded")
        self.assertEqual(EmailLog.objects.filter(source_event="shipment.sent").count(), 1)
        self.assertEqual(ShipmentStatusHistory.objects.filter(event_type="shipment_sent").count(), 1)

    def test_generate_shipping_label_creates_label_and_history(self):
        result = shipment_commands.generate_shipping_label(
            tenant_id=self.tenant.id,
            order_number="8001",
            actor_role="owner",
        )

        shipment = Shipment.objects.get(order=self.order)
        self.assertEqual(result, "shipment-label-generated")
        self.assertEqual(shipment.label_status, Shipment.LabelStatus.GENERATED)
        self.assertTrue(shipment.label_code.startswith(f"HBX-{self.tenant.id}-8001-"))
        self.assertEqual(shipment.label_url, "/ops/shipping/8001/label/")
        self.assertTrue(
            ShipmentStatusHistory.objects.filter(
                shipment=shipment,
                event_type="shipment_label_generated",
            ).exists()
        )

    def test_generate_shipping_label_is_idempotent(self):
        first = shipment_commands.generate_shipping_label(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")
        second = shipment_commands.generate_shipping_label(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")

        self.assertEqual(first, "shipment-label-generated")
        self.assertEqual(second, "shipment-label-already-generated")
        self.assertEqual(Shipment.objects.count(), 1)
        self.assertEqual(ShipmentStatusHistory.objects.filter(event_type="shipment_label_generated").count(), 1)

    def test_shipment_delivered_is_idempotent(self):
        shipment_commands.mark_shipment_sent(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")
        first = shipment_commands.mark_shipment_delivered(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")
        second = shipment_commands.mark_shipment_delivered(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")

        self.assertEqual(first, "shipment-delivered")
        self.assertEqual(second, "shipment-delivered-already-recorded")
        self.assertEqual(EmailLog.objects.filter(source_event="shipment.delivered").count(), 2)
        self.assertEqual(ShipmentStatusHistory.objects.filter(event_type="shipment_delivered").count(), 1)

    def test_shipment_delivered_requires_sent_shipment(self):
        Shipment.objects.create(tenant=self.tenant, order=self.order)

        result = shipment_commands.mark_shipment_delivered(tenant_id=self.tenant.id, order_number="8001", actor_role="owner")

        self.assertEqual(result, "shipment-delivery-blocked")
        self.assertEqual(EmailLog.objects.filter(source_event="shipment.delivered").count(), 0)
        self.assertEqual(ShipmentStatusHistory.objects.filter(event_type="shipment_delivered").count(), 0)

    def test_shipment_commands_do_not_cross_tenants(self):
        other_tenant = Tenant.objects.create(name="Outra Loja", slug="outra-loja", subdomain="outra-loja")

        sent_result = shipment_commands.mark_shipment_sent(tenant_id=other_tenant.id, order_number="8001", actor_role="owner")
        delivered_result = shipment_commands.mark_shipment_delivered(tenant_id=other_tenant.id, order_number="8001", actor_role="owner")
        label_result = shipment_commands.generate_shipping_label(tenant_id=other_tenant.id, order_number="8001", actor_role="owner")

        self.assertEqual(sent_result, "shipment-order-not-found")
        self.assertEqual(delivered_result, "shipment-order-not-found")
        self.assertEqual(label_result, "shipment-order-not-found")
        self.assertEqual(Shipment.objects.filter(tenant=other_tenant).count(), 0)
