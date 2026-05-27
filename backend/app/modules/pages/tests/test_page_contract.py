from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.pages.application.admin_page_commands import admin_page_commands
from app.modules.pages.application.admin_page_queries import admin_page_queries
from app.modules.pages.application.storefront_page_queries import storefront_page_queries
from app.modules.pages.models import Page
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class PageContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Pages", slug="loja-pages", subdomain="loja-pages")
        self.other_tenant = Tenant.objects.create(name="Outra Pages", slug="outra-pages", subdomain="outra-pages")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"

    def _login_owner(self, *, email: str, role: str):
        OwnerUser.objects.create(tenant=self.tenant, email=email, role=role, is_active=True)
        user = User.objects.create_user(username=email, email=email, password="secret")
        self.client.force_login(user)
        return user

    def test_admin_command_creates_page_for_current_tenant(self):
        result = admin_page_commands.create_page(
            tenant_id=self.tenant.id,
            payload={
                "title": "Sobre a loja",
                "slug": "sobre",
                "status": Page.Status.PUBLISHED,
                "body": "Conteúdo institucional",
                "seo_title": "Sobre",
                "seo_description": "Conheça a loja",
            },
        )

        self.assertEqual(result["result"], "page-created")
        page = Page.objects.get()
        self.assertEqual(page.tenant, self.tenant)
        self.assertEqual(page.slug, "sobre")
        self.assertEqual(page.status, Page.Status.PUBLISHED)
        self.assertIsNotNone(page.published_at)

    def test_admin_command_rejects_duplicate_slug_per_tenant(self):
        Page.objects.create(tenant=self.tenant, slug="sobre", title="Sobre")

        result = admin_page_commands.create_page(
            tenant_id=self.tenant.id,
            payload={"title": "Sobre 2", "slug": "sobre", "status": Page.Status.DRAFT},
        )

        self.assertEqual(result["result"], "page-invalid")
        self.assertIn("slug", result["errors"])

    def test_admin_command_allows_same_slug_in_another_tenant(self):
        Page.objects.create(tenant=self.other_tenant, slug="sobre", title="Sobre")

        result = admin_page_commands.create_page(
            tenant_id=self.tenant.id,
            payload={"title": "Sobre", "slug": "sobre", "status": Page.Status.DRAFT},
        )

        self.assertEqual(result["result"], "page-created")
        self.assertEqual(Page.objects.filter(slug="sobre").count(), 2)

    def test_admin_queries_list_only_current_tenant_pages(self):
        Page.objects.create(tenant=self.tenant, slug="sobre", title="Sobre")
        Page.objects.create(tenant=self.other_tenant, slug="trocas", title="Trocas")

        pages = admin_page_queries.list_pages(tenant_id=self.tenant.id)

        self.assertEqual([page["slug"] for page in pages], ["sobre"])

    def test_storefront_query_returns_only_published_page_for_tenant(self):
        Page.objects.create(tenant=self.tenant, slug="sobre", title="Sobre", status=Page.Status.PUBLISHED)
        Page.objects.create(tenant=self.tenant, slug="rascunho", title="Rascunho", status=Page.Status.DRAFT)
        Page.objects.create(tenant=self.other_tenant, slug="sobre", title="Outro", status=Page.Status.PUBLISHED)

        page = storefront_page_queries.get_published_page(tenant_id=self.tenant.id, slug="sobre")

        self.assertEqual(page["title"], "Sobre")
        self.assertIsNone(storefront_page_queries.get_published_page(tenant_id=self.tenant.id, slug="rascunho"))
        self.assertEqual(
            storefront_page_queries.get_published_page(tenant_id=self.other_tenant.id, slug="sobre")["title"],
            "Outro",
        )

    def test_storefront_view_renders_published_page(self):
        Page.objects.create(
            tenant=self.tenant,
            slug="sobre",
            title="Sobre a loja",
            body="Conteúdo institucional",
            status=Page.Status.PUBLISHED,
            seo_description="Conheça nossa curadoria",
        )

        response = self.client.get(reverse("storefront_pages:page-detail", kwargs={"page_slug": "sobre"}), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/storefront_page.html")
        self.assertContains(response, "Sobre a loja")
        self.assertContains(response, "Conteúdo institucional")
        self.assertContains(response, "Conheça nossa curadoria")

    def test_storefront_view_hides_draft_and_other_tenant_page(self):
        Page.objects.create(tenant=self.tenant, slug="rascunho", title="Rascunho", status=Page.Status.DRAFT)
        Page.objects.create(tenant=self.other_tenant, slug="sobre", title="Outro", status=Page.Status.PUBLISHED)

        draft_response = self.client.get(
            reverse("storefront_pages:page-detail", kwargs={"page_slug": "rascunho"}),
            HTTP_HOST=self.host,
        )
        other_response = self.client.get(
            reverse("storefront_pages:page-detail", kwargs={"page_slug": "sobre"}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(draft_response.status_code, 404)
        self.assertEqual(other_response.status_code, 404)

    def test_admin_list_and_create_views(self):
        list_response = self.client.get(reverse("pages:admin-pages-list"), HTTP_HOST=self.host)

        self.assertEqual(list_response.status_code, 200)
        self.assertTemplateUsed(list_response, "pages/templates/admin_pages_list_page.html")
        self.assertContains(list_response, "Nenhuma página encontrada")

        create_response = self.client.post(
            reverse("pages:admin-pages-create"),
            {
                "title": "Política de trocas",
                "slug": "trocas",
                "status": Page.Status.PUBLISHED,
                "body": "Trocas em até 7 dias.",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(create_response["Location"], reverse("pages:admin-pages-list"))
        self.assertTrue(Page.objects.filter(tenant=self.tenant, slug="trocas").exists())

    def test_admin_pages_list_hides_create_and_edit_for_role_without_page_permission(self):
        self._login_owner(email="support.pages@hubx.market", role="support")
        page = Page.objects.create(tenant=self.tenant, slug="sobre", title="Sobre", status=Page.Status.DRAFT)

        response = self.client.get(reverse("pages:admin-pages-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("pages:admin-pages-create"))
        self.assertNotContains(response, reverse("pages:admin-pages-edit", kwargs={"page_id": page.id}))
        self.assertContains(response, "Sem permissão para editar")

    def test_admin_pages_create_rejects_role_without_page_permission(self):
        self._login_owner(email="support.pages.post@hubx.market", role="support")

        response = self.client.post(
            reverse("pages:admin-pages-create"),
            {
                "title": "Bloqueada",
                "slug": "bloqueada",
                "status": Page.Status.PUBLISHED,
                "body": "Não deveria criar.",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Permissão insuficiente", status_code=400)
        self.assertFalse(Page.objects.filter(tenant=self.tenant, slug="bloqueada").exists())

    def test_admin_edit_view_updates_current_tenant_page(self):
        page = Page.objects.create(tenant=self.tenant, slug="sobre", title="Sobre", status=Page.Status.DRAFT)

        response = self.client.post(
            reverse("pages:admin-pages-edit", kwargs={"page_id": page.id}),
            {
                "title": "Sobre atualizado",
                "slug": "sobre-atualizado",
                "status": Page.Status.PUBLISHED,
                "body": "Novo conteúdo",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        page.refresh_from_db()
        self.assertEqual(page.title, "Sobre atualizado")
        self.assertEqual(page.slug, "sobre-atualizado")
        self.assertEqual(page.status, Page.Status.PUBLISHED)
