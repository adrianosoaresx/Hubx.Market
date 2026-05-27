from django.test import TestCase
from django.utils import timezone

from app.modules.audit.models import AuditLog
from app.modules.orders.models import Order
from app.modules.payments.application.refund_approval_commands import payment_refund_approval_commands
from app.modules.payments.models import PaymentAttempt, PaymentRefund
from app.modules.tenants.models import Tenant


class PaymentRefundApprovalCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Refund Approval Tenant", slug="refund-approval", subdomain="refund-approval")
        self.other_tenant = Tenant.objects.create(name="Other Refund Approval", slug="other-refund-approval", subdomain="other-refund-approval")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9901",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9901",
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
            external_reference="ch_9901",
            paid_at=timezone.now(),
        )
        self.refund = PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-9901",
            status=PaymentRefund.Status.REQUESTED,
            amount="120.00",
            currency_code="BRL",
            provider_code="pagarme",
            external_reference="ch_9901",
            reason_code="customer-request",
            metadata={"provider_call": "not-executed"},
            requested_at=timezone.now(),
        )

    def test_approve_refund_transitions_requested_to_processing_without_provider_call(self):
        result, refund = payment_refund_approval_commands.approve_refund(
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            actor_label="Ops Ana",
            approval_note="Aprovado para execução futura.",
        )

        self.assertEqual(result, "refund-approval-ready")
        self.assertEqual(refund.status, PaymentRefund.Status.PROCESSING)
        self.assertEqual(refund.metadata["approved_by"], "Ops Ana")
        self.assertEqual(refund.metadata["approval_note"], "Aprovado para execução futura.")
        self.assertEqual(refund.metadata["approval_contract_version"], "refund-approval-v1")
        self.assertEqual(refund.metadata["provider_call"], "not-executed")
        log = AuditLog.objects.get(module="payments", action="refund.approved")
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.entity_type, "PaymentRefund")
        self.assertEqual(log.entity_id, str(refund.id))
        self.assertEqual(log.actor_label, "Ops Ana")
        self.assertEqual(log.metadata["refund_key"], str(refund.refund_key))
        self.assertEqual(log.metadata["amount"], "120.00")
        self.assertEqual(log.metadata["provider_call"], "not-executed")
        self.assertNotIn("external_reference", log.metadata)

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.PAID)

    def test_approve_refund_blocks_cross_tenant_lookup(self):
        result, refund = payment_refund_approval_commands.approve_refund(
            tenant_id=self.other_tenant.id,
            refund_key=str(self.refund.refund_key),
            actor_label="Ops Ana",
        )

        self.assertEqual(result, "refund-approval-unavailable")
        self.assertIsNone(refund)
        self.refund.refresh_from_db()
        self.assertEqual(self.refund.status, PaymentRefund.Status.REQUESTED)

    def test_approve_refund_blocks_refund_with_blockers(self):
        self.refund.blockers = ["order-already-shipped"]
        self.refund.save(update_fields=["blockers", "updated_at"])

        result, refund = payment_refund_approval_commands.approve_refund(
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            actor_label="Ops Ana",
        )

        self.assertEqual(result, "refund-approval-blocked")
        self.assertEqual(refund.status, PaymentRefund.Status.REQUESTED)
        self.assertIn("refund-has-blockers", refund.metadata["approval_blockers"])
        self.assertEqual(refund.metadata["provider_call"], "not-executed")

    def test_approve_refund_blocks_non_requested_status(self):
        self.refund.status = PaymentRefund.Status.PROCESSING
        self.refund.save(update_fields=["status", "updated_at"])

        result, refund = payment_refund_approval_commands.approve_refund(
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            actor_label="Ops Ana",
        )

        self.assertEqual(result, "refund-approval-blocked")
        self.assertEqual(refund.status, PaymentRefund.Status.PROCESSING)
        self.assertIn("refund-status-not-requested", refund.metadata["approval_blockers"])

    def test_approve_refund_requires_actor_attempt_reference_and_positive_amount(self):
        self.refund.payment_attempt = None
        self.refund.external_reference = ""
        self.refund.amount = "0.00"
        self.refund.save(update_fields=["payment_attempt", "external_reference", "amount", "updated_at"])

        result, refund = payment_refund_approval_commands.approve_refund(
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            actor_label="",
        )

        self.assertEqual(result, "refund-approval-blocked")
        self.assertEqual(refund.status, PaymentRefund.Status.REQUESTED)
        self.assertIn("approval-actor-missing", refund.metadata["approval_blockers"])
        self.assertIn("paid-attempt-missing", refund.metadata["approval_blockers"])
        self.assertIn("external-reference-missing", refund.metadata["approval_blockers"])
        self.assertIn("refund-amount-invalid", refund.metadata["approval_blockers"])
