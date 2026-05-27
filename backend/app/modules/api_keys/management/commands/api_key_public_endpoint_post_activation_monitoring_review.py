from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_post_activation_monitoring_review_queries import (
    api_key_public_endpoint_post_activation_monitoring_review_queries,
)


class Command(BaseCommand):
    help = "Revisa monitoramento pós-ativação de endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "activation-evidence-ready",
            "monitoring-window-observed",
            "dashboard-reviewed",
            "auth-failure-rate-acceptable",
            "rate-limit-rate-acceptable",
            "endpoint-enabled-stable",
            "alert-noise-acceptable",
            "threshold-tuning-needed-logged",
            "rollback-not-required",
            "expansion-decision-deferred",
            "no-sensitive-data-observed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_post_activation_monitoring_review_queries.get_review(
            activation_evidence_ready=options["activation_evidence_ready"],
            monitoring_window_observed=options["monitoring_window_observed"],
            dashboard_reviewed=options["dashboard_reviewed"],
            auth_failure_rate_acceptable=options["auth_failure_rate_acceptable"],
            rate_limit_rate_acceptable=options["rate_limit_rate_acceptable"],
            endpoint_enabled_stable=options["endpoint_enabled_stable"],
            alert_noise_acceptable=options["alert_noise_acceptable"],
            threshold_tuning_needed_logged=options["threshold_tuning_needed_logged"],
            rollback_not_required=options["rollback_not_required"],
            expansion_decision_deferred=options["expansion_decision_deferred"],
            no_sensitive_data_observed=options["no_sensitive_data_observed"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for key, value in review["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for requirement in review["requirements"]:
            self.stdout.write(f"requirement key={requirement.key} summary={requirement.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for check in review["monitoring_checks"]:
            self.stdout.write(f"monitoring_check={check}")
        for item in review["out_of_scope"]:
            self.stdout.write(f"out_of_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key public endpoint post-activation monitoring review is blocked.")
