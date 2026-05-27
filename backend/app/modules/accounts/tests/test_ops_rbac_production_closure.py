from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.ops_rbac_production_closure_queries import ops_rbac_production_closure_queries
from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OpsRbacProductionClosureQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Closure Tenant",
            slug="rbac-closure-tenant",
            subdomain="rbac-closure-tenant",
            is_active=True,
        )

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_closure_is_ready_when_activation_and_monitoring_are_ready(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.closure@hubx.market", role="owner", is_active=True)
        User.objects.create_user(username="owner-closure", email="owner.closure@hubx.market", password="secret")

        closure = ops_rbac_production_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertEqual(closure["result"], "ops-rbac-production-closure-ready")
        self.assertTrue(closure["ready"])
        self.assertEqual(closure["blockers"], ())
        self.assertIn("Platform Owner MFA/SSO Review", closure["next_tracks"])

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_closure_is_watch_when_monitoring_has_watch_signal(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.watch@hubx.market", role="owner", is_active=True)
        User.objects.create_user(username="owner-watch", email="owner.watch@hubx.market", password="secret")
        for _ in range(3):
            AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.ops_permission_denied")

        closure = ops_rbac_production_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertEqual(closure["status"], "watch")
        self.assertFalse(closure["ready"])
        self.assertEqual(closure["blockers"], ())

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=False)
    def test_closure_blocks_when_activation_is_blocked(self):
        closure = ops_rbac_production_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            require_email_delivery=False,
            block_on_notification_failures=False,
        )

        self.assertEqual(closure["status"], "blocked")
        self.assertIn("activation:rollout:ops-gate-readiness-blocked", closure["blockers"])


class OpsRbacProductionClosureCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Closure Command",
            slug="rbac-closure-command",
            subdomain="rbac-closure-command",
            is_active=True,
        )

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_command_outputs_ready_closure(self):
        OwnerUser.objects.create(tenant=self.tenant, email="admin.closure@hubx.market", role="admin", is_active=True)
        User.objects.create_user(username="admin-closure", email="admin.closure@hubx.market", password="secret")
        output = StringIO()

        call_command("ops_rbac_production_closure", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=activation-evidence", output.getvalue())
        self.assertIn("residual_risk=", output.getvalue())
        self.assertIn("next_track=", output.getvalue())

    def test_command_can_fail_when_not_ready(self):
        with self.assertRaises(CommandError):
            call_command(
                "ops_rbac_production_closure",
                "--tenant-id",
                str(self.tenant.id),
                "--allow-email-dry-run",
                "--allow-notification-failures",
                "--fail-on-blockers",
                stdout=StringIO(),
            )
