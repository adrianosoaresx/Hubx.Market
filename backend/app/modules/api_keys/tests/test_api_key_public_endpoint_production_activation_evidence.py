from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_production_activation_evidence_queries import (
    api_key_public_endpoint_production_activation_evidence_queries,
)


class ApiKeyPublicEndpointProductionActivationEvidenceTests(TestCase):
    def test_evidence_ready_when_all_activation_signals_are_present(self):
        evidence = api_key_public_endpoint_production_activation_evidence_queries.get_evidence(
            **self._ready_flags()
        )

        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["result"], "api-key-public-endpoint-production-activation-evidence-ready")
        self.assertEqual(evidence["blockers"], ())
        self.assertEqual(evidence["environment"], "production")
        self.assertEqual(evidence["evidence_reference"], "ops-evidence/api-keys-public/2026-05-18")
        self.assertIn("API Key Public Endpoint Post-Activation Monitoring Review", evidence["next_tracks"])

    def test_evidence_blocks_without_production_environment_or_rollout(self):
        flags = self._ready_flags()
        flags["environment"] = "staging"
        flags["rollout_review_ready"] = False

        evidence = api_key_public_endpoint_production_activation_evidence_queries.get_evidence(**flags)

        self.assertFalse(evidence["ready"])
        self.assertIn("public-endpoint-production-activation-evidence:environment_production:missing", evidence["blockers"])
        self.assertIn("public-endpoint-production-activation-evidence:rollout_review_ready:missing", evidence["blockers"])

    def test_evidence_blocks_and_drops_sensitive_reference(self):
        flags = self._ready_flags()
        flags["evidence_reference"] = "ops/token=leaked"

        evidence = api_key_public_endpoint_production_activation_evidence_queries.get_evidence(**flags)

        self.assertFalse(evidence["ready"])
        self.assertEqual(evidence["evidence_reference"], "")
        self.assertIn("public-endpoint-production-activation-evidence:evidence_reference_present:missing", evidence["blockers"])

    def test_command_outputs_sanitized_evidence(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_production_activation_evidence",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("decision key=sensitive-data status=guarded", value)
        self.assertIn("captured_evidence=metrics_endpoint_reachable=True", value)
        self.assertIn("next_track=API Key Public Endpoint Post-Activation Monitoring Review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_production_activation_evidence", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, object]:
        return {
            "environment": "production",
            "evidence_reference": "ops-evidence/api-keys-public/2026-05-18",
            "rollout_review_ready": True,
            "token_redacted": True,
            "metrics_endpoint_reachable": True,
            "metrics_payload_valid": True,
            "prometheus_scrape_active": True,
            "dashboard_imported": True,
            "alert_rules_loaded": True,
            "endpoint_enabled_metric_present": True,
            "request_metric_present": True,
            "auth_failure_metric_present": True,
            "rate_limit_metric_present": True,
            "rollback_rehearsed": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--environment=production",
            "--evidence-reference=ops-evidence/api-keys-public/2026-05-18",
            "--rollout-review-ready",
            "--token-redacted",
            "--metrics-endpoint-reachable",
            "--metrics-payload-valid",
            "--prometheus-scrape-active",
            "--dashboard-imported",
            "--alert-rules-loaded",
            "--endpoint-enabled-metric-present",
            "--request-metric-present",
            "--auth-failure-metric-present",
            "--rate-limit-metric-present",
            "--rollback-rehearsed",
        )
