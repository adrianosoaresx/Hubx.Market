from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_observability_closure_queries import (
    api_key_public_endpoint_observability_closure_queries,
)


class ApiKeyPublicEndpointObservabilityClosureTests(TestCase):
    def test_closure_ready_when_artifacts_and_rollout_are_ready(self):
        closure = api_key_public_endpoint_observability_closure_queries.get_closure(rollout_ready=True)

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["status"], "ready")
        self.assertEqual(closure["blockers"], ())
        self.assertTrue(closure["artifacts"]["metrics-service"])
        self.assertTrue(closure["artifacts"]["metrics-endpoint"])
        self.assertTrue(closure["artifacts"]["grafana-dashboard"])
        self.assertTrue(closure["artifacts"]["prometheus-alert-rules"])
        self.assertTrue(closure["artifacts"]["observability-runbook"])
        self.assertIn("API Key Public Endpoint Production Rollout Review", closure["next_tracks"])

    def test_closure_blocks_without_rollout_ready_signal(self):
        closure = api_key_public_endpoint_observability_closure_queries.get_closure()

        self.assertFalse(closure["ready"])
        self.assertEqual(closure["status"], "blocked")
        self.assertIn("rollout-ready:missing", closure["blockers"])

    def test_command_outputs_artifacts_and_residual_risks_without_sensitive_material(self):
        output = StringIO()

        call_command("api_key_public_endpoint_observability_closure", "--rollout-ready", stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("artifact name=metrics-service present=True", value)
        self.assertIn("artifact name=grafana-dashboard present=True", value)
        self.assertIn("artifact name=prometheus-alert-rules present=True", value)
        self.assertIn("decision key=sensitive-data status=guarded", value)
        self.assertIn("residual_risk=", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_observability_closure", "--fail-on-blockers", stdout=StringIO())
