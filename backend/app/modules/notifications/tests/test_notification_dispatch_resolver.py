from django.test import SimpleTestCase

from app.modules.notifications.application.notification_dispatch_resolver import (
    resolve_notification_dispatch_previews,
)


class NotificationDispatchResolverTests(SimpleTestCase):
    def test_resolves_customer_and_owner_previews_for_event(self):
        previews = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=42,
            entity_type="order",
            entity_id=3051,
        )

        self.assertEqual(
            {preview.intent_key for preview in previews},
            {"customer.payment.failed", "owner.payment.failed"},
        )
        self.assertEqual({preview.tenant_id for preview in previews}, {"42"})
        self.assertTrue(all(preview.channel == "email" for preview in previews))

    def test_filters_previews_by_audience(self):
        previews = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=42,
            entity_type="order",
            entity_id=3051,
            audience="customer",
        )

        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0].intent_key, "customer.payment.failed")
        self.assertEqual(previews[0].audience, "customer")

    def test_preview_contains_tenant_scoped_idempotency_key(self):
        previews = resolve_notification_dispatch_previews(
            source_event="shipment.sent",
            tenant_id="tenant-a",
            entity_type="shipment",
            entity_id="ship-9",
            audience="customer",
        )

        self.assertEqual(len(previews), 1)
        self.assertEqual(previews[0].idempotency_key, "tenant-a:customer.shipment.sent:shipment:ship-9:email")
        self.assertEqual(previews[0].cta_target, "customer_order_detail")

    def test_returns_empty_preview_for_unknown_or_incomplete_context(self):
        self.assertEqual(
            resolve_notification_dispatch_previews(
                source_event="unknown.event",
                tenant_id=42,
                entity_type="order",
                entity_id=3051,
            ),
            [],
        )
        self.assertEqual(
            resolve_notification_dispatch_previews(
                source_event="payment.failed",
                tenant_id="",
                entity_type="order",
                entity_id=3051,
            ),
            [],
        )
