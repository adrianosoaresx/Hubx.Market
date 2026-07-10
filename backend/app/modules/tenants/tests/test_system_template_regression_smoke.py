from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from app.modules.catalog.models import Product, ProductVariant
from app.modules.tenants.application.system_template_regression_smoke import (
    SystemTemplateSmokeTarget,
    system_template_regression_smoke,
)
from app.modules.tenants.management.commands.local_e2e_smoke import Command as LocalE2ESmokeCommand
from app.modules.tenants.models import Tenant


@override_settings(
    ALLOWED_HOSTS=[".hubx.market", "hubx.market", "localhost", "testserver"],
    HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-smoke-demo",
)
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
            "central-home-public-entrypoints",
            "central-login-public-nav",
            "customer-orders-nav-target",
            "ops-dashboard",
            "public-demo-access",
            "public-plans",
            "platform-acquisitions-list",
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

    def test_smoke_blocks_when_marker_group_is_missing(self):
        target = SystemTemplateSmokeTarget(
            key="missing-marker-group",
            path="/",
            expected_status=200,
            markers=("Hubx Smoke Demo",),
            marker_groups=(("Marcador A", "Marcador B"),),
        )

        payload = system_template_regression_smoke.run(client=self.client, host=self.host, targets=(target,))

        self.assertFalse(payload["ready"])
        self.assertIn("system-template-regression:missing-marker-group:missing:Marcador A or Marcador B", payload["blockers"])

    def test_anonymous_non_demo_storefront_home_keeps_login_entry(self):
        tenant = Tenant.objects.create(
            name="Regular Store",
            slug="regular-store",
            subdomain="regular-store",
            is_active=True,
        )

        response = self.client.get("/", HTTP_HOST=f"{tenant.subdomain}.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrar")
        self.assertNotContains(response, "Sair")

    def test_management_command_outputs_smoke_targets(self):
        output = StringIO()

        call_command("system_template_regression_smoke", host=self.host, stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("target key=storefront-home-nav host=hubx-smoke-demo.hubx.market path=/ status=200 ready=True", value)
        self.assertIn("target key=central-home-public-entrypoints host=hubx.market path=/ status=200 ready=True", value)
        self.assertIn("target key=public-demo-access host=hubx.market path=/demo/ status=200 ready=True", value)
        self.assertIn("target key=public-plans host=hubx.market path=/plans/ status=200 ready=True", value)
        self.assertIn(
            "target key=platform-acquisitions-list host=hubx.market path=/ops/platform/acquisitions/ status=200 ready=True",
            value,
        )
        self.assertIn("target key=platform-onboarding-list host=hubx.market path=/ops/platform/onboarding/ status=200 ready=True", value)
        self.assertIn("target key=platform-tenants-list host=hubx.market path=/ops/platform/tenants/ status=200 ready=True", value)
        self.assertIn("next_track=System Validation Pass 2 — Browser Smoke Evidence", value)

    def test_management_command_blocks_unknown_owner_authentication(self):
        with self.assertRaises(CommandError):
            call_command(
                "system_template_regression_smoke",
                host=self.host,
                owner_email="missing-owner@hubx.market",
                stdout=StringIO(),
            )

    def test_local_e2e_storefront_checks_customer_store_logo_and_social_image(self):
        tenant = Tenant.objects.create(
            name="Arnaldo Móveis Rústicos",
            slug="arnaldo-moveis-rusticos",
            subdomain="arnaldomoveisrusticos",
            logo_url="https://cdn.example.com/arnaldo/logo.png",
            is_active=True,
        )
        product = Product.objects.create(
            tenant=tenant,
            name="Mesa rústica Arnaldo",
            slug="mesa-rustica-arnaldo",
            brand_name="Arnaldo",
            category_label="Móveis rústicos",
            description="Mesa em madeira para validar vitrine tenant-owned.",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="ARNALDO-MESA-001",
            price="1499.90",
            stock=3,
            is_default=True,
            is_active=True,
        )

        results = LocalE2ESmokeCommand()._visitor_storefront(host="arnaldomoveisrusticos.hubx.market")
        blockers = [result for result in results if result.key.startswith("storefront-branding:") and not result.ready]

        self.assertFalse(blockers, [blocker.summary for blocker in blockers])
        result_by_key = {result.key: result for result in results}
        self.assertTrue(result_by_key["storefront-branding:/:logo"].ready)
        self.assertTrue(result_by_key["storefront-branding:/:social-image"].ready)
        self.assertTrue(result_by_key["storefront-branding:/catalog/:logo"].ready)
        self.assertTrue(result_by_key["storefront-branding:/catalog/:social-image"].ready)
