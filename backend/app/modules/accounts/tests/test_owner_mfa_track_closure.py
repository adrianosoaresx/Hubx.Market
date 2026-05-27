from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.accounts.application.owner_mfa_track_closure_queries import owner_mfa_track_closure_queries
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class OwnerMfaTrackClosureTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Owner MFA Track Closure",
            slug="owner-mfa-track-closure",
            subdomain="owner-mfa-track-closure",
        )

    def test_track_closure_ready_when_audit_and_track_signals_are_clean(self):
        self._mfa_log()

        closure = owner_mfa_track_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            **self._audit_flags(),
            **self._track_flags(),
        )

        self.assertTrue(closure["ready"])
        self.assertEqual(closure["result"], "owner-mfa-track-closure-ready")
        self.assertEqual(closure["blockers"], ())
        self.assertIn("Security ROI Re-Selection Review", closure["next_tracks"])

    def test_track_closure_blocks_when_audit_closure_is_blocked(self):
        closure = owner_mfa_track_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            **self._audit_flags(),
            **self._track_flags(),
        )

        self.assertFalse(closure["ready"])
        self.assertIn("audit:owner-mfa-audit-evidence-export-closure-blocked", closure["blockers"])
        self.assertIn("audit:export:evidence:no-mfa-events", closure["blockers"])

    def test_track_closure_blocks_when_support_handoff_is_missing(self):
        self._mfa_log()
        track_flags = self._track_flags()
        track_flags["support_handoff_completed"] = False

        closure = owner_mfa_track_closure_queries.get_closure(
            tenant_id=self.tenant.id,
            **self._audit_flags(),
            **track_flags,
        )

        self.assertFalse(closure["ready"])
        self.assertIn("track:support-handoff-not-completed", closure["blockers"])

    def test_command_outputs_track_closure_without_export_content(self):
        self._mfa_log()
        output = StringIO()

        call_command(
            "owner_mfa_track_closure",
            "--tenant-id",
            str(self.tenant.id),
            "--expected-actions-confirmed",
            "--export-scope-documented",
            "--redaction-reviewed",
            "--recipient-approved",
            "--artifact-delivered",
            "--retention-owner-confirmed",
            "--storage-decision-recorded",
            "--audit-residual-risks-accepted",
            "--mfa-track-decision-recorded",
            "--rollout-state-documented",
            "--support-handoff-completed",
            "--next-roi-decision-recorded",
            "--track-residual-risks-accepted",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("decision key=classification", output.getvalue())
        self.assertIn("mfa_action=owner.mfa_factor_verified", output.getvalue())
        self.assertNotIn('"action"', output.getvalue())
        self.assertNotIn("must-not-export", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "owner_mfa_track_closure",
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

    def _audit_flags(self) -> dict[str, bool]:
        return {
            "expected_actions_confirmed": True,
            "export_scope_documented": True,
            "redaction_reviewed": True,
            "recipient_approved": True,
            "artifact_delivered": True,
            "retention_owner_confirmed": True,
            "storage_decision_recorded": True,
            "audit_residual_risks_accepted": True,
        }

    def _track_flags(self) -> dict[str, bool]:
        return {
            "mfa_track_decision_recorded": True,
            "rollout_state_documented": True,
            "support_handoff_completed": True,
            "next_roi_decision_recorded": True,
            "track_residual_risks_accepted": True,
        }
