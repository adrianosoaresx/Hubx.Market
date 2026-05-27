from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.security_roi_reselection_queries import security_roi_reselection_queries


class Command(BaseCommand):
    help = "Re-seleciona o próximo ROI de segurança após closure MFA/Vault/Audit."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--since", default="")
        parser.add_argument("--until", default="")
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--format", dest="output_format", choices=["jsonl", "csv"], default="jsonl")
        for name in (
            "expected-actions-confirmed",
            "export-scope-documented",
            "redaction-reviewed",
            "recipient-approved",
            "artifact-delivered",
            "retention-owner-confirmed",
            "storage-decision-recorded",
            "audit-residual-risks-accepted",
            "mfa-track-decision-recorded",
            "rollout-state-documented",
            "support-handoff-completed",
            "next-roi-decision-recorded",
            "track-residual-risks-accepted",
            "evidence-storage-signature-required",
            "next-tenant-expansion-ready",
            "session-policy-gap-confirmed",
            "api-key-surface-active",
            "security-backlog-pause-preferred",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = security_roi_reselection_queries.get_review(
            tenant_id=options["tenant_id"],
            since=options["since"],
            until=options["until"],
            limit=options["limit"],
            output_format=options["output_format"],
            expected_actions_confirmed=options["expected_actions_confirmed"],
            export_scope_documented=options["export_scope_documented"],
            redaction_reviewed=options["redaction_reviewed"],
            recipient_approved=options["recipient_approved"],
            artifact_delivered=options["artifact_delivered"],
            retention_owner_confirmed=options["retention_owner_confirmed"],
            storage_decision_recorded=options["storage_decision_recorded"],
            audit_residual_risks_accepted=options["audit_residual_risks_accepted"],
            mfa_track_decision_recorded=options["mfa_track_decision_recorded"],
            rollout_state_documented=options["rollout_state_documented"],
            support_handoff_completed=options["support_handoff_completed"],
            next_roi_decision_recorded=options["next_roi_decision_recorded"],
            track_residual_risks_accepted=options["track_residual_risks_accepted"],
            evidence_storage_signature_required=options["evidence_storage_signature_required"],
            next_tenant_expansion_ready=options["next_tenant_expansion_ready"],
            session_policy_gap_confirmed=options["session_policy_gap_confirmed"],
            api_key_surface_active=options["api_key_surface_active"],
            security_backlog_pause_preferred=options["security_backlog_pause_preferred"],
        )
        recommendation = review["recommendation"]
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} tenant_id={review['tenant_id']} "
            f"recommendation={recommendation.recommended_track} score={recommendation.score}"
        )
        for candidate in review["candidates"]:
            self.stdout.write(
                f"candidate key={candidate.key} score={candidate.score} track={candidate.recommended_track}"
            )
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("Security ROI re-selection is blocked.")
