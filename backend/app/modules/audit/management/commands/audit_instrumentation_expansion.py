from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.audit.application.audit_instrumentation_expansion_queries import audit_instrumentation_expansion_queries


class Command(BaseCommand):
    help = "Revisa o fechamento da Battery F — Audit Instrumentation Expansion."

    def add_arguments(self, parser):
        for name in (
            "critical-inventory-ready",
            "payment-admin-actions-ready",
            "api-key-actions-ready",
            "catalog-admin-actions-ready",
            "evidence-review-ready",
            "metadata-redaction-ready",
            "tenant-scope-confirmed",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        ignored = {
            "fail_on_blockers",
            "verbosity",
            "settings",
            "pythonpath",
            "traceback",
            "no_color",
            "force_color",
            "skip_checks",
            "stdout",
            "stderr",
        }
        review = audit_instrumentation_expansion_queries.get_review(
            **{key: value for key, value in options.items() if key not in ignored}
        )
        self.stdout.write(f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for action in review["instrumented_actions"]:
            self.stdout.write(f"instrumented_action={action}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("Audit instrumentation expansion is blocked.")
