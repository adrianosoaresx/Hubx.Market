from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_real_endpoint_execution_queries import (
    owner_mfa_hashicorp_vault_real_endpoint_execution_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class _FakeVaultClient:
    def __init__(self, *, payload=None, exc=None, **kwargs):
        self.payload = payload or {}
        self.exc = exc
        self.auth = SimpleNamespace(approle=SimpleNamespace(login=lambda **kwargs: None))
        self.secrets = SimpleNamespace(
            kv=SimpleNamespace(v2=SimpleNamespace(read_secret_version=self.read_secret_version))
        )

    def read_secret_version(self, *, path, mount_point):
        if self.exc:
            raise self.exc
        return self.payload


class _FakeVaultModule:
    def __init__(self, *, payload=None, exc=None):
        self.payload = payload or {}
        self.exc = exc

    def Client(self, **kwargs):
        return _FakeVaultClient(payload=self.payload, exc=self.exc, **kwargs)


class OwnerMfaHashicorpVaultRealEndpointExecutionTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="MFA Vault Endpoint",
            slug="mfa-vault-endpoint",
            subdomain="mfa-vault-endpoint",
        )
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.vault.endpoint@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
    )
    def test_hashicorp_vault_endpoint_reads_secret_field(self):
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_secret_providers.resolve("owners/hashicorp/probe")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "hashicorp-vault")
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-ready")
        self.assertEqual(result.secret, self.secret)

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
    )
    def test_hashicorp_vault_endpoint_maps_missing_secret_field(self):
        hvac = _FakeVaultModule(payload={"data": {"data": {}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_secret_providers.resolve("owners/hashicorp/probe")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-missing")
        self.assertEqual(result.secret, "")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
    )
    def test_hashicorp_vault_endpoint_maps_permission_error(self):
        hvac = _FakeVaultModule(exc=PermissionError("permission denied"))

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_secret_providers.resolve("owners/hashicorp/probe")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-permission-denied")
        self.assertEqual(result.secret, "")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_ready_when_review_and_vault_probe_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_hashicorp_vault_real_endpoint_execution_queries.get_evidence(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp/evidence",
                canary_owner_email=self.owner.email,
            )

        self.assertTrue(result["ready"])
        self.assertTrue(result["endpoint_enabled"])
        self.assertEqual(result["probe"]["result"], "owner-mfa-secret-provider-vault-ready")
        self.assertIn("Owner MFA Hashicorp Vault Staging Smoke Evidence", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=False,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/hashicorp/evidence": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_blocks_when_endpoint_flag_is_disabled(self):
        self._factor(secret_reference="ref:owners/hashicorp/evidence")

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            result = owner_mfa_hashicorp_vault_real_endpoint_execution_queries.get_evidence(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp/evidence",
                canary_owner_email=self.owner.email,
            )

        self.assertFalse(result["ready"])
        self.assertIn("hashicorp-vault-endpoint-not-enabled", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True,
        OWNER_MFA_HASHICORP_VAULT_ADDR="https://vault.internal",
        OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD="token",
        OWNER_MFA_HASHICORP_VAULT_TOKEN="vault-token",
        OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT="secret",
        OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD="totp_secret",
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_endpoint_evidence_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_real_endpoint_execute",
                "--tenant-id",
                str(self.tenant.id),
                "--probe-reference",
                "owners/hashicorp/command",
                "--canary-owner-email",
                self.owner.email,
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("endpoint_enabled=True", output.getvalue())
        self.assertIn("probe_result=owner-mfa-secret-provider-vault-ready", output.getvalue())
        self.assertIn("decision key=secret-redaction", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp/command", output.getvalue())
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
