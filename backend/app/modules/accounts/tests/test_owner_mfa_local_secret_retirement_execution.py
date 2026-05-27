from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_local_secret_retirement_execution_queries import owner_mfa_local_secret_retirement_execution_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaLocalSecretRetirementExecutionTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Retirement Exec", slug="mfa-retirement-exec", subdomain="mfa-retirement-exec")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.retirement.exec@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_before_phase_is_ready_when_external_references_are_resolved(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_retirement_execution_queries.get_evidence(tenant_id=self.tenant.id, phase="before")

        self.assertTrue(result["ready"])
        self.assertEqual(result["phase"], "before")
        self.assertEqual(result["setting_current"], "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_after_phase_blocks_until_setting_is_disabled(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_retirement_execution_queries.get_evidence(tenant_id=self.tenant.id, phase="after")

        self.assertFalse(result["ready"])
        self.assertIn("local-secret-setting-still-enabled", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_after_phase_is_ready_when_setting_is_disabled_and_storage_is_external(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_retirement_execution_queries.get_evidence(tenant_id=self.tenant.id, phase="after")

        self.assertTrue(result["ready"])
        self.assertEqual(result["setting_current"], "OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_after_phase_still_blocks_local_plain_regression(self):
        self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_local_secret_retirement_execution_queries.get_evidence(tenant_id=self.tenant.id, phase="after")

        self.assertFalse(result["ready"])
        self.assertIn("local-plain-factors-present", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_command_outputs_evidence_and_rollback(self):
        self._factor(secret_reference="ref:owners/1/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            call_command(
                "owner_mfa_local_secret_retirement_execution",
                "--tenant-id",
                str(self.tenant.id),
                "--phase",
                "before",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("phase=before", output.getvalue())
        self.assertIn("evidence=", output.getvalue())
        self.assertIn("rollback=", output.getvalue())

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
