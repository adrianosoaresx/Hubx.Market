from django.test import TestCase
from django.urls import reverse

from app.modules.accounts.application.account_customer_area_queries import (
    account_customer_area_queries,
)


class CustomerAreaViewTests(TestCase):
    def test_account_orders_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-orders"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/orders_page.html")
        self.assertContains(response, "Meus pedidos")
        self.assertContains(response, "#1048")

    def test_account_orders_view_applies_search_filter(self):
        response = self.client.get(reverse("accounts:account-orders"), {"q": "1041"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#1041")
        self.assertNotContains(response, "#1048")

    def test_account_order_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "1048"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/order_detail_page.html")
        self.assertContains(response, "Pedido #1048")
        self.assertContains(response, "Tênis Hubx Runner")

    def test_account_addresses_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-addresses"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/addresses_page.html")
        self.assertContains(response, "Meus endereços")
        self.assertContains(response, "Casa")

    def test_account_address_readiness_routes_redirect_back_to_addresses_page(self):
        create_response = self.client.get(reverse("accounts:account-address-create"))
        edit_response = self.client.get(reverse("accounts:account-address-edit", kwargs={"address_id": 1}))
        delete_response = self.client.get(reverse("accounts:account-address-delete", kwargs={"address_id": 1}))

        self.assertRedirects(create_response, "/accounts/account/addresses/?intent=create#address-management", fetch_redirect_response=False)
        self.assertRedirects(edit_response, "/accounts/account/addresses/?intent=edit&address_id=1#address-management", fetch_redirect_response=False)
        self.assertRedirects(delete_response, "/accounts/account/addresses/?intent=delete&address_id=1#address-management", fetch_redirect_response=False)

    def test_account_profile_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/profile_page.html")
        self.assertContains(response, "Meu perfil")
        self.assertContains(response, "ana@hubx.market")

    def test_account_customer_area_query_service_returns_expected_contract(self):
        orders_payload = account_customer_area_queries.get_orders_page_data()
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("1048")
        profile_payload = account_customer_area_queries.get_profile_page_data()

        self.assertEqual(orders_payload["page_title"], "Meus pedidos")
        self.assertEqual(order_detail_payload["order_number"], "#1048")
        self.assertEqual(profile_payload["email"], "ana@hubx.market")


class CustomerAreaPersistedProfileTests(TestCase):
    fixtures = ["accounts_minimal_seed.json"]

    def test_customer_area_query_service_uses_persisted_profile_when_available(self):
        profile_payload = account_customer_area_queries.get_profile_page_data()

        self.assertTrue(account_customer_area_queries.using_persisted_profile_source())
        self.assertEqual(profile_payload["email"], "ana.persisted@hubx.market")
        self.assertEqual(profile_payload["last_name"], "Persistida")
        self.assertFalse(profile_payload["order_updates_opt_in"])

    def test_account_profile_view_renders_persisted_profile_when_present(self):
        response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/profile_page.html")
        self.assertContains(response, "ana.persisted@hubx.market")
        self.assertContains(response, "Persistida")


class CustomerAreaPersistedReadTests(TestCase):
    fixtures = ["customer_area_minimal_seed.json"]

    def test_customer_area_query_service_uses_persisted_sources_when_available(self):
        orders_payload = account_customer_area_queries.get_orders_page_data()
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("3051")
        addresses_payload = account_customer_area_queries.get_addresses_page_data()
        profile_payload = account_customer_area_queries.get_profile_page_data()

        self.assertTrue(account_customer_area_queries.using_persisted_profile_source())
        self.assertTrue(account_customer_area_queries.using_persisted_orders_source())
        self.assertTrue(account_customer_area_queries.using_persisted_addresses_source())

        self.assertEqual(orders_payload["page_title"], "Meus pedidos")
        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(order_detail_payload["payment_status"], "Confirmado")
        self.assertEqual(order_detail_payload["shipping_status"], "Preparando envio")
        self.assertEqual(order_detail_payload["subtotal"], "R$ 249,90")
        self.assertEqual(order_detail_payload["total"], "R$ 269,80")
        self.assertEqual(order_detail_payload["order_items"][0]["title"], "Tênis Hubx Area")
        self.assertIn("pagamento confirmado", order_detail_payload["summary_content"].lower())

        self.assertEqual(addresses_payload["addresses"][0]["title"], "Casa")
        self.assertIn("Rua Persistida, 321", addresses_payload["addresses"][0]["content"])
        self.assertIn("CEP 01010-100", addresses_payload["addresses"][0]["footer"])

        self.assertEqual(profile_payload["email"], "ana.area@hubx.market")
        self.assertEqual(profile_payload["last_name"], "Área")

    def test_customer_area_views_render_persisted_records_when_present(self):
        orders_response = self.client.get(reverse("accounts:account-orders"))
        order_detail_response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))
        addresses_response = self.client.get(reverse("accounts:account-addresses"))
        profile_response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(orders_response.status_code, 200)
        self.assertContains(orders_response, "#3051")
        self.assertContains(orders_response, "Confirmado")

        self.assertEqual(order_detail_response.status_code, 200)
        self.assertContains(order_detail_response, "Pedido #3051")
        self.assertContains(order_detail_response, "Tênis Hubx Area")
        self.assertContains(order_detail_response, "Entrega em Rua Persistida, 321")
        self.assertContains(order_detail_response, "Entrega residencial em horário comercial.")

        self.assertEqual(addresses_response.status_code, 200)
        self.assertContains(addresses_response, "Rua Persistida, 321")
        self.assertContains(addresses_response, "Escritório")
        self.assertContains(addresses_response, '/accounts/account/addresses/1/edit/')
        self.assertContains(addresses_response, '/accounts/account/addresses/new/')

        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, "ana.area@hubx.market")
        self.assertContains(profile_response, "Área")
