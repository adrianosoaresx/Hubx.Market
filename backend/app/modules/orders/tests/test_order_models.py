from django.test import TestCase

from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.tenants.models import Tenant


class OrderReadinessModelTests(TestCase):
    def test_order_and_order_item_persist_minimal_admin_read_data(self):
        tenant = Tenant.objects.create(
            name="Hubx Orders Demo",
            slug="hubx-orders-demo",
            subdomain="hubx-orders-demo",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="ana-souza",
            reference="#1048",
            full_name="Ana Souza",
            email="ana@hubx.market",
        )

        order = Order.objects.create(
            tenant=tenant,
            customer=customer,
            number="1048",
            status="paid",
            customer_name="Ana Souza",
            customer_email="ana@hubx.market",
            customer_phone="(11) 99999-0000",
            fulfillment_status_label="Separando itens",
            fulfillment_status_variant="info",
            payment_status="Confirmado",
            shipping_status="Separando itens",
            shipping_address_summary="Rua das Laranjeiras, 100 · São Paulo/SP",
            notes_content="Entrega em horário comercial.",
            subtotal="299.90",
            shipping_total="24.90",
            discount_total="0.00",
            total="324.80",
            installments_summary="3x de R$ 108,26 sem juros",
        )
        OrderItem.objects.create(
            order=order,
            title="Tênis Hubx Runner",
            subtitle="Preto · 42",
            meta="SKU RUNNER-001-BLK-42",
            price_snapshot="299.90",
            quantity=1,
            sort_order=1,
        )

        stored = Order.objects.prefetch_related("items").get(pk=order.pk)

        self.assertEqual(stored.tenant, tenant)
        self.assertEqual(stored.customer, customer)
        self.assertEqual(stored.number, "1048")
        self.assertEqual(stored.payment_status, "Confirmado")
        self.assertEqual(stored.items.count(), 1)
        self.assertEqual(stored.items.first().title, "Tênis Hubx Runner")

    def test_order_auto_populates_customer_when_match_is_unambiguous(self):
        tenant = Tenant.objects.create(
            name="Hubx Auto Link Orders",
            slug="hubx-auto-link-orders",
            subdomain="hubx-auto-link-orders",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="ana-order-auto-link",
            reference="#O-1",
            full_name="Ana Order Auto",
            email="ana.order@hubx.market",
        )

        order = Order.objects.create(
            tenant=tenant,
            number="2049",
            customer_name="Ana Order Auto",
            customer_email="ana.order@hubx.market",
        )

        order.refresh_from_db()
        self.assertEqual(order.customer, customer)

    def test_order_auto_populate_is_noop_when_match_is_ambiguous(self):
        tenant = Tenant.objects.create(
            name="Hubx Ambiguous Orders",
            slug="hubx-ambiguous-orders",
            subdomain="hubx-ambiguous-orders",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="ana-order-ambiguous-a",
            reference="#O-2A",
            full_name="Ana Order Ambiguous",
            email="ana.order.ambiguous@hubx.market",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="ana-order-ambiguous-b",
            reference="#O-2B",
            full_name="Ana Order Ambiguous 2",
            email="ANA.ORDER.AMBIGUOUS@hubx.market",
        )

        order = Order.objects.create(
            tenant=tenant,
            number="2050",
            customer_name="Ana Order Ambiguous",
            customer_email="ana.order.ambiguous@hubx.market",
        )

        order.refresh_from_db()
        self.assertIsNone(order.customer)
