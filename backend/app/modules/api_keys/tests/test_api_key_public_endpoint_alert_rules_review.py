from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_alert_rules_review_queries import (
    api_key_public_endpoint_alert_rules_review_queries,
)


class ApiKeyPublicEndpointAlertRulesReviewTests(TestCase):
    def test_review_ready_recommends_minimal_alert_rules(self):
        review = api_key_public_endpoint_alert_rules_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-alert-rules-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("HubxApiKeyPublicAuthFailuresHigh", review["rules"])
        self.assertIn("HubxApiKeyPublicRateLimitedHigh", review["rules"])
        self.assertIn("HubxApiKeyPublicEndpointDisabled", review["rules"])
        self.assertIn("API Key Public Endpoint Alert Rules Execution", review["next_tracks"])

    def test_review_blocks_without_prerequisites(self):
        flags = self._ready_flags()
        flags["metrics_endpoint_available"] = False
        flags["dashboard_available"] = False

        review = api_key_public_endpoint_alert_rules_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-alert-rules:metrics_endpoint_available:missing", review["blockers"])
        self.assertIn("public-endpoint-alert-rules:dashboard_available:missing", review["blockers"])

    def test_review_blocks_without_alert_coverage(self):
        flags = self._ready_flags()
        flags["auth_failure_alert_required"] = False
        flags["rate_limit_alert_required"] = False
        flags["endpoint_disabled_alert_required"] = False

        review = api_key_public_endpoint_alert_rules_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-alert-rules:auth_failure_alert_required:missing", review["blockers"])
        self.assertIn("public-endpoint-alert-rules:rate_limit_alert_required:missing", review["blockers"])
        self.assertIn("public-endpoint-alert-rules:endpoint_disabled_alert_required:missing", review["blockers"])

    def test_review_blocks_without_safe_labels_and_runbook(self):
        flags = self._ready_flags()
        flags["tenant_endpoint_labels_required"] = False
        flags["no_sensitive_labels_required"] = False
        flags["runbook_annotations_required"] = False

        review = api_key_public_endpoint_alert_rules_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-alert-rules:tenant_endpoint_labels_required:missing", review["blockers"])
        self.assertIn("public-endpoint-alert-rules:no_sensitive_labels_required:missing", review["blockers"])
        self.assertIn("public-endpoint-alert-rules:runbook_annotations_required:missing", review["blockers"])

    def test_command_outputs_alert_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_alert_rules_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("rule=HubxApiKeyPublicAuthFailuresHigh", value)
        self.assertIn("decision key=severity status=warning-first", value)
        self.assertIn("requirement key=endpoint-disabled", value)
        self.assertIn("out_of_scope=não criar YAML de alert rules nesta review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_alert_rules_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "metrics_endpoint_available": True,
            "dashboard_available": True,
            "auth_failure_alert_required": True,
            "rate_limit_alert_required": True,
            "endpoint_disabled_alert_required": True,
            "tenant_endpoint_labels_required": True,
            "low_cardinality_required": True,
            "runbook_annotations_required": True,
            "no_sensitive_labels_required": True,
            "warning_first_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--metrics-endpoint-available",
            "--dashboard-available",
            "--auth-failure-alert-required",
            "--rate-limit-alert-required",
            "--endpoint-disabled-alert-required",
            "--tenant-endpoint-labels-required",
            "--low-cardinality-required",
            "--runbook-annotations-required",
            "--no-sensitive-labels-required",
            "--warning-first-required",
        )
