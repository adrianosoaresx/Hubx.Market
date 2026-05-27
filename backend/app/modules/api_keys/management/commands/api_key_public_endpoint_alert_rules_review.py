from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_alert_rules_review_queries import (
    api_key_public_endpoint_alert_rules_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato de alert rules para endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "metrics-endpoint-available",
            "dashboard-available",
            "auth-failure-alert-required",
            "rate-limit-alert-required",
            "endpoint-disabled-alert-required",
            "tenant-endpoint-labels-required",
            "low-cardinality-required",
            "runbook-annotations-required",
            "no-sensitive-labels-required",
            "warning-first-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_alert_rules_review_queries.get_review(
            metrics_endpoint_available=options["metrics_endpoint_available"],
            dashboard_available=options["dashboard_available"],
            auth_failure_alert_required=options["auth_failure_alert_required"],
            rate_limit_alert_required=options["rate_limit_alert_required"],
            endpoint_disabled_alert_required=options["endpoint_disabled_alert_required"],
            tenant_endpoint_labels_required=options["tenant_endpoint_labels_required"],
            low_cardinality_required=options["low_cardinality_required"],
            runbook_annotations_required=options["runbook_annotations_required"],
            no_sensitive_labels_required=options["no_sensitive_labels_required"],
            warning_first_required=options["warning_first_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for rule in review["rules"]:
            self.stdout.write(f"rule={rule}")
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
            raise CommandError("API key public endpoint alert rules review is blocked.")
