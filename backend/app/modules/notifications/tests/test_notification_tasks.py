from django.test import TestCase, override_settings

from app.modules.notifications.models import EmailLog
from app.modules.notifications.tasks import process_email_log_task, process_planned_email_logs_task
from app.modules.tenants.models import Tenant


class NotificationTaskTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Task", slug="loja-task", subdomain="loja-task")

    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=True)
    def test_process_email_log_task_delegates_to_delivery_command(self):
        log = self._create_log("1")

        result = process_email_log_task.run(tenant_id=self.tenant.id, log_id=log.id)

        self.assertEqual(result, "email-log-dry-run")
        log.refresh_from_db()
        self.assertEqual(log.status, EmailLog.Status.SKIPPED)

    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=True)
    def test_process_planned_email_logs_task_processes_limited_batch(self):
        first = self._create_log("1")
        second = self._create_log("2")

        result = process_planned_email_logs_task.run(tenant_id=self.tenant.id, limit=1)

        first.refresh_from_db()
        second.refresh_from_db()
        self.assertEqual(result, {"email-log-dry-run": 1})
        self.assertEqual(first.status, EmailLog.Status.SKIPPED)
        self.assertEqual(second.status, EmailLog.Status.PLANNED)

    def _create_log(self, suffix: str):
        return EmailLog.objects.create(
            tenant=self.tenant,
            source_event="payment.paid",
            intent_key="customer.payment.confirmed",
            audience="customer",
            entity_type="order",
            entity_id=suffix,
            idempotency_key=f"{self.tenant.id}:customer.payment.confirmed:order:{suffix}:email",
            recipient_delivery_key=f"{self.tenant.id}:customer.payment.confirmed:order:{suffix}:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento confirmado",
        )
