from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.system_roi_post_quota_reselection_queries import (
    system_roi_post_quota_reselection_queries,
)


class Command(BaseCommand):
    help = "Re-seleciona o próximo ROI sistêmico após closure de quotas comerciais de API keys."

    def add_arguments(self, parser):
        for name in (
            "quota-contract-ready",
            "quota-model-ready",
            "quota-enforcement-review-ready",
            "quota-enforcement-ready",
            "quota-admin-visibility-review-ready",
            "quota-admin-visibility-ready",
            "quota-metrics-ready",
            "quota-audit-ready",
            "quota-no-billing-charge-created",
            "quota-no-plan-enforcement-created",
            "quota-no-sensitive-material-recorded",
            "quota-docs-updated",
            "quota-decision-recorded",
            "payments-provider-production-blocker",
            "payments-refund-reconciliation-blocker",
            "shipping-quote-conversion-blocker",
            "shipping-carrier-contract-ready",
            "cross-module-runbook-gap-confirmed",
            "production-closure-requested",
            "storefront-conversion-pressure-confirmed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = system_roi_post_quota_reselection_queries.get_review(
            **self._review_options(options=options)
        )
        recommendation = review["recommendation"]
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']} "
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
        for item in review["out_of_scope"]:
            self.stdout.write(f"out_of_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("System ROI post-quota re-selection is blocked.")

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
