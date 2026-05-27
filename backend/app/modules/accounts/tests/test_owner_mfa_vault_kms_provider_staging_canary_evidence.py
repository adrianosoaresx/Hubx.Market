from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_staging_canary_evidence_queries import (
    owner_mfa_vault_kms_provider_staging_canary_evidence_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderStagingCanaryEvidenceTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Canary Evidence", slug="mfa-canary-evidence", subdomain="mfa-canary-evidence")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.canary.evidence@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/canary-evidence/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_canary_evidence_ready_when_review_and_manual_results_pass(self):
        self._factor(secret_reference="ref:owners/canary-evidence/probe")

        result = owner_mfa_vault_kms_provider_staging_canary_evidence_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/canary-evidence/probe",
            canary_owner_email=self.owner.email,
            valid_login_passed=True,
            invalid_challenge_blocked=True,
            post_health_ready=True,
            logs_redacted=True,
            rollback_verified=True,
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Vault/KMS Provider Real Adapter Contract Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/canary-evidence/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_canary_evidence_blocks_failed_manual_result(self):
        self._factor(secret_reference="ref:owners/canary-evidence/probe")

        result = owner_mfa_vault_kms_provider_staging_canary_evidence_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/canary-evidence/probe",
            canary_owner_email=self.owner.email,
            valid_login_passed=True,
            invalid_challenge_blocked=False,
            post_health_ready=True,
            logs_redacted=True,
            rollback_verified=True,
        )

        self.assertFalse(result["ready"])
        self.assertIn("manual-check-failed:invalid_challenge_blocked", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="timeout",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_canary_evidence_blocks_when_review_not_ready(self):
        self._factor(secret_reference="ref:owners/canary-evidence/probe")

        result = owner_mfa_vault_kms_provider_staging_canary_evidence_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/canary-evidence/probe",
            canary_owner_email=self.owner.email,
            valid_login_passed=True,
            invalid_challenge_blocked=True,
            post_health_ready=True,
            logs_redacted=True,
            rollback_verified=True,
        )

        self.assertFalse(result["ready"])
        self.assertIn("staging-canary-review-not-ready", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/canary-evidence/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_evidence_without_secret(self):
        self._factor(secret_reference="ref:owners/canary-evidence/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_staging_canary_evidence",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/canary-evidence/command",
            "--canary-owner-email",
            self.owner.email,
            "--valid-login-passed",
            "--invalid-challenge-blocked",
            "--post-health-ready",
            "--logs-redacted",
            "--rollback-verified",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("evidence=valid_login_passed=True", output.getvalue())
        self.assertIn("decision key=invalid-challenge", output.getvalue())
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
