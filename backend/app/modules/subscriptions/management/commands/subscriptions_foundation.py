from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.subscriptions.application.subscriptions_foundation_queries import subscriptions_foundation_queries


class Command(BaseCommand):
    help = "Revisa o fechamento da Battery E — Subscriptions & Tenant Billing Foundation."

    def add_arguments(self, parser):
        for name in (
            "domain-contract-ready",
            "plan-model-ready",
            "tenant-subscription-state-ready",
            "admin-read-surface-review-ready",
            "admin-read-surface-ready",
            "enforcement-boundary-ready",
            "audit-events-ready",
            "no-billing-provider-created",
            "no-store-payment-coupling",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = subscriptions_foundation_queries.get_review(
            **{key: value for key, value in options.items() if key not in {"fail_on_blockers", "verbosity", "settings", "pythonpath", "traceback", "no_color", "force_color", "skip_checks", "stdout", "stderr"}}
        )
        self.stdout.write(f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}")
        for decision in review["decisions"]:
            self.stdout.write(f"decision key={decision.key} status={decision.status} summary={decision.summary}")
        for blocker in review["blockers"]:
            self.stdout.write(f"blocker={blocker}")
        for item in review["closure_scope"]:
            self.stdout.write(f"closure_scope={item}")
        for track in review["next_tracks"]:
            self.stdout.write(f"next_track={track}")
        if options["fail_on_blockers"] and not review["ready"]:
            raise CommandError("Subscriptions foundation is blocked.")
