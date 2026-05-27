from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.accounts.application.ops_rbac_post_production_monitoring_queries import (
    ops_rbac_post_production_monitoring_queries,
)
from app.modules.audit.models import AuditLog
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class OpsRbacPostProductionMonitoringQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Monitoring Tenant",
            slug="rbac-monitoring-tenant",
            subdomain="rbac-monitoring-tenant",
            is_active=True,
        )

    def test_snapshot_is_healthy_without_recent_signals(self):
        snapshot = ops_rbac_post_production_monitoring_queries.get_snapshot(tenant_id=self.tenant.id)

        self.assertEqual(snapshot["result"], "ops-rbac-post-production-healthy")
        self.assertTrue(snapshot["healthy"])
        self.assertEqual(snapshot["watch_signals"], ())
        self.assertEqual(snapshot["rollback_signals"], ())

    def test_snapshot_flags_watch_signal_for_permission_denied_threshold(self):
        for _ in range(3):
            AuditLog.objects.create(
                tenant=self.tenant,
                module="accounts",
                action="owner.ops_permission_denied",
                actor_label="owner@hubx.market",
            )

        snapshot = ops_rbac_post_production_monitoring_queries.get_snapshot(tenant_id=self.tenant.id)

        self.assertEqual(snapshot["status"], "watch")
        self.assertEqual(snapshot["watch_signals"][0].key, "owner.ops_permission_denied")
        self.assertEqual(snapshot["watch_signals"][0].count, 3)

    def test_snapshot_flags_rollback_signal_for_rate_limit_and_email_failure(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.login_rate_limited",
            actor_label="owner@hubx.market",
        )
        self._create_email_log(status=EmailLog.Status.FAILED)

        snapshot = ops_rbac_post_production_monitoring_queries.get_snapshot(tenant_id=self.tenant.id)

        self.assertEqual(snapshot["status"], "rollback")
        self.assertEqual({signal.key for signal in snapshot["rollback_signals"]}, {"owner.login_rate_limited", "owner.access.email_failed"})

    def _create_email_log(self, *, status: str):
        return EmailLog.objects.create(
            tenant=self.tenant,
            source_event="owner.invited",
            intent_key="owner.access.invite",
            audience="owner",
            entity_type="owner_user",
            entity_id="1",
            idempotency_key=f"{self.tenant.id}:owner.access.invite:owner_user:1",
            recipient_delivery_key=f"{self.tenant.id}:owner.access.invite:owner_user:1:email:owner@hubx.market",
            recipient_type="owner_user",
            recipient_id="1",
            recipient_email="owner@hubx.market",
            title="Acesso administrativo",
            status=status,
        )


class OpsRbacPostProductionMonitoringCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Monitoring Command",
            slug="rbac-monitoring-command",
            subdomain="rbac-monitoring-command",
            is_active=True,
        )

    def test_command_outputs_healthy_snapshot(self):
        output = StringIO()

        call_command("ops_rbac_post_production_monitoring", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[HEALTHY]", output.getvalue())
        self.assertIn("watch_signals=0", output.getvalue())
        self.assertIn("rollback_signals=0", output.getvalue())

    def test_command_can_fail_on_rollback_signal(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.login_rate_limited",
            actor_label="owner@hubx.market",
        )

        with self.assertRaises(CommandError):
            call_command(
                "ops_rbac_post_production_monitoring",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-rollback",
                stdout=StringIO(),
            )
