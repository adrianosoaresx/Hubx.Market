from django.test import TestCase

from app.modules.shipping.application.delivery_promise_queries import delivery_promise_queries


class DeliveryPromiseQueryTests(TestCase):
    def test_pre_checkout_promise_requires_tenant(self):
        self.assertEqual(delivery_promise_queries.get_pre_checkout_promise(tenant_id=None), {})

    def test_pre_checkout_promise_is_honest_about_final_checkout_selection(self):
        payload = delivery_promise_queries.get_pre_checkout_promise(tenant_id=1)

        self.assertEqual(payload["title"], "Entrega no próximo passo")
        self.assertIn("checkout", payload["description"])
        self.assertEqual(len(payload["items"]), 2)
        self.assertEqual(payload["items"][0]["label"], "Entrega padrão")
        self.assertIn("A partir de", payload["items"][0]["price_hint"])
        self.assertIn("dependem do endereço", payload["note"])
