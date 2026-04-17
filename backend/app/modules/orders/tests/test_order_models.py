from django.test import TestCase

from app.modules.orders.models import Order, OrderItem
from app.modules.tenants.models import Tenant


class OrderReadinessModelTests(TestCase):
    def test_order_and_order_item_persist_minimal_admin_read_data(self):
        tenant = Tenant.objects.create(
            name="Hubx Orders Demo",
            slug="hubx-orders-demo",
            subdomain="hubx-orders-demo",
        )

        order = Order.objects.create(
            tenant=tenant,
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
        self.assertEqual(stored.number, "1048")
        self.assertEqual(stored.payment_status, "Confirmado")
        self.assertEqual(stored.items.count(), 1)
        self.assertEqual(stored.items.first().title, "Tênis Hubx Runner")
