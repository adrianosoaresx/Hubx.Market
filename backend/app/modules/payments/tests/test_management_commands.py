from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from app.modules.catalog.models import Product, ProductVariant
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.payments.models import PaymentAttempt
from app.modules.payments.models import PaymentRefund
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
        self.assertIn("[OK] Live global flag", output)
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
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="live",
        PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=False,
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
        PAGARME_SECRET_KEY="sk_live_hubx",
        PAGARME_API_BASE_URL="https://api.pagar.me/core/v5",
        PAGARME_WEBHOOK_SIGNATURE_HEADER="X-Hub-Signature",
    )
    def test_command_blocks_production_live_without_explicit_global_flag(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_readiness",
            target="production",
            webhook_url="https://store.hubx.market/payments/webhook/",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] Provider rollout mode", output)
        self.assertIn("[OK] Provider fallback mode", output)
        self.assertIn("[BLOCKED] Live global flag", output)
        self.assertIn("payment_production_readiness=blocked", output)

    @override_settings(
        PAYMENTS_PROVIDER_DEFAULT="pagarme",
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="controlled",
        PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS="tenant-a",
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
        PAGARME_SECRET_KEY="sk_live_hubx",
        PAGARME_API_BASE_URL="https://api.pagar.me/core/v5",
        PAGARME_WEBHOOK_SIGNATURE_HEADER="X-Hub-Signature",
    )
    def test_command_reports_production_ready_for_controlled_rollout(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_readiness",
            target="production",
            webhook_url="https://store.hubx.market/payments/webhook/",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("[OK] Provider rollout mode", output)
        self.assertIn("[OK] Enabled rollout tenants", output)
        self.assertIn("[OK] Provider fallback mode", output)
        self.assertIn("payment_production_readiness=ready", output)


class ListPaymentAttemptsCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="List Attempts Tenant", slug="list-attempts", subdomain="list-attempts")
        self.other_tenant = Tenant.objects.create(name="Other Attempts Tenant", slug="other-attempts", subdomain="other-attempts")
        self.order = Order.objects.create(tenant=self.tenant, number="9301", customer_email="list@example.com")
        self.other_order = Order.objects.create(tenant=self.other_tenant, number="9302", customer_email="other-list@example.com")
        self.pending_attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="10.00",
        )
        self.failed_attempt = PaymentAttempt.objects.create(
            tenant=self.other_tenant,
            order=self.other_order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.FAILED,
            amount="10.00",
        )
        PaymentAttempt.objects.filter(id=self.pending_attempt.id).update(updated_at=timezone.now() - timedelta(hours=8))

    def test_list_payment_attempts_filters_by_tenant_and_status(self):
        stdout = StringIO()

        call_command(
            "list_payment_attempts",
            tenant_id=str(self.tenant.id),
            status="pending",
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("order_number=9301", output)
        self.assertNotIn("order_number=9302", output)
        self.assertIn("payment_attempts=1", output)

    def test_list_payment_attempts_filters_stale_pending_attempts(self):
        stdout = StringIO()

        call_command("list_payment_attempts", stale_hours=6, stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("order_number=9301", output)
        self.assertNotIn("order_number=9302", output)


class ListPaymentReconciliationIssuesCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Reconciliation Tenant", slug="reconciliation", subdomain="reconciliation")
        self.other_tenant = Tenant.objects.create(name="Other Reconciliation Tenant", slug="other-reconciliation", subdomain="other-reconciliation")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9401",
            status="pending",
            customer_email="reconciliation@example.com",
            payment_status="Pagamento pendente",
            payment_reference="",
            total="120.00",
        )
        self.other_order = Order.objects.create(
            tenant=self.other_tenant,
            number="9402",
            status="pending",
            customer_email="other-reconciliation@example.com",
            payment_status="Pagamento pendente",
            total="80.00",
        )

    def test_list_payment_reconciliation_issues_reports_paid_attempt_without_confirmed_order(self):
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9401",
            paid_at=timezone.now(),
        )

        stdout = StringIO()
        call_command("list_payment_reconciliation_issues", tenant_id=self.tenant.id, stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("issue_code=attempt_paid_order_unconfirmed", output)
        self.assertIn("severity=critical", output)
        self.assertIn("order_number=9401", output)

    def test_list_payment_reconciliation_issues_reports_amount_mismatch_and_filters_tenant(self):
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="110.00",
        )
        PaymentAttempt.objects.create(
            tenant=self.other_tenant,
            order=self.other_order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="70.00",
        )

        stdout = StringIO()
        call_command("list_payment_reconciliation_issues", tenant_id=self.tenant.id, stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("issue_code=attempt_amount_mismatch", output)
        self.assertIn("order_number=9401", output)
        self.assertNotIn("order_number=9402", output)

    def test_list_payment_reconciliation_issues_reports_zero_when_clean(self):
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount="120.00",
        )

        stdout = StringIO()
        call_command("list_payment_reconciliation_issues", tenant_id=self.tenant.id, stdout=stdout)

        self.assertIn("payment_reconciliation_issues=0", stdout.getvalue())


class ListPaymentRefundCandidatesCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Refund Tenant", slug="refund-tenant", subdomain="refund-tenant")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9601",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9601",
            total="120.00",
        )

    def test_list_payment_refund_candidates_reports_ready_paid_order(self):
        attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9601",
            paid_at=timezone.now(),
        )

        stdout = StringIO()
        call_command("list_payment_refund_candidates", tenant_id=self.tenant.id, stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("order_number=9601", output)
        self.assertIn("readiness=ready", output)
        self.assertIn(f"attempt_key={attempt.attempt_key}", output)
        self.assertIn("external_reference=ch_9601", output)

    def test_list_payment_refund_candidates_reports_blockers(self):
        self.order.status = "shipped"
        self.order.save(update_fields=["status", "updated_at"])
        PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9601",
            paid_at=timezone.now(),
        )

        stdout = StringIO()
        call_command("list_payment_refund_candidates", tenant_id=self.tenant.id, stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("readiness=blocked", output)
        self.assertIn("order-already-shipped", output)

    def test_list_payment_refund_candidates_requires_tenant(self):
        stdout = StringIO()

        call_command("list_payment_refund_candidates", stdout=stdout)

        self.assertIn("payment_refund_candidates=blocked reason=tenant-required", stdout.getvalue())


class PaymentSandboxValidateRefundCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Sandbox Refund Tenant", slug="sandbox-refund", subdomain="sandbox-refund")
        self.other_tenant = Tenant.objects.create(name="Other Sandbox Refund", slug="other-sandbox-refund", subdomain="other-sandbox-refund")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9709",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9709",
            total="120.00",
        )
        self.attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9709",
            paid_at=timezone.now(),
        )
        self.refund = PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-9709",
            status=PaymentRefund.Status.PROCESSING,
            amount="120.00",
            currency_code="BRL",
            provider_code="lite",
            external_reference="ch_9709",
            reason_code="sandbox-validation",
            requested_at=timezone.now(),
        )

    def test_payment_sandbox_validate_refund_dry_run_reports_candidate_without_execution(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_validate_refund",
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            dry_run=True,
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        output = stdout.getvalue()
        self.assertIn("payment_sandbox_refund_candidate", output)
        self.assertIn("order_number=9709", output)
        self.assertIn("payment_sandbox_refund_validation=dry-run result=ready", output)
        self.assertEqual(self.refund.status, PaymentRefund.Status.PROCESSING)
        self.assertEqual(self.refund.provider_refund_reference, "")

    def test_payment_sandbox_validate_refund_blocks_non_processing_refund(self):
        self.refund.status = PaymentRefund.Status.REQUESTED
        self.refund.save(update_fields=["status", "updated_at"])
        stdout = StringIO()

        call_command(
            "payment_sandbox_validate_refund",
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            stdout=stdout,
        )

        output = stdout.getvalue()
        self.assertIn("payment_sandbox_refund_validation=blocked reason=refund-not-processing", output)

    def test_payment_sandbox_validate_refund_executes_via_command_service_with_lite_adapter(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_validate_refund",
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        output = stdout.getvalue()
        self.assertIn("result=refund-execution-accepted", output)
        self.assertEqual(self.refund.status, PaymentRefund.Status.PROCESSING)
        self.assertTrue(self.refund.provider_refund_reference)
        self.assertEqual(self.refund.metadata["provider_refund"]["status"], "accepted")

    def test_payment_sandbox_validate_refund_is_tenant_scoped(self):
        stdout = StringIO()

        call_command(
            "payment_sandbox_validate_refund",
            tenant_id=self.other_tenant.id,
            refund_key=str(self.refund.refund_key),
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        self.assertIn("payment_sandbox_refund_validation=unavailable reason=refund-not-found", stdout.getvalue())
        self.assertEqual(self.refund.provider_refund_reference, "")


class PaymentRefundSandboxEvidenceCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Refund Evidence Tenant", slug="refund-evidence", subdomain="refund-evidence")
        self.other_tenant = Tenant.objects.create(name="Other Refund Evidence", slug="other-refund-evidence", subdomain="other-refund-evidence")
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9810",
            status="paid",
            payment_status="Pagamento confirmado",
            payment_reference="ch_9810",
            total="120.00",
        )
        self.attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PAID,
            amount="120.00",
            external_reference="ch_9810",
            paid_at=timezone.now(),
        )
        self.refund = PaymentRefund.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_attempt=self.attempt,
            idempotency_key="refund-9810",
            status=PaymentRefund.Status.PROCESSING,
            amount="120.00",
            currency_code="BRL",
            provider_code="pagarme",
            external_reference="ch_9810",
            provider_refund_reference="rf_9810",
            reason_code="sandbox-evidence",
            metadata={
                "provider_refund": {
                    "provider_code": "pagarme",
                    "provider_refund_reference": "rf_9810",
                    "status": "accepted",
                    "payload_snapshot": {"id": "rf_9810"},
                }
            },
            requested_at=timezone.now(),
        )

    def test_capture_payment_refund_sandbox_evidence_writes_metadata_only(self):
        stdout = StringIO()

        call_command(
            "capture_payment_refund_sandbox_evidence",
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            captured_by="Ops Finance",
            decision="sandbox-observed",
            dry_run_output="payment_sandbox_refund_validation=dry-run result=ready",
            execution_output="result=refund-execution-accepted",
            provider_dashboard_reference="pagarme:rf_9810",
            reconciliation_reference="ops-finance:9810",
            notes="Sandbox observado sem efeitos cross-module.",
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        evidence = self.refund.metadata["sandbox_evidence"]
        self.assertIn("payment_refund_sandbox_evidence result=refund-sandbox-evidence-captured", stdout.getvalue())
        self.assertEqual(evidence["captured_by"], "Ops Finance")
        self.assertEqual(evidence["decision"], "sandbox-observed")
        self.assertEqual(self.refund.status, PaymentRefund.Status.PROCESSING)
        self.assertEqual(self.refund.provider_refund_reference, "rf_9810")
        self.assertEqual(self.refund.metadata["provider_refund"]["provider_refund_reference"], "rf_9810")

    def test_capture_payment_refund_sandbox_evidence_is_tenant_scoped(self):
        stdout = StringIO()

        call_command(
            "capture_payment_refund_sandbox_evidence",
            tenant_id=self.other_tenant.id,
            refund_key=str(self.refund.refund_key),
            captured_by="Ops Finance",
            decision="sandbox-observed",
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        self.assertIn("payment_refund_sandbox_evidence=refund-sandbox-evidence-unavailable", stdout.getvalue())
        self.assertNotIn("sandbox_evidence", self.refund.metadata)

    def test_capture_payment_refund_sandbox_evidence_blocks_sensitive_content(self):
        stdout = StringIO()

        call_command(
            "capture_payment_refund_sandbox_evidence",
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            captured_by="Ops Finance",
            decision="sandbox-observed",
            notes="Authorization: Bearer secret-token",
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        self.assertIn("payment_refund_sandbox_evidence=refund-sandbox-evidence-sensitive-blocked", stdout.getvalue())
        self.assertNotIn("sandbox_evidence", self.refund.metadata)

    def test_capture_payment_refund_sandbox_evidence_requires_references_for_limited_production_go(self):
        stdout = StringIO()

        call_command(
            "capture_payment_refund_sandbox_evidence",
            tenant_id=self.tenant.id,
            refund_key=str(self.refund.refund_key),
            captured_by="Ops Finance",
            decision="go-production-limited",
            provider_dashboard_reference="pagarme:rf_9810",
            stdout=stdout,
        )

        self.refund.refresh_from_db()
        self.assertIn("payment_refund_sandbox_evidence result=refund-sandbox-evidence-blocked", stdout.getvalue())
        self.assertNotIn("sandbox_evidence", self.refund.metadata)


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
