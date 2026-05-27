from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.core.exceptions import ValidationError
from django.test import TestCase

from app.modules.accounts.application.owner_mfa_enrollment_queries import owner_mfa_enrollment_queries
from app.modules.accounts.application.owner_mfa_recovery_code_commands import owner_mfa_recovery_code_commands
from app.modules.accounts.models import OwnerMfaFactor, OwnerMfaRecoveryCode, OwnerUser
from app.modules.tenants.models import Tenant


class OwnerMfaEnrollmentQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Tenant", slug="mfa-tenant", subdomain="mfa-tenant")
        self.other_tenant = Tenant.objects.create(name="Other MFA", slug="other-mfa", subdomain="other-mfa")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.mfa@hubx.market", role="owner")

    def test_enrollment_requires_tenant(self):
        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=None)

        self.assertEqual(result["result"], "owner-mfa-enrollment-tenant-required")

    def test_enrollment_blocks_owner_without_verified_factor(self):
        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertIn(f"owner-{self.owner.id}:mfa-not-enrolled", result["blockers"])

    def test_enrollment_is_ready_with_verified_active_factor(self):
        OwnerMfaFactor.objects.create(
            tenant=self.tenant,
            owner=self.owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            is_verified=True,
        )

        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=self.tenant.id)

        self.assertTrue(result["ready"])
        self.assertEqual(result["enrolled_owner_count"], 1)

    def test_enrollment_is_ready_with_unused_recovery_code(self):
        owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=1,
            actor_role="owner",
        )

        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=self.tenant.id)

        self.assertTrue(result["ready"])
        self.assertEqual(result["enrolled_owner_count"], 1)

    def test_enrollment_blocks_recovery_factor_without_unused_code(self):
        generated = owner_mfa_recovery_code_commands.generate_codes(
            tenant_id=self.tenant.id,
            owner_id=self.owner.id,
            count=1,
            actor_role="owner",
        )
        owner_mfa_recovery_code_commands.consume_code(
            tenant_id=self.tenant.id,
            owner=self.owner,
            code=generated["codes"][0],
        )

        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertEqual(OwnerMfaRecoveryCode.objects.filter(used_at__isnull=True).count(), 0)

    def test_enrollment_is_tenant_scoped(self):
        other_owner = OwnerUser.objects.create(tenant=self.other_tenant, email="other.mfa@hubx.market", role="owner")
        OwnerMfaFactor.objects.create(
            tenant=self.other_tenant,
            owner=other_owner,
            factor_type=OwnerMfaFactor.FactorType.TOTP,
            provider_key="internal",
            is_verified=True,
        )

        result = owner_mfa_enrollment_queries.list_owner_enrollment(tenant_id=self.tenant.id)

        self.assertEqual(result["owner_count"], 1)
        self.assertFalse(result["ready"])

    def test_factor_rejects_cross_tenant_owner(self):
        with self.assertRaises(ValidationError):
            OwnerMfaFactor.objects.create(
                tenant=self.other_tenant,
                owner=self.owner,
                factor_type=OwnerMfaFactor.FactorType.TOTP,
                provider_key="internal",
            )


class OwnerMfaEnrollmentCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="MFA Command", slug="mfa-command", subdomain="mfa-command")
        self.owner = OwnerUser.objects.create(tenant=self.tenant, email="owner.command@hubx.market", role="owner")

    def test_command_outputs_owner_enrollment(self):
        output = StringIO()

        call_command("owner_mfa_enrollment_readiness", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[BLOCKED]", output.getvalue())
        self.assertIn("owner.command@hubx.market", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_enrollment_readiness",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
