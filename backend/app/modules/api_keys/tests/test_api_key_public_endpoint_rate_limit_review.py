from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_endpoint_rate_limit_review_queries import (
    api_key_public_endpoint_rate_limit_review_queries,
)


class ApiKeyPublicEndpointRateLimitReviewTests(TestCase):
    def test_review_ready_recommends_fixed_window_policy(self):
        review = api_key_public_endpoint_rate_limit_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-endpoint-rate-limit-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["recommended_policy"]["algorithm"], "fixed-window")
        self.assertEqual(review["recommended_policy"]["scope"], "tenant+api_key+endpoint")
        self.assertEqual(review["recommended_policy"]["event"], "api_key.rate_limited")
        self.assertIn("API Key Public Endpoint Rate Limit Execution", review["next_tracks"])

    def test_review_blocks_without_rate_limit_key(self):
        flags = self._ready_flags()
        flags["rate_limit_key_available"] = False

        review = api_key_public_endpoint_rate_limit_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-rate-limit:rate_limit_key_available:missing", review["blockers"])

    def test_review_blocks_without_tenant_and_key_scope(self):
        flags = self._ready_flags()
        flags["per_tenant_and_key_required"] = False

        review = api_key_public_endpoint_rate_limit_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-rate-limit:per_tenant_and_key_required:missing", review["blockers"])

    def test_review_requires_retry_after_and_audit_event(self):
        flags = self._ready_flags()
        flags["retry_after_required"] = False
        flags["audit_event_required"] = False

        review = api_key_public_endpoint_rate_limit_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-endpoint-rate-limit:retry_after_required:missing", review["blockers"])
        self.assertIn("public-endpoint-rate-limit:audit_event_required:missing", review["blockers"])

    def test_command_outputs_policy_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_endpoint_rate_limit_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("recommended_policy algorithm=fixed-window scope=tenant+api_key+endpoint", value)
        self.assertIn("decision key=identity", value)
        self.assertIn("requirement key=observability", value)
        self.assertIn("out_of_scope=não implementar throttle nesta review", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_endpoint_rate_limit_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "public_endpoint_active": True,
            "rate_limit_key_available": True,
            "per_tenant_and_key_required": True,
            "cache_backend_required": True,
            "fixed_window_acceptable": True,
            "default_limit_config_required": True,
            "endpoint_override_config_required": True,
            "retry_after_required": True,
            "audit_event_required": True,
            "fail_closed_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--public-endpoint-active",
            "--rate-limit-key-available",
            "--per-tenant-and-key-required",
            "--cache-backend-required",
            "--fixed-window-acceptable",
            "--default-limit-config-required",
            "--endpoint-override-config-required",
            "--retry-after-required",
            "--audit-event-required",
            "--fail-closed-required",
        )
