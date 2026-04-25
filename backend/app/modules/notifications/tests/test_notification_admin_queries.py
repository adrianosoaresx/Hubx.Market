from django.test import TestCase

from app.modules.notifications.application.notification_admin_queries import list_admin_email_logs
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationAdminQueryTests(TestCase):
    def test_lists_tenant_scoped_email_logs_with_status_filter(self):
        tenant = Tenant.objects.create(name="Loja Admin", slug="loja-admin-notif", subdomain="loja-admin-notif")
        other_tenant = Tenant.objects.create(name="Outra Admin", slug="outra-admin-notif", subdomain="outra-admin-notif")
        failed = self._create_log(tenant, suffix="1", status=EmailLog.Status.FAILED)
        self._create_log(tenant, suffix="2", status=EmailLog.Status.PLANNED)
        self._create_log(other_tenant, suffix="3", status=EmailLog.Status.FAILED)

        items = list_admin_email_logs(tenant_id=tenant.id, status=EmailLog.Status.FAILED)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].id, failed.id)
        self.assertEqual(items[0].tenant_id, str(tenant.id))
        self.assertEqual(items[0].status, EmailLog.Status.FAILED)

    def _create_log(self, tenant, *, suffix: str, status: str):
        return EmailLog.objects.create(
            tenant=tenant,
            source_event="payment.failed",
            intent_key="customer.payment.failed",
            audience="customer",
            entity_type="order",
            entity_id=suffix,
            idempotency_key=f"{tenant.id}:customer.payment.failed:order:{suffix}:email",
            recipient_delivery_key=f"{tenant.id}:customer.payment.failed:order:{suffix}:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email=f"customer{suffix}@example.com",
            title="Pagamento falhou",
            status=status,
        )
