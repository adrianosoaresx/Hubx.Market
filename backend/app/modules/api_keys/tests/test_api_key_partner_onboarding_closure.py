from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_partner_onboarding_closure_queries import (
    api_key_partner_onboarding_closure_queries,
)


class ApiKeyPartnerOnboardingClosureTests(TestCase):
    def test_closure_ready_when_publication_evidence_and_deferrals_are_complete(self):
        closure = api_key_partner_onboarding_closure_queries.get_closure(**self._ready_flags())

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["result"], "api-key-partner-onboarding-closure-ready")
        self.assertEqual(closure["blockers"], ())
        self.assertEqual(closure["publication_evidence"]["version"], "2026-05-26")
        self.assertIn("partner documentation publication evidence", closure["closed_scope"])
        self.assertIn("System ROI Re-Selection Review", closure["next_tracks"])

    def test_closure_blocks_without_publication_evidence_readiness(self):
        closure = api_key_partner_onboarding_closure_queries.get_closure(
            onboarding_scope_closed=True,
            residual_risks_accepted=True,
            next_roi_decision_recorded=True,
            partner_activation_deferred=True,
            commercial_quotas_deferred=True,
            new_endpoint_expansion_deferred=True,
        )

        self.assertFalse(closure["ready"])
        self.assertIn("publication:api-key-partner-documentation-publication-evidence-blocked", closure["blockers"])
        self.assertIn("publication:execution:onboarding:roi:governance:model-ready:missing", closure["blockers"])

    def test_closure_blocks_without_scope_and_risk_signals(self):
        closure = api_key_partner_onboarding_closure_queries.get_closure(**self._publication_flags())

        self.assertFalse(closure["ready"])
        self.assertIn("onboarding-scope-closed:missing", closure["blockers"])
        self.assertIn("residual-risks-accepted:missing", closure["blockers"])
        self.assertIn("new-endpoint-expansion-deferred:missing", closure["blockers"])

    def test_command_outputs_closure_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_partner_onboarding_closure",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("decision key=scope status=closed", value)
        self.assertIn("closed_scope=public catalog onboarding guide", value)
        self.assertIn("next_track=System ROI Re-Selection Review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_partner_onboarding_closure", "--fail-on-blockers", stdout=StringIO())

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

    def _ready_flags(self) -> dict[str, object]:
        return {
            **self._publication_flags(),
            "onboarding_scope_closed": True,
            "residual_risks_accepted": True,
            "next_roi_decision_recorded": True,
            "partner_activation_deferred": True,
            "commercial_quotas_deferred": True,
            "new_endpoint_expansion_deferred": True,
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
        )
