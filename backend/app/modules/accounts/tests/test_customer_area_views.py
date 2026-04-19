from django.test import TestCase
from django.urls import reverse

from app.modules.accounts.models import AccountProfile
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.accounts.application.account_customer_area_queries import (
    account_customer_area_queries,
)
from app.modules.orders.models import Order


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

    def test_account_addresses_page_renders_create_form_when_intent_present(self):
        response = self.client.get(reverse("accounts:account-addresses"), {"intent": "create"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adicionar endereço")
        self.assertContains(response, 'name="line_1"')

    def test_account_addresses_page_renders_feedback_message_when_result_present(self):
        response = self.client.get(reverse("accounts:account-addresses"), {"result": "address-created"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Endereço salvo")

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
        self.assertEqual(orders_payload["operational_linkage_visibility"]["orders_mode"], "fixture")


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
        self.assertIn("histórico já está salvo", orders_payload["page_description"].lower())
        self.assertIn("retomar o acompanhamento", orders_payload["table_description"].lower())
        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(order_detail_payload["payment_status"], "Confirmado")
        self.assertEqual(order_detail_payload["shipping_status"], "Preparando envio")
        self.assertEqual(order_detail_payload["subtotal"], "R$ 249,90")
        self.assertEqual(order_detail_payload["total"], "R$ 269,80")
        self.assertEqual(order_detail_payload["order_items"][0]["title"], "Tênis Hubx Area")
        self.assertIn("pagamento confirmado", order_detail_payload["summary_content"].lower())
        self.assertIn("entrega em preparando envio", order_detail_payload["summary_content"].lower())
        self.assertEqual(order_detail_payload["summary_subtitle"], "Atualizado há 2 dias")
        self.assertIn("pagamento já foi aprovado", order_detail_payload["summary_note"].lower())
        self.assertIn("Entrega prevista para Rua Persistida, 321", order_detail_payload["summary_note"])
        self.assertIn("próxima compra mais simples", order_detail_payload["summary_note"].lower())
        self.assertIn("atualizado há 2 dias", order_detail_payload["page_meta"].lower())
        self.assertEqual(order_detail_payload["activity_items"][-1]["title"], "Histórico salvo na sua conta")
        self.assertIn("primeiro pedido", order_detail_payload["activity_items"][-1]["description"].lower())

        self.assertEqual(addresses_payload["addresses"][0]["title"], "Casa")
        self.assertIn("Rua Persistida, 321", addresses_payload["addresses"][0]["content"])
        self.assertIn("CEP 01010-100", addresses_payload["addresses"][0]["footer"])

        self.assertEqual(profile_payload["email"], "ana.area@hubx.market")
        self.assertEqual(profile_payload["last_name"], "Área")
        self.assertEqual(orders_payload["operational_linkage_visibility"]["profile_mode"], "explicit")
        self.assertEqual(orders_payload["operational_linkage_visibility"]["orders_mode"], "explicit")
        self.assertEqual(addresses_payload["operational_linkage_visibility"]["addresses_mode"], "explicit")
        self.assertEqual(order_detail_payload["operational_linkage_mode"], "explicit")
        self.assertEqual(profile_payload["operational_linkage_mode"], "explicit")

    def test_customer_area_query_service_prefers_explicit_links_when_available(self):
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(order_detail_payload["payment_status"], "Confirmado")

    def test_customer_area_query_service_falls_back_to_tenant_and_email_when_links_are_absent(self):
        AccountProfile.objects.filter(pk=2).update(customer=None)
        Order.objects.filter(pk=2).update(customer=None, customer_email="ana.area@hubx.market")

        orders = account_customer_area_queries.list_orders()
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("3051")
        addresses_payload = account_customer_area_queries.get_addresses_page_data()

        self.assertEqual(len(orders), 1)
        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(addresses_payload["addresses"][0]["title"], "Casa")
        self.assertEqual(account_customer_area_queries.get_linkage_visibility()["profile_mode"], "fallback")
        self.assertEqual(account_customer_area_queries.get_linkage_visibility()["orders_mode"], "fallback")

    def test_customer_area_views_render_persisted_records_when_present(self):
        orders_response = self.client.get(reverse("accounts:account-orders"))
        order_detail_response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))
        addresses_response = self.client.get(reverse("accounts:account-addresses"))
        profile_response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(orders_response.status_code, 200)
        self.assertContains(orders_response, "#3051")
        self.assertContains(orders_response, "Pago · pagamento confirmado · entrega preparando envio · atualizado há 2 dias · histórico salvo")
        self.assertContains(orders_response, "Atualizado em 16/04/2026")

        self.assertEqual(order_detail_response.status_code, 200)
        self.assertContains(order_detail_response, "Pedido #3051")
        self.assertContains(order_detail_response, "Tênis Hubx Area")
        self.assertContains(order_detail_response, "Entrega em Rua Persistida, 321 · São Paulo/SP · última atualização em 16/04/2026 · atualizado há 2 dias")
        self.assertContains(order_detail_response, "Entrega prevista para Rua Persistida, 321")
        self.assertContains(order_detail_response, "Status atual confirmado")
        self.assertContains(order_detail_response, "Pagamento e entrega acompanhados")
        self.assertContains(order_detail_response, "acompanhamento contínuo pela área do cliente")
        self.assertContains(order_detail_response, "Histórico salvo na sua conta")

        self.assertEqual(addresses_response.status_code, 200)
        self.assertContains(addresses_response, "Rua Persistida, 321")
        self.assertContains(addresses_response, "Escritório")
        self.assertContains(addresses_response, '/accounts/account/addresses/1/edit/')
        self.assertContains(addresses_response, '/accounts/account/addresses/new/')

        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, "ana.area@hubx.market")
        self.assertContains(profile_response, "Área")

    def test_account_overview_uses_retention_messaging_when_persisted_orders_exist(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "histórico já começou")
        self.assertContains(response, "acompanhar seu pedido atual")

    def test_account_address_create_persists_customer_address(self):
        response = self.client.post(
            reverse("accounts:account-address-create"),
            {
                "label": "Casa nova",
                "recipient_name": "Ana Área",
                "line_1": "Rua Nova, 500",
                "line_2": "Casa 2",
                "district": "Jardins",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "01400-000",
                "is_default": "1",
            },
        )

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-created#address-management", fetch_redirect_response=False)

        refreshed = self.client.get(reverse("accounts:account-addresses"))
        self.assertContains(refreshed, "Casa nova")
        self.assertContains(refreshed, "Rua Nova, 500")

    def test_account_address_edit_updates_customer_address(self):
        response = self.client.post(
            reverse("accounts:account-address-edit", kwargs={"address_id": 1}),
            {
                "label": "Casa atualizada",
                "recipient_name": "Ana Área",
                "line_1": "Rua Persistida, 999",
                "line_2": "Apto 99",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "01010-100",
                "is_default": "1",
            },
        )

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-updated#address-management", fetch_redirect_response=False)

        refreshed = self.client.get(reverse("accounts:account-addresses"))
        self.assertContains(refreshed, "Casa atualizada")
        self.assertContains(refreshed, "Rua Persistida, 999")

    def test_account_address_delete_removes_current_customer_address(self):
        confirmation = self.client.get(reverse("accounts:account-addresses"), {"intent": "delete", "address_id": "1"})
        self.assertContains(confirmation, "Remover endereço")

        response = self.client.post(reverse("accounts:account-address-delete", kwargs={"address_id": 1}))

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-deleted#address-management", fetch_redirect_response=False)

        refreshed = self.client.get(reverse("accounts:account-addresses"))
        self.assertNotContains(refreshed, "Rua Persistida, 321")
        self.assertContains(refreshed, "Escritório")

    def test_account_address_delete_does_not_remove_another_customer_address(self):
        customer = Customer.objects.create(
            tenant_id=7,
            slug="outro-customer",
            reference="#7788",
            full_name="Outro Customer",
            email="outro@hubx.market",
            phone="(11) 94444-0000",
            status="active",
            account_type="Storefront",
        )
        address = CustomerAddress.objects.create(
            customer=customer,
            label="Outro endereço",
            recipient_name="Outro Customer",
            line_1="Rua de Outro, 10",
            district="Centro",
            city="São Paulo",
            state="SP",
            postal_code="01000-000",
            is_default=False,
        )

        response = self.client.post(reverse("accounts:account-address-delete", kwargs={"address_id": address.pk}))

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-delete-blocked#address-management", fetch_redirect_response=False)
        self.assertTrue(CustomerAddress.objects.filter(pk=address.pk).exists())

    def test_account_address_create_shows_inline_feedback_when_form_is_invalid(self):
        response = self.client.post(
            reverse("accounts:account-address-create"),
            {
                "label": "",
                "recipient_name": "Ana Área",
                "line_1": "",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revise os campos do endereço")
        self.assertContains(response, "Este campo é obrigatório")
