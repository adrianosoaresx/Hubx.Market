from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.accounts.application.initial_owner_provisioning_commands import initial_owner_provisioning_commands
from app.modules.accounts.application.ops_gate_readiness_queries import ops_gate_readiness_queries
from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class InitialOwnerProvisioningCommandServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Provision Tenant",
            slug="provision-tenant",
            subdomain="provision-tenant",
            is_active=True,
        )

    def test_provisions_owner_and_user_then_readiness_passes(self):
        result = initial_owner_provisioning_commands.provision_initial_owner(
            tenant_id=self.tenant.id,
            email="first.owner@hubx.market",
            full_name="First Owner",
            actor_label="test",
        )

        self.assertEqual(result["result"], "initial-owner-provisioned")
        owner = OwnerUser.objects.get(tenant=self.tenant, email="first.owner@hubx.market")
        user = User.objects.get(email="first.owner@hubx.market")
        self.assertTrue(owner.is_active)
        self.assertEqual(owner.role, "owner")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.initial_provisioned",
                entity_id=str(owner.id),
            ).exists()
        )

        readiness = ops_gate_readiness_queries.get_readiness(tenant_id=self.tenant.id)
        self.assertTrue(readiness["ready"])

    def test_provisioning_is_idempotent_for_existing_owner_and_user(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="existing.owner@hubx.market",
            role="owner",
            is_active=True,
            receives_notifications=True,
        )
        User.objects.create_user(username="existing-owner", email="existing.owner@hubx.market", password="secret")

        result = initial_owner_provisioning_commands.provision_initial_owner(
            tenant_id=self.tenant.id,
            email="existing.owner@hubx.market",
        )

        self.assertEqual(result["result"], "initial-owner-provisioned")
        self.assertFalse(result["owner"]["created"])
        self.assertFalse(result["user"]["created"])
        self.assertEqual(OwnerUser.objects.filter(tenant=self.tenant, email="existing.owner@hubx.market").count(), 1)
        self.assertEqual(User.objects.filter(email="existing.owner@hubx.market").count(), 1)

    def test_dry_run_does_not_persist_owner_or_user(self):
        result = initial_owner_provisioning_commands.provision_initial_owner(
            tenant_id=self.tenant.id,
            email="dry.run@hubx.market",
            dry_run=True,
        )

        self.assertEqual(result["result"], "initial-owner-dry-run")
        self.assertFalse(OwnerUser.objects.filter(email="dry.run@hubx.market").exists())
        self.assertFalse(User.objects.filter(email="dry.run@hubx.market").exists())

    def test_blocks_ambiguous_django_user_email(self):
        User.objects.create_user(username="duplicate-a", email="duplicate@hubx.market", password="secret")
        User.objects.create_user(username="duplicate-b", email="duplicate@hubx.market", password="secret")

        result = initial_owner_provisioning_commands.provision_initial_owner(
            tenant_id=self.tenant.id,
            email="duplicate@hubx.market",
        )

        self.assertEqual(result["result"], "initial-owner-ambiguous-user")
        self.assertFalse(OwnerUser.objects.filter(email="duplicate@hubx.market").exists())


class ProvisionInitialOwnerCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Provision CLI Tenant",
            slug="provision-cli-tenant",
            subdomain="provision-cli-tenant",
            is_active=True,
        )

    def test_command_outputs_provisioned_summary(self):
        output = StringIO()

        call_command(
            "provision_initial_owner",
            "--tenant-id",
            str(self.tenant.id),
            "--email",
            "cli.owner@hubx.market",
            "--full-name",
            "CLI Owner",
            stdout=output,
        )

        self.assertIn("[initial-owner-provisioned]", output.getvalue())
        self.assertTrue(OwnerUser.objects.filter(tenant=self.tenant, email="cli.owner@hubx.market").exists())
        self.assertTrue(User.objects.filter(email="cli.owner@hubx.market").exists())

    def test_command_dry_run_outputs_without_persisting(self):
        output = StringIO()

        call_command(
            "provision_initial_owner",
            "--tenant-id",
            str(self.tenant.id),
            "--email",
            "dry.cli@hubx.market",
            "--dry-run",
            stdout=output,
        )

        self.assertIn("[initial-owner-dry-run]", output.getvalue())
        self.assertFalse(OwnerUser.objects.filter(email="dry.cli@hubx.market").exists())

    def test_command_raises_for_invalid_email(self):
        with self.assertRaises(CommandError):
            call_command(
                "provision_initial_owner",
                "--tenant-id",
                str(self.tenant.id),
                "--email",
                "invalid",
                stdout=StringIO(),
            )
