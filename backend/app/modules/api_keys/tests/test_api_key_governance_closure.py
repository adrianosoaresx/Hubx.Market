from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_governance_closure_queries import api_key_governance_closure_queries


class ApiKeyGovernanceClosureTests(TestCase):
    def test_closure_ready_when_governance_track_is_complete(self):
        closure = api_key_governance_closure_queries.get_closure(**self._ready_flags())

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["result"], "api-key-governance-closure-ready")
        self.assertEqual(closure["blockers"], ())
        self.assertTrue(closure["artifacts"]["api-key-model"])
        self.assertTrue(closure["artifacts"]["catalog-list-endpoint"])
        self.assertTrue(closure["artifacts"]["catalog-detail-endpoint"])
        self.assertTrue(closure["artifacts"]["grafana-dashboard"])
        self.assertIn("System ROI Re-Selection Review", closure["next_tracks"])

    def test_closure_blocks_without_required_ready_signals(self):
        closure = api_key_governance_closure_queries.get_closure()

        self.assertFalse(closure["ready"])
        self.assertIn("model-ready:missing", closure["blockers"])
        self.assertIn("runtime-auth-ready:missing", closure["blockers"])
        self.assertIn("public-endpoints-ready:missing", closure["blockers"])
        self.assertIn("no-secret-exposure-confirmed:missing", closure["blockers"])

    def test_command_outputs_closure_without_sensitive_material(self):
        output = StringIO()

        call_command("api_key_governance_closure", *self._ready_args(), stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("artifact name=api-key-model present=True", value)
        self.assertIn("closed_scope=GET /api/v1/catalog/products/<slug>/", value)
        self.assertIn("decision key=sensitive-data status=guarded", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_governance_closure", "--fail-on-blockers", stdout=StringIO())

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
