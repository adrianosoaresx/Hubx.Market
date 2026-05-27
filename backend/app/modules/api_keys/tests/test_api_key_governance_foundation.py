from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_governance_foundation_queries import (
    api_key_governance_foundation_queries,
)


class ApiKeyGovernanceFoundationTests(TestCase):
    def test_review_ready_when_all_governance_signals_are_confirmed(self):
        review = api_key_governance_foundation_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-governance-foundation-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("API Key Model Minimal Contract Execution", review["next_tracks"])

    def test_review_blocks_without_public_api_surface(self):
        flags = self._ready_flags()
        flags["public_api_surface_confirmed"] = False

        review = api_key_governance_foundation_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("governance:public_api_surface_confirmed:missing", review["blockers"])
        self.assertIn("API Key Public Surface Demand Review", review["next_tracks"])

    def test_review_requires_hashed_secret_storage(self):
        flags = self._ready_flags()
        flags["hashed_secret_storage_required"] = False

        review = api_key_governance_foundation_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("governance:hashed_secret_storage_required:missing", review["blockers"])

    def test_command_outputs_requirements_without_generating_secret(self):
        output = StringIO()

        call_command(
            "api_key_governance_foundation",
            *self._ready_args(),
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertIn("requirement key=model", output.getvalue())
        self.assertNotIn("secret=", output.getvalue())
        self.assertNotIn("plaintext", output.getvalue().lower())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_governance_foundation", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "public_api_surface_confirmed": True,
            "tenant_scoped_model_required": True,
            "hashed_secret_storage_required": True,
            "scoped_permissions_required": True,
            "revocation_required": True,
            "audit_events_required": True,
            "last_used_tracking_required": True,
            "rate_limit_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--public-api-surface-confirmed",
            "--tenant-scoped-model-required",
            "--hashed-secret-storage-required",
            "--scoped-permissions-required",
            "--revocation-required",
            "--audit-events-required",
            "--last-used-tracking-required",
            "--rate-limit-required",
        )
