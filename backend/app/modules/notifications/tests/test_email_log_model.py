from django.db import IntegrityError
from django.test import TestCase

from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class EmailLogModelTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste",
            subdomain="loja-teste",
        )

    def test_email_log_defaults_to_planned_status(self):
        log = EmailLog.objects.create(
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

        self.assertEqual(log.status, EmailLog.Status.PLANNED)
        self.assertEqual(log.channel, "email")
        self.assertEqual(str(log), f"{self.tenant.id}:customer.payment.failed:planned")

    def test_recipient_delivery_key_is_unique(self):
        payload = {
            "tenant": self.tenant,
            "source_event": "payment.failed",
            "intent_key": "customer.payment.failed",
            "audience": "customer",
            "entity_type": "order",
            "entity_id": "3051",
            "idempotency_key": "1:customer.payment.failed:order:3051:email",
            "recipient_delivery_key": "1:customer.payment.failed:order:3051:email:customer:99",
            "recipient_type": "customer",
            "recipient_id": "99",
            "recipient_email": "customer@example.com",
            "title": "Pagamento não concluído",
        }
        EmailLog.objects.create(**payload)

        with self.assertRaises(IntegrityError):
            EmailLog.objects.create(**payload)
