from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.ops_gate_production_rollout_queries import ops_gate_production_rollout_queries
from app.modules.accounts.models import OwnerUser
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class OpsGateProductionRolloutQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Production Rollout Tenant",
            slug="production-rollout-tenant",
            subdomain="production-rollout-tenant",
            is_active=True,
        )
        OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market", is_active=True)
        User.objects.create_user(username="owner", email="owner@hubx.market", password="secret")

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_rollout_evidence_ready_when_gate_and_provider_are_ready(self):
        evidence = ops_gate_production_rollout_queries.get_rollout_evidence(tenant_id=self.tenant.id)

        self.assertEqual(evidence["result"], "ops-gate-production-ready")
        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["blockers"], ())
        self.assertEqual(evidence["tenants"][0]["notifications"].total, 0)

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_rollout_evidence_blocks_notification_failures_by_default(self):
        self._create_email_log(status=EmailLog.Status.FAILED)

        evidence = ops_gate_production_rollout_queries.get_rollout_evidence(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn(f"tenant-{self.tenant.id}:notification-failures-present", evidence["blockers"])
        self.assertEqual(evidence["tenants"][0]["notifications"].failed, 1)

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=False,
        NOTIFICATIONS_EMAIL_DRY_RUN=True,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        DEFAULT_FROM_EMAIL="",
    )
    def test_rollout_evidence_blocks_gate_and_provider_when_required(self):
        evidence = ops_gate_production_rollout_queries.get_rollout_evidence(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn("ops-gate-not-enabled", evidence["blockers"])
        self.assertIn("notification-provider-not-ready", evidence["blockers"])

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


class OpsGateProductionRolloutCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Production Rollout Command",
            slug="production-rollout-command",
            subdomain="production-rollout-command",
            is_active=True,
        )
        OwnerUser.objects.create(tenant=self.tenant, email="owner.command@hubx.market", is_active=True)
        User.objects.create_user(username="owner-command", email="owner.command@hubx.market", password="secret")

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_command_outputs_ready_evidence(self):
        output = StringIO()

        call_command("ops_gate_production_rollout", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("gate_enabled=true", output.getvalue())
        self.assertIn("email_failed=0", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "ops_gate_production_rollout",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
