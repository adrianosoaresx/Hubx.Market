from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.coupons.application.admin_coupon_commands import admin_coupon_commands
from app.modules.coupons.application.admin_coupon_queries import admin_coupon_queries
from app.modules.coupons.models import Coupon, CouponRedemption
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class AdminCouponViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Cupons Admin", slug="loja-cupons-admin", subdomain="loja-cupons-admin")
        self.other_tenant = Tenant.objects.create(name="Outra Cupons Admin", slug="outra-cupons-admin", subdomain="outra-cupons-admin")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"

    def _login_owner(self, *, email: str, role: str):
        OwnerUser.objects.create(tenant=self.tenant, email=email, role=role, is_active=True)
        user = User.objects.create_user(username=email, email=email, password="secret")
        self.client.force_login(user)
        return user

    def test_coupon_list_view_renders_empty_state_for_tenant(self):
        response = self.client.get(reverse("coupons:admin-coupons-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_coupons_list_page.html")
        self.assertContains(response, "Cupons")
        self.assertContains(response, "Nenhum cupom encontrado")
        self.assertContains(response, reverse("coupons:admin-coupons-create"))

    def test_coupon_list_hides_create_action_for_role_without_coupon_permission(self):
        self._login_owner(email="support.coupons@hubx.market", role="support")

        response = self.client.get(reverse("coupons:admin-coupons-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse("coupons:admin-coupons-create"))

    def test_coupon_create_post_rejects_role_without_coupon_permission(self):
        self._login_owner(email="support.coupons.post@hubx.market", role="support")

        response = self.client.post(
            reverse("coupons:admin-coupons-create"),
            {
                "code": "SUPPORT10",
                "name": "Support 10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.PERCENT,
                "discount_value": "10.00",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Permissão insuficiente", status_code=400)
        self.assertFalse(Coupon.objects.filter(code="SUPPORT10").exists())

    def test_coupon_list_view_renders_only_current_tenant_coupons(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            name="Promo 10",
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )
        Coupon.objects.create(
            tenant=self.other_tenant,
            code="OTHER",
            name="Outro",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="5.00",
        )

        response = self.client.get(reverse("coupons:admin-coupons-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PROMO10")
        self.assertContains(response, "Promo 10")
        self.assertNotContains(response, "OTHER")

    def test_coupon_create_view_renders_form(self):
        response = self.client.get(reverse("coupons:admin-coupons-create"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_coupon_form_page.html")
        self.assertContains(response, "Novo cupom")
        self.assertContains(response, "Código")

    def test_coupon_create_post_creates_coupon_for_current_tenant(self):
        response = self.client.post(
            reverse("coupons:admin-coupons-create"),
            {
                "code": " promo10 ",
                "name": "Promo 10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.PERCENT,
                "discount_value": "10.00",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("coupons:admin-coupons-list"))
        coupon = Coupon.objects.get()
        self.assertEqual(coupon.tenant, self.tenant)
        self.assertEqual(coupon.code, "PROMO10")
        self.assertEqual(coupon.name, "Promo 10")

    def test_coupon_create_post_rejects_duplicate_code_per_tenant(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )

        response = self.client.post(
            reverse("coupons:admin-coupons-create"),
            {
                "code": "promo10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.PERCENT,
                "discount_value": "15.00",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Já existe um cupom", status_code=400)
        self.assertEqual(Coupon.objects.filter(tenant=self.tenant).count(), 1)

    def test_coupon_create_allows_same_code_in_other_tenant(self):
        Coupon.objects.create(
            tenant=self.other_tenant,
            code="PROMO10",
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )

        result = admin_coupon_commands.create_coupon(
            tenant_id=self.tenant.id,
            payload={
                "code": "promo10",
                "status": Coupon.Status.ACTIVE,
                "discount_type": Coupon.DiscountType.FIXED,
                "discount_value": "5.00",
            },
        )

        self.assertEqual(result["result"], "coupon-created")
        self.assertEqual(Coupon.objects.filter(code="PROMO10").count(), 2)

    def test_admin_coupon_query_service_is_tenant_scoped(self):
        Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="10.00",
        )
        Coupon.objects.create(
            tenant=self.other_tenant,
            code="OTHER",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="5.00",
        )

        coupons = admin_coupon_queries.list_coupons(tenant_id=self.tenant.id)

        self.assertEqual([coupon["code"] for coupon in coupons], ["PROMO10"])

    def test_coupon_list_view_shows_redemption_aggregates_for_current_tenant(self):
        coupon = Coupon.objects.create(
            tenant=self.tenant,
            code="PROMO10",
            name="Promo 10",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="10.00",
        )
        unused_coupon = Coupon.objects.create(
            tenant=self.tenant,
            code="UNUSED",
            name="Sem uso",
            discount_type=Coupon.DiscountType.PERCENT,
            discount_value="5.00",
        )
        other_coupon = Coupon.objects.create(
            tenant=self.other_tenant,
            code="PROMO10",
            name="Outro tenant",
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="10.00",
        )
        first_order = Order.objects.create(
            tenant=self.tenant,
            number="9101",
            discount_total="10.00",
            coupon_code="PROMO10",
            promotion_snapshot={"coupon_code": "PROMO10"},
        )
        second_order = Order.objects.create(
            tenant=self.tenant,
            number="9102",
            discount_total="15.00",
            coupon_code="PROMO10",
            promotion_snapshot={"coupon_code": "PROMO10"},
        )
        reversed_order = Order.objects.create(
            tenant=self.tenant,
            number="9103",
            discount_total="7.00",
            coupon_code="PROMO10",
            promotion_snapshot={"coupon_code": "PROMO10"},
        )
        reversed_only_order = Order.objects.create(
            tenant=self.tenant,
            number="9104",
            discount_total="5.00",
            coupon_code="UNUSED",
            promotion_snapshot={"coupon_code": "UNUSED"},
        )
        other_order = Order.objects.create(
            tenant=self.other_tenant,
            number="9101",
            discount_total="99.00",
            coupon_code="PROMO10",
            promotion_snapshot={"coupon_code": "PROMO10"},
        )
        CouponRedemption.objects.create(
            tenant=self.tenant,
            coupon=coupon,
            order=first_order,
            coupon_code_snapshot="PROMO10",
            discount_total_snapshot="10.00",
            promotion_snapshot={"coupon_code": "PROMO10"},
            source_type="application_command",
            source_label="Coupon Redemption Commands",
        )
        CouponRedemption.objects.create(
            tenant=self.tenant,
            coupon=coupon,
            order=second_order,
            coupon_code_snapshot="PROMO10",
            discount_total_snapshot="15.00",
            promotion_snapshot={"coupon_code": "PROMO10"},
            source_type="application_command",
            source_label="Coupon Redemption Commands",
        )
        CouponRedemption.objects.create(
            tenant=self.tenant,
            coupon=coupon,
            order=reversed_order,
            coupon_code_snapshot="PROMO10",
            discount_total_snapshot="7.00",
            promotion_snapshot={"coupon_code": "PROMO10"},
            status=CouponRedemption.Status.REVERSED,
            source_type="admin_action",
            source_label="Admin Orders",
        )
        CouponRedemption.objects.create(
            tenant=self.tenant,
            coupon=unused_coupon,
            order=reversed_only_order,
            coupon_code_snapshot="UNUSED",
            discount_total_snapshot="5.00",
            promotion_snapshot={"coupon_code": "UNUSED"},
            status=CouponRedemption.Status.REVERSED,
            source_type="admin_action",
            source_label="Admin Orders",
        )
        CouponRedemption.objects.create(
            tenant=self.other_tenant,
            coupon=other_coupon,
            order=other_order,
            coupon_code_snapshot="PROMO10",
            discount_total_snapshot="99.00",
            promotion_snapshot={"coupon_code": "PROMO10"},
            source_type="application_command",
            source_label="Coupon Redemption Commands",
        )

        coupons = admin_coupon_queries.list_coupons(tenant_id=self.tenant.id)
        promo = next(item for item in coupons if item["code"] == "PROMO10")
        unused = next(item for item in coupons if item["code"] == unused_coupon.code)
        response = self.client.get(reverse("coupons:admin-coupons-list"), HTTP_HOST=self.host)

        self.assertEqual(promo["redemption_count"], 2)
        self.assertEqual(promo["active_redemption_count"], 2)
        self.assertEqual(promo["reversed_redemption_count"], 1)
        self.assertEqual(promo["redemption_discount_total"], "R$ 25,00")
        self.assertEqual(promo["reversed_redemption_discount_total"], "R$ 7,00")
        self.assertEqual(promo["redemption_label"], "2 uso(s) ativos · R$ 25,00 em descontos · 1 reversão(ões)")
        self.assertEqual(unused["redemption_count"], 0)
        self.assertEqual(unused["active_redemption_count"], 0)
        self.assertEqual(unused["reversed_redemption_count"], 1)
        self.assertEqual(unused["redemption_label"], "Nenhum uso ativo · 1 reversão(ões)")
        self.assertContains(response, "Resgates")
        self.assertContains(response, "2 uso(s) ativos · R$ 25,00 em descontos · 1 reversão(ões)")
        self.assertContains(response, "Nenhum uso ativo · 1 reversão(ões)")
        self.assertNotContains(response, "R$ 99,00")
