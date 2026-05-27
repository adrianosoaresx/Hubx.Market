from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries import (
    owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderRealAdapterSkeletonTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Real Skeleton", slug="mfa-real-skeleton", subdomain="mfa-real-skeleton")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.real.skeleton@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/real-skeleton/probe": secret},
    )
    def test_provider_real_adapter_branch_resolves_configured_reference(self):
        result = owner_mfa_secret_providers.resolve("owners/real-skeleton/probe")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "hashicorp-vault")
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-ready")
        self.assertEqual(result.secret, self.secret)

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="timeout",
    )
    def test_provider_real_adapter_branch_maps_timeout(self):
        result = owner_mfa_secret_providers.resolve("owners/real-skeleton/probe")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-timeout")
        self.assertEqual(result.secret, "")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
    )
    def test_provider_real_adapter_branch_blocks_invalid_reference_before_lookup(self):
        result = owner_mfa_secret_providers.resolve("../owners/real-skeleton/probe")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-invalid-reference")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/real-skeleton/evidence": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_ready_when_contract_and_real_probe_are_ready(self):
        self._factor(secret_reference="ref:owners/real-skeleton/evidence")

        result = owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/real-skeleton/evidence",
            canary_owner_email=self.owner.email,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["probe"]["result"], "owner-mfa-secret-provider-vault-ready")
        self.assertTrue(result["real_adapter_enabled"])
        self.assertIn("Owner MFA Vault/KMS Provider SDK Dependency Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=False,
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/real-skeleton/evidence": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_blocks_when_real_adapter_mode_is_disabled(self):
        self._factor(secret_reference="ref:owners/real-skeleton/evidence")

        result = owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/real-skeleton/evidence",
            canary_owner_email=self.owner.email,
        )

        self.assertFalse(result["ready"])
        self.assertIn("real-adapter-mode-not-enabled", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/real-skeleton/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_evidence_without_secret(self):
        self._factor(secret_reference="ref:owners/real-skeleton/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_real_adapter_skeleton_execute",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/real-skeleton/command",
            "--canary-owner-email",
            self.owner.email,
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("probe_result=owner-mfa-secret-provider-vault-ready", output.getvalue())
        self.assertIn("decision key=real-adapter-mode", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="hashicorp-vault",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
