from __future__ import annotations

from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.application.owner_mfa_provider_health_metrics_queries import owner_mfa_provider_health_metrics_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaProviderHealthMetricsTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Provider Metrics", slug="mfa-provider-metrics", subdomain="mfa-provider-metrics")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.provider.metrics@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_exports_provider_health_metrics_without_secret_values(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            payload = owner_mfa_provider_health_metrics_queries.export_prometheus_metrics()

        self.assertIn("hubx_accounts_owner_mfa_provider_health_status", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",provider="env",status="HEALTHY"', payload)
        self.assertIn('state="resolved"', payload)
        self.assertNotIn(self.secret, payload)

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_exports_unresolved_reference_signal(self):
        self._factor(secret_reference="ref:owners/1/totp")

        payload = owner_mfa_provider_health_metrics_queries.export_prometheus_metrics()

        self.assertIn('status="CRITICAL"', payload)
        self.assertIn('state="unresolved"} 1', payload)
        self.assertIn('signal="external-reference-unresolved"', payload)

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="accounts-token", OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_metrics_view_returns_prometheus_payload_with_token(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            response = self.client.get(
                reverse("accounts:owner-mfa-provider-health-metrics"),
                HTTP_X_HUBX_OBSERVABILITY_TOKEN="accounts-token",
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8")
        self.assertContains(response, "hubx_accounts_owner_mfa_provider_health_status")

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="accounts-token")
    def test_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("accounts:owner-mfa-provider-health-metrics"))

        self.assertEqual(response.status_code, 403)

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="")
    def test_metrics_view_is_not_found_without_configured_token(self):
        response = self.client.get(reverse("accounts:owner-mfa-provider-health-metrics"))

        self.assertEqual(response.status_code, 404)

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
