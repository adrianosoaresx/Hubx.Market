from django.test import TestCase

from app.modules.catalog.models import Product
from app.modules.reviews.application.review_summary_queries import product_review_summary_queries
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


class ProductReviewSummaryQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Reviews Store", slug="reviews-store", subdomain="reviews-store")
        self.other_tenant = Tenant.objects.create(name="Other Reviews", slug="other-reviews", subdomain="other-reviews")
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto com reviews",
            slug="produto-com-reviews",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto de outra loja",
            slug="produto-outra-loja",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.empty_product = Product.objects.create(
            tenant=self.tenant,
            name="Produto sem reviews",
            slug="produto-sem-reviews",
            status=Product.Status.ACTIVE,
            is_active=True,
        )

    def test_product_review_defaults_to_pending(self):
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Excelente",
            author_name="Cliente A",
        )

        self.assertEqual(review.status, ProductReview.Status.PENDING)

    def test_product_review_summary_uses_only_approved_same_tenant_reviews(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            status=ProductReview.Status.APPROVED,
            author_name="Cliente A",
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=3,
            status=ProductReview.Status.APPROVED,
            author_name="Cliente B",
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=1,
            status=ProductReview.Status.PENDING,
            author_name="Cliente C",
        )
        ProductReview.objects.create(
            tenant=self.other_tenant,
            product=self.other_product,
            rating=1,
            status=ProductReview.Status.APPROVED,
            author_name="Outra loja",
        )

        summary = product_review_summary_queries.get_product_review_summary(
            tenant_id=self.tenant.id,
            product_id=self.product.id,
        )
        cross_tenant_summary = product_review_summary_queries.get_product_review_summary(
            tenant_id=self.other_tenant.id,
            product_id=self.product.id,
        )

        self.assertEqual(summary["review_count"], 2)
        self.assertEqual(summary["rating_average"], "4.0")
        self.assertEqual(summary["status"], "ready")
        self.assertEqual(cross_tenant_summary["review_count"], 0)
        self.assertEqual(cross_tenant_summary["status"], "empty")

    def test_product_review_bulk_summaries_are_approved_only_and_tenant_scoped(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            status=ProductReview.Status.APPROVED,
            author_name="Cliente A",
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=3,
            status=ProductReview.Status.APPROVED,
            author_name="Cliente B",
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=1,
            status=ProductReview.Status.REJECTED,
            author_name="Cliente C",
        )
        ProductReview.objects.create(
            tenant=self.other_tenant,
            product=self.other_product,
            rating=1,
            status=ProductReview.Status.APPROVED,
            author_name="Outra loja",
        )

        summaries = product_review_summary_queries.get_product_review_summaries(
            tenant_id=self.tenant.id,
            product_ids=[self.product.id, self.empty_product.id, self.product.id, "invalid"],
        )

        self.assertEqual(set(summaries.keys()), {self.product.id, self.empty_product.id})
        self.assertEqual(summaries[self.product.id]["review_count"], 2)
        self.assertEqual(summaries[self.product.id]["rating_average"], "4.0")
        self.assertEqual(summaries[self.product.id]["status"], "ready")
        self.assertEqual(summaries[self.empty_product.id], {"review_count": 0, "rating_average": "0.0", "status": "empty"})

    def test_product_review_bulk_summaries_require_tenant_and_product_ids(self):
        self.assertEqual(
            product_review_summary_queries.get_product_review_summaries(
                tenant_id=None,
                product_ids=[self.product.id],
            ),
            {},
        )
        self.assertEqual(
            product_review_summary_queries.get_product_review_summaries(
                tenant_id=self.tenant.id,
                product_ids=[],
            ),
            {},
        )

    def test_list_approved_product_reviews_hides_pending_and_rejected(self):
        approved = ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=5,
            title="Gostei",
            body="Entrega boa e produto correto.",
            status=ProductReview.Status.APPROVED,
            author_name="Cliente A",
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            rating=2,
            status=ProductReview.Status.REJECTED,
            author_name="Cliente B",
        )

        reviews = product_review_summary_queries.list_approved_product_reviews(
            tenant_id=self.tenant.id,
            product_id=self.product.id,
            limit=5,
        )

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0]["rating"], approved.rating)
        self.assertEqual(reviews[0]["title"], "Gostei")
        self.assertEqual(reviews[0]["author_name"], "Cliente A")

    def test_product_review_summary_requires_tenant_and_product(self):
        self.assertEqual(
            product_review_summary_queries.get_product_review_summary(tenant_id=None, product_id=self.product.id),
            {"review_count": 0, "rating_average": "0.0", "status": "empty"},
        )
        self.assertEqual(
            product_review_summary_queries.list_approved_product_reviews(tenant_id=self.tenant.id, product_id=None),
            [],
        )
