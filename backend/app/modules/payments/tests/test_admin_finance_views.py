from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.orders.models import Order
from app.modules.payments.models import PaymentAttempt
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class AdminPaymentFinanceViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Finance Tenant", slug="finance-tenant", subdomain="finance-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Finance", slug="other-finance", subdomain="other-finance")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9501",
            status="pending",
            payment_status="Pagamento pendente",
            total="120.00",
        )
        self.other_order = Order.objects.create(
            tenant=self.other_tenant,
            number="9502",
            status="pending",
            payment_status="Pagamento pendente",
            total="80.00",
        )

    def test_admin_payment_finance_view_renders_reconciliation_issues(self):
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9501",
            paid_at=timezone.now(),
        )

        response = self.client.get(
            reverse("payments_ops:admin-finance"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_orders_list_page.html")
        self.assertContains(response, "Financeiro de pagamentos")
        self.assertContains(response, "Tentativa paga sem pedido confirmado")
        self.assertContains(response, "#9501")
        self.assertContains(response, "attempt_paid_order_unconfirmed")

    def test_admin_payment_finance_view_is_tenant_scoped(self):
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="110.00",
        )
        PaymentAttempt.objects.create(
            tenant=self.other_tenant,
            order=self.other_order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="70.00",
        )

        response = self.client.get(
            reverse("payments_ops:admin-finance"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#9501")
        self.assertNotContains(response, "#9502")

    def test_admin_payment_finance_view_shows_empty_state_when_clean(self):
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="120.00",
        )

        response = self.client.get(
            reverse("payments_ops:admin-finance"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma divergência financeira")
