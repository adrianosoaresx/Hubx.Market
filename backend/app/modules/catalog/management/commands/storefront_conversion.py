from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.catalog.application.storefront_conversion_closure_queries import storefront_conversion_closure_queries
from app.modules.catalog.application.storefront_conversion_insights import storefront_conversion_insights


class Command(BaseCommand):
    help = "Executa reviews da Battery I — Storefront Data-Driven Conversion."

    def add_arguments(self, parser):
        parser.add_argument("--review", choices=("baseline", "pdp-funnel", "search-dropoff", "closure"), required=True)
        parser.add_argument("--tenant-id", dest="tenant_id", default="")
        for name in (
            "baseline-ready",
            "pdp-funnel-ready",
            "search-facet-dropoff-ready",
            "experiment-contract-ready",
            "experiment-execution-ready",
            "no-full-redesign",
            "docs-updated",
            "decision-recorded",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = str(options["review"])
        tenant_id = options["tenant_id"]
        if review == "baseline":
            payload = storefront_conversion_insights.baseline(tenant_id=tenant_id)
            self.stdout.write(
                "[READY] result=storefront-conversion-baseline-ready module=catalog "
                f"events={payload['total_events']} listings={payload['listing_views']} pdp={payload['pdp_views']} "
                f"cta={payload['cta_intents']} successful_cta={payload['successful_ctas']}"
            )
            return
        if review == "pdp-funnel":
            payload = storefront_conversion_insights.pdp_funnel(tenant_id=tenant_id)
            self.stdout.write(f"[READY] result=storefront-pdp-funnel-ready module=catalog products={len(payload['products'])}")
            for slug, stats in payload["products"].items():
                self.stdout.write(
                    f"product slug={slug} pdp_views={stats['pdp_views']} cta_intents={stats['cta_intents']} successful_ctas={stats['successful_ctas']} unavailable_ctas={stats['unavailable_ctas']}"
                )
            return
        if review == "search-dropoff":
            payload = storefront_conversion_insights.search_facet_dropoff(tenant_id=tenant_id)
            self.stdout.write(
                f"[READY] result=storefront-search-dropoff-ready module=catalog zero_result_count={payload['zero_result_count']}"
            )
            return

        payload = storefront_conversion_closure_queries.get_review(
            baseline_ready=bool(options["baseline_ready"]),
            pdp_funnel_ready=bool(options["pdp_funnel_ready"]),
            search_facet_dropoff_ready=bool(options["search_facet_dropoff_ready"]),
            experiment_contract_ready=bool(options["experiment_contract_ready"]),
            experiment_execution_ready=bool(options["experiment_execution_ready"]),
            no_full_redesign=bool(options["no_full_redesign"]),
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
            raise CommandError("Storefront conversion is blocked.")
