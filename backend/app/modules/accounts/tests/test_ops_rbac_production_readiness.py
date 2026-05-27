from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.ops_rbac_production_readiness_queries import ops_rbac_production_readiness_queries
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


class OpsRbacProductionReadinessQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Production Tenant",
            slug="rbac-production-tenant",
            subdomain="rbac-production-tenant",
            is_active=True,
        )

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_readiness_is_ready_with_active_full_admin_owner(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.rbac@hubx.market", role="owner", is_active=True)
        User.objects.create_user(username="owner-rbac", email="owner.rbac@hubx.market", password="secret")

        evidence = ops_rbac_production_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertEqual(evidence["result"], "ops-rbac-production-ready")
        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["blockers"], ())
        self.assertIn("owners.manage", evidence["required_permissions"])

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_readiness_blocks_tenant_without_full_admin_owner(self):
        OwnerUser.objects.create(tenant=self.tenant, email="viewer.rbac@hubx.market", role="viewer", is_active=True)
        User.objects.create_user(username="viewer-rbac", email="viewer.rbac@hubx.market", password="secret")

        evidence = ops_rbac_production_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn(f"tenant-{self.tenant.id}:no_active_full_admin_owner", evidence["blockers"])
        self.assertEqual(evidence["tenants"][0].blockers, ("no_active_full_admin_owner",))

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_readiness_blocks_unknown_active_role(self):
        OwnerUser.objects.create(tenant=self.tenant, email="mystery.rbac@hubx.market", role="mystery", is_active=True)

        evidence = ops_rbac_production_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn(f"tenant-{self.tenant.id}:unknown_owner_role", evidence["blockers"])
        self.assertEqual(evidence["tenants"][0].unknown_roles, ("mystery",))

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=False)
    def test_readiness_blocks_when_gate_expected_enabled(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.rbac@hubx.market", role="owner", is_active=True)
        User.objects.create_user(username="owner-rbac", email="owner.rbac@hubx.market", password="secret")

        evidence = ops_rbac_production_readiness_queries.get_readiness(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn("ops-gate-not-enabled", evidence["blockers"])


class OpsRbacProductionReadinessCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Production Command",
            slug="rbac-production-command",
            subdomain="rbac-production-command",
            is_active=True,
        )
        OwnerUser.objects.create(tenant=self.tenant, email="owner.command@hubx.market", role="admin", is_active=True)
        User.objects.create_user(username="owner-command", email="owner.command@hubx.market", password="secret")

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_command_outputs_ready_evidence(self):
        output = StringIO()

        call_command("ops_rbac_production_readiness", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("gate_enabled=true", output.getvalue())
        self.assertIn("full_admin_count=1", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "ops_rbac_production_readiness",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
