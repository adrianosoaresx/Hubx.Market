from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_staging_canary_queries import (
    owner_mfa_vault_kms_provider_staging_canary_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderStagingCanaryTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Canary", slug="mfa-canary", subdomain="mfa-canary")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.canary@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/canary/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_canary_review_ready_when_readiness_evidence_and_owner_are_ready(self):
        self._factor(secret_reference="ref:owners/canary/probe")

        result = owner_mfa_vault_kms_provider_staging_canary_queries.get_review(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/canary/probe",
            canary_owner_email=self.owner.email,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Vault/KMS Provider Staging Canary Evidence Execution", result["next_tracks"])
        self.assertTrue(result["manual_checklist"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/canary/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_canary_review_blocks_without_owner_email(self):
        self._factor(secret_reference="ref:owners/canary/probe")

        result = owner_mfa_vault_kms_provider_staging_canary_queries.get_review(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/canary/probe",
            canary_owner_email="",
        )

        self.assertFalse(result["ready"])
        self.assertIn("canary-owner-email-required", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="timeout",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_canary_review_blocks_when_readiness_evidence_is_blocked(self):
        self._factor(secret_reference="ref:owners/canary/probe")

        result = owner_mfa_vault_kms_provider_staging_canary_queries.get_review(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/canary/probe",
            canary_owner_email=self.owner.email,
        )

        self.assertFalse(result["ready"])
        self.assertIn("readiness-evidence-not-ready", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/canary/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_checklist_without_secret(self):
        self._factor(secret_reference="ref:owners/canary/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_staging_canary_review",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/canary/command",
            "--canary-owner-email",
            self.owner.email,
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("manual_check=", output.getvalue())
        self.assertIn("success_signal=", output.getvalue())
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
