from django.test import TestCase, override_settings

from app.modules.notifications.infrastructure.email_delivery import EmailDeliveryAdapter
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class EmailDeliveryAdapterTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-delivery",
            subdomain="loja-teste-delivery",
        )
        self.log = EmailLog.objects.create(
            tenant=self.tenant,
            source_event="payment.paid",
            intent_key="customer.payment.confirmed",
            audience="customer",
            entity_type="order",
            entity_id="",
            idempotency_key="1:customer.payment.confirmed:order:3051:email",
            recipient_delivery_key="1:customer.payment.confirmed:order:3051:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento confirmado",
            description="O pagamento foi confirmado.",
            cta_label="Ver pedido",
            cta_target="customer_order_detail",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="3051",
            customer_email="customer@example.com",
            total="10.00",
        )
        self.log.entity_id = str(self.order.id)
        self.log.save(update_fields=("entity_id", "updated_at"))

    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=True)
    def test_dry_run_does_not_send_email(self):
        result = EmailDeliveryAdapter().deliver(log=self.log)

        self.assertEqual(result.status, "dry-run")
        self.assertIn("dry-run", result.message)

    @override_settings(
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
        EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    )
    def test_real_mode_uses_django_email_backend(self):
        from django.core import mail

        result = EmailDeliveryAdapter().deliver(log=self.log)

        self.assertEqual(result.status, "sent")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["customer@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Pagamento confirmado")
        self.assertIn("https://loja-teste-delivery.hubx.market/accounts/account/orders/3051/", mail.outbox[0].body)

    @override_settings(NOTIFICATIONS_EMAIL_DRY_RUN=False, DEFAULT_FROM_EMAIL="")
    def test_real_mode_requires_from_email(self):
        result = EmailDeliveryAdapter().deliver(log=self.log)

        self.assertEqual(result.status, "failed")
        self.assertIn("DEFAULT_FROM_EMAIL", result.message)
