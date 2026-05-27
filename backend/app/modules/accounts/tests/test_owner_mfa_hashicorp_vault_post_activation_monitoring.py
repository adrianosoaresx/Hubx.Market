from __future__ import annotations

from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_hashicorp_vault_post_activation_monitoring_queries import (
    owner_mfa_hashicorp_vault_post_activation_monitoring_queries,
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


class OwnerMfaHashicorpVaultPostActivationMonitoringTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Vault Monitor", slug="mfa-vault-monitor", subdomain="mfa-vault-monitor")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.vault.monitor@hubx.market", role="owner")

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
    def test_monitoring_healthy_when_all_signals_are_clean(self):
        self._factor(secret_reference="ref:owners/hashicorp-monitor/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_hashicorp_vault_post_activation_monitoring_queries.get_review(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-monitor/evidence",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=True,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=True,
                evidence_redacted=True,
            )

        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["classification"], "HEALTHY")
        self.assertIn("Owner MFA Vault/KMS Production Closure Review", result["next_tracks"])

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
    def test_monitoring_watch_when_window_is_not_elapsed(self):
        self._factor(secret_reference="ref:owners/hashicorp-monitor/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_hashicorp_vault_post_activation_monitoring_queries.get_review(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-monitor/evidence",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=False,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=True,
                evidence_redacted=True,
            )

        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "watch")
        self.assertIn("monitoring-window-not-elapsed", result["watch_items"])

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
    def test_monitoring_rollback_when_signal_is_present(self):
        self._factor(secret_reference="ref:owners/hashicorp-monitor/evidence")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            result = owner_mfa_hashicorp_vault_post_activation_monitoring_queries.get_review(
                tenant_id=self.tenant.id,
                probe_reference="owners/hashicorp-monitor/evidence",
                canary_owner_email=self.owner.email,
                monitoring_window_elapsed=True,
                provider_health_stable=True,
                owner_login_error_spike_absent=True,
                support_incidents_absent=True,
                rollback_signal_absent=False,
                evidence_redacted=True,
            )

        self.assertFalse(result["ready"])
        self.assertEqual(result["status"], "rollback")
        self.assertIn("rollback-signal-present", result["blockers"])

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
        self._factor(secret_reference="ref:owners/hashicorp-monitor/command")
        hvac = _FakeVaultModule(payload={"data": {"data": {"totp_secret": self.secret}}})
        output = StringIO()

        with patch("app.modules.accounts.infrastructure.owner_mfa_secret_providers.importlib.import_module", return_value=hvac):
            call_command(
                "owner_mfa_hashicorp_vault_post_activation_monitoring",
                "--tenant-id",
                str(self.tenant.id),
                "--probe-reference",
                "owners/hashicorp-monitor/command",
                "--canary-owner-email",
                self.owner.email,
                "--monitoring-window-elapsed",
                "--provider-health-stable",
                "--owner-login-error-spike-absent",
                "--support-incidents-absent",
                "--rollback-signal-absent",
                "--evidence-redacted",
                stdout=output,
            )

        self.assertIn("[HEALTHY]", output.getvalue())
        self.assertIn("classification=HEALTHY", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertNotIn(self.secret, output.getvalue())
        self.assertNotIn("owners/hashicorp-monitor/command", output.getvalue())
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
