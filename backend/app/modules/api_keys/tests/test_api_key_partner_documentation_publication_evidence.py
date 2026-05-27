from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_partner_documentation_publication_evidence_queries import (
    api_key_partner_documentation_publication_evidence_queries,
)


class ApiKeyPartnerDocumentationPublicationEvidenceTests(TestCase):
    def test_publication_evidence_ready_when_sanitized_delivery_is_confirmed(self):
        review = api_key_partner_documentation_publication_evidence_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-partner-documentation-publication-evidence-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["evidence"].version, "2026-05-26")
        self.assertEqual(review["evidence"].channel, "restricted-support-ticket")
        self.assertIn("API Key Partner Onboarding Closure Review", review["next_tracks"])

    def test_publication_evidence_blocks_without_execution_readiness(self):
        review = api_key_partner_documentation_publication_evidence_queries.get_review(
            **self._evidence_fields(),
            publication_confirmed=True,
            support_notified=True,
            activation_status_recorded=True,
            smoke_template_attached=True,
            redaction_confirmed=True,
            no_credential_shared=True,
            no_runtime_activation_performed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("execution:api-key-partner-documentation-execution-blocked", review["blockers"])
        self.assertIn("execution:onboarding:roi:governance:model-ready:missing", review["blockers"])

    def test_publication_evidence_blocks_without_required_evidence_fields(self):
        review = api_key_partner_documentation_publication_evidence_queries.get_review(
            **self._execution_flags(),
            publication_confirmed=True,
            support_notified=True,
            activation_status_recorded=True,
            smoke_template_attached=True,
            redaction_confirmed=True,
            no_credential_shared=True,
            no_runtime_activation_performed=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("published-version:missing", review["blockers"])
        self.assertIn("approved-channel:missing", review["blockers"])
        self.assertIn("evidence-reference:missing", review["blockers"])

    def test_publication_evidence_blocks_without_redaction_and_runtime_guards(self):
        review = api_key_partner_documentation_publication_evidence_queries.get_review(
            **self._execution_flags(),
            **self._evidence_fields(),
            publication_confirmed=True,
            support_notified=True,
            activation_status_recorded=True,
            smoke_template_attached=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("redaction-confirmed:missing", review["blockers"])
        self.assertIn("no-credential-shared:missing", review["blockers"])
        self.assertIn("no-runtime-activation-performed:missing", review["blockers"])

    def test_command_outputs_sanitized_publication_evidence(self):
        output = StringIO()

        call_command(
            "api_key_partner_documentation_publication_evidence",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("version=2026-05-26", value)
        self.assertIn("channel=restricted-support-ticket", value)
        self.assertIn("decision key=redaction status=guarded", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "api_key_partner_documentation_publication_evidence",
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

    def _evidence_fields(self) -> dict[str, str]:
        return {
            "published_version": "2026-05-26",
            "approved_channel": "restricted-support-ticket",
            "target_audience": "approved-partner",
            "tenant_reference": "tenant-ref-001",
            "published_at": "2026-05-26T12:00:00-03:00",
            "evidence_reference": "DOC-EVIDENCE-001",
        }

    def _ready_flags(self) -> dict[str, object]:
        return {
            **self._execution_flags(),
            **self._evidence_fields(),
            "publication_confirmed": True,
            "support_notified": True,
            "activation_status_recorded": True,
            "smoke_template_attached": True,
            "redaction_confirmed": True,
            "no_credential_shared": True,
            "no_runtime_activation_performed": True,
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
        )
