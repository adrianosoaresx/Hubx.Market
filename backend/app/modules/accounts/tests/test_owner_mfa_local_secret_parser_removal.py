from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_local_secret_parser_removal_execution_queries import (
    owner_mfa_local_secret_parser_removal_execution_queries,
)
from app.modules.accounts.application.owner_mfa_local_secret_parser_removal_queries import owner_mfa_local_secret_parser_removal_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaLocalSecretParserRemovalTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_review_ready_when_sweep_is_ready_and_local_env_is_disabled(self):
        tenant, owner = self._tenant_owner("parser-ready")
        self._factor(tenant=tenant, owner=owner, secret_reference="ref:owners/parser-ready/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_PARSER_READY_TOTP": self.secret}):
            result = owner_mfa_local_secret_parser_removal_queries.get_review()

        self.assertTrue(result["ready"])
        self.assertEqual(result["status"], "ready")
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Local Secret Parser Removal Execution Review", result["next_tracks"])

    @override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_review_blocks_when_sweep_has_local_plain_data(self):
        tenant, owner = self._tenant_owner("parser-local")
        self._factor(tenant=tenant, owner=owner, secret_reference=f"plain:{self.secret}")

        result = owner_mfa_local_secret_parser_removal_queries.get_review()

        self.assertFalse(result["ready"])
        self.assertIn(f"tenant-{tenant.id}:local-plain-factors-present", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_review_blocks_when_local_env_is_reenabled(self):
        tenant, owner = self._tenant_owner("parser-env")
        self._factor(tenant=tenant, owner=owner, secret_reference="ref:owners/parser-env/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_PARSER_ENV_TOTP": self.secret}):
            result = owner_mfa_local_secret_parser_removal_queries.get_review()

        self.assertFalse(result["ready"])
        self.assertIn("local-secret-env-enabled", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_command_outputs_surfaces_plan_and_rollback(self):
        tenant, owner = self._tenant_owner("parser-command")
        self._factor(tenant=tenant, owner=owner, secret_reference="ref:owners/parser-command/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_PARSER_COMMAND_TOTP": self.secret}):
            call_command("owner_mfa_local_secret_parser_removal_review", stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("parser_surface=", output.getvalue())
        self.assertIn("removal_plan=", output.getvalue())
        self.assertIn("rollback=", output.getvalue())

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_execution_ready_when_review_ready_and_parser_probes_are_unsupported(self):
        tenant, owner = self._tenant_owner("parser-execute")
        self._factor(tenant=tenant, owner=owner, secret_reference="ref:owners/parser-execute/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_PARSER_EXECUTE_TOTP": self.secret}):
            result = owner_mfa_local_secret_parser_removal_execution_queries.get_evidence()

        self.assertTrue(result["ready"])
        self.assertEqual(result["local_probe"]["storage_mode"], "unsupported-local")
        self.assertEqual(result["legacy_probe"]["storage_mode"], "unsupported-local")
        self.assertFalse(result["local_probe"]["secret_returned"])
        self.assertIn("Owner MFA Vault/KMS Provider Review", result["next_tracks"])

    @override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_execution_blocks_when_review_still_has_local_data(self):
        tenant, owner = self._tenant_owner("parser-execute-local")
        self._factor(tenant=tenant, owner=owner, secret_reference=f"plain:{self.secret}")

        result = owner_mfa_local_secret_parser_removal_execution_queries.get_evidence()

        self.assertFalse(result["ready"])
        self.assertIn(f"tenant-{tenant.id}:local-plain-factors-present", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_", OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_execution_command_outputs_probe_and_rollback(self):
        tenant, owner = self._tenant_owner("parser-execute-command")
        self._factor(tenant=tenant, owner=owner, secret_reference="ref:owners/parser-execute-command/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_PARSER_EXECUTE_COMMAND_TOTP": self.secret}):
            call_command("owner_mfa_local_secret_parser_removal_execute", stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("local_probe=unsupported-local", output.getvalue())
        self.assertIn("decision key=parser-local-blocked", output.getvalue())
        self.assertIn("rollback=", output.getvalue())

    def _tenant_owner(self, slug: str) -> tuple[Tenant, OwnerUser]:
        tenant = Tenant.objects.create(name=slug, slug=slug, subdomain=slug)
        owner = OwnerUser.objects.create(tenant=tenant, email=f"owner@{slug}.hubx.market", role="owner")
        return tenant, owner

    def _factor(self, *, tenant: Tenant, owner: OwnerUser, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=tenant,
            owner=owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
