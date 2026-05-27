from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_adapter_contract_queries import (
    owner_mfa_vault_kms_provider_real_adapter_contract_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderRealAdapterContractTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Real Adapter", slug="mfa-real-adapter", subdomain="mfa-real-adapter")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.real.adapter@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/real-adapter/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_contract_ready_when_canary_and_confirmations_are_ready(self):
        self._factor(secret_reference="ref:owners/real-adapter/probe")

        result = owner_mfa_vault_kms_provider_real_adapter_contract_queries.get_contract(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/real-adapter/probe",
            canary_owner_email=self.owner.email,
            sdk_dependency_confirmed=True,
            credential_strategy_confirmed=True,
            network_timeout_confirmed=True,
            rollout_owner_confirmed=True,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/real-adapter/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_contract_blocks_missing_confirmation(self):
        self._factor(secret_reference="ref:owners/real-adapter/probe")

        result = owner_mfa_vault_kms_provider_real_adapter_contract_queries.get_contract(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/real-adapter/probe",
            canary_owner_email=self.owner.email,
            sdk_dependency_confirmed=False,
            credential_strategy_confirmed=True,
            network_timeout_confirmed=True,
            rollout_owner_confirmed=True,
        )

        self.assertFalse(result["ready"])
        self.assertIn("confirmation-missing:sdk_dependency_confirmed", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="aws-kms",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/real-adapter/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_contract_blocks_target_not_supported_for_real_adapter(self):
        self._factor(secret_reference="ref:owners/real-adapter/probe", provider_key="aws-kms")

        result = owner_mfa_vault_kms_provider_real_adapter_contract_queries.get_contract(
            tenant_id=self.tenant.id,
            target_provider="aws-kms",
            probe_reference="owners/real-adapter/probe",
            canary_owner_email=self.owner.email,
            sdk_dependency_confirmed=True,
            credential_strategy_confirmed=True,
            network_timeout_confirmed=True,
            rollout_owner_confirmed=True,
        )

        self.assertFalse(result["ready"])
        self.assertIn("real-target-provider-unsupported", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/real-adapter/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_contract_without_secret(self):
        self._factor(secret_reference="ref:owners/real-adapter/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_real_adapter_contract",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/real-adapter/command",
            "--canary-owner-email",
            self.owner.email,
            "--sdk-dependency-confirmed",
            "--credential-strategy-confirmed",
            "--network-timeout-confirmed",
            "--rollout-owner-confirmed",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("real_adapter_contract=", output.getvalue())
        self.assertIn("implementation_plan=", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())

    def _factor(self, *, secret_reference: str, provider_key: str = "hashicorp-vault") -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key=provider_key,
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
