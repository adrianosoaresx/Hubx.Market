from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.accounts.application.ops_gate_readiness_queries import ops_gate_readiness_queries
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


class OpsGateReadinessQueryTests(TestCase):
    def test_readiness_passes_when_active_tenant_has_active_owner_with_user(self):
        tenant = Tenant.objects.create(name="Ready Tenant", slug="ready-tenant", subdomain="ready-tenant")
        OwnerUser.objects.create(tenant=tenant, email="owner@hubx.market", is_active=True)
        User.objects.create_user(username="owner", email="owner@hubx.market", password="secret")

        result = ops_gate_readiness_queries.get_readiness()

        self.assertEqual(result["result"], "ops-gate-ready")
        self.assertTrue(result["ready"])
        self.assertEqual(result["blocked_tenant_count"], 0)
        self.assertTrue(result["tenants"][0].ready)

    def test_readiness_blocks_tenant_without_active_owner_user(self):
        tenant = Tenant.objects.create(name="Blocked Tenant", slug="blocked-tenant", subdomain="blocked-tenant")
        OwnerUser.objects.create(tenant=tenant, email="missing@hubx.market", is_active=True)

        result = ops_gate_readiness_queries.get_readiness()
        tenant_result = result["tenants"][0]

        self.assertEqual(result["result"], "ops-gate-blocked")
        self.assertFalse(result["ready"])
        self.assertEqual(tenant_result.blockers, ("owner_without_django_user",))
        self.assertEqual(tenant_result.missing_user_emails, ("missing@hubx.market",))

    def test_readiness_blocks_inactive_or_ambiguous_django_users(self):
        tenant = Tenant.objects.create(name="Ambiguous Tenant", slug="ambiguous-tenant", subdomain="ambiguous-tenant")
        OwnerUser.objects.create(tenant=tenant, email="inactive@hubx.market", is_active=True)
        OwnerUser.objects.create(tenant=tenant, email="duplicate@hubx.market", is_active=True)
        User.objects.create_user(username="inactive", email="inactive@hubx.market", password="secret", is_active=False)
        User.objects.create_user(username="duplicate-a", email="duplicate@hubx.market", password="secret")
        User.objects.create_user(username="duplicate-b", email="duplicate@hubx.market", password="secret")

        result = ops_gate_readiness_queries.get_readiness()
        tenant_result = result["tenants"][0]

        self.assertFalse(result["ready"])
        self.assertIn("owner_with_inactive_django_user", tenant_result.blockers)
        self.assertIn("owner_email_ambiguous", tenant_result.blockers)
        self.assertEqual(tenant_result.inactive_user_emails, ("inactive@hubx.market",))
        self.assertEqual(tenant_result.duplicate_user_emails, ("duplicate@hubx.market",))


class OpsGateReadinessCommandTests(TestCase):
    def test_command_outputs_ready_summary(self):
        tenant = Tenant.objects.create(name="Ready Command", slug="ready-command", subdomain="ready-command")
        OwnerUser.objects.create(tenant=tenant, email="owner.command@hubx.market", is_active=True)
        User.objects.create_user(username="owner-command", email="owner.command@hubx.market", password="secret")
        output = StringIO()

        call_command("ops_auth_gate_readiness", stdout=output)

        self.assertIn("[READY] tenants=1 blocked_tenants=0", output.getvalue())
        self.assertIn("ready=true", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        Tenant.objects.create(name="Blocked Command", slug="blocked-command", subdomain="blocked-command")

        with self.assertRaises(CommandError):
            call_command("ops_auth_gate_readiness", "--fail-on-blockers", stdout=StringIO())
