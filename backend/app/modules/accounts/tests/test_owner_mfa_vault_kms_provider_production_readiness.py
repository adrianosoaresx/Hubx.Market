from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_production_readiness_queries import (
    owner_mfa_vault_kms_provider_production_readiness_queries,
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


class OwnerMfaVaultKmsProviderProductionReadinessTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="MFA Vault Production Readiness",
            slug="mfa-vault-production-readiness",
            subdomain="mfa-vault-production-readiness",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.mfa.vault.production@hubx.market",
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
    def test_readiness_go_when_smoke_health_and_confirmations_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp-production/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_vault_kms_provider_production_readiness_queries.get_review(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-production/evidence",
                canary_owner_email=self.owner.email,
                runbook_reviewed=True,
                rollback_owner_confirmed=True,
                monitoring_confirmed=True,
                change_window_confirmed=True,
                credential_rotation_confirmed=True,
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["go_no_go"]["decision"], "GO")
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Hashicorp Vault Production Gate Review", result["next_tracks"])

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
    def test_readiness_blocks_missing_change_window(self):
        self._factor(secret_reference="ref:owners/hashicorp-production/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_vault_kms_provider_production_readiness_queries.get_review(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-production/evidence",
                canary_owner_email=self.owner.email,
                runbook_reviewed=True,
                rollback_owner_confirmed=True,
                monitoring_confirmed=True,
                change_window_confirmed=False,
                credential_rotation_confirmed=True,
            )

        self.assertFalse(result["ready"])
        self.assertEqual(result["go_no_go"]["decision"], "NO-GO")
        self.assertIn("confirmation-missing:change_window_confirmed", result["blockers"])

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
    def test_command_outputs_go_no_go_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-production/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_vault_kms_provider_production_readiness",
                "--tenant-id",
                str(self.tenant.id),
                "--probe-reference",
                "owners/hashicorp-production/command",
                "--canary-owner-email",
                self.owner.email,
                "--runbook-reviewed",
                "--rollback-owner-confirmed",
                "--monitoring-confirmed",
                "--change-window-confirmed",
                "--credential-rotation-confirmed",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision=GO", output.getvalue())
        self.assertIn("decision key=provider-health", output.getvalue())
        self.assertIn("runbook=", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-production/command", output.getvalue())
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
