from django.test import TestCase

from app.modules.accounts.models import OwnerUser
from app.modules.customers.models import Customer
from app.modules.notifications.application.notification_event_handlers import notification_event_handlers
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class NotificationEventHandlerTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-eventos",
            subdomain="loja-teste-eventos",
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-eventos",
            full_name="Cliente Eventos",
            email="cliente.eventos@example.com",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9001",
            status="pending",
            customer_name="Cliente Eventos",
            customer_email="cliente.eventos@example.com",
            total="99.90",
        )

    def test_records_customer_email_log_for_payment_failed_event(self):
        results = notification_event_handlers.record_customer_order_event_email_logs(
            tenant_id=self.tenant.id,
            source_event="payment.failed",
            order_number="9001",
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].created)
        log = EmailLog.objects.get()
        self.assertEqual(log.tenant_id, self.tenant.id)
        self.assertEqual(log.source_event, "payment.failed")
        self.assertEqual(log.intent_key, "customer.payment.failed")
        self.assertEqual(log.recipient_type, "customer")
        self.assertEqual(log.recipient_id, str(self.customer.id))
        self.assertEqual(log.recipient_email, "cliente.eventos@example.com")

    def test_reuses_existing_email_log_for_replayed_event(self):
        first = notification_event_handlers.record_customer_order_event_email_logs(
            tenant_id=self.tenant.id,
            source_event="payment.failed",
            order_number="9001",
        )
        second = notification_event_handlers.record_customer_order_event_email_logs(
            tenant_id=self.tenant.id,
            source_event="payment.failed",
            order_number="9001",
        )

        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertTrue(first[0].created)
        self.assertFalse(second[0].created)
        self.assertEqual(EmailLog.objects.count(), 1)

    def test_skips_event_without_customer_identity(self):
        self.order.customer = None
        self.order.customer_email = "guest@example.com"
        self.order.save(update_fields=("customer", "customer_email", "updated_at"))

        results = notification_event_handlers.record_customer_order_event_email_logs(
            tenant_id=self.tenant.id,
            source_event="payment.failed",
            order_number="9001",
        )

        self.assertEqual(results, [])
        self.assertEqual(EmailLog.objects.count(), 0)

    def test_records_owner_email_log_for_payment_failed_event(self):
        owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner@example.com",
            full_name="Owner Example",
        )

        results = notification_event_handlers.record_owner_order_event_email_logs(
            tenant_id=self.tenant.id,
            source_event="payment.failed",
            order_number="9001",
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].created)
        log = EmailLog.objects.get()
        self.assertEqual(log.intent_key, "owner.payment.failed")
        self.assertEqual(log.recipient_type, "owner_user")
        self.assertEqual(log.recipient_id, str(owner.id))
        self.assertEqual(log.recipient_email, "owner@example.com")
