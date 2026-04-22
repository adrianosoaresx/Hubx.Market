from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.application.account_page_queries import account_page_queries
from app.modules.accounts.models import AccountProfile
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.tenants.models import Tenant


class AccountViewTests(TestCase):
    def test_login_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/login_page.html")
        self.assertContains(response, "Entrar")
        self.assertContains(response, "Quando sua conta estiver vinculada a um perfil persistido")
        self.assertContains(response, "Acessar conta")

    def test_register_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:register"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/register_page.html")
        self.assertContains(response, "Criar conta")

    def test_forgot_password_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:forgot-password"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/forgot_password_page.html")
        self.assertContains(response, "Recuperar senha")

    def test_reset_password_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:reset-password"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/reset_password_page.html")
        self.assertContains(response, "Redefinir senha")

    def test_account_overview_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/account_overview_page.html")
        self.assertContains(response, "Minha conta")
        self.assertContains(response, "#1048")

    def test_account_page_query_service_returns_expected_contract(self):
        login_payload = account_page_queries.get_login_page_data()
        overview_payload = account_page_queries.get_account_overview_data()

        self.assertEqual(login_payload["page_title"], "Entrar")
        self.assertTrue(login_payload["remember_me"])
        self.assertEqual(login_payload["login_label"], "E-mail da conta")
        self.assertEqual(login_payload["primary_label"], "Acessar conta")
        self.assertEqual(login_payload["login_value"], "")
        self.assertEqual(login_payload["profile_mode"], "missing")
        self.assertEqual(overview_payload["page_title"], "Minha conta")
        self.assertEqual(overview_payload["summary_title"], "Resumo da conta")
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][0], "#1048")
        self.assertEqual(overview_payload["profile_mode"], "missing")
        self.assertIn("ainda não encontramos um perfil persistido", overview_payload["summary_content"].lower())
        self.assertIn("voltar ao catálogo", overview_payload["page_meta"].lower())


