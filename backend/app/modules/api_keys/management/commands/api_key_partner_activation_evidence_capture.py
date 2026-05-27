from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_partner_activation_evidence_capture_queries import (
    api_key_partner_activation_evidence_capture_queries,
)


class Command(BaseCommand):
    help = "Revisa a captura de evidência sanitizada da ativação de parceiro por API key."

    def add_arguments(self, parser):
        for name in (
            "smoke-execution-ready",
            "list-result-attached",
            "detail-result-attached",
            "negative-auth-result-attached",
            "metrics-snapshot-attached",
            "audit-log-reference-attached",
            "partner-handoff-reference-attached",
            "support-handoff-reference-attached",
            "redaction-confirmed",
            "no-secret-material-recorded",
            "rollback-note-attached",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--evidence-reference", default="")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_partner_activation_evidence_capture_queries.get_review(
            **self._review_options(options=options)
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']} "
            f"evidence={review['evidence_reference']}"
        )
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["evidence_items"]:
            self.stdout.write(f"evidence_item={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key partner activation evidence capture is blocked.")

    def _review_options(self, *, options: dict[str, object]) -> dict[str, object]:
        ignored_options = {
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
        return {key: value for key, value in options.items() if key not in ignored_options}
