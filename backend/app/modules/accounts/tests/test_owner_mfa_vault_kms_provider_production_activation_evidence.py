from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_production_activation_evidence_queries import (
    owner_mfa_vault_kms_provider_production_activation_evidence_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class _FakeVaultClient:
    def __init__(self, *, payload=None, **kwargs):
        self.payload = payload or {}
        self.auth = SimpleNamespace(approle=SimpleNamespace(login=lambda **kwargs: None))
        self.secrets = SimpleNamespace(
            kv=SimpleNamespace(v2=SimpleNamespace(read_secret_version=self.read_secret_version))
        )

    def read_secret_version(self, *, path, mount_point):
        return self.payload


class _FakeVaultModule:
    def __init__(self, *, payload=None):
        self.payload = payload or {}

    def Client(self, **kwargs):
        return _FakeVaultClient(payload=self.payload, **kwargs)


class OwnerMfaVaultKmsProviderProductionActivationEvidenceTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="MFA Vault Activation",
            slug="mfa-vault-activation",
            subdomain="mfa-vault-activation",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.mfa.vault.activation@hubx.market",
            role="owner",
        )

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.production.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_activation_evidence_ready_when_gate_and_post_activation_confirmations_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp-activation/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_vault_kms_provider_production_activation_evidence_queries.get_evidence(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-activation/evidence",
                canary_owner_email=self.owner.email,
                deployment_completed=True,
                flags_enabled_for_tenant=True,
                post_deploy_probe_passed=True,
                owner_login_challenge_passed=True,
                provider_health_ready=True,
                rollback_not_required=True,
                evidence_redacted=True,
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Hashicorp Vault Post-Activation Monitoring Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.production.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_activation_evidence_blocks_failed_owner_login_confirmation(self):
        self._factor(secret_reference="ref:owners/hashicorp-activation/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_vault_kms_provider_production_activation_evidence_queries.get_evidence(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-activation/evidence",
                canary_owner_email=self.owner.email,
                deployment_completed=True,
                flags_enabled_for_tenant=True,
                post_deploy_probe_passed=True,
                owner_login_challenge_passed=False,
                provider_health_ready=True,
                rollback_not_required=True,
                evidence_redacted=True,
            )

        self.assertFalse(result["ready"])
        self.assertIn("confirmation-missing:owner_login_challenge_passed", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.production.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_activation_evidence_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-activation/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_vault_kms_provider_production_activation_evidence",
                "--tenant-id",
                str(self.tenant.id),
                "--probe-reference",
                "owners/hashicorp-activation/command",
                "--canary-owner-email",
                self.owner.email,
                "--deployment-completed",
                "--flags-enabled-for-tenant",
                "--post-deploy-probe-passed",
                "--owner-login-challenge-passed",
                "--provider-health-ready",
                "--rollback-not-required",
                "--evidence-redacted",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("evidence=gate_decision=GO", output.getvalue())
        self.assertIn("decision key=runtime-validation", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-activation/command", output.getvalue())
        self.assertNotIn("vault-token", output.getvalue())

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
