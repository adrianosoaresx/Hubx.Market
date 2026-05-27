from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_provider_health_queries import owner_mfa_provider_health_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaProviderHealthTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Provider Health", slug="mfa-provider-health", subdomain="mfa-provider-health")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.provider.health@hubx.market", role="owner")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_health_is_healthy_when_external_reference_resolves(self):
        self._factor(secret_reference="ref:owners/1/totp")

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            result = owner_mfa_provider_health_queries.get_health(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "HEALTHY")
        self.assertEqual(result["external_reference_count"], 1)
        self.assertEqual(result["external_reference_unresolved_count"], 0)

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_health_is_critical_when_external_reference_is_missing(self):
        self._factor(secret_reference="ref:owners/1/totp")

        result = owner_mfa_provider_health_queries.get_health(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "CRITICAL")
        self.assertIn("external-reference-unresolved", result["signals"])

    def test_health_is_critical_when_provider_is_not_configured_for_external_reference(self):
        self._factor(secret_reference="ref:owners/1/totp")

        result = owner_mfa_provider_health_queries.get_health(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "CRITICAL")
        self.assertIn("provider-not-configured", result["signals"])

    def test_health_is_watch_when_local_plain_still_exists(self):
        self._factor(secret_reference=f"plain:{self.secret}")

        result = owner_mfa_provider_health_queries.get_health(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "WATCH")
        self.assertIn("local-plain-still-present", result["signals"])

    def test_health_is_watch_when_no_totp_external_reference_exists(self):
        result = owner_mfa_provider_health_queries.get_health(tenant_id=self.tenant.id)

        self.assertEqual(result["status"], "WATCH")
        self.assertIn("no-external-reference-factors", result["signals"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_command_outputs_status_and_counts(self):
        self._factor(secret_reference="ref:owners/1/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": self.secret}):
            call_command("owner_mfa_provider_health", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[HEALTHY]", output.getvalue())
        self.assertIn("external_reference=1", output.getvalue())
        self.assertIn("runbook=", output.getvalue())

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
