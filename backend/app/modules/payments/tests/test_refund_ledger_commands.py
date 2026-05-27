from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from app.modules.orders.models import Order
from app.modules.payments.application.refund_ledger_commands import payment_refund_ledger_commands
from app.modules.payments.models import PaymentAttempt, PaymentRefund
from app.modules.tenants.models import Tenant


class PaymentRefundLedgerCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Refund Ledger Tenant", slug="refund-ledger", subdomain="refund-ledger")
        self.other_tenant = Tenant.objects.create(name="Other Refund Ledger Tenant", slug="other-refund-ledger", subdomain="other-refund-ledger")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9701",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9701",
            total="120.00",
        )
        self.attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9701",
            paid_at=timezone.now(),
        )

    def test_request_refund_intent_creates_requested_ledger_without_mutating_order_or_attempt(self):
        result, refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            idempotency_key="refund-9701",
            reason_code="customer-request",
        )

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(result, "refund-intent-ready")
        self.assertEqual(refund.status, PaymentRefund.Status.REQUESTED)
        self.assertEqual(refund.payment_attempt_id, self.attempt.id)
        self.assertEqual(refund.amount, self.order.total)
        self.assertEqual(refund.external_reference, "ch_9701")
        self.assertEqual(refund.metadata["provider_call"], "not-executed")
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.PAID)

    def test_request_refund_intent_is_idempotent_per_tenant(self):
        first_result, first_refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            idempotency_key="refund-9701",
        )
        second_result, second_refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            idempotency_key="refund-9701",
        )

        self.assertEqual(first_result, "refund-intent-ready")
        self.assertEqual(second_result, "refund-intent-ready")
        self.assertEqual(first_refund.id, second_refund.id)
        self.assertEqual(PaymentRefund.objects.filter(tenant=self.tenant).count(), 1)

    def test_request_refund_intent_blocks_shipped_order_with_ledger_record(self):
        self.order.status = "shipped"
        self.order.save(update_fields=["status", "updated_at"])

        result, refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            idempotency_key="refund-shipped-9701",
        )

        self.assertEqual(result, "refund-intent-blocked")
        self.assertEqual(refund.status, PaymentRefund.Status.BLOCKED)
        self.assertIn("order-already-shipped", refund.blockers)

    def test_request_refund_intent_requires_tenant_and_idempotency_key(self):
        missing_tenant_result, missing_tenant_refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=None,
            order_number=self.order.number,
            idempotency_key="refund-missing-tenant",
        )
        missing_key_result, missing_key_refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            idempotency_key="",
        )

        self.assertEqual(missing_tenant_result, "refund-intent-blocked")
        self.assertIsNone(missing_tenant_refund)
        self.assertEqual(missing_key_result, "refund-intent-blocked")
        self.assertIsNone(missing_key_refund)
        self.assertFalse(PaymentRefund.objects.exists())

    def test_request_refund_intent_does_not_cross_tenant_order_scope(self):
        result, refund = payment_refund_ledger_commands.request_refund_intent(
            tenant_id=self.other_tenant.id,
            order_number=self.order.number,
            idempotency_key="refund-cross-tenant",
        )

        self.assertEqual(result, "refund-intent-unavailable")
        self.assertIsNone(refund)
        self.assertFalse(PaymentRefund.objects.exists())

    def test_request_payment_refund_intent_command_outputs_ledger_contract(self):
        stdout = StringIO()

        call_command(
            "request_payment_refund_intent",
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            idempotency_key="refund-command-9701",
            reason_code="support-approved",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("payment_refund_intent result=refund-intent-ready", output)
        self.assertIn("order_number=9701", output)
        self.assertIn("status=requested", output)
        self.assertIn("external_reference=ch_9701", output)
