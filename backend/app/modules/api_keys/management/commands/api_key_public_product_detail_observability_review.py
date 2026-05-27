from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_product_detail_observability_review_queries import (
    api_key_public_product_detail_observability_review_queries,
)


class Command(BaseCommand):
    help = "Revisa observabilidade do endpoint público de detalhe de produto protegido por API key."

    def add_arguments(self, parser):
        for name in (
            "detail-endpoint-executed",
            "metrics-endpoint-label-present",
            "enabled-gauge-present",
            "dashboard-endpoint-filter-covers-detail",
            "alert-rules-endpoint-label-covers-detail",
            "rate-limit-metrics-reused",
            "auth-failure-metrics-reused",
            "no-new-dashboard-required",
            "no-new-alert-rules-required",
            "no-sensitive-labels-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_product_detail_observability_review_queries.get_review(
            detail_endpoint_executed=options["detail_endpoint_executed"],
            metrics_endpoint_label_present=options["metrics_endpoint_label_present"],
            enabled_gauge_present=options["enabled_gauge_present"],
            dashboard_endpoint_filter_covers_detail=options["dashboard_endpoint_filter_covers_detail"],
            alert_rules_endpoint_label_covers_detail=options["alert_rules_endpoint_label_covers_detail"],
            rate_limit_metrics_reused=options["rate_limit_metrics_reused"],
            auth_failure_metrics_reused=options["auth_failure_metrics_reused"],
            no_new_dashboard_required=options["no_new_dashboard_required"],
            no_new_alert_rules_required=options["no_new_alert_rules_required"],
            no_sensitive_labels_required=options["no_sensitive_labels_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']} endpoint={review['endpoint']}"
        )
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
            raise CommandError("API key public product detail observability review is blocked.")
