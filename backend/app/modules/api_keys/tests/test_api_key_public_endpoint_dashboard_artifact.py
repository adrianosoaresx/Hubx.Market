from __future__ import annotations

import json
from pathlib import Path

from django.test import SimpleTestCase


class ApiKeyPublicEndpointDashboardArtifactTests(SimpleTestCase):
    dashboard_path = (
        Path(__file__).resolve().parents[5]
        / "infra"
        / "observability"
        / "grafana"
        / "api-key-public-endpoints-dashboard.json"
    )

    def test_dashboard_json_contains_required_public_endpoint_panels(self):
        payload = json.loads(self.dashboard_path.read_text(encoding="utf-8"))

        self.assertEqual(payload["title"], "Hubx API Key Public Endpoints")
        self.assertEqual(payload["uid"], "hubx-api-key-public-endpoints")
        self.assertEqual(payload["templating"]["list"][0]["name"], "DS_PROMETHEUS")

        panel_titles = {panel["title"] for panel in payload["panels"]}
        self.assertIn("Public request rate by tenant / endpoint / result", panel_titles)
        self.assertIn("Authentication failures by tenant / endpoint / reason", panel_titles)
        self.assertIn("Rate limited requests by tenant / endpoint / prefix", panel_titles)
        self.assertIn("Public endpoint enabled", panel_titles)
        self.assertIn("Top tenants by public request volume (1h)", panel_titles)

        expressions = "\n".join(
            target["expr"]
            for panel in payload["panels"]
            for target in panel.get("targets", ())
        )
        self.assertIn("hubx_api_key_public_request_total", expressions)
        self.assertIn("hubx_api_key_auth_failure_total", expressions)
        self.assertIn("hubx_api_key_rate_limited_total", expressions)
        self.assertIn("hubx_api_key_public_endpoint_enabled", expressions)
        self.assertIn("tenant_id", expressions)
        self.assertIn("endpoint", expressions)

    def test_dashboard_artifact_does_not_expose_sensitive_api_key_material(self):
        value = self.dashboard_path.read_text(encoding="utf-8")

        self.assertNotIn("secret", value.lower())
        self.assertNotIn("key_hash", value)
        self.assertNotIn("authorization", value.lower())
        self.assertNotIn("X-Hubx-Api-Key", value)
