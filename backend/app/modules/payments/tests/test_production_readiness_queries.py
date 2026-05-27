from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.payments.application.production_readiness_queries import (
    payment_financial_reconciliation_production_queries,
    payment_provider_production_activation_evidence_queries,
    payment_provider_production_gate_queries,
    payment_refund_production_gate_queries,
    payment_refund_production_smoke_evidence_queries,
    payment_webhook_production_smoke_queries,
    payments_production_closure_queries,
)


class PaymentsProductionReadinessTests(TestCase):
    def test_all_battery_c_reviews_are_ready_with_required_signals(self):
        reviews = (
            payment_provider_production_gate_queries.get_review(**self._provider_gate_flags()),
            payment_provider_production_activation_evidence_queries.get_review(**self._provider_evidence_flags()),
            payment_webhook_production_smoke_queries.get_review(**self._webhook_smoke_flags()),
            payment_refund_production_gate_queries.get_review(**self._refund_gate_flags()),
            payment_refund_production_smoke_evidence_queries.get_review(**self._refund_evidence_flags()),
            payment_financial_reconciliation_production_queries.get_review(**self._financial_reconciliation_flags()),
            payments_production_closure_queries.get_review(**self._closure_flags()),
        )

        for review in reviews:
            self.assertTrue(review["ready"], review["blockers"])
            self.assertEqual(review["blockers"], ())
        self.assertEqual(reviews[-1]["result"], "payments-production-closure-ready")
        self.assertIn("Battery D — Shipping Quote Productionization", reviews[-1]["next_tracks"])

    def test_provider_gate_blocks_without_credentials_and_rollback(self):
        review = payment_provider_production_gate_queries.get_review(
            provider_mode_production_confirmed=True,
            tenant_rollout_scope_defined=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("payment-provider-production-gate:provider_credentials_configured:missing", review["blockers"])
        self.assertIn("payment-provider-production-gate:rollback_plan_ready:missing", review["blockers"])

    def test_closure_blocks_without_reconciliation(self):
        review = payments_production_closure_queries.get_review(
            **{**self._closure_flags(), "financial_reconciliation_ready": False}
        )

        self.assertFalse(review["ready"])
        self.assertIn("payments-production-closure:financial_reconciliation_ready:missing", review["blockers"])

    def test_command_outputs_closure_without_sensitive_material(self):
        output = StringIO()

        call_command("payments_production_readiness", "--review", "closure", *self._closure_args(), stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("result=payments-production-closure-ready", value)
        self.assertIn("next_track=Battery D — Shipping Quote Productionization", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("token=", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("payments_production_readiness", "--review", "closure", "--fail-on-blockers", stdout=StringIO())

    def _provider_gate_flags(self) -> dict[str, bool]:
        return {
            "provider_credentials_configured": True,
            "provider_mode_production_confirmed": True,
            "tenant_rollout_scope_defined": True,
            "webhook_secret_configured": True,
            "hosted_return_url_configured": True,
            "observability_ready": True,
            "runbook_reviewed": True,
            "rollback_plan_ready": True,
            "finance_owner_approved": True,
            "no_secret_material_recorded": True,
        }

    def _provider_evidence_flags(self) -> dict[str, bool]:
        return {
            "production_gate_ready": True,
            "tenant_reference_recorded": True,
            "provider_dashboard_reference_recorded": True,
            "production_payment_intent_created": True,
            "hosted_checkout_reached": True,
            "return_url_observed": True,
            "metrics_snapshot_attached": True,
            "rollback_not_required": True,
            "no_secret_material_recorded": True,
        }

    def _webhook_smoke_flags(self) -> dict[str, bool]:
        return {
            "activation_evidence_ready": True,
            "paid_webhook_observed": True,
            "failed_webhook_observed_or_deferred": True,
            "signature_validation_confirmed": True,
            "idempotency_confirmed": True,
            "order_payment_status_confirmed": True,
            "inventory_side_effects_confirmed": True,
            "audit_log_confirmed": True,
            "no_sensitive_payload_recorded": True,
        }

    def _refund_gate_flags(self) -> dict[str, bool]:
        return {
            "webhook_smoke_ready": True,
            "refund_foundation_closed": True,
            "sandbox_evidence_captured": True,
            "provider_refund_reference_ready": True,
            "finance_approval_required": True,
            "single_refund_manual_scope": True,
            "reconciliation_reference_required": True,
            "rollback_plan_ready": True,
            "no_self_service_enabled": True,
            "no_batch_execution_enabled": True,
        }

    def _refund_evidence_flags(self) -> dict[str, bool]:
        return {
            "refund_gate_ready": True,
            "refund_key_recorded": True,
            "provider_refund_status_recorded": True,
            "provider_dashboard_reference_recorded": True,
            "internal_ledger_updated": True,
            "reconciliation_reference_recorded": True,
            "operator_recorded": True,
            "no_customer_self_service": True,
            "no_sensitive_material_recorded": True,
        }

    def _financial_reconciliation_flags(self) -> dict[str, bool]:
        return {
            "provider_activation_evidence_ready": True,
            "webhook_smoke_ready": True,
            "refund_evidence_ready_or_no_go_recorded": True,
            "reconciliation_report_exported": True,
            "paid_attempts_matched": True,
            "amount_mismatches_reviewed": True,
            "pending_attempts_triaged": True,
            "refund_entries_reconciled_or_deferred": True,
            "finance_owner_signed_off": True,
            "no_auto_correction_enabled": True,
        }

    def _closure_flags(self) -> dict[str, bool]:
        return {
            "provider_gate_ready": True,
            "provider_activation_evidence_ready": True,
            "webhook_smoke_ready": True,
            "refund_gate_ready": True,
            "refund_smoke_evidence_ready_or_no_go_recorded": True,
            "financial_reconciliation_ready": True,
            "rollback_runbook_ready": True,
            "monitoring_window_defined": True,
            "incident_owner_defined": True,
            "no_unbounded_rollout": True,
            "no_sensitive_material_recorded": True,
            "decision_recorded": True,
        }

    def _closure_args(self) -> tuple[str, ...]:
        return tuple(f"--{key.replace('_', '-')}" for key, value in self._closure_flags().items() if value)
