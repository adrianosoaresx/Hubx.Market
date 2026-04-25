from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class ProcessEmailLogsCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-process-email",
            subdomain="loja-teste-process-email",
        )
        self.other_tenant = Tenant.objects.create(
            name="Outra Loja",
            slug="outra-loja-process-email",
            subdomain="outra-loja-process-email",
        )

    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=True)
    def test_processes_only_tenant_planned_logs_in_dry_run(self):
        first = self._create_log(self.tenant, suffix="1")
        second = self._create_log(self.tenant, suffix="2")
        other = self._create_log(self.other_tenant, suffix="3")

        call_command("process_email_logs", tenant_id=str(self.tenant.id), limit=1)

        first.refresh_from_db()
        second.refresh_from_db()
        other.refresh_from_db()
        self.assertEqual(first.status, EmailLog.Status.SKIPPED)
        self.assertEqual(second.status, EmailLog.Status.PLANNED)
        self.assertEqual(other.status, EmailLog.Status.PLANNED)

    def _create_log(self, tenant, *, suffix: str):
        return EmailLog.objects.create(
            tenant=tenant,
            source_event="payment.paid",
            intent_key="customer.payment.confirmed",
            audience="customer",
            entity_type="order",
            entity_id=f"305{suffix}",
            idempotency_key=f"{tenant.id}:customer.payment.confirmed:order:305{suffix}:email",
            recipient_delivery_key=f"{tenant.id}:customer.payment.confirmed:order:305{suffix}:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento confirmado",
        )
