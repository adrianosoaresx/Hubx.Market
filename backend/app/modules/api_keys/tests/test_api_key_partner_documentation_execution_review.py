from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_partner_documentation_execution_review_queries import (
    api_key_partner_documentation_execution_review_queries,
)


class ApiKeyPartnerDocumentationExecutionReviewTests(TestCase):
    def test_execution_review_ready_when_delivery_package_is_documented(self):
        review = api_key_partner_documentation_execution_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-documentation-execution-ready")
        self.assertEqual(review["blockers"], ())
        self.assertTrue(review["execution_artifacts"]["delivery-package-section"])
        self.assertTrue(review["execution_artifacts"]["smoke-evidence-template"])
        self.assertIn("API Key Partner Documentation Publication Evidence Review", review["next_tracks"])

    def test_execution_review_blocks_without_onboarding_readiness(self):
        review = api_key_partner_documentation_execution_review_queries.get_review(
            delivery_channel_documented=True,
            support_handoff_documented=True,
            smoke_evidence_template_ready=True,
            change_control_documented=True,
            owner_approved=True,
            no_runtime_change_required=True,
            no_commercial_terms_included=True,
            no_sensitive_material_included=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("onboarding:api-key-partner-onboarding-documentation-blocked", review["blockers"])
        self.assertIn("onboarding:roi:governance:model-ready:missing", review["blockers"])

    def test_execution_review_blocks_without_execution_signals(self):
        review = api_key_partner_documentation_execution_review_queries.get_review(**self._onboarding_flags())

        self.assertFalse(review["ready"])
        self.assertIn("delivery-channel-documented:missing", review["blockers"])
        self.assertIn("support-handoff-documented:missing", review["blockers"])
        self.assertIn("no-sensitive-material-included:missing", review["blockers"])

    def test_command_outputs_delivery_scope_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_partner_documentation_execution_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("artifact name=delivery-package-section present=True", value)
        self.assertIn("decision key=safety-boundary status=guarded", value)
        self.assertIn("delivery_scope=smoke evidence template", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "api_key_partner_documentation_execution_review",
                "--fail-on-blockers",
                stdout=StringIO(),
            )

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

    def _ready_flags(self) -> dict[str, bool]:
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
        )
