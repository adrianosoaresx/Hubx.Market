from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_local_secret_code_retirement_execution_queries import (
    owner_mfa_local_secret_code_retirement_execution_queries,
)
from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaLocalSecretCodeRetirementExecutionTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Code Retirement Exec", slug="mfa-code-retirement-exec", subdomain="mfa-code-retirement-exec")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.code.retirement.exec@hubx.market", role="owner")

    def test_local_plain_default_is_disabled(self):
        self.assertFalse(owner_mfa_secret_storage.can_accept_local_plain())

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_execution_ready_when_default_is_disabled_and_readiness_is_ready(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_code_retirement_execution_queries.get_evidence(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_execution_blocks_when_env_reenables_local_plain(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_local_secret_code_retirement_execution_queries.get_evidence(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "blocked")
        self.assertIn("local-secret-default-or-env-enabled", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_execution_command_outputs_rollback(self):
        self._factor(secret_reference="ref:owners/1/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            call_command("owner_mfa_local_secret_code_retirement_execute", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=default-local-secret-disabled", output.getvalue())
        self.assertIn("rollback=definir OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1", output.getvalue())

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