class AccountPersistedReadTests(TestCase):
    fixtures = ["accounts_minimal_seed.json"]

    def test_account_query_service_uses_persisted_profile_when_available(self):
        login_payload = account_page_queries.get_login_page_data()
        overview_payload = account_page_queries.get_account_overview_data()

        self.assertTrue(account_page_queries.using_persisted_source())
        self.assertEqual(login_payload["login_value"], "ana.persisted@hubx.market")
        self.assertIn("Ana Persistida", login_payload["helper_text"])
        self.assertIn("Ana Persistida", overview_payload["summary_content"])
        self.assertIn("newsletter ativa", overview_payload["summary_content"])
        self.assertIn("conta continua disponível para retomar pedidos", overview_payload["summary_content"])
        self.assertIn("14/04/2026", overview_payload["activity_content"])

    def test_account_overview_view_renders_persisted_profile_when_present(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/account_overview_page.html")
        self.assertContains(response, "Ana Persistida")
        self.assertContains(response, "qual é o melhor ponto de retorno")
        self.assertContains(response, "Voltar ao catálogo")

    def test_account_query_service_scopes_profile_by_tenant_when_requested(self):
        second_tenant = Tenant.objects.create(
            name="Second Accounts Demo",
            slug="second-accounts-demo",
            subdomain="second-accounts-demo",
            is_active=True,
        )
        AccountProfile.objects.create(
            tenant=second_tenant,
            email="bruna.persisted@hubx.market",
            first_name="Bruna",
            last_name="Escopo",
            phone="(21) 98888-0000",
            newsletter_opt_in=False,
            order_updates_opt_in=True,
            is_active=True,
        )

        self.assertTrue(account_page_queries.using_persisted_source(tenant_id=3))
        self.assertTrue(account_page_queries.using_persisted_source(tenant_id=second_tenant.id))

        tenant_one_login = account_page_queries.get_login_page_data(tenant_id=3)
        tenant_two_login = account_page_queries.get_login_page_data(tenant_id=second_tenant.id)
        tenant_one_overview = account_page_queries.get_account_overview_data(tenant_id=3)
        tenant_two_overview = account_page_queries.get_account_overview_data(tenant_id=second_tenant.id)

        self.assertEqual(tenant_one_login["login_value"], "ana.persisted@hubx.market")
        self.assertIn("Ana Persistida", tenant_one_login["helper_text"])
        self.assertIn("Ana Persistida", tenant_one_overview["summary_content"])
        self.assertIn("newsletter ativa", tenant_one_overview["summary_content"])

        self.assertEqual(tenant_two_login["login_value"], "bruna.persisted@hubx.market")
        self.assertIn("Bruna Escopo", tenant_two_login["helper_text"])
        self.assertIn("Bruna Escopo", tenant_two_overview["summary_content"])
        self.assertIn("atualizações de pedido ativas", tenant_two_overview["summary_content"])
        self.assertNotIn("newsletter ativa", tenant_two_overview["summary_content"])


class AccountOverviewContinuityTests(TestCase):
    fixtures = ["customer_area_minimal_seed.json"]

    def test_account_overview_uses_persisted_order_continuity_when_available(self):
        overview_payload = account_page_queries.get_account_overview_data()

        self.assertIn("acompanha 1 pedido", overview_payload["page_description"])
        self.assertIn("facilitar o retorno certo", overview_payload["summary_subtitle"].lower())
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][0], "#3051")
        self.assertIn("pedido em preparação", overview_payload["recent_orders"][0]["cells"][1].lower())
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][2], "R$ 269,80")
        self.assertIn("pedido mais recente pago", overview_payload["activity_content"].lower())
        self.assertIn("confirmação do envio", overview_payload["activity_content"].lower())
        self.assertIn("primeira compra já registrada", overview_payload["page_meta"].lower())
        self.assertIn("catálogo continua disponível", overview_payload["quick_links_subtitle"].lower())

    def test_account_overview_view_renders_continuity_context(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "acompanha 1 pedido")
        self.assertContains(response, "facilitar o retorno certo")
        self.assertContains(response, "#3051")
        self.assertContains(response, "pedido em preparação")
        self.assertContains(response, "Pedido mais recente pago")
        self.assertContains(response, "Primeira compra já registrada")
        self.assertContains(response, "Voltar ao catálogo")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_account_overview_scopes_order_continuity_by_tenant(self):
        primary_profile = AccountProfile.objects.select_related("tenant", "customer").filter(is_active=True).order_by("id").first()
        self.assertIsNotNone(primary_profile)
        secondary_tenant = Tenant.objects.create(
            name="Second Account Overview Tenant",
            slug="second-account-overview-tenant",
            subdomain="second-account-overview-tenant",
            is_active=True,
        )
        secondary_customer = Customer.objects.create(
            tenant=secondary_tenant,
            slug="account-overview-secondary-customer",
            reference="#9801",
            full_name="Ana Overview Secondary",
            email=primary_profile.email,
            phone="(21) 98888-1111",
            status="active",
            account_type="Storefront",
        )
        AccountProfile.objects.create(
            tenant=secondary_tenant,
            customer=secondary_customer,
            email=primary_profile.email,
            first_name="Ana",
            last_name="Overview Secondary",
            phone="(21) 98888-1111",
            is_active=True,
        )
        secondary_order = Order.objects.create(
            tenant=secondary_tenant,
            customer=secondary_customer,
            number="9550",
            status="shipped",
            customer_name=secondary_customer.full_name,
            customer_email=secondary_customer.email,
            customer_phone=secondary_customer.phone,
            payment_status="Confirmado",
            shipping_status="Em trânsito",
            fulfillment_status_label="Em trânsito",
            fulfillment_status_variant="shipped",
            shipping_address_summary="Rua Secondary, 99 · Rio de Janeiro/RJ",
            notes_content="Pedido da loja secundária.",
            subtotal="150.00",
            shipping_total="20.00",
            discount_total="0.00",
            total="170.00",
            installments_summary="",
        )
        OrderItem.objects.create(
            order=secondary_order,
            title="Item Overview Secondary",
            subtitle="Único",
            meta="SKU OVERVIEW-SECONDARY-001",
            price_snapshot="170.00",
            quantity=1,
            sort_order=1,
        )

        primary_payload = account_page_queries.get_account_overview_data(tenant_id=primary_profile.tenant_id)
        secondary_payload = account_page_queries.get_account_overview_data(tenant_id=secondary_tenant.id)

        self.assertEqual(primary_payload["recent_orders"][0]["cells"][0], "#3051")
        self.assertNotIn("#9550", str(primary_payload["recent_orders"]))
        self.assertIn("#9550", str(secondary_payload["recent_orders"]))
        self.assertIn("enquanto esta entrega avança", secondary_payload["page_meta"].lower())
