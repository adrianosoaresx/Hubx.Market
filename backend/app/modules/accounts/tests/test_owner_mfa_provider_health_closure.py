from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_provider_health_closure_queries import owner_mfa_provider_health_closure_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaProviderHealthClosureTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Provider Closure", slug="mfa-provider-closure", subdomain="mfa-provider-closure")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.provider.closure@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_closure_ready_when_health_and_artifacts_are_ready(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())
        self.assertIn("Owner MFA Vault/KMS Provider Review", result["next_tracks"])

    def test_closure_watch_when_only_local_plain_remains(self):
        self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "watch")
        self.assertFalse(result["ready"])
        self.assertEqual(result["blockers"], ())

    def test_closure_blocks_when_provider_health_is_critical(self):
        self._factor(secret_reference="ref:owners/1/totp")

        result = owner_mfa_provider_health_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "blocked")
        self.assertTrue(any(blocker.startswith("health:") for blocker in result["blockers"]))

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_command_outputs_decisions_and_residual_risks(self):
        self._factor(secret_reference="ref:owners/1/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            call_command("owner_mfa_provider_health_closure", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=provider-health", output.getvalue())
        self.assertIn("artifact name=grafana-dashboard present=True", output.getvalue())
        self.assertIn("residual_risk=", output.getvalue())

    def _factor(self, *, secret_reference: str) -> OwnerMfaFactor:
        return OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference=secret_reference,
            is_active=True,
            is_verified=True,
        )
