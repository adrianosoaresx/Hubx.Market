from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.audit.application.admin_audit_log_queries import admin_audit_log_queries
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class AuditLogContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Audit", slug="loja-audit", subdomain="loja-audit")
        self.other_tenant = Tenant.objects.create(name="Outra Audit", slug="outra-audit", subdomain="outra-audit")
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"

    def test_record_event_requires_tenant_by_default(self):
        result = audit_log_commands.record_event(
            tenant_id=None,
            module="orders",
            action="status_changed",
        )

        self.assertEqual(result["result"], "audit-tenant-required")
        self.assertEqual(AuditLog.objects.count(), 0)

    def test_record_event_creates_tenant_scoped_log(self):
        result = audit_log_commands.record_event(
            tenant_id=self.tenant.id,
            module="orders",
            action="status_changed",
            entity_type="Order",
            entity_id="123",
            actor_label="owner@example.com",
            summary="Pedido atualizado",
            metadata={"status": "paid", "unsafe": {"nested": "value"}},
        )

        self.assertEqual(result["result"], "audit-recorded")
        log = AuditLog.objects.get()
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.module, "orders")
        self.assertEqual(log.action, "status_changed")
        self.assertEqual(log.metadata["status"], "paid")
        self.assertIsInstance(log.metadata["unsafe"], str)

    def test_record_event_allows_platform_scope_only_when_explicit(self):
        result = audit_log_commands.record_event(
            tenant_id=None,
            module="tenants",
            action="maintenance_enabled",
            allow_platform_scope=True,
        )

        self.assertEqual(result["result"], "audit-recorded")
        self.assertIsNone(AuditLog.objects.get().tenant)

    def test_admin_query_lists_only_current_tenant_logs(self):
        AuditLog.objects.create(tenant=self.tenant, module="orders", action="updated", summary="Atual")
        AuditLog.objects.create(tenant=self.other_tenant, module="orders", action="updated", summary="Outro")
        AuditLog.objects.create(module="tenants", action="platform", summary="Global")

        logs = admin_audit_log_queries.list_logs(tenant_id=self.tenant.id)

        self.assertEqual([log["summary"] for log in logs], ["Atual"])

    def test_admin_query_filters_module_action_and_search(self):
        AuditLog.objects.create(tenant=self.tenant, module="orders", action="updated", summary="Pedido atualizado")
        AuditLog.objects.create(tenant=self.tenant, module="catalog", action="updated", summary="Produto atualizado")

        logs = admin_audit_log_queries.list_logs(
            tenant_id=self.tenant.id,
            module="orders",
            action="updated",
            search="pedido",
        )

        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["module"], "orders")

    def test_admin_query_reads_platform_scope_only_when_explicit(self):
        AuditLog.objects.create(module="tenants", action="created", summary="Tenant criado")

        tenant_logs = admin_audit_log_queries.list_logs(tenant_id=None)
        platform_logs = admin_audit_log_queries.list_logs(tenant_id=None, allow_platform_scope=True)

        self.assertEqual(tenant_logs, [])
        self.assertEqual(len(platform_logs), 1)
        self.assertEqual(platform_logs[0]["summary"], "Tenant criado")

    def test_admin_view_renders_current_tenant_logs(self):
        AuditLog.objects.create(tenant=self.tenant, module="orders", action="updated", summary="Pedido atualizado")
        AuditLog.objects.create(tenant=self.other_tenant, module="orders", action="updated", summary="Outro tenant")

        response = self.client.get(reverse("audit:admin-audit-log-list"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_audit_log_list_page.html")
        self.assertContains(response, "Pedido atualizado")
        self.assertNotContains(response, "Outro tenant")

    def test_admin_view_filters_logs(self):
        AuditLog.objects.create(tenant=self.tenant, module="orders", action="updated", summary="Pedido atualizado")
        AuditLog.objects.create(tenant=self.tenant, module="catalog", action="updated", summary="Produto atualizado")

        response = self.client.get(
            reverse("audit:admin-audit-log-list"),
            {"module": "orders"},
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedido atualizado")
        self.assertNotContains(response, "Produto atualizado")

    def test_admin_export_view_returns_tenant_scoped_jsonl(self):
        AuditLog.objects.create(tenant=self.tenant, module="orders", action="updated", summary="Pedido atualizado")
        AuditLog.objects.create(tenant=self.other_tenant, module="orders", action="updated", summary="Outro tenant")

        response = self.client.get(reverse("audit:admin-audit-evidence-export"), HTTP_HOST=self.host)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/x-ndjson; charset=utf-8")
        self.assertContains(response, "Pedido atualizado")
        self.assertNotContains(response, "Outro tenant")

    def test_admin_export_view_rejects_missing_tenant_context(self):
        response = self.client.get(reverse("audit:admin-audit-evidence-export"), HTTP_HOST="testserver")

        self.assertEqual(response.status_code, 400)
