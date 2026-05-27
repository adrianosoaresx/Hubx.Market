from __future__ import annotations

from pathlib import Path

from django.test import SimpleTestCase


class ApiKeyPublicEndpointAlertRulesArtifactTests(SimpleTestCase):
    rules_path = (
        Path(__file__).resolve().parents[5]
        / "infra"
        / "observability"
        / "prometheus"
        / "api-keys-alert-rules.yml"
    )

    def test_alert_rules_artifact_contains_required_rules_and_metrics(self):
        value = self.rules_path.read_text(encoding="utf-8")

        self.assertIn("groups:", value)
        self.assertIn("name: hubx-api-keys-public-endpoints", value)
        self.assertIn("alert: HubxApiKeyPublicAuthFailuresHigh", value)
        self.assertIn("alert: HubxApiKeyPublicRateLimitedHigh", value)
        self.assertIn("alert: HubxApiKeyPublicEndpointDisabled", value)
        self.assertIn("hubx_api_key_auth_failure_total", value)
        self.assertIn("hubx_api_key_rate_limited_total", value)
        self.assertIn("hubx_api_key_public_endpoint_enabled", value)
        self.assertIn("tenant_id", value)
        self.assertIn("endpoint", value)
        self.assertIn("severity: warning", value)
        self.assertIn("domain: api_keys", value)

    def test_alert_rules_artifact_does_not_expose_sensitive_api_key_material(self):
        value = self.rules_path.read_text(encoding="utf-8")

        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)
        self.assertNotIn("api_key=", value)
