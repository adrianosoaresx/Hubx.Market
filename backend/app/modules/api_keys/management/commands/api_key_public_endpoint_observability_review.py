from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_observability_review_queries import (
    api_key_public_endpoint_observability_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato de observabilidade para endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "public-endpoint-active",
            "auth-events-available",
            "rate-limit-events-available",
            "prometheus-metrics-required",
            "endpoint-labels-required",
            "tenant-labels-required",
            "key-prefix-labels-allowed",
            "no-secret-material-required",
            "alert-rules-required",
            "dashboard-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_observability_review_queries.get_review(
            public_endpoint_active=options["public_endpoint_active"],
            auth_events_available=options["auth_events_available"],
            rate_limit_events_available=options["rate_limit_events_available"],
            prometheus_metrics_required=options["prometheus_metrics_required"],
            endpoint_labels_required=options["endpoint_labels_required"],
            tenant_labels_required=options["tenant_labels_required"],
            key_prefix_labels_allowed=options["key_prefix_labels_allowed"],
            no_secret_material_required=options["no_secret_material_required"],
            alert_rules_required=options["alert_rules_required"],
            dashboard_required=options["dashboard_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for metric in review["recommended_metrics"]:
            self.stdout.write(f"recommended_metric={metric}")
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
            raise CommandError("API key public endpoint observability review is blocked.")
