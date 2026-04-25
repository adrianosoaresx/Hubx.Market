from django.test import TestCase

from app.modules.notifications.application.notification_dispatch_envelopes import (
    build_notification_dispatch_envelope,
)
from app.modules.notifications.application.notification_dispatch_resolver import (
    resolve_notification_dispatch_previews,
)
from app.modules.notifications.application.notification_log_writer import record_email_log_from_envelope
from app.modules.notifications.application.notification_recipient_targets import build_customer_recipient_target
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationLogWriterTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste",
            subdomain="loja-teste",
        )

    def test_records_email_log_from_envelope(self):
        envelope = self._build_customer_payment_failed_envelope()

        result = record_email_log_from_envelope(envelope=envelope)

        self.assertTrue(result.created)
        self.assertEqual(EmailLog.objects.count(), 1)
        self.assertEqual(str(result.log.tenant_id), str(self.tenant.id))
        self.assertEqual(result.log.intent_key, "customer.payment.failed")
        self.assertEqual(result.log.recipient_email, "customer@example.com")
        self.assertEqual(result.log.status, EmailLog.Status.PLANNED)

    def test_reuses_existing_email_log_by_recipient_delivery_key(self):
        envelope = self._build_customer_payment_failed_envelope()
        first = record_email_log_from_envelope(envelope=envelope)

        second = record_email_log_from_envelope(envelope=envelope)

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.log.id, second.log.id)
        self.assertEqual(EmailLog.objects.count(), 1)

    def _build_customer_payment_failed_envelope(self):
        preview = resolve_notification_dispatch_previews(
            source_event="payment.failed",
            tenant_id=self.tenant.id,
            entity_type="order",
            entity_id=3051,
            audience="customer",
        )[0]
        recipient = build_customer_recipient_target(
            tenant_id=self.tenant.id,
            customer_id=99,
            email="customer@example.com",
            display_name="Cliente",
        )
        return build_notification_dispatch_envelope(preview=preview, recipient=recipient)
