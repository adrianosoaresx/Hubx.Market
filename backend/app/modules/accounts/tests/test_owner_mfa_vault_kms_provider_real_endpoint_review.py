from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_provider_real_endpoint_review_queries import (
    owner_mfa_vault_kms_provider_real_endpoint_review_queries,
)
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaVaultKmsProviderRealEndpointReviewTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="MFA Real Endpoint",
            slug="mfa-real-endpoint",
            subdomain="mfa-real-endpoint",
        )
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.real.endpoint@hubx.market", role="owner")

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/real-endpoint/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_review_ready_for_hashicorp_vault_when_contract_is_confirmed(self):
        self._factor(secret_reference="ref:owners/real-endpoint/probe")

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            result = owner_mfa_vault_kms_provider_real_endpoint_review_queries.get_review(
                tenant_id=self.tenant.id,
                target_provider="hashicorp-vault",
                probe_reference="owners/real-endpoint/probe",
                canary_owner_email=self.owner.email,
                endpoint_url_confirmed=True,
                auth_strategy_confirmed=True,
                secret_path_contract_confirmed=True,
                timeout_budget_confirmed=True,
                rollback_confirmed=True,
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["endpoint_contract"]["provider"], "hashicorp-vault")
        self.assertIn("OWNER_MFA_HASHICORP_VAULT_ADDR", result["endpoint_contract"]["settings"])
        self.assertIn("Owner MFA Hashicorp Vault Real Endpoint Execution", result["next_tracks"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/real-endpoint/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_review_blocks_missing_timeout_confirmation(self):
        self._factor(secret_reference="ref:owners/real-endpoint/probe")

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            result = owner_mfa_vault_kms_provider_real_endpoint_review_queries.get_review(
                tenant_id=self.tenant.id,
                target_provider="hashicorp-vault",
                probe_reference="owners/real-endpoint/probe",
                canary_owner_email=self.owner.email,
                endpoint_url_confirmed=True,
                auth_strategy_confirmed=True,
                secret_path_contract_confirmed=True,
                timeout_budget_confirmed=False,
                rollback_confirmed=True,
            )

        self.assertFalse(result["ready"])
        self.assertIn("confirmation-missing:timeout_budget_confirmed", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="gcp-secret-manager",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/real-endpoint/probe": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_review_blocks_non_initial_endpoint_target(self):
        self._factor(secret_reference="ref:owners/real-endpoint/probe", provider_key="gcp-secret-manager")

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            result = owner_mfa_vault_kms_provider_real_endpoint_review_queries.get_review(
                tenant_id=self.tenant.id,
                target_provider="gcp-secret-manager",
                probe_reference="owners/real-endpoint/probe",
                canary_owner_email=self.owner.email,
                endpoint_url_confirmed=True,
                auth_strategy_confirmed=True,
                secret_path_contract_confirmed=True,
                timeout_budget_confirmed=True,
                rollback_confirmed=True,
            )

        self.assertFalse(result["ready"])
        self.assertIn("real-endpoint-target-not-supported", result["blockers"])

    @override_settings(
        OWNER_MFA_SECRET_PROVIDER="hashicorp-vault",
        OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=True,
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS="ready",
        OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS={"owners/real-endpoint/command": secret},
        OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False,
    )
    def test_command_outputs_endpoint_contract_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/real-endpoint/command")
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module"):
            call_command(
                "owner_mfa_vault_kms_provider_real_endpoint_review",
                "--tenant-id",
                str(self.tenant.id),
                "--target-provider",
                "hashicorp-vault",
                "--probe-reference",
                "owners/real-endpoint/command",
                "--canary-owner-email",
                self.owner.email,
                "--endpoint-url-confirmed",
                "--auth-strategy-confirmed",
                "--secret-path-contract-confirmed",
                "--timeout-budget-confirmed",
                "--rollback-confirmed",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("endpoint_provider=hashicorp-vault", output.getvalue())
        self.assertIn("endpoint_contract=", output.getvalue())
        self.assertIn("decision key=endpoint-target", output.getvalue())
        self.assertIn("rollback=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/real-endpoint/command", output.getvalue())

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
