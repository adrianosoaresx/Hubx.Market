from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_observability_review_queries import (
    api_key_public_endpoint_observability_review_queries,
)


class ApiKeyPublicEndpointObservabilityReviewTests(TestCase):
    def test_review_ready_recommends_minimal_metrics(self):
        review = api_key_public_endpoint_observability_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-observability-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("hubx_api_key_public_request_total", review["recommended_metrics"])
        self.assertIn("hubx_api_key_auth_failure_total", review["recommended_metrics"])
        self.assertIn("hubx_api_key_rate_limited_total", review["recommended_metrics"])
        self.assertIn("API Key Public Endpoint Metrics Execution", review["next_tracks"])

    def test_review_blocks_without_auth_and_rate_limit_events(self):
        flags = self._ready_flags()
        flags["auth_events_available"] = False
        flags["rate_limit_events_available"] = False

        review = api_key_public_endpoint_observability_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-observability:auth_events_available:missing", review["blockers"])
        self.assertIn("public-endpoint-observability:rate_limit_events_available:missing", review["blockers"])

    def test_review_blocks_without_safe_label_contract(self):
        flags = self._ready_flags()
        flags["tenant_labels_required"] = False
        flags["no_secret_material_required"] = False

        review = api_key_public_endpoint_observability_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-observability:tenant_labels_required:missing", review["blockers"])
        self.assertIn("public-endpoint-observability:no_secret_material_required:missing", review["blockers"])

    def test_review_requires_alerts_and_dashboard(self):
        flags = self._ready_flags()
        flags["alert_rules_required"] = False
        flags["dashboard_required"] = False

        review = api_key_public_endpoint_observability_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-observability:alert_rules_required:missing", review["blockers"])
        self.assertIn("public-endpoint-observability:dashboard_required:missing", review["blockers"])

    def test_command_outputs_metrics_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_observability_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommended_metric=hubx_api_key_public_request_total", value)
        self.assertIn("decision key=sensitive-data", value)
        self.assertIn("requirement key=alerts", value)
        self.assertIn("out_of_scope=não implementar métricas nesta review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_observability_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "public_endpoint_active": True,
            "auth_events_available": True,
            "rate_limit_events_available": True,
            "prometheus_metrics_required": True,
            "endpoint_labels_required": True,
            "tenant_labels_required": True,
            "key_prefix_labels_allowed": True,
            "no_secret_material_required": True,
            "alert_rules_required": True,
            "dashboard_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--public-endpoint-active",
            "--auth-events-available",
            "--rate-limit-events-available",
            "--prometheus-metrics-required",
            "--endpoint-labels-required",
            "--tenant-labels-required",
            "--key-prefix-labels-allowed",
            "--no-secret-material-required",
            "--alert-rules-required",
            "--dashboard-required",
        )
