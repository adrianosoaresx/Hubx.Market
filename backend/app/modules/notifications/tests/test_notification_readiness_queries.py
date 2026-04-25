from django.test import TestCase

from app.modules.notifications.application.notification_readiness_queries import (
    get_notification_readiness_snapshot,
)
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationReadinessQueryTests(TestCase):
    def test_returns_tenant_scoped_status_counts(self):
        tenant = Tenant.objects.create(name="Loja Teste", slug="loja-readiness", subdomain="loja-readiness")
        other_tenant = Tenant.objects.create(name="Outra Loja", slug="outra-readiness", subdomain="outra-readiness")
        self._create_log(tenant, suffix="1", status=EmailLog.Status.PLANNED)
        self._create_log(tenant, suffix="2", status=EmailLog.Status.FAILED)
        self._create_log(other_tenant, suffix="3", status=EmailLog.Status.SENT)

        snapshot = get_notification_readiness_snapshot(tenant_id=tenant.id)

        self.assertEqual(snapshot.total, 2)
        self.assertEqual(snapshot.planned, 1)
        self.assertEqual(snapshot.failed, 1)
        self.assertEqual(snapshot.sent, 0)
        self.assertTrue(snapshot.has_pending_delivery)
        self.assertTrue(snapshot.has_failures)

    def _create_log(self, tenant, *, suffix: str, status: str):
        return EmailLog.objects.create(
            tenant=tenant,
            source_event="payment.paid",
            intent_key="customer.payment.confirmed",
            audience="customer",
            entity_type="order",
            entity_id=f"30{suffix}",
            idempotency_key=f"{tenant.id}:customer.payment.confirmed:order:30{suffix}:email",
            recipient_delivery_key=f"{tenant.id}:customer.payment.confirmed:order:30{suffix}:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento confirmado",
            status=status,
        )
