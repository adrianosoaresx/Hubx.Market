from django.test import TestCase

from app.modules.notifications.application.notification_log_status_commands import (
    mark_email_log_failed,
    mark_email_log_requested,
    mark_email_log_sent,
    mark_email_log_skipped,
)
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationLogStatusCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-status",
            subdomain="loja-teste-status",
        )
        self.other_tenant = Tenant.objects.create(
            name="Outra Loja",
            slug="outra-loja-status",
            subdomain="outra-loja-status",
        )
        self.log = self._create_log()

    def test_marks_log_requested_with_tenant_scope(self):
        result = mark_email_log_requested(tenant_id=self.tenant.id, log_id=self.log.id)

        self.assertEqual(result.status, EmailLog.Status.REQUESTED)
        self.assertIsNotNone(result.requested_at)

    def test_does_not_update_log_from_another_tenant(self):
        result = mark_email_log_requested(tenant_id=self.other_tenant.id, log_id=self.log.id)

        self.assertIsNone(result)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, EmailLog.Status.PLANNED)

    def test_marks_requested_log_as_sent(self):
        mark_email_log_requested(tenant_id=self.tenant.id, log_id=self.log.id)

        result = mark_email_log_sent(tenant_id=self.tenant.id, log_id=self.log.id)

        self.assertEqual(result.status, EmailLog.Status.SENT)
        self.assertIsNotNone(result.sent_at)
        self.assertEqual(result.last_error, "")

    def test_does_not_fail_sent_log(self):
        mark_email_log_sent(tenant_id=self.tenant.id, log_id=self.log.id)

        result = mark_email_log_failed(tenant_id=self.tenant.id, log_id=self.log.id, error="provider down")

        self.assertEqual(result.status, EmailLog.Status.SENT)
        self.assertEqual(result.last_error, "")

    def test_marks_log_failed_with_error_snapshot(self):
        result = mark_email_log_failed(tenant_id=self.tenant.id, log_id=self.log.id, error="provider down")

        self.assertEqual(result.status, EmailLog.Status.FAILED)
        self.assertIsNotNone(result.failed_at)
        self.assertEqual(result.last_error, "provider down")

    def test_marks_planned_log_skipped(self):
        result = mark_email_log_skipped(tenant_id=self.tenant.id, log_id=self.log.id, reason="missing preference")

        self.assertEqual(result.status, EmailLog.Status.SKIPPED)
        self.assertEqual(result.last_error, "missing preference")

    def _create_log(self):
        return EmailLog.objects.create(
            tenant=self.tenant,
            source_event="payment.failed",
            intent_key="customer.payment.failed",
            audience="customer",
            entity_type="order",
            entity_id="3051",
            idempotency_key="1:customer.payment.failed:order:3051:email",
            recipient_delivery_key="1:customer.payment.failed:order:3051:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento não concluído",
        )
