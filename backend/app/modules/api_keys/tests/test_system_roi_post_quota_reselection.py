from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.system_roi_post_quota_reselection_queries import (
    system_roi_post_quota_reselection_queries,
)


class SystemRoiPostQuotaReselectionTests(TestCase):
    def test_reselection_recommends_payments_when_provider_and_finance_are_blockers(self):
        review = system_roi_post_quota_reselection_queries.get_review(
            **self._quota_ready_flags(),
            payments_provider_production_blocker=True,
            payments_refund_reconciliation_blocker=True,
            shipping_quote_conversion_blocker=True,
            shipping_carrier_contract_ready=True,
            cross_module_runbook_gap_confirmed=True,
            production_closure_requested=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "system-roi-post-quota-reselection-ready")
        self.assertEqual(review["recommendation"].recommended_track, "Payments Production Readiness Review")
        self.assertIn("Payments Production Readiness Review", review["next_tracks"])

    def test_reselection_can_recommend_shipping_when_payments_pressure_is_absent(self):
        review = system_roi_post_quota_reselection_queries.get_review(
            **self._quota_ready_flags(),
            shipping_quote_conversion_blocker=True,
            shipping_carrier_contract_ready=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["recommendation"].recommended_track, "Shipping Real Quote & SLA Activation Review")

    def test_reselection_can_recommend_cross_module_runbooks_when_requested(self):
        review = system_roi_post_quota_reselection_queries.get_review(
            **self._quota_ready_flags(),
            cross_module_runbook_gap_confirmed=True,
            production_closure_requested=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["recommendation"].recommended_track, "Cross-Module Production Runbook Closure Review")

    def test_reselection_blocks_without_quota_closure(self):
        review = system_roi_post_quota_reselection_queries.get_review(
            payments_provider_production_blocker=True,
            payments_refund_reconciliation_blocker=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("quota-closure:api-key-commercial-quotas-closure-blocked", review["blockers"])
        self.assertIn("quota-closure:commercial-quotas-closure:contract_ready:missing", review["blockers"])

    def test_reselection_blocks_when_no_candidate_crosses_threshold(self):
        review = system_roi_post_quota_reselection_queries.get_review(**self._quota_ready_flags())

        self.assertFalse(review["ready"])
        self.assertIn("roi:no-post-quota-candidate-above-threshold", review["blockers"])

    def test_command_outputs_recommendation_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "system_roi_post_quota_reselection",
            *self._quota_ready_args(),
            "--payments-provider-production-blocker",
            "--payments-refund-reconciliation-blocker",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommendation=Payments Production Readiness Review", value)
        self.assertIn("candidate key=payments-production-readiness", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("system_roi_post_quota_reselection", "--fail-on-blockers", stdout=StringIO())

    def _quota_ready_flags(self) -> dict[str, bool]:
        return {
            "quota_contract_ready": True,
            "quota_model_ready": True,
            "quota_enforcement_review_ready": True,
            "quota_enforcement_ready": True,
            "quota_admin_visibility_review_ready": True,
            "quota_admin_visibility_ready": True,
            "quota_metrics_ready": True,
            "quota_audit_ready": True,
            "quota_no_billing_charge_created": True,
            "quota_no_plan_enforcement_created": True,
            "quota_no_sensitive_material_recorded": True,
            "quota_docs_updated": True,
            "quota_decision_recorded": True,
        }

    def _quota_ready_args(self) -> tuple[str, ...]:
        return (
            "--quota-contract-ready",
            "--quota-model-ready",
            "--quota-enforcement-review-ready",
            "--quota-enforcement-ready",
            "--quota-admin-visibility-review-ready",
            "--quota-admin-visibility-ready",
            "--quota-metrics-ready",
            "--quota-audit-ready",
            "--quota-no-billing-charge-created",
            "--quota-no-plan-enforcement-created",
            "--quota-no-sensitive-material-recorded",
            "--quota-docs-updated",
            "--quota-decision-recorded",
        )
