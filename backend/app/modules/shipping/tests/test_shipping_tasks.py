from django.test import TestCase

from app.modules.accounts.models import OwnerUser
from app.modules.customers.models import Customer
from app.modules.orders.models import Order
from app.modules.shipping.models import Shipment
from app.modules.shipping.tasks import sync_pending_shipments_tracking_task, sync_shipment_tracking_task
from app.modules.tenants.models import Tenant


class ShippingTaskTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Shipping Task", slug="loja-shipping-task", subdomain="loja-shipping-task")
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-shipping-task",
            full_name="Cliente Shipping Task",
            email="cliente.shipping.task@example.com",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.shipping.task@example.com",
            full_name="Owner Shipping Task",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9951",
            customer_email="cliente.shipping.task@example.com",
        )

    def test_sync_shipment_tracking_task_delegates_to_sync_service(self):
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9951",
        )

        result = sync_shipment_tracking_task.run(tenant_id=self.tenant.id, order_number="9951")

        self.assertEqual(result, "tracking-sync-unchanged")

    def test_sync_pending_shipments_tracking_task_processes_limited_batch(self):
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.SENT,
            tracking_code="BR9951",
        )
        second_order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9952",
            customer_email="cliente.shipping.task@example.com",
        )
        Shipment.objects.create(
            tenant=self.tenant,
            order=second_order,
            status=Shipment.Status.SENT,
            tracking_code="BR9952",
        )

        result = sync_pending_shipments_tracking_task.run(tenant_id=self.tenant.id, limit=1)

        self.assertEqual(result, {"tracking-sync-unchanged": 1})

    def test_sync_pending_shipments_tracking_task_ignores_terminal_shipments(self):
        Shipment.objects.create(
            tenant=self.tenant,
            order=self.order,
            status=Shipment.Status.DELIVERED,
            tracking_code="BR9951",
        )

        result = sync_pending_shipments_tracking_task.run(tenant_id=self.tenant.id, limit=10)

        self.assertEqual(result, {})
