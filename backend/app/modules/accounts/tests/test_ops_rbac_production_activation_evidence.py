from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.ops_rbac_production_activation_evidence_queries import (
    ops_rbac_production_activation_evidence_queries,
)
from app.modules.accounts.models import OwnerUser
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class OpsRbacProductionActivationEvidenceQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Production Activation Tenant",
            slug="rbac-production-activation-tenant",
            subdomain="rbac-production-activation-tenant",
            is_active=True,
        )

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_evidence_is_ready_when_rollout_and_rbac_are_ready(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.production@hubx.market", role="owner", is_active=True)
        User.objects.create_user(username="owner-production", email="owner.production@hubx.market", password="secret")

        evidence = ops_rbac_production_activation_evidence_queries.get_evidence(tenant_id=self.tenant.id)

        self.assertEqual(evidence["result"], "ops-rbac-production-activation-ready")
        self.assertTrue(evidence["ready"])
        self.assertEqual(evidence["blockers"], ())
        self.assertEqual(evidence["environment_label"], "production")
        self.assertEqual(evidence["manual_checks"][-1].key, "owner-access-metrics")
        self.assertIn("HUBX_OPS_AUTH_GATE_ENFORCED=0", evidence["rollback_steps"][0])

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_evidence_blocks_with_prefixed_rollout_and_rbac_blockers(self):
        OwnerUser.objects.create(tenant=self.tenant, email="viewer.production@hubx.market", role="viewer", is_active=True)
        User.objects.create_user(username="viewer-production", email="viewer.production@hubx.market", password="secret")
        self._create_email_log(status=EmailLog.Status.FAILED)

        evidence = ops_rbac_production_activation_evidence_queries.get_evidence(tenant_id=self.tenant.id)

        self.assertFalse(evidence["ready"])
        self.assertIn(f"rollout:tenant-{self.tenant.id}:notification-failures-present", evidence["blockers"])
        self.assertIn(f"rbac:tenant-{self.tenant.id}:no_active_full_admin_owner", evidence["blockers"])

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


class OpsRbacProductionActivationEvidenceCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="RBAC Production Activation Command",
            slug="rbac-production-activation-command",
            subdomain="rbac-production-activation-command",
            is_active=True,
        )

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=True,
        NOTIFICATIONS_EMAIL_DRY_RUN=False,
        EMAIL_BACKEND="django.core.mail.backends.smtp.EmailBackend",
        DEFAULT_FROM_EMAIL="no-reply@hubx.market",
    )
    def test_command_outputs_production_evidence_package(self):
        OwnerUser.objects.create(tenant=self.tenant, email="admin.production@hubx.market", role="admin", is_active=True)
        User.objects.create_user(username="admin-production", email="admin.production@hubx.market", password="secret")
        output = StringIO()

        call_command(
            "ops_rbac_production_activation_evidence",
            "--tenant-id",
            str(self.tenant.id),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY] environment=production", value)
        self.assertIn("command.rollout=python manage.py ops_gate_production_rollout", value)
        self.assertIn("command.rbac=python manage.py ops_rbac_production_readiness", value)
        self.assertIn("manual_check.owner-access-metrics", value)
        self.assertIn("rollback.1=setar HUBX_OPS_AUTH_GATE_ENFORCED=0", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "ops_rbac_production_activation_evidence",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
