from __future__ import annotations

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.models import SubscriptionAcquisitionLead, SubscriptionCoupon, TenantSubscription
from app.modules.tenants.models import Tenant, TenantOnboarding


@override_settings(
    ALLOWED_HOSTS=["hubx.market", ".hubx.market", "testserver"],
    HUBX_PLATFORM_TENANT_SLUG="platform-system",
    HUBX_OPS_AUTH_GATE_ENFORCED=True,
    HUBX_MARKET_ROOT_DOMAIN="hubx.market",
)
class SubscriptionCouponE2ETests(TestCase):
    central_host = "hubx.market"

    def setUp(self):
        self.platform_tenant = Tenant.objects.create(
            name="Platform System",
            slug="platform-system",
            subdomain="platform-system",
        )
        self.platform_email = "platform.owner@hubx.market"
        User.objects.create_user(
            username=self.platform_email,
            email=self.platform_email,
            password="secret",
        )
        OwnerUser.objects.create(
            tenant=self.platform_tenant,
            email=self.platform_email,
            role="owner",
            is_active=True,
        )
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="100.00",
            trial_days=30,
            requires_payment_method=True,
        )

    def test_public_plans_form_renders_active_plan_options_and_preserves_selection(self):
        response = self.client.get(
            f"{reverse('subscription_public:plans')}?plan=starter",
            HTTP_HOST=self.central_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<option value="starter" selected>Starter · R$ 100,00</option>')
        self.assertContains(response, "30 dias grátis")

    @override_settings(
        CSRF_TRUSTED_ORIGINS=["https://hubx.market", "https://*.hubx.market"],
        SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"),
    )
    def test_public_plans_post_accepts_https_origin_behind_proxy_with_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        get_response = csrf_client.get(
            reverse("subscription_public:plans"),
            HTTP_HOST=self.central_host,
            HTTP_X_FORWARDED_PROTO="https",
        )
        csrf_token = get_response.cookies["csrftoken"].value

        response = csrf_client.post(
            reverse("subscription_public:plans"),
            {
                "csrfmiddlewaretoken": csrf_token,
                "plan_code": "starter",
                "store_name": "Loja VPS",
                "desired_subdomain": "loja-vps",
                "contact_name": "Contato VPS",
                "contact_email": "vps@example.com",
            },
            HTTP_HOST=self.central_host,
            HTTP_ORIGIN="https://hubx.market",
            HTTP_X_FORWARDED_PROTO="https",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recebemos sua intenção")
        self.assertTrue(SubscriptionAcquisitionLead.objects.filter(desired_subdomain="loja-vps").exists())

    def test_assisted_plan_coupon_e2e_creates_snapshot_until_subscription(self):
        platform_client = self._logged_platform_client()
        list_response = platform_client.get(
            reverse("subscription_coupons:platform-subscription-coupons-list"),
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Cupons SaaS")

        create_coupon_response = platform_client.post(
            reverse("subscription_coupons:platform-subscription-coupons-create"),
            {
                "code": "assist20",
                "name": "Assistido 20%",
                "status": SubscriptionCoupon.Status.ACTIVE,
                "discount_type": SubscriptionCoupon.DiscountType.PERCENT,
                "discount_value": "20.00",
                "plan_code": "starter",
            },
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(create_coupon_response.status_code, 302)
        self.assertTrue(SubscriptionCoupon.objects.filter(code="ASSIST20", plan__code="starter").exists())

        invalid_response = self.client.post(
            reverse("subscription_public:plans"),
            {
                "plan_code": "starter",
                "store_name": "Cupom Invalido",
                "desired_subdomain": "cupom-invalido",
                "contact_email": "invalid@example.com",
                "coupon_code": "naoexiste",
            },
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, "Cupom SaaS inválido")
        self.assertFalse(SubscriptionAcquisitionLead.objects.filter(desired_subdomain="cupom-invalido").exists())

        lead_response = self.client.post(
            reverse("subscription_public:plans"),
            {
                "plan_code": "starter",
                "store_name": "Loja Assistida",
                "desired_subdomain": "loja-assistida",
                "contact_name": "Assist Owner",
                "contact_email": "assist.owner@example.com",
                "coupon_code": "assist20",
            },
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(lead_response.status_code, 200)
        self.assertContains(lead_response, "Cupom ASSIST20 aplicado")
        lead = SubscriptionAcquisitionLead.objects.get(desired_subdomain="loja-assistida")
        self.assertEqual(lead.coupon_code_snapshot, "ASSIST20")
        self.assertEqual(str(lead.coupon_discount_total_snapshot), "20.00")
        self.assertEqual(str(lead.effective_monthly_price_snapshot), "80.00")

        convert_response = platform_client.post(
            reverse("subscription_acquisitions:platform-acquisitions-convert", kwargs={"lead_id": lead.id}),
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(convert_response.status_code, 302)
        lead.refresh_from_db()
        onboarding = TenantOnboarding.objects.get(pk=lead.onboarding_id)
        self.assertEqual(onboarding.coupon_code_snapshot, "ASSIST20")
        self.assertEqual(str(onboarding.effective_monthly_price_snapshot), "80.00")

        complete_response = platform_client.post(
            reverse("tenant_onboarding:onboarding-complete", kwargs={"onboarding_id": onboarding.id}),
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(complete_response.status_code, 302)
        tenant = Tenant.objects.get(slug="loja-assistida")
        subscription = TenantSubscription.objects.get(tenant=tenant)
        self.assertEqual(subscription.coupon_code_snapshot, "ASSIST20")
        self.assertEqual(str(subscription.coupon_discount_total_snapshot), "20.00")
        self.assertEqual(str(subscription.effective_monthly_price_snapshot), "80.00")
        self.assertEqual(subscription.promotion_snapshot["source"], "public-plans")
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_created").exists())
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_applied", entity_type="TenantSubscription").exists())

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=20,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_self_service_signup_coupon_e2e_blocks_invalid_and_creates_discounted_trial(self):
        platform_client = self._logged_platform_client()
        create_coupon_response = platform_client.post(
            reverse("subscription_coupons:platform-subscription-coupons-create"),
            {
                "code": "signup30",
                "name": "Signup 30",
                "status": SubscriptionCoupon.Status.ACTIVE,
                "discount_type": SubscriptionCoupon.DiscountType.FIXED,
                "discount_value": "30.00",
                "plan_code": "starter",
            },
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(create_coupon_response.status_code, 302)

        invalid_response = self.client.post(
            reverse("subscription_public:plans-signup"),
            {
                "plan_code": "starter",
                "store_name": "Signup Bloqueado",
                "desired_subdomain": "signup-bloqueado",
                "owner_name": "Blocked Owner",
                "owner_email": "blocked.owner@example.com",
                "access_token": "signup-token",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "accept_terms": "1",
                "coupon_code": "naoexiste",
            },
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(invalid_response.status_code, 200)
        self.assertContains(invalid_response, "Cupom SaaS inválido")
        self.assertFalse(Tenant.objects.filter(slug="signup-bloqueado").exists())
        self.assertFalse(OwnerUser.objects.filter(email="blocked.owner@example.com").exists())

        signup_response = self.client.post(
            reverse("subscription_public:plans-signup"),
            {
                "plan_code": "starter",
                "store_name": "Signup Cupom",
                "desired_subdomain": "signup-cupom",
                "owner_name": "Signup Owner",
                "owner_email": "signup.owner@example.com",
                "access_token": "signup-token",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "accept_terms": "1",
                "coupon_code": "signup30",
            },
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(signup_response.status_code, 200)
        self.assertContains(signup_response, "Loja criada em modo manutenção")
        self.assertContains(signup_response, "Cupom SIGNUP30")
        tenant = Tenant.objects.get(slug="signup-cupom")
        subscription = TenantSubscription.objects.get(tenant=tenant)
        onboarding = TenantOnboarding.objects.get(tenant=tenant)
        self.assertEqual(subscription.coupon_code_snapshot, "SIGNUP30")
        self.assertEqual(str(subscription.coupon_discount_total_snapshot), "30.00")
        self.assertEqual(str(subscription.effective_monthly_price_snapshot), "70.00")
        self.assertEqual(onboarding.coupon_code_snapshot, "SIGNUP30")
        self.assertTrue(OwnerUser.objects.filter(tenant=tenant, email="signup.owner@example.com", role="owner").exists())
        self.assertTrue(AuditLog.objects.filter(action="tenant.self_service_signup_completed", tenant=tenant).exists())
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_applied", entity_type="TenantSubscription").exists())

    def _logged_platform_client(self):
        login_response = self.client.post(
            reverse("accounts:login"),
            {"login": self.platform_email, "password": "secret"},
            HTTP_HOST=self.central_host,
        )
        self.assertEqual(login_response.status_code, 302)
        self.assertEqual(login_response["Location"], "/ops/platform/tenants/")
        return self.client
