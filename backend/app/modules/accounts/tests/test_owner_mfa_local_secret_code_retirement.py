from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_local_secret_code_retirement_queries import owner_mfa_local_secret_code_retirement_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaLocalSecretCodeRetirementTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Code Retirement", slug="mfa-code-retirement", subdomain="mfa-code-retirement")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.code.retirement@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_readiness_ready_when_local_setting_is_disabled_and_provider_closure_is_ready(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_code_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Local Secret Code Retirement Execution Review", result["next_tracks"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_readiness_blocks_when_local_setting_is_still_enabled(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_code_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("local-secret-setting-enabled", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_readiness_blocks_when_local_plain_factor_remains(self):
        self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_local_secret_code_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("local-plain-factors-present", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_readiness_blocks_when_provider_closure_is_critical(self):
        self._factor(secret_reference="ref:owners/1/totp")

        result = owner_mfa_local_secret_code_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any(blocker.startswith("provider-closure:health:") for blocker in result["blockers"]))

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_command_outputs_code_surfaces_and_residual_risks(self):
        self._factor(secret_reference="ref:owners/1/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            call_command("owner_mfa_local_secret_code_retirement_readiness", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=setting-disabled", output.getvalue())
        self.assertIn("code_surface=", output.getvalue())
        self.assertIn("residual_risk=", output.getvalue())

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
