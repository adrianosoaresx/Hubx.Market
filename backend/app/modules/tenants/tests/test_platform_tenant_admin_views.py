from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.application.platform_tenant_admin_queries import platform_tenant_admin_queries
from app.modules.tenants.models import Tenant


@override_settings(
    HUBX_MARKET_ROOT_DOMAIN="hubx.market",
    HUBX_PLATFORM_TENANT_SLUG="loja-platform",
    HUBX_OPS_AUTH_GATE_ENFORCED=False,
    ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
)
class PlatformTenantAdminViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Platform",
            slug="loja-platform",
            subdomain="loja-platform",
            custom_domain="loja.example.com",
        )
        self.other_tenant = Tenant.objects.create(
            name="Outra Platform",
            slug="outra-platform",
            subdomain="outra-platform",
            is_active=False,
        )
        self.maintenance_tenant = Tenant.objects.create(
            name="Manutenção Platform",
            slug="manutencao-platform",
            subdomain="manutencao-platform",
            maintenance_mode=True,
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def _login_owner(self, *, email: str, role: str):
        OwnerUser.objects.create(tenant=self.tenant, email=email, role=role, is_active=True)
        user = User.objects.create_user(username=email, email=email, password="secret")
        self.client.force_login(user)
        return user

    def test_platform_tenant_query_lists_operational_inventory(self):
        rows = platform_tenant_admin_queries.list_tenants()
        summary = platform_tenant_admin_queries.get_summary()
        tenant_detail = platform_tenant_admin_queries.get_tenant(slug=self.tenant.slug)

        self.assertEqual([row["slug"] for row in rows], ["loja-platform", "manutencao-platform", "outra-platform"])
        self.assertEqual(rows[0]["storefront_host"], "loja-platform.hubx.market")
        self.assertEqual(rows[0]["custom_domain"], "loja.example.com")
        self.assertEqual(tenant_detail["storefront_url"], "https://loja-platform.hubx.market")
        self.assertTrue(tenant_detail["custom_domain_configured"])
        self.assertEqual(summary, {"total": 3, "active": 1, "maintenance": 1, "inactive": 1})

    def test_platform_tenants_read_only_surface_renders_inventory(self):
        response = self.client.get(reverse("tenants:platform-tenants-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_platform_tenants_list_page.html")
        self.assertContains(response, "Inventário de lojas")
        self.assertContains(response, "loja-platform.hubx.market")
        self.assertContains(response, "loja.example.com")
        self.assertContains(response, "Manutenção")
        self.assertContains(response, "Esta tela não cria, edita ou remove tenants.")
        self.assertContains(
            response,
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
        )

    def test_platform_tenants_list_shows_create_link_for_owner(self):
        self._login_owner(email="owner.platform@hubx.market", role="owner")

        response = self.client.get(reverse("tenants:platform-tenants-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("tenants:platform-tenants-create"))

    def test_platform_tenant_create_form_requires_manage_permission(self):
        self._login_owner(email="support.create.platform@hubx.market", role="support")

        response = self.client.get(reverse("tenants:platform-tenants-create"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Criação indisponível")
        self.assertNotContains(response, "Cadastro mínimo")

    def test_platform_tenant_create_form_renders_for_owner(self):
        self._login_owner(email="owner.create.platform@hubx.market", role="owner")

        response = self.client.get(reverse("tenants:platform-tenants-create"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_platform_tenant_form_page.html")
        self.assertContains(response, "Nova loja")
        self.assertContains(response, "Cadastro mínimo")
        self.assertContains(response, "custom_domain permanece contract-only")

    def test_platform_tenant_create_post_creates_tenant_and_redirects_to_detail(self):
        self._login_owner(email="owner.post.platform@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-create"),
            {
                "name": "Nova Via UI",
                "slug": "nova-via-ui",
                "subdomain": "nova-via-ui",
                "custom_domain": "nova-ui.example.com",
                "is_active": "1",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": "nova-via-ui"}),
        )
        tenant = Tenant.objects.get(slug="nova-via-ui")
        self.assertEqual(tenant.custom_domain, "nova-ui.example.com")
        self.assertTrue(AuditLog.objects.filter(tenant__isnull=True, action="platform.tenant.created", entity_id=str(tenant.id)).exists())

    def test_platform_tenant_create_post_returns_400_for_duplicate_slug(self):
        self._login_owner(email="owner.duplicate.platform@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-create"),
            {
                "name": "Duplicada",
                "slug": self.tenant.slug,
                "subdomain": "duplicada",
                "is_active": "1",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Já existe uma loja com este slug.", status_code=400)
        self.assertFalse(Tenant.objects.filter(name="Duplicada").exists())

    def test_platform_tenant_create_post_rejects_role_without_manage_permission(self):
        self._login_owner(email="support.post.platform@hubx.market", role="support")

        response = self.client.post(
            reverse("tenants:platform-tenants-create"),
            {"name": "Bloqueada UI", "slug": "bloqueada-ui", "subdomain": "bloqueada-ui"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Criação indisponível", status_code=400)
        self.assertFalse(Tenant.objects.filter(slug="bloqueada-ui").exists())

    def test_platform_tenant_detail_read_only_surface_renders_operational_metadata(self):
        response = self.client.get(
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_platform_tenant_detail_page.html")
        self.assertContains(response, "Detalhe da loja")
        self.assertContains(response, "Loja Platform")
        self.assertContains(response, "loja-platform.hubx.market")
        self.assertContains(response, "loja.example.com")
        self.assertContains(response, "Contract-only; ainda não resolve HTTP")
        self.assertContains(response, "Nenhum dado de catálogo, pedidos, clientes ou pagamentos é lido neste detalhe.")

    def test_platform_tenant_detail_shows_state_actions_for_owner(self):
        self._login_owner(email="owner.state.platform@hubx.market", role="owner")

        response = self.client.get(
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("tenants:platform-tenants-state", kwargs={"tenant_slug": self.tenant.slug}))
        self.assertContains(response, "Desativar loja")
        self.assertContains(response, "Ligar manutenção")
        self.assertContains(
            response,
            reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": self.tenant.slug}),
        )
        self.assertContains(response, "Domínio customizado")
        self.assertContains(response, "Cadastro contract-only")
        self.assertContains(response, "Owner inicial")
        self.assertContains(response, "Bootstrap indisponível")

    def test_platform_tenant_detail_shows_owner_bootstrap_form_when_no_active_owner_exists(self):
        self._login_owner(email="owner.bootstrap.platform@hubx.market", role="owner")
        tenant = Tenant.objects.create(name="Sem Owner", slug="sem-owner", subdomain="sem-owner")

        response = self.client.get(
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant.slug}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse("tenants:platform-tenants-owner-bootstrap", kwargs={"tenant_slug": tenant.slug}),
        )
        self.assertContains(response, "Provisionar owner")
        self.assertNotContains(response, "Bootstrap indisponível")

    def test_platform_tenant_state_post_updates_state_and_redirects(self):
        self._login_owner(email="owner.state.post@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-state", kwargs={"tenant_slug": self.tenant.slug}),
            {"action": "deactivate"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
        )
        self.tenant.refresh_from_db()
        self.assertFalse(self.tenant.is_active)
        self.assertTrue(AuditLog.objects.filter(tenant__isnull=True, action="platform.tenant.deactivate", entity_id=str(self.tenant.id)).exists())

    def test_platform_tenant_state_post_rejects_role_without_manage_permission(self):
        self._login_owner(email="support.state.platform@hubx.market", role="support")

        response = self.client.post(
            reverse("tenants:platform-tenants-state", kwargs={"tenant_slug": self.tenant.slug}),
            {"action": "deactivate"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("platform-tenant-state-permission-denied", response["Location"])
        self.tenant.refresh_from_db()
        self.assertTrue(self.tenant.is_active)

    def test_platform_tenant_state_post_returns_404_for_unknown_slug(self):
        self._login_owner(email="owner.state.404@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-state", kwargs={"tenant_slug": "ausente"}),
            {"action": "activate"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 404)

    def test_platform_tenant_custom_domain_post_updates_domain_and_redirects(self):
        self._login_owner(email="owner.domain.post@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": self.tenant.slug}),
            {"custom_domain": "https://Nova-Loja.Example.COM:443/path"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
        )
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.custom_domain, "nova-loja.example.com")
        self.assertTrue(
            AuditLog.objects.filter(
                tenant__isnull=True,
                action="platform.tenant.custom_domain_updated",
                entity_id=str(self.tenant.id),
            ).exists()
        )

    def test_platform_tenant_custom_domain_post_clears_domain(self):
        self._login_owner(email="owner.domain.clear@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": self.tenant.slug}),
            {"custom_domain": ""},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.tenant.refresh_from_db()
        self.assertIsNone(self.tenant.custom_domain)

    def test_platform_tenant_custom_domain_post_rejects_duplicate_domain(self):
        self._login_owner(email="owner.domain.duplicate@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": self.other_tenant.slug}),
            {"custom_domain": "LOJA.EXAMPLE.COM"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("platform-tenant-custom-domain-invalid", response["Location"])
        self.other_tenant.refresh_from_db()
        self.assertIsNone(self.other_tenant.custom_domain)

    def test_platform_tenant_custom_domain_post_rejects_role_without_manage_permission(self):
        self._login_owner(email="support.domain.platform@hubx.market", role="support")

        response = self.client.post(
            reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": self.tenant.slug}),
            {"custom_domain": "blocked.example.com"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("platform-tenant-custom-domain-permission-denied", response["Location"])
        self.tenant.refresh_from_db()
        self.assertEqual(self.tenant.custom_domain, "loja.example.com")

    def test_platform_tenant_custom_domain_post_returns_404_for_unknown_slug(self):
        self._login_owner(email="owner.domain.404@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-custom-domain", kwargs={"tenant_slug": "ausente"}),
            {"custom_domain": "ausente.example.com"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 404)

    def test_platform_tenant_owner_bootstrap_post_provisions_owner_and_redirects(self):
        self._login_owner(email="owner.bootstrap.post@hubx.market", role="owner")
        tenant = Tenant.objects.create(name="Bootstrap UI", slug="bootstrap-ui", subdomain="bootstrap-ui")

        response = self.client.post(
            reverse("tenants:platform-tenants-owner-bootstrap", kwargs={"tenant_slug": tenant.slug}),
            {
                "owner_email": "first.ui@hubx.market",
                "owner_name": "First UI",
                "owner_role": "owner",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": tenant.slug}),
        )
        owner = OwnerUser.objects.get(tenant=tenant, email="first.ui@hubx.market")
        self.assertTrue(
            AuditLog.objects.filter(
                tenant__isnull=True,
                action="platform.tenant.owner_bootstrapped",
                entity_id=str(owner.id),
            ).exists()
        )

    def test_platform_tenant_owner_bootstrap_post_rejects_existing_owner(self):
        self._login_owner(email="owner.bootstrap.existing@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-owner-bootstrap", kwargs={"tenant_slug": self.tenant.slug}),
            {"owner_email": "another.owner@hubx.market", "owner_role": "owner"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("platform-tenant-owner-bootstrap-already-has-owner", response["Location"])
        self.assertFalse(OwnerUser.objects.filter(tenant=self.tenant, email="another.owner@hubx.market").exists())

    def test_platform_tenant_owner_bootstrap_post_rejects_role_without_manage_permission(self):
        self._login_owner(email="support.bootstrap.platform@hubx.market", role="support")
        tenant = Tenant.objects.create(name="Blocked Bootstrap UI", slug="blocked-bootstrap-ui", subdomain="blocked-bootstrap-ui")

        response = self.client.post(
            reverse("tenants:platform-tenants-owner-bootstrap", kwargs={"tenant_slug": tenant.slug}),
            {"owner_email": "blocked.ui@hubx.market", "owner_role": "owner"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("platform-tenant-owner-bootstrap-permission-denied", response["Location"])
        self.assertFalse(OwnerUser.objects.filter(tenant=tenant, email="blocked.ui@hubx.market").exists())

    def test_platform_tenant_owner_bootstrap_post_returns_404_for_unknown_slug(self):
        self._login_owner(email="owner.bootstrap.404@hubx.market", role="owner")

        response = self.client.post(
            reverse("tenants:platform-tenants-owner-bootstrap", kwargs={"tenant_slug": "ausente"}),
            {"owner_email": "missing.ui@hubx.market", "owner_role": "owner"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 404)

    def test_platform_tenant_detail_returns_404_for_unknown_slug(self):
        response = self.client.get(
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": "tenant-ausente"}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 404)

    def test_platform_tenants_surface_hides_rows_for_role_without_permission(self):
        self._login_owner(email="support.platform@hubx.market", role="support")

        response = self.client.get(reverse("tenants:platform-tenants-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma loja visível")
        self.assertNotContains(response, "loja-platform.hubx.market")

    def test_platform_tenant_detail_hides_data_for_role_without_permission(self):
        self._login_owner(email="support.detail.platform@hubx.market", role="support")

        response = self.client.get(
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Loja não visível")
        self.assertNotContains(response, "loja-platform.hubx.market")

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_platform_tenants_surface_uses_ops_permission_when_gate_is_enabled(self):
        self._login_owner(email="support.gate.platform@hubx.market", role="support")

        response = self.client.get(reverse("tenants:platform-tenants-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 403)

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_platform_tenant_detail_uses_ops_permission_when_gate_is_enabled(self):
        self._login_owner(email="support.gate.detail.platform@hubx.market", role="support")

        response = self.client.get(
            reverse("tenants:platform-tenants-detail", kwargs={"tenant_slug": self.tenant.slug}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 403)
