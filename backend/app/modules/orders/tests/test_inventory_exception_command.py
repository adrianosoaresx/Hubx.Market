from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.catalog.models import Product, ProductVariant
from app.modules.orders.application.inventory_exception_metrics_queries import inventory_exception_metrics_queries
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class ListInventoryExceptionsCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Inventory Ops", slug="loja-inventory-ops", subdomain="loja-inventory-ops")
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Estoque",
            slug="produto-estoque",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=self.product,
            sku="INV-001",
            price="10.00",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9801",
            status="pending",
            customer_name="Cliente Estoque",
            customer_email="estoque@example.com",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
            subtotal="10.00",
            total="10.00",
        )
        self.order.items.create(
            title="Produto Estoque",
            variant_sku="INV-001",
            price_snapshot="10.00",
            quantity=1,
        )
        self.review_order = Order.objects.create(
            tenant=self.tenant,
            number="9802",
            status="pending",
            customer_name="Cliente Revisão",
            customer_email="review@example.com",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        self.review_order.items.create(
            title="Produto Ausente",
            variant_sku="INV-MISSING",
            price_snapshot="10.00",
            quantity=1,
        )

    def test_list_inventory_exceptions_filters_active_exceptions(self):
        output = StringIO()

        call_command("list_inventory_exceptions", tenant_id=str(self.tenant.id), quick_filter="active", stdout=output)

        value = output.getvalue()
        self.assertIn("order_number=9801", value)
        self.assertIn("state=Exceção ativa", value)
        self.assertIn("inventory_exceptions=1", value)

    def test_list_inventory_exceptions_filters_assigned_review_exceptions(self):
        output = StringIO()

        call_command("list_inventory_exceptions", tenant_id=str(self.tenant.id), quick_filter="assigned", stdout=output)

        value = output.getvalue()
        self.assertIn("order_number=9802", value)
        self.assertIn("owner=Operação interna", value)
        self.assertIn("inventory_exceptions=1", value)

    def test_inventory_exception_metrics_export_prometheus_payload(self):
        payload = inventory_exception_metrics_queries.export_prometheus_metrics()

        self.assertIn("hubx_inventory_exception_total", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",state="excecao_ativa"', payload)
        self.assertIn("hubx_inventory_exception_priority_total", payload)
        self.assertIn("hubx_inventory_exception_owner_total", payload)

    @override_settings(INVENTORY_OBSERVABILITY_TOKEN="inventory-token")
    def test_inventory_exception_metrics_view_returns_payload_with_token(self):
        response = self.client.get(
            reverse("orders:inventory-exception-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="inventory-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])
        self.assertContains(response, "hubx_inventory_exception_total")

    @override_settings(INVENTORY_OBSERVABILITY_TOKEN="inventory-token")
    def test_inventory_exception_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("orders:inventory-exception-metrics"))

        self.assertEqual(response.status_code, 403)

    @override_settings(INVENTORY_OBSERVABILITY_TOKEN="", ORDERS_OBSERVABILITY_TOKEN="")
    def test_inventory_exception_metrics_view_is_not_found_without_token(self):
        response = self.client.get(reverse("orders:inventory-exception-metrics"))

        self.assertEqual(response.status_code, 404)
