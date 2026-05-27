from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_endpoint_production_activation_evidence_queries import (
    api_key_public_endpoint_production_activation_evidence_queries,
)


class Command(BaseCommand):
    help = "Captura evidência sanitizada da ativação produtiva de observabilidade de endpoints públicos por API key."

    def add_arguments(self, parser):
        parser.add_argument("--environment", default="")
        parser.add_argument("--evidence-reference", default="")
        for name in (
            "rollout-review-ready",
            "token-redacted",
            "metrics-endpoint-reachable",
            "metrics-payload-valid",
            "prometheus-scrape-active",
            "dashboard-imported",
            "alert-rules-loaded",
            "endpoint-enabled-metric-present",
            "request-metric-present",
            "auth-failure-metric-present",
            "rate-limit-metric-present",
            "rollback-rehearsed",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        evidence = api_key_public_endpoint_production_activation_evidence_queries.get_evidence(
            environment=options["environment"],
            evidence_reference=options["evidence_reference"],
            rollout_review_ready=options["rollout_review_ready"],
            token_redacted=options["token_redacted"],
            metrics_endpoint_reachable=options["metrics_endpoint_reachable"],
            metrics_payload_valid=options["metrics_payload_valid"],
            prometheus_scrape_active=options["prometheus_scrape_active"],
            dashboard_imported=options["dashboard_imported"],
            alert_rules_loaded=options["alert_rules_loaded"],
            endpoint_enabled_metric_present=options["endpoint_enabled_metric_present"],
            request_metric_present=options["request_metric_present"],
            auth_failure_metric_present=options["auth_failure_metric_present"],
            rate_limit_metric_present=options["rate_limit_metric_present"],
            rollback_rehearsed=options["rollback_rehearsed"],
        )
        self.stdout.write(
            f"[{str(evidence['status']).upper()}] result={evidence['result']} "
            f"module={evidence['module']} environment={evidence['environment']} "
            f"evidence_reference={evidence['evidence_reference']}"
        )
        for key, value in evidence["signals"].items():
            self.stdout.write(f"signal key={key} value={value}")
        for decision in evidence["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for requirement in evidence["requirements"]:
            self.stdout.write(f"requirement key={requirement.key} summary={requirement.summary}")
        for blocker in evidence["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in evidence["captured_evidence"]:
            self.stdout.write(f"captured_evidence={item}")
        for item in evidence["out_of_scope"]:
            self.stdout.write(f"out_of_scope={item}")
        for track in evidence["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not evidence["ready"]:
            raise CommandError("API key public endpoint production activation evidence is blocked.")
