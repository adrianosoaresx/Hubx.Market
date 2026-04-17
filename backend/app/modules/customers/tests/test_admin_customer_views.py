from django.test import TestCase
from django.urls import reverse

from app.modules.customers.application.admin_customer_queries import admin_customer_queries


class AdminCustomerViewTests(TestCase):
    def test_customers_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("customers:admin-customers-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_customers_list_page.html")
        self.assertContains(response, "Clientes")
        self.assertContains(response, "Ana Souza")

    def test_customers_list_view_applies_search_filter(self):
        response = self.client.get(reverse("customers:admin-customers-list"), {"q": "Bruno"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bruno Lima")
        self.assertNotContains(response, "Ana Souza")

    def test_customer_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-souza"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_customer_detail_page.html")
        self.assertContains(response, "Ana Souza")
        self.assertContains(response, "#8821")

    def test_admin_customer_query_service_returns_expected_contract(self):
        customer = admin_customer_queries.get_customer("ana-souza")

        self.assertEqual(customer["slug"], "ana-souza")
        self.assertEqual(customer["customer_status_label"], "Ativo")
        self.assertEqual(customer["email"], "ana@hubx.market")

    def test_admin_customer_query_service_reports_persisted_source_readiness(self):
        self.assertFalse(admin_customer_queries.using_persisted_source())


class AdminCustomerPersistedReadTests(TestCase):
    fixtures = ["customers_minimal_seed.json"]

    def test_admin_customer_query_service_uses_persisted_records_when_available(self):
        customer = admin_customer_queries.get_customer("ana-persistida")

        self.assertTrue(admin_customer_queries.using_persisted_source())
        self.assertEqual(customer["slug"], "ana-persistida")
        self.assertEqual(customer["name"], "Ana Persistida")
        self.assertEqual(customer["customer_status_label"], "VIP")
        self.assertEqual(customer["account_type_label"], "Storefront")
        self.assertEqual(customer["customer_reference"], "#9901")
        self.assertEqual(customer["last_activity"], "15/04/2026 às 17:45")
        self.assertEqual(customer["customer_since"], "10/04/2026 às 12:30")
        self.assertEqual(customer["last_seen"], "15/04/2026 às 16:10")
        self.assertIn("Cliente Ana Persistida com status vip", customer["summary_content"])
        self.assertIn("ana.persistida@hubx.market", customer["contact_content"])
        self.assertIn("telefone (11) 98888-1111", customer["profile_content"])
        self.assertIn("#9901", customer["account_notes_content"])
        self.assertEqual(len(customer["activity_items"]), 2)

    def test_admin_customer_views_render_persisted_records_when_present(self):
        list_response = self.client.get(reverse("customers:admin-customers-list"))
        detail_response = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Ana Persistida")
        self.assertContains(list_response, "VIP")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/admin_customer_detail_page.html")
        self.assertContains(detail_response, "Ana Persistida")
        self.assertContains(detail_response, "#9901")
        self.assertContains(detail_response, "ana.persistida@hubx.market")
