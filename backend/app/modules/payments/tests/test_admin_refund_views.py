from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.orders.models import Order
from app.modules.payments.models import PaymentAttempt, PaymentRefund
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class AdminPaymentRefundsViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Refund Ops Tenant", slug="refund-ops", subdomain="refund-ops")
        self.other_tenant = Tenant.objects.create(name="Other Refund Ops", slug="other-refund-ops", subdomain="other-refund-ops")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9801",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9801",
            total="120.00",
        )
        self.other_order = Order.objects.create(
            tenant=self.other_tenant,
            number="9802",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9802",
            total="80.00",
        )
        self.attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9801",
            paid_at=timezone.now(),
        )

    def test_admin_payment_refunds_view_renders_refund_ledger(self):
        PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-9801",
            status=PaymentRefund.Status.REQUESTED,
            amount="120.00",
            currency_code="BRL",
            provider_code="pagarme",
            external_reference="ch_9801",
            reason_code="customer-request",
            requested_at=timezone.now(),
        )

        response = self.client.get(
            reverse("payments_ops:admin-refunds"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_orders_list_page.html")
        self.assertContains(response, "Refunds de pagamentos")
        self.assertContains(response, "#9801")
        self.assertContains(response, "BRL 120.00")
        self.assertContains(response, "Solicitado")
        self.assertContains(response, "refund-9801")
        self.assertContains(response, "ch_9801")
        self.assertContains(response, "Aprovar internamente")
        self.assertContains(response, "Não executa estorno")

    def test_admin_payment_refunds_view_is_tenant_scoped(self):
        PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-9801",
            status=PaymentRefund.Status.REQUESTED,
            amount="120.00",
            external_reference="ch_9801",
        )
        PaymentRefund.objects.create(
            tenant=self.other_tenant,
            order=self.other_order,
            idempotency_key="refund-9802",
            status=PaymentRefund.Status.REQUESTED,
            amount="80.00",
            external_reference="ch_9802",
        )

        response = self.client.get(
            reverse("payments_ops:admin-refunds"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#9801")
        self.assertNotContains(response, "#9802")

    def test_admin_payment_refunds_view_filters_by_status(self):
        PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-requested-9801",
            status=PaymentRefund.Status.REQUESTED,
            amount="120.00",
        )
        PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-blocked-9801",
            status=PaymentRefund.Status.BLOCKED,
            amount="120.00",
            blockers=["order-already-shipped"],
        )

        response = self.client.get(
            f"{reverse('payments_ops:admin-refunds')}?status=blocked",
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "refund-blocked-9801")
        self.assertContains(response, "order-already-shipped")
        self.assertNotContains(response, "refund-requested-9801")

    def test_admin_payment_refunds_view_shows_empty_state(self):
        response = self.client.get(
            reverse("payments_ops:admin-refunds"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum refund registrado")

    def test_admin_payment_refund_approve_action_transitions_requested_refund(self):
        refund = PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-approve-9801",
            status=PaymentRefund.Status.REQUESTED,
            amount="120.00",
            currency_code="BRL",
            provider_code="pagarme",
            external_reference="ch_9801",
        )

        response = self.client.post(
            reverse("payments_ops:admin-refund-approve", kwargs={"refund_key": refund.refund_key}),
            {"approval_note": "Aprovado via teste ops."},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        refund.refresh_from_db()
        self.order.refresh_from_db()
        self.attempt.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("payments_ops:admin-refunds"))
        self.assertEqual(refund.status, PaymentRefund.Status.PROCESSING)
        self.assertEqual(refund.metadata["approved_by"], "Ops interno")
        self.assertEqual(refund.metadata["approval_note"], "Aprovado via teste ops.")
        self.assertEqual(refund.metadata["provider_call"], "not-executed")
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.PAID)

    def test_admin_payment_refund_approve_action_does_not_cross_tenant(self):
        refund = PaymentRefund.objects.create(
            tenant=self.other_tenant,
            order=self.other_order,
            idempotency_key="refund-other-9802",
            status=PaymentRefund.Status.REQUESTED,
            amount="80.00",
            external_reference="ch_9802",
        )

        response = self.client.post(
            reverse("payments_ops:admin-refund-approve", kwargs={"refund_key": refund.refund_key}),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        refund.refresh_from_db()

        self.assertEqual(response.status_code, 302)
        self.assertEqual(refund.status, PaymentRefund.Status.REQUESTED)
