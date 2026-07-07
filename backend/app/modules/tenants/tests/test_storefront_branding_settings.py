from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.application.storefront_branding_commands import storefront_branding_commands
from app.modules.tenants.models import Tenant


@override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class StorefrontBrandingSettingsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Branding",
            slug="loja-branding",
            subdomain="loja-branding",
        )
        self.other_tenant = Tenant.objects.create(
            name="Outra Branding",
            slug="outra-branding",
            subdomain="outra-branding",
            storefront_hero_title="Hero externo",
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def _login_owner(self, *, email: str, role: str):
        OwnerUser.objects.create(tenant=self.tenant, email=email, role=role, is_active=True)
        user = User.objects.create_user(username=email, email=email, password="secret")
        self.client.force_login(user)
        return user

    def _payload(self, **overrides):
        payload = {
            "logo_url": "https://cdn.example.com/loja/logo.png",
            "conversion_primary_color": "#0f766e",
            "storefront_hero_enabled": "1",
            "storefront_hero_title": "Nova vitrine institucional",
            "storefront_hero_description": "Uma curadoria feita para quem quer comprar com mais clareza.",
            "storefront_hero_image_url": "https://cdn.example.com/loja/banner.jpg",
            "storefront_hero_cta_label": "Conhecer produtos",
            "storefront_hero_cta_href": "/catalog/",
        }
        payload.update(overrides)
        return payload

    def test_command_updates_storefront_hero_for_current_tenant_and_audits(self):
        result = storefront_branding_commands.update_storefront_hero(
            tenant_id=self.tenant.id,
            payload=self._payload(),
            actor_label="owner@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "storefront-branding-updated")
        self.tenant.refresh_from_db()
        self.other_tenant.refresh_from_db()
        self.assertEqual(self.tenant.storefront_hero_title, "Nova vitrine institucional")
        self.assertEqual(self.tenant.logo_url, "https://cdn.example.com/loja/logo.png")
        self.assertEqual(self.tenant.conversion_primary_color, "#0f766e")
        self.assertEqual(self.tenant.storefront_hero_cta_href, "/catalog/")
        self.assertEqual(self.other_tenant.storefront_hero_title, "Hero externo")
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="tenants",
                action="tenant.storefront_branding_updated",
                entity_id=str(self.tenant.id),
            ).exists()
        )

    def test_command_rejects_external_cta_href(self):
        result = storefront_branding_commands.update_storefront_hero(
            tenant_id=self.tenant.id,
            payload=self._payload(storefront_hero_cta_href="https://example.com/catalog"),
            actor_role="owner",
        )

        self.assertEqual(result["result"], "storefront-branding-invalid")
        self.assertIn("storefront_hero_cta_href", result["errors"])

    def test_command_rejects_invalid_logo_url(self):
        result = storefront_branding_commands.update_storefront_hero(
            tenant_id=self.tenant.id,
            payload=self._payload(logo_url="logo-sem-protocolo.png"),
            actor_role="owner",
        )

        self.assertEqual(result["result"], "storefront-branding-invalid")
        self.assertIn("logo_url", result["errors"])

    def test_command_rejects_low_contrast_conversion_color(self):
        result = storefront_branding_commands.update_storefront_hero(
            tenant_id=self.tenant.id,
            payload=self._payload(conversion_primary_color="#ffe797"),
            actor_role="owner",
        )

        self.assertEqual(result["result"], "storefront-branding-invalid")
        self.assertIn("conversion_primary_color", result["errors"])

    def test_settings_view_renders_branding_form(self):
        response = self.client.get(reverse("tenant_branding:storefront-branding-settings"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_storefront_branding_page.html")
        self.assertContains(response, "Branding da loja")
        self.assertContains(response, "logo_url")
        self.assertContains(response, "conversion_primary_color")
        self.assertContains(response, "storefront_hero_image_url")
        self.assertContains(response, "Prévia")

    def test_settings_view_persists_current_tenant_branding(self):
        response = self.client.post(
            reverse("tenant_branding:storefront-branding-settings"),
            self._payload(
                logo_url="https://cdn.example.com/loja/logo-admin.png",
                storefront_hero_title="Hero salvo pelo ops",
            ),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.tenant.refresh_from_db()
        self.other_tenant.refresh_from_db()
        self.assertEqual(self.tenant.logo_url, "https://cdn.example.com/loja/logo-admin.png")
        self.assertEqual(self.tenant.conversion_primary_color, "#0f766e")
        self.assertEqual(self.tenant.storefront_hero_title, "Hero salvo pelo ops")
        self.assertEqual(self.other_tenant.storefront_hero_title, "Hero externo")

    def test_settings_view_exposes_tenant_conversion_theme_variables(self):
        self.tenant.conversion_primary_color = "#0f766e"
        self.tenant.save(update_fields=["conversion_primary_color"])

        response = self.client.get(reverse("tenant_branding:storefront-branding-settings"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "--tenant-conversion-primary: #0f766e")
        self.assertContains(response, "--tenant-conversion-primary-hover: #0c635c")

    def test_settings_view_rejects_role_without_branding_permission(self):
        self._login_owner(email="support.branding@hubx.market", role="support")

        response = self.client.post(
            reverse("tenant_branding:storefront-branding-settings"),
            self._payload(storefront_hero_title="Bloqueado"),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Permissão insuficiente para gerenciar branding", status_code=400)
        self.tenant.refresh_from_db()
        self.assertNotEqual(self.tenant.storefront_hero_title, "Bloqueado")
