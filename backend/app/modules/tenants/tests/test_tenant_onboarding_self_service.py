from __future__ import annotations

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription
from app.modules.tenants.application.tenant_onboarding_commands import tenant_onboarding_commands
from app.modules.tenants.application.tenant_onboarding_queries import tenant_onboarding_queries
from app.modules.tenants.models import Tenant, TenantOnboarding


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class TenantOnboardingSelfServiceTests(TestCase):
    def setUp(self):
        self.platform_tenant = Tenant.objects.create(
            name="Platform Host",
            slug="platform-host",
            subdomain="platform-host",
        )
        self.host = f"{self.platform_tenant.subdomain}.hubx.market"
        self.owner_user = User.objects.create_user(
            username="platform.owner@hubx.market",
            email="platform.owner@hubx.market",
            password="secret",
        )
        OwnerUser.objects.create(
            tenant=self.platform_tenant,
            email="platform.owner@hubx.market",
            role="owner",
            is_active=True,
        )
        self.client.force_login(self.owner_user)
        subscription_commands.upsert_plan(code="starter", name="Starter", monthly_price="99.90")

    def test_draft_steps_and_completion_create_store_subscription_owner_and_audit(self):
        onboarding = self._create_ready_onboarding()

        result = tenant_onboarding_commands.complete_onboarding(
            onboarding_id=onboarding.id,
            actor_label="platform.owner@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "tenant-onboarding-completed")
        tenant = Tenant.objects.get(slug="nova-loja")
        self.assertEqual(tenant.subdomain, "nova-loja")
        self.assertEqual(tenant.custom_domain, "nova.example.com")
        self.assertTrue(TenantSubscription.objects.filter(tenant=tenant, plan__code="starter").exists())
        self.assertTrue(OwnerUser.objects.filter(tenant=tenant, email="new.owner@hubx.market", role="owner").exists())
        onboarding.refresh_from_db()
        self.assertEqual(onboarding.status, TenantOnboarding.Status.COMPLETED)
        self.assertEqual(onboarding.tenant, tenant)
        self.assertTrue(AuditLog.objects.filter(action="platform.tenant_onboarding.completed").exists())

    def test_step_validation_blocks_duplicate_slug_without_creating_tenant(self):
        Tenant.objects.create(name="Existente", slug="existente", subdomain="existente")
        result = tenant_onboarding_commands.create_onboarding(
            payload={"store_name": "Duplicada"},
            actor_label="platform.owner@hubx.market",
            actor_role="owner",
        )
        onboarding_id = result["onboarding"]["id"]

        step = tenant_onboarding_commands.update_step(
            onboarding_id=onboarding_id,
            step_key="store",
            payload={"store_name": "Duplicada", "store_slug": "existente", "store_subdomain": "nova-duplicada"},
            actor_label="platform.owner@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(step["result"], "tenant-onboarding-step-invalid")
        self.assertEqual(Tenant.objects.filter(slug="nova-duplicada").count(), 0)
        self.assertTrue(AuditLog.objects.filter(action="platform.tenant_onboarding.blocked").exists())

    def test_plan_step_rejects_archived_plan(self):
        SubscriptionPlan.objects.filter(code="starter").update(status=SubscriptionPlan.Status.ARCHIVED)
        onboarding = TenantOnboarding.objects.create(store_name="Plano Bloqueado", created_by_label="ops")

        result = tenant_onboarding_commands.update_step(
            onboarding_id=onboarding.id,
            step_key="plan",
            payload={"plan_code": "starter"},
            actor_label="platform.owner@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "tenant-onboarding-step-invalid")
        self.assertEqual(result["errors"]["plan_code"], "Selecione um plano ativo.")

    def test_role_without_manage_permission_cannot_complete(self):
        onboarding = self._create_ready_onboarding()

        result = tenant_onboarding_commands.complete_onboarding(
            onboarding_id=onboarding.id,
            actor_label="support@hubx.market",
            actor_role="support",
        )

        self.assertEqual(result["result"], "tenant-onboarding-complete-permission-denied")
        self.assertFalse(Tenant.objects.filter(slug="nova-loja").exists())

    def test_queries_return_progress_and_active_plans(self):
        onboarding = self._create_ready_onboarding()

        payload = tenant_onboarding_queries.get_onboarding(onboarding_id=onboarding.id)
        plans = tenant_onboarding_queries.list_active_plans()

        self.assertEqual(payload["progress"], 100)
        self.assertTrue(payload["ready_for_completion"])
        self.assertEqual(plans[0]["code"], "starter")

    def test_list_create_detail_and_complete_views_render_wizard(self):
        list_response = self.client.get(reverse("tenant_onboarding:onboarding-list"), HTTP_HOST=self.host)
        self.assertEqual(list_response.status_code, 200)
        self.assertTemplateUsed(list_response, "pages/templates/admin_tenant_onboarding_list_page.html")
        self.assertContains(list_response, "Onboarding de lojas")

        create_response = self.client.post(
            reverse("tenant_onboarding:onboarding-create"),
            {"store_name": "Via UI", "store_display_name": "Via UI", "primary_color": "#0f766e"},
            HTTP_HOST=self.host,
        )
        self.assertEqual(create_response.status_code, 302)
        onboarding = TenantOnboarding.objects.get(store_name="Via UI")

        detail_response = self.client.get(
            reverse("tenant_onboarding:onboarding-detail", kwargs={"onboarding_id": onboarding.id}),
            HTTP_HOST=self.host,
        )
        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/admin_tenant_onboarding_detail_page.html")
        self.assertContains(detail_response, "Criar/ativar loja")
        self.assertContains(detail_response, "Checklist")

    def _create_ready_onboarding(self) -> TenantOnboarding:
        result = tenant_onboarding_commands.create_onboarding(
            payload={"store_name": "Nova Loja", "store_display_name": "Nova Loja", "primary_color": "#4f46e5"},
            actor_label="platform.owner@hubx.market",
            actor_role="owner",
        )
        onboarding_id = result["onboarding"]["id"]
        for step_key, payload in (
            ("store", {"store_name": "Nova Loja", "store_slug": "nova-loja", "store_subdomain": "nova-loja"}),
            ("plan", {"plan_code": "starter"}),
            ("owner", {"owner_email": "new.owner@hubx.market", "owner_name": "New Owner", "owner_role": "owner"}),
            ("branding", {"store_display_name": "Nova Loja", "primary_color": "#4f46e5"}),
            ("domain", {"custom_domain": "nova.example.com"}),
        ):
            step = tenant_onboarding_commands.update_step(
                onboarding_id=onboarding_id,
                step_key=step_key,
                payload=payload,
                actor_label="platform.owner@hubx.market",
                actor_role="owner",
            )
            self.assertEqual(step["result"], "tenant-onboarding-step-updated")
        return TenantOnboarding.objects.get(pk=onboarding_id)
