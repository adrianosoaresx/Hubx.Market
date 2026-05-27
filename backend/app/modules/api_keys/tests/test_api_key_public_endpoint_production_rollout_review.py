from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_production_rollout_review_queries import (
    api_key_public_endpoint_production_rollout_review_queries,
)


class ApiKeyPublicEndpointProductionRolloutReviewTests(TestCase):
    def test_review_ready_when_all_rollout_controls_are_present(self):
        review = api_key_public_endpoint_production_rollout_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-production-rollout-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("API Key Public Endpoint Production Activation Evidence", review["next_tracks"])
        self.assertIn("carregar scrape no Prometheus", review["runbook_steps"])
        self.assertIn("rotacionar `API_KEYS_OBSERVABILITY_TOKEN` se houver suspeita de exposição", review["rollback_steps"])

    def test_review_blocks_without_observability_or_token(self):
        flags = self._ready_flags()
        flags["observability_closure_ready"] = False
        flags["production_token_configured"] = False

        review = api_key_public_endpoint_production_rollout_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-production-rollout:observability_closure_ready:missing", review["blockers"])
        self.assertIn("public-endpoint-production-rollout:production_token_configured:missing", review["blockers"])

    def test_review_blocks_without_smoke_evidence_and_rollback(self):
        flags = self._ready_flags()
        flags["smoke_metrics_planned"] = False
        flags["evidence_capture_required"] = False
        flags["rollback_plan_available"] = False

        review = api_key_public_endpoint_production_rollout_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-production-rollout:smoke_metrics_planned:missing", review["blockers"])
        self.assertIn("public-endpoint-production-rollout:evidence_capture_required:missing", review["blockers"])
        self.assertIn("public-endpoint-production-rollout:rollback_plan_available:missing", review["blockers"])

    def test_command_outputs_rollout_plan_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_production_rollout_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("decision key=token status=required", value)
        self.assertIn("requirement key=scrape", value)
        self.assertIn("runbook_step=carregar scrape no Prometheus", value)
        self.assertIn("rollback_step=rotacionar `API_KEYS_OBSERVABILITY_TOKEN`", value)
        self.assertIn("out_of_scope=não ativar produção nesta review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_production_rollout_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "observability_closure_ready": True,
            "production_token_configured": True,
            "prometheus_scrape_planned": True,
            "dashboard_import_planned": True,
            "alert_rules_load_planned": True,
            "smoke_metrics_planned": True,
            "rollback_plan_available": True,
            "evidence_capture_required": True,
            "owner_approval_required": True,
            "no_secret_exposure_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--observability-closure-ready",
            "--production-token-configured",
            "--prometheus-scrape-planned",
            "--dashboard-import-planned",
            "--alert-rules-load-planned",
            "--smoke-metrics-planned",
            "--rollback-plan-available",
            "--evidence-capture-required",
            "--owner-approval-required",
            "--no-secret-exposure-required",
        )
