from decimal import Decimal

from django.test import TestCase

from app.modules.coupons.application.coupon_redemption_commands import coupon_redemption_commands
from app.modules.coupons.models import Coupon, CouponRedemption
from app.modules.customers.models import Customer
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class CouponRedemptionCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Redemption", slug="loja-redemption", subdomain="loja-redemption")
        self.other_tenant = Tenant.objects.create(name="Outra Redemption", slug="outra-redemption", subdomain="outra-redemption")
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            email="ana.redemption@hubx.market",
            full_name="Ana Redemption",
        )
        self.coupon = Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="10.00",
        )

    def _order(self, **overrides):
        defaults = {
            "tenant": self.tenant,
            "customer": self.customer,
            "number": "9001",
            "status": "pending",
            "customer_email": self.customer.email,
            "subtotal": Decimal("100.00"),
            "shipping_total": Decimal("0.00"),
            "discount_total": Decimal("10.00"),
            "total": Decimal("90.00"),
            "coupon_code": "PROMO10",
            "promotion_snapshot": {
                "coupon_code": "PROMO10",
                "discount_total": "10.00",
                "source": "cart",
                "validation_result": "coupon-valid",
            },
        }
        defaults.update(overrides)
        return Order.objects.create(**defaults)

    def test_record_order_coupon_redemption_creates_tenant_scoped_ledger(self):
        order = self._order()

        result = coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        self.assertEqual(result["result"], "coupon-redemption-recorded")
        redemption = CouponRedemption.objects.get(pk=result["redemption_id"])
        self.assertEqual(redemption.tenant, self.tenant)
        self.assertEqual(redemption.coupon, self.coupon)
        self.assertEqual(redemption.order, order)
        self.assertEqual(redemption.customer, self.customer)
        self.assertEqual(redemption.coupon_code_snapshot, "PROMO10")
        self.assertEqual(redemption.discount_total_snapshot, Decimal("10.00"))
        self.assertEqual(redemption.promotion_snapshot["validation_result"], "coupon-valid")
        self.assertEqual(redemption.status, CouponRedemption.Status.APPLIED)
        self.assertEqual(redemption.source_label, "Coupon Redemption Commands")

    def test_record_order_coupon_redemption_is_idempotent(self):
        order = self._order()

        first_result = coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )
        second_result = coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        self.assertEqual(first_result["result"], "coupon-redemption-recorded")
        self.assertEqual(second_result["result"], "coupon-redemption-already-recorded")
        self.assertEqual(CouponRedemption.objects.filter(order=order).count(), 1)

    def test_record_order_coupon_redemption_skips_orders_without_valid_coupon_snapshot(self):
        order = self._order(coupon_code="PROMO10", discount_total=Decimal("10.00"), promotion_snapshot={})

        result = coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        self.assertEqual(result["result"], "coupon-redemption-skipped-no-coupon")
        self.assertFalse(CouponRedemption.objects.exists())

    def test_record_order_coupon_redemption_respects_tenant_scope(self):
        order = self._order()

        result = coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.other_tenant.id,
            order_number=order.number,
        )

        self.assertEqual(result["result"], "coupon-redemption-order-not-found")
        self.assertFalse(CouponRedemption.objects.exists())

    def test_reverse_order_coupon_redemption_marks_applied_ledger_as_reversed(self):
        order = self._order()
        coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        result = coupon_redemption_commands.reverse_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        self.assertEqual(result["result"], "coupon-redemption-reversed")
        redemption = CouponRedemption.objects.get(order=order)
        self.assertEqual(redemption.status, CouponRedemption.Status.REVERSED)
        self.assertIsNotNone(redemption.reversed_at)
        self.assertEqual(redemption.source_type, "admin_action")
        self.assertEqual(redemption.source_label, "Admin Orders")

    def test_reverse_order_coupon_redemption_is_idempotent(self):
        order = self._order()
        coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )
        first_result = coupon_redemption_commands.reverse_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )
        second_result = coupon_redemption_commands.reverse_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        self.assertEqual(first_result["result"], "coupon-redemption-reversed")
        self.assertEqual(second_result["result"], "coupon-redemption-already-reversed")
        self.assertEqual(CouponRedemption.objects.filter(order=order, status=CouponRedemption.Status.REVERSED).count(), 1)

    def test_reverse_order_coupon_redemption_respects_tenant_scope(self):
        order = self._order()
        coupon_redemption_commands.record_order_coupon_redemption(
            tenant_id=self.tenant.id,
            order_number=order.number,
        )

        result = coupon_redemption_commands.reverse_order_coupon_redemption(
            tenant_id=self.other_tenant.id,
            order_number=order.number,
        )

        self.assertEqual(result["result"], "coupon-redemption-order-not-found")
        self.assertEqual(CouponRedemption.objects.get(order=order).status, CouponRedemption.Status.APPLIED)
