from django.test import TestCase
from django.utils import timezone

from app.modules.coupons.application.coupon_validation_queries import (
    coupon_validation_queries,
    normalize_coupon_code,
)
from app.modules.coupons.models import Coupon
from app.modules.tenants.models import Tenant


class CouponValidationQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Cupom", slug="loja-cupom", subdomain="loja-cupom")
        self.other_tenant = Tenant.objects.create(name="Outra Cupom", slug="outra-cupom", subdomain="outra-cupom")

    def _snapshot(self, subtotal="199.90"):
        return {
            "cart_id": 10,
            "subtotal": subtotal,
            "items": [
                {
                    "product_id": 1,
                    "product_slug": "produto",
                    "variant_sku": "SKU-1",
                    "quantity": 1,
                    "price_snapshot": subtotal,
                }
            ],
        }

    def test_normalize_coupon_code_is_deterministic(self):
        self.assertEqual(normalize_coupon_code(" promo10 "), "PROMO10")
        self.assertEqual(normalize_coupon_code(""), "")

    def test_validate_cart_coupon_requires_tenant(self):
        result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=None,
            coupon_code="PROMO10",
            cart_snapshot=self._snapshot(),
        )

        self.assertEqual(result["result"], "coupon-unavailable")
        self.assertEqual(result["reason"], "tenant-required")
        self.assertEqual(result["discount_total"], "0.00")

    def test_validate_cart_coupon_requires_coupon_code(self):
        result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code="",
            cart_snapshot=self._snapshot(),
        )

        self.assertEqual(result["result"], "coupon-unavailable")
        self.assertEqual(result["reason"], "coupon-code-required")
        self.assertEqual(result["coupon_code"], "")

    def test_validate_cart_coupon_requires_cart_snapshot_with_items(self):
        result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code="PROMO10",
            cart_snapshot={"subtotal": "0.00", "items": []},
        )

        self.assertEqual(result["result"], "coupon-unavailable")
        self.assertEqual(result["reason"], "cart-snapshot-required")
        self.assertEqual(result["discount_total"], "0.00")

    def test_validate_cart_coupon_returns_invalid_for_missing_or_inactive_coupon(self):
        inactive = Coupon.objects.create(
            tenant=self.tenant,
            code="OFF",
            status=Coupon.Status.INACTIVE,
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )

        missing = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code="MISSING",
            cart_snapshot=self._snapshot(),
        )
        inactive_result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code=inactive.code,
            cart_snapshot=self._snapshot(),
        )
        cross_tenant = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.other_tenant.id,
            coupon_code=inactive.code,
            cart_snapshot=self._snapshot(),
        )

        self.assertEqual(missing["result"], "coupon-invalid")
        self.assertEqual(inactive_result["result"], "coupon-invalid")
        self.assertEqual(cross_tenant["result"], "coupon-invalid")

    def test_validate_cart_coupon_returns_expired_for_outside_validity_window(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="OLD",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="10.00",
            ends_at=timezone.now() - timezone.timedelta(days=1),
        )

        result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code="old",
            cart_snapshot=self._snapshot(),
        )

        self.assertEqual(result["result"], "coupon-expired")
        self.assertEqual(result["reason"], "coupon-expired")
        self.assertEqual(result["discount_total"], "0.00")

    def test_validate_cart_coupon_calculates_percent_discount(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )

        result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code=" promo10 ",
            cart_snapshot=self._snapshot(),
        )

        self.assertEqual(result["result"], "coupon-valid")
        self.assertEqual(result["coupon_code"], "PROMO10")
        self.assertEqual(result["discount_total"], "19.99")

    def test_validate_cart_coupon_calculates_fixed_discount_capped_by_subtotal(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="FIXED",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="250.00",
        )

        result = coupon_validation_queries.validate_cart_coupon(
            tenant_id=self.tenant.id,
            coupon_code="fixed",
            cart_snapshot=self._snapshot(subtotal="199.90"),
        )

        self.assertEqual(result["result"], "coupon-valid")
        self.assertEqual(result["discount_total"], "199.90")
