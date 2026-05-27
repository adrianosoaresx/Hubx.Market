from django.test import TestCase

from app.modules.catalog.models import Product
from app.modules.customers.models import Customer
from app.modules.reviews.application.customer_review_status_queries import customer_review_status_queries
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


class CustomerReviewStatusQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Review Status", slug="review-status", subdomain="review-status")
        self.other_tenant = Tenant.objects.create(name="Other Review Status", slug="other-review-status", subdomain="other-review-status")
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-review-status",
            full_name="Cliente Review Status",
            email="cliente.review.status@example.com",
        )
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Status",
            slug="produto-status",
            status=Product.Status.ACTIVE,
            is_active=True,
        )

    def test_get_customer_product_review_status_returns_empty_when_missing(self):
        status = customer_review_status_queries.get_customer_product_review_status(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertFalse(status["found"])
        self.assertEqual(status["status"], "")

    def test_get_customer_product_review_status_returns_pending_label(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            product=self.product,
            rating=5,
            title="Pendente",
        )

        status = customer_review_status_queries.get_customer_product_review_status(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertTrue(status["found"])
        self.assertEqual(status["status"], ProductReview.Status.PENDING)
        self.assertEqual(status["status_label"], "Avaliação em moderação")

    def test_get_customer_product_review_status_is_tenant_scoped(self):
        other_customer = Customer.objects.create(
            tenant=self.other_tenant,
            slug="cliente-review-status-outro",
            full_name="Cliente Review Status Outro",
            email="cliente.review.status.outro@example.com",
        )
        other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto Status Outro",
            slug="produto-status-outro",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductReview.objects.create(
            tenant=self.other_tenant,
            customer=other_customer,
            product=other_product,
            rating=5,
            title="Outro tenant",
        )

        status = customer_review_status_queries.get_customer_product_review_status(
            tenant_id=self.tenant.id,
            customer_id=other_customer.id,
            product_id=other_product.id,
        )

        self.assertFalse(status["found"])
