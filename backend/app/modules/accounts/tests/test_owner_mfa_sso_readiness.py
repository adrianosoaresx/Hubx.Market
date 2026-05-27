from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_sso_readiness_queries import owner_mfa_sso_readiness_queries


class OwnerMfaSsoReadinessQueryTests(TestCase):
    def test_readiness_defaults_to_password_only(self):
        readiness = owner_mfa_sso_readiness_queries.get_readiness()

        self.assertEqual(readiness["result"], "owner-mfa-sso-ready")
        self.assertEqual(readiness["mode"], "password-only")
        self.assertEqual(readiness["blockers"], ())

    @override_settings(OWNER_MFA_REQUIRED=True, OWNER_MFA_PROVIDER="")
    def test_readiness_blocks_mfa_without_provider(self):
        readiness = owner_mfa_sso_readiness_queries.get_readiness()

        self.assertFalse(readiness["ready"])
        self.assertIn("owner-mfa-provider-missing", readiness["blockers"])

    @override_settings(
        OWNER_SSO_ENABLED=True,
        OWNER_SSO_PROVIDER="oidc",
        OWNER_SSO_LOGIN_URL="https://idp.example.com/login",
        OWNER_SSO_CALLBACK_PATH="/accounts/sso/callback/",
    )
    def test_readiness_accepts_configured_sso_contract(self):
        readiness = owner_mfa_sso_readiness_queries.get_readiness()

        self.assertTrue(readiness["ready"])
        self.assertEqual(readiness["mode"], "sso")
        self.assertEqual(readiness["sso_provider"], "oidc")


class OwnerMfaSsoReadinessCommandTests(TestCase):
    def test_command_outputs_contracts(self):
        output = StringIO()

        call_command("owner_mfa_sso_readiness", stdout=output)

        self.assertIn("[READY] mode=password-only", output.getvalue())
        self.assertIn("contract key=mfa", output.getvalue())
        self.assertIn("next_track=Owner MFA Enrollment Model Review", output.getvalue())

    @override_settings(OWNER_SSO_ENABLED=True, OWNER_SSO_PROVIDER="")
    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("owner_mfa_sso_readiness", "--fail-on-blockers", stdout=StringIO())
