from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries import (
    owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderAdapterSkeletonTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Skeleton", slug="mfa-skeleton", subdomain="mfa-skeleton")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.skeleton@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/skeleton/totp": secret},
    )
    def test_provider_skeleton_resolves_configured_reference(self):
        result = owner_mfa_secret_providers.resolve("owners/skeleton/totp")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "hashicorp-vault")
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-ready")
        self.assertEqual(result.secret, self.secret)

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="aws-secrets-manager",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_NAMESPACE="prod/owners",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"prod/owners/skeleton/totp": secret},
    )
    def test_provider_skeleton_applies_namespace_without_changing_reference(self):
        result = owner_mfa_secret_providers.resolve("skeleton/totp")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "aws-secrets-manager")
        self.assertEqual(result.reference, "skeleton/totp")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={},
    )
    def test_provider_skeleton_returns_missing_without_exception(self):
        result = owner_mfa_secret_providers.resolve("owners/missing/totp")

        self.assertFalse(result.ready)
        self.assertEqual(result.secret, "")
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-missing")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="hashicorp-vault", OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="timeout")
    def test_provider_skeleton_returns_timeout_as_recoverable_failure(self):
        result = owner_mfa_secret_providers.resolve("owners/timeout/totp")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-timeout")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="hashicorp-vault", OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready")
    def test_provider_skeleton_rejects_invalid_reference(self):
        result = owner_mfa_secret_providers.resolve("../owners/totp")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-invalid-reference")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/skeleton/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_ready_when_contract_and_probe_are_ready(self):
        self._factor(secret_reference="ref:owners/skeleton/probe")

        result = owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/skeleton/probe",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["probe"]["result"], "owner-mfa-secret-provider-vault-ready")
        self.assertTrue(result["probe"]["secret_returned"])
        self.assertIn("Owner MFA Vault/KMS Provider Readiness Evidence Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="timeout",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_blocks_when_probe_fails(self):
        self._factor(secret_reference="ref:owners/skeleton/probe")

        result = owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/skeleton/probe",
        )

        self.assertFalse(result["ready"])
        self.assertIn("probe:owner-mfa-secret-provider-vault-timeout", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/skeleton/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_probe_decisions_and_rollback(self):
        self._factor(secret_reference="ref:owners/skeleton/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_adapter_skeleton_execute",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/skeleton/command",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("probe_result=owner-mfa-secret-provider-vault-ready", output.getvalue())
        self.assertIn("decision key=probe-resolution", output.getvalue())
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
