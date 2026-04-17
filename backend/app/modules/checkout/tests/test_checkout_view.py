from django.test import TestCase
from django.urls import reverse

from app.modules.checkout.application.checkout_page_queries import checkout_page_queries


class CheckoutViewTests(TestCase):
    def test_checkout_view_renders_design_system_template(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/checkout_page.html")
        self.assertContains(response, "Finalizar compra")
        self.assertContains(response, "Tênis Hubx Runner")

    def test_checkout_view_contains_payment_and_shipping_options(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrega padrão")
        self.assertContains(response, "Cartão de crédito")

    def test_checkout_query_service_returns_expected_contract(self):
        payload = checkout_page_queries.get_checkout_page_data()

        self.assertEqual(payload["page_title"], "Finalizar compra")
        self.assertEqual(payload["shipping_method_selected"], "standard")
        self.assertEqual(payload["payment_method_selected"], "credit_card")
        self.assertEqual(payload["order_items"][0]["title"], "Tênis Hubx Runner")


class CheckoutPersistedReadTests(TestCase):
    fixtures = ["checkout_minimal_seed.json"]

    def test_checkout_query_service_uses_persisted_session_when_available(self):
        payload = checkout_page_queries.get_checkout_page_data()

        self.assertTrue(checkout_page_queries.using_persisted_source())
        self.assertEqual(payload["first_name"], "Ana")
        self.assertEqual(payload["email"], "ana.persisted@hubx.market")
        self.assertEqual(payload["shipping_method_selected"], "express")
        self.assertEqual(payload["payment_method_selected"], "pix")
        self.assertEqual(payload["subtotal"], "R$ 459,80")
        self.assertEqual(payload["discount_total"], "-R$ 15,00")
        self.assertEqual(payload["order_items"][0]["title"], "Tênis Hubx Runner Persistido")
        self.assertEqual(payload["order_items"][0]["price"], "R$ 399,90")
        self.assertEqual(payload["checkout_steps"][0]["state"], "complete")
        self.assertEqual(payload["checkout_steps"][1]["state"], "complete")
        self.assertEqual(payload["checkout_steps"][2]["state"], "complete")
        self.assertEqual(payload["checkout_steps"][3]["state"], "upcoming")
        self.assertIn("2 item(ns)", payload["page_description"])
        self.assertIn("Entrega expressa", payload["page_description"])
        self.assertIn("PIX", payload["page_description"])

    def test_checkout_view_renders_persisted_session_when_present(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/checkout_page.html")
        self.assertContains(response, "ana.persisted@hubx.market")
        self.assertContains(response, "Entrega expressa")
        self.assertContains(response, "PIX")
        self.assertContains(response, "Tênis Hubx Runner Persistido")
        self.assertContains(response, "Revise 2 item(ns) antes de concluir o pedido.")
