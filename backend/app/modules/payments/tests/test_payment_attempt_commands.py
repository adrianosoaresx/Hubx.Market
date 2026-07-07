import json
from urllib.error import URLError
from unittest.mock import MagicMock, patch

from django.db import IntegrityError
from django.test import TestCase
from django.test import override_settings

from app.modules.payments.application.gateway_bootstrap_commands import gateway_bootstrap_commands
from app.modules.payments.application.provider_adapter_commands import provider_adapter_commands
from app.modules.orders.models import Order
from app.modules.payments.application.payment_attempt_commands import payment_attempt_commands
from app.modules.payments.infrastructure.alert_signal_metrics import (
    get_payment_alert_signal_snapshot,
    reset_payment_alert_signal,
)
from app.modules.payments.domain.webhook_normalization import normalize_payment_webhook
from app.modules.payments.models import PaymentAttempt
from app.modules.tenants.models import Tenant


@override_settings(
    PAYMENTS_PROVIDER_DEFAULT="pagarme",
    PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="sandbox",
    PAGARME_API_BASE_URL="https://api.pagar.me/core/v5",
    PAGARME_SECRET_KEY="sk_test_hubx",
)
class PaymentAttemptCommandTests(TestCase):
    def setUp(self):
        reset_payment_alert_signal("provider_intent.failed")
        reset_payment_alert_signal("provider_rollout.blocked")
        self.tenant = Tenant.objects.create(
            name="Hubx Payment Attempt Tenant",
            slug="hubx-payment-attempt-tenant",
            subdomain="hubx-payment-attempt-tenant",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="8101",
            status="pending",
            customer_name="Ana Attempt",
            customer_email="ana.attempt@hubx.market",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            payment_reference="",
            shipping_status="Aguardando confirmação",
            shipping_address_summary="Rua Attempt, 81 · São Paulo/SP",
            notes_content="Pedido pronto para tentativa de pagamento.",
            subtotal="199.90",
            shipping_total="20.00",
            discount_total="0.00",
            total="219.90",
        )

    def test_bootstrap_pending_attempt_creates_single_pending_record(self):
        first_result, first_attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pix",
            provider_label="PIX",
        )

        second_result, second_attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pix",
            provider_label="PIX",
        )

        self.assertEqual(first_result, "payment-attempt-ready")
        self.assertEqual(second_result, "payment-attempt-ready")
        self.assertIsNotNone(first_attempt)
        self.assertEqual(first_attempt.id, second_attempt.id)
        self.assertEqual(PaymentAttempt.objects.count(), 1)
        self.assertEqual(first_attempt.status, PaymentAttempt.Status.PENDING)
        self.assertEqual(first_attempt.metadata["timeline"][0]["code"], "attempt_created")
        self.assertEqual(first_attempt.metadata["checkout_session_key"], "")

    def test_bootstrap_pending_attempt_persists_checkout_session_trace_when_provided(self):
        result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pix",
            provider_label="PIX",
            source_session_key="sess-123",
        )

        self.assertEqual(result, "payment-attempt-ready")
        self.assertEqual(attempt.metadata["checkout_session_key"], "sess-123")
        self.assertIn("sess-123", attempt.metadata["timeline"][0]["description"])

    def test_payment_attempt_model_allows_only_one_pending_attempt_per_order(self):
        result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pix",
            provider_label="PIX",
        )

        self.assertEqual(result, "payment-attempt-ready")
        self.assertIsNotNone(attempt)

        with self.assertRaises(IntegrityError):
            PaymentAttempt.objects.create(
                tenant=self.tenant,
                order=self.order,
                payment_method_code="pix",
                provider_code="pix",
                provider_label="PIX",
                status=PaymentAttempt.Status.PENDING,
                amount="219.90",
                currency_code="BRL",
                metadata={},
            )

    def test_bootstrap_pending_attempt_recovers_when_pending_attempt_wins_race(self):
        class RacingRepository:
            def __init__(self, *, order, tenant):
                self.order = order
                self.tenant = tenant
                self.lookup_count = 0
                self.pending_attempt = PaymentAttempt.objects.create(
                    tenant=self.tenant,
                    order=self.order,
                    payment_method_code="pix",
                    provider_code="pix",
                    provider_label="PIX",
                    status=PaymentAttempt.Status.PENDING,
                    amount="219.90",
                    currency_code="BRL",
                    metadata={},
                )

            def get_order(self, *, tenant_id, order_number):
                return self.order if tenant_id == self.tenant.id and order_number == self.order.number else None

            def get_latest_pending_attempt(self, *, order_id):
                self.lookup_count += 1
                if self.lookup_count == 1:
                    return None
                if self.pending_attempt is not None and order_id == self.order.id:
                    return self.pending_attempt
                return None

            def get_latest_attempt_for_order(self, *, order_id):
                return self.pending_attempt if order_id == self.order.id else None

            def get_attempt_by_external_reference(self, *, tenant_id, external_reference):
                return None

            def create_attempt(self, **kwargs):
                raise IntegrityError("simulated-race")

            def save_attempt(self, attempt) -> None:
                attempt.save()

        racing_service = payment_attempt_commands.__class__(
            repository=RacingRepository(order=self.order, tenant=self.tenant)
        )

        result, attempt = racing_service.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pix",
            provider_label="PIX",
        )

        self.assertEqual(result, "payment-attempt-ready")
        self.assertIsNotNone(attempt)
        self.assertEqual(PaymentAttempt.objects.filter(order=self.order, status=PaymentAttempt.Status.PENDING).count(), 1)

    def test_reconcile_external_event_marks_attempt_paid(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="credit_card",
            provider_code="credit_card",
            provider_label="Cartão de crédito",
        )

        reconciled = payment_attempt_commands.reconcile_external_event(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            event_type="payment.paid",
            external_reference="pi_8101",
            provider_label="Gateway Stripe",
        )

        attempt.refresh_from_db()
        self.assertEqual(reconciled.id, attempt.id)
        self.assertEqual(attempt.status, PaymentAttempt.Status.PAID)
        self.assertEqual(attempt.external_reference, "pi_8101")
        self.assertEqual(attempt.provider_label, "Gateway Stripe")
        self.assertIsNotNone(attempt.paid_at)

    def test_gateway_bootstrap_builds_idempotent_contract_for_pending_attempt(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Gateway Pagar.me",
        )

        first_result, first_contract = gateway_bootstrap_commands.build_contract(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )
        second_result, second_contract = gateway_bootstrap_commands.build_contract(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(first_result, "gateway-bootstrap-ready")
        self.assertEqual(second_result, "gateway-bootstrap-ready")
        self.assertEqual(first_contract.provider_request_key, second_contract.provider_request_key)
        self.assertEqual(first_contract.order_number, self.order.number)
        self.assertEqual(first_contract.amount, "219.90")
        self.assertEqual(first_contract.provider_code, "pagarme")
        self.assertEqual(first_contract.metadata["tenant_slug"], self.tenant.slug)
        self.assertTrue(attempt.provider_request_key.startswith("payatt-"))
        self.assertIsNotNone(attempt.bootstrapped_at)
        self.assertEqual(attempt.metadata["timeline"][-1]["code"], "gateway_bootstrapped")

    def test_gateway_bootstrap_rejects_missing_pending_attempt(self):
        result, contract = gateway_bootstrap_commands.build_contract(
            tenant_id=self.tenant.id,
            attempt_key="00000000-0000-0000-0000-000000000000",
        )

        self.assertEqual(result, "gateway-bootstrap-unavailable")
        self.assertIsNone(contract)

    def test_gateway_bootstrap_requires_resolved_tenant_context(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Gateway Pagar.me",
        )

        result, contract = gateway_bootstrap_commands.build_contract(
            tenant_id=None,
            attempt_key=str(attempt.attempt_key),
        )

        self.assertEqual(result, "gateway-bootstrap-unavailable")
        self.assertIsNone(contract)

    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_provider_adapter_creates_real_pagarme_intent_and_reuses_cached_response(self, mocked_urlopen):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Gateway Pagar.me",
        )
        mocked_response = mocked_urlopen.return_value.__enter__.return_value
        mocked_response.read.return_value = json.dumps(
            {
                "id": "plink_123",
                "url": "https://checkout.pagar.me/link/plink_123",
            }
        ).encode("utf-8")

        first_result, first_response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )
        second_result, second_response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(first_result, "provider-intent-ready")
        self.assertEqual(second_result, "provider-intent-ready")
        self.assertEqual(first_response.external_reference, second_response.external_reference)
        self.assertEqual(first_response.external_reference, attempt.external_reference)
        self.assertIn("provider_intent", attempt.metadata)
        self.assertEqual(attempt.metadata["provider_intent"]["provider_code"], "pagarme")
        self.assertEqual(first_response.action_url, "https://checkout.pagar.me/link/plink_123")
        self.assertEqual(mocked_urlopen.call_count, 1)

        request = mocked_urlopen.call_args.args[0]
        request_payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(request.full_url, "https://api.pagar.me/core/v5/paymentlinks")
        self.assertEqual(request_payload["type"], "order")
        self.assertEqual(request_payload["order_code"], self.order.number)
        self.assertEqual(request_payload["payment_settings"]["accepted_payment_methods"], ["pix"])
        self.assertEqual(request_payload["payment_settings"]["pix_settings"]["expires_in"], 30)
        self.assertEqual(request_payload["cart_settings"]["items"][0]["amount"], 21990)
        self.assertEqual(request_payload["cart_settings"]["items"][0]["default_quantity"], 1)
        self.assertEqual(request.get_header("Authorization"), "Basic c2tfdGVzdF9odWJ4Og==")

    @override_settings(
        PAYMENTS_PROVIDER_DEFAULT="asaas",
        ASAAS_API_KEY="asaas_test_key",
        ASAAS_BASE_URL="https://api-sandbox.asaas.com/v3",
    )
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_provider_adapter_creates_real_asaas_hosted_payment(self, mocked_urlopen):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
        )
        customer_context = MagicMock()
        customer_context.__enter__.return_value.read.return_value = json.dumps({"id": "cus_123"}).encode("utf-8")
        payment_context = MagicMock()
        payment_context.__enter__.return_value.read.return_value = json.dumps(
            {
                "id": "pay_123",
                "invoiceUrl": "https://sandbox.asaas.com/i/pay_123",
            }
        ).encode("utf-8")
        mocked_urlopen.side_effect = [customer_context, payment_context]

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(result, "provider-intent-ready")
        self.assertEqual(attempt.provider_code, "asaas")
        self.assertEqual(attempt.provider_label, "Asaas")
        self.assertEqual(response.provider_code, "asaas")
        self.assertEqual(response.action_url, "https://sandbox.asaas.com/i/pay_123")
        self.assertEqual(attempt.external_reference, "pay_123")
        self.assertEqual(mocked_urlopen.call_count, 2)

        customer_request = mocked_urlopen.call_args_list[0].args[0]
        payment_request = mocked_urlopen.call_args_list[1].args[0]
        customer_payload = json.loads(customer_request.data.decode("utf-8"))
        payment_payload = json.loads(payment_request.data.decode("utf-8"))
        self.assertEqual(customer_request.full_url, "https://api-sandbox.asaas.com/v3/customers")
        self.assertEqual(payment_request.full_url, "https://api-sandbox.asaas.com/v3/payments")
        self.assertEqual(customer_request.get_header("Access_token"), "asaas_test_key")
        self.assertEqual(customer_payload["externalReference"], "hubx-market:hubx-payment-attempt-tenant:8101")
        self.assertEqual(payment_payload["customer"], "cus_123")
        self.assertEqual(payment_payload["billingType"], "PIX")
        self.assertEqual(payment_payload["value"], 219.9)
        self.assertEqual(payment_payload["externalReference"], "hubx-market:hubx-payment-attempt-tenant:8101")

    def test_asaas_webhook_normalizes_payment_received(self):
        normalized = normalize_payment_webhook(
            {
                "event": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_123",
                    "externalReference": "hubx-market:hubx-payment-attempt-tenant:8101",
                },
            }
        )

        self.assertIsNotNone(normalized)
        self.assertEqual(normalized.event_type, "payment.paid")
        self.assertEqual(normalized.tenant_subdomain, "hubx-payment-attempt-tenant")
        self.assertEqual(normalized.order_number, "8101")
        self.assertEqual(normalized.payment_reference, "pay_123")
        self.assertEqual(normalized.payment_source_label, "Asaas")

    def test_bootstrap_pending_attempt_defaults_provider_to_configured_gateway(self):
        result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="credit_card",
        )

        self.assertEqual(result, "payment-attempt-ready")
        self.assertEqual(attempt.provider_code, "pagarme")
        self.assertEqual(attempt.provider_label, "Pagar.me")

    def test_provider_adapter_rejects_paid_attempt(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="credit_card",
            provider_code="stripe",
            provider_label="Gateway Stripe",
        )
        payment_attempt_commands.reconcile_external_event(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            event_type="payment.paid",
            external_reference="pi_8101",
            provider_label="Gateway Stripe",
        )

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        self.assertEqual(result, "provider-intent-unavailable")
        self.assertIsNone(response)

    def test_provider_adapter_requires_resolved_tenant_context(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Gateway Pagar.me",
        )

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=None,
            attempt_key=str(attempt.attempt_key),
        )

        self.assertEqual(result, "provider-intent-unavailable")
        self.assertIsNone(response)

    @override_settings(
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="controlled",
        PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS="outro-tenant",
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
    )
    def test_provider_adapter_blocks_real_intent_for_non_allowlisted_tenant(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
        )

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(result, "provider-intent-unavailable")
        self.assertIsNone(response)
        self.assertEqual(attempt.metadata["provider_rollout"]["rollout_mode"], "controlled")
        self.assertEqual(attempt.metadata["provider_rollout"]["reason_code"], "tenant-not-allowlisted")
        self.assertEqual(attempt.metadata["timeline"][-1]["code"], "provider_rollout_blocked")
        self.assertEqual(get_payment_alert_signal_snapshot("provider_rollout.blocked")["count"], 1)

    @override_settings(
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="controlled",
        PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS="hubx-payment-attempt-tenant",
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
    )
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_provider_adapter_allows_real_intent_for_allowlisted_tenant(self, mocked_urlopen):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
        )
        mocked_response = mocked_urlopen.return_value.__enter__.return_value
        mocked_response.read.return_value = json.dumps(
            {
                "id": "plink_allow_123",
                "url": "https://checkout.pagar.me/link/plink_allow_123",
            }
        ).encode("utf-8")

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(result, "provider-intent-ready")
        self.assertIsNotNone(response)
        self.assertEqual(attempt.metadata["provider_rollout"]["reason_code"], "tenant-allowlisted")
        self.assertTrue(attempt.metadata["provider_rollout"]["real_provider_active"])
        self.assertEqual(mocked_urlopen.call_count, 1)

    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_provider_adapter_records_alert_signal_when_real_provider_fails(self, mocked_urlopen):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Gateway Pagar.me",
        )
        mocked_urlopen.side_effect = URLError("offline")

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        snapshot = get_payment_alert_signal_snapshot("provider_intent.failed")
        self.assertEqual(result, "provider-intent-unavailable")
        self.assertIsNone(response)
        self.assertEqual(snapshot["count"], 1)
        self.assertEqual(snapshot["tenant_id"], self.tenant.id)
        self.assertEqual(snapshot["order_number"], self.order.number)
        self.assertEqual(snapshot["provider_code"], "pagarme")
        self.assertEqual(snapshot["reason_code"], "pagarme-network-unavailable")
        attempt.refresh_from_db()
        self.assertEqual(attempt.metadata["provider_intent_failure"]["reason_code"], "pagarme-network-unavailable")
        self.assertEqual(attempt.metadata["timeline"][-1]["code"], "provider_intent_failed")

    @override_settings(
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="live",
        PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=False,
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
    )
    def test_provider_adapter_blocks_live_global_without_explicit_flag(self):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
        )

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(result, "provider-intent-unavailable")
        self.assertIsNone(response)
        self.assertEqual(attempt.metadata["provider_rollout"]["rollout_mode"], "live")
        self.assertEqual(attempt.metadata["provider_rollout"]["reason_code"], "live-global-not-enabled")

    @override_settings(
        PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE="live",
        PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=True,
        PAYMENTS_REAL_PROVIDER_FALLBACK_MODE="block",
    )
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_provider_adapter_allows_live_global_with_explicit_flag(self, mocked_urlopen):
        _result, attempt = payment_attempt_commands.bootstrap_pending_attempt(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
        )
        mocked_response = mocked_urlopen.return_value.__enter__.return_value
        mocked_response.read.return_value = json.dumps(
            {
                "id": "plink_live_123",
                "url": "https://checkout.pagar.me/link/plink_live_123",
            }
        ).encode("utf-8")

        result, response = provider_adapter_commands.create_external_intent(
            tenant_id=self.tenant.id,
            attempt_key=str(attempt.attempt_key),
        )

        attempt.refresh_from_db()
        self.assertEqual(result, "provider-intent-ready")
        self.assertIsNotNone(response)
        self.assertEqual(attempt.metadata["provider_rollout"]["reason_code"], "live-global-enabled")
        self.assertTrue(attempt.metadata["provider_rollout"]["real_provider_active"])
