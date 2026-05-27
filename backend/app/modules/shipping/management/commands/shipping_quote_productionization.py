from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.shipping.application.shipping_quote_productionization_queries import (
    shipping_quote_productionization_queries,
)


class Command(BaseCommand):
    help = "Revisa o fechamento da Battery D — Shipping Quote Productionization."

    def add_arguments(self, parser):
        for name in (
            "provider-contract-ready",
            "adapter-skeleton-ready",
            "checkout-integration-review-ready",
            "checkout-execution-ready",
            "failure-ux-ready",
            "observability-ready",
            "tenant-scope-confirmed",
            "no-order-without-delivery-confirmed",
            "no-provider-secret-recorded",
            "rollback-plan-ready",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = shipping_quote_productionization_queries.get_review(
            **self._review_options(options=options)
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
            raise CommandError("Shipping quote productionization is blocked.")

    def _review_options(self, *, options: dict[str, object]) -> dict[str, object]:
        ignored = {
            "fail_on_blockers",
            "verbosity",
            "settings",
            "pythonpath",
            "traceback",
            "no_color",
            "force_color",
            "skip_checks",
            "stdout",
            "stderr",
        }
        return {key: value for key, value in options.items() if key not in ignored}
