from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.audit.application.audit_evidence_closure_queries import audit_evidence_closure_queries
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class AuditEvidenceClosureQueryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit Closure", slug="audit-closure", subdomain="audit-closure")

    def test_closure_ready_for_tenant_scope(self):
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.login")

        closure = audit_evidence_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertEqual(closure["result"], "audit-evidence-closure-ready")
        self.assertTrue(closure["ready"])
        self.assertEqual(closure["sample_count"], 1)
        self.assertIn("Platform Owner MFA/SSO Review", closure["next_tracks"])

    def test_closure_ready_for_empty_tenant_scope(self):
        closure = audit_evidence_closure_queries.get_closure(tenant_id=self.tenant.id)

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["sample_count"], 0)

    def test_closure_blocks_without_scope(self):
        closure = audit_evidence_closure_queries.get_closure()

        self.assertFalse(closure["ready"])
        self.assertIn("audit-evidence-export-tenant-required", closure["blockers"])


class AuditEvidenceClosureCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Audit Closure Cmd", slug="audit-closure-cmd", subdomain="audit-closure-cmd")

    def test_command_outputs_ready_closure(self):
        output = StringIO()

        call_command("audit_evidence_closure", "--tenant-id", str(self.tenant.id), stdout=output)

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=command-export", output.getvalue())
        self.assertIn("next_track=", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("audit_evidence_closure", "--fail-on-blockers", stdout=StringIO())
