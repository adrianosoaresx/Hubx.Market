from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_runtime_authentication_contract_queries import (
    api_key_runtime_authentication_contract_queries,
)


class ApiKeyRuntimeAuthenticationContractTests(TestCase):
    def test_review_ready_when_all_runtime_signals_are_confirmed(self):
        review = api_key_runtime_authentication_contract_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-runtime-authentication-contract-ready")
        self.assertEqual(review["blockers"], ())
        self.assertIn("API Key Runtime Authentication Skeleton Execution", review["next_tracks"])

    def test_review_blocks_without_tenant_context(self):
        flags = self._ready_flags()
        flags["tenant_context_required"] = False

        review = api_key_runtime_authentication_contract_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("runtime-auth:tenant_context_required:missing", review["blockers"])
        self.assertIn("API Key Runtime Authentication Contract Follow-Up", review["next_tracks"])

    def test_review_requires_hash_verification(self):
        flags = self._ready_flags()
        flags["hash_verification_required"] = False

        review = api_key_runtime_authentication_contract_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("runtime-auth:hash_verification_required:missing", review["blockers"])

    def test_review_requires_scope_enforcement(self):
        flags = self._ready_flags()
        flags["scope_enforcement_required"] = False

        review = api_key_runtime_authentication_contract_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("runtime-auth:scope_enforcement_required:missing", review["blockers"])

    def test_command_outputs_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_runtime_authentication_contract",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("decision key=tenant-boundary", value)
        self.assertIn("requirement key=verification", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("hbx_", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_runtime_authentication_contract", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "api_key_model_available": True,
            "bearer_header_required": True,
            "tenant_context_required": True,
            "prefix_lookup_required": True,
            "hash_verification_required": True,
            "active_status_required": True,
            "scope_enforcement_required": True,
            "last_used_tracking_required": True,
            "auth_failure_audit_required": True,
            "rate_limit_boundary_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--api-key-model-available",
            "--bearer-header-required",
            "--tenant-context-required",
            "--prefix-lookup-required",
            "--hash-verification-required",
            "--active-status-required",
            "--scope-enforcement-required",
            "--last-used-tracking-required",
            "--auth-failure-audit-required",
            "--rate-limit-boundary-required",
        )
