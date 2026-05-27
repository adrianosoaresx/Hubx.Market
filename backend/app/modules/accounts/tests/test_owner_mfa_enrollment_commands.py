from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.accounts.application.owner_mfa_enrollment_commands import owner_mfa_enrollment_commands
from app.modules.accounts.models import OwnerMfaFactor, OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaEnrollmentCommandServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Commands", slug="mfa-commands", subdomain="mfa-commands")
        self.other_tenant = Tenant.objects.create(name="MFA Other", slug="mfa-other", subdomain="mfa-other")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa.commands@hubx.market", role="owner")

    def test_register_factor_creates_pending_factor_and_audit_event(self):
        result = owner_mfa_enrollment_commands.register_factor(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            actor_label="admin@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "owner-mfa-factor-registered")
        factor = OwnerMfaFactor.objects.get()
        self.assertEqual(factor.tenant, self.tenant)
        self.assertEqual(factor.owner, self.owner)
        self.assertFalse(factor.is_verified)
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_factor_registered").exists())

    def test_register_factor_is_tenant_scoped(self):
        result = owner_mfa_enrollment_commands.register_factor(
            tenant_id=self.other_tenant.id,
            owner_id=self.owner.id,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            actor_role="owner",
        )

        self.assertEqual(result["result"], "owner-mfa-owner-not-found")
        self.assertFalse(OwnerMfaFactor.objects.exists())

    def test_register_factor_blocks_without_permission(self):
        result = owner_mfa_enrollment_commands.register_factor(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            actor_role="marketing",
        )

        self.assertEqual(result["result"], "owner-mfa-permission-denied")

    def test_deactivate_factor_records_audit_event(self):
        factor = OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            is_active=True,
        )

        result = owner_mfa_enrollment_commands.deactivate_factor(
            tenant_id=self.tenant.id,
            factor_id=factor.id,
            actor_label="admin@hubx.market",
            actor_role="owner",
        )

        factor.refresh_from_db()
        self.assertEqual(result["result"], "owner-mfa-factor-deactivated")
        self.assertFalse(factor.is_active)
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_factor_deactivated").exists())


class OwnerMfaFactorManagementCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Mgmt", slug="mfa-mgmt", subdomain="mfa-mgmt")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mgmt@hubx.market", role="owner")

    def test_register_command_outputs_result(self):
        output = StringIO()

        call_command(
            "owner_mfa_factor",
            "register",
            "--tenant-id",
            str(self.tenant.id),
            "--owner-id",
            str(self.owner.id),
            stdout=output,
        )

        self.assertIn("owner-mfa-factor-registered", output.getvalue())
