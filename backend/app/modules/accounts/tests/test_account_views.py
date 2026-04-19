from django.test import TestCase
from django.urls import reverse

from app.modules.accounts.application.account_page_queries import account_page_queries


class AccountViewTests(TestCase):
    def test_login_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:login"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/login_page.html")
        self.assertContains(response, "Entrar")
        self.assertContains(response, "ana@hubx.market")
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
        self.assertEqual(overview_payload["page_title"], "Minha conta")
        self.assertEqual(overview_payload["summary_title"], "Resumo da conta")
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][0], "#1048")


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
        self.assertIn("conta segue pronta para acompanhar compras e voltar quando quiser", overview_payload["summary_content"])
        self.assertIn("14/04/2026", overview_payload["activity_content"])

    def test_account_overview_view_renders_persisted_profile_when_present(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/account_overview_page.html")
        self.assertContains(response, "Ana Persistida")
        self.assertContains(response, "Veja rapidamente como sua conta está preparada")
