from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.application.owner_access_metrics_queries import owner_access_metrics_queries
from app.modules.audit.models import AuditLog
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


class OwnerAccessMetricsTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Owner Metrics", slug="owner-metrics", subdomain="owner-metrics")

    def test_exports_owner_access_audit_and_email_metrics(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.login_failed",
            actor_label="owner@hubx.market",
        )
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.login_rate_limited",
            actor_label="owner@hubx.market",
        )
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.ops_permission_denied",
            actor_label="owner@hubx.market",
        )
        EmailLog.objects.create(
            tenant=self.tenant,
            source_event="owner.invited",
            intent_key="owner.access.invite",
            audience="owner",
            entity_type="owner_user",
            entity_id="1",
            idempotency_key=f"{self.tenant.id}:owner.access.invite:owner_user:1",
            recipient_delivery_key=f"{self.tenant.id}:owner.access.invite:owner_user:1:email:owner@hubx.market",
            recipient_type="owner_user",
            recipient_id="1",
            recipient_email="owner@hubx.market",
            title="Acesso administrativo",
            status=EmailLog.Status.FAILED,
        )

        payload = owner_access_metrics_queries.export_prometheus_metrics()

        self.assertIn("hubx_accounts_owner_access_audit_event_total", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",action="owner.login_failed"', payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",action="owner.login_rate_limited"', payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",action="owner.ops_permission_denied"', payload)
        self.assertIn("hubx_accounts_owner_access_email_log_total", payload)
        self.assertIn('intent_key="owner.access.invite",status="failed"', payload)

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="accounts-token")
    def test_metrics_view_returns_prometheus_payload_with_token(self):
        response = self.client.get(
            reverse("accounts:owner-access-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="accounts-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/plain; version=0.0.4; charset=utf-8")
        self.assertContains(response, "hubx_accounts_owner_access_audit_event_total")

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="accounts-token")
    def test_metrics_view_accepts_bearer_token(self):
        response = self.client.get(
            reverse("accounts:owner-access-metrics"),
            HTTP_AUTHORIZATION="Bearer accounts-token",
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="accounts-token")
    def test_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("accounts:owner-access-metrics"))

        self.assertEqual(response.status_code, 403)

    @override_settings(ACCOUNTS_OBSERVABILITY_TOKEN="")
    def test_metrics_view_is_not_found_without_configured_token(self):
        response = self.client.get(reverse("accounts:owner-access-metrics"))

        self.assertEqual(response.status_code, 404)
