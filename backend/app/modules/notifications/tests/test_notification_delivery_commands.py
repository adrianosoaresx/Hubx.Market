from dataclasses import dataclass

from django.test import TestCase

from app.modules.notifications.application.notification_delivery_commands import EmailDeliveryCommandService
from app.modules.notifications.infrastructure.email_delivery import EmailDeliveryResult
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


@dataclass
class StubEmailDeliveryAdapter:
    status: str
    message: str

    def deliver(self, *, log: EmailLog) -> EmailDeliveryResult:
        return EmailDeliveryResult(status=self.status, message=self.message)


class NotificationDeliveryCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-command-delivery",
            subdomain="loja-teste-command-delivery",
        )
        self.other_tenant = Tenant.objects.create(
            name="Outra Loja",
            slug="outra-loja-command-delivery",
            subdomain="outra-loja-command-delivery",
        )
        self.log = self._create_log()

    def test_processes_log_as_dry_run_skip(self):
        service = EmailDeliveryCommandService(
            adapter=StubEmailDeliveryAdapter(status="dry-run", message="dry-run active")
        )

        result = service.process_email_log(tenant_id=self.tenant.id, log_id=self.log.id)

        self.assertEqual(result.result, "email-log-dry-run")
        self.assertEqual(result.log.status, EmailLog.Status.SKIPPED)
        self.assertEqual(result.log.last_error, "dry-run active")
        self.assertIsNotNone(result.log.requested_at)

    def test_processes_log_as_sent(self):
        service = EmailDeliveryCommandService(adapter=StubEmailDeliveryAdapter(status="sent", message="accepted"))

        result = service.process_email_log(tenant_id=self.tenant.id, log_id=self.log.id)

        self.assertEqual(result.result, "email-log-sent")
        self.assertEqual(result.log.status, EmailLog.Status.SENT)
        self.assertIsNotNone(result.log.sent_at)

    def test_processes_log_as_failed(self):
        service = EmailDeliveryCommandService(adapter=StubEmailDeliveryAdapter(status="failed", message="provider down"))

        result = service.process_email_log(tenant_id=self.tenant.id, log_id=self.log.id)

        self.assertEqual(result.result, "email-log-failed")
        self.assertEqual(result.log.status, EmailLog.Status.FAILED)
        self.assertEqual(result.log.last_error, "provider down")

    def test_does_not_process_cross_tenant_log(self):
        service = EmailDeliveryCommandService(adapter=StubEmailDeliveryAdapter(status="sent", message="accepted"))

        result = service.process_email_log(tenant_id=self.other_tenant.id, log_id=self.log.id)

        self.assertEqual(result.result, "email-log-unavailable")
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, EmailLog.Status.PLANNED)

    def _create_log(self):
        return EmailLog.objects.create(
            tenant=self.tenant,
            source_event="payment.paid",
            intent_key="customer.payment.confirmed",
            audience="customer",
            entity_type="order",
            entity_id="3051",
            idempotency_key="1:customer.payment.confirmed:order:3051:email",
            recipient_delivery_key="1:customer.payment.confirmed:order:3051:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento confirmado",
        )
