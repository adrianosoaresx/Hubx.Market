from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.system_roi_reselection_queries import system_roi_reselection_queries


class Command(BaseCommand):
    help = "Re-seleciona o próximo ROI sistêmico após Platform Store Management closure."

    def add_arguments(self, parser):
        for name in (
            "tenant-ops-closed-confirmed",
            "owner-bootstrap-closed-confirmed",
            "custom-domain-runtime-closed-confirmed",
            "production-evidence-confirmed",
            "docs-tests-confirmed",
            "remaining-risks-accepted",
            "production-validation-preferred",
            "storefront-regression-pressure-confirmed",
            "payments-provider-blocker-confirmed",
            "shipping-provider-blocker-confirmed",
            "platform-ops-support-pressure-confirmed",
            "cross-module-runbook-pressure-confirmed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
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
        review = system_roi_reselection_queries.get_review(
            **{key: value for key, value in options.items() if key not in ignored_options}
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
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("System ROI re-selection is blocked.")
