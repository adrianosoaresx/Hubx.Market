from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_vault_kms_production_closure_queries import (
    owner_mfa_vault_kms_production_closure_queries,
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


class OwnerMfaVaultKmsProductionClosureTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="MFA Vault Closure",
            slug="mfa-vault-closure",
            subdomain="mfa-vault-closure",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.mfa.vault.closure@hubx.market",
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
    def test_closure_ready_when_monitoring_and_closure_signals_are_clean(self):
        self._factor(secret_reference="ref:owners/hashicorp-closure/ready")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            closure = owner_mfa_vault_kms_production_closure_queries.get_closure(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-closure/ready",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=True,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=True,
                evidence_redacted=True,
                rollback_runbook_confirmed=True,
                residual_risks_accepted=True,
                tenant_expansion_plan_documented=True,
            )

        self.assertEqual(closure["result"], "owner-mfa-vault-kms-production-closure-ready")
        self.assertTrue(closure["ready"])
        self.assertEqual(closure["blockers"], ())
        self.assertIn("Owner MFA Hashicorp Vault Tenant Expansion Review", closure["next_tracks"])

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
    def test_closure_blocks_when_expansion_plan_is_missing(self):
        self._factor(secret_reference="ref:owners/hashicorp-closure/blocked")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            closure = owner_mfa_vault_kms_production_closure_queries.get_closure(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-closure/blocked",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=True,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=True,
                evidence_redacted=True,
                rollback_runbook_confirmed=True,
                residual_risks_accepted=True,
                tenant_expansion_plan_documented=False,
            )

        self.assertFalse(closure["ready"])
        self.assertEqual(closure["status"], "blocked")
        self.assertIn("closure:tenant-expansion-plan-not-documented", closure["blockers"])

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
    def test_command_outputs_closure_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-closure/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_vault_kms_production_closure",
                "--tenant-id",
                str(self.tenant.id),
                "--probe-reference",
                "owners/hashicorp-closure/command",
                "--canary-owner-email",
                self.owner.email,
                "--monitoring-window-elapsed",
                "--provider-health-stable",
                "--owner-login-error-spike-absent",
                "--support-incidents-absent",
                "--rollback-signal-absent",
                "--evidence-redacted",
                "--rollback-runbook-confirmed",
                "--residual-risks-accepted",
                "--tenant-expansion-plan-documented",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertIn("expansion_guardrail=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-closure/command", output.getvalue())
        self.assertNotIn("vault-token", output.getvalue())

    def test_command_can_fail_when_closure_is_blocked(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_vault_kms_production_closure",
                "--tenant-id",
                str(self.tenant.id),
                "--canary-owner-email",
                self.owner.email,
                "--fail-on-blockers",
                stdout=StringIO(),
            )

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
