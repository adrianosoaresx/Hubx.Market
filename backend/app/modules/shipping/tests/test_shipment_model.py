from django.test import TestCase

from app.modules.orders.models import Order
from app.modules.shipping.models import Shipment, ShipmentStatusHistory
from app.modules.tenants.models import Tenant


class ShipmentModelTests(TestCase):
    def test_shipment_is_tenant_scoped_and_linked_to_order(self):
        tenant = Tenant.objects.create(name="Loja Ship", slug="loja-ship", subdomain="loja-ship")
        order = Order.objects.create(tenant=tenant, number="7001", customer_email="ship@example.com")

        shipment = Shipment.objects.create(
            tenant=tenant,
            order=order,
            tracking_code="BR123",
            carrier_name="Correios",
        )

        self.assertEqual(shipment.status, Shipment.Status.CREATED)
        self.assertEqual(shipment.tenant, tenant)
        self.assertEqual(shipment.order, order)
        self.assertEqual(str(shipment), f"{tenant.id}:{order.id}:created")

    def test_shipment_status_history_is_tenant_scoped_and_linked_to_shipment(self):
        tenant = Tenant.objects.create(name="Loja Ship History", slug="loja-ship-history", subdomain="loja-ship-history")
        order = Order.objects.create(tenant=tenant, number="7002", customer_email="ship-history@example.com")
        shipment = Shipment.objects.create(tenant=tenant, order=order)

        history = ShipmentStatusHistory.objects.create(
            shipment=shipment,
            tenant=tenant,
            event_type="shipment_sent",
            source_type="application_command",
            source_label="Shipping Commands",
            actor_label="Operação interna",
            title="Shipment enviado",
        )

        self.assertEqual(history.shipment, shipment)
        self.assertEqual(history.tenant, tenant)
        self.assertEqual(str(history), f"{tenant.id}:{shipment.id}:shipment_sent")
