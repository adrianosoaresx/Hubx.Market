from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_partner_activation_closure_queries import (
    api_key_partner_activation_closure_queries,
)
from app.modules.api_keys.application.api_key_partner_activation_evidence_capture_queries import (
    api_key_partner_activation_evidence_capture_queries,
)
from app.modules.api_keys.application.api_key_partner_activation_post_smoke_monitoring_queries import (
    api_key_partner_activation_post_smoke_monitoring_queries,
)
from app.modules.api_keys.application.api_key_partner_activation_smoke_execution_queries import (
    api_key_partner_activation_smoke_execution_queries,
)


class ApiKeyPartnerActivationRemainingWavesTests(TestCase):
    def test_smoke_execution_ready_when_operational_checks_are_sanitized(self):
        review = api_key_partner_activation_smoke_execution_queries.get_review(**self._smoke_execution_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-activation-smoke-execution-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["identifiers"]["partner_reference"], "partner-ref-001")
        self.assertIn("API Key Partner Activation Evidence Capture", review["next_tracks"])

    def test_smoke_execution_blocks_and_sanitizes_secret_like_references(self):
        review = api_key_partner_activation_smoke_execution_queries.get_review(
            **{
                **self._smoke_execution_flags(),
                "evidence_reference": "Authorization: Bearer secret",
            }
        )

        self.assertFalse(review["ready"])
        self.assertEqual(review["identifiers"]["evidence_reference"], "")
        self.assertIn("partner-activation-smoke-execution:evidence_reference_present:missing", review["blockers"])

    def test_evidence_capture_ready_when_required_artifacts_are_attached(self):
        review = api_key_partner_activation_evidence_capture_queries.get_review(**self._evidence_capture_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-activation-evidence-capture-ready")
        self.assertIn("sanitized detail endpoint result", review["evidence_items"])
        self.assertIn("API Key Partner Activation Post-Smoke Monitoring", review["next_tracks"])

    def test_post_smoke_monitoring_ready_when_initial_window_is_stable(self):
        review = api_key_partner_activation_post_smoke_monitoring_queries.get_review(
            **self._post_smoke_monitoring_flags()
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-activation-post-smoke-monitoring-ready")
        self.assertIn("API Key Partner Activation Closure Review", review["next_tracks"])

    def test_closure_ready_when_all_remaining_battery_a_waves_are_closed(self):
        review = api_key_partner_activation_closure_queries.get_review(**self._closure_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-activation-closure-ready")
        self.assertIn("API Key Commercial Quotas Contract Review", review["next_tracks"])
        self.assertIn("commercial quota track selection", review["closure_scope"])

    def test_commands_output_no_sensitive_material(self):
        output = StringIO()

        call_command("api_key_partner_activation_smoke_execution", *self._smoke_execution_args(), stdout=output)
        call_command("api_key_partner_activation_evidence_capture", *self._evidence_capture_args(), stdout=output)
        call_command(
            "api_key_partner_activation_post_smoke_monitoring",
            *self._post_smoke_monitoring_args(),
            stdout=output,
        )
        call_command("api_key_partner_activation_closure", *self._closure_args(), stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("result=api-key-partner-activation-closure-ready", value)
        self.assertIn("next_track=API Key Commercial Quotas Contract Review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_commands_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_partner_activation_closure", "--fail-on-blockers", stdout=StringIO())

    def _smoke_execution_flags(self) -> dict[str, object]:
        return {
            "smoke_contract_ready": True,
            "partner_reference": "partner-ref-001",
            "tenant_reference": "tenant-ref-001",
            "target_environment": "staging",
            "list_endpoint_checked": True,
            "detail_endpoint_checked": True,
            "list_status_expected": True,
            "detail_status_expected": True,
            "auth_failure_negative_checked": True,
            "observability_signal_checked": True,
            "rollback_not_required": True,
            "evidence_reference": "SMOKE-EXEC-001",
            "redaction_confirmed": True,
            "no_secret_material_recorded": True,
            "no_runtime_change_performed": True,
        }

    def _evidence_capture_flags(self) -> dict[str, object]:
        return {
            "smoke_execution_ready": True,
            "evidence_reference": "SMOKE-EVIDENCE-001",
            "list_result_attached": True,
            "detail_result_attached": True,
            "negative_auth_result_attached": True,
            "metrics_snapshot_attached": True,
            "audit_log_reference_attached": True,
            "partner_handoff_reference_attached": True,
            "support_handoff_reference_attached": True,
            "redaction_confirmed": True,
            "no_secret_material_recorded": True,
            "rollback_note_attached": True,
        }

    def _post_smoke_monitoring_flags(self) -> dict[str, object]:
        return {
            "evidence_capture_ready": True,
            "monitoring_window_observed": True,
            "partner_access_stable": True,
            "auth_failure_rate_expected": True,
            "rate_limit_noise_expected": True,
            "endpoint_error_rate_expected": True,
            "support_ticket_status_recorded": True,
            "rollback_not_required": True,
            "no_sensitive_data_observed": True,
            "commercial_quota_pressure_recorded": True,
        }

    def _closure_flags(self) -> dict[str, object]:
        return {
            "smoke_contract_ready": True,
            "smoke_execution_ready": True,
            "evidence_capture_ready": True,
            "post_smoke_monitoring_ready": True,
            "partner_handoff_closed": True,
            "support_handoff_closed": True,
            "rollback_window_closed": True,
            "no_sensitive_material_retained": True,
            "no_runtime_change_pending": True,
            "commercial_quota_track_selected": True,
            "docs_updated": True,
            "decision_recorded": True,
        }

    def _smoke_execution_args(self) -> tuple[str, ...]:
        return (
            "--smoke-contract-ready",
            "--partner-reference",
            "partner-ref-001",
            "--tenant-reference",
            "tenant-ref-001",
            "--target-environment",
            "staging",
            "--list-endpoint-checked",
            "--detail-endpoint-checked",
            "--list-status-expected",
            "--detail-status-expected",
            "--auth-failure-negative-checked",
            "--observability-signal-checked",
            "--rollback-not-required",
            "--evidence-reference",
            "SMOKE-EXEC-001",
            "--redaction-confirmed",
            "--no-secret-material-recorded",
            "--no-runtime-change-performed",
        )

    def _evidence_capture_args(self) -> tuple[str, ...]:
        return (
            "--smoke-execution-ready",
            "--evidence-reference",
            "SMOKE-EVIDENCE-001",
            "--list-result-attached",
            "--detail-result-attached",
            "--negative-auth-result-attached",
            "--metrics-snapshot-attached",
            "--audit-log-reference-attached",
            "--partner-handoff-reference-attached",
            "--support-handoff-reference-attached",
            "--redaction-confirmed",
            "--no-secret-material-recorded",
            "--rollback-note-attached",
        )

    def _post_smoke_monitoring_args(self) -> tuple[str, ...]:
        return (
            "--evidence-capture-ready",
            "--monitoring-window-observed",
            "--partner-access-stable",
            "--auth-failure-rate-expected",
            "--rate-limit-noise-expected",
            "--endpoint-error-rate-expected",
            "--support-ticket-status-recorded",
            "--rollback-not-required",
            "--no-sensitive-data-observed",
            "--commercial-quota-pressure-recorded",
        )

    def _closure_args(self) -> tuple[str, ...]:
        return (
            "--smoke-contract-ready",
            "--smoke-execution-ready",
            "--evidence-capture-ready",
            "--post-smoke-monitoring-ready",
            "--partner-handoff-closed",
            "--support-handoff-closed",
            "--rollback-window-closed",
            "--no-sensitive-material-retained",
            "--no-runtime-change-pending",
            "--commercial-quota-track-selected",
            "--docs-updated",
            "--decision-recorded",
        )
