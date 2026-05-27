from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from app.modules.api_keys.application.api_key_public_product_detail_endpoint_contract_review_queries import (
    api_key_public_product_detail_endpoint_contract_review_queries,
)


class Command(BaseCommand):
    help = "Revisa contrato do endpoint público de detalhe de produto protegido por API key."

    def add_arguments(self, parser):
        for name in (
            "expansion-review-ready",
            "catalog-owner-confirmed",
            "slug-lookup-required",
            "tenant-scope-required",
            "active-product-only-required",
            "read-catalog-scope-required",
            "safe-payload-required",
            "public-variant-summary-required",
            "rate-limit-endpoint-required",
            "metrics-endpoint-label-required",
            "rollout-flag-required",
            "no-pii-or-stock-raw-required",
        ):
            parser.add_argument(f"--{name}", action="store_true")
        parser.add_argument("--fail-on-blockers", action="store_true")

    def handle(self, *args, **options):
        review = api_key_public_product_detail_endpoint_contract_review_queries.get_review(
            expansion_review_ready=options["expansion_review_ready"],
            catalog_owner_confirmed=options["catalog_owner_confirmed"],
            slug_lookup_required=options["slug_lookup_required"],
            tenant_scope_required=options["tenant_scope_required"],
            active_product_only_required=options["active_product_only_required"],
            read_catalog_scope_required=options["read_catalog_scope_required"],
            safe_payload_required=options["safe_payload_required"],
            public_variant_summary_required=options["public_variant_summary_required"],
            rate_limit_endpoint_required=options["rate_limit_endpoint_required"],
            metrics_endpoint_label_required=options["metrics_endpoint_label_required"],
            rollout_flag_required=options["rollout_flag_required"],
            no_pii_or_stock_raw_required=options["no_pii_or_stock_raw_required"],
        )
        self.stdout.write(
            f"[{str(review['status']).upper()}] result={review['result']} module={review['module']}"
        )
        for key, value in review["endpoint_contract"].items():
            self.stdout.write(f"endpoint_contract {key}={value}")
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
            raise CommandError("API key public product detail endpoint contract review is blocked.")
