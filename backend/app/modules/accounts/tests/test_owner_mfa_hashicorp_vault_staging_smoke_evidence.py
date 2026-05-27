from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_staging_smoke_evidence_queries import (
    owner_mfa_hashicorp_vault_staging_smoke_evidence_queries,
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


class OwnerMfaHashicorpVaultStagingSmokeEvidenceTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="MFA Vault Smoke",
            slug="mfa-vault-smoke",
            subdomain="mfa-vault-smoke",
        )
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.vault.smoke@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.staging.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_smoke_evidence_ready_when_execution_and_confirmations_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp-smoke/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_hashicorp_vault_staging_smoke_evidence_queries.get_evidence(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-smoke/evidence",
                canary_owner_email=self.owner.email,
                staging_probe_passed=True,
                invalid_path_blocked=True,
                logs_redacted=True,
                rollback_verified=True,
                post_smoke_health_ready=True,
        )

        self.assertTrue(result["ready"])
        self.assertIn("evidence_pack", result)
        self.assertIn("Owner MFA Vault/KMS Provider Production Readiness Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.staging.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_smoke_evidence_blocks_missing_redaction_confirmation(self):
        self._factor(secret_reference="ref:owners/hashicorp-smoke/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_hashicorp_vault_staging_smoke_evidence_queries.get_evidence(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-smoke/evidence",
                canary_owner_email=self.owner.email,
                staging_probe_passed=True,
                invalid_path_blocked=True,
                logs_redacted=False,
                rollback_verified=True,
                post_smoke_health_ready=True,
            )

        self.assertFalse(result["ready"])
        self.assertIn("confirmation-missing:logs_redacted", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.staging.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_smoke_evidence_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-smoke/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_staging_smoke_evidence",
                "--tenant-id",
                str(self.tenant.id),
                "--probe-reference",
                "owners/hashicorp-smoke/command",
                "--canary-owner-email",
                self.owner.email,
                "--staging-probe-passed",
                "--invalid-path-blocked",
                "--logs-redacted",
                "--rollback-verified",
                "--post-smoke-health-ready",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("evidence=probe_result=owner-mfa-secret-provider-vault-ready", output.getvalue())
        self.assertIn("decision key=redaction", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-smoke/command", output.getvalue())
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
