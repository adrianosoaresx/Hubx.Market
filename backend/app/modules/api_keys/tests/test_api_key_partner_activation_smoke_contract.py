from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_partner_activation_smoke_contract_queries import (
    api_key_partner_activation_smoke_contract_queries,
)


class ApiKeyPartnerActivationSmokeContractTests(TestCase):
    def test_smoke_contract_ready_when_partner_activation_scope_is_documented(self):
        review = api_key_partner_activation_smoke_contract_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-activation-smoke-contract-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["contract"].partner_reference, "partner-ref-001")
        self.assertIn("GET /api/v1/catalog/products/", review["smoke_scope"])
        self.assertIn("API Key Partner Activation Smoke Execution", review["next_tracks"])

    def test_smoke_contract_blocks_without_roi_recommendation(self):
        review = api_key_partner_activation_smoke_contract_queries.get_review(
            **self._closure_flags(),
            **self._contract_fields(),
            smoke_scope_documented=True,
            list_endpoint_in_scope=True,
            detail_endpoint_in_scope=True,
            expected_status_codes_documented=True,
            observability_check_documented=True,
            rollback_plan_documented=True,
            redaction_plan_documented=True,
            no_new_endpoint_in_smoke=True,
            no_commercial_terms_in_smoke=True,
            no_runtime_change_in_smoke=True,
            no_credential_material_in_smoke=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("roi:api-key-post-onboarding-roi-reselection-blocked", review["blockers"])
        self.assertIn("roi:roi:no-post-onboarding-candidate-above-threshold", review["blockers"])

    def test_smoke_contract_blocks_without_contract_fields(self):
        review = api_key_partner_activation_smoke_contract_queries.get_review(
            **self._roi_flags(),
            smoke_scope_documented=True,
            list_endpoint_in_scope=True,
            detail_endpoint_in_scope=True,
            expected_status_codes_documented=True,
            observability_check_documented=True,
            rollback_plan_documented=True,
            redaction_plan_documented=True,
            no_new_endpoint_in_smoke=True,
            no_commercial_terms_in_smoke=True,
            no_runtime_change_in_smoke=True,
            no_credential_material_in_smoke=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("partner-reference:missing", review["blockers"])
        self.assertIn("target-environment:missing", review["blockers"])
        self.assertIn("smoke-evidence-reference:missing", review["blockers"])

    def test_smoke_contract_blocks_without_boundary_guards(self):
        review = api_key_partner_activation_smoke_contract_queries.get_review(
            **self._roi_flags(),
            **self._contract_fields(),
            smoke_scope_documented=True,
            list_endpoint_in_scope=True,
            detail_endpoint_in_scope=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("rollback-plan-documented:missing", review["blockers"])
        self.assertIn("no-runtime-change-in-smoke:missing", review["blockers"])
        self.assertIn("no-credential-material-in-smoke:missing", review["blockers"])

    def test_command_outputs_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_partner_activation_smoke_contract",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("partner=partner-ref-001", value)
        self.assertIn("decision key=boundaries status=guarded", value)
        self.assertIn("smoke_scope=GET /api/v1/catalog/products/<slug>/", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_partner_activation_smoke_contract", "--fail-on-blockers", stdout=StringIO())

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

    def _roi_flags(self) -> dict[str, object]:
        return {
            **self._closure_flags(),
            "partner_activation_requested": True,
            "partner_api_key_ready": True,
        }

    def _contract_fields(self) -> dict[str, str]:
        return {
            "partner_reference": "partner-ref-001",
            "target_environment": "staging",
            "product_slug_reference": "product-slug-ref-001",
            "smoke_evidence_reference": "SMOKE-CONTRACT-001",
        }

    def _ready_flags(self) -> dict[str, object]:
        return {
            **self._roi_flags(),
            **self._contract_fields(),
            "smoke_scope_documented": True,
            "list_endpoint_in_scope": True,
            "detail_endpoint_in_scope": True,
            "expected_status_codes_documented": True,
            "observability_check_documented": True,
            "rollback_plan_documented": True,
            "redaction_plan_documented": True,
            "no_new_endpoint_in_smoke": True,
            "no_commercial_terms_in_smoke": True,
            "no_runtime_change_in_smoke": True,
            "no_credential_material_in_smoke": True,
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
            "--partner-activation-requested",
            "--partner-api-key-ready",
            "--partner-reference",
            "partner-ref-001",
            "--target-environment",
            "staging",
            "--product-slug-reference",
            "product-slug-ref-001",
            "--smoke-evidence-reference",
            "SMOKE-CONTRACT-001",
            "--smoke-scope-documented",
            "--list-endpoint-in-scope",
            "--detail-endpoint-in-scope",
            "--expected-status-codes-documented",
            "--observability-check-documented",
            "--rollback-plan-documented",
            "--redaction-plan-documented",
            "--no-new-endpoint-in-smoke",
            "--no-commercial-terms-in-smoke",
            "--no-runtime-change-in-smoke",
            "--no-credential-material-in-smoke",
        )
