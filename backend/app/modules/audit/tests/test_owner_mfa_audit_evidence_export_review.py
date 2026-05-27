from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.audit.application.owner_mfa_audit_evidence_export_review_queries import (
    owner_mfa_audit_evidence_export_review_queries,
)
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaAuditEvidenceExportReviewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Owner MFA Audit Export",
            slug="owner-mfa-audit-export",
            subdomain="owner-mfa-audit-export",
        )
        self.other_tenant = Tenant.objects.create(
            name="Other MFA Audit Export",
            slug="other-mfa-audit-export",
            subdomain="other-mfa-audit-export",
        )

    def test_review_ready_for_tenant_scoped_mfa_events(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="MFA verified",
            metadata={"secret": "must-not-export"},
        )
        AuditLog.objects.create(
            tenant=self.other_tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="Other tenant",
        )

        review = owner_mfa_audit_evidence_export_review_queries.get_review(
            tenant_id=self.tenant.id,
            expected_actions_confirmed=True,
            export_scope_documented=True,
            redaction_reviewed=True,
            recipient_approved=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "owner-mfa-audit-evidence-export-review-ready")
        self.assertEqual(review["sample_count"], 1)
        self.assertEqual(review["mfa_event_count"], 1)
        self.assertIn("owner.mfa_factor_verified", review["mfa_actions"])
        self.assertIn("Owner MFA Audit Evidence Export Execution", review["next_tracks"])

    def test_review_blocks_without_mfa_events(self):
        AuditLog.objects.create(tenant=self.tenant, module="accounts", action="owner.login", summary="Login")

        review = owner_mfa_audit_evidence_export_review_queries.get_review(
            tenant_id=self.tenant.id,
            expected_actions_confirmed=True,
            export_scope_documented=True,
            redaction_reviewed=True,
            recipient_approved=True,
        )

        self.assertFalse(review["ready"])
        self.assertEqual(review["status"], "blocked")
        self.assertIn("evidence:no-mfa-events", review["blockers"])

    def test_review_blocks_without_required_confirmations(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.mfa_recovery_code_used",
            summary="Recovery code used",
        )

        review = owner_mfa_audit_evidence_export_review_queries.get_review(tenant_id=self.tenant.id)

        self.assertFalse(review["ready"])
        self.assertIn("review:expected-actions-not-confirmed", review["blockers"])
        self.assertIn("review:redaction-not-reviewed", review["blockers"])

    def test_command_outputs_review_without_metadata(self):
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="MFA verified",
            metadata={"secret": "must-not-export"},
        )
        output = StringIO()

        call_command(
            "owner_mfa_audit_evidence_export_review",
            "--tenant-id",
            str(self.tenant.id),
            "--expected-actions-confirmed",
            "--export-scope-documented",
            "--redaction-reviewed",
            "--recipient-approved",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("mfa_action=owner.mfa_factor_verified", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertNotIn("must-not-export", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_audit_evidence_export_review",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )
