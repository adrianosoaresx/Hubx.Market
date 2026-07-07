from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.application.admin_merchant_operations_queries import admin_merchant_operations_queries
from app.modules.accounts.models import OwnerUser
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class AdminMerchantOperationsViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Merchant Ops",
            slug="loja-merchant-ops",
            subdomain="loja-merchant-ops",
        )
        self.other_tenant = Tenant.objects.create(
            name="Outra Merchant Ops",
            slug="outra-merchant-ops",
            subdomain="outra-merchant-ops",
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def _login_owner(self, *, email: str, role: str):
        OwnerUser.objects.create(tenant=self.tenant, email=email, role=role, is_active=True)
        user = User.objects.create_user(username=email, email=email, password="secret")
        self.client.force_login(user)
        return user

    def test_merchant_ops_dashboard_renders_operational_cockpit(self):
        response = self.client.get(
            reverse("merchant_ops:admin-dashboard"),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_dashboard_page.html")
        self.assertContains(response, "Operação da loja")
        self.assertContains(response, "Pedidos pendentes")
        self.assertContains(response, "/ops/orders/")
        self.assertContains(response, "Filas operacionais")
        self.assertContains(response, 'aria-label="Tema da interface"')
        self.assertContains(response, "Claro")
        self.assertContains(response, "Escuro")
        self.assertContains(response, "Sistema")
        self.assertNotContains(response, 'href="/catalog/"')
        self.assertNotContains(response, 'href="/cart/"')
        self.assertNotContains(response, 'href="/accounts/account/orders/"')

    def test_merchant_ops_dashboard_keeps_logout_without_customer_top_menu(self):
        self._login_owner(email="owner.ops@hubx.market", role="owner")

        response = self.client.get(reverse("merchant_ops:admin-dashboard"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertContains(response, "Sair")
        self.assertNotContains(response, 'href="/catalog/"')
        self.assertNotContains(response, 'href="/cart/"')
        self.assertNotContains(response, 'href="/accounts/account/orders/"')

    def test_merchant_ops_dashboard_personalizes_navigation_for_support(self):
        self._login_owner(email="support.ops@hubx.market", role="support")

        response = self.client.get(reverse("merchant_ops:admin-dashboard"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/ops/orders/")
        self.assertContains(response, "/ops/customers/")
        self.assertContains(response, "/ops/reviews/")
        self.assertNotContains(response, "/ops/coupons/")
        self.assertNotContains(response, "/ops/pages/")
        self.assertNotContains(response, "/ops/payments/finance/")

    def test_merchant_ops_dashboard_personalizes_navigation_for_marketing(self):
        self._login_owner(email="marketing.ops@hubx.market", role="marketing")

        response = self.client.get(reverse("merchant_ops:admin-dashboard"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/ops/catalog/products/")
        self.assertContains(response, "/ops/coupons/")
        self.assertContains(response, "/ops/pages/")
        self.assertContains(response, "/ops/reviews/")
        self.assertNotContains(response, "/ops/orders/")
        self.assertNotContains(response, "/ops/customers/")
        self.assertNotContains(response, "/ops/payments/refunds/")

    def test_merchant_ops_dashboard_filters_operational_tasks_by_permission(self):
        self._login_owner(email="support.tasks@hubx.market", role="support")
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="paused.tasks@hubx.market",
            full_name="Paused Tasks",
            receives_notifications=False,
        )
        Order.objects.create(
            tenant=self.tenant,
            number="OPS-TASK",
            status=Order.Status.PENDING,
            customer_email="cliente@hubx.market",
            payment_status="Aguardando PIX",
        )

        response = self.client.get(reverse("merchant_ops:admin-dashboard"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedidos")
        self.assertNotContains(response, "Owners inativos ou com notificações administrativas pausadas")

    def test_merchant_ops_dashboard_scopes_signals_to_resolved_tenant(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="paused@hubx.market",
            full_name="Paused Owner",
            receives_notifications=False,
        )
        OwnerUser.objects.create(
            tenant=self.other_tenant,
            email="other-paused@hubx.market",
            full_name="Other Paused Owner",
            receives_notifications=False,
        )
        Order.objects.create(
            tenant=self.tenant,
            number="OPS-1",
            status=Order.Status.PENDING,
            customer_email="cliente@hubx.market",
            payment_status="Aguardando PIX",
        )
        Order.objects.create(
            tenant=self.other_tenant,
            number="OPS-2",
            status=Order.Status.PENDING,
            customer_email="outro@hubx.market",
            payment_status="Aguardando PIX",
        )

        dashboard = admin_merchant_operations_queries.get_dashboard(tenant_id=self.tenant.id)

        task_counts = {task["area"]: task["count"] for task in dashboard["tasks"]}
        self.assertEqual(task_counts["Pedidos"], 1)
        self.assertEqual(task_counts["Owners"], 1)
