from __future__ import annotations

from io import StringIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.application.api_key_commercial_quotas_closure_queries import (
    api_key_commercial_quotas_closure_queries,
)
from app.modules.api_keys.application.api_key_public_endpoint_metrics import api_key_public_endpoint_metrics
from app.modules.api_keys.application.api_key_quota_commands import api_key_quota_commands
from app.modules.api_keys.application.api_key_quota_enforcement import api_key_quota_enforcement
from app.modules.api_keys.application.api_key_quota_queries import api_key_quota_queries
from app.modules.api_keys.models import ApiKeyQuota, ApiKeyQuotaUsage
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


@override_settings(
    API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED=True,
    API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED=True,
    ALLOWED_HOSTS=[".hubx.market", "testserver"],
)
class ApiKeyCommercialQuotasExecutionTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.tenant = Tenant.objects.create(name="Quota Tenant", slug="quota-tenant", subdomain="quota-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Quota", slug="other-quota", subdomain="other-quota")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.key = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="Catalog partner",
            scopes=["read:catalog"],
        )
        self.api_key_id = self.key["api_key"]["id"]

    def tearDown(self):
        cache.clear()

    def test_quota_model_command_is_tenant_scoped_and_records_audit_without_secret(self):
        result = api_key_quota_commands.upsert_quota(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            limit=10,
            window_seconds=3600,
            actor_label="owner@hubx.market",
        )
        cross_tenant = api_key_quota_commands.upsert_quota(
            tenant_id=self.other_tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
        )

        self.assertEqual(result["result"], "api-key-quota-created")
        self.assertEqual(cross_tenant["result"], "api-key-quota-api-key-not-found")
        quota = ApiKeyQuota.objects.get(pk=result["quota"]["id"])
        self.assertEqual(quota.tenant, self.tenant)
        self.assertEqual(quota.limit, 10)
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.quota_upserted")
        self.assertEqual(audit_log.metadata["prefix"], self.key["api_key"]["prefix"])
        self.assertNotIn("secret", str(audit_log.metadata).lower())
        self.assertNotIn("key_hash", str(audit_log.metadata).lower())
        self.assertNotIn(self.key["secret"], str(audit_log.metadata))

    def test_runtime_enforcement_allows_when_quota_is_not_configured(self):
        decision = api_key_quota_enforcement.check_allowed(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            prefix=self.key["api_key"]["prefix"],
        )

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "api-key-quota-not-configured")
        self.assertEqual(ApiKeyQuotaUsage.objects.count(), 0)

    def test_runtime_enforcement_blocks_after_quota_limit_and_records_observability(self):
        api_key_quota_commands.upsert_quota(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            limit=1,
            window_seconds=3600,
        )

        first = api_key_quota_enforcement.check_allowed(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            prefix=self.key["api_key"]["prefix"],
        )
        blocked = api_key_quota_enforcement.check_allowed(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            prefix=self.key["api_key"]["prefix"],
        )

        self.assertTrue(first.allowed)
        self.assertFalse(blocked.allowed)
        self.assertEqual(blocked.reason, "api-key-quota-exceeded")
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.quota_exceeded")
        self.assertEqual(audit_log.metadata["limit"], 1)
        metrics = api_key_public_endpoint_metrics.export_prometheus_metrics()
        self.assertIn("hubx_api_key_quota_exceeded_total", metrics)
        self.assertIn('result="quota_exceeded"', metrics)

    def test_public_endpoint_returns_429_when_commercial_quota_is_exceeded(self):
        api_key_quota_commands.upsert_quota(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            limit=1,
            window_seconds=3600,
        )

        first_response = self._get_public_products()
        blocked_response = self._get_public_products()

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(blocked_response.status_code, 429)
        self.assertIn("Retry-After", blocked_response)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, action="api_key.quota_exceeded").exists())

    def test_admin_quota_visibility_is_read_only_and_tenant_scoped(self):
        api_key_quota_commands.upsert_quota(
            tenant_id=self.tenant.id,
            api_key_id=self.api_key_id,
            endpoint="catalog.products.list",
            limit=50,
            window_seconds=86400,
        )
        user = User.objects.create_user(username="owner@hubx.market", email="owner@hubx.market", password="secret")
        self.client.force_login(user)

        rows = api_key_quota_queries.list_quotas(tenant_id=self.tenant.id)
        other_rows = api_key_quota_queries.list_quotas(tenant_id=self.other_tenant.id)
        response = self.client.get(reverse("api_keys_ops:admin-api-key-quotas-list"), HTTP_HOST=self.host)

        self.assertEqual(len(rows), 1)
        self.assertEqual(other_rows, [])
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_api_key_quotas_page.html")
        self.assertContains(response, "Quotas de API keys")
        self.assertContains(response, "Catalog partner")
        self.assertContains(response, "catalog.products.list")
        self.assertNotContains(response, self.key["secret"])
        self.assertNotContains(response, "key_hash")

    def test_closure_ready_when_all_battery_b_waves_are_done(self):
        review = api_key_commercial_quotas_closure_queries.get_review(**self._closure_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-commercial-quotas-closure-ready")
        self.assertIn("ApiKeyQuota model", review["closure_scope"])
        self.assertIn("System ROI Re-Selection Review", review["next_tracks"])

    def test_closure_command_outputs_no_sensitive_material(self):
        output = StringIO()

        call_command("api_key_commercial_quotas_closure", *self._closure_args(), stdout=output)

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("result=api-key-commercial-quotas-closure-ready", value)
        self.assertIn("closure_scope=runtime quota enforcement after rate-limit", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("Bearer", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_closure_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_commercial_quotas_closure", "--fail-on-blockers", stdout=StringIO())

    def _get_public_products(self):
        return self.client.get(
            reverse("catalog_public_api:products-list"),
            HTTP_HOST=self.host,
            HTTP_AUTHORIZATION=f"Bearer {self.key['secret']}",
        )

    def _closure_flags(self) -> dict[str, bool]:
        return {
            "contract_ready": True,
            "model_ready": True,
            "enforcement_review_ready": True,
            "enforcement_ready": True,
            "admin_visibility_review_ready": True,
            "admin_visibility_ready": True,
            "metrics_ready": True,
            "audit_ready": True,
            "no_billing_charge_created": True,
            "no_plan_enforcement_created": True,
            "no_sensitive_material_recorded": True,
            "docs_updated": True,
            "decision_recorded": True,
        }

    def _closure_args(self) -> tuple[str, ...]:
        return (
            "--contract-ready",
            "--model-ready",
            "--enforcement-review-ready",
            "--enforcement-ready",
            "--admin-visibility-review-ready",
            "--admin-visibility-ready",
            "--metrics-ready",
            "--audit-ready",
            "--no-billing-charge-created",
            "--no-plan-enforcement-created",
            "--no-sensitive-material-recorded",
            "--docs-updated",
            "--decision-recorded",
        )
