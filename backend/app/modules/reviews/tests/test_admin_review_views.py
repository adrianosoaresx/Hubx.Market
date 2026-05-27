from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.accounts.models import OwnerUser
from app.modules.catalog.models import Product
from app.modules.reviews.application.admin_review_commands import admin_review_commands
from app.modules.reviews.application.admin_review_queries import admin_review_queries
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class AdminReviewViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Reviews Admin", slug="loja-reviews-admin", subdomain="loja-reviews-admin")
        self.other_tenant = Tenant.objects.create(name="Outra Reviews Admin", slug="outra-reviews-admin", subdomain="outra-reviews-admin")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Avaliado",
            slug="produto-avaliado",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto Outra Loja",
            slug="produto-outra-loja",
            status=Product.Status.ACTIVE,
            is_active=True,
        )

    def _login_owner(self, *, email: str, role: str):
        OwnerUser.objects.create(tenant=self.tenant, email=email, role=role, is_active=True)
        user = User.objects.create_user(username=email, email=email, password="secret")
        self.client.force_login(user)
        return user

    def test_admin_reviews_list_renders_empty_state_for_tenant(self):
        response = self.client.get(reverse("reviews:admin-reviews-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_reviews_list_page.html")
        self.assertContains(response, "Avaliações")
        self.assertContains(response, "Nenhuma avaliação para moderar")
        self.assertContains(response, reverse("reviews:admin-reviews-create"))

    def test_admin_reviews_list_hides_actions_for_role_without_review_permission(self):
        self._login_owner(email="viewer.reviews@hubx.market", role="viewer")
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Pendente",
            status=ProductReview.Status.PENDING,
        )

        response = self.client.get(reverse("reviews:admin-reviews-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pendente")
        self.assertNotContains(response, reverse("reviews:admin-reviews-create"))
        self.assertNotContains(response, reverse("reviews:admin-review-moderate", kwargs={"review_id": review.id}))
        self.assertContains(response, "Sem permissão para moderar")

    def test_admin_reviews_list_is_tenant_scoped(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Amei",
            author_name="Cliente A",
        )
        ProductReview.objects.create(
            tenant=self.other_tenant,
            product=self.other_product,
            rating=1,
            title="Outra loja",
            author_name="Cliente B",
        )

        response = self.client.get(reverse("reviews:admin-reviews-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Amei")
        self.assertNotContains(response, "Outra loja")

    def test_admin_reviews_list_filters_by_status(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Review pendente única",
            status=ProductReview.Status.PENDING,
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=4,
            title="Aprovada",
            status=ProductReview.Status.APPROVED,
            moderated_at=timezone.now(),
        )

        response = self.client.get(
            reverse("reviews:admin-reviews-list"),
            {"status": ProductReview.Status.APPROVED},
            HTTP_HOST=self.host,
        )

        self.assertContains(response, "Aprovada")
        self.assertNotContains(response, "Review pendente única")

    def test_admin_review_moderate_post_approves_review_for_current_tenant(self):
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            status=ProductReview.Status.PENDING,
        )

        response = self.client.post(
            reverse("reviews:admin-review-moderate", kwargs={"review_id": review.id}),
            {"action": "approve"},
            HTTP_HOST=self.host,
        )

        review.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("reviews:admin-reviews-list"))
        self.assertEqual(review.status, ProductReview.Status.APPROVED)
        self.assertIsNotNone(review.moderated_at)

    def test_admin_review_moderate_post_is_tenant_scoped(self):
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            status=ProductReview.Status.PENDING,
        )

        response = self.client.post(
            reverse("reviews:admin-review-moderate", kwargs={"review_id": review.id}),
            {"action": "approve"},
            HTTP_HOST=self.other_host,
        )

        review.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertIsNone(review.moderated_at)

    def test_admin_review_query_service_is_tenant_scoped(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Atual",
        )
        ProductReview.objects.create(
            tenant=self.other_tenant,
            product=self.other_product,
            rating=1,
            title="Outra",
        )

        reviews = admin_review_queries.list_reviews(tenant_id=self.tenant.id)

        self.assertEqual([review["title"] for review in reviews], ["Atual"])

    def test_admin_review_command_rejects_review_without_changing_content(self):
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Conteúdo original",
            body="Texto original",
            status=ProductReview.Status.APPROVED,
        )

        result, moderated_review = admin_review_commands.moderate_review(
            tenant_id=self.tenant.id,
            review_id=review.id,
            action="reject",
            moderated_by="Ops",
        )

        moderated_review.refresh_from_db()
        self.assertEqual(result, "review-rejected")
        self.assertEqual(moderated_review.status, ProductReview.Status.REJECTED)
        self.assertEqual(moderated_review.title, "Conteúdo original")
        self.assertEqual(moderated_review.body, "Texto original")

    def test_admin_review_create_view_renders_form(self):
        response = self.client.get(reverse("reviews:admin-reviews-create"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_review_form_page.html")
        self.assertContains(response, "Nova avaliação")
        self.assertContains(response, "Slug do produto")

    def test_admin_review_create_post_creates_pending_review_for_current_tenant(self):
        response = self.client.post(
            reverse("reviews:admin-reviews-create"),
            {
                "product_slug": self.product.slug,
                "rating": "5",
                "title": "Excelente",
                "body": "Chegou rápido e funcionou bem.",
                "author_name": "Cliente Ops",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("reviews:admin-reviews-list"))
        review = ProductReview.objects.get(title="Excelente")
        self.assertEqual(review.tenant, self.tenant)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertEqual(review.author_name, "Cliente Ops")

    def test_admin_review_create_post_rejects_role_without_review_permission(self):
        self._login_owner(email="viewer.reviews.post@hubx.market", role="viewer")

        response = self.client.post(
            reverse("reviews:admin-reviews-create"),
            {
                "product_slug": self.product.slug,
                "rating": "5",
                "title": "Sem permissão",
                "author_name": "Cliente Ops",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Permissão insuficiente", status_code=400)
        self.assertFalse(ProductReview.objects.filter(title="Sem permissão").exists())

    def test_admin_review_create_post_rejects_invalid_rating(self):
        response = self.client.post(
            reverse("reviews:admin-reviews-create"),
            {
                "product_slug": self.product.slug,
                "rating": "8",
                "title": "Nota inválida",
                "author_name": "Cliente Ops",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Informe uma nota entre 1 e 5", status_code=400)
        self.assertFalse(ProductReview.objects.filter(title="Nota inválida").exists())

    def test_admin_review_create_post_does_not_use_cross_tenant_product(self):
        response = self.client.post(
            reverse("reviews:admin-reviews-create"),
            {
                "product_slug": self.product.slug,
                "rating": "5",
                "title": "Tentativa cross tenant",
                "author_name": "Cliente Ops",
            },
            HTTP_HOST=self.other_host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Produto não encontrado para este tenant", status_code=400)
        self.assertFalse(ProductReview.objects.filter(title="Tentativa cross tenant").exists())
