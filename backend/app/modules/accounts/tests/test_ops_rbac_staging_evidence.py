from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.ops_rbac_staging_evidence_queries import ops_rbac_staging_evidence_queries
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


class OpsRbacStagingEvidenceQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Staging Tenant",
            slug="rbac-staging-tenant",
            subdomain="rbac-staging-tenant",
            is_active=True,
        )

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_evidence_is_ready_when_preflight_and_rbac_are_ready(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.staging@hubx.market", role="owner", is_active=True)
        User.objects.create_user(username="owner-staging", email="owner.staging@hubx.market", password="secret")

        evidence = ops_rbac_staging_evidence_queries.get_evidence(tenant_id=self.tenant.id)

        self.assertEqual(evidence["result"], "ops-rbac-staging-evidence-ready")
        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["blockers"], ())
        self.assertEqual(evidence["environment_label"], "staging")
        self.assertEqual(evidence["manual_checks"][0].key, "owner-dashboard")
        self.assertIn("HUBX_OPS_AUTH_GATE_ENFORCED=0", evidence["rollback_steps"][0])

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=False)
    def test_evidence_blocks_with_prefixed_blockers(self):
        OwnerUser.objects.create(tenant=self.tenant, email="viewer.staging@hubx.market", role="viewer", is_active=True)
        User.objects.create_user(username="viewer-staging", email="viewer.staging@hubx.market", password="secret")

        evidence = ops_rbac_staging_evidence_queries.get_evidence(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn("preflight:ops-gate-not-enabled", evidence["blockers"])
        self.assertIn("rbac:ops-gate-not-enabled", evidence["blockers"])
        self.assertIn(f"rbac:tenant-{self.tenant.id}:no_active_full_admin_owner", evidence["blockers"])


class OpsRbacStagingEvidenceCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Staging Command",
            slug="rbac-staging-command",
            subdomain="rbac-staging-command",
            is_active=True,
        )

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_command_outputs_staging_evidence_package(self):
        OwnerUser.objects.create(tenant=self.tenant, email="admin.staging@hubx.market", role="admin", is_active=True)
        User.objects.create_user(username="admin-staging", email="admin.staging@hubx.market", password="secret")
        output = StringIO()

        call_command(
            "ops_rbac_staging_activation_evidence",
            "--tenant-id",
            str(self.tenant.id),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY] environment=staging", value)
        self.assertIn("command.preflight=python manage.py ops_gate_activation_preflight", value)
        self.assertIn("command.rbac=python manage.py ops_rbac_production_readiness", value)
        self.assertIn("manual_check.owner-dashboard", value)
        self.assertIn("rollback.1=setar HUBX_OPS_AUTH_GATE_ENFORCED=0", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "ops_rbac_staging_activation_evidence",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
