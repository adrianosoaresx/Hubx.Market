from __future__ import annotations

from datetime import timedelta
from io import StringIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.subscriptions.application.subscription_coupon_queries import subscription_coupon_queries
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.application.subscription_queries import subscription_queries
from app.modules.subscriptions.application.subscriptions_foundation_queries import subscriptions_foundation_queries
from app.modules.subscriptions.models import SubscriptionAcquisitionLead, SubscriptionCoupon, SubscriptionPlan, TenantSubscription
from app.modules.tenants.models import Tenant, TenantOnboarding


@override_settings(
    ALLOWED_HOSTS=["testserver", ".hubx.market", "hubx.market"],
    HUBX_PLATFORM_TENANT_SLUG="platform-system",
    HUBX_OPS_AUTH_GATE_ENFORCED=False,
)
class SubscriptionsFoundationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Billing Tenant", slug="billing-tenant", subdomain="billing-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Billing", slug="other-billing", subdomain="other-billing")
        self.platform_tenant = Tenant.objects.create(name="Platform System", slug="platform-system", subdomain="platform-system")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.platform_host = "hubx.market"

    def test_plan_and_tenant_subscription_are_created_with_audit(self):
        plan_result = subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="99.90",
            included_api_quota=10000,
            trial_days=30,
            requires_payment_method=True,
            features=("30 dias grátis", "Cartão obrigatório"),
            actor_label="ops@hubx.market",
        )
        subscription_result = subscription_commands.set_tenant_subscription(
            tenant_id=self.tenant.id,
            plan_code="starter",
            status=TenantSubscription.Status.ACTIVE,
            external_reference="manual-contract-001",
            actor_label="ops@hubx.market",
        )

        self.assertEqual(plan_result["result"], "subscription-plan-created")
        self.assertEqual(subscription_result["result"], "tenant-subscription-created")
        plan = SubscriptionPlan.objects.get(code="starter")
        self.assertEqual(str(plan.monthly_price), plan_result["plan"]["monthly_price"])
        self.assertEqual(plan.trial_days, 30)
        self.assertTrue(plan.requires_payment_method)
        self.assertIn("Cartão obrigatório", plan.feature_list)
        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(subscription.plan.code, "starter")
        self.assertEqual(subscription.status, TenantSubscription.Status.ACTIVE)
        self.assertIsNone(subscription.trial_ends_at)
        self.assertEqual(subscription.billing_provider_code, "asaas")
        self.assertEqual(subscription.billing_provider_label, "Asaas")
        self.assertTrue(AuditLog.objects.filter(module="subscriptions", action="subscription.plan_upserted").exists())
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, action="tenant_subscription.updated").exists())

    def test_trialing_subscription_sets_trial_end_from_plan(self):
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="99.90",
            trial_days=30,
            requires_payment_method=True,
        )

        result = subscription_commands.set_tenant_subscription(
            tenant_id=self.tenant.id,
            plan_code="starter",
            status=TenantSubscription.Status.TRIALING,
        )

        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(result["result"], "tenant-subscription-created")
        self.assertIsNotNone(subscription.trial_ends_at)
        self.assertEqual(subscription.trial_ends_at.date(), (subscription.started_at + timedelta(days=30)).date())
        self.assertIn("trial_ends_at", result["subscription"])

    def test_tenant_subscription_requires_existing_plan_and_tenant(self):
        missing_tenant = subscription_commands.set_tenant_subscription(tenant_id=None, plan_code="starter")
        missing_plan = subscription_commands.set_tenant_subscription(tenant_id=self.tenant.id, plan_code="starter")

        self.assertEqual(missing_tenant["result"], "tenant-subscription-tenant-required")
        self.assertEqual(missing_plan["result"], "tenant-subscription-plan-not-found")

    def test_subscription_coupon_validation_handles_commercial_rules(self):
        starter_result = subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")
        pro_result = subscription_commands.upsert_plan(code="pro", name="Pro", monthly_price="200.00")
        starter = SubscriptionPlan.objects.get(code=starter_result["plan"]["code"])
        pro = SubscriptionPlan.objects.get(code=pro_result["plan"]["code"])
        SubscriptionCoupon.objects.create(
            code="saas10",
            name="SaaS 10",
            discount_type=SubscriptionCoupon.DiscountType.PERCENT,
            discount_value="10.00",
        )
        SubscriptionCoupon.objects.create(
            code="FIXEDBIG",
            name="Fixed cap",
            discount_type=SubscriptionCoupon.DiscountType.FIXED,
            discount_value="500.00",
            plan=starter,
        )
        SubscriptionCoupon.objects.create(
            code="OFF",
            name="Inactive",
            status=SubscriptionCoupon.Status.INACTIVE,
            discount_type=SubscriptionCoupon.DiscountType.PERCENT,
            discount_value="20.00",
        )
        SubscriptionCoupon.objects.create(
            code="OLD",
            name="Expired",
            discount_type=SubscriptionCoupon.DiscountType.FIXED,
            discount_value="10.00",
            ends_at=timezone.now() - timedelta(days=1),
        )
        SubscriptionCoupon.objects.create(
            code="PROONLY",
            name="Pro only",
            discount_type=SubscriptionCoupon.DiscountType.PERCENT,
            discount_value="15.00",
            plan=pro,
        )

        percent = subscription_coupon_queries.validate_plan_coupon(plan_code="starter", coupon_code="saas10")
        fixed = subscription_coupon_queries.validate_plan_coupon(plan_code="starter", coupon_code="FIXEDBIG")
        inactive = subscription_coupon_queries.validate_plan_coupon(plan_code="starter", coupon_code="OFF")
        expired = subscription_coupon_queries.validate_plan_coupon(plan_code="starter", coupon_code="OLD")
        missing = subscription_coupon_queries.validate_plan_coupon(plan_code="starter", coupon_code="MISSING")
        not_applicable = subscription_coupon_queries.validate_plan_coupon(plan_code="starter", coupon_code="PROONLY")

        self.assertEqual(percent["result"], "subscription-coupon-valid")
        self.assertEqual(percent["discount_total"], "10.00")
        self.assertEqual(percent["effective_monthly_price"], "90.00")
        self.assertEqual(fixed["result"], "subscription-coupon-valid")
        self.assertEqual(fixed["discount_total"], "100.00")
        self.assertEqual(fixed["effective_monthly_price"], "0.00")
        self.assertEqual(inactive["result"], "subscription-coupon-invalid")
        self.assertEqual(expired["result"], "subscription-coupon-expired")
        self.assertEqual(missing["result"], "subscription-coupon-invalid")
        self.assertEqual(not_applicable["result"], "subscription-coupon-not-applicable")

    def test_public_acquisition_lead_creates_safe_draft_without_side_effects(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="99.90")

        result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": "starter",
                "store_name": "Lead Store",
                "desired_subdomain": "lead-store",
                "contact_name": "Lead Owner",
                "contact_email": "lead.owner@example.com",
            }
        )

        self.assertEqual(result["result"], "subscription-acquisition-lead-created")
        self.assertEqual(SubscriptionAcquisitionLead.objects.count(), 1)
        self.assertFalse(Tenant.objects.filter(slug="lead-store").exists())
        self.assertFalse(TenantSubscription.objects.filter(external_reference__icontains="lead").exists())
        self.assertFalse(OwnerUser.objects.filter(email="lead.owner@example.com").exists())
        self.assertTrue(AuditLog.objects.filter(action="subscription.acquisition_requested").exists())

    def test_public_acquisition_lead_saves_coupon_snapshots(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")
        SubscriptionCoupon.objects.create(
            code="saas25",
            name="SaaS 25",
            discount_type=SubscriptionCoupon.DiscountType.FIXED,
            discount_value="25.00",
        )

        result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": "starter",
                "store_name": "Coupon Lead",
                "desired_subdomain": "coupon-lead",
                "contact_email": "coupon.lead@example.com",
                "coupon_code": "saas25",
            }
        )

        lead = SubscriptionAcquisitionLead.objects.get(desired_subdomain="coupon-lead")
        self.assertEqual(result["result"], "subscription-acquisition-lead-created")
        self.assertEqual(lead.coupon_code_snapshot, "SAAS25")
        self.assertEqual(str(lead.coupon_discount_total_snapshot), "25.00")
        self.assertEqual(str(lead.effective_monthly_price_snapshot), "75.00")
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_applied", entity_type="SubscriptionAcquisitionLead").exists())

    def test_public_acquisition_rejects_invalid_coupon_without_creating_lead(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")

        result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": "starter",
                "store_name": "Invalid Coupon Lead",
                "desired_subdomain": "invalid-coupon-lead",
                "contact_email": "invalid.coupon@example.com",
                "coupon_code": "missing",
            }
        )

        self.assertEqual(result["result"], "subscription-acquisition-lead-invalid")
        self.assertIn("coupon_code", result["errors"])
        self.assertEqual(SubscriptionAcquisitionLead.objects.count(), 0)

    def test_public_acquisition_rejects_archived_plan(self):
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="99.90",
            status=SubscriptionPlan.Status.ARCHIVED,
        )

        result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": "starter",
                "store_name": "Archived Plan Store",
                "desired_subdomain": "archived-plan-store",
                "contact_email": "lead@example.com",
            }
        )

        self.assertEqual(result["result"], "subscription-acquisition-lead-invalid")
        self.assertEqual(result["errors"]["plan_code"], "Selecione um plano ativo.")
        self.assertEqual(SubscriptionAcquisitionLead.objects.count(), 0)

    def test_public_plans_view_renders_and_posts_without_tenant_context(self):
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            description="Plano inicial com trial controlado.",
            monthly_price="99.90",
            trial_days=30,
            requires_payment_method=True,
            features=("30 dias grátis para validar a loja", "Cartão obrigatório na ativação do trial"),
        )

        tenant_host_response = self.client.get(reverse("subscription_public:plans"), HTTP_HOST=self.host)
        post_response = self.client.post(
            reverse("subscription_public:plans"),
            {
                "plan_code": "starter",
                "store_name": "Public Plan Store",
                "desired_subdomain": "public-plan-store",
                "contact_email": "public@example.com",
            },
            HTTP_HOST=self.platform_host,
        )

        self.assertEqual(tenant_host_response.status_code, 200)
        self.assertTemplateUsed(tenant_host_response, "pages/templates/public_plans_page.html")
        self.assertContains(tenant_host_response, "Planos Hubx Market")
        self.assertContains(tenant_host_response, "Iniciar onboarding")
        self.assertContains(tenant_host_response, "Onboarding assistido")
        self.assertContains(tenant_host_response, "Asaas")
        self.assertContains(tenant_host_response, "Teste grátis por 30 dias")
        self.assertContains(tenant_host_response, "30 dias grátis")
        self.assertContains(tenant_host_response, "Cartão obrigatório")
        self.assertContains(tenant_host_response, "/mês após 30 dias")
        self.assertContains(tenant_host_response, "Não insira dados de cartão")
        self.assertContains(tenant_host_response, 'href="/demo/"')
        self.assertContains(tenant_host_response, "Acessar demo")
        self.assertContains(tenant_host_response, "Onboarding assistido")
        self.assertNotContains(tenant_host_response, "Demo lifestyle")
        self.assertNotContains(tenant_host_response, "/media/demo-catalog/fixtures/")
        self.assertNotContains(tenant_host_response, "Billing Tenant")
        self.assertEqual(post_response.status_code, 200)
        self.assertContains(post_response, "Recebemos sua intenção")
        self.assertTrue(SubscriptionAcquisitionLead.objects.filter(desired_subdomain="public-plan-store").exists())

    def test_public_plans_view_blocks_invalid_coupon(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")

        response = self.client.post(
            reverse("subscription_public:plans"),
            {
                "plan_code": "starter",
                "store_name": "Blocked Coupon Store",
                "desired_subdomain": "blocked-coupon-store",
                "contact_email": "blocked.coupon@example.com",
                "coupon_code": "missing",
            },
            HTTP_HOST=self.platform_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cupom SaaS inválido")
        self.assertFalse(SubscriptionAcquisitionLead.objects.filter(desired_subdomain="blocked-coupon-store").exists())

    @override_settings(HUBX_PUBLIC_SIGNUP_ENABLED=False)
    def test_public_signup_route_requires_feature_flag(self):
        response = self.client.get(reverse("subscription_public:plans-signup"), HTTP_HOST=self.platform_host)

        self.assertEqual(response.status_code, 404)

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=10,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_public_signup_view_explains_trial_and_card_requirement(self):
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="99.90",
            trial_days=30,
            requires_payment_method=True,
        )

        response = self.client.get(
            reverse("subscription_public:plans-signup"),
            {"plan": "starter"},
            HTTP_HOST=self.platform_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "trial interna de 30 dias")
        self.assertContains(response, "checkout hospedado do provider")
        self.assertContains(response, "Não insira dados de cartão")
        self.assertContains(response, "R$ 99,90 /mês após 30 dias")

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=10,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_public_signup_creates_tenant_trial_owner_and_onboarding_without_lead(self):
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="99.90",
            trial_days=30,
            requires_payment_method=True,
        )

        response = self.client.post(
            reverse("subscription_public:plans-signup"),
            {
                "plan_code": "starter",
                "store_name": "Self Service Store",
                "desired_subdomain": "self-service-store",
                "owner_name": "Self Owner",
                "owner_email": "self.owner@example.com",
                "contact_phone": "(11) 99999-0000",
                "access_token": "signup-token",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "accept_terms": "1",
            },
            HTTP_HOST=self.platform_host,
        )

        tenant = Tenant.objects.get(slug="self-service-store")
        owner = OwnerUser.objects.get(tenant=tenant, email="self.owner@example.com")
        user = User.objects.get(email="self.owner@example.com")
        subscription = TenantSubscription.objects.get(tenant=tenant)
        onboarding = TenantOnboarding.objects.get(tenant=tenant)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Loja criada em modo manutenção")
        self.assertTrue(tenant.is_active)
        self.assertTrue(tenant.maintenance_mode)
        self.assertEqual(subscription.plan.code, "starter")
        self.assertEqual(subscription.status, TenantSubscription.Status.TRIALING)
        self.assertEqual(subscription.plan.trial_days, 30)
        self.assertTrue(subscription.plan.requires_payment_method)
        self.assertIsNotNone(subscription.trial_ends_at)
        self.assertEqual(subscription.billing_provider_code, "asaas")
        self.assertEqual(subscription.billing_provider_label, "Asaas")
        self.assertEqual(owner.role, "owner")
        self.assertTrue(user.check_password("StrongPass123!"))
        self.assertEqual(onboarding.status, TenantOnboarding.Status.COMPLETED)
        self.assertEqual(SubscriptionAcquisitionLead.objects.count(), 0)
        self.assertTrue(AuditLog.objects.filter(tenant=tenant, action="tenant.self_service_created").exists())
        self.assertTrue(AuditLog.objects.filter(tenant=tenant, action="tenant.self_service_signup_completed").exists())

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=10,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_public_signup_applies_coupon_snapshot_to_trial_subscription(self):
        subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="100.00",
            trial_days=30,
            requires_payment_method=True,
        )
        SubscriptionCoupon.objects.create(
            code="saas25",
            name="SaaS 25",
            discount_type=SubscriptionCoupon.DiscountType.FIXED,
            discount_value="25.00",
        )

        response = self.client.post(
            reverse("subscription_public:plans-signup"),
            {
                "plan_code": "starter",
                "store_name": "Coupon Signup",
                "desired_subdomain": "coupon-signup",
                "owner_name": "Coupon Owner",
                "owner_email": "coupon.owner@example.com",
                "access_token": "signup-token",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "accept_terms": "1",
                "coupon_code": "saas25",
            },
            HTTP_HOST=self.platform_host,
        )

        tenant = Tenant.objects.get(slug="coupon-signup")
        subscription = TenantSubscription.objects.get(tenant=tenant)
        onboarding = TenantOnboarding.objects.get(tenant=tenant)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cupom SAAS25")
        self.assertEqual(subscription.coupon_code_snapshot, "SAAS25")
        self.assertEqual(str(subscription.coupon_discount_total_snapshot), "25.00")
        self.assertEqual(str(subscription.effective_monthly_price_snapshot), "75.00")
        self.assertEqual(onboarding.coupon_code_snapshot, "SAAS25")
        self.assertEqual(str(onboarding.effective_monthly_price_snapshot), "75.00")
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_applied", entity_type="TenantSubscription").exists())

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=10,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_public_signup_rejects_invalid_coupon_before_side_effects(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")

        response = self.client.post(
            reverse("subscription_public:plans-signup"),
            {
                "plan_code": "starter",
                "store_name": "Invalid Coupon Signup",
                "desired_subdomain": "invalid-coupon-signup",
                "owner_name": "Invalid Coupon Owner",
                "owner_email": "invalid.coupon.owner@example.com",
                "access_token": "signup-token",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "accept_terms": "1",
                "coupon_code": "missing",
            },
            HTTP_HOST=self.platform_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cupom SaaS inválido")
        self.assertFalse(Tenant.objects.filter(slug="invalid-coupon-signup").exists())
        self.assertFalse(OwnerUser.objects.filter(email="invalid.coupon.owner@example.com").exists())
        self.assertFalse(TenantSubscription.objects.filter(external_reference__icontains="invalid-coupon-signup").exists())

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=10,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_public_signup_requires_access_token_when_controlled(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="99.90")

        response = self.client.post(
            reverse("subscription_public:plans-signup"),
            {
                "plan_code": "starter",
                "store_name": "Blocked Store",
                "desired_subdomain": "blocked-store",
                "owner_name": "Blocked Owner",
                "owner_email": "blocked.owner@example.com",
                "password": "StrongPass123!",
                "password_confirm": "StrongPass123!",
                "accept_terms": "1",
            },
            HTTP_HOST=self.platform_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Codigo de acesso invalido")
        self.assertFalse(Tenant.objects.filter(slug="blocked-store").exists())
        self.assertFalse(OwnerUser.objects.filter(email="blocked.owner@example.com").exists())

    @override_settings(
        HUBX_PUBLIC_SIGNUP_ENABLED=True,
        HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN="signup-token",
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_MAX_ATTEMPTS=10,
        HUBX_PUBLIC_SIGNUP_RATE_LIMIT_WINDOW_SECONDS=60,
    )
    def test_public_signup_handles_subdomain_race_as_form_error(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="99.90")

        with patch(
            "app.modules.tenants.application.public_tenant_signup_commands.Tenant.objects.create",
            side_effect=IntegrityError("duplicate subdomain"),
        ):
            response = self.client.post(
                reverse("subscription_public:plans-signup"),
                {
                    "plan_code": "starter",
                    "store_name": "Race Store",
                    "desired_subdomain": "race-store",
                    "owner_name": "Race Owner",
                    "owner_email": "race.owner@example.com",
                    "access_token": "signup-token",
                    "password": "StrongPass123!",
                    "password_confirm": "StrongPass123!",
                    "accept_terms": "1",
                },
                HTTP_HOST=self.platform_host,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este subdominio acabou de ser reservado")
        self.assertFalse(Tenant.objects.filter(slug="race-store").exists())

    def test_platform_acquisition_conversion_creates_onboarding_only(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")
        SubscriptionCoupon.objects.create(
            code="assist20",
            name="Assist 20",
            discount_type=SubscriptionCoupon.DiscountType.PERCENT,
            discount_value="20.00",
        )
        lead_result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": "starter",
                "store_name": "Convert Store",
                "desired_subdomain": "convert-store",
                "contact_name": "Convert Owner",
                "contact_email": "convert.owner@example.com",
                "coupon_code": "assist20",
            }
        )
        owner = User.objects.create_user(username="platform.owner@hubx.market", email="platform.owner@hubx.market", password="secret")
        OwnerUser.objects.create(tenant=self.platform_tenant, email="platform.owner@hubx.market", role="owner", is_active=True)
        self.client.force_login(owner)

        response = self.client.post(
            reverse("subscription_acquisitions:platform-acquisitions-convert", kwargs={"lead_id": lead_result["lead"]["id"]}),
            HTTP_HOST=self.platform_host,
        )

        lead = SubscriptionAcquisitionLead.objects.get(pk=lead_result["lead"]["id"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(lead.status, SubscriptionAcquisitionLead.Status.CONVERTED)
        self.assertIsNotNone(lead.onboarding_id)
        onboarding = TenantOnboarding.objects.get(pk=lead.onboarding_id, plan_code="starter")
        self.assertEqual(onboarding.coupon_code_snapshot, "ASSIST20")
        self.assertEqual(str(onboarding.coupon_discount_total_snapshot), "20.00")
        self.assertEqual(str(onboarding.effective_monthly_price_snapshot), "80.00")
        self.assertFalse(Tenant.objects.filter(slug="convert-store").exists())
        self.assertFalse(TenantSubscription.objects.filter(external_reference__icontains="convert").exists())
        self.assertFalse(OwnerUser.objects.filter(email="convert.owner@example.com").exists())
        self.assertTrue(AuditLog.objects.filter(action="subscription.acquisition_converted").exists())

    def test_platform_acquisition_discard_marks_lead_without_side_effects(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="99.90")
        lead_result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": "starter",
                "store_name": "Discard Store",
                "desired_subdomain": "discard-store",
                "contact_email": "discard@example.com",
            }
        )
        owner = User.objects.create_user(username="platform.admin@hubx.market", email="platform.admin@hubx.market", password="secret")
        OwnerUser.objects.create(tenant=self.platform_tenant, email="platform.admin@hubx.market", role="admin", is_active=True)
        self.client.force_login(owner)

        response = self.client.post(
            reverse("subscription_acquisitions:platform-acquisitions-discard", kwargs={"lead_id": lead_result["lead"]["id"]}),
            HTTP_HOST=self.platform_host,
        )

        lead = SubscriptionAcquisitionLead.objects.get(pk=lead_result["lead"]["id"])
        self.assertEqual(response.status_code, 302)
        self.assertEqual(lead.status, SubscriptionAcquisitionLead.Status.DISCARDED)
        self.assertIsNone(lead.onboarding_id)
        self.assertFalse(Tenant.objects.filter(slug="discard-store").exists())
        self.assertTrue(AuditLog.objects.filter(action="subscription.acquisition_discarded").exists())

    def test_platform_subscription_coupon_surface_allows_owner_and_blocks_support(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="100.00")
        owner = User.objects.create_user(username="coupon.owner@hubx.market", email="coupon.owner@hubx.market", password="secret")
        OwnerUser.objects.create(tenant=self.platform_tenant, email="coupon.owner@hubx.market", role="owner", is_active=True)
        self.client.force_login(owner)

        list_response = self.client.get(
            reverse("subscription_coupons:platform-subscription-coupons-list"),
            HTTP_HOST=self.platform_host,
        )
        create_response = self.client.post(
            reverse("subscription_coupons:platform-subscription-coupons-create"),
            {
                "code": "launch",
                "name": "Launch",
                "status": SubscriptionCoupon.Status.ACTIVE,
                "discount_type": SubscriptionCoupon.DiscountType.PERCENT,
                "discount_value": "15.00",
                "plan_code": "starter",
            },
            HTTP_HOST=self.platform_host,
        )
        coupon = SubscriptionCoupon.objects.get(code="LAUNCH")
        status_response = self.client.post(
            reverse("subscription_coupons:platform-subscription-coupons-status", kwargs={"coupon_id": coupon.id}),
            {"status": SubscriptionCoupon.Status.INACTIVE},
            HTTP_HOST=self.platform_host,
        )

        coupon.refresh_from_db()
        self.assertEqual(list_response.status_code, 200)
        self.assertTemplateUsed(list_response, "pages/templates/admin_subscription_coupons_list_page.html")
        self.assertContains(list_response, "Cupons SaaS")
        self.assertEqual(create_response.status_code, 302)
        self.assertEqual(coupon.plan.code, "starter")
        self.assertEqual(status_response.status_code, 302)
        self.assertEqual(coupon.status, SubscriptionCoupon.Status.INACTIVE)
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_created").exists())
        self.assertTrue(AuditLog.objects.filter(action="subscription.coupon_status_changed").exists())

        support = User.objects.create_user(username="coupon.support@hubx.market", email="coupon.support@hubx.market", password="secret")
        OwnerUser.objects.create(tenant=self.platform_tenant, email="coupon.support@hubx.market", role="support", is_active=True)
        self.client.force_login(support)
        blocked_response = self.client.post(
            reverse("subscription_coupons:platform-subscription-coupons-create"),
            {
                "code": "support",
                "name": "Support",
                "status": SubscriptionCoupon.Status.ACTIVE,
                "discount_type": SubscriptionCoupon.DiscountType.PERCENT,
                "discount_value": "15.00",
            },
            HTTP_HOST=self.platform_host,
        )

        self.assertEqual(blocked_response.status_code, 400)
        self.assertFalse(SubscriptionCoupon.objects.filter(code="SUPPORT").exists())
        self.assertContains(blocked_response, "Permissão platform obrigatória", status_code=400)

    def test_queries_and_admin_surface_are_tenant_scoped(self):
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="99.90")
        subscription_commands.set_tenant_subscription(
            tenant_id=self.tenant.id,
            plan_code="starter",
            status=TenantSubscription.Status.TRIALING,
        )
        subscription_commands.set_tenant_subscription(
            tenant_id=self.other_tenant.id,
            plan_code="starter",
            status=TenantSubscription.Status.ACTIVE,
        )
        user = User.objects.create_user(username="owner@hubx.market", email="owner@hubx.market", password="secret")
        self.client.force_login(user)

        rows = subscription_queries.list_tenant_subscriptions(tenant_id=self.tenant.id)
        response = self.client.get(reverse("subscriptions:admin-subscriptions-list"), HTTP_HOST=self.host)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["tenant_name"], "Billing Tenant")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_subscriptions_list_page.html")
        self.assertContains(response, "Assinatura SaaS")
        self.assertContains(response, "Starter")
        self.assertNotContains(response, "Other Billing")
        self.assertNotContains(response, "Authorization")
        self.assertNotContains(response, "token=")

    def test_foundation_closure_ready_when_all_waves_are_done(self):
        review = subscriptions_foundation_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "subscriptions-foundation-ready")
        self.assertIn("tenant subscription state", review["closure_scope"])
        self.assertIn("Battery F — Audit Instrumentation Expansion", review["next_tracks"])

    def test_foundation_command_outputs_no_sensitive_material(self):
        output = StringIO()

        call_command("subscriptions_foundation", *self._ready_args(), stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("result=subscriptions-foundation-ready", value)
        self.assertIn("next_track=Battery F — Audit Instrumentation Expansion", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("token=", value)

    def test_foundation_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("subscriptions_foundation", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "domain_contract_ready": True,
            "plan_model_ready": True,
            "tenant_subscription_state_ready": True,
            "admin_read_surface_review_ready": True,
            "admin_read_surface_ready": True,
            "enforcement_boundary_ready": True,
            "audit_events_ready": True,
            "no_billing_provider_created": True,
            "no_store_payment_coupling": True,
            "docs_updated": True,
            "decision_recorded": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return tuple(f"--{key.replace('_', '-')}" for key, value in self._ready_flags().items() if value)
