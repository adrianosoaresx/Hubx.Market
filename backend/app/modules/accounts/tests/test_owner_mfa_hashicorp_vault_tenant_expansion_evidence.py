from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries import (
    owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries,
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


class OwnerMfaHashicorpVaultTenantExpansionEvidenceTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.canary = Tenant.objects.create(
            name="MFA Vault Evidence Canary",
            slug="mfa-vault-evidence-canary",
            subdomain="mfa-vault-evidence-canary",
        )
        self.target = Tenant.objects.create(
            name="MFA Vault Evidence Target",
            slug="mfa-vault-evidence-target",
            subdomain="mfa-vault-evidence-target",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.canary,
            email="owner.mfa.vault.expansion.evidence@hubx.market",
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
    def test_evidence_ready_when_review_and_target_confirmations_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp-expansion-evidence/ready")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            evidence = owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries.get_evidence(
                canary_tenant_id=self.canary.id,
                target_tenant_id=self.target.id,
                probe_reference="owners/hashicorp-expansion-evidence/ready",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=True,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=True,
                canary_evidence_redacted=True,
                rollback_runbook_confirmed=True,
                residual_risks_accepted=True,
                tenant_expansion_plan_documented=True,
                expansion_window_confirmed=True,
                per_tenant_evidence_required=True,
                support_standby_confirmed=True,
                rollback_window_confirmed=True,
                target_flags_enabled=True,
                target_activation_evidence_captured=True,
                target_monitoring_scheduled=True,
                target_owner_login_challenge_passed=True,
                target_provider_health_ready=True,
                rollback_not_required=True,
                evidence_redacted=True,
            )

        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["status"], "ready")
        self.assertEqual(evidence["blockers"], ())
        self.assertIn("Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review", evidence["next_tracks"])

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
    def test_evidence_blocks_when_target_monitoring_is_missing(self):
        self._factor(secret_reference="ref:owners/hashicorp-expansion-evidence/blocked")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            evidence = owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries.get_evidence(
                canary_tenant_id=self.canary.id,
                target_tenant_id=self.target.id,
                probe_reference="owners/hashicorp-expansion-evidence/blocked",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=True,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=True,
                canary_evidence_redacted=True,
                rollback_runbook_confirmed=True,
                residual_risks_accepted=True,
                tenant_expansion_plan_documented=True,
                expansion_window_confirmed=True,
                per_tenant_evidence_required=True,
                support_standby_confirmed=True,
                rollback_window_confirmed=True,
                target_flags_enabled=True,
                target_activation_evidence_captured=True,
                target_monitoring_scheduled=False,
                target_owner_login_challenge_passed=True,
                target_provider_health_ready=True,
                rollback_not_required=True,
                evidence_redacted=True,
            )

        self.assertFalse(evidence["ready"])
        self.assertIn("confirmation-missing:target_monitoring_scheduled", evidence["blockers"])

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
    def test_command_outputs_evidence_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-expansion-evidence/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_tenant_expansion_evidence",
                "--canary-tenant-id",
                str(self.canary.id),
                "--target-tenant-id",
                str(self.target.id),
                "--probe-reference",
                "owners/hashicorp-expansion-evidence/command",
                "--canary-owner-email",
                self.owner.email,
                "--monitoring-window-elapsed",
                "--provider-health-stable",
                "--owner-login-error-spike-absent",
                "--support-incidents-absent",
                "--rollback-signal-absent",
                "--canary-evidence-redacted",
                "--rollback-runbook-confirmed",
                "--residual-risks-accepted",
                "--tenant-expansion-plan-documented",
                "--expansion-window-confirmed",
                "--per-tenant-evidence-required",
                "--support-standby-confirmed",
                "--rollback-window-confirmed",
                "--target-flags-enabled",
                "--target-activation-evidence-captured",
                "--target-monitoring-scheduled",
                "--target-owner-login-challenge-passed",
                "--target-provider-health-ready",
                "--rollback-not-required",
                "--evidence-redacted",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("evidence=target_tenant_id=", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-expansion-evidence/command", output.getvalue())
        self.assertNotIn("vault-token", output.getvalue())

    def test_command_can_fail_when_evidence_is_blocked(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_hashicorp_vault_tenant_expansion_evidence",
                "--canary-tenant-id",
                str(self.canary.id),
                "--target-tenant-id",
                str(self.target.id),
                "--canary-owner-email",
                self.owner.email,
                "--fail-on-blockers",
                stdout=StringIO(),
            )

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.canary,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="hashicorp-vault",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
