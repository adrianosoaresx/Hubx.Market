from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.notifications.application.notification_production_delivery_commands import notification_production_delivery_commands
from app.modules.notifications.application.notification_production_delivery_queries import (
    notification_delivery_evidence_queries,
    notification_failure_handling_queries,
    notification_production_closure_queries,
    notification_production_monitoring_queries,
    notification_provider_production_gate_queries,
)


class Command(BaseCommand):
    help = "Executa reviews e smoke da Battery G — Notifications Production Delivery."

    def add_arguments(self, parser):
        parser.add_argument(
            "--review",
            choices=("provider-gate", "smoke", "evidence", "failure-handling", "monitoring", "closure"),
            required=True,
        )
        parser.add_argument("--tenant-id", dest="tenant_id", default="")
        parser.add_argument("--recipient-email", dest="recipient_email", default="")
        parser.add_argument("--smoke-key", dest="smoke_key", default="production-smoke")
        for name in (
            "provider-credentials-confirmed",
            "sender-domain-confirmed",
            "rollback-confirmed",
            "smoke-sent",
            "provider-message-id-recorded",
            "no-customer-pii-exported",
            "bounce-handling-confirmed",
            "metrics-confirmed",
            "dashboard-confirmed",
            "alert-owner-confirmed",
            "provider-gate-ready",
            "smoke-execution-ready",
            "evidence-capture-ready",
            "failure-handling-ready",
            "monitoring-ready",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = options["review"]
        payload = self._run_review(review=review, options=options)
        self.stdout.write(f"[{str(payload['status']).upper()}] result={payload['result']} module={payload['module']}")
        for decision in payload.get("decisions", ()):
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        if "provider_blockers" in payload:
            blockers = ",".join(payload["provider_blockers"]) or "none"
            self.stdout.write(f"provider_blockers={blockers}")
        if "snapshot" in payload:
            snapshot = payload["snapshot"]
            self.stdout.write(
                f"snapshot tenant={snapshot.tenant_id} sent={snapshot.sent} failed={snapshot.failed} planned={snapshot.planned} requested={snapshot.requested}"
            )
        for key, value in payload.get("failure_classifications", {}).items():
            self.stdout.write(f"failure_classification key={key} count={value}")
        for item in payload.get("evidence_scope", ()):
            self.stdout.write(f"evidence_scope={item}")
        for item in payload.get("closure_scope", ()):
            self.stdout.write(f"closure_scope={item}")
        for key, value in payload.get("evidence", {}).items():
            self.stdout.write(f"evidence {key}={value}")
        for blocker in payload.get("blockers", ()):
            self.stdout.write(f"blocker={blocker}")
        for track in payload.get("next_tracks", ()):
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not payload["ready"]:
            raise CommandError("Notifications production delivery is blocked.")

    def _run_review(self, *, review: str, options: dict[str, object]) -> dict[str, object]:
        if review == "provider-gate":
            return notification_provider_production_gate_queries.get_review(
                provider_credentials_confirmed=bool(options["provider_credentials_confirmed"]),
                sender_domain_confirmed=bool(options["sender_domain_confirmed"]),
                rollback_confirmed=bool(options["rollback_confirmed"]),
            )
        if review == "smoke":
            result = notification_production_delivery_commands.execute_transactional_smoke(
                tenant_id=options["tenant_id"],
                recipient_email=options["recipient_email"],
                smoke_key=options["smoke_key"],
            )
            ready = result.result == "notification-smoke-sent"
            return {
                "result": result.result,
                "ready": ready,
                "status": "ready" if ready else "blocked",
                "module": "notifications",
                "evidence": result.evidence,
                "blockers": () if ready else (f"notification-smoke:{result.result}",),
            }
        if review == "evidence":
            return notification_delivery_evidence_queries.get_review(
                tenant_id=options["tenant_id"],
                smoke_sent=bool(options["smoke_sent"]),
                provider_message_id_recorded=bool(options["provider_message_id_recorded"]),
                no_customer_pii_exported=bool(options["no_customer_pii_exported"]),
            )
        if review == "failure-handling":
            return notification_failure_handling_queries.get_review(
                tenant_id=options["tenant_id"],
                bounce_handling_confirmed=bool(options["bounce_handling_confirmed"]),
            )
        if review == "monitoring":
            return notification_production_monitoring_queries.get_review(
                tenant_id=options["tenant_id"],
                metrics_confirmed=bool(options["metrics_confirmed"]),
                dashboard_confirmed=bool(options["dashboard_confirmed"]),
                alert_owner_confirmed=bool(options["alert_owner_confirmed"]),
            )
        return notification_production_closure_queries.get_review(
            tenant_id=options["tenant_id"],
            provider_gate_ready=bool(options["provider_gate_ready"]),
            smoke_execution_ready=bool(options["smoke_execution_ready"]),
            evidence_capture_ready=bool(options["evidence_capture_ready"]),
            failure_handling_ready=bool(options["failure_handling_ready"]),
            monitoring_ready=bool(options["monitoring_ready"]),
            docs_updated=bool(options["docs_updated"]),
            decision_recorded=bool(options["decision_recorded"]),
        )
