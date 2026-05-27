from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.audit.models import AuditLog
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.application.subscription_queries import subscription_queries
from app.modules.subscriptions.application.subscriptions_foundation_queries import subscriptions_foundation_queries
from app.modules.subscriptions.models import SubscriptionPlan, TenantSubscription
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market"])
class SubscriptionsFoundationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Billing Tenant", slug="billing-tenant", subdomain="billing-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Billing", slug="other-billing", subdomain="other-billing")
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def test_plan_and_tenant_subscription_are_created_with_audit(self):
        plan_result = subscription_commands.upsert_plan(
            code="starter",
            name="Starter",
            monthly_price="99.90",
            included_api_quota=10000,
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
        self.assertEqual(str(SubscriptionPlan.objects.get(code="starter").monthly_price), plan_result["plan"]["monthly_price"])
        subscription = TenantSubscription.objects.get(tenant=self.tenant)
        self.assertEqual(subscription.plan.code, "starter")
        self.assertEqual(subscription.status, TenantSubscription.Status.ACTIVE)
        self.assertTrue(AuditLog.objects.filter(module="subscriptions", action="subscription.plan_upserted").exists())
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, action="tenant_subscription.updated").exists())

    def test_tenant_subscription_requires_existing_plan_and_tenant(self):
        missing_tenant = subscription_commands.set_tenant_subscription(tenant_id=None, plan_code="starter")
        missing_plan = subscription_commands.set_tenant_subscription(tenant_id=self.tenant.id, plan_code="starter")

        self.assertEqual(missing_tenant["result"], "tenant-subscription-tenant-required")
        self.assertEqual(missing_plan["result"], "tenant-subscription-plan-not-found")

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
