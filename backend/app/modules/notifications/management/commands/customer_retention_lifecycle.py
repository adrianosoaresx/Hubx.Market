from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.newsletter.application.newsletter_segment_queries import newsletter_segment_queries
from app.modules.notifications.application.customer_retention_lifecycle_commands import customer_retention_lifecycle_commands
from app.modules.notifications.application.customer_retention_lifecycle_queries import customer_retention_lifecycle_closure_queries


class Command(BaseCommand):
    help = "Executa planejamento e closure da Battery H — Customer Retention Lifecycle."

    def add_arguments(self, parser):
        parser.add_argument("--review", choices=("segment", "plan-post-purchase", "closure"), required=True)
        parser.add_argument("--tenant-id", dest="tenant_id", default="")
        parser.add_argument("--order-id", dest="order_id", default="")
        parser.add_argument("--limit", type=int, default=50)
        for name in (
            "lifecycle-contract-ready",
            "newsletter-segment-ready",
            "post-purchase-intent-ready",
            "notification-integration-ready",
            "opt-out-boundary-ready",
            "no-complex-automation",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = str(options["review"])
        if review == "segment":
            subscribers = newsletter_segment_queries.list_subscribed_segment(
                tenant_id=options["tenant_id"],
                limit=options["limit"],
            )
            self.stdout.write(f"[READY] result=newsletter-segment-ready module=newsletter count={len(subscribers)}")
            return
        if review == "plan-post-purchase":
            result = customer_retention_lifecycle_commands.plan_post_purchase_follow_up(
                tenant_id=options["tenant_id"],
                order_id=options["order_id"],
            )
            status = "ready" if result["result"] in {"retention-lifecycle-planned", "retention-lifecycle-already-planned"} else "blocked"
            self.stdout.write(f"[{status.upper()}] result={result['result']} module=notifications")
            if options["fail_on_blockers"] and status != "ready":
                raise CommandError("Customer retention post-purchase planning is blocked.")
            return

        payload = customer_retention_lifecycle_closure_queries.get_review(
            lifecycle_contract_ready=bool(options["lifecycle_contract_ready"]),
            newsletter_segment_ready=bool(options["newsletter_segment_ready"]),
            post_purchase_intent_ready=bool(options["post_purchase_intent_ready"]),
            notification_integration_ready=bool(options["notification_integration_ready"]),
            opt_out_boundary_ready=bool(options["opt_out_boundary_ready"]),
            no_complex_automation=bool(options["no_complex_automation"]),
            docs_updated=bool(options["docs_updated"]),
            decision_recorded=bool(options["decision_recorded"]),
        )
        self.stdout.write(f"[{str(payload['status']).upper()}] result={payload['result']} module={payload['module']}")
        for decision in payload["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for item in payload["closure_scope"]:
            self.stdout.write(f"closure_scope={item}")
        for blocker in payload["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for track in payload["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not payload["ready"]:
            raise CommandError("Customer retention lifecycle is blocked.")
