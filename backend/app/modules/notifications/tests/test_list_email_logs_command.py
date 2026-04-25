from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class ListEmailLogsCommandTests(TestCase):
    def test_lists_tenant_logs_for_operations(self):
        tenant = Tenant.objects.create(name="Loja List", slug="loja-list-email", subdomain="loja-list-email")
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
        call_command("list_email_logs", tenant_id=str(tenant.id), status=EmailLog.Status.FAILED, stdout=output)

        self.assertIn("intent=customer.payment.failed", output.getvalue())
        self.assertIn("Listed 1 email log(s).", output.getvalue())

    def test_lists_stale_tenant_logs_for_operations(self):
        tenant = Tenant.objects.create(name="Loja Stale", slug="loja-stale-email", subdomain="loja-stale-email")
        stale_log = EmailLog.objects.create(
            tenant=tenant,
            source_event="order.created",
            intent_key="customer.order.received",
            audience="customer",
            entity_type="order",
            entity_id="1",
            idempotency_key=f"{tenant.id}:customer.order.received:order:1:email",
            recipient_delivery_key=f"{tenant.id}:customer.order.received:order:1:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pedido recebido",
            status=EmailLog.Status.REQUESTED,
        )
        EmailLog.objects.create(
            tenant=tenant,
            source_event="order.created",
            intent_key="owner.order.created",
            audience="owner",
            entity_type="order",
            entity_id="1",
            idempotency_key=f"{tenant.id}:owner.order.created:order:1:email",
            recipient_delivery_key=f"{tenant.id}:owner.order.created:order:1:email:owner:99",
            recipient_type="owner",
            recipient_id="99",
            recipient_email="owner@example.com",
            title="Pedido recebido",
            status=EmailLog.Status.REQUESTED,
        )
        EmailLog.objects.filter(id=stale_log.id).update(updated_at=timezone.now() - timedelta(hours=8))

        output = StringIO()
        call_command(
            "list_email_logs",
            tenant_id=str(tenant.id),
            status=EmailLog.Status.REQUESTED,
            stale_hours=6,
            stdout=output,
        )

        self.assertIn("intent=customer.order.received", output.getvalue())
        self.assertNotIn("intent=owner.order.created", output.getvalue())
        self.assertIn("Listed 1 email log(s).", output.getvalue())
