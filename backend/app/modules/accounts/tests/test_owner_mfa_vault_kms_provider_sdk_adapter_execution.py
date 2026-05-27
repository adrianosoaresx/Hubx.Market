from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_sdk_adapter_execution_queries import (
    owner_mfa_vault_kms_provider_sdk_adapter_execution_queries,
)
from app.modules.accounts.infrastructure.owner_mfa_secret_providers import owner_mfa_secret_providers
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderSdkAdapterExecutionTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA SDK Adapter", slug="mfa-sdk-adapter", subdomain="mfa-sdk-adapter")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.sdk.adapter@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/sdk-adapter/probe": secret},
    )
    def test_sdk_adapter_branch_resolves_after_lazy_import(self):
        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            result = owner_mfa_secret_providers.resolve("owners/sdk-adapter/probe")

        self.assertTrue(result.ready)
        self.assertEqual(result.provider, "hashicorp-vault")
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-ready")
        self.assertEqual(result.secret, self.secret)

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
    )
    def test_sdk_adapter_branch_maps_missing_dependency_to_unavailable(self):
        with patch(
            "app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module",
            side_effect=ImportError("missing hvac"),
        ):
            result = owner_mfa_secret_providers.resolve("owners/sdk-adapter/probe")

        self.assertFalse(result.ready)
        self.assertEqual(result.result, "owner-mfa-secret-provider-vault-unavailable")
        self.assertEqual(result.secret, "")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/sdk-adapter/evidence": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_ready_when_dependency_review_and_sdk_probe_are_ready(self):
        self._factor(secret_reference="ref:owners/sdk-adapter/evidence")

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            result = owner_mfa_vault_kms_provider_sdk_adapter_execution_queries.get_evidence(
                tenant_id=self.tenant.id,
                target_provider="hashicorp-vault",
                probe_reference="owners/sdk-adapter/evidence",
                canary_owner_email=self.owner.email,
            )

        self.assertTrue(result["ready"])
        self.assertTrue(result["sdk_adapter_enabled"])
        self.assertEqual(result["probe"]["result"], "owner-mfa-secret-provider-vault-ready")
        self.assertIn("Owner MFA Vault/KMS Provider Real Endpoint Review", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=False,
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS={"owners/sdk-adapter/evidence": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_execution_blocks_when_sdk_adapter_mode_is_disabled(self):
        self._factor(secret_reference="ref:owners/sdk-adapter/evidence")

        result = owner_mfa_vault_kms_provider_sdk_adapter_execution_queries.get_evidence(
            tenant_id=self.tenant.id,
            target_provider="hashicorp-vault",
            probe_reference="owners/sdk-adapter/evidence",
            canary_owner_email=self.owner.email,
        )

        self.assertFalse(result["ready"])
        self.assertIn("sdk-adapter-mode-not-enabled", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/sdk-adapter/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_sdk_evidence_without_secret(self):
        self._factor(secret_reference="ref:owners/sdk-adapter/command")
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            call_command(
                "owner_mfa_vault_kms_provider_sdk_adapter_execute",
                "--tenant-id",
                str(self.tenant.id),
                "--target-provider",
                "hashicorp-vault",
                "--probe-reference",
                "owners/sdk-adapter/command",
                "--canary-owner-email",
                self.owner.email,
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("sdk_adapter_enabled=True", output.getvalue())
        self.assertIn("probe_result=owner-mfa-secret-provider-vault-ready", output.getvalue())
        self.assertIn("decision key=lazy-import", output.getvalue())
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
