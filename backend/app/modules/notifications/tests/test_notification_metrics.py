from django.test import TestCase

from app.modules.notifications.application.notification_metrics_queries import notification_metrics_queries
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationMetricsQueryTests(TestCase):
    def test_exports_email_log_status_counts(self):
        tenant = Tenant.objects.create(name="Loja Metrics", slug="loja-metrics", subdomain="loja-metrics")
        self._create_log(tenant, suffix="1", status=EmailLog.Status.PLANNED)
        self._create_log(tenant, suffix="2", status=EmailLog.Status.FAILED)

        payload = notification_metrics_queries.export_prometheus_metrics()

        self.assertIn("# HELP hubx_notifications_email_log_total", payload)
        self.assertIn(f'hubx_notifications_email_log_total{{tenant_id="{tenant.id}",status="planned"}} 1', payload)
        self.assertIn(f'hubx_notifications_email_log_total{{tenant_id="{tenant.id}",status="failed"}} 1', payload)

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
            recipient_email="customer@example.com",
            title="Pagamento falhou",
            status=status,
        )
