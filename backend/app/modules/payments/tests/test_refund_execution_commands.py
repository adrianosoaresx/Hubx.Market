from dataclasses import dataclass
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from app.modules.orders.models import Order
from app.modules.payments.application.refund_execution_commands import payment_refund_execution_commands
from app.modules.payments.infrastructure.provider_adapters import ProviderAdapterError, RefundProviderResponse
from app.modules.payments.models import PaymentAttempt, PaymentRefund
from app.modules.tenants.models import Tenant


@dataclass
class StubRefundAdapter:
    response: RefundProviderResponse | None = None
    error: ProviderAdapterError | None = None

    def create_refund(self, *, contract):
        if self.error is not None:
            raise self.error
        return self.response


class PaymentRefundExecutionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Refund Execution Tenant", slug="refund-execution", subdomain="refund-execution")
        self.other_tenant = Tenant.objects.create(name="Other Refund Execution", slug="other-refund-execution", subdomain="other-refund-execution")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9911",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9911",
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
            external_reference="ch_9911",
            paid_at=timezone.now(),
        )
        self.refund = PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-9911",
            status=PaymentRefund.Status.PROCESSING,
            amount="120.00",
            currency_code="BRL",
            provider_code="pagarme",
            external_reference="ch_9911",
            reason_code="customer-request",
            metadata={"provider_call": "not-executed"},
            requested_at=timezone.now(),
        )

    def test_execute_refund_records_accepted_response_and_keeps_processing(self):
        adapter = StubRefundAdapter(
            response=RefundProviderResponse(
                provider_code="pagarme",
                provider_refund_reference="rf_9911",
                status="accepted",
                payload_snapshot={"provider_call": "lite"},
            )
        )

        with patch("app.modules.payments.application.refund_execution_commands.get_provider_adapter", return_value=adapter):
            result, refund = payment_refund_execution_commands.execute_refund(
                tenant_id=self.tenant.id,
                refund_key=str(self.refund.refund_key),
            )

        self.assertEqual(result, "refund-execution-accepted")
        self.assertEqual(refund.status, PaymentRefund.Status.PROCESSING)
        self.assertEqual(refund.provider_refund_reference, "rf_9911")
        self.assertEqual(refund.metadata["provider_refund"]["status"], "accepted")
        self.assertEqual(refund.metadata["provider_refund"]["payload_snapshot"]["provider_call"], "lite")

    def test_execute_refund_records_succeeded_response_without_touching_order_or_attempt(self):
        adapter = StubRefundAdapter(
            response=RefundProviderResponse(
                provider_code="pagarme",
                provider_refund_reference="rf_9911",
                status="succeeded",
                payload_snapshot={"status": "succeeded"},
            )
        )

        with patch("app.modules.payments.application.refund_execution_commands.get_provider_adapter", return_value=adapter):
            result, refund = payment_refund_execution_commands.execute_refund(
                tenant_id=self.tenant.id,
                refund_key=str(self.refund.refund_key),
            )

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()
        self.assertEqual(result, "refund-execution-succeeded")
        self.assertEqual(refund.status, PaymentRefund.Status.SUCCEEDED)
        self.assertIsNotNone(refund.completed_at)
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.PAID)

    def test_execute_refund_records_failed_response(self):
        adapter = StubRefundAdapter(
            response=RefundProviderResponse(
                provider_code="pagarme",
                provider_refund_reference="rf_9911",
                status="failed",
                payload_snapshot={"reason": "provider-refused"},
            )
        )

        with patch("app.modules.payments.application.refund_execution_commands.get_provider_adapter", return_value=adapter):
            result, refund = payment_refund_execution_commands.execute_refund(
                tenant_id=self.tenant.id,
                refund_key=str(self.refund.refund_key),
            )

        self.assertEqual(result, "refund-execution-failed")
        self.assertEqual(refund.status, PaymentRefund.Status.FAILED)
        self.assertIsNotNone(refund.failed_at)
        self.assertEqual(refund.metadata["provider_refund"]["status"], "failed")

    def test_execute_refund_marks_failed_when_adapter_raises(self):
        adapter = StubRefundAdapter(error=ProviderAdapterError("provider-offline"))

        with patch("app.modules.payments.application.refund_execution_commands.get_provider_adapter", return_value=adapter):
            result, refund = payment_refund_execution_commands.execute_refund(
                tenant_id=self.tenant.id,
                refund_key=str(self.refund.refund_key),
            )

        self.assertEqual(result, "refund-execution-failed")
        self.assertEqual(refund.status, PaymentRefund.Status.FAILED)
        self.assertEqual(refund.metadata["provider_refund"]["reason_code"], "provider-offline")

    def test_execute_refund_blocks_cross_tenant_lookup(self):
        result, refund = payment_refund_execution_commands.execute_refund(
            tenant_id=self.other_tenant.id,
            refund_key=str(self.refund.refund_key),
        )

        self.assertEqual(result, "refund-execution-unavailable")
        self.assertIsNone(refund)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, PaymentRefund.Status.PROCESSING)

    def test_execute_refund_blocks_invalid_state_and_records_blockers(self):
        self.refund.status = PaymentRefund.Status.REQUESTED
        self.refund.save(update_fields=["status", "updated_at"])

        result, refund = payment_refund_execution_commands.execute_refund(
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
        )

        self.assertEqual(result, "refund-execution-blocked")
        self.assertEqual(refund.status, PaymentRefund.Status.REQUESTED)
        self.assertIn("refund-status-not-processing", refund.metadata["execution_blockers"])
