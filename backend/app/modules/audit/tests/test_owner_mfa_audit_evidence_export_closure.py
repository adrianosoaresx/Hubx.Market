from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.audit.application.owner_mfa_audit_evidence_export_closure_queries import (
    owner_mfa_audit_evidence_export_closure_queries,
)
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaAuditEvidenceExportClosureTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Owner MFA Audit Export Closure",
            slug="owner-mfa-audit-export-closure",
            subdomain="owner-mfa-audit-export-closure",
        )

    def test_closure_ready_when_export_and_closure_signals_are_clean(self):
        self._mfa_log()

        closure = owner_mfa_audit_evidence_export_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            **self._review_flags(),
            **self._closure_flags(),
        )

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["result"], "owner-mfa-audit-evidence-export-closure-ready")
        self.assertEqual(closure["export_count"], 1)
        self.assertEqual(closure["blockers"], ())
        self.assertIn("Owner MFA Track Closure Review", closure["next_tracks"])

    def test_closure_blocks_when_artifact_was_not_delivered(self):
        self._mfa_log()
        closure_flags = self._closure_flags()
        closure_flags["artifact_delivered"] = False

        closure = owner_mfa_audit_evidence_export_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            **self._review_flags(),
            **closure_flags,
        )

        self.assertFalse(closure["ready"])
        self.assertEqual(closure["status"], "blocked")
        self.assertIn("closure:artifact-not-delivered", closure["blockers"])

    def test_closure_blocks_when_export_is_blocked(self):
        closure = owner_mfa_audit_evidence_export_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            **self._review_flags(),
            **self._closure_flags(),
        )

        self.assertFalse(closure["ready"])
        self.assertIn("export:owner-mfa-audit-evidence-export-blocked", closure["blockers"])
        self.assertIn("export:evidence:no-mfa-events", closure["blockers"])

    def test_command_outputs_closure_without_export_content_or_metadata(self):
        self._mfa_log()
        output = StringIO()

        call_command(
            "owner_mfa_audit_evidence_export_closure",
            "--tenant-id",
            str(self.tenant.id),
            "--expected-actions-confirmed",
            "--export-scope-documented",
            "--redaction-reviewed",
            "--recipient-approved",
            "--artifact-delivered",
            "--retention-owner-confirmed",
            "--storage-decision-recorded",
            "--residual-risks-accepted",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("mfa_action=owner.mfa_factor_verified", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertNotIn("must-not-export", output.getvalue())
        self.assertNotIn('"action"', output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_audit_evidence_export_closure",
                "--tenant-id",
                str(self.tenant.id),
                "--fail-on-blockers",
                stdout=StringIO(),
            )

    def _mfa_log(self) -> None:
        AuditLog.objects.create(
            tenant=self.tenant,
            module="accounts",
            action="owner.mfa_factor_verified",
            summary="MFA verified",
            metadata={"secret": "must-not-export"},
        )

    def _review_flags(self) -> dict[str, bool]:
        return {
            "expected_actions_confirmed": True,
            "export_scope_documented": True,
            "redaction_reviewed": True,
            "recipient_approved": True,
        }

    def _closure_flags(self) -> dict[str, bool]:
        return {
            "artifact_delivered": True,
            "retention_owner_confirmed": True,
            "storage_decision_recorded": True,
            "residual_risks_accepted": True,
        }
