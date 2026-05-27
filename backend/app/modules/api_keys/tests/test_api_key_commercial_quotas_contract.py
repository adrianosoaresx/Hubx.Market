from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_commercial_quotas_contract_queries import (
    api_key_commercial_quotas_contract_queries,
)


class ApiKeyCommercialQuotasContractTests(TestCase):
    def test_contract_ready_when_operator_selects_battery_b_and_quota_shape_is_documented(self):
        review = api_key_commercial_quotas_contract_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-commercial-quotas-contract-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["contract"].dimensions, ("tenant_id", "api_key_id", "endpoint", "window"))
        self.assertEqual(review["contract"].response_status, 429)
        self.assertIn("API Key Quota Model Minimal Execution", review["next_tracks"])

    def test_contract_blocks_without_onboarding_closure(self):
        review = api_key_commercial_quotas_contract_queries.get_review(
            battery_b_selected_by_operator=True,
            battery_a_remaining_deferred=True,
            commercial_quota_pressure_confirmed=True,
            quota_dimensions_documented=True,
            quota_window_documented=True,
            quota_default_limits_documented=True,
            quota_overage_behavior_documented=True,
            quota_error_contract_documented=True,
            quota_observability_documented=True,
            quota_admin_visibility_documented=True,
            no_billing_charge_in_contract=True,
            no_plan_enforcement_in_contract=True,
            no_runtime_enforcement_in_contract=True,
            no_new_endpoint_in_contract=True,
            no_sensitive_material_in_contract=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("onboarding:api-key-partner-onboarding-closure-blocked", review["blockers"])
        self.assertIn("onboarding:publication:execution:onboarding:roi:governance:model-ready:missing", review["blockers"])

    def test_contract_blocks_without_operator_selection_and_commercial_pressure(self):
        review = api_key_commercial_quotas_contract_queries.get_review(
            **self._closure_flags(),
            quota_dimensions_documented=True,
            quota_window_documented=True,
            quota_default_limits_documented=True,
            quota_overage_behavior_documented=True,
            quota_error_contract_documented=True,
            quota_observability_documented=True,
            quota_admin_visibility_documented=True,
            no_billing_charge_in_contract=True,
            no_plan_enforcement_in_contract=True,
            no_runtime_enforcement_in_contract=True,
            no_new_endpoint_in_contract=True,
            no_sensitive_material_in_contract=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("battery-b-selected-by-operator:missing", review["blockers"])
        self.assertIn("battery-a-remaining-deferred:missing", review["blockers"])
        self.assertIn("commercial-quota-pressure-confirmed:missing", review["blockers"])

    def test_contract_blocks_without_boundary_guards(self):
        review = api_key_commercial_quotas_contract_queries.get_review(
            **self._closure_flags(),
            battery_b_selected_by_operator=True,
            battery_a_remaining_deferred=True,
            commercial_quota_pressure_confirmed=True,
            quota_dimensions_documented=True,
            quota_window_documented=True,
            quota_default_limits_documented=True,
            quota_overage_behavior_documented=True,
            quota_error_contract_documented=True,
            quota_observability_documented=True,
            quota_admin_visibility_documented=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("no-billing-charge-in-contract:missing", review["blockers"])
        self.assertIn("no-runtime-enforcement-in-contract:missing", review["blockers"])
        self.assertIn("no-sensitive-material-in-contract:missing", review["blockers"])

    def test_command_outputs_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_commercial_quotas_contract",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("scope=read:catalog", value)
        self.assertIn("decision key=boundaries status=guarded", value)
        self.assertIn("closed_scope=quota dimensions tenant_id/api_key_id/endpoint/window", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_commercial_quotas_contract", "--fail-on-blockers", stdout=StringIO())

    def _governance_flags(self) -> dict[str, bool]:
        return {
            "model_ready": True,
            "runtime_auth_ready": True,
            "drf_adapter_ready": True,
            "public_endpoints_ready": True,
            "observability_ready": True,
            "expansion_closed": True,
            "no_billing_or_quotas_required": True,
            "no_secret_exposure_confirmed": True,
        }

    def _onboarding_flags(self) -> dict[str, bool]:
        return {
            **self._governance_flags(),
            "partner_docs_versioned": True,
            "endpoint_examples_documented": True,
            "activation_checklist_ready": True,
            "error_contract_documented": True,
            "safe_examples_confirmed": True,
            "no_new_endpoint_required": True,
            "no_quota_or_billing_required": True,
        }

    def _execution_flags(self) -> dict[str, bool]:
        return {
            **self._onboarding_flags(),
            "delivery_channel_documented": True,
            "support_handoff_documented": True,
            "smoke_evidence_template_ready": True,
            "change_control_documented": True,
            "owner_approved": True,
            "no_runtime_change_required": True,
            "no_commercial_terms_included": True,
            "no_sensitive_material_included": True,
        }

    def _publication_flags(self) -> dict[str, object]:
        return {
            **self._execution_flags(),
            "published_version": "2026-05-26",
            "approved_channel": "restricted-support-ticket",
            "target_audience": "approved-partner",
            "tenant_reference": "tenant-ref-001",
            "published_at": "2026-05-26T12:00:00-03:00",
            "evidence_reference": "DOC-EVIDENCE-001",
            "publication_confirmed": True,
            "support_notified": True,
            "activation_status_recorded": True,
            "smoke_template_attached": True,
            "redaction_confirmed": True,
            "no_credential_shared": True,
            "no_runtime_activation_performed": True,
        }

    def _closure_flags(self) -> dict[str, object]:
        return {
            **self._publication_flags(),
            "onboarding_scope_closed": True,
            "residual_risks_accepted": True,
            "next_roi_decision_recorded": True,
            "partner_activation_deferred": True,
            "commercial_quotas_deferred": True,
            "new_endpoint_expansion_deferred": True,
        }

    def _ready_flags(self) -> dict[str, object]:
        return {
            **self._closure_flags(),
            "battery_b_selected_by_operator": True,
            "battery_a_remaining_deferred": True,
            "commercial_quota_pressure_confirmed": True,
            "quota_dimensions_documented": True,
            "quota_window_documented": True,
            "quota_default_limits_documented": True,
            "quota_overage_behavior_documented": True,
            "quota_error_contract_documented": True,
            "quota_observability_documented": True,
            "quota_admin_visibility_documented": True,
            "no_billing_charge_in_contract": True,
            "no_plan_enforcement_in_contract": True,
            "no_runtime_enforcement_in_contract": True,
            "no_new_endpoint_in_contract": True,
            "no_sensitive_material_in_contract": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--model-ready",
            "--runtime-auth-ready",
            "--drf-adapter-ready",
            "--public-endpoints-ready",
            "--observability-ready",
            "--expansion-closed",
            "--no-billing-or-quotas-required",
            "--no-secret-exposure-confirmed",
            "--partner-docs-versioned",
            "--endpoint-examples-documented",
            "--activation-checklist-ready",
            "--error-contract-documented",
            "--safe-examples-confirmed",
            "--no-new-endpoint-required",
            "--no-quota-or-billing-required",
            "--delivery-channel-documented",
            "--support-handoff-documented",
            "--smoke-evidence-template-ready",
            "--change-control-documented",
            "--owner-approved",
            "--no-runtime-change-required",
            "--no-commercial-terms-included",
            "--no-sensitive-material-included",
            "--published-version",
            "2026-05-26",
            "--approved-channel",
            "restricted-support-ticket",
            "--target-audience",
            "approved-partner",
            "--tenant-reference",
            "tenant-ref-001",
            "--published-at",
            "2026-05-26T12:00:00-03:00",
            "--evidence-reference",
            "DOC-EVIDENCE-001",
            "--publication-confirmed",
            "--support-notified",
            "--activation-status-recorded",
            "--smoke-template-attached",
            "--redaction-confirmed",
            "--no-credential-shared",
            "--no-runtime-activation-performed",
            "--onboarding-scope-closed",
            "--residual-risks-accepted",
            "--next-roi-decision-recorded",
            "--partner-activation-deferred",
            "--commercial-quotas-deferred",
            "--new-endpoint-expansion-deferred",
            "--battery-b-selected-by-operator",
            "--battery-a-remaining-deferred",
            "--commercial-quota-pressure-confirmed",
            "--quota-dimensions-documented",
            "--quota-window-documented",
            "--quota-default-limits-documented",
            "--quota-overage-behavior-documented",
            "--quota-error-contract-documented",
            "--quota-observability-documented",
            "--quota-admin-visibility-documented",
            "--no-billing-charge-in-contract",
            "--no-plan-enforcement-in-contract",
            "--no-runtime-enforcement-in-contract",
            "--no-new-endpoint-in-contract",
            "--no-sensitive-material-in-contract",
        )
