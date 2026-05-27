from __future__ import annotations

from io import StringIO

from django.contrib.auth.hashers import check_password
from django.core.management import call_command
from django.test import TestCase

from app.modules.accounts.application.owner_mfa_recovery_code_commands import owner_mfa_recovery_code_commands
from app.modules.accounts.models import OwnerMfaFactor, OwnerMfaRecoveryCode, OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaRecoveryCodeCommandServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Recovery", slug="mfa-recovery", subdomain="mfa-recovery")
        self.other_tenant = Tenant.objects.create(name="MFA Recovery Other", slug="mfa-recovery-other", subdomain="mfa-recovery-other")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.recovery@hubx.market", role="owner")

    def test_generate_codes_stores_hashes_and_returns_plain_codes_once(self):
        result = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=3,
            actor_label="admin@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "owner-mfa-recovery-codes-generated")
        self.assertEqual(len(result["codes"]), 3)
        stored_codes = list(OwnerMfaRecoveryCode.objects.order_by("id"))
        self.assertEqual(len(stored_codes), 3)
        self.assertNotIn(result["codes"][0], [code.code_hash for code in stored_codes])
        self.assertTrue(check_password(result["codes"][0].replace("-", ""), stored_codes[0].code_hash))
        self.assertTrue(
            OwnerMfaFactor.objects.filter(
                tenant=self.tenant,
                owner=self.owner,
                factor_type=OwnerMfaFactor.FactorType.RECOVERY_CODE,
                is_verified=True,
                is_active=True,
            ).exists()
        )
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_recovery_codes_generated").exists())

    def test_generate_codes_replaces_unused_codes(self):
        first = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=2,
            actor_role="owner",
        )
        second = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=4,
            actor_role="owner",
        )

        self.assertEqual(len(first["codes"]), 2)
        self.assertEqual(len(second["codes"]), 4)
        self.assertEqual(OwnerMfaRecoveryCode.objects.filter(tenant=self.tenant, owner=self.owner, used_at__isnull=True).count(), 4)

    def test_consume_code_marks_only_one_code_used(self):
        result = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=2,
            actor_role="owner",
        )

        consumed = owner_mfa_recovery_code_commands.consume_code(
            tenant_id=self.tenant.id,
            owner=self.owner,
            code=result["codes"][0],
        )
        consumed_again = owner_mfa_recovery_code_commands.consume_code(
            tenant_id=self.tenant.id,
            owner=self.owner,
            code=result["codes"][0],
        )

        self.assertIsNotNone(consumed)
        self.assertIsNone(consumed_again)
        self.assertEqual(OwnerMfaRecoveryCode.objects.filter(used_at__isnull=True).count(), 1)
        self.assertTrue(AuditLog.objects.filter(action="owner.mfa_recovery_code_used").exists())

    def test_generate_codes_is_tenant_scoped(self):
        result = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.other_tenant.id,
            owner_id=self.owner.id,
            actor_role="owner",
        )

        self.assertEqual(result["result"], "owner-mfa-owner-not-found")
        self.assertFalse(OwnerMfaRecoveryCode.objects.exists())

    def test_generate_codes_blocks_without_permission(self):
        result = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            actor_role="marketing",
        )

        self.assertEqual(result["result"], "owner-mfa-permission-denied")


class OwnerMfaRecoveryCodeManagementCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Recovery Mgmt", slug="mfa-recovery-mgmt", subdomain="mfa-recovery-mgmt")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.recovery.mgmt@hubx.market", role="owner")

    def test_generate_command_outputs_plain_codes_once(self):
        output = StringIO()

        call_command(
            "owner_mfa_recovery_codes",
            "generate",
            "--tenant-id",
            str(self.tenant.id),
            "--owner-id",
            str(self.owner.id),
            "--count",
            "2",
            stdout=output,
        )

        self.assertIn("owner-mfa-recovery-codes-generated", output.getvalue())
        self.assertEqual(output.getvalue().count("recovery_code="), 2)
