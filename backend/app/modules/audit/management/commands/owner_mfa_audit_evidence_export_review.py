from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.audit.application.owner_mfa_audit_evidence_export_review_queries import (
    owner_mfa_audit_evidence_export_review_queries,
)


class Command(BaseCommand):
    help = "Revisa readiness de export de evidência AuditLog para MFA owner/admin."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-id", dest="tenant_id", required=True)
        parser.add_argument("--since", default="")
        parser.add_argument("--until", default="")
        parser.add_argument("--expected-actions-confirmed", action="store_true")
        parser.add_argument("--export-scope-documented", action="store_true")
        parser.add_argument("--redaction-reviewed", action="store_true")
        parser.add_argument("--recipient-approved", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = owner_mfa_audit_evidence_export_review_queries.get_review(
            tenant_id=options["tenant_id"],
            since=options["since"],
            until=options["until"],
            expected_actions_confirmed=options["expected_actions_confirmed"],
            export_scope_documented=options["export_scope_documented"],
            redaction_reviewed=options["redaction_reviewed"],
            recipient_approved=options["recipient_approved"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} tenant_id={review['tenant_id']} "
            f"module={review['module']} sample_count={review['sample_count']} mfa_event_count={review['mfa_event_count']}"
        )
        for action in review["mfa_actions"]:
            self.stdout.write(f"mfa_action={action}")
        for key, value in review["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for contract in review["export_contract"]:
            self.stdout.write(f"export_contract={contract}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("Owner MFA audit evidence export review is not ready.")
