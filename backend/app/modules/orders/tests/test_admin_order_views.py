from django.test import TestCase
from django.urls import reverse

from app.modules.orders.application.admin_order_queries import admin_order_queries


class AdminOrderViewTests(TestCase):
    def test_orders_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("orders:admin-orders-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_orders_list_page.html")
        self.assertContains(response, "Pedidos")
        self.assertContains(response, "#1048")

    def test_orders_list_view_applies_search_filter(self):
        response = self.client.get(reverse("orders:admin-orders-list"), {"q": "Bruno"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#1049")
        self.assertNotContains(response, "#1048")

    def test_order_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "1048"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_order_detail_page.html")
        self.assertContains(response, "Pedido #1048")
        self.assertContains(response, "Ana Souza")

    def test_admin_order_query_service_returns_expected_contract(self):
        order = admin_order_queries.get_order("1048")

        self.assertEqual(order["order_number"], "1048")
        self.assertEqual(order["order_status_label"], "Pago")
        self.assertEqual(order["customer"], "Ana Souza")

    def test_admin_order_query_service_reports_persisted_source_readiness(self):
        self.assertFalse(admin_order_queries.using_persisted_source())


class AdminOrderPersistedReadTests(TestCase):
    fixtures = ["orders_minimal_seed.json"]

    def test_admin_order_query_service_uses_persisted_records_when_available(self):
        order = admin_order_queries.get_order("2048")

        self.assertTrue(admin_order_queries.using_persisted_source())
        self.assertEqual(order["order_number"], "2048")
        self.assertEqual(order["customer"], "Ana Persistida")
        self.assertEqual(order["payment_status"], "Confirmado")
        self.assertEqual(order["shipping_status"], "Preparando envio")
        self.assertEqual(order["subtotal"], "R$ 399,90")
        self.assertEqual(order["discount"], "-R$ 10,00")
        self.assertEqual(order["order_items"][0]["title"], "Tênis Hubx Runner Persistido")
        self.assertIn("Pedido #2048 de Ana Persistida", order["summary_content"])
        self.assertIn("ana.persisted@hubx.market", order["customer_content"])
        self.assertIn("Rua Persistida, 200", order["shipping_content"])
        self.assertEqual(order["updated_at"], "14/04/2026 às 12:00")
        self.assertGreaterEqual(len(order["activity_items"]), 2)

    def test_admin_order_views_render_persisted_records_when_present(self):
        list_response = self.client.get(reverse("orders:admin-orders-list"))
        detail_response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "#2048")
        self.assertContains(list_response, "Ana Persistida")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/admin_order_detail_page.html")
        self.assertContains(detail_response, "Pedido #2048")
        self.assertContains(detail_response, "Ana Persistida")
        self.assertContains(detail_response, "Rua Persistida, 200")
