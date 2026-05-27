from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_post_onboarding_roi_reselection_queries import (
    api_key_post_onboarding_roi_reselection_queries,
)


class Command(BaseCommand):
    help = "Re-seleciona o próximo ROI sistêmico após closure de onboarding de parceiros."

    def add_arguments(self, parser):
        for name in (
            "model-ready",
            "runtime-auth-ready",
            "drf-adapter-ready",
            "public-endpoints-ready",
            "observability-ready",
            "expansion-closed",
            "no-billing-or-quotas-required",
            "no-secret-exposure-confirmed",
            "partner-docs-versioned",
            "endpoint-examples-documented",
            "activation-checklist-ready",
            "error-contract-documented",
            "safe-examples-confirmed",
            "no-new-endpoint-required",
            "no-quota-or-billing-required",
            "delivery-channel-documented",
            "support-handoff-documented",
            "smoke-evidence-template-ready",
            "change-control-documented",
            "owner-approved",
            "no-runtime-change-required",
            "no-commercial-terms-included",
            "no-sensitive-material-included",
            "publication-confirmed",
            "support-notified",
            "activation-status-recorded",
            "smoke-template-attached",
            "redaction-confirmed",
            "no-credential-shared",
            "no-runtime-activation-performed",
            "onboarding-scope-closed",
            "residual-risks-accepted",
            "next-roi-decision-recorded",
            "partner-activation-deferred",
            "commercial-quotas-deferred",
            "new-endpoint-expansion-deferred",
            "partner-activation-requested",
            "partner-api-key-ready",
            "commercial-quota-pressure-confirmed",
            "new-endpoint-demand-confirmed",
            "admin-support-load-confirmed",
            "api-key-track-pause-preferred",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--published-version", default="")
        parser.add_argument("--approved-channel", default="")
        parser.add_argument("--target-audience", default="")
        parser.add_argument("--tenant-reference", default="")
        parser.add_argument("--published-at", default="")
        parser.add_argument("--evidence-reference", default="")
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
        review = api_key_post_onboarding_roi_reselection_queries.get_review(
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
            raise CommandError("API key post-onboarding ROI re-selection is blocked.")
