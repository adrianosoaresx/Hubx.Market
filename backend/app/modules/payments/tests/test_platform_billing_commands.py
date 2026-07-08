import json
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from app.modules.accounts.models import OwnerUser
from app.modules.payments.application.platform_billing_commands import platform_billing_commands
from app.modules.payments.application.webhook_commands import payment_webhook_commands
from app.modules.payments.models import PlatformFeeLedger
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription
from app.modules.tenants.models import Tenant


class PlatformBillingCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Pro Billing Tenant",
            slug="pro-billing-tenant",
            subdomain="pro-billing-tenant",
        )
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.pro.billing@hubx.market",
            full_name="Owner Pro Billing",
        )
        subscription_commands.upsert_plan(
            code="pro",
            name="Pro",
            billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            platform_fee_percent="2.00",
            minimum_monthly_fee="259.90",
            requires_billing_method=True,
        )
        subscription_commands.set_tenant_subscription(
            tenant_id=self.tenant.id,
            plan_code="pro",
            status=TenantSubscription.Status.ACTIVE,
        )
        period_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start.replace(month=period_start.month + 1) if period_start.month < 12 else period_start.replace(year=period_start.year + 1, month=1)
        self.ledger = PlatformFeeLedger.objects.create(
            tenant=self.tenant,
            ledger_key=f"minimum:{self.tenant.id}:{period_start.date().isoformat()}",
            kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT,
            status=PlatformFeeLedger.Status.PENDING_COLLECTION,
            plan_code_snapshot="pro",
            billing_model_snapshot=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            platform_fee_percent_snapshot="2.00",
            minimum_monthly_fee_snapshot="259.90",
            billing_period_start=period_start,
            billing_period_end=period_end,
            basis_amount="100.00",
            fee_amount="159.90",
            currency_code="BRL",
        )

    @override_settings(
        PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED=True,
        ASAAS_API_KEY="asaas_platform_key",
        ASAAS_BASE_URL="https://api-sandbox.asaas.com/v3",
        ASAAS_PLATFORM_BILLING_DUE_DAYS=5,
    )
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_create_complementary_charge_creates_customer_and_hosted_asaas_charge(self, mocked_urlopen):
        customer_context = MagicMock()
        customer_context.__enter__.return_value.read.return_value = json.dumps({"id": "cus_platform_123"}).encode("utf-8")
        payment_context = MagicMock()
        payment_context.__enter__.return_value.read.return_value = json.dumps(
            {
                "id": "pay_platform_123",
                "invoiceUrl": "https://sandbox.asaas.com/i/pay_platform_123",
                "status": "PENDING",
            }
        ).encode("utf-8")
        mocked_urlopen.side_effect = [customer_context, payment_context]

        result, ledger = platform_billing_commands.create_complementary_charge_for_ledger(
            ledger_id=self.ledger.id,
            actor_label="test",
        )

        self.assertEqual(result, "platform-billing-charge-created")
        ledger.refresh_from_db()
        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(ledger.provider_code, "asaas")
        self.assertEqual(ledger.provider_payment_reference, "pay_platform_123")
        self.assertEqual(ledger.status, PlatformFeeLedger.Status.PENDING_COLLECTION)
        self.assertEqual(ledger.metadata["provider_call"], "executed")
        self.assertEqual(ledger.metadata["billing_checkout_url"], "https://sandbox.asaas.com/i/pay_platform_123")
        self.assertEqual(subscription.billing_external_reference, "cus_platform_123")
        self.assertEqual(subscription.billing_method_status, TenantSubscription.BillingMethodStatus.PENDING)
        self.assertEqual(subscription.billing_checkout_url, "https://sandbox.asaas.com/i/pay_platform_123")
        self.assertEqual(mocked_urlopen.call_count, 2)

        customer_request = mocked_urlopen.call_args_list[0].args[0]
        payment_request = mocked_urlopen.call_args_list[1].args[0]
        customer_payload = json.loads(customer_request.data.decode("utf-8"))
        payment_payload = json.loads(payment_request.data.decode("utf-8"))
        self.assertEqual(customer_request.full_url, "https://api-sandbox.asaas.com/v3/customers")
        self.assertEqual(payment_request.full_url, "https://api-sandbox.asaas.com/v3/payments")
        self.assertEqual(customer_payload["externalReference"], f"hubx-platform-billing:{self.tenant.id}:{self.tenant.slug}")
        self.assertEqual(customer_payload["email"], "owner.pro.billing@hubx.market")
        self.assertEqual(payment_payload["customer"], "cus_platform_123")
        self.assertEqual(payment_payload["billingType"], "CREDIT_CARD")
        self.assertEqual(payment_payload["value"], 159.9)
        self.assertEqual(payment_payload["externalReference"], f"hubx-platform-fee:{self.ledger.ledger_key}")
        self.assertNotIn("creditCardToken", payment_payload)

    @override_settings(
        PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED=True,
        ASAAS_API_KEY="asaas_platform_key",
        ASAAS_BASE_URL="https://api-sandbox.asaas.com/v3",
    )
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_create_complementary_charge_replay_reuses_existing_provider_reference(self, mocked_urlopen):
        customer_context = MagicMock()
        customer_context.__enter__.return_value.read.return_value = json.dumps({"id": "cus_platform_123"}).encode("utf-8")
        payment_context = MagicMock()
        payment_context.__enter__.return_value.read.return_value = json.dumps(
            {
                "id": "pay_platform_123",
                "invoiceUrl": "https://sandbox.asaas.com/i/pay_platform_123",
                "status": "PENDING",
            }
        ).encode("utf-8")
        mocked_urlopen.side_effect = [customer_context, payment_context]

        first_result, first_ledger = platform_billing_commands.create_complementary_charge_for_ledger(
            ledger_id=self.ledger.id,
            actor_label="test",
        )
        second_result, second_ledger = platform_billing_commands.create_complementary_charge_for_ledger(
            ledger_id=self.ledger.id,
            actor_label="test",
        )

        self.assertEqual(first_result, "platform-billing-charge-created")
        self.assertEqual(second_result, "platform-billing-charge-existing")
        self.assertEqual(first_ledger.id, second_ledger.id)
        self.assertEqual(second_ledger.provider_payment_reference, "pay_platform_123")
        self.assertEqual(mocked_urlopen.call_count, 2)

    @override_settings(
        PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED=True,
        ASAAS_API_KEY="asaas_platform_key",
        ASAAS_BASE_URL="https://api-sandbox.asaas.com/v3",
        ASAAS_PLATFORM_BILLING_REMOTE_IP="203.0.113.10",
    )
    @patch("app.modules.payments.infrastructure.provider_adapters.urlopen")
    def test_create_complementary_charge_uses_existing_tokenized_method_reference(self, mocked_urlopen):
        platform_billing_commands.register_external_billing_method(
            tenant_id=self.tenant.id,
            provider_customer_reference="cus_existing_123",
            provider_method_reference="tokenized-card-reference",
            status=TenantSubscription.BillingMethodStatus.ACTIVE,
            actor_label="test",
            trusted_activation=True,
        )
        payment_context = MagicMock()
        payment_context.__enter__.return_value.read.return_value = json.dumps(
            {
                "id": "pay_token_123",
                "invoiceUrl": "https://sandbox.asaas.com/i/pay_token_123",
                "status": "PENDING",
            }
        ).encode("utf-8")
        mocked_urlopen.side_effect = [payment_context]

        result, ledger = platform_billing_commands.create_complementary_charge_for_ledger(
            ledger_id=self.ledger.id,
            actor_label="test",
        )

        self.assertEqual(result, "platform-billing-charge-created")
        ledger.refresh_from_db()
        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(subscription.billing_method_status, TenantSubscription.BillingMethodStatus.ACTIVE)
        self.assertIsNotNone(subscription.billing_method_verified_at)
        self.assertEqual(mocked_urlopen.call_count, 1)
        payment_request = mocked_urlopen.call_args.args[0]
        payment_payload = json.loads(payment_request.data.decode("utf-8"))
        self.assertEqual(payment_payload["customer"], "cus_existing_123")
        self.assertEqual(payment_payload["creditCardToken"], "tokenized-card-reference")
        self.assertEqual(payment_payload["remoteIp"], "203.0.113.10")
        ledger.refresh_from_db()
        request_snapshot = ledger.metadata["provider_response"]["request"]
        self.assertEqual(request_snapshot["creditCardToken"], "[REDACTED]")
        self.assertNotIn("tokenized-card-reference", json.dumps(ledger.metadata))

    def test_register_external_billing_method_blocks_untrusted_active_token(self):
        result = platform_billing_commands.register_external_billing_method(
            tenant_id=self.tenant.id,
            provider_customer_reference="cus_untrusted_123",
            provider_method_reference="tokenized-card-reference",
            status=TenantSubscription.BillingMethodStatus.ACTIVE,
            actor_label="tenant-owner",
        )

        self.assertEqual(result["result"], "platform-billing-method-unverified")
        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(subscription.billing_method_status, TenantSubscription.BillingMethodStatus.MISSING)
        self.assertEqual(subscription.billing_method_reference, "")
        self.assertEqual(subscription.billing_external_reference, "")

    @override_settings(ASAAS_WEBHOOK_TOKEN="asaas-webhook-token")
    def test_platform_fee_webhook_marks_complementary_charge_paid(self):
        self.ledger.provider_code = "asaas"
        self.ledger.provider_payment_reference = "pay_platform_123"
        self.ledger.save(update_fields=["provider_code", "provider_payment_reference", "updated_at"])

        result, status = payment_webhook_commands.process_webhook(
            payload={
                "event": "PAYMENT_RECEIVED",
                "payment": {
                    "id": "pay_platform_123",
                    "status": "RECEIVED",
                    "externalReference": f"hubx-platform-fee:{self.ledger.ledger_key}",
                },
            },
            provided_token="asaas-webhook-token",
            raw_body=b"{}",
            provided_signature="",
        )

        self.assertEqual(status, 200)
        self.assertEqual(result, "platform-billing-charge-paid")
        self.ledger.refresh_from_db()
        self.assertEqual(self.ledger.status, PlatformFeeLedger.Status.PAID)
        self.assertEqual(self.ledger.metadata["last_provider_event"], "PAYMENT_RECEIVED")

    @override_settings(ASAAS_WEBHOOK_TOKEN="asaas-webhook-token")
    def test_platform_fee_webhook_replay_keeps_single_paid_ledger(self):
        self.ledger.provider_code = "asaas"
        self.ledger.provider_payment_reference = "pay_platform_123"
        self.ledger.save(update_fields=["provider_code", "provider_payment_reference", "updated_at"])
        payload = {
            "event": "PAYMENT_RECEIVED",
            "payment": {
                "id": "pay_platform_123",
                "status": "RECEIVED",
                "externalReference": f"hubx-platform-fee:{self.ledger.ledger_key}",
            },
        }

        first_result, first_status = payment_webhook_commands.process_webhook(
            payload=payload,
            provided_token="asaas-webhook-token",
            raw_body=b"{}",
            provided_signature="",
        )
        second_result, second_status = payment_webhook_commands.process_webhook(
            payload=payload,
            provided_token="asaas-webhook-token",
            raw_body=b"{}",
            provided_signature="",
        )

        self.ledger.refresh_from_db()
        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first_result, "platform-billing-charge-paid")
        self.assertEqual(second_result, "platform-billing-charge-paid")
        self.assertEqual(self.ledger.status, PlatformFeeLedger.Status.PAID)
        self.assertEqual(PlatformFeeLedger.objects.filter(ledger_key=self.ledger.ledger_key).count(), 1)

    @override_settings(
        SUBSCRIPTIONS_PRO_DELINQUENCY_GRACE_DAYS=5,
        SUBSCRIPTIONS_PRO_DELINQUENCY_SUSPEND_DAYS=15,
    )
    def test_apply_pro_delinquency_policy_marks_past_due_suspends_and_reactivates(self):
        period_end = timezone.now() - timedelta(days=7)
        self.ledger.billing_period_end = period_end
        self.ledger.save(update_fields=["billing_period_end", "updated_at"])

        results = platform_billing_commands.apply_pro_delinquency_policy(
            tenant_id=self.tenant.id,
            reference_at=timezone.now(),
            actor_label="test",
        )

        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(results["marked_past_due"], 1)
        self.assertEqual(subscription.status, TenantSubscription.Status.PAST_DUE)

        results = platform_billing_commands.apply_pro_delinquency_policy(
            tenant_id=self.tenant.id,
            reference_at=period_end + timedelta(days=16),
            actor_label="test",
        )

        subscription.refresh_from_db()
        self.assertEqual(results["suspended"], 1)
        self.assertEqual(subscription.status, TenantSubscription.Status.SUSPENDED)

        self.ledger.status = PlatformFeeLedger.Status.PAID
        self.ledger.save(update_fields=["status", "updated_at"])
        results = platform_billing_commands.apply_pro_delinquency_policy(
            tenant_id=self.tenant.id,
            reference_at=timezone.now(),
            actor_label="test",
        )

        subscription.refresh_from_db()
        self.assertEqual(results["reactivated"], 1)
        self.assertEqual(subscription.status, TenantSubscription.Status.ACTIVE)
