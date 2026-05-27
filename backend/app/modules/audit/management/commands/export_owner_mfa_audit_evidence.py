from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.audit.application.owner_mfa_audit_evidence_export_execution_queries import (
    owner_mfa_audit_evidence_export_execution_queries,
)


class Command(BaseCommand):
    help = "Exporta evidência MFA owner/admin tenant-scoped a partir de AuditLog."

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
        parser.add_argument("--fail-on-empty", action="store_true")

    def handle(self, *args, **options):
        result = owner_mfa_audit_evidence_export_execution_queries.export(
            tenant_id=options["tenant_id"],
            since=options["since"],
            until=options["until"],
            limit=options["limit"],
            output_format=options["output_format"],
            expected_actions_confirmed=options["expected_actions_confirmed"],
            export_scope_documented=options["export_scope_documented"],
            redaction_reviewed=options["redaction_reviewed"],
            recipient_approved=options["recipient_approved"],
        )
        if result["result"] != "owner-mfa-audit-evidence-exported":
            raise CommandError(result.get("errors") or result.get("blockers") or result["result"])
        if options["fail_on_empty"] and result["count"] == 0:
            raise CommandError("Owner MFA audit evidence export is empty.")
        content = str(result["content"] or "")
        if content:
            self.stdout.write(content)
