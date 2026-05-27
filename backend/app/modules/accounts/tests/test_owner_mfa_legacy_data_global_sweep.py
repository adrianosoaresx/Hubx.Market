from __future__ import annotations

from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_legacy_data_global_sweep_queries import owner_mfa_legacy_data_global_sweep_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaLegacyDataGlobalSweepTests(TestCase):
    secret = "GEZDGNBVGY3TQOJQ"

    def test_sweep_is_watch_when_no_active_totp_exists(self):
        result = owner_mfa_legacy_data_global_sweep_queries.get_sweep()

        self.assertEqual(result["status"], "watch")
        self.assertEqual(result["tenant_count"], 0)
        self.assertEqual(result["blockers"], ())

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_sweep_ready_when_all_tenants_use_resolved_external_references(self):
        first_tenant, first_owner = self._tenant_owner("sweep-ready-a")
        second_tenant, second_owner = self._tenant_owner("sweep-ready-b")
        self._factor(tenant=first_tenant, owner=first_owner, secret_reference="ref:owners/a/totp")
        self._factor(tenant=second_tenant, owner=second_owner, secret_reference="ref:owners/b/totp")

        with patch.dict(
            "os.environ",
            {
                "OWNER_MFA_SECRET_OWNERS_A_TOTP": self.secret,
                "OWNER_MFA_SECRET_OWNERS_B_TOTP": self.secret,
            },
        ):
            result = owner_mfa_legacy_data_global_sweep_queries.get_sweep()

        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["ready"])
        self.assertEqual(result["totals"]["external_reference_count"], 2)
        self.assertEqual(result["totals"]["local_plain_count"], 0)

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_sweep_blocks_local_plain_and_unresolved_external_by_tenant(self):
        local_tenant, local_owner = self._tenant_owner("sweep-local")
        external_tenant, external_owner = self._tenant_owner("sweep-external")
        self._factor(tenant=local_tenant, owner=local_owner, secret_reference=f"plain:{self.secret}")
        self._factor(tenant=external_tenant, owner=external_owner, secret_reference="ref:owners/missing/totp")

        result = owner_mfa_legacy_data_global_sweep_queries.get_sweep()

        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["totals"]["blocked_tenant_count"], 2)
        self.assertIn(f"tenant-{local_tenant.id}:local-plain-factors-present", result["blockers"])
        self.assertIn(f"tenant-{external_tenant.id}:external-secret-unresolved", result["blockers"])

    @override_settings(OWNER_MFA_SECRET_PROVIDER="env", OWNER_MFA_SECRET_ENV_PREFIX="OWNER_MFA_SECRET_")
    def test_command_outputs_totals_and_next_tracks(self):
        tenant, owner = self._tenant_owner("sweep-command")
        self._factor(tenant=tenant, owner=owner, secret_reference="ref:owners/command/totp")
        output = StringIO()

        with patch.dict("os.environ", {"OWNER_MFA_SECRET_OWNERS_COMMAND_TOTP": self.secret}):
            call_command("owner_mfa_legacy_data_global_sweep", stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("external_reference=1", output.getvalue())
        self.assertIn("next_track=", output.getvalue())

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
