from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.accounts.application.security_roi_reselection_queries import security_roi_reselection_queries
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class SecurityRoiReselectionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Security ROI",
            slug="security-roi",
            subdomain="security-roi",
        )

    def test_reselection_recommends_api_key_governance_when_surface_is_active(self):
        self._mfa_log()

        review = security_roi_reselection_queries.get_review(
            tenant_id=self.tenant.id,
            **self._closure_flags(),
            api_key_surface_active=True,
            session_policy_gap_confirmed=True,
        )

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "security-roi-reselection-ready")
        self.assertEqual(review["recommendation"].recommended_track, "API Key Governance Foundation Review")
        self.assertIn("API Key Governance Foundation Review", review["next_tracks"])

    def test_reselection_blocks_when_mfa_track_closure_is_not_ready(self):
        review = security_roi_reselection_queries.get_review(
            tenant_id=self.tenant.id,
            **self._closure_flags(),
            api_key_surface_active=True,
        )

        self.assertFalse(review["ready"])
        self.assertIn("mfa:owner-mfa-track-closure-blocked", review["blockers"])

    def test_reselection_blocks_when_no_candidate_crosses_threshold(self):
        self._mfa_log()

        review = security_roi_reselection_queries.get_review(
            tenant_id=self.tenant.id,
            **self._closure_flags(),
        )

        self.assertFalse(review["ready"])
        self.assertIn("roi:no-security-candidate-above-threshold", review["blockers"])

    def test_command_outputs_recommendation_without_export_content(self):
        self._mfa_log()
        output = StringIO()

        call_command(
            "security_roi_reselection",
            "--tenant-id",
            str(self.tenant.id),
            *self._closure_flag_args(),
            "--api-key-surface-active",
            stdout=output,
        )

        self.assertIn("[READY]", output.getvalue())
        self.assertIn("recommendation=API Key Governance Foundation Review", output.getvalue())
        self.assertIn("candidate key=api-key-governance", output.getvalue())
        self.assertNotIn('"action"', output.getvalue())
        self.assertNotIn("must-not-export", output.getvalue())

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command(
                "security_roi_reselection",
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

    def _closure_flags(self) -> dict[str, bool]:
        return {
            "expected_actions_confirmed": True,
            "export_scope_documented": True,
            "redaction_reviewed": True,
            "recipient_approved": True,
            "artifact_delivered": True,
            "retention_owner_confirmed": True,
            "storage_decision_recorded": True,
            "audit_residual_risks_accepted": True,
            "mfa_track_decision_recorded": True,
            "rollout_state_documented": True,
            "support_handoff_completed": True,
            "next_roi_decision_recorded": True,
            "track_residual_risks_accepted": True,
        }

    def _closure_flag_args(self) -> tuple[str, ...]:
        return (
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
        )
