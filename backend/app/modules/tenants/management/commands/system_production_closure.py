from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.tenants.application.system_production_closure_queries import (
    system_production_go_nogo_queries,
    system_production_observability_closure_queries,
    system_production_readiness_matrix_queries,
    system_production_rollback_drill_queries,
    system_production_runbook_gap_queries,
    system_production_smoke_checklist_queries,
)


class Command(BaseCommand):
    help = "Executa reviews da Battery J — System Production Closure."

    def add_arguments(self, parser):
        parser.add_argument(
            "--review",
            choices=("matrix", "runbooks", "smoke", "observability", "rollback", "go-nogo"),
            required=True,
        )
        for name in (
            "matrix-reviewed",
            "watch-risks-accepted",
            "payments-runbook-ready",
            "notifications-runbook-ready",
            "shipping-runbook-ready",
            "catalog-runbook-ready",
            "checkout-runbook-ready",
            "incident-owner-confirmed",
            "tenant-resolution-smoke",
            "storefront-catalog-smoke",
            "cart-checkout-smoke",
            "payment-provider-smoke",
            "notification-smoke",
            "api-key-smoke",
            "no-sensitive-output",
            "prometheus-scrape-confirmed",
            "grafana-dashboards-confirmed",
            "alertmanager-routes-confirmed",
            "audit-export-ready",
            "oncall-triage-confirmed",
            "feature-flags-rollback-confirmed",
            "provider-rollback-confirmed",
            "ops-gate-rollback-confirmed",
            "communication-plan-confirmed",
            "data-restore-owner-confirmed",
            "readiness-matrix-ready",
            "runbooks-ready",
            "smoke-checklist-ready",
            "observability-ready",
            "rollback-drill-ready",
            "residual-risks-accepted",
            "decision-owner-confirmed",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        payload = self._review(options=options)
        self.stdout.write(f"[{str(payload['status']).upper()}] result={payload['result']} module={payload['module']}")
        for decision in payload.get("decisions", ()):
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for row in payload.get("matrix", ()):
            self.stdout.write(f"matrix module={row['module']} status={row['status']} risk={row['risk']}")
        for item in payload.get("critical_runbooks", ()):
            self.stdout.write(f"critical_runbook={item}")
        for item in payload.get("smoke_scope", ()):
            self.stdout.write(f"smoke_scope={item}")
        for item in payload.get("rollback_scope", ()):
            self.stdout.write(f"rollback_scope={item}")
        for item in payload.get("closure_scope", ()):
            self.stdout.write(f"closure_scope={item}")
        for blocker in payload.get("blockers", ()):
            self.stdout.write(f"blocker={blocker}")
        for track in payload.get("next_tracks", ()):
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not payload["ready"]:
            raise CommandError("System production closure is blocked.")

    def _review(self, *, options: dict[str, object]) -> dict[str, object]:
        review = options["review"]
        if review == "matrix":
            return system_production_readiness_matrix_queries.get_review(
                matrix_reviewed=bool(options["matrix_reviewed"]),
                watch_risks_accepted=bool(options["watch_risks_accepted"]),
            )
        if review == "runbooks":
            return system_production_runbook_gap_queries.get_review(
                payments_runbook_ready=bool(options["payments_runbook_ready"]),
                notifications_runbook_ready=bool(options["notifications_runbook_ready"]),
                shipping_runbook_ready=bool(options["shipping_runbook_ready"]),
                catalog_runbook_ready=bool(options["catalog_runbook_ready"]),
                checkout_runbook_ready=bool(options["checkout_runbook_ready"]),
                incident_owner_confirmed=bool(options["incident_owner_confirmed"]),
            )
        if review == "smoke":
            return system_production_smoke_checklist_queries.get_review(
                tenant_resolution_smoke=bool(options["tenant_resolution_smoke"]),
                storefront_catalog_smoke=bool(options["storefront_catalog_smoke"]),
                cart_checkout_smoke=bool(options["cart_checkout_smoke"]),
                payment_provider_smoke=bool(options["payment_provider_smoke"]),
                notification_smoke=bool(options["notification_smoke"]),
                api_key_smoke=bool(options["api_key_smoke"]),
                no_sensitive_output=bool(options["no_sensitive_output"]),
            )
        if review == "observability":
            return system_production_observability_closure_queries.get_review(
                prometheus_scrape_confirmed=bool(options["prometheus_scrape_confirmed"]),
                grafana_dashboards_confirmed=bool(options["grafana_dashboards_confirmed"]),
                alertmanager_routes_confirmed=bool(options["alertmanager_routes_confirmed"]),
                audit_export_ready=bool(options["audit_export_ready"]),
                oncall_triage_confirmed=bool(options["oncall_triage_confirmed"]),
            )
        if review == "rollback":
            return system_production_rollback_drill_queries.get_review(
                feature_flags_rollback_confirmed=bool(options["feature_flags_rollback_confirmed"]),
                provider_rollback_confirmed=bool(options["provider_rollback_confirmed"]),
                ops_gate_rollback_confirmed=bool(options["ops_gate_rollback_confirmed"]),
                communication_plan_confirmed=bool(options["communication_plan_confirmed"]),
                data_restore_owner_confirmed=bool(options["data_restore_owner_confirmed"]),
            )
        return system_production_go_nogo_queries.get_review(
            readiness_matrix_ready=bool(options["readiness_matrix_ready"]),
            runbooks_ready=bool(options["runbooks_ready"]),
            smoke_checklist_ready=bool(options["smoke_checklist_ready"]),
            observability_ready=bool(options["observability_ready"]),
            rollback_drill_ready=bool(options["rollback_drill_ready"]),
            residual_risks_accepted=bool(options["residual_risks_accepted"]),
            decision_owner_confirmed=bool(options["decision_owner_confirmed"]),
            docs_updated=bool(options["docs_updated"]),
            decision_recorded=bool(options["decision_recorded"]),
        )
