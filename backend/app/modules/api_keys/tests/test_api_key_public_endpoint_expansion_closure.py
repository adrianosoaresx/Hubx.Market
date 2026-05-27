from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_expansion_closure_queries import (
    api_key_public_endpoint_expansion_closure_queries,
)


class ApiKeyPublicEndpointExpansionClosureTests(TestCase):
    def test_closure_ready_when_list_detail_and_observability_are_ready(self):
        closure = api_key_public_endpoint_expansion_closure_queries.get_closure(**self._ready_flags())

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["result"], "api-key-public-endpoint-expansion-closure-ready")
        self.assertEqual(closure["blockers"], ())
        self.assertTrue(closure["artifacts"]["catalog-detail-query"])
        self.assertTrue(closure["artifacts"]["catalog-detail-view"])
        self.assertTrue(closure["artifacts"]["detail-enabled-gauge"])
        self.assertIn("GET /api/v1/catalog/products/<slug>/", closure["closed_scope"])
        self.assertIn("API Key Governance Closure Review", closure["next_tracks"])

    def test_closure_blocks_without_readiness_signals(self):
        closure = api_key_public_endpoint_expansion_closure_queries.get_closure()

        self.assertFalse(closure["ready"])
        self.assertIn("list-endpoint-ready:missing", closure["blockers"])
        self.assertIn("detail-endpoint-ready:missing", closure["blockers"])
        self.assertIn("observability-ready:missing", closure["blockers"])
        self.assertIn("no-additional-endpoint-selected:missing", closure["blockers"])

    def test_command_outputs_closure_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_expansion_closure",
            "--list-endpoint-ready",
            "--detail-endpoint-ready",
            "--observability-ready",
            "--no-additional-endpoint-selected",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("artifact name=catalog-detail-query present=True", value)
        self.assertIn("closed_scope=GET /api/v1/catalog/products/<slug>/", value)
        self.assertIn("decision key=privacy status=guarded", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_expansion_closure", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "list_endpoint_ready": True,
            "detail_endpoint_ready": True,
            "observability_ready": True,
            "no_additional_endpoint_selected": True,
        }
