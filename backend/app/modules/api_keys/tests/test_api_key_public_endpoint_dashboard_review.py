from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_dashboard_review_queries import (
    api_key_public_endpoint_dashboard_review_queries,
)


class ApiKeyPublicEndpointDashboardReviewTests(TestCase):
    def test_review_ready_recommends_minimal_dashboard(self):
        review = api_key_public_endpoint_dashboard_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-dashboard-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["dashboard"]["owner"], "api_keys")
        self.assertIn("public_request_rate_by_tenant_endpoint_result", review["panels"])
        self.assertIn("auth_failure_rate_by_tenant_endpoint_reason", review["panels"])
        self.assertIn("rate_limited_rate_by_tenant_endpoint_prefix", review["panels"])
        self.assertIn("public_endpoint_enabled_state", review["panels"])
        self.assertIn("API Key Public Endpoint Dashboard Execution", review["next_tracks"])

    def test_review_blocks_without_core_panels(self):
        flags = self._ready_flags()
        flags["requests_panel_required"] = False
        flags["auth_failure_panel_required"] = False
        flags["rate_limit_panel_required"] = False

        review = api_key_public_endpoint_dashboard_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-dashboard:requests_panel_required:missing", review["blockers"])
        self.assertIn("public-endpoint-dashboard:auth_failure_panel_required:missing", review["blockers"])
        self.assertIn("public-endpoint-dashboard:rate_limit_panel_required:missing", review["blockers"])

    def test_review_blocks_without_safe_label_contract(self):
        flags = self._ready_flags()
        flags["tenant_endpoint_filters_required"] = False
        flags["low_cardinality_required"] = False
        flags["no_sensitive_labels_required"] = False

        review = api_key_public_endpoint_dashboard_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-dashboard:tenant_endpoint_filters_required:missing", review["blockers"])
        self.assertIn("public-endpoint-dashboard:low_cardinality_required:missing", review["blockers"])
        self.assertIn("public-endpoint-dashboard:no_sensitive_labels_required:missing", review["blockers"])

    def test_review_keeps_alert_rules_as_separate_plan(self):
        flags = self._ready_flags()
        flags["alert_rules_plan_required"] = False

        review = api_key_public_endpoint_dashboard_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-dashboard:alert_rules_plan_required:missing", review["blockers"])
        self.assertIn("API Key Public Endpoint Dashboard Follow-Up", review["next_tracks"])

    def test_command_outputs_dashboard_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_dashboard_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("dashboard title=Hubx API Key Public Endpoints", value)
        self.assertIn("panel=public_request_rate_by_tenant_endpoint_result", value)
        self.assertIn("decision key=security", value)
        self.assertIn("requirement key=rate-limit", value)
        self.assertIn("out_of_scope=não criar dashboard JSON nesta review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_dashboard_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "metrics_endpoint_available": True,
            "observability_token_required": True,
            "requests_panel_required": True,
            "auth_failure_panel_required": True,
            "rate_limit_panel_required": True,
            "endpoint_enabled_panel_required": True,
            "tenant_endpoint_filters_required": True,
            "low_cardinality_required": True,
            "no_sensitive_labels_required": True,
            "alert_rules_plan_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--metrics-endpoint-available",
            "--observability-token-required",
            "--requests-panel-required",
            "--auth-failure-panel-required",
            "--rate-limit-panel-required",
            "--endpoint-enabled-panel-required",
            "--tenant-endpoint-filters-required",
            "--low-cardinality-required",
            "--no-sensitive-labels-required",
            "--alert-rules-plan-required",
        )
