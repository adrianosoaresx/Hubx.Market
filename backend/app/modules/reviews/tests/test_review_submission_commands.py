from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.reviews.application.review_submission_commands import product_review_submission_commands
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


class ProductReviewSubmissionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Review Submission", slug="review-submission", subdomain="review-submission")
        self.other_tenant = Tenant.objects.create(name="Other Review Submission", slug="other-review-submission", subdomain="other-review-submission")
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Review",
            slug="produto-review",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto Outro Tenant",
            slug="produto-outro-tenant",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-review",
            reference="#1001",
            full_name="Ana Review",
            email="ana.review@example.com",
            status="active",
        )

    def test_submit_product_review_creates_pending_review_for_tenant_product(self):
        result, review = product_review_submission_commands.submit_product_review(
            tenant_id=self.tenant.id,
            product_slug="produto-review",
            rating=5,
            title="Ótimo produto",
            body="Gostei da experiência.",
            author_name="Ana",
            customer_id=self.customer.id,
            source="internal_test",
        )

        self.assertEqual(result, "review-submitted-pending")
        self.assertEqual(review.tenant, self.tenant)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.customer, self.customer)
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.title, "Ótimo produto")

    def test_submit_product_review_blocks_invalid_rating(self):
        result, review = product_review_submission_commands.submit_product_review(
            tenant_id=self.tenant.id,
            product_id=self.product.id,
            rating=6,
            title="Inválida",
        )

        self.assertEqual(result, "review-submission-blocked")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_submit_product_review_does_not_cross_tenant_products(self):
        result, review = product_review_submission_commands.submit_product_review(
            tenant_id=self.tenant.id,
            product_id=self.other_product.id,
            rating=5,
            title="Cross tenant",
        )

        self.assertEqual(result, "review-product-not-found")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_submit_product_review_ignores_cross_tenant_customer(self):
        other_customer = Customer.objects.create(
            tenant=self.other_tenant,
            slug="cliente-outro",
            reference="#2001",
            full_name="Outro Cliente",
            email="outro@example.com",
            status="active",
        )

        result, review = product_review_submission_commands.submit_product_review(
            tenant_id=self.tenant.id,
            product_id=self.product.id,
            rating=4,
            title="Sem customer cross-tenant",
            customer_id=other_customer.id,
        )

        self.assertEqual(result, "review-submitted-pending")
        self.assertIsNone(review.customer)
        self.assertEqual(review.author_name, "Cliente")

    def test_submit_product_review_management_command(self):
        stdout = StringIO()

        call_command(
            "submit_product_review",
            tenant_id=self.tenant.id,
            product_slug="produto-review",
            rating=5,
            title="Via CLI",
            author_name="Ops",
            stdout=stdout,
        )

        review = ProductReview.objects.get()
        self.assertIn("product_review_submission result=review-submitted-pending", stdout.getvalue())
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertEqual(review.title, "Via CLI")
        self.assertEqual(review.author_name, "Ops")
