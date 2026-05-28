from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.tenants.application.system_template_regression_smoke import (
    SystemTemplateSmokeTarget,
    system_template_regression_smoke,
)
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class SystemTemplateRegressionSmokeTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Smoke Demo",
            slug="hubx-smoke-demo",
            subdomain="hubx-smoke-demo",
            is_active=True,
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def test_smoke_passes_for_storefront_and_admin_templates(self):
        payload = system_template_regression_smoke.run(client=self.client, host=self.host)

        self.assertTrue(payload["ready"])
        self.assertEqual(payload["result"], "system-template-regression-smoke-ready")
        self.assertEqual([result.key for result in payload["results"]], [
            "storefront-home-nav",
            "storefront-catalog-list",
            "customer-login-form",
            "customer-orders-nav-target",
            "ops-dashboard",
            "platform-onboarding-list",
            "platform-tenants-list",
        ])
        self.assertFalse(payload["blockers"])
        self.assertIn("System Validation Pass 2 — Browser Smoke Evidence", payload["next_tracks"])

    def test_smoke_blocks_when_legacy_orders_link_is_present(self):
        target = SystemTemplateSmokeTarget(
            key="legacy-orders-link",
            path="/",
            expected_status=200,
            markers=("Hubx Smoke Demo",),
            forbidden_markers=('href="/orders/"', 'href="/catalog/"'),
        )

        payload = system_template_regression_smoke.run(client=self.client, host=self.host, targets=(target,))

        self.assertFalse(payload["ready"])
        self.assertIn('system-template-regression:legacy-orders-link:forbidden:href="/catalog/"', payload["blockers"])

    def test_smoke_blocks_when_marker_is_missing(self):
        target = SystemTemplateSmokeTarget(
            key="missing-marker",
            path="/accounts/login/",
            expected_status=200,
            markers=("Marcador que não existe",),
        )

        payload = system_template_regression_smoke.run(client=self.client, host=self.host, targets=(target,))

        self.assertFalse(payload["ready"])
        self.assertIn("system-template-regression:missing-marker:missing:Marcador que não existe", payload["blockers"])

    def test_management_command_outputs_smoke_targets(self):
        output = StringIO()

        call_command("system_template_regression_smoke", host=self.host, stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("target key=storefront-home-nav path=/ status=200 ready=True", value)
        self.assertIn("target key=platform-onboarding-list path=/ops/platform/onboarding/ status=200 ready=True", value)
        self.assertIn("target key=platform-tenants-list path=/ops/platform/tenants/ status=200 ready=True", value)
        self.assertIn("next_track=System Validation Pass 2 — Browser Smoke Evidence", value)

    def test_management_command_blocks_unknown_owner_authentication(self):
        with self.assertRaises(CommandError):
            call_command(
                "system_template_regression_smoke",
                host=self.host,
                owner_email="missing-owner@hubx.market",
                stdout=StringIO(),
            )
