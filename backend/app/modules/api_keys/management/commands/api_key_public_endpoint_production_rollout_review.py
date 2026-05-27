from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_production_rollout_review_queries import (
    api_key_public_endpoint_production_rollout_review_queries,
)


class Command(BaseCommand):
    help = "Revisa rollout produtivo de observabilidade para endpoints públicos protegidos por API key."

    def add_arguments(self, parser):
        for name in (
            "observability-closure-ready",
            "production-token-configured",
            "prometheus-scrape-planned",
            "dashboard-import-planned",
            "alert-rules-load-planned",
            "smoke-metrics-planned",
            "rollback-plan-available",
            "evidence-capture-required",
            "owner-approval-required",
            "no-secret-exposure-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_endpoint_production_rollout_review_queries.get_review(
            observability_closure_ready=options["observability_closure_ready"],
            production_token_configured=options["production_token_configured"],
            prometheus_scrape_planned=options["prometheus_scrape_planned"],
            dashboard_import_planned=options["dashboard_import_planned"],
            alert_rules_load_planned=options["alert_rules_load_planned"],
            smoke_metrics_planned=options["smoke_metrics_planned"],
            rollback_plan_available=options["rollback_plan_available"],
            evidence_capture_required=options["evidence_capture_required"],
            owner_approval_required=options["owner_approval_required"],
            no_secret_exposure_required=options["no_secret_exposure_required"],
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
        for step in review["runbook_steps"]:
            self.stdout.write(f"runbook_step={step}")
        for step in review["rollback_steps"]:
            self.stdout.write(f"rollback_step={step}")
        for item in review["out_of_scope"]:
            self.stdout.write(f"out_of_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("API key public endpoint production rollout review is blocked.")
