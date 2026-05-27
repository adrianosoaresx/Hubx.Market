from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_system_roi_reselection_queries import (
    api_key_system_roi_reselection_queries,
)


class ApiKeySystemRoiReselectionTests(TestCase):
    def test_reselection_recommends_partner_onboarding_docs_after_governance_closure(self):
        review = api_key_system_roi_reselection_queries.get_review(
            **self._ready_flags(),
            partner_docs_missing=True,
            partner_onboarding_requested=True,
            commercial_quota_pressure_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-system-roi-reselection-ready")
        self.assertEqual(
            review["recommendation"].recommended_track,
            "API Key Partner Onboarding Documentation Review",
        )
        self.assertIn("API Key Partner Onboarding Documentation Review", review["next_tracks"])

    def test_reselection_can_prioritize_incident_hardening_when_pressure_is_confirmed(self):
        review = api_key_system_roi_reselection_queries.get_review(
            **self._ready_flags(),
            production_incident_pressure_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(
            review["recommendation"].recommended_track,
            "API Key Production Incident Hardening Review",
        )

    def test_reselection_blocks_when_governance_closure_is_not_ready(self):
        review = api_key_system_roi_reselection_queries.get_review(
            partner_docs_missing=True,
            partner_onboarding_requested=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("governance:api-key-governance-closure-blocked", review["blockers"])
        self.assertIn("governance:model-ready:missing", review["blockers"])

    def test_reselection_blocks_when_no_candidate_crosses_threshold(self):
        review = api_key_system_roi_reselection_queries.get_review(**self._ready_flags())

        self.assertFalse(review["ready"])
        self.assertIn("roi:no-system-candidate-above-threshold", review["blockers"])

    def test_command_outputs_recommendation_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_system_roi_reselection",
            *self._ready_args(),
            "--partner-docs-missing",
            "--partner-onboarding-requested",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommendation=API Key Partner Onboarding Documentation Review", value)
        self.assertIn("candidate key=partner-onboarding-docs", value)
        self.assertIn("decision key=partner-usability-gap status=confirmed", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_system_roi_reselection", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
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
        )
