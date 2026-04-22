from django.test import TestCase

from app.modules.catalog.models import Product, ProductVariant
from app.modules.customers.models import Customer
from app.modules.orders.application.customer_order_payment_commands import customer_order_payment_commands
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.tenants.models import Tenant


class ExternalPaymentCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Payment Tenant",
            slug="hubx-payment-tenant",
            subdomain="hubx-payment-tenant",
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ana-payment",
            reference="#PAY-1",
            full_name="Ana Payment",
            email="ana.payment@hubx.market",
        )
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Tênis Payment Ready",
            slug="tenis-payment-ready",
            brand_name="Hubx",
            category_label="Calçados",
            status="active",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="PAY-READY-001",
            price="199.90",
            stock=8,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="4001",
            status="pending",
            customer_name="Ana Payment",
            customer_email="ana.payment@hubx.market",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            payment_reference="",
            shipping_status="Aguardando confirmação",
            shipping_address_summary="Rua Payment, 100 · São Paulo/SP",
            notes_content="Pedido iniciado a partir da revisão do checkout. Aguardando evolução do fluxo de pagamento.",
            subtotal="199.90",
            shipping_total="20.00",
            discount_total="0.00",
            total="219.90",
        )
        OrderItem.objects.create(
            order=self.order,
            title="Tênis Payment Ready",
            subtitle="Azul · 40",
            meta="SKU PAY-READY-001",
            variant_sku="PAY-READY-001",
            price_snapshot="199.90",
            quantity=1,
            sort_order=1,
        )

    def test_confirm_external_payment_marks_order_paid_and_records_reference(self):
        result = customer_order_payment_commands.confirm_external_payment(
            tenant_id=self.tenant.id,
            order_number="4001",
            payment_reference="pi_12345",
            payment_source_label="Gateway Stripe",
        )

        self.assertEqual(result, "payment-confirmed")

        self.order.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.order.payment_status, "Pagamento confirmado")
        self.assertEqual(self.order.payment_source_type, "external_payment")
        self.assertEqual(self.order.payment_source_label, "Gateway Stripe")
        self.assertEqual(self.order.payment_reference, "pi_12345")
        self.assertIsNotNone(self.order.payment_confirmed_at)
        self.assertIsNotNone(self.order.inventory_reserved_at)
        self.assertEqual(self.order.fulfillment_status_label, "Separando itens")
        self.assertEqual(self.order.shipping_status, "Preparando envio")
        self.assertEqual(self.variant.stock, 7)
        self.assertEqual(self.variant.reserved_stock, 2)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=self.order,
                event_type="payment_paid_external",
                source_type="payment_event",
                source_label="Gateway Stripe",
            ).exists()
        )
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=self.order,
                event_type="inventory_reserved_after_payment",
                source_type="payment_event",
            ).exists()
        )

    def test_confirm_external_payment_is_idempotent_safe_for_paid_order(self):
        first_result = customer_order_payment_commands.confirm_external_payment(
            tenant_id=self.tenant.id,
            order_number="4001",
            payment_reference="pi_12345",
            payment_source_label="Gateway Stripe",
        )
        self.assertEqual(first_result, "payment-confirmed")

        self.variant.refresh_from_db()
        stock_after_first = self.variant.stock
        reserved_after_first = self.variant.reserved_stock

        second_result = customer_order_payment_commands.confirm_external_payment(
            tenant_id=self.tenant.id,
            order_number="4001",
            payment_reference="pi_12345",
            payment_source_label="Gateway Stripe",
        )

        self.assertEqual(second_result, "payment-already-confirmed")

        self.order.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(self.order.payment_reference, "pi_12345")
        self.assertEqual(self.variant.stock, stock_after_first)
        self.assertEqual(self.variant.reserved_stock, reserved_after_first)
        self.assertEqual(
            OrderStatusHistory.objects.filter(order=self.order, event_type="payment_paid_external").count(),
            1,
        )

    def test_confirm_external_payment_requires_resolved_tenant_context(self):
        result = customer_order_payment_commands.confirm_external_payment(
            tenant_id=None,
            order_number="4001",
            payment_reference="pi_12345",
            payment_source_label="Gateway Stripe",
        )

        self.assertEqual(result, "payment-confirmation-unavailable")

    def test_confirm_internal_payment_requires_resolved_tenant_context(self):
        result = customer_order_payment_commands.confirm_internal_payment(
            tenant_id=None,
            customer_id=self.customer.id,
            email=self.customer.email,
            order_number="4001",
        )

        self.assertEqual(result, "payment-confirmation-unavailable")

    def test_fail_external_payment_marks_order_pending_without_stock_impact(self):
        result = customer_order_payment_commands.fail_external_payment(
            tenant_id=self.tenant.id,
            order_number="4001",
            payment_reference="pi_fail_123",
            payment_source_label="Gateway Stripe",
        )

        self.assertEqual(result, "payment-failed")

        self.order.refresh_from_db()
        self.variant.refresh_from_db()

        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.order.payment_status, "Pagamento falhou")
        self.assertEqual(self.order.payment_source_type, "external_payment_failed")
        self.assertEqual(self.order.payment_source_label, "Gateway Stripe")
        self.assertEqual(self.order.payment_reference, "pi_fail_123")
        self.assertIsNotNone(self.order.payment_failed_at)
        self.assertIsNone(self.order.inventory_reserved_at)
        self.assertEqual(self.order.fulfillment_status_label, "Aguardando novo pagamento")
        self.assertEqual(self.order.shipping_status, "Aguardando nova tentativa")
        self.assertEqual(self.variant.stock, 8)
        self.assertEqual(self.variant.reserved_stock, 1)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=self.order,
                event_type="payment_failed_external",
                source_type="payment_event",
                source_label="Gateway Stripe",
            ).exists()
        )

    def test_fail_external_payment_is_blocked_after_order_is_paid(self):
        confirm_result = customer_order_payment_commands.confirm_external_payment(
            tenant_id=self.tenant.id,
            order_number="4001",
            payment_reference="pi_12345",
            payment_source_label="Gateway Stripe",
        )
        self.assertEqual(confirm_result, "payment-confirmed")

        failed_result = customer_order_payment_commands.fail_external_payment(
            tenant_id=self.tenant.id,
            order_number="4001",
            payment_reference="pi_fail_123",
            payment_source_label="Gateway Stripe",
        )

        self.assertEqual(failed_result, "payment-failure-blocked")

    def test_fail_external_payment_requires_resolved_tenant_context(self):
        result = customer_order_payment_commands.fail_external_payment(
            tenant_id=None,
            order_number="4001",
            payment_reference="pi_fail_123",
            payment_source_label="Gateway Stripe",
        )

        self.assertEqual(result, "payment-confirmation-unavailable")
