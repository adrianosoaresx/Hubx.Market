from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_secret_storage import owner_mfa_secret_storage
from app.modules.accounts.application.owner_mfa_secret_storage_readiness_queries import owner_mfa_secret_storage_readiness_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaSecretStorageTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Secret", slug="mfa-secret", subdomain="mfa-secret")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.secret@hubx.market", role="owner")

    def test_resolver_blocks_plain_prefix_as_unsupported_local(self):
        resolution = owner_mfa_secret_storage.resolve("plain:GEZDGNBVGY3TQOJQ")

        self.assertFalse(resolution.ready)
        self.assertEqual(resolution.storage_mode, "unsupported-local")
        self.assertEqual(resolution.secret, "")
        self.assertEqual(resolution.result, "owner-mfa-secret-local-unsupported")

    def test_resolver_classifies_external_reference_as_unresolved(self):
        resolution = owner_mfa_secret_storage.resolve("ref:owners/1/totp")

        self.assertFalse(resolution.ready)
        self.assertEqual(resolution.storage_mode, "external-reference")
        self.assertEqual(resolution.reference, "owners/1/totp")

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_resolver_resolves_external_reference_from_env_provider(self):
        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": "GEZDGNBVGY3TQOJQ"}):
            resolution = owner_mfa_secret_storage.resolve("ref:owners/1/totp")

        self.assertTrue(resolution.ready)
        self.assertEqual(resolution.storage_mode, "external-reference")
        self.assertEqual(resolution.secret, "GEZDGNBVGY3TQOJQ")
        self.assertEqual(resolution.result, "owner-mfa-secret-provider-env-ready")

    @override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_readiness_blocks_local_plain_even_when_env_is_allowed(self):
        factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference="plain:GEZDGNBVGY3TQOJQ",
            is_active=True,
            is_verified=True,
        )

        result = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertEqual(result["local_plain_count"], 1)
        self.assertIn(f"factor-{factor.id}:local-secret-unsupported", result["blockers"])

    @override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False)
    def test_readiness_blocks_local_plain_when_disabled(self):
        factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference="GEZDGNBVGY3TQOJQ",
            is_active=True,
            is_verified=True,
        )

        result = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn(f"factor-{factor.id}:local-secret-unsupported", result["blockers"])

    def test_readiness_blocks_external_reference_until_provider_exists(self):
        factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="vault",
            secret_reference="ref:owners/1/totp",
            is_active=True,
            is_verified=True,
        )

        result = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn(f"factor-{factor.id}:external-secret-unresolved", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_readiness_allows_external_reference_when_env_provider_resolves(self):
        OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="env",
            secret_reference="ref:owners/1/totp",
            is_active=True,
            is_verified=True,
        )

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_1_TOTP": "GEZDGNBVGY3TQOJQ"}):
            result = owner_mfa_secret_storage_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertTrue(result["ready"])
        self.assertEqual(result["external_reference_count"], 1)

    @override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)
    def test_command_outputs_counts(self):
        OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference="GEZDGNBVGY3TQOJQ",
            is_active=True,
            is_verified=True,
        )
        output = StringIO()

        call_command("owner_mfa_secret_storage_readiness", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[BLOCKED]", output.getvalue())
        self.assertIn("local_plain=1", output.getvalue())
