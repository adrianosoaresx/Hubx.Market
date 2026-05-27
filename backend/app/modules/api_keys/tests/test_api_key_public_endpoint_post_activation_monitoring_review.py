from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_post_activation_monitoring_review_queries import (
    api_key_public_endpoint_post_activation_monitoring_review_queries,
)


class ApiKeyPublicEndpointPostActivationMonitoringReviewTests(TestCase):
    def test_review_ready_when_all_monitoring_signals_are_acceptable(self):
        review = api_key_public_endpoint_post_activation_monitoring_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-post-activation-monitoring-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("API Key Public Endpoint Expansion Review", review["next_tracks"])
        self.assertIn("validar `hubx_api_key_public_endpoint_enabled` estável por endpoint", review["monitoring_checks"])

    def test_review_blocks_without_activation_or_window(self):
        flags = self._ready_flags()
        flags["activation_evidence_ready"] = False
        flags["monitoring_window_observed"] = False

        review = api_key_public_endpoint_post_activation_monitoring_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-post-activation-monitoring:activation_evidence_ready:missing", review["blockers"])
        self.assertIn("public-endpoint-post-activation-monitoring:monitoring_window_observed:missing", review["blockers"])

    def test_review_blocks_without_traffic_health_or_rollback_decision(self):
        flags = self._ready_flags()
        flags["auth_failure_rate_acceptable"] = False
        flags["rate_limit_rate_acceptable"] = False
        flags["rollback_not_required"] = False

        review = api_key_public_endpoint_post_activation_monitoring_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-post-activation-monitoring:auth_failure_rate_acceptable:missing", review["blockers"])
        self.assertIn("public-endpoint-post-activation-monitoring:rate_limit_rate_acceptable:missing", review["blockers"])
        self.assertIn("public-endpoint-post-activation-monitoring:rollback_not_required:missing", review["blockers"])

    def test_command_outputs_monitoring_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_post_activation_monitoring_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("decision key=traffic-health status=acceptable", value)
        self.assertIn("monitoring_check=validar `hubx_api_key_public_endpoint_enabled`", value)
        self.assertIn("next_track=API Key Public Endpoint Expansion Review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_post_activation_monitoring_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "activation_evidence_ready": True,
            "monitoring_window_observed": True,
            "dashboard_reviewed": True,
            "auth_failure_rate_acceptable": True,
            "rate_limit_rate_acceptable": True,
            "endpoint_enabled_stable": True,
            "alert_noise_acceptable": True,
            "threshold_tuning_needed_logged": True,
            "rollback_not_required": True,
            "expansion_decision_deferred": True,
            "no_sensitive_data_observed": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--activation-evidence-ready",
            "--monitoring-window-observed",
            "--dashboard-reviewed",
            "--auth-failure-rate-acceptable",
            "--rate-limit-rate-acceptable",
            "--endpoint-enabled-stable",
            "--alert-noise-acceptable",
            "--threshold-tuning-needed-logged",
            "--rollback-not-required",
            "--expansion-decision-deferred",
            "--no-sensitive-data-observed",
        )
