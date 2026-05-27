from __future__ import annotations

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from app.modules.api_keys.application.api_key_public_product_detail_endpoint_contract_review_queries import (
    api_key_public_product_detail_endpoint_contract_review_queries,
)


class ApiKeyPublicProductDetailEndpointContractReviewTests(TestCase):
    def test_review_ready_defines_product_detail_contract(self):
        review = api_key_public_product_detail_endpoint_contract_review_queries.get_review(**self._ready_flags())

        self.assertTrue(review["ready"])
        self.assertEqual(review["result"], "api-key-public-product-detail-endpoint-contract-review-ready")
        self.assertEqual(review["blockers"], ())
        self.assertEqual(review["endpoint_contract"]["path"], "/api/v1/catalog/products/<slug>/")
        self.assertEqual(review["endpoint_contract"]["scope"], "read:catalog")
        self.assertEqual(review["endpoint_contract"]["rate_limit_endpoint"], "catalog.products.detail")
        self.assertIn("API Key Public Product Detail Endpoint Execution", review["next_tracks"])

    def test_review_blocks_without_catalog_ownership_or_tenant_scope(self):
        flags = self._ready_flags()
        flags["catalog_owner_confirmed"] = False
        flags["tenant_scope_required"] = False

        review = api_key_public_product_detail_endpoint_contract_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-product-detail-contract:catalog_owner_confirmed:missing", review["blockers"])
        self.assertIn("public-product-detail-contract:tenant_scope_required:missing", review["blockers"])

    def test_review_blocks_without_payload_and_operations_contract(self):
        flags = self._ready_flags()
        flags["safe_payload_required"] = False
        flags["rate_limit_endpoint_required"] = False
        flags["rollout_flag_required"] = False

        review = api_key_public_product_detail_endpoint_contract_review_queries.get_review(**flags)

        self.assertFalse(review["ready"])
        self.assertIn("public-product-detail-contract:safe_payload_required:missing", review["blockers"])
        self.assertIn("public-product-detail-contract:rate_limit_endpoint_required:missing", review["blockers"])
        self.assertIn("public-product-detail-contract:rollout_flag_required:missing", review["blockers"])

    def test_command_outputs_contract_without_sensitive_material(self):
        output = StringIO()

        call_command(
            "api_key_public_product_detail_endpoint_contract_review",
            *self._ready_args(),
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("[READY]", value)
        self.assertIn("endpoint_contract path=/api/v1/catalog/products/<slug>/", value)
        self.assertIn("decision key=payload status=required", value)
        self.assertIn("next_track=API Key Public Product Detail Endpoint Execution", value)
        self.assertNotIn("secret=", value)
        self.assertNotIn("key_hash=", value)
        self.assertNotIn("Authorization", value)
        self.assertNotIn("X-Hubx-Api-Key", value)

    def test_command_can_fail_on_blockers(self):
        with self.assertRaises(CommandError):
            call_command("api_key_public_product_detail_endpoint_contract_review", "--fail-on-blockers", stdout=StringIO())

    def _ready_flags(self) -> dict[str, bool]:
        return {
            "expansion_review_ready": True,
            "catalog_owner_confirmed": True,
            "slug_lookup_required": True,
            "tenant_scope_required": True,
            "active_product_only_required": True,
            "read_catalog_scope_required": True,
            "safe_payload_required": True,
            "public_variant_summary_required": True,
            "rate_limit_endpoint_required": True,
            "metrics_endpoint_label_required": True,
            "rollout_flag_required": True,
            "no_pii_or_stock_raw_required": True,
        }

    def _ready_args(self) -> tuple[str, ...]:
        return (
            "--expansion-review-ready",
            "--catalog-owner-confirmed",
            "--slug-lookup-required",
            "--tenant-scope-required",
            "--active-product-only-required",
            "--read-catalog-scope-required",
            "--safe-payload-required",
            "--public-variant-summary-required",
            "--rate-limit-endpoint-required",
            "--metrics-endpoint-label-required",
            "--rollout-flag-required",
            "--no-pii-or-stock-raw-required",
        )
