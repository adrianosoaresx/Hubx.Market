from django.test import TestCase

from app.modules.audit.models import AuditLog
from app.modules.catalog.models import Product
from app.modules.coupons.application.admin_coupon_commands import admin_coupon_commands
from app.modules.coupons.models import Coupon
from app.modules.pages.application.admin_page_commands import admin_page_commands
from app.modules.pages.models import Page
from app.modules.reviews.application.admin_review_commands import admin_review_commands
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


class GovernancePermissionEnforcementTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Gate", slug="loja-gate", subdomain="loja-gate")

    def test_coupon_create_blocks_role_without_commercial_permission(self):
        result = admin_coupon_commands.create_coupon(
            tenant_id=self.tenant.id,
            actor_role="content_editor",
            payload={
                "code": "promo10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.PERCENT,
                "discount_value": "10.00",
            },
        )

        self.assertEqual(result["result"], "coupon-permission-denied")
        self.assertFalse(Coupon.objects.exists())
        self.assertFalse(AuditLog.objects.exists())

    def test_page_update_blocks_role_without_content_permission(self):
        page = Page.objects.create(tenant=self.tenant, slug="sobre", title="Sobre")

        result = admin_page_commands.update_page(
            tenant_id=self.tenant.id,
            page_id=page.id,
            actor_role="support",
            payload={
                "title": "Sobre atualizado",
                "slug": "sobre",
                "status": Page.Status.PUBLISHED,
                "body": "Conteúdo público",
            },
        )

        page.refresh_from_db()
        self.assertEqual(result["result"], "page-permission-denied")
        self.assertEqual(page.title, "Sobre")
        self.assertFalse(AuditLog.objects.exists())

    def test_review_moderation_blocks_viewer_role(self):
        product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Gate",
            slug="produto-gate",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=5,
            status=ProductReview.Status.PENDING,
        )

        result, moderated_review = admin_review_commands.moderate_review(
            tenant_id=self.tenant.id,
            review_id=review.id,
            action="approve",
            actor_role="viewer",
        )

        review.refresh_from_db()
        self.assertEqual(result, "review-permission-denied")
        self.assertIsNone(moderated_review)
        self.assertEqual(review.status, ProductReview.Status.PENDING)
        self.assertFalse(AuditLog.objects.exists())

    def test_allowed_roles_still_record_audit_events(self):
        page_result = admin_page_commands.create_page(
            tenant_id=self.tenant.id,
            actor_role="content_editor",
            payload={"title": "Trocas", "slug": "trocas", "status": Page.Status.PUBLISHED},
        )
        coupon_result = admin_coupon_commands.create_coupon(
            tenant_id=self.tenant.id,
            actor_role="marketing",
            payload={
                "code": "promo10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.PERCENT,
                "discount_value": "10.00",
            },
        )

        self.assertEqual(page_result["result"], "page-created")
        self.assertEqual(coupon_result["result"], "coupon-created")
        self.assertEqual(
            set(AuditLog.objects.values_list("action", flat=True)),
            {"page.created", "coupon.created"},
        )
