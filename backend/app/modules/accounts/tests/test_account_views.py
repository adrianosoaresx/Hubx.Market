from django.contrib.auth import SESSION_KEY
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from app.modules.accounts.application.account_page_queries import account_page_queries
from app.modules.accounts.application.demo_session_login_commands import (
    DEMO_SESSION_RETURN_URL_KEY,
    DEMO_SESSION_SOURCE_KEY,
)
from app.modules.accounts.application.owner_session_policy import (
    OWNER_SESSION_KIND_KEY,
    OWNER_SESSION_REMEMBERED_KEY,
)
from app.modules.accounts.application.owner_login_commands import OWNER_MFA_PENDING_SESSION_KEY
from app.modules.accounts.application.owner_mfa_challenge_commands import TotpChallengeVerifier
from app.modules.accounts.application.owner_mfa_recovery_code_commands import owner_mfa_recovery_code_commands
from app.modules.accounts.models import AccountProfile, OwnerMfaFactor, OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.customers.models import Customer
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order, OrderItem
from app.modules.tenants.models import Tenant
import time
from unittest.mock import patch


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
        self.assertFalse(login_payload["remember_me"])
        self.assertEqual(login_payload["login_label"], "E-mail da conta")
        self.assertEqual(login_payload["primary_label"], "Acessar conta")
        self.assertEqual(login_payload["login_value"], "")
        self.assertEqual(login_payload["profile_mode"], "missing")
        self.assertEqual(overview_payload["page_title"], "Minha conta")
        self.assertEqual(overview_payload["summary_title"], "Resumo da conta")
        self.assertEqual(overview_payload["recent_orders_title"], "Pedidos para acompanhar")
        self.assertEqual(overview_payload["activity_title"], "O que acompanhar agora")
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][0], "#1048")
        self.assertEqual(overview_payload["profile_mode"], "missing")
        self.assertIn("ainda não encontramos um perfil persistido", overview_payload["summary_content"].lower())
        self.assertIn("voltar à loja", overview_payload["page_meta"].lower())


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class OwnerLoginViewTests(TestCase):
    def setUp(self):
        cache.clear()
        self.tenant = Tenant.objects.create(
            name="Owner Login Tenant",
            slug="owner-login-tenant",
            subdomain="owner-login-tenant",
            is_active=True,
        )
        self.user = User.objects.create_user(
            username="owner-login",
            email="owner.login@hubx.market",
            password="secret-pass",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.login@hubx.market",
            full_name="Owner Login",
            role="owner",
            is_active=True,
        )

    def test_owner_login_post_authenticates_active_owner_and_redirects_to_next(self):
        response = self.client.post(
            reverse("accounts:login"),
            data={
                "login": "owner.login@hubx.market",
                "password": "secret-pass",
                "next": reverse("owners:admin-owners-list"),
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("owners:admin-owners-list"))
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.user.id))
        self.assertEqual(self.client.session[OWNER_SESSION_KIND_KEY], "owner")
        self.assertFalse(self.client.session[OWNER_SESSION_REMEMBERED_KEY])
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.login",
                entity_id=str(self.owner.id),
            ).exists()
        )

    def test_customer_login_post_authenticates_profile_and_redirects_to_account(self):
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-login",
            full_name="Cliente Login",
            email="cliente.login@hubx.market",
        )
        profile = AccountProfile.objects.create(
            tenant=self.tenant,
            customer=customer,
            email="cliente.login@hubx.market",
            first_name="Cliente",
            last_name="Login",
        )
        customer_user = User.objects.create_user(
            username="cliente-login",
            email="cliente.login@hubx.market",
            password="secret-pass",
        )

        response = self.client.post(
            reverse("accounts:login"),
            data={
                "login": "cliente.login@hubx.market",
                "password": "secret-pass",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:account-overview"))
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(customer_user.id))
        self.assertEqual(self.client.session["hubx_account_profile_id"], profile.id)
        self.assertEqual(self.client.session["hubx_account_session_kind"], "customer")

    @override_settings(OWNER_MFA_REQUIRED=True, OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_owner_login_with_mfa_required_redirects_to_challenge_without_session(self):
        self._create_verified_totp_factor()

        response = self.client.post(
            reverse("accounts:login"),
            data={
                "login": "owner.login@hubx.market",
                "password": "secret-pass",
                "next": reverse("owners:admin-owners-list"),
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:owner-mfa-challenge"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertIn(OWNER_MFA_PENDING_SESSION_KEY, self.client.session)
        self.assertTrue(AuditLog.objects.filter(action="owner.login_mfa_required").exists())

    @override_settings(OWNER_MFA_REQUIRED=True, OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_owner_mfa_challenge_completes_login_session(self):
        self._create_verified_totp_factor()
        self.client.post(
            reverse("accounts:login"),
            data={
                "login": "owner.login@hubx.market",
                "password": "secret-pass",
                "next": reverse("owners:admin-owners-list"),
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_LOGIN_TOTP": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"}):
            response = self.client.post(
                reverse("accounts:owner-mfa-challenge"),
                data={"challenge": self._current_challenge(), "next": reverse("owners:admin-owners-list")},
                HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("owners:admin-owners-list"))
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.user.id))
        self.assertEqual(self.client.session[OWNER_SESSION_KIND_KEY], "owner")
        self.assertNotIn(OWNER_MFA_PENDING_SESSION_KEY, self.client.session)
        self.assertTrue(AuditLog.objects.filter(action="owner.login_mfa_completed").exists())
        self.assertTrue(AuditLog.objects.filter(action="owner.login").exists())

    @override_settings(OWNER_MFA_REQUIRED=True, OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_owner_mfa_challenge_rejects_invalid_code_without_session(self):
        self._create_verified_totp_factor()
        self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_LOGIN_TOTP": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"}):
            response = self.client.post(
                reverse("accounts:owner-mfa-challenge"),
                data={"challenge": "000000"},
                HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertIn(OWNER_MFA_PENDING_SESSION_KEY, self.client.session)
        self.assertTrue(AuditLog.objects.filter(action="owner.login_mfa_failed").exists())

    @override_settings(OWNER_MFA_REQUIRED=True)
    def test_owner_mfa_challenge_accepts_recovery_code_once(self):
        result = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=1,
            actor_role="owner",
        )
        self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        response = self.client.post(
            reverse("accounts:owner-mfa-challenge"),
            data={"challenge": result["codes"][0]},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.user.id))
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_recovery_code_used").exists())

    @override_settings(OWNER_MFA_REQUIRED=True, OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_owner_mfa_challenge_accepts_external_secret_reference(self):
        OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference="ref:owners/login/totp",
            is_active=True,
            is_verified=True,
        )
        self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_LOGIN_TOTP": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"}):
            response = self.client.post(
                reverse("accounts:owner-mfa-challenge"),
                data={"challenge": self._current_challenge()},
                HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.user.id))

    @override_settings(OWNER_MFA_REQUIRED=True)
    def test_owner_login_blocks_when_mfa_required_without_verified_factor(self):
        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(AuditLog.objects.filter(action="owner.login_mfa_blocked").exists())

    @override_settings(OWNER_MFA_REQUIRED=False, OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_owner_mfa_enforcement_rollback_setting_preserves_direct_login(self):
        self._create_verified_totp_factor()

        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.user.id))
        self.assertNotIn(OWNER_MFA_PENDING_SESSION_KEY, self.client.session)

    def _create_verified_totp_factor(self):
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference="ref:owners/login/totp",
            is_active=True,
            is_verified=True,
        )

    def _current_challenge(self) -> str:
        verifier = TotpChallengeVerifier()
        secret = verifier._normalize_secret("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ")
        return verifier._code(secret=secret, counter=int(time.time()) // verifier.interval_seconds)

    @override_settings(OWNER_SESSION_IDLE_SECONDS=1800, OWNER_SESSION_REMEMBER_SECONDS=86400)
    def test_owner_login_uses_short_session_without_remember_me(self):
        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), 1800)
        self.assertEqual(self.client.session[OWNER_SESSION_KIND_KEY], "owner")
        self.assertFalse(self.client.session[OWNER_SESSION_REMEMBERED_KEY])
        audit_log = AuditLog.objects.get(
            tenant=self.tenant,
            module="accounts",
            action="owner.login",
            entity_id=str(self.owner.id),
        )
        self.assertEqual(audit_log.metadata["session_expiry_seconds"], 1800)
        self.assertFalse(audit_log.metadata["session_remembered"])

    @override_settings(OWNER_SESSION_IDLE_SECONDS=1800, OWNER_SESSION_REMEMBER_SECONDS=86400)
    def test_owner_login_uses_remember_me_session_when_requested(self):
        response = self.client.post(
            reverse("accounts:login"),
            data={
                "login": "owner.login@hubx.market",
                "password": "secret-pass",
                "remember_me": "on",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session.get_expiry_age(), 86400)
        self.assertEqual(self.client.session[OWNER_SESSION_KIND_KEY], "owner")
        self.assertTrue(self.client.session[OWNER_SESSION_REMEMBERED_KEY])
        audit_log = AuditLog.objects.get(
            tenant=self.tenant,
            module="accounts",
            action="owner.login",
            entity_id=str(self.owner.id),
        )
        self.assertEqual(audit_log.metadata["session_expiry_seconds"], 86400)
        self.assertTrue(audit_log.metadata["session_remembered"])

    def test_owner_login_rejects_missing_owner_for_current_tenant(self):
        other_tenant = Tenant.objects.create(
            name="Other Owner Login Tenant",
            slug="other-owner-login-tenant",
            subdomain="other-owner-login-tenant",
            is_active=True,
        )

        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{other_tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertContains(response, "Não foi possível entrar", status_code=400)

    def test_owner_login_rejects_inactive_owner(self):
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])

        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_owner_login_rejects_unsafe_next_url(self):
        response = self.client.post(
            reverse("accounts:login"),
            data={
                "login": "owner.login@hubx.market",
                "password": "secret-pass",
                "next": "https://evil.example/ops/",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("merchant_ops:admin-dashboard"))

    @override_settings(OWNER_LOGIN_RATE_LIMIT_MAX_ATTEMPTS=2, OWNER_LOGIN_RATE_LIMIT_WINDOW_SECONDS=60, OWNER_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS=120)
    def test_owner_login_rate_limits_repeated_failures(self):
        for _ in range(2):
            response = self.client.post(
                reverse("accounts:login"),
                data={"login": "owner.login@hubx.market", "password": "wrong-pass"},
                HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
                REMOTE_ADDR="203.0.113.10",
            )
            self.assertEqual(response.status_code, 400)

        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            REMOTE_ADDR="203.0.113.10",
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response["Retry-After"], "120")
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.login_rate_limited",
                actor_label="owner.login@hubx.market",
            ).exists()
        )

    @override_settings(OWNER_LOGIN_RATE_LIMIT_MAX_ATTEMPTS=2, OWNER_LOGIN_RATE_LIMIT_WINDOW_SECONDS=60, OWNER_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS=120)
    def test_owner_login_success_clears_failed_attempts(self):
        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "wrong-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            REMOTE_ADDR="203.0.113.20",
        )
        self.assertEqual(response.status_code, 400)

        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "secret-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            REMOTE_ADDR="203.0.113.20",
        )

        self.assertEqual(response.status_code, 302)
        self.client.logout()

        response = self.client.post(
            reverse("accounts:login"),
            data={"login": "owner.login@hubx.market", "password": "wrong-pass"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
            REMOTE_ADDR="203.0.113.20",
        )
        self.assertEqual(response.status_code, 400)

    def test_owner_logout_clears_session_and_records_audit(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("accounts:logout"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("accounts:login"))
        self.assertNotIn(SESSION_KEY, self.client.session)
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.logout",
                entity_id=str(self.owner.id),
            ).exists()
        )

    def test_owner_forgot_password_returns_generic_success_and_reset_url_when_valid(self):
        response = self.client.post(
            reverse("accounts:forgot-password"),
            data={"email": "owner.login@hubx.market"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se este e-mail estiver habilitado")
        self.assertContains(response, "/accounts/reset-password/")
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="owner.password_reset_requested",
                intent_key="owner.access.password_reset",
                recipient_email="owner.login@hubx.market",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.password_reset_requested",
                entity_id=str(self.owner.id),
            ).exists()
        )

    def test_owner_forgot_password_is_generic_for_unknown_owner(self):
        response = self.client.post(
            reverse("accounts:forgot-password"),
            data={"email": "unknown@hubx.market"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Se este e-mail estiver habilitado")
        self.assertNotContains(response, "/accounts/reset-password/")

    def test_owner_reset_password_token_updates_password_and_redirects_to_login(self):
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            reverse("accounts:reset-password-token", kwargs={"uidb64": uidb64, "token": token}),
            data={"password": "OwnerPass-12345", "confirm_password": "OwnerPass-12345"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{reverse('accounts:login')}?reset=completed")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("OwnerPass-12345"))
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.password_reset_completed",
                entity_id=str(self.owner.id),
            ).exists()
        )

    def test_owner_reset_password_token_rejects_cross_tenant_owner_context(self):
        other_tenant = Tenant.objects.create(
            name="Other Reset Tenant",
            slug="other-reset-tenant",
            subdomain="other-reset-tenant",
            is_active=True,
        )
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            reverse("accounts:reset-password-token", kwargs={"uidb64": uidb64, "token": token}),
            data={"password": "OwnerPass-12345", "confirm_password": "OwnerPass-12345"},
            HTTP_HOST=f"{other_tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.check_password("OwnerPass-12345"))


@override_settings(
    ALLOWED_HOSTS=["testserver", ".hubx.market", ".localhost", "localhost"],
    HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo",
)
class DemoSessionLoginViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Demo",
            slug="hubx-demo",
            subdomain="hubx-demo",
            is_active=True,
        )
        self.admin_user = User.objects.create_user(
            username="demo-admin",
            email="admin@hubx-demo.market",
            password="unused-pass",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="admin@hubx-demo.market",
            full_name="Admin Demo",
            role="owner",
            is_active=True,
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-demo",
            full_name="Cliente Demo",
            email="cliente@hubx-demo.market",
            status=Customer.Status.ACTIVE,
        )
        self.profile = AccountProfile.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            email="cliente@hubx-demo.market",
            first_name="Cliente",
            last_name="Demo",
            is_active=True,
        )
        self.customer_user = User.objects.create_user(
            username="demo-customer",
            email="cliente@hubx-demo.market",
            password="unused-pass",
        )

    def test_demo_session_login_admin_authenticates_directly_and_redirects_to_ops(self):
        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ops/")
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.admin_user.id))
        self.assertEqual(self.client.session[OWNER_SESSION_KIND_KEY], "owner")
        self.assertFalse(self.client.session[OWNER_SESSION_REMEMBERED_KEY])
        self.assertEqual(self.client.session[DEMO_SESSION_SOURCE_KEY], "public-demo")
        self.assertNotIn(DEMO_SESSION_RETURN_URL_KEY, self.client.session)
        self.assertNotIn("hubx_account_session_kind", self.client.session)

    def test_demo_session_login_customer_authenticates_directly_and_redirects_to_storefront(self):
        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "customer"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/")
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.customer_user.id))
        self.assertEqual(self.client.session["hubx_account_profile_id"], self.profile.id)
        self.assertEqual(self.client.session["hubx_account_session_kind"], "customer")
        self.assertEqual(self.client.session[DEMO_SESSION_SOURCE_KEY], "public-demo")
        self.assertNotIn(DEMO_SESSION_RETURN_URL_KEY, self.client.session)
        self.assertNotIn(OWNER_SESSION_KIND_KEY, self.client.session)

    def test_demo_session_login_stores_safe_central_return_url(self):
        return_url = "http://hubx.market/demo/"

        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin", "return_url": return_url},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[DEMO_SESSION_RETURN_URL_KEY], return_url)

    def test_demo_session_login_ignores_unsafe_return_url(self):
        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin", "return_url": "https://evil.example/demo/"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session[DEMO_SESSION_SOURCE_KEY], "public-demo")
        self.assertNotIn(DEMO_SESSION_RETURN_URL_KEY, self.client.session)

    def test_demo_admin_logout_returns_to_central_demo_entry(self):
        self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        response = self.client.post(reverse("accounts:logout"), HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://hubx.market/demo/")
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_demo_logout_without_authenticated_session_returns_to_central_demo_entry(self):
        response = self.client.post(reverse("accounts:logout"), HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://hubx.market/demo/")
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market")
    def test_demo_logout_without_authenticated_session_uses_safe_return_url(self):
        return_url = "http://127.0.0.1:8002/demo/"

        response = self.client.post(
            reverse("accounts:logout"),
            {"return_url": return_url},
            HTTP_HOST="hubx-demo.localhost:8002",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], return_url)
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market")
    def test_demo_customer_logout_returns_to_exact_local_demo_entry(self):
        return_url = "http://127.0.0.1:8002/demo/"
        self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "customer", "return_url": return_url},
            HTTP_HOST="hubx-demo.localhost:8002",
        )

        response = self.client.post(reverse("accounts:logout"), HTTP_HOST="hubx-demo.localhost:8002")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], return_url)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_demo_logout_with_unsafe_return_url_falls_back_to_central_demo_entry(self):
        self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin", "return_url": "https://evil.example/demo/"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        response = self.client.post(reverse("accounts:logout"), HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "http://hubx.market/demo/")
        self.assertNotIn(SESSION_KEY, self.client.session)

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market")
    def test_demo_session_login_works_on_localhost_demo_subdomain(self):
        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin"},
            HTTP_HOST="hubx-demo.localhost:8002",
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], "/ops/")
        self.assertEqual(str(self.client.session[SESSION_KEY]), str(self.admin_user.id))

    def test_demo_session_login_rejects_central_host_without_demo_tenant_context(self):
        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "admin"},
            HTTP_HOST="hubx.market",
        )

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(SESSION_KEY, self.client.session)

    def test_demo_session_login_rejects_unknown_profile(self):
        response = self.client.get(
            reverse("accounts:demo-session-login"),
            {"profile": "support"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 404)
        self.assertNotIn(SESSION_KEY, self.client.session)


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
        self.assertContains(response, "Voltar à loja")

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
        self.assertEqual(overview_payload["recent_orders_title"], "Pedidos para acompanhar")
        self.assertEqual(overview_payload["activity_title"], "O que acompanhar agora")
        self.assertIn("melhor próximo retorno", overview_payload["activity_subtitle"].lower())
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][0], "#3051")
        self.assertTrue(overview_payload["recent_orders"][0]["cells"][1].lower().startswith("pedido em preparação"))
        self.assertIn("atualizado há", overview_payload["recent_orders"][0]["cells"][1].lower())
        self.assertIn("pago", overview_payload["recent_orders"][0]["cells"][1].lower())
        self.assertEqual(overview_payload["recent_orders"][0]["cells"][2], "R$ 269,80")
        self.assertIn("melhor acompanhamento agora", overview_payload["activity_content"].lower())
        self.assertIn("pedido mais recente", overview_payload["activity_content"].lower())
        self.assertIn("confirmação do envio", overview_payload["activity_content"].lower())
        self.assertIn("primeira compra já registrada", overview_payload["page_meta"].lower())
        self.assertIn("loja continua disponível", overview_payload["quick_links_subtitle"].lower())

    def test_account_overview_view_renders_continuity_context(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "acompanha 1 pedido")
        self.assertContains(response, "facilitar o retorno certo")
        self.assertContains(response, "Pedidos para acompanhar")
        self.assertContains(response, "O que acompanhar agora")
        self.assertContains(response, "#3051")
        self.assertContains(response, "pedido em preparação")
        self.assertContains(response, "melhor acompanhamento agora")
        self.assertContains(response, "Primeira compra já registrada")
        self.assertContains(response, "Voltar à loja")

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
