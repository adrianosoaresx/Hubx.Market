from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from app.modules.orders.models import Order
from app.modules.payments.application.platform_fee_ledger_commands import platform_fee_ledger_commands
from app.modules.payments.models import PaymentAttempt, PlatformFeeLedger
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription
from app.modules.tenants.models import Tenant


class PlatformFeeLedgerCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Platform Fee Tenant",
            slug="platform-fee-tenant",
            subdomain="platform-fee-tenant",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            number="9901",
            status=Order.Status.PAID,
            payment_status="Pagamento confirmado",
            total="219.90",
        )
        self.attempt = PaymentAttempt.objects.create(
            tenant=self.tenant,
            order=self.order,
            payment_method_code="pix",
            provider_code="asaas",
            provider_label="Asaas",
            status=PaymentAttempt.Status.PAID,
            amount="219.90",
            external_reference="pay_9901",
            metadata={
                "provider_intent": {
                    "payload_snapshot": {
                        "request": {
                            "payment": {
                                "splits": [{"walletId": "wallet_hubx", "percentualValue": 2.0}],
                            }
                        }
                    }
                }
            },
        )

    def _set_plan(self, subscription_status=TenantSubscription.Status.ACTIVE, **overrides):
        payload = {
            "code": "starter",
            "name": "Essencial",
            "billing_model": SubscriptionPlan.BillingModel.TAKE_RATE_ONLY,
            "platform_fee_percent": "2.00",
            "minimum_monthly_fee": "0.00",
        }
        payload.update(overrides)
        subscription_commands.upsert_plan(**payload)
        subscription_commands.set_tenant_subscription(
            tenant_id=self.tenant.id,
            plan_code=payload["code"],
            status=subscription_status,
        )

    def test_record_paid_order_fee_creates_idempotent_split_ledger(self):
        self._set_plan()

        first_result, first_ledger = platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )
        second_result, second_ledger = platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )

        self.assertEqual(first_result, "platform-fee-created")
        self.assertEqual(second_result, "platform-fee-existing")
        self.assertEqual(first_ledger.id, second_ledger.id)
        self.assertEqual(PlatformFeeLedger.objects.count(), 1)
        self.assertEqual(first_ledger.status, PlatformFeeLedger.Status.SPLIT_REQUESTED)
        self.assertEqual(first_ledger.plan_code_snapshot, "starter")
        self.assertEqual(first_ledger.platform_fee_percent_snapshot, Decimal("2.00"))
        self.assertEqual(first_ledger.fee_amount, Decimal("4.40"))
        self.assertEqual(first_ledger.provider_payment_reference, "pay_9901")

    def test_record_paid_order_fee_keeps_platform_fee_for_suspended_subscription(self):
        self._set_plan(subscription_status=TenantSubscription.Status.SUSPENDED)

        result, ledger = platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )

        self.assertEqual(result, "platform-fee-created")
        self.assertEqual(ledger.status, PlatformFeeLedger.Status.SPLIT_REQUESTED)
        self.assertEqual(ledger.fee_amount, Decimal("4.40"))

    def test_record_paid_order_fee_marks_monthly_paid_order_overage(self):
        now = timezone.now()
        self._set_plan(monthly_paid_order_limit=1)
        Order.objects.create(
            tenant=self.tenant,
            number="9900",
            status=Order.Status.PAID,
            payment_status="Pagamento confirmado",
            payment_confirmed_at=now,
            total="50.00",
        )
        self.order.payment_confirmed_at = now
        self.order.save(update_fields=["payment_confirmed_at", "updated_at"])

        result, ledger = platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )

        self.assertEqual(result, "platform-fee-created")
        self.assertTrue(ledger.metadata["commercial_overage"])
        self.assertEqual(ledger.metadata["monthly_paid_order_limit"], 1)
        self.assertEqual(ledger.metadata["monthly_paid_order_count"], 2)
        self.assertEqual(ledger.metadata["overage_count"], 1)

    def test_close_minimum_commitment_creates_difference_for_pro(self):
        self._set_plan(
            code="pro",
            name="Pro",
            billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            minimum_monthly_fee="259.90",
        )
        self.order.total = Decimal("5000.00")
        self.order.save(update_fields=["total", "updated_at"])
        platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )

        result, ledger = platform_fee_ledger_commands.close_minimum_commitment_period(tenant_id=self.tenant.id)

        self.assertEqual(result, "platform-fee-minimum-created")
        self.assertEqual(ledger.kind, PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT)
        self.assertEqual(ledger.status, PlatformFeeLedger.Status.PENDING_COLLECTION)
        self.assertEqual(ledger.basis_amount, Decimal("100.00"))
        self.assertEqual(ledger.fee_amount, Decimal("159.90"))

    def test_close_minimum_commitment_replay_does_not_duplicate_adjustment(self):
        self._set_plan(
            code="pro",
            name="Pro",
            billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            minimum_monthly_fee="259.90",
        )
        self.order.total = Decimal("5000.00")
        self.order.save(update_fields=["total", "updated_at"])
        platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )

        first_result, first_ledger = platform_fee_ledger_commands.close_minimum_commitment_period(tenant_id=self.tenant.id)
        second_result, second_ledger = platform_fee_ledger_commands.close_minimum_commitment_period(tenant_id=self.tenant.id)

        self.assertEqual(first_result, "platform-fee-minimum-created")
        self.assertEqual(second_result, "platform-fee-minimum-existing")
        self.assertEqual(first_ledger.id, second_ledger.id)
        self.assertEqual(
            PlatformFeeLedger.objects.filter(kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT).count(),
            1,
        )

    def test_close_minimum_commitment_uses_billing_period_for_delayed_webhook(self):
        self._set_plan(
            code="pro",
            name="Pro",
            billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            minimum_monthly_fee="259.90",
        )
        current_start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_period_day = current_start - timedelta(days=1)
        previous_start = previous_period_day.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        previous_end = current_start
        PlatformFeeLedger.objects.create(
            tenant=self.tenant,
            ledger_key=f"order:delayed:{previous_start.date().isoformat()}",
            kind=PlatformFeeLedger.Kind.ORDER_TAKE_RATE,
            status=PlatformFeeLedger.Status.SPLIT_REQUESTED,
            plan_code_snapshot="pro",
            billing_model_snapshot=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            platform_fee_percent_snapshot="2.00",
            minimum_monthly_fee_snapshot="259.90",
            billing_period_start=previous_start,
            billing_period_end=previous_end,
            basis_amount="10000.00",
            fee_amount="200.00",
            currency_code="BRL",
        )

        result, ledger = platform_fee_ledger_commands.close_minimum_commitment_period(
            tenant_id=self.tenant.id,
            reference_at=previous_start + timedelta(days=10),
        )

        self.assertEqual(result, "platform-fee-minimum-created")
        self.assertEqual(ledger.basis_amount, Decimal("200.00"))
        self.assertEqual(ledger.fee_amount, Decimal("59.90"))

    def test_close_minimum_commitment_skips_when_take_rate_exceeds_minimum(self):
        self._set_plan(
            code="pro",
            name="Pro",
            billing_model=SubscriptionPlan.BillingModel.MINIMUM_COMMITMENT,
            minimum_monthly_fee="259.90",
        )
        self.order.total = Decimal("20000.00")
        self.order.save(update_fields=["total", "updated_at"])
        platform_fee_ledger_commands.record_paid_order_fee(
            tenant_id=self.tenant.id,
            order_number=self.order.number,
            payment_attempt=self.attempt,
        )

        result, ledger = platform_fee_ledger_commands.close_minimum_commitment_period(tenant_id=self.tenant.id)

        self.assertEqual(result, "platform-fee-minimum-satisfied")
        self.assertIsNone(ledger)
        self.assertFalse(PlatformFeeLedger.objects.filter(kind=PlatformFeeLedger.Kind.PRO_MINIMUM_ADJUSTMENT).exists())
