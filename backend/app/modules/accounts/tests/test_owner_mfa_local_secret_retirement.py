from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_local_secret_retirement_queries import owner_mfa_local_secret_retirement_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaLocalSecretRetirementTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Retirement", slug="mfa-retirement", subdomain="mfa-retirement")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.retirement@hubx.market", role="owner")

    def test_retirement_blocks_when_local_plain_factor_remains(self):
        self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_local_secret_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertEqual(result["local_plain_count"], 1)
        self.assertIn("local-plain-factors-present", result["blockers"])

    def test_retirement_blocks_when_external_reference_is_unresolved(self):
        factor = self._factor(secret_reference="ref:owners/1/totp")

        result = owner_mfa_local_secret_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn(f"factor-{factor.id}:external-secret-unresolved", result["blockers"])
        self.assertIn("secret-storage-readiness-blocked", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_retirement_ready_when_all_totp_factors_are_resolved_external_references(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_retirement_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertTrue(result["ready"])
        self.assertEqual(result["local_plain_count"], 0)
        self.assertEqual(result["external_reference_count"], 1)
        self.assertEqual(result["setting_target"], "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_command_outputs_runbook_and_target_setting(self):
        self._factor(secret_reference="ref:owners/1/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            call_command("owner_mfa_local_secret_retirement_readiness", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("target=OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False", output.getvalue())
        self.assertIn("runbook=", output.getvalue())

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
