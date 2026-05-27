from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries import (
    owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries,
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


class OwnerMfaHashicorpVaultTargetPostExpansionMonitoringTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.canary = Tenant.objects.create(
            name="MFA Vault Target Monitor Canary",
            slug="mfa-vault-target-monitor-canary",
            subdomain="mfa-vault-target-monitor-canary",
        )
        self.target = Tenant.objects.create(
            name="MFA Vault Target Monitor",
            slug="mfa-vault-target-monitor",
            subdomain="mfa-vault-target-monitor",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.canary,
            email="owner.mfa.vault.target.monitor@hubx.market",
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
    def test_monitoring_healthy_when_target_signals_are_clean(self):
        self._factor(secret_reference="ref:owners/hashicorp-target-monitor/healthy")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            review = owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries.get_review(
                **self._ready_kwargs(probe_reference="owners/hashicorp-target-monitor/healthy")
            )

        self.assertTrue(review["ready"])
        self.assertEqual(review["status"], "healthy")
        self.assertEqual(review["classification"], "HEALTHY")
        self.assertIn("Owner MFA Hashicorp Vault Next Tenant Expansion Review", review["next_tracks"])

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
    def test_monitoring_watch_when_target_window_is_not_elapsed(self):
        self._factor(secret_reference="ref:owners/hashicorp-target-monitor/watch")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        kwargs = self._ready_kwargs(probe_reference="owners/hashicorp-target-monitor/watch")
        kwargs["target_monitoring_window_elapsed"] = False

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            review = owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries.get_review(**kwargs)

        self.assertFalse(review["ready"])
        self.assertEqual(review["status"], "watch")
        self.assertIn("target-monitoring-window-not-elapsed", review["watch_items"])

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
    def test_monitoring_rollback_when_target_signal_is_present(self):
        self._factor(secret_reference="ref:owners/hashicorp-target-monitor/rollback")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        kwargs = self._ready_kwargs(probe_reference="owners/hashicorp-target-monitor/rollback")
        kwargs["target_rollback_signal_absent"] = False

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            review = owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries.get_review(**kwargs)

        self.assertFalse(review["ready"])
        self.assertEqual(review["status"], "rollback")
        self.assertIn("target-rollback-signal-present", review["blockers"])

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
    def test_command_outputs_monitoring_without_secret_or_path(self):
        self._factor(secret_reference="ref:owners/hashicorp-target-monitor/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_target_post_expansion_monitoring",
                "--canary-tenant-id",
                str(self.canary.id),
                "--target-tenant-id",
                str(self.target.id),
                "--probe-reference",
                "owners/hashicorp-target-monitor/command",
                "--canary-owner-email",
                self.owner.email,
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
                stdout=output,
            )

        self.assertIn("[HEALTHY]", output.getvalue())
        self.assertIn("classification=HEALTHY", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-target-monitor/command", output.getvalue())
        self.assertNotIn("vault-token", output.getvalue())

    def _ready_kwargs(self, *, probe_reference: str) -> dict[str, object]:
        return {
            "canary_tenant_id": self.canary.id,
            "target_tenant_id": self.target.id,
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
        }

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
