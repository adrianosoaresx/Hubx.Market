from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings

from app.modules.catalog.models import Product, ProductVariant
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.payments.models import PaymentAttempt
from app.modules.tenants.models import Tenant


class PaymentSandboxReadinessCommandTests(SimpleTestCase):
    @override_settings(
        PAYMENTS_PROVIDER_DEFAULT="pagarme",
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="controlled",
        PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS="sandbox-a,sandbox-b",
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
        PAGARME_SECRET_KEY="sk_test_hubx",
        PAGARME_API_BASE_URL="https://api.pagar.me/core/v5",
        PAGARME_WEBHOOK_SIGNATURE_HEADER="X-Hub-Signature",
        PAYMENTS_WEBHOOK_TOKEN="fallback-token",
    )
    def test_command_reports_ready_when_required_settings_are_present(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_readiness",
            webhook_url="https://sandbox.example.com/payments/webhook/",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] Provider default", output)
        self.assertIn("[OK] Provider rollout mode", output)
        self.assertIn("[OK] Enabled rollout tenants", output)
        self.assertIn("[OK] Provider fallback mode", output)
        self.assertIn("payment_sandbox_readiness=ready", output)

    @override_settings(
        PAYMENTS_PROVIDER_DEFAULT="",
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="controlled",
        PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS=[],
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="",
        PAGARME_SECRET_KEY="",
        PAGARME_API_BASE_URL="",
        PAGARME_WEBHOOK_SIGNATURE_HEADER="",
        PAYMENTS_WEBHOOK_TOKEN="",
    )
    def test_command_reports_blockers_when_settings_are_missing(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_readiness",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[BLOCKED] Provider default", output)
        self.assertIn("[OK] Provider rollout mode", output)
        self.assertIn("[BLOCKED] Enabled rollout tenants", output)
        self.assertIn("[BLOCKED] Provider fallback mode", output)
        self.assertIn("[BLOCKED] Pagar.me secret key", output)
        self.assertIn("[BLOCKED] Public webhook URL", output)
        self.assertIn("payment_sandbox_readiness=blocked", output)


@override_settings(
    PAYMENTS_PROVIDER_DEFAULT="pagarme",
    PAGARME_SECRET_KEY="sk_test_hubx",
    PAGARME_API_BASE_URL="https://api.pagar.me/core/v5",
    PAGARME_WEBHOOK_SIGNATURE_HEADER="X-Hub-Signature",
)
class PaymentSandboxValidateWebhookCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Sandbox Validate Tenant",
            slug="sandbox-validate-tenant",
            subdomain="sandbox-validate-tenant",
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="sandbox-customer",
            reference="#SB-1",
            full_name="Sandbox Customer",
            email="sandbox.customer@hubx.market",
        )
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Sandbox",
            slug="produto-sandbox",
            brand_name="Hubx",
            category_label="Teste",
            status="active",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="SANDBOX-001",
            price="119.90",
            stock=4,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9199",
            status="pending",
            customer_name="Sandbox Customer",
            customer_email="sandbox.customer@hubx.market",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            payment_reference="",
            shipping_status="Aguardando confirmação",
            shipping_address_summary="Rua Sandbox, 99",
            notes_content="Pedido sandbox.",
            subtotal="109.90",
            shipping_total="10.00",
            discount_total="0.00",
            total="119.90",
        )
        OrderItem.objects.create(
            order=self.order,
            title="Produto Sandbox",
            subtitle="Único",
            meta="SKU SANDBOX-001",
            variant_sku="SANDBOX-001",
            price_snapshot="119.90",
            quantity=1,
            sort_order=1,
        )
        self.attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="119.90",
        )

    def test_command_confirms_paid_webhook_and_reconciles_order(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_validate_webhook",
            tenant_slug=self.tenant.slug,
            order_number=self.order.number,
            stdout=stdout,
        )

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()
        self.variant.refresh_from_db()
        output = stdout.getvalue()

        self.assertIn("result=payment-confirmed", output)
        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.order.payment_status, "Pagamento confirmado")
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.PAID)
        self.assertEqual(self.variant.stock, 3)

    def test_command_marks_failed_webhook_without_inventory_impact(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_validate_webhook",
            tenant_slug=self.tenant.slug,
            order_number=self.order.number,
            event="failed",
            stdout=stdout,
        )

        self.order.refresh_from_db()
        self.attempt.refresh_from_db()
        self.variant.refresh_from_db()
        output = stdout.getvalue()

        self.assertIn("result=payment-failed", output)
        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.order.payment_status, "Pagamento falhou")
        self.assertEqual(self.attempt.status, PaymentAttempt.Status.FAILED)
        self.assertEqual(self.variant.stock, 4)
