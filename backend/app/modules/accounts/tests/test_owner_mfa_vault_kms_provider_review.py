from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_review_queries import owner_mfa_vault_kms_provider_review_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderReviewTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Vault", slug="mfa-vault", subdomain="mfa-vault")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.vault@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_review_ready_for_adapter_contract_when_current_env_health_is_closed(self):
        self._factor(secret_reference="ref:owners/vault/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_VAULT_TOTP": self.secret}):
            result = owner_mfa_vault_kms_provider_review_queries.get_review(
                tenant_id=self.tenant.id,
                target_provider="hashicorp-vault",
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["current_provider"], "env")
        self.assertEqual(result["target_provider"], "hashicorp-vault")
        self.assertIn("Owner MFA Vault/KMS Provider Adapter Contract Review", result["next_tracks"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_review_blocks_unsupported_target_provider(self):
        self._factor(secret_reference="ref:owners/vault/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_VAULT_TOTP": self.secret}):
            result = owner_mfa_vault_kms_provider_review_queries.get_review(
                tenant_id=self.tenant.id,
                target_provider="plaintext-file",
            )

        self.assertFalse(result["ready"])
        self.assertIn("target-provider-unsupported", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_review_blocks_when_provider_health_is_not_closed(self):
        self._factor(secret_reference="ref:owners/vault/totp")

        result = owner_mfa_vault_kms_provider_review_queries.get_review(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn("provider-health-closure-blocked", result["blockers"])

    def test_review_requires_tenant_scope(self):
        result = owner_mfa_vault_kms_provider_review_queries.get_review(tenant_id="")

        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"], ("tenant-required",))

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_command_outputs_contract_rollout_and_rollback(self):
        self._factor(secret_reference="ref:owners/vault/command")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_VAULT_COMMAND": self.secret}):
            call_command(
                "owner_mfa_vault_kms_provider_review",
                "--tenant-id",
                str(self.tenant.id),
                "--target-provider",
                "aws-secrets-manager",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("adapter_contract=", output.getvalue())
        self.assertIn("rollout_plan=", output.getvalue())
        self.assertIn("rollback=", output.getvalue())

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
