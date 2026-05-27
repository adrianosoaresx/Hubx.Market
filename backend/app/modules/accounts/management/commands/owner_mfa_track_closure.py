from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.accounts.application.owner_mfa_track_closure_queries import owner_mfa_track_closure_queries


class Command(BaseCommand):
    help = "Fecha a trilha operacional MFA owner/admin após evidência auditável."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--since", default="")
        parser.add_argument("--until", default="")
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--format", dest="output_format", choices=["jsonl", "csv"], default="jsonl")
        parser.add_argument("--expected-actions-confirmed", action="store_true")
        parser.add_argument("--export-scope-documented", action="store_true")
        parser.add_argument("--redaction-reviewed", action="store_true")
        parser.add_argument("--recipient-approved", action="store_true")
        parser.add_argument("--artifact-delivered", action="store_true")
        parser.add_argument("--retention-owner-confirmed", action="store_true")
        parser.add_argument("--storage-decision-recorded", action="store_true")
        parser.add_argument("--audit-residual-risks-accepted", action="store_true")
        parser.add_argument("--mfa-track-decision-recorded", action="store_true")
        parser.add_argument("--rollout-state-documented", action="store_true")
        parser.add_argument("--support-handoff-completed", action="store_true")
        parser.add_argument("--next-roi-decision-recorded", action="store_true")
        parser.add_argument("--track-residual-risks-accepted", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        closure = owner_mfa_track_closure_queries.get_closure(
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
        )
        self.stdout.write(
            f"[{str(closure['status']).upper()}] result={closure['result']} tenant_id={closure['tenant_id']} "
            f"audit_result={closure['audit_closure']['result']} export_count={closure['audit_closure']['export_count']}"
        )
        for action in closure["audit_closure"]["mfa_actions"]:
            self.stdout.write(f"mfa_action={action}")
        for key, value in closure["closure_signals"].items():
            self.stdout.write(f"closure_signal key={key} value={value}")
        for decision in closure["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in closure["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for risk in closure["residual_risks"]:
            self.stdout.write(f"residual_risk={risk}")
        for track in closure["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not closure["ready"]:
            raise CommandError("Owner MFA track closure is blocked.")
