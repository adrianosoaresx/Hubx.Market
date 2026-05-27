from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_product_detail_observability_review_queries import (
    api_key_public_product_detail_observability_review_queries,
)


class ApiKeyPublicProductDetailObservabilityReviewTests(TestCase):
    def test_review_ready_when_existing_observability_covers_detail(self):
        review = api_key_public_product_detail_observability_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-product-detail-observability-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["endpoint"], "catalog.products.detail")
        self.assertIn("API Key Public Endpoint Expansion Closure Review", review["next_tracks"])

    def test_review_blocks_without_metrics_and_gauge(self):
        flags = self._ready_flags()
        flags["metrics_endpoint_label_present"] = False
        flags["enabled_gauge_present"] = False

        review = api_key_public_product_detail_observability_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-product-detail-observability:metrics_endpoint_label_present:missing", review["blockers"])
        self.assertIn("public-product-detail-observability:enabled_gauge_present:missing", review["blockers"])

    def test_review_blocks_without_dashboard_or_alert_coverage(self):
        flags = self._ready_flags()
        flags["dashboard_endpoint_filter_covers_detail"] = False
        flags["alert_rules_endpoint_label_covers_detail"] = False

        review = api_key_public_product_detail_observability_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-product-detail-observability:dashboard_endpoint_filter_covers_detail:missing", review["blockers"])
        self.assertIn("public-product-detail-observability:alert_rules_endpoint_label_covers_detail:missing", review["blockers"])

    def test_command_outputs_observability_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_product_detail_observability_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("endpoint=catalog.products.detail", value)
        self.assertIn("decision key=artifacts status=no-new-artifact", value)
        self.assertIn("next_track=API Key Public Endpoint Expansion Closure Review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_product_detail_observability_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "detail_endpoint_executed": True,
            "metrics_endpoint_label_present": True,
            "enabled_gauge_present": True,
            "dashboard_endpoint_filter_covers_detail": True,
            "alert_rules_endpoint_label_covers_detail": True,
            "rate_limit_metrics_reused": True,
            "auth_failure_metrics_reused": True,
            "no_new_dashboard_required": True,
            "no_new_alert_rules_required": True,
            "no_sensitive_labels_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--detail-endpoint-executed",
            "--metrics-endpoint-label-present",
            "--enabled-gauge-present",
            "--dashboard-endpoint-filter-covers-detail",
            "--alert-rules-endpoint-label-covers-detail",
            "--rate-limit-metrics-reused",
            "--auth-failure-metrics-reused",
            "--no-new-dashboard-required",
            "--no-new-alert-rules-required",
            "--no-sensitive-labels-required",
        )
