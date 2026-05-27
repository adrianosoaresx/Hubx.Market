from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_readiness_evidence_queries import (
    owner_mfa_vault_kms_provider_readiness_evidence_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderReadinessEvidenceTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Evidence", slug="mfa-evidence", subdomain="mfa-evidence")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.evidence@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/evidence/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_readiness_evidence_ready_when_skeleton_and_health_are_ready(self):
        self._factor(secret_reference="ref:owners/evidence/probe")

        result = owner_mfa_vault_kms_provider_readiness_evidence_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/evidence/probe",
        )

        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Vault/KMS Provider Staging Canary Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="timeout",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_readiness_evidence_blocks_when_skeleton_probe_fails(self):
        self._factor(secret_reference="ref:owners/evidence/probe")

        result = owner_mfa_vault_kms_provider_readiness_evidence_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/evidence/probe",
        )

        self.assertFalse(result["ready"])
        self.assertIn("skeleton-execution-not-ready", result["blockers"])
        self.assertIn("probe:owner-mfa-secret-provider-vault-timeout", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/evidence/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_readiness_evidence_blocks_when_target_mismatches_health_provider(self):
        self._factor(secret_reference="ref:owners/evidence/probe")

        result = owner_mfa_vault_kms_provider_readiness_evidence_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="aws-secrets-manager",
            probe_reference="owners/evidence/probe",
        )

        self.assertFalse(result["ready"])
        self.assertIn("current-provider-does-not-match-target", result["blockers"])
        self.assertIn("provider-health-target-mismatch", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS={"owners/evidence/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_evidence_pack_without_secret_value(self):
        self._factor(secret_reference="ref:owners/evidence/command")
        output = StringIO()

        call_command(
            "owner_mfa_vault_kms_provider_readiness_evidence",
            "--tenant-id",
            str(self.tenant.id),
            "--target-provider",
            "hashicorp-vault",
            "--probe-reference",
            "owners/evidence/command",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("evidence=probe_result=owner-mfa-secret-provider-vault-ready", output.getvalue())
        self.assertIn("decision key=provider-health-closure", output.getvalue())
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
