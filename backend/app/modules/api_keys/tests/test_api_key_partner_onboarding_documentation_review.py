from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_partner_onboarding_documentation_review_queries import (
    api_key_partner_onboarding_documentation_review_queries,
)


class ApiKeyPartnerOnboardingDocumentationReviewTests(TestCase):
    def test_review_ready_when_partner_documentation_contract_is_complete(self):
        review = api_key_partner_onboarding_documentation_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-onboarding-documentation-ready")
        self.assertEqual(review["blockers"], ())
        self.assertTrue(review["documentation_artifacts"]["partner-onboarding-doc"])
        self.assertTrue(review["documentation_artifacts"]["catalog-list-example"])
        self.assertTrue(review["documentation_artifacts"]["catalog-detail-example"])
        self.assertIn("API Key Partner Documentation Execution Review", review["next_tracks"])

    def test_review_blocks_without_governance_readiness(self):
        review = api_key_partner_onboarding_documentation_review_queries.get_review(
            partner_docs_versioned=True,
            endpoint_examples_documented=True,
            activation_checklist_ready=True,
            error_contract_documented=True,
            safe_examples_confirmed=True,
            no_new_endpoint_required=True,
            no_quota_or_billing_required=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("roi:api-key-system-roi-reselection-blocked", review["blockers"])
        self.assertIn("roi:governance:model-ready:missing", review["blockers"])

    def test_review_blocks_without_documentation_signals(self):
        review = api_key_partner_onboarding_documentation_review_queries.get_review(
            **self._governance_flags(),
        )

        self.assertFalse(review["ready"])
        self.assertIn("partner-docs-versioned:missing", review["blockers"])
        self.assertIn("endpoint-examples-documented:missing", review["blockers"])
        self.assertIn("safe-examples-confirmed:missing", review["blockers"])

    def test_command_outputs_safe_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_partner_onboarding_documentation_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("artifact name=partner-onboarding-doc present=True", value)
        self.assertIn("decision key=examples status=safe", value)
        self.assertIn("closed_scope=GET /api/v1/catalog/products/<slug>/", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "api_key_partner_onboarding_documentation_review",
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

    def _ready_flags(self) -> dict[str, bool]:
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
        )
