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


class GovernanceInstrumentationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Governança", slug="loja-governanca", subdomain="loja-governanca")
        self.other_tenant = Tenant.objects.create(name="Outra Governança", slug="outra-governanca", subdomain="outra-governanca")

    def test_coupon_creation_records_sensitive_admin_audit_event(self):
        result = admin_coupon_commands.create_coupon(
            tenant_id=self.tenant.id,
            actor_label="owner@example.com",
            payload={
                "code": "promo10",
                "name": "Promo 10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.PERCENT,
                "discount_value": "10.00",
            },
        )

        self.assertEqual(result["result"], "coupon-created")
        log = AuditLog.objects.get(module="coupons", action="coupon.created")
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.entity_type, "Coupon")
        self.assertEqual(log.entity_id, str(result["coupon"]["id"]))
        self.assertEqual(log.actor_label, "owner@example.com")
        self.assertEqual(log.metadata["code"], "PROMO10")
        self.assertEqual(log.metadata["discount_type"], Coupon.DiscountType.PERCENT)

    def test_page_create_and_update_record_public_content_audit_events(self):
        create_result = admin_page_commands.create_page(
            tenant_id=self.tenant.id,
            actor_label="editor@example.com",
            payload={
                "title": "Sobre a loja",
                "slug": "sobre",
                "status": Page.Status.DRAFT,
                "body": "Conteúdo institucional",
            },
        )
        update_result = admin_page_commands.update_page(
            tenant_id=self.tenant.id,
            page_id=create_result["page"]["id"],
            actor_label="editor@example.com",
            payload={
                "title": "Sobre publicado",
                "slug": "sobre",
                "status": Page.Status.PUBLISHED,
                "body": "Conteúdo público",
            },
        )

        self.assertEqual(create_result["result"], "page-created")
        self.assertEqual(update_result["result"], "page-updated")
        logs = list(AuditLog.objects.filter(module="pages").order_by("id"))
        self.assertEqual([log.action for log in logs], ["page.created", "page.updated"])
        self.assertEqual([log.tenant for log in logs], [self.tenant, self.tenant])
        self.assertEqual(logs[0].metadata["status"], Page.Status.DRAFT)
        self.assertEqual(logs[1].metadata["status"], Page.Status.PUBLISHED)
        self.assertEqual(logs[1].metadata["title"], "Sobre publicado")

    def test_review_moderation_records_trust_surface_audit_event(self):
        product = Product.objects.create(
            tenant=self.tenant,
            name="Produto auditável",
            slug="produto-auditavel",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        review = ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=5,
            title="Ótimo",
            body="Gostei",
            author_name="Cliente",
        )

        result, moderated_review = admin_review_commands.moderate_review(
            tenant_id=self.tenant.id,
            review_id=review.id,
            action="approve",
            moderated_by="moderator@example.com",
        )

        self.assertEqual(result, "review-approved")
        self.assertEqual(moderated_review.status, ProductReview.Status.APPROVED)
        log = AuditLog.objects.get(module="reviews", action="review.approved")
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.entity_type, "ProductReview")
        self.assertEqual(log.entity_id, str(review.id))
        self.assertEqual(log.actor_label, "moderator@example.com")
        self.assertEqual(log.metadata["product_id"], product.id)
        self.assertEqual(log.metadata["rating"], 5)

    def test_instrumented_events_remain_tenant_scoped(self):
        admin_coupon_commands.create_coupon(
            tenant_id=self.tenant.id,
            payload={
                "code": "tenant",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.FIXED,
                "discount_value": "5.00",
            },
        )
        admin_coupon_commands.create_coupon(
            tenant_id=self.other_tenant.id,
            payload={
                "code": "other",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.FIXED,
                "discount_value": "5.00",
            },
        )

        logs = AuditLog.objects.filter(tenant=self.tenant)

        self.assertEqual(logs.count(), 1)
        self.assertEqual(logs.get().metadata["code"], "TENANT")
