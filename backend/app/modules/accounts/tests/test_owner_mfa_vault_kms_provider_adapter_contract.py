from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_adapter_contract_queries import (
    owner_mfa_vault_kms_provider_adapter_contract_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderAdapterContractTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Adapter", slug="mfa-adapter", subdomain="mfa-adapter")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.adapter@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_contract_ready_when_vault_review_is_ready(self):
        self._factor(secret_reference="ref:owners/adapter/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_ADAPTER_TOTP": self.secret}):
            result = owner_mfa_vault_kms_provider_adapter_contract_queries.get_contract(
                tenant_id=self.tenant.id,
                target_provider="hashicorp-vault",
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["target_provider"], "hashicorp-vault")
        self.assertIn("OWNER_MFA_SECRET_TIMEOUT_MS=<int default 1500>", result["settings_contract"])
        self.assertIn("Owner MFA Vault/KMS Provider Adapter Skeleton Execution", result["next_tracks"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_contract_blocks_when_provider_review_is_blocked(self):
        self._factor(secret_reference="ref:owners/adapter/totp")

        result = owner_mfa_vault_kms_provider_adapter_contract_queries.get_contract(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn("provider-health-closure-blocked", result["blockers"])
        self.assertIn("vault-kms-provider-review-not-ready", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_contract_blocks_unsupported_target_provider(self):
        self._factor(secret_reference="ref:owners/adapter/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_ADAPTER_TOTP": self.secret}):
            result = owner_mfa_vault_kms_provider_adapter_contract_queries.get_contract(
                tenant_id=self.tenant.id,
                target_provider="plaintext-file",
            )

        self.assertFalse(result["ready"])
        self.assertIn("target-provider-unsupported", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_command_outputs_settings_interface_security_and_tests(self):
        self._factor(secret_reference="ref:owners/adapter/command")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_ADAPTER_COMMAND": self.secret}):
            call_command(
                "owner_mfa_vault_kms_provider_adapter_contract",
                "--tenant-id",
                str(self.tenant.id),
                "--target-provider",
                "aws-secrets-manager",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("settings_contract=", output.getvalue())
        self.assertIn("adapter_interface=", output.getvalue())
        self.assertIn("security_control=", output.getvalue())
        self.assertIn("test_contract=", output.getvalue())

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
