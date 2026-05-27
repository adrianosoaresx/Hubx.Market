from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_pilot_review_queries import (
    api_key_public_endpoint_pilot_review_queries,
)


class ApiKeyPublicEndpointPilotReviewTests(TestCase):
    def test_review_ready_recommends_catalog_read_only_pilot(self):
        review = api_key_public_endpoint_pilot_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-pilot-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["recommended_pilot"]["module"], "catalog")
        self.assertEqual(review["recommended_pilot"]["endpoint"], "/api/v1/catalog/products/")
        self.assertEqual(review["recommended_pilot"]["scope"], "read:catalog")
        self.assertIn("API Key Public Catalog Products Endpoint Execution", review["next_tracks"])

    def test_review_blocks_when_endpoint_is_not_read_only(self):
        flags = self._ready_flags()
        flags["pilot_endpoint_read_only"] = False

        review = api_key_public_endpoint_pilot_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-pilot:pilot_endpoint_read_only:missing", review["blockers"])

    def test_review_blocks_without_safe_payload_and_no_pii(self):
        flags = self._ready_flags()
        flags["safe_payload_required"] = False
        flags["no_pii_required"] = False

        review = api_key_public_endpoint_pilot_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-pilot:safe_payload_required:missing", review["blockers"])
        self.assertIn("public-endpoint-pilot:no_pii_required:missing", review["blockers"])

    def test_review_blocks_if_ops_reuse_is_not_forbidden(self):
        flags = self._ready_flags()
        flags["no_admin_ops_reuse_required"] = False

        review = api_key_public_endpoint_pilot_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-pilot:no_admin_ops_reuse_required:missing", review["blockers"])

    def test_command_outputs_recommended_pilot_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_pilot_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommended_pilot module=catalog method=GET endpoint=/api/v1/catalog/products/ scope=read:catalog", value)
        self.assertIn("decision key=pilot-surface", value)
        self.assertIn("out_of_scope=não expor pedidos, clientes, pagamentos ou dados pessoais", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_pilot_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "drf_adapter_available": True,
            "pilot_endpoint_read_only": True,
            "tenant_context_required": True,
            "explicit_scope_required": True,
            "rate_limit_plan_required": True,
            "safe_payload_required": True,
            "no_pii_required": True,
            "no_admin_ops_reuse_required": True,
            "versioned_url_required": True,
            "rollout_flag_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--drf-adapter-available",
            "--pilot-endpoint-read-only",
            "--tenant-context-required",
            "--explicit-scope-required",
            "--rate-limit-plan-required",
            "--safe-payload-required",
            "--no-pii-required",
            "--no-admin-ops-reuse-required",
            "--versioned-url-required",
            "--rollout-flag-required",
        )
