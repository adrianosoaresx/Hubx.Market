from django.test import SimpleTestCase

from app.modules.notifications.application.notification_dispatch_envelopes import (
    build_notification_dispatch_envelope,
)
from app.modules.notifications.application.notification_dispatch_resolver import (
    resolve_notification_dispatch_previews,
)
from app.modules.notifications.application.notification_recipient_targets import (
    build_customer_recipient_target,
    build_owner_recipient_target,
)


class NotificationDispatchEnvelopeTests(SimpleTestCase):
    def test_builds_envelope_from_matching_preview_and_recipient(self):
        preview = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=42,
            entity_type="order",
            entity_id=3051,
            audience="customer",
        )[0]
        recipient = build_customer_recipient_target(
            tenant_id=42,
            customer_id=99,
            email="customer@example.com",
            display_name="Cliente",
        )

        envelope = build_notification_dispatch_envelope(preview=preview, recipient=recipient)

        self.assertIsNotNone(envelope)
        self.assertEqual(envelope.tenant_id, "42")
        self.assertEqual(envelope.intent_key, "customer.payment.failed")
        self.assertEqual(envelope.recipient_type, "customer")
        self.assertEqual(envelope.recipient_email, "customer@example.com")
        self.assertEqual(
            envelope.recipient_delivery_key,
            "42:customer.payment.failed:order:3051:email:customer:99",
        )

    def test_rejects_cross_tenant_recipient(self):
        preview = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=42,
            entity_type="order",
            entity_id=3051,
            audience="customer",
        )[0]
        recipient = build_customer_recipient_target(
            tenant_id=43,
            customer_id=99,
            email="customer@example.com",
        )

        self.assertIsNone(build_notification_dispatch_envelope(preview=preview, recipient=recipient))

    def test_rejects_mismatched_audience(self):
        preview = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=42,
            entity_type="order",
            entity_id=3051,
            audience="customer",
        )[0]
        recipient = build_owner_recipient_target(
            tenant_id=42,
            owner_id=7,
            email="owner@example.com",
        )

        self.assertIsNone(build_notification_dispatch_envelope(preview=preview, recipient=recipient))

    def test_rejects_recipient_without_delivery_address(self):
        preview = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=42,
            entity_type="order",
            entity_id=3051,
            audience="customer",
        )[0]
        recipient = build_customer_recipient_target(
            tenant_id=42,
            customer_id=99,
            email="",
        )

        self.assertIsNone(build_notification_dispatch_envelope(preview=preview, recipient=recipient))
