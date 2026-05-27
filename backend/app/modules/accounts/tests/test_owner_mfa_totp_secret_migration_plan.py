from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_totp_secret_migration_plan_queries import owner_mfa_totp_secret_migration_plan_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaTotpSecretMigrationPlanTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Migration", slug="mfa-migration", subdomain="mfa-migration")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.migration@hubx.market", role="owner")

    def test_plan_blocks_local_plain_after_parser_removal(self):
        factor = self._factor(secret_reference="plain:GEZDGNBVGY3TQOJQ")

        result = owner_mfa_totp_secret_migration_plan_queries.get_plan(tenant_id=self.tenant.id, reference_prefix="mfa")

        self.assertFalse(result["ready"])
        self.assertEqual(result["migrate_count"], 0)
        candidate = result["candidates"][0]
        self.assertEqual(candidate.factor_id, factor.id)
        self.assertEqual(candidate.action, "blocked")
        self.assertEqual(candidate.current_storage_mode, "unsupported-local")
        self.assertEqual(candidate.target_reference, f"mfa/tenant-{self.tenant.id}/owner-{self.owner.id}/totp-{factor.id}")
        self.assertIn(f"factor-{factor.id}:local-secret-unsupported", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_plan_keeps_resolved_external_factor_as_already_external(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": "GEZDGNBVGY3TQOJQ"}):
            result = owner_mfa_totp_secret_migration_plan_queries.get_plan(tenant_id=self.tenant.id)

        self.assertTrue(result["ready"])
        self.assertEqual(result["already_external_count"], 1)
        self.assertEqual(result["candidates"][0].action, "already-external")

    def test_plan_blocks_unresolved_external_factor(self):
        factor = self._factor(secret_reference="ref:owners/1/totp")

        result = owner_mfa_totp_secret_migration_plan_queries.get_plan(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn(f"factor-{factor.id}:external-secret-unresolved", result["blockers"])

    def test_plan_blocks_missing_secret(self):
        factor = self._factor(secret_reference="")

        result = owner_mfa_totp_secret_migration_plan_queries.get_plan(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn(f"factor-{factor.id}:secret-missing", result["blockers"])

    def test_command_outputs_candidate_and_runbook(self):
        self._factor(secret_reference="plain:GEZDGNBVGY3TQOJQ")
        output = StringIO()

        call_command(
            "owner_mfa_totp_secret_migration_plan",
            "--tenant-id",
            str(self.tenant.id),
            "--reference-prefix",
            "mfa",
            stdout=output,
        )

        self.assertIn("[BLOCKED]", output.getvalue())
        self.assertIn("candidate factor=", output.getvalue())
        self.assertIn("local-secret-unsupported", output.getvalue())
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
