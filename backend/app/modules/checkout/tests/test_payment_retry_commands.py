from django.test import TestCase

from app.modules.catalog.models import Product, ProductVariant
from app.modules.checkout.application.checkout_reorder_commands import checkout_reorder_commands
from app.modules.customers.models import Customer
from app.modules.checkout.application.checkout_payment_retry_commands import checkout_payment_retry_commands
from app.modules.checkout.models import CheckoutSession
from app.modules.orders.models import Order, OrderItem
from app.modules.payments.models import PaymentAttempt
from app.modules.tenants.models import Tenant


class CheckoutPaymentRetryCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Retry Tenant",
            slug="hubx-retry-tenant",
            subdomain="hubx-retry-tenant",
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ana-retry",
            reference="#RETRY-1",
            full_name="Ana Retry",
            email="ana.retry@hubx.market",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="6001",
            status="pending",
            customer_name="Ana Retry",
            customer_email="ana.retry@hubx.market",
            fulfillment_status_label="Aguardando novo pagamento",
            fulfillment_status_variant="warning",
            payment_status="Pagamento falhou",
            payment_source_type="external_payment_failed",
            payment_source_label="Gateway Stripe",
            payment_reference="pi_fail_6001",
            shipping_status="Aguardando nova tentativa",
            shipping_address_summary="Rua Retry, 60 · São Paulo/SP",
            notes_content="Um evento externo informou falha no pagamento. O pedido continua salvo e aguarda uma nova tentativa segura de pagamento.",
            subtotal="199.90",
            shipping_total="20.00",
            discount_total="0.00",
            total="219.90",
        )
        OrderItem.objects.create(
            order=self.order,
            title="Tênis Retry Ready",
            subtitle="Preto · 42",
            meta="SKU RETRY-001",
            variant_sku="RETRY-001",
            price_snapshot="199.90",
            quantity=1,
            sort_order=1,
        )

    def test_bootstrap_from_failed_order_recreates_payment_retry_session(self):
        product = Product.objects.create(
            tenant=self.tenant,
            name="Tênis Retry Ready",
            slug="tenis-retry-ready",
            brand_name="Hubx",
            category_label="Calçados",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RETRY-001",
            price="209.90",
            stock=7,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        result, session_key = checkout_payment_retry_commands.bootstrap_from_failed_order(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            email=self.customer.email,
            order_number="6001",
        )

        self.assertEqual(result, "payment-retry-ready")
        self.assertTrue(session_key)

        session = CheckoutSession.objects.get(session_key=session_key)
        self.assertEqual(session.items.count(), 1)
        self.assertEqual(session.items.first().variant_sku, "RETRY-001")
        self.assertEqual(session.payment_method_selected, "credit_card")
        self.assertFalse(session.accept_terms)
        self.assertEqual(self.order.payment_attempts.count(), 1)
        self.assertEqual(self.order.payment_attempts.first().status, PaymentAttempt.Status.PENDING)

    def test_bootstrap_from_failed_order_blocks_non_failed_order(self):
        self.order.payment_status = "Pagamento pendente"
        self.order.payment_source_type = "checkout_pending"
        self.order.save(update_fields=["payment_status", "payment_source_type", "updated_at"])

        result, session_key = checkout_payment_retry_commands.bootstrap_from_failed_order(
            tenant_id=self.tenant.id,
            customer_id=self.customer.id,
            email=self.customer.email,
            order_number="6001",
        )

        self.assertEqual(result, "payment-retry-blocked")
        self.assertIsNone(session_key)

    def test_bootstrap_from_failed_order_requires_resolved_tenant_context(self):
        result, session_key = checkout_payment_retry_commands.bootstrap_from_failed_order(
            tenant_id=None,
            customer_id=self.customer.id,
            email=self.customer.email,
            order_number="6001",
        )

        self.assertEqual(result, "payment-retry-unavailable")
        self.assertIsNone(session_key)

    def test_reorder_bootstrap_requires_resolved_tenant_context(self):
        result, session_key = checkout_reorder_commands.bootstrap_from_order(
            tenant_id=None,
            customer_id=self.customer.id,
            email=self.customer.email,
            order_number="6001",
        )

        self.assertEqual(result, "reorder-lite-unavailable")
        self.assertIsNone(session_key)
