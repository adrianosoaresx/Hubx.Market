from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_commercial_quotas_closure_queries import (
    api_key_commercial_quotas_closure_queries,
)


class Command(BaseCommand):
    help = "Revisa o fechamento da Battery B de quotas comerciais de API keys."

    def add_arguments(self, parser):
        for name in (
            "contract-ready",
            "model-ready",
            "enforcement-review-ready",
            "enforcement-ready",
            "admin-visibility-review-ready",
            "admin-visibility-ready",
            "metrics-ready",
            "audit-ready",
            "no-billing-charge-created",
            "no-plan-enforcement-created",
            "no-sensitive-material-recorded",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_commercial_quotas_closure_queries.get_review(
            **self._review_options(options=options)
        )
        self.stdout.write(f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["closure_scope"]:
            self.stdout.write(f"closure_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key commercial quotas closure is blocked.")

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
