from django.test import TestCase

from app.modules.catalog.models import Product, ProductVariant
from app.modules.customers.models import Customer
from app.modules.orders.models import Order
from app.modules.reviews.application.review_eligibility_queries import review_eligibility_queries
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


class ReviewEligibilityQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Review Eligibility", slug="review-eligibility", subdomain="review-eligibility")
        self.other_tenant = Tenant.objects.create(name="Other Review Eligibility", slug="other-review-eligibility", subdomain="other-review-eligibility")
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Elegível",
            slug="produto-elegivel",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="ELIGIBLE-SKU",
            price="99.00",
            stock=10,
        )
        self.other_product = Product.objects.create(
            tenant=self.other_tenant,
            name="Produto Outro Tenant",
            slug="produto-outro-tenant",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=self.other_product,
            sku="OTHER-ELIGIBLE-SKU",
            price="99.00",
            stock=10,
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-elegivel",
            full_name="Cliente Elegível",
            email="cliente.elegivel@example.com",
        )
        self.other_customer = Customer.objects.create(
            tenant=self.other_tenant,
            slug="cliente-outro",
            full_name="Cliente Outro",
            email="cliente.outro@example.com",
        )

    def _order(self, *, status="shipped", fulfillment_status_label="Concluído", shipping_status="Entregue"):
        order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="1001",
            status=status,
            fulfillment_status_label=fulfillment_status_label,
            shipping_status=shipping_status,
        )
        order.items.create(
            title=self.product.name,
            product_id_snapshot=self.product.id,
            product_slug_snapshot=self.product.slug,
            variant_sku=self.variant.sku,
            price_snapshot="99.00",
            quantity=1,
        )
        return order

    def test_customer_with_delivered_order_for_product_is_eligible(self):
        self._order()

        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertTrue(result["eligible"])
        self.assertEqual(result["result"], "review-eligible")
        self.assertEqual(result["order_number"], "1001")

    def test_customer_without_purchase_is_not_eligible(self):
        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["result"], "review-ineligible-no-purchase")

    def test_customer_with_legacy_sku_only_order_is_still_eligible(self):
        order = self._order()
        order.items.update(product_id_snapshot=None, product_slug_snapshot="")

        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertTrue(result["eligible"])
        self.assertEqual(result["result"], "review-eligible")

    def test_snapshot_takes_precedence_over_legacy_sku_fallback(self):
        other_product_same_tenant = Product.objects.create(
            tenant=self.tenant,
            name="Outro Produto Mesmo Tenant",
            slug="outro-produto-mesmo-tenant",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        order = self._order()
        order.items.update(
            product_id_snapshot=other_product_same_tenant.id,
            product_slug_snapshot=other_product_same_tenant.slug,
            variant_sku=self.variant.sku,
        )

        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["result"], "review-ineligible-no-purchase")

    def test_customer_with_paid_but_not_delivered_order_is_not_eligible(self):
        self._order(status="paid", fulfillment_status_label="Separando itens", shipping_status="Preparando envio")

        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["result"], "review-ineligible-not-delivered")

    def test_duplicate_customer_product_review_is_not_eligible(self):
        self._order()
        ProductReview.objects.create(
            tenant=self.tenant,
            product=self.product,
            customer=self.customer,
            rating=5,
            title="Já avaliei",
        )

        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.product.id,
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["result"], "review-ineligible-duplicate")

    def test_cross_tenant_customer_is_not_found(self):
        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.other_customer.id,
            product_id=self.product.id,
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["result"], "review-ineligible-customer-not-found")

    def test_cross_tenant_product_is_not_found(self):
        result = review_eligibility_queries.can_customer_review_product(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            product_id=self.other_product.id,
        )

        self.assertFalse(result["eligible"])
        self.assertEqual(result["result"], "review-ineligible-product-not-found")
