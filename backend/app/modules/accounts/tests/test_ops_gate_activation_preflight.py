from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.accounts.application.ops_gate_activation_preflight_queries import ops_gate_activation_preflight_queries
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


class OpsGateActivationPreflightQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Preflight Tenant",
            slug="preflight-tenant",
            subdomain="preflight-tenant",
            is_active=True,
        )

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=False)
    def test_preflight_ready_when_tenant_readiness_passes_and_gate_expected_disabled(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market", is_active=True)
        User.objects.create_user(username="owner", email="owner@hubx.market", password="secret")

        result = ops_gate_activation_preflight_queries.get_preflight(
            tenant_id=self.tenant.id,
            expected_gate_state="disabled",
        )

        self.assertEqual(result["result"], "ops-gate-activation-ready")
        self.assertTrue(result["ready"])
        self.assertEqual(result["blockers"], ())

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=False)
    def test_preflight_blocks_when_gate_expected_enabled_but_is_disabled(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market", is_active=True)
        User.objects.create_user(username="owner", email="owner@hubx.market", password="secret")

        result = ops_gate_activation_preflight_queries.get_preflight(
            tenant_id=self.tenant.id,
            expected_gate_state="enabled",
        )

        self.assertFalse(result["ready"])
        self.assertIn("ops-gate-not-enabled", result["blockers"])

    @override_settings(
        HUBX_OPS_AUTH_GATE_ENFORCED=False,
        NOTIFICATIONS_EMAIL_DRY_RUN=True,
        EMAIL_BACKEND="django.core.mail.backends.console.EmailBackend",
        DEFAULT_FROM_EMAIL="",
    )
    def test_preflight_blocks_when_real_email_delivery_is_required_but_provider_not_ready(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market", is_active=True)
        User.objects.create_user(username="owner", email="owner@hubx.market", password="secret")

        result = ops_gate_activation_preflight_queries.get_preflight(
            tenant_id=self.tenant.id,
            require_email_delivery=True,
        )

        self.assertFalse(result["ready"])
        self.assertIn("notification-provider-not-ready", result["blockers"])


class OpsGateActivationPreflightCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Preflight Command Tenant",
            slug="preflight-command-tenant",
            subdomain="preflight-command-tenant",
            is_active=True,
        )

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=False)
    def test_command_outputs_ready_summary(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner.command@hubx.market", is_active=True)
        User.objects.create_user(username="owner-command", email="owner.command@hubx.market", password="secret")
        output = StringIO()

        call_command(
            "ops_gate_activation_preflight",
            "--tenant-id",
            str(self.tenant.id),
            "--expect-gate",
            "disabled",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("gate_enabled=false", output.getvalue())
        self.assertIn("blocked_tenants=0", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "ops_gate_activation_preflight",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
