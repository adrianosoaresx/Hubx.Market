from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_expansion_review_queries import (
    api_key_public_endpoint_expansion_review_queries,
)


class ApiKeyPublicEndpointExpansionReviewTests(TestCase):
    def test_review_ready_recommends_product_detail_endpoint(self):
        review = api_key_public_endpoint_expansion_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-expansion-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["recommended_candidate"]["endpoint"], "GET /api/v1/catalog/products/<slug>/")
        self.assertEqual(review["recommended_candidate"]["scope"], "read:catalog")
        self.assertIn("API Key Public Product Detail Endpoint Contract Review", review["next_tracks"])

    def test_review_blocks_without_post_activation_or_candidate(self):
        flags = self._ready_flags()
        flags["post_activation_monitoring_ready"] = False
        flags["candidate_endpoint_identified"] = False

        review = api_key_public_endpoint_expansion_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-expansion:post_activation_monitoring_ready:missing", review["blockers"])
        self.assertIn("public-endpoint-expansion:candidate_endpoint_identified:missing", review["blockers"])

    def test_review_blocks_without_contract_and_privacy_guards(self):
        flags = self._ready_flags()
        flags["tenant_context_required"] = False
        flags["payload_contract_required"] = False
        flags["no_pii_required"] = False

        review = api_key_public_endpoint_expansion_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-expansion:tenant_context_required:missing", review["blockers"])
        self.assertIn("public-endpoint-expansion:payload_contract_required:missing", review["blockers"])
        self.assertIn("public-endpoint-expansion:no_pii_required:missing", review["blockers"])

    def test_command_outputs_expansion_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_expansion_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommended_candidate endpoint=GET /api/v1/catalog/products/<slug>/", value)
        self.assertIn("decision key=privacy status=guarded", value)
        self.assertIn("next_track=API Key Public Product Detail Endpoint Contract Review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_expansion_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "post_activation_monitoring_ready": True,
            "candidate_endpoint_identified": True,
            "read_only_required": True,
            "tenant_context_required": True,
            "explicit_scope_required": True,
            "rate_limit_required": True,
            "observability_required": True,
            "payload_contract_required": True,
            "no_pii_required": True,
            "no_cross_module_leak_required": True,
            "rollout_flag_required": True,
            "expansion_deferred_until_contract": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--post-activation-monitoring-ready",
            "--candidate-endpoint-identified",
            "--read-only-required",
            "--tenant-context-required",
            "--explicit-scope-required",
            "--rate-limit-required",
            "--observability-required",
            "--payload-contract-required",
            "--no-pii-required",
            "--no-cross-module-leak-required",
            "--rollout-flag-required",
            "--expansion-deferred-until-contract",
        )
