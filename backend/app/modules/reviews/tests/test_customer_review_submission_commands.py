from django.test import TestCase

from app.modules.catalog.models import Product, ProductVariant
from app.modules.customers.models import Customer
from app.modules.orders.models import Order
from app.modules.reviews.application.customer_review_submission_commands import customer_review_submission_commands
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


class CustomerReviewSubmissionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Customer Review", slug="customer-review", subdomain="customer-review")
        self.other_tenant = Tenant.objects.create(name="Other Customer Review", slug="other-customer-review", subdomain="other-customer-review")
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Comprado",
            slug="produto-comprado",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="CUSTOMER-REVIEW-SKU",
            price="99.00",
            stock=10,
        )
        self.other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto Outro Tenant",
            slug="produto-outro-tenant-review",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-review-publica",
            full_name="Cliente Review Pública",
            email="cliente.review.publica@example.com",
        )
        self.other_customer = Customer.objects.create(
            tenant=self.other_tenant,
            slug="cliente-outro-review",
            full_name="Cliente Outro Review",
            email="cliente.outro.review@example.com",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="1001",
            status=Order.Status.SHIPPED,
            fulfillment_status_label="Concluído",
            shipping_status="Entregue",
        )
        self.order.items.create(
            title=self.product.name,
            product_id_snapshot=self.product.id,
            product_slug_snapshot=self.product.slug,
            variant_sku=self.variant.sku,
            price_snapshot="99.00",
            quantity=1,
        )

    def test_customer_review_submission_creates_pending_review(self):
        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=self.product.id,
            rating=5,
            title="Gostei muito",
            body="Produto chegou bem e cumpriu o prometido.",
            author_name="Cliente Feliz",
            consent_display_name=True,
        )

        self.assertEqual(result, "customer-review-submitted-pending")
        self.assertEqual(review.tenant, self.tenant)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.customer, self.customer)
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertEqual(review.author_name, "Cliente Feliz")

    def test_customer_review_submission_hides_name_without_consent(self):
        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=self.product.id,
            rating=4,
            author_name="Nome Privado",
            consent_display_name=False,
        )

        self.assertEqual(result, "customer-review-submitted-pending")
        self.assertEqual(review.author_name, "Cliente")

    def test_customer_review_submission_blocks_invalid_rating(self):
        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=self.product.id,
            rating=6,
        )

        self.assertEqual(result, "customer-review-invalid-rating")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_customer_review_submission_blocks_not_delivered_order(self):
        self.order.status = Order.Status.PAID
        self.order.fulfillment_status_label = "Separando itens"
        self.order.shipping_status = "Preparando envio"
        self.order.save(update_fields=["status", "fulfillment_status_label", "shipping_status", "updated_at"])

        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=self.product.id,
            rating=5,
        )

        self.assertEqual(result, "customer-review-ineligible")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_customer_review_submission_blocks_cross_tenant_customer(self):
        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.other_customer.id,
            order_number=self.order.number,
            product_id=self.product.id,
            rating=5,
        )

        self.assertEqual(result, "customer-review-ineligible")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_customer_review_submission_blocks_cross_tenant_product(self):
        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=self.other_product.id,
            rating=5,
        )

        self.assertEqual(result, "customer-review-ineligible")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_customer_review_submission_blocks_product_not_in_order(self):
        other_product_same_tenant = Product.objects.create(
            tenant=self.tenant,
            name="Outro Produto",
            slug="outro-produto-review",
            status=Product.Status.ACTIVE,
            is_active=True,
        )

        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=other_product_same_tenant.id,
            rating=5,
        )

        self.assertEqual(result, "customer-review-ineligible")
        self.assertIsNone(review)
        self.assertFalse(ProductReview.objects.exists())

    def test_customer_review_submission_blocks_duplicate_review(self):
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            customer=self.customer,
            rating=5,
            title="Já avaliado",
        )

        result, review = customer_review_submission_commands.submit_customer_product_review(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            order_number=self.order.number,
            product_id=self.product.id,
            rating=4,
        )

        self.assertEqual(result, "customer-review-duplicate")
        self.assertIsNone(review)
        self.assertEqual(ProductReview.objects.count(), 1)
