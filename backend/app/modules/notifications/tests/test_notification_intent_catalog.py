from django.test import SimpleTestCase

from app.modules.notifications.application.notification_intent_catalog import (
    build_idempotency_key,
    get_notification_intent,
    list_notification_intents,
)


class NotificationIntentCatalogTests(SimpleTestCase):
    def test_catalog_lists_customer_and_owner_transactional_intents(self):
        intents = list_notification_intents()
        intent_keys = {intent.intent_key for intent in intents}

        self.assertIn("customer.order.received", intent_keys)
        self.assertIn("customer.payment.confirmed", intent_keys)
        self.assertIn("customer.payment.failed", intent_keys)
        self.assertIn("customer.shipment.sent", intent_keys)
        self.assertIn("customer.shipment.delivered", intent_keys)
        self.assertIn("owner.order.created", intent_keys)
        self.assertIn("owner.payment.failed", intent_keys)
        self.assertIn("owner.shipment.delivered", intent_keys)

    def test_catalog_filters_by_audience_and_source_event(self):
        customer_intents = list_notification_intents(audience="customer")
        payment_failed_intents = list_notification_intents(source_event="payment.failed")

        self.assertTrue(customer_intents)
        self.assertTrue(all(intent.audience == "customer" for intent in customer_intents))
        self.assertEqual(
            {intent.intent_key for intent in payment_failed_intents},
            {"customer.payment.failed", "owner.payment.failed"},
        )

    def test_catalog_returns_intent_by_key(self):
        intent = get_notification_intent("customer.payment.failed")

        self.assertIsNotNone(intent)
        self.assertEqual(intent.source_event, "payment.failed")
        self.assertEqual(intent.audience, "customer")
        self.assertEqual(intent.channel, "email")
        self.assertIn("pedido continua salvo", intent.description)

    def test_idempotency_key_includes_tenant_intent_entity_and_channel(self):
        intent = get_notification_intent("customer.order.received")

        key = build_idempotency_key(
            intent=intent,
            tenant_id=42,
            entity_type="order",
            entity_id="3051",
        )

        self.assertEqual(key, "42:customer.order.received:order:3051:email")
