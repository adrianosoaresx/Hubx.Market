from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class NotificationReadinessCommandTests(TestCase):
    def test_prints_tenant_scoped_readiness_summary(self):
        tenant = Tenant.objects.create(name="Loja Teste", slug="loja-readiness-cmd", subdomain="loja-readiness-cmd")
        EmailLog.objects.create(
            tenant=tenant,
            source_event="payment.failed",
            intent_key="customer.payment.failed",
            audience="customer",
            entity_type="order",
            entity_id="1",
            idempotency_key=f"{tenant.id}:customer.payment.failed:order:1:email",
            recipient_delivery_key=f"{tenant.id}:customer.payment.failed:order:1:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento falhou",
            status=EmailLog.Status.FAILED,
        )

        output = StringIO()
        call_command("notification_readiness", tenant_id=str(tenant.id), stdout=output)

        self.assertIn(f"tenant={tenant.id}", output.getvalue())
        self.assertIn("total=1", output.getvalue())
        self.assertIn("failed=1", output.getvalue())
        self.assertIn("failures=true", output.getvalue())
