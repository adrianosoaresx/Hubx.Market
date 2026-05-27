from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.audit.application.audit_evidence_export_queries import audit_evidence_export_queries
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class AuditEvidenceExportQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit Export", slug="audit-export", subdomain="audit-export")
        self.other_tenant = Tenant.objects.create(name="Other Export", slug="other-export", subdomain="other-export")

    def test_export_requires_tenant_or_platform_scope(self):
        result = audit_evidence_export_queries.export(tenant_id=None)

        self.assertEqual(result["result"], "audit-evidence-export-tenant-required")

    def test_export_jsonl_is_tenant_scoped(self):
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.login", summary="Atual")
        AuditLog.objects.create(tenant=self.other_tenant, module="accounts", action="owner.login", summary="Outro")

        result = audit_evidence_export_queries.export(tenant_id=self.tenant.id)

        self.assertEqual(result["result"], "audit-evidence-exported")
        self.assertEqual(result["count"], 1)
        row = json.loads(result["content"])
        self.assertEqual(row["tenant_id"], self.tenant.id)
        self.assertEqual(row["summary"], "Atual")

    def test_export_filters_module_action_and_includes_metadata(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.ops_permission_denied",
            summary="Bloqueado",
            metadata={"path": "/ops/owners/"},
        )
        AuditLog.objects.create(tenant=self.tenant, module="orders", action="updated", summary="Pedido")

        result = audit_evidence_export_queries.export(
            tenant_id=self.tenant.id,
            module="accounts",
            action="owner.ops_permission_denied",
            include_metadata=True,
        )

        row = json.loads(result["content"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(row["metadata"]["path"], "/ops/owners/")

    def test_export_platform_scope_only_when_explicit(self):
        AuditLog.objects.create(module="tenants", action="maintenance_enabled", summary="Global")

        result = audit_evidence_export_queries.export(tenant_id=None, allow_platform_scope=True)

        self.assertEqual(result["count"], 1)
        row = json.loads(result["content"])
        self.assertIsNone(row["tenant_id"])

    def test_export_csv_outputs_header_and_row(self):
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.login", summary="Entrou")

        result = audit_evidence_export_queries.export(tenant_id=self.tenant.id, output_format="csv")

        self.assertIn("id,tenant_id,module,action", result["content"])
        self.assertIn("accounts,owner.login", result["content"])


class AuditEvidenceExportCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit Export Cmd", slug="audit-export-cmd", subdomain="audit-export-cmd")

    def test_command_outputs_jsonl(self):
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.login", summary="Entrou")
        output = StringIO()

        call_command("export_audit_evidence", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn('"module": "accounts"', output.getvalue())
        self.assertIn('"action": "owner.login"', output.getvalue())

    def test_command_can_fail_on_empty_export(self):
        with self.assertRaises(CommandError):
            call_command(
                "export_audit_evidence",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-empty",
                stdout=StringIO(),
            )
