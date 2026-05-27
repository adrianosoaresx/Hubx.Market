from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_queries import (
    owner_mfa_hashicorp_vault_tenant_expansion_queries,
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


class OwnerMfaHashicorpVaultTenantExpansionTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.canary = Tenant.objects.create(
            name="MFA Vault Canary",
            slug="mfa-vault-canary",
            subdomain="mfa-vault-canary",
        )
        self.target = Tenant.objects.create(
            name="MFA Vault Target",
            slug="mfa-vault-target",
            subdomain="mfa-vault-target",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.canary,
            email="owner.mfa.vault.expansion@hubx.market",
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
    def test_expansion_ready_when_canary_closure_and_target_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp-expansion/ready")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            review = owner_mfa_hashicorp_vault_tenant_expansion_queries.get_review(
                canary_tenant_id=self.canary.id,
                target_tenant_ids=str(self.target.id),
                probe_reference="owners/hashicorp-expansion/ready",
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
                expansion_window_confirmed=True,
                per_tenant_evidence_required=True,
                support_standby_confirmed=True,
                rollback_window_confirmed=True,
            )

        self.assertTrue(review["ready"])
        self.assertEqual(review["status"], "ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution", review["next_tracks"])

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
    def test_expansion_blocks_inactive_target_and_parallel_window(self):
        self.target.is_active = False
        self.target.save(update_fields=["is_active"])
        self._factor(secret_reference="ref:owners/hashicorp-expansion/blocked")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            review = owner_mfa_hashicorp_vault_tenant_expansion_queries.get_review(
                canary_tenant_id=self.canary.id,
                target_tenant_ids=str(self.target.id),
                probe_reference="owners/hashicorp-expansion/blocked",
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
                expansion_window_confirmed=True,
                per_tenant_evidence_required=True,
                support_standby_confirmed=True,
                rollback_window_confirmed=True,
                max_parallel_tenants=2,
            )

        self.assertFalse(review["ready"])
        self.assertIn(f"target:{self.target.id}:tenant-inactive", review["blockers"])
        self.assertIn("expansion:single_tenant_window:missing", review["blockers"])

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
    def test_command_outputs_expansion_plan_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-expansion/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_tenant_expansion_review",
                "--canary-tenant-id",
                str(self.canary.id),
                "--target-tenant-ids",
                str(self.target.id),
                "--probe-reference",
                "owners/hashicorp-expansion/command",
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
                "--expansion-window-confirmed",
                "--per-tenant-evidence-required",
                "--support-standby-confirmed",
                "--rollback-window-confirmed",
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("target_tenant tenant_id=", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertIn("evidence_requirement=", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-expansion/command", output.getvalue())
        self.assertNotIn("vault-token", output.getvalue())

    def test_command_can_fail_when_review_is_blocked(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_hashicorp_vault_tenant_expansion_review",
                "--canary-tenant-id",
                str(self.canary.id),
                "--target-tenant-ids",
                "",
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
