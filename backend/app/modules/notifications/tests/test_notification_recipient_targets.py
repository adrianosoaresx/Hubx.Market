from django.test import SimpleTestCase

from app.modules.notifications.application.notification_recipient_targets import (
    build_customer_recipient_target,
    build_owner_recipient_target,
)


class NotificationRecipientTargetTests(SimpleTestCase):
    def test_builds_customer_target_without_mixing_identity_type(self):
        target = build_customer_recipient_target(
            tenant_id=42,
            customer_id=3051,
            email=" customer@example.com ",
            display_name=" Cliente ",
        )

        self.assertIsNotNone(target)
        self.assertEqual(target.tenant_id, "42")
        self.assertEqual(target.audience, "customer")
        self.assertEqual(target.recipient_type, "customer")
        self.assertEqual(target.recipient_id, "3051")
        self.assertEqual(target.email, "customer@example.com")
        self.assertEqual(target.display_name, "Cliente")
        self.assertTrue(target.is_deliverable)

    def test_builds_owner_target_as_owner_user(self):
        target = build_owner_recipient_target(
            tenant_id="tenant-a",
            owner_id="7",
            email="owner@example.com",
        )

        self.assertIsNotNone(target)
        self.assertEqual(target.tenant_id, "tenant-a")
        self.assertEqual(target.audience, "owner")
        self.assertEqual(target.recipient_type, "owner_user")
        self.assertEqual(target.recipient_id, "7")

    def test_target_without_email_is_not_deliverable(self):
        target = build_customer_recipient_target(
            tenant_id=42,
            customer_id=3051,
            email="",
        )

        self.assertIsNotNone(target)
        self.assertFalse(target.is_deliverable)

    def test_returns_none_without_tenant_or_identity_context(self):
        self.assertIsNone(
            build_customer_recipient_target(
                tenant_id="",
                customer_id=3051,
                email="customer@example.com",
            )
        )
        self.assertIsNone(
            build_owner_recipient_target(
                tenant_id=42,
                owner_id="",
                email="owner@example.com",
            )
        )
