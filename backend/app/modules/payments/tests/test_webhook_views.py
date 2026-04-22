import json
import hashlib
import hmac

from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.catalog.models import Product, ProductVariant
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.payments.infrastructure.alert_signal_metrics import (
    get_payment_alert_signal_snapshot,
    reset_payment_alert_signal,
)
from app.modules.payments.models import PaymentAttempt
from app.modules.tenants.models import Tenant


@override_settings(
    PAYMENTS_WEBHOOK_TOKEN="test-webhook-token",
    PAGARME_SECRET_KEY="sk_test_webhook",
    PAYMENTS_OBSERVABILITY_TOKEN="ops-token",
    ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost", "127.0.0.1"],
)
class PaymentWebhookViewTests(TestCase):
    def setUp(self):
        reset_payment_alert_signal("webhook.invalid_signature")
        reset_payment_alert_signal("webhook.tenant_unavailable")
        reset_payment_alert_signal("hosted_redirect.unavailable")
        self.tenant = Tenant.objects.create(
            name="Hubx Webhook Tenant",
            slug="hubx-webhook-tenant",
            subdomain="hubx-webhook-tenant",
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ana-webhook",
            reference="#WEB-1",
            full_name="Ana Webhook",
            email="ana.webhook@hubx.market",
        )
        self.product = Product.objects.create(
            tenant=self.tenant,
            name="Tênis Webhook Ready",
            slug="tenis-webhook-ready",
            brand_name="Hubx",
            category_label="Calçados",
            status="active",
            is_active=True,
        )
        self.variant = ProductVariant.objects.create(
            product=self.product,
            sku="WEBHOOK-001",
            price="219.90",
            stock=5,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="5001",
            status="pending",
            customer_name="Ana Webhook",
            customer_email="ana.webhook@hubx.market",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            payment_reference="",
            shipping_status="Aguardando confirmação",
            shipping_address_summary="Rua Webhook, 500 · São Paulo/SP",
            notes_content="Pedido iniciado a partir da revisão do checkout. Aguardando evolução do fluxo de pagamento.",
            subtotal="219.90",
            shipping_total="20.00",
            discount_total="0.00",
            total="239.90",
        )
        OrderItem.objects.create(
            order=self.order,
            title="Tênis Webhook Ready",
            subtitle="Cinza · 41",
            meta="SKU WEBHOOK-001",
            variant_sku="WEBHOOK-001",
            price_snapshot="219.90",
            quantity=1,
            sort_order=1,
        )
        self.payment_attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="credit_card",
            provider_code="credit_card",
            provider_label="Cartão de crédito",
            status=PaymentAttempt.Status.PENDING,
            amount="239.90",
        )

    def _post(self, payload: dict[str, object], *, token: str = "test-webhook-token"):
        body = json.dumps(payload)
        return self.client.post(
            reverse("payments:webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUBX_WEBHOOK_TOKEN=token,
        )

    def _post_pagarme(self, payload: dict[str, object], *, signature: str | None = None):
        body = json.dumps(payload)
        webhook_signature = signature or hmac.new(
            b"sk_test_webhook",
            body.encode("utf-8"),
            hashlib.sha1,
        ).hexdigest()
        return self.client.post(
            reverse("payments:webhook"),
            data=body,
            content_type="application/json",
            HTTP_X_HUB_SIGNATURE=webhook_signature,
        )

    def test_payment_webhook_confirms_external_payment(self):
        response = self._post(
            {
                "event_type": "payment.paid",
                "tenant_slug": self.tenant.slug,
                "order_number": "5001",
                "payment_reference": "ch_123",
                "payment_source_label": "Gateway Pagar.me",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "payment-confirmed")

        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.payment_attempt.refresh_from_db()

        self.assertEqual(self.order.status, "paid")
        self.assertEqual(self.order.payment_status, "Pagamento confirmado")
        self.assertEqual(self.order.payment_source_type, "external_payment")
        self.assertEqual(self.order.payment_source_label, "Gateway Pagar.me")
        self.assertEqual(self.order.payment_reference, "ch_123")
        self.assertIsNotNone(self.order.payment_confirmed_at)
        self.assertEqual(self.payment_attempt.status, PaymentAttempt.Status.PAID)
        self.assertEqual(self.payment_attempt.external_reference, "ch_123")
        self.assertIsNotNone(self.payment_attempt.paid_at)
        self.assertEqual(self.variant.stock, 4)
        self.assertEqual(self.variant.reserved_stock, 1)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=self.order,
                event_type="payment_paid_external",
                source_type="payment_event",
            ).exists()
        )

    def test_payment_webhook_is_idempotent_safe(self):
        first_response = self._post(
            {
                "event_type": "payment.paid",
                "tenant_subdomain": self.tenant.subdomain,
                "order_number": "5001",
                "payment_reference": "ch_123",
                "provider": "Gateway Pagar.me",
            }
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = self._post(
            {
                "event_type": "payment.paid",
                "tenant_subdomain": self.tenant.subdomain,
                "order_number": "5001",
                "payment_reference": "ch_123",
                "provider": "Gateway Pagar.me",
            }
        )

        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()["result"], "payment-already-confirmed")
        self.assertEqual(
            OrderStatusHistory.objects.filter(order=self.order, event_type="payment_paid_external").count(),
            1,
        )

    def test_payment_webhook_rejects_invalid_token(self):
        response = self._post(
            {
                "event_type": "payment.paid",
                "tenant_slug": self.tenant.slug,
                "order_number": "5001",
            },
            token="wrong-token",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["result"], "payment-webhook-forbidden")

    def test_payment_webhook_rejects_unsupported_event(self):
        response = self._post(
            {
                "event_type": "payment.refunded",
                "tenant_slug": self.tenant.slug,
                "order_number": "5001",
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["result"], "payment-webhook-unsupported-event")

    def test_payment_webhook_marks_external_failure_without_stock_impact(self):
        response = self._post(
            {
                "event_type": "payment.failed",
                "tenant_slug": self.tenant.slug,
                "order_number": "5001",
                "payment_reference": "ch_fail_123",
                "payment_source_label": "Gateway Pagar.me",
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "payment-failed")

        self.order.refresh_from_db()
        self.variant.refresh_from_db()
        self.payment_attempt.refresh_from_db()

        self.assertEqual(self.order.status, "pending")
        self.assertEqual(self.order.payment_status, "Pagamento falhou")
        self.assertEqual(self.order.payment_source_type, "external_payment_failed")
        self.assertEqual(self.order.payment_reference, "ch_fail_123")
        self.assertIsNotNone(self.order.payment_failed_at)
        self.assertEqual(self.payment_attempt.status, PaymentAttempt.Status.FAILED)
        self.assertEqual(self.payment_attempt.external_reference, "ch_fail_123")
        self.assertIsNotNone(self.payment_attempt.failed_at)
        self.assertIsNone(self.order.inventory_reserved_at)
        self.assertEqual(self.variant.stock, 5)
        self.assertEqual(self.variant.reserved_stock, 0)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=self.order,
                event_type="payment_failed_external",
                source_type="payment_event",
            ).exists()
        )

    def test_payment_webhook_normalizes_pagarme_style_payload(self):
        response = self._post_pagarme(
            {
                "provider": "pagarme",
                "type": "order.paid",
                "data": {
                    "id": "pg_order_123",
                    "metadata": {
                        "tenant_slug": self.tenant.slug,
                        "order_number": "5001",
                    },
                    "charges": [
                        {
                            "id": "pg_ch_123",
                        }
                    ],
                },
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "payment-confirmed")

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_source_label, "Pagar.me")
        self.assertEqual(self.order.payment_reference, "pg_ch_123")

    def test_payment_webhook_normalizes_stripe_style_payload(self):
        response = self._post(
            {
                "provider": "stripe",
                "type": "payment_intent.succeeded",
                "data": {
                    "object": {
                        "id": "pi_987",
                        "metadata": {
                            "tenant_subdomain": self.tenant.subdomain,
                            "order_number": "5001",
                        },
                    }
                },
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "payment-confirmed")

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_source_label, "stripe")
        self.assertEqual(self.order.payment_reference, "pi_987")

    def test_payment_webhook_normalizes_failed_stripe_style_payload(self):
        response = self._post(
            {
                "provider": "stripe",
                "type": "payment_intent.payment_failed",
                "data": {
                    "object": {
                        "id": "pi_fail_987",
                        "metadata": {
                            "tenant_subdomain": self.tenant.subdomain,
                            "order_number": "5001",
                        },
                    }
                },
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["result"], "payment-failed")

        self.order.refresh_from_db()
        self.assertEqual(self.order.payment_source_label, "stripe")
        self.assertEqual(self.order.payment_reference, "pi_fail_987")

    def test_payment_webhook_rejects_invalid_pagarme_signature(self):
        response = self._post_pagarme(
            {
                "provider": "pagarme",
                "type": "charge.paid",
                "data": {
                    "id": "pg_ch_invalid",
                    "metadata": {
                        "tenant_slug": self.tenant.slug,
                        "order_number": "5001",
                    },
                },
            },
            signature="invalid-signature",
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["result"], "payment-webhook-invalid-signature")
        self.assertEqual(get_payment_alert_signal_snapshot("webhook.invalid_signature")["count"], 1)

    def test_payment_webhook_records_alert_signal_when_tenant_cannot_be_resolved(self):
        response = self._post(
            {
                "event_type": "payment.paid",
                "tenant_slug": "tenant-inexistente",
                "order_number": "5001",
                "payment_reference": "ch_missing_tenant",
                "payment_source_label": "Gateway Pagar.me",
            }
        )

        snapshot = get_payment_alert_signal_snapshot("webhook.tenant_unavailable")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["result"], "payment-webhook-tenant-unavailable")
        self.assertEqual(snapshot["count"], 1)
        self.assertEqual(snapshot["order_number"], "5001")
        self.assertEqual(snapshot["provider_code"], "Gateway Pagar.me")
        self.assertEqual(snapshot["reason_code"], "payment.paid")

    def test_hosted_payment_redirect_redirects_to_provider_action_url(self):
        response = self.client.get(
            reverse("payments:hosted-redirect", kwargs={"attempt_key": self.payment_attempt.attempt_key}),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("https://payments.hubx.local/credit_card/pay/", response["Location"])

        self.payment_attempt.refresh_from_db()
        self.assertTrue(str(self.payment_attempt.external_reference).startswith("ext-payatt-"))
        self.assertIn("provider_intent", self.payment_attempt.metadata)

    def test_hosted_payment_redirect_returns_to_back_url_when_attempt_is_unavailable(self):
        self.payment_attempt.status = PaymentAttempt.Status.PAID
        self.payment_attempt.save(update_fields=["status", "updated_at"])

        response = self.client.get(
            reverse("payments:hosted-redirect", kwargs={"attempt_key": self.payment_attempt.attempt_key}),
            {"back_url": reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f'{reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})}?result=hosted-payment-unavailable',
            response["Location"],
        )
        self.assertEqual(get_payment_alert_signal_snapshot("hosted_redirect.unavailable")["count"], 1)
        self.payment_attempt.refresh_from_db()
        self.assertEqual(self.payment_attempt.metadata["timeline"][-1]["code"], "hosted_redirect_unavailable")

    def test_hosted_payment_return_registers_success_hint_and_redirects_back(self):
        response = self.client.get(
            reverse("payments:hosted-return", kwargs={"attempt_key": self.payment_attempt.attempt_key}),
            {
                "back_url": reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number}),
                "status": "succeeded",
                "payment_reference": "pi_return_123",
                "provider": "Gateway Stripe",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f'{reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})}?result=hosted-payment-return-pending-verification',
            response["Location"],
        )
        self.payment_attempt.refresh_from_db()
        self.assertEqual(self.payment_attempt.external_reference, "pi_return_123")
        self.assertIn("provider_return", self.payment_attempt.metadata)
        self.assertEqual(self.payment_attempt.metadata["provider_return"]["status_hint"], "succeeded")

    def test_hosted_payment_redirect_requires_resolved_tenant_context(self):
        response = self.client.get(
            reverse("payments:hosted-redirect", kwargs={"attempt_key": self.payment_attempt.attempt_key}),
            {"back_url": reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f'{reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})}?result=hosted-payment-unavailable',
            response["Location"],
        )
        self.payment_attempt.refresh_from_db()
        self.assertEqual(self.payment_attempt.external_reference, "")
        self.assertNotIn("provider_intent", self.payment_attempt.metadata)

    def test_hosted_payment_return_requires_resolved_tenant_context(self):
        response = self.client.get(
            reverse("payments:hosted-return", kwargs={"attempt_key": self.payment_attempt.attempt_key}),
            {
                "back_url": reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number}),
                "status": "succeeded",
                "payment_reference": "pi_return_123",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f'{reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})}?result=hosted-payment-unavailable',
            response["Location"],
        )
        self.payment_attempt.refresh_from_db()
        self.assertEqual(self.payment_attempt.external_reference, "")
        self.assertNotIn("provider_return", self.payment_attempt.metadata)

    def test_payment_alert_metrics_requires_internal_observability_token(self):
        response = self.client.get(reverse("payments:alert-metrics"))

        self.assertEqual(response.status_code, 403)

    def test_payment_alert_metrics_exports_prometheus_counters_for_recorded_signals(self):
        self._post_pagarme(
            {
                "provider": "pagarme",
                "type": "charge.paid",
                "data": {
                    "id": "pg_ch_invalid",
                    "metadata": {
                        "tenant_slug": self.tenant.slug,
                        "order_number": "5001",
                    },
                },
            },
            signature="invalid-signature",
        )

        response = self.client.get(
            reverse("payments:alert-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="ops-token",
        )

        body = response.content.decode("utf-8")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8")
        self.assertIn("# TYPE hubx_payments_alert_signal_total counter", body)
        self.assertIn('hubx_payments_alert_signal_total{signal_code="webhook.invalid_signature"} 1', body)
        self.assertIn(
            'hubx_payments_alert_signal_last_timestamp_seconds{signal_code="webhook.invalid_signature"}',
            body,
        )

    def test_payment_alert_metrics_accepts_bearer_authorization_token(self):
        self._post_pagarme(
            {
                "provider": "pagarme",
                "type": "charge.paid",
                "data": {
                    "id": "pg_ch_invalid_bearer",
                    "metadata": {
                        "tenant_slug": self.tenant.slug,
                        "order_number": "5001",
                    },
                },
            },
            signature="invalid-signature",
        )

        response = self.client.get(
            reverse("payments:alert-metrics"),
            HTTP_AUTHORIZATION="Bearer ops-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'hubx_payments_alert_signal_total{signal_code="webhook.invalid_signature"} 1',
            response.content.decode("utf-8"),
        )

    def test_hosted_payment_return_registers_failed_hint_and_redirects_back(self):
        response = self.client.get(
            reverse("payments:hosted-return", kwargs={"attempt_key": self.payment_attempt.attempt_key}),
            {
                "back_url": reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number}),
                "status": "failed",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f'{reverse("accounts:account-order-detail", kwargs={"order_number": self.order.number})}?result=hosted-payment-return-failed',
            response["Location"],
        )
