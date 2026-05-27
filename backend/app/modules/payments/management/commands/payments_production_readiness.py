from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.payments.application.production_readiness_queries import (
    payment_financial_reconciliation_production_queries,
    payment_provider_production_activation_evidence_queries,
    payment_provider_production_gate_queries,
    payment_refund_production_gate_queries,
    payment_refund_production_smoke_evidence_queries,
    payment_webhook_production_smoke_queries,
    payments_production_closure_queries,
)


REVIEWS = {
    "provider-gate": payment_provider_production_gate_queries.get_review,
    "provider-evidence": payment_provider_production_activation_evidence_queries.get_review,
    "webhook-smoke": payment_webhook_production_smoke_queries.get_review,
    "refund-gate": payment_refund_production_gate_queries.get_review,
    "refund-evidence": payment_refund_production_smoke_evidence_queries.get_review,
    "financial-reconciliation": payment_financial_reconciliation_production_queries.get_review,
    "closure": payments_production_closure_queries.get_review,
}


class Command(BaseCommand):
    help = "Executa reviews da Battery C — Payments Production Readiness."

    def add_arguments(self, parser):
        parser.add_argument("--review", choices=tuple(REVIEWS.keys()), default="closure")
        parser.add_argument("--fail-on-blockers", action="store_true")
        for name in (
            "provider-credentials-configured",
            "provider-mode-production-confirmed",
            "tenant-rollout-scope-defined",
            "webhook-secret-configured",
            "hosted-return-url-configured",
            "observability-ready",
            "runbook-reviewed",
            "rollback-plan-ready",
            "finance-owner-approved",
            "no-secret-material-recorded",
            "production-gate-ready",
            "tenant-reference-recorded",
            "provider-dashboard-reference-recorded",
            "production-payment-intent-created",
            "hosted-checkout-reached",
            "return-url-observed",
            "metrics-snapshot-attached",
            "rollback-not-required",
            "activation-evidence-ready",
            "paid-webhook-observed",
            "failed-webhook-observed-or-deferred",
            "signature-validation-confirmed",
            "idempotency-confirmed",
            "order-payment-status-confirmed",
            "inventory-side-effects-confirmed",
            "audit-log-confirmed",
            "no-sensitive-payload-recorded",
            "no-sensitive-material-recorded",
            "webhook-smoke-ready",
            "refund-foundation-closed",
            "sandbox-evidence-captured",
            "provider-refund-reference-ready",
            "finance-approval-required",
            "single-refund-manual-scope",
            "reconciliation-reference-required",
            "no-self-service-enabled",
            "no-batch-execution-enabled",
            "refund-gate-ready",
            "refund-key-recorded",
            "provider-refund-status-recorded",
            "internal-ledger-updated",
            "reconciliation-reference-recorded",
            "operator-recorded",
            "no-customer-self-service",
            "provider-activation-evidence-ready",
            "refund-evidence-ready-or-no-go-recorded",
            "reconciliation-report-exported",
            "paid-attempts-matched",
            "amount-mismatches-reviewed",
            "pending-attempts-triaged",
            "refund-entries-reconciled-or-deferred",
            "no-auto-correction-enabled",
            "provider-gate-ready",
            "refund-smoke-evidence-ready-or-no-go-recorded",
            "financial-reconciliation-ready",
            "rollback-runbook-ready",
            "monitoring-window-defined",
            "incident-owner-defined",
            "no-unbounded-rollout",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")

    def handle(self, *args, **options):
        review_name = options["review"]
        review = REVIEWS[review_name](**self._review_options(review_name=review_name, options=options))
        self.stdout.write(f"[{str(review['status']).upper()}] result={review['result']} module={review['module']} review={review_name}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review.get("closure_scope", ()):
            self.stdout.write(f"closure_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("Payments production readiness review is blocked.")

    def _review_options(self, *, review_name: str, options: dict[str, object]) -> dict[str, object]:
        ignored = {
            "review",
            "fail_on_blockers",
            "verbosity",
            "settings",
            "pythonpath",
            "traceback",
            "no_color",
            "force_color",
            "skip_checks",
            "stdout",
            "stderr",
        }
        allowed_by_review = {
            "provider-gate": {
                "provider_credentials_configured",
                "provider_mode_production_confirmed",
                "tenant_rollout_scope_defined",
                "webhook_secret_configured",
                "hosted_return_url_configured",
                "observability_ready",
                "runbook_reviewed",
                "rollback_plan_ready",
                "finance_owner_approved",
                "no_secret_material_recorded",
            },
            "provider-evidence": {
                "production_gate_ready",
                "tenant_reference_recorded",
                "provider_dashboard_reference_recorded",
                "production_payment_intent_created",
                "hosted_checkout_reached",
                "return_url_observed",
                "metrics_snapshot_attached",
                "rollback_not_required",
                "no_secret_material_recorded",
            },
            "webhook-smoke": {
                "activation_evidence_ready",
                "paid_webhook_observed",
                "failed_webhook_observed_or_deferred",
                "signature_validation_confirmed",
                "idempotency_confirmed",
                "order_payment_status_confirmed",
                "inventory_side_effects_confirmed",
                "audit_log_confirmed",
                "no_sensitive_payload_recorded",
            },
            "refund-gate": {
                "webhook_smoke_ready",
                "refund_foundation_closed",
                "sandbox_evidence_captured",
                "provider_refund_reference_ready",
                "finance_approval_required",
                "single_refund_manual_scope",
                "reconciliation_reference_required",
                "rollback_plan_ready",
                "no_self_service_enabled",
                "no_batch_execution_enabled",
            },
            "refund-evidence": {
                "refund_gate_ready",
                "refund_key_recorded",
                "provider_refund_status_recorded",
                "provider_dashboard_reference_recorded",
                "internal_ledger_updated",
                "reconciliation_reference_recorded",
                "operator_recorded",
                "no_customer_self_service",
                "no_sensitive_material_recorded",
            },
            "financial-reconciliation": {
                "provider_activation_evidence_ready",
                "webhook_smoke_ready",
                "refund_evidence_ready_or_no_go_recorded",
                "reconciliation_report_exported",
                "paid_attempts_matched",
                "amount_mismatches_reviewed",
                "pending_attempts_triaged",
                "refund_entries_reconciled_or_deferred",
                "finance_owner_approved",
                "no_auto_correction_enabled",
            },
            "closure": {
                "provider_gate_ready",
                "provider_activation_evidence_ready",
                "webhook_smoke_ready",
                "refund_gate_ready",
                "refund_smoke_evidence_ready_or_no_go_recorded",
                "financial_reconciliation_ready",
                "rollback_runbook_ready",
                "monitoring_window_defined",
                "incident_owner_defined",
                "no_unbounded_rollout",
                "no_sensitive_material_recorded",
                "decision_recorded",
            },
        }
        allowed = allowed_by_review[review_name]
        review_options = {
            key: value
            for key, value in options.items()
            if key not in ignored and key in allowed
        }
        if review_name == "financial-reconciliation":
            review_options["finance_owner_signed_off"] = bool(review_options.pop("finance_owner_approved", False))
        return review_options
