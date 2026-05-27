from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.audit.application.owner_mfa_audit_evidence_export_execution_queries import (
    owner_mfa_audit_evidence_export_execution_queries,
)
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaAuditEvidenceExportExecutionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Owner MFA Audit Export Execution",
            slug="owner-mfa-audit-export-execution",
            subdomain="owner-mfa-audit-export-execution",
        )
        self.other_tenant = Tenant.objects.create(
            name="Other MFA Audit Export Execution",
            slug="other-mfa-audit-export-execution",
            subdomain="other-mfa-audit-export-execution",
        )

    def test_export_outputs_only_tenant_scoped_mfa_rows_without_metadata(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="MFA verified",
            metadata={"secret": "must-not-export"},
        )
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.login", summary="Login")
        AuditLog.objects.create(
            tenant=self.other_tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="Other tenant",
        )

        result = owner_mfa_audit_evidence_export_execution_queries.export(
            tenant_id=self.tenant.id,
            expected_actions_confirmed=True,
            export_scope_documented=True,
            redaction_reviewed=True,
            recipient_approved=True,
        )

        self.assertEqual(result["result"], "owner-mfa-audit-evidence-exported")
        self.assertEqual(result["count"], 1)
        row = json.loads(result["content"])
        self.assertEqual(row["tenant_id"], self.tenant.id)
        self.assertEqual(row["action"], "owner.mfa_factor_verified")
        self.assertNotIn("metadata", row)
        self.assertNotIn("must-not-export", result["content"])
        self.assertNotIn("Other tenant", result["content"])

    def test_export_blocks_when_review_is_not_ready(self):
        result = owner_mfa_audit_evidence_export_execution_queries.export(tenant_id=self.tenant.id)

        self.assertFalse(result["ready"])
        self.assertEqual(result["result"], "owner-mfa-audit-evidence-export-blocked")
        self.assertIn("evidence:no-mfa-events", result["blockers"])

    def test_export_supports_csv(self):
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.mfa_recovery_code_used")

        result = owner_mfa_audit_evidence_export_execution_queries.export(
            tenant_id=self.tenant.id,
            output_format="csv",
            expected_actions_confirmed=True,
            export_scope_documented=True,
            redaction_reviewed=True,
            recipient_approved=True,
        )

        self.assertEqual(result["format"], "csv")
        self.assertIn("id,tenant_id,module,action", result["content"])
        self.assertIn("accounts,owner.mfa_recovery_code_used", result["content"])

    def test_command_outputs_jsonl_without_metadata(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="MFA verified",
            metadata={"secret": "must-not-export"},
        )
        output = StringIO()

        call_command(
            "export_owner_mfa_audit_evidence",
            "--tenant-id",
            str(self.tenant.id),
            "--expected-actions-confirmed",
            "--export-scope-documented",
            "--redaction-reviewed",
            "--recipient-approved",
            stdout=output,
        )

        self.assertIn('"action": "owner.mfa_factor_verified"', output.getvalue())
        self.assertNotIn("metadata", output.getvalue())
        self.assertNotIn("must-not-export", output.getvalue())

    def test_command_fails_when_review_is_blocked(self):
        with self.assertRaises(CommandError):
            call_command(
                "export_owner_mfa_audit_evidence",
                "--tenant-id",
                str(self.tenant.id),
                stdout=StringIO(),
            )
