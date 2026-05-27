from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_dashboard_review_queries import (
    api_key_public_endpoint_dashboard_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato de dashboard para endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "metrics-endpoint-available",
            "observability-token-required",
            "requests-panel-required",
            "auth-failure-panel-required",
            "rate-limit-panel-required",
            "endpoint-enabled-panel-required",
            "tenant-endpoint-filters-required",
            "low-cardinality-required",
            "no-sensitive-labels-required",
            "alert-rules-plan-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_dashboard_review_queries.get_review(
            metrics_endpoint_available=options["metrics_endpoint_available"],
            observability_token_required=options["observability_token_required"],
            requests_panel_required=options["requests_panel_required"],
            auth_failure_panel_required=options["auth_failure_panel_required"],
            rate_limit_panel_required=options["rate_limit_panel_required"],
            endpoint_enabled_panel_required=options["endpoint_enabled_panel_required"],
            tenant_endpoint_filters_required=options["tenant_endpoint_filters_required"],
            low_cardinality_required=options["low_cardinality_required"],
            no_sensitive_labels_required=options["no_sensitive_labels_required"],
            alert_rules_plan_required=options["alert_rules_plan_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for key, value in review["dashboard"].items():
            self.stdout.write(f"dashboard {key}={value}")
        for panel in review["panels"]:
            self.stdout.write(f"panel={panel}")
        for key, value in review["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for requirement in review["requirements"]:
            self.stdout.write(f"requirement key={requirement.key} summary={requirement.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["out_of_scope"]:
            self.stdout.write(f"out_of_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key public endpoint dashboard review is blocked.")
