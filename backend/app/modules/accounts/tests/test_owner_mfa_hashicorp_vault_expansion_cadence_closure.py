from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_expansion_cadence_closure_queries import (
    owner_mfa_hashicorp_vault_expansion_cadence_closure_queries,
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


class OwnerMfaHashicorpVaultExpansionCadenceClosureTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.canary = Tenant.objects.create(name="MFA Vault Cadence Canary", slug="mfa-vault-cadence-canary", subdomain="mfa-vault-cadence-canary")
        self.current = Tenant.objects.create(name="MFA Vault Cadence Current", slug="mfa-vault-cadence-current", subdomain="mfa-vault-cadence-current")
        self.next_tenant = Tenant.objects.create(name="MFA Vault Cadence Next", slug="mfa-vault-cadence-next", subdomain="mfa-vault-cadence-next")
        self.owner = OwnerUser.objects.create(tenant=self.canary, email="owner.mfa.vault.cadence@hubx.market", role="owner")

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
    def test_closure_ready_when_cadence_ready_and_closure_signals_are_ready(self):
        self._factor(secret_reference="ref:owners/hashicorp-cadence/ready")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            closure = owner_mfa_hashicorp_vault_expansion_cadence_closure_queries.get_closure(
                **self._ready_kwargs(probe_reference="owners/hashicorp-cadence/ready")
            )

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["status"], "ready")
        self.assertEqual(closure["cadence_status"], "ready")
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
    def test_closure_ready_when_cadence_is_paused(self):
        self._factor(secret_reference="ref:owners/hashicorp-cadence/paused")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        kwargs = self._ready_kwargs(probe_reference="owners/hashicorp-cadence/paused")
        kwargs["next_target_tenant_ids"] = ""
        kwargs["stop_after_current_target"] = True

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            closure = owner_mfa_hashicorp_vault_expansion_cadence_closure_queries.get_closure(**kwargs)

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["status"], "ready")
        self.assertEqual(closure["cadence_status"], "paused")
        self.assertIn("Owner MFA Audit Evidence Export Review", closure["next_tracks"])

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
    def test_closure_blocks_when_archive_is_missing(self):
        self._factor(secret_reference="ref:owners/hashicorp-cadence/blocked")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        kwargs = self._ready_kwargs(probe_reference="owners/hashicorp-cadence/blocked")
        kwargs["evidence_archive_complete"] = False

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            closure = owner_mfa_hashicorp_vault_expansion_cadence_closure_queries.get_closure(**kwargs)

        self.assertFalse(closure["ready"])
        self.assertIn("closure:evidence_archive_complete:missing", closure["blockers"])

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
        self._factor(secret_reference="ref:owners/hashicorp-cadence/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_expansion_cadence_closure",
                "--canary-tenant-id",
                str(self.canary.id),
                "--current-target-tenant-id",
                str(self.current.id),
                "--next-target-tenant-ids",
                str(self.next_tenant.id),
                "--probe-reference",
                "owners/hashicorp-cadence/command",
                "--canary-owner-email",
                self.owner.email,
                *self._ready_flags(),
                stdout=output,
            )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("cadence_status=ready", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-cadence/command", output.getvalue())
        self.assertNotIn("vault-token", output.getvalue())

    def test_command_can_fail_when_closure_is_blocked(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_hashicorp_vault_expansion_cadence_closure",
                "--canary-tenant-id",
                str(self.canary.id),
                "--current-target-tenant-id",
                str(self.current.id),
                "--canary-owner-email",
                self.owner.email,
                "--fail-on-blockers",
                stdout=StringIO(),
            )

    def _ready_kwargs(self, *, probe_reference: str) -> dict[str, object]:
        return {
            "canary_tenant_id": self.canary.id,
            "current_target_tenant_id": self.current.id,
            "next_target_tenant_ids": str(self.next_tenant.id),
            "probe_reference": probe_reference,
            "canary_owner_email": self.owner.email,
            "canary_monitoring_window_elapsed": True,
            "canary_provider_health_stable": True,
            "canary_owner_login_error_spike_absent": True,
            "canary_support_incidents_absent": True,
            "canary_rollback_signal_absent": True,
            "canary_evidence_redacted": True,
            "rollback_runbook_confirmed": True,
            "residual_risks_accepted": True,
            "tenant_expansion_plan_documented": True,
            "expansion_window_confirmed": True,
            "per_tenant_evidence_required": True,
            "support_standby_confirmed": True,
            "rollback_window_confirmed": True,
            "target_flags_enabled": True,
            "target_activation_evidence_captured": True,
            "target_monitoring_scheduled": True,
            "target_owner_login_challenge_passed": True,
            "target_provider_health_ready": True,
            "rollback_not_required": True,
            "expansion_evidence_redacted": True,
            "target_monitoring_window_elapsed": True,
            "target_provider_health_stable": True,
            "target_owner_login_error_spike_absent": True,
            "target_support_incidents_absent": True,
            "target_rollback_signal_absent": True,
            "evidence_redacted": True,
            "next_window_confirmed": True,
            "operator_capacity_confirmed": True,
            "previous_target_evidence_archived": True,
            "stop_after_current_target": False,
            "max_parallel_tenants": 1,
            "cadence_decision_recorded": True,
            "evidence_archive_complete": True,
            "residual_risks_reviewed": True,
            "rotation_runbook_queued": True,
            "audit_evidence_ready": True,
        }

    def _ready_flags(self) -> tuple[str, ...]:
        return (
            "--canary-monitoring-window-elapsed",
            "--canary-provider-health-stable",
            "--canary-owner-login-error-spike-absent",
            "--canary-support-incidents-absent",
            "--canary-rollback-signal-absent",
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
            "--expansion-evidence-redacted",
            "--target-monitoring-window-elapsed",
            "--target-provider-health-stable",
            "--target-owner-login-error-spike-absent",
            "--target-support-incidents-absent",
            "--target-rollback-signal-absent",
            "--evidence-redacted",
            "--next-window-confirmed",
            "--operator-capacity-confirmed",
            "--previous-target-evidence-archived",
            "--cadence-decision-recorded",
            "--evidence-archive-complete",
            "--residual-risks-reviewed",
            "--rotation-runbook-queued",
            "--audit-evidence-ready",
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
