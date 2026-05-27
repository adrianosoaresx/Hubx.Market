from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.application.owner_mfa_break_glass_readiness_queries import owner_mfa_break_glass_readiness_queries
from app.modules.accounts.application.owner_mfa_login_enforcement_readiness_queries import owner_mfa_login_enforcement_readiness_queries
from app.modules.accounts.application.owner_mfa_operational_closure_queries import owner_mfa_operational_closure_queries
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaOperationalReadinessTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Ops", slug="mfa-ops", subdomain="mfa-ops")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.ops.mfa@hubx.market", role="owner")
        OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            secret_reference="GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ",
            is_active=True,
            is_verified=True,
        )

    @override_settings(OWNER_MFA_BREAK_GLASS_ENABLED=False, OWNER_MFA_BREAK_GLASS_OWNER_EMAILS=())
    def test_break_glass_readiness_blocks_when_disabled(self):
        result = owner_mfa_break_glass_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn("break-glass-disabled", result["blockers"])

    @override_settings(
        OWNER_MFA_REQUIRED=True,
        OWNER_MFA_BREAK_GLASS_ENABLED=True,
        OWNER_MFA_BREAK_GLASS_OWNER_EMAILS=("owner.ops.mfa@hubx.market",),
    )
    def test_login_enforcement_readiness_is_ready_with_enrollment_and_break_glass(self):
        result = owner_mfa_login_enforcement_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertTrue(result["ready"])
        self.assertEqual(result["result"], "owner-mfa-login-enforcement-ready")

    @override_settings(
        OWNER_MFA_REQUIRED=True,
        OWNER_MFA_BREAK_GLASS_ENABLED=True,
        OWNER_MFA_BREAK_GLASS_OWNER_EMAILS=("owner.ops.mfa@hubx.market",),
    )
    def test_operational_closure_command_outputs_next_tracks(self):
        output = StringIO()

        call_command("owner_mfa_operational_closure", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=admin-surface", output.getvalue())
        self.assertIn("next_track=Owner MFA Secret Storage Hardening Review", output.getvalue())

    @override_settings(OWNER_MFA_BREAK_GLASS_ENABLED=True, OWNER_MFA_BREAK_GLASS_OWNER_EMAILS=("owner.ops.mfa@hubx.market",))
    def test_break_glass_command_outputs_ready_account(self):
        output = StringIO()

        call_command("owner_mfa_break_glass_readiness", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("active_account=owner.ops.mfa@hubx.market", output.getvalue())
