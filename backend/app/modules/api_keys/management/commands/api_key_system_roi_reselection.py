from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_system_roi_reselection_queries import (
    api_key_system_roi_reselection_queries,
)


class Command(BaseCommand):
    help = "Re-seleciona o próximo ROI sistêmico após closure de governança de API keys."

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
            "partner-docs-missing",
            "partner-onboarding-requested",
            "commercial-quota-pressure-confirmed",
            "new-endpoint-demand-confirmed",
            "admin-ux-gap-confirmed",
            "production-incident-pressure-confirmed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_system_roi_reselection_queries.get_review(
            model_ready=options["model_ready"],
            runtime_auth_ready=options["runtime_auth_ready"],
            drf_adapter_ready=options["drf_adapter_ready"],
            public_endpoints_ready=options["public_endpoints_ready"],
            observability_ready=options["observability_ready"],
            expansion_closed=options["expansion_closed"],
            no_billing_or_quotas_required=options["no_billing_or_quotas_required"],
            no_secret_exposure_confirmed=options["no_secret_exposure_confirmed"],
            partner_docs_missing=options["partner_docs_missing"],
            partner_onboarding_requested=options["partner_onboarding_requested"],
            commercial_quota_pressure_confirmed=options["commercial_quota_pressure_confirmed"],
            new_endpoint_demand_confirmed=options["new_endpoint_demand_confirmed"],
            admin_ux_gap_confirmed=options["admin_ux_gap_confirmed"],
            production_incident_pressure_confirmed=options["production_incident_pressure_confirmed"],
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
            raise CommandError("API key system ROI re-selection is blocked.")
