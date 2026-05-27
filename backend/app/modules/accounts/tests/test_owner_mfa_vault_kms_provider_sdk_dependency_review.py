from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_sdk_dependency_review_queries import (
    owner_mfa_vault_kms_provider_sdk_dependency_review_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderSdkDependencyReviewTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA SDK Review", slug="mfa-sdk-review", subdomain="mfa-sdk-review")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.sdk.review@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/sdk-review/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_review_ready_when_skeleton_and_confirmations_are_ready(self):
        self._factor(secret_reference="ref:owners/sdk-review/probe")

        result = owner_mfa_vault_kms_provider_sdk_dependency_review_queries.get_review(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/sdk-review/probe",
            canary_owner_email=self.owner.email,
            dependency_pinned_confirmed=True,
            import_optional_confirmed=True,
            deploy_rollback_confirmed=True,
            license_review_confirmed=True,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["dependency_contract"]["packages"], ("hvac",))
        self.assertEqual(result["import_contract"]["imports"], ("hvac",))
        self.assertIn("Owner MFA Vault/KMS Provider SDK Adapter Execution", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/sdk-review/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_review_blocks_when_license_confirmation_is_missing(self):
        self._factor(secret_reference="ref:owners/sdk-review/probe")

        result = owner_mfa_vault_kms_provider_sdk_dependency_review_queries.get_review(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/sdk-review/probe",
            canary_owner_email=self.owner.email,
            dependency_pinned_confirmed=True,
            import_optional_confirmed=True,
            deploy_rollback_confirmed=True,
            license_review_confirmed=False,
        )

        self.assertFalse(result["ready"])
        self.assertIn("confirmation-missing:license_review_confirmed", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="aws-kms",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/sdk-review/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_review_blocks_unsupported_direct_kms_target(self):
        self._factor(secret_reference="ref:owners/sdk-review/probe", provider_key="aws-kms")

        result = owner_mfa_vault_kms_provider_sdk_dependency_review_queries.get_review(
            tenant_id=self.tenant.id,
            target_provider="aws-kms",
            probe_reference="owners/sdk-review/probe",
            canary_owner_email=self.owner.email,
            dependency_pinned_confirmed=True,
            import_optional_confirmed=True,
            deploy_rollback_confirmed=True,
            license_review_confirmed=True,
        )

        self.assertFalse(result["ready"])
        self.assertIn("sdk-target-provider-unsupported", result["blockers"])
        self.assertEqual(result["dependency_contract"]["packages"], ())

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/sdk-review/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_dependency_contract_without_secret(self):
        self._factor(secret_reference="ref:owners/sdk-review/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_sdk_dependency_review",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/sdk-review/command",
            "--canary-owner-email",
            self.owner.email,
            "--dependency-pinned-confirmed",
            "--import-optional-confirmed",
            "--deploy-rollback-confirmed",
            "--license-review-confirmed",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("packages=hvac", output.getvalue())
        self.assertIn("dependency_contract=", output.getvalue())
        self.assertIn("import_contract=", output.getvalue())
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
