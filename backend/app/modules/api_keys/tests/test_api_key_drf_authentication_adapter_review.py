from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_drf_authentication_adapter_review_queries import (
    api_key_drf_authentication_adapter_review_queries,
)


class ApiKeyDrfAuthenticationAdapterReviewTests(TestCase):
    def test_review_ready_when_all_adapter_boundaries_are_confirmed(self):
        review = api_key_drf_authentication_adapter_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-drf-authentication-adapter-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("API Key DRF Authentication Adapter Execution", review["next_tracks"])

    def test_review_blocks_when_global_drf_auth_is_not_forbidden(self):
        flags = self._ready_flags()
        flags["global_drf_auth_forbidden"] = False

        review = api_key_drf_authentication_adapter_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("drf-adapter:global_drf_auth_forbidden:missing", review["blockers"])
        self.assertIn("API Key DRF Authentication Adapter Follow-Up", review["next_tracks"])

    def test_review_blocks_without_per_view_opt_in(self):
        flags = self._ready_flags()
        flags["per_view_opt_in_required"] = False

        review = api_key_drf_authentication_adapter_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("drf-adapter:per_view_opt_in_required:missing", review["blockers"])

    def test_review_blocks_without_scope_mapping(self):
        flags = self._ready_flags()
        flags["required_scope_mapping_required"] = False

        review = api_key_drf_authentication_adapter_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("drf-adapter:required_scope_mapping_required:missing", review["blockers"])

    def test_command_outputs_requirements_without_implementing_adapter(self):
        output = StringIO()

        call_command(
            "api_key_drf_authentication_adapter_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("decision key=global-settings", value)
        self.assertIn("requirement key=principal", value)
        self.assertIn("out_of_scope=não implementar authentication class nesta review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_drf_authentication_adapter_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "runtime_service_available": True,
            "tenant_middleware_required": True,
            "per_view_opt_in_required": True,
            "global_drf_auth_forbidden": True,
            "required_scope_mapping_required": True,
            "safe_principal_required": True,
            "permission_class_required": True,
            "rate_limit_hook_required": True,
            "failure_response_contract_required": True,
            "no_public_endpoint_in_adapter": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--runtime-service-available",
            "--tenant-middleware-required",
            "--per-view-opt-in-required",
            "--global-drf-auth-forbidden",
            "--required-scope-mapping-required",
            "--safe-principal-required",
            "--permission-class-required",
            "--rate-limit-hook-required",
            "--failure-response-contract-required",
            "--no-public-endpoint-in-adapter",
        )
