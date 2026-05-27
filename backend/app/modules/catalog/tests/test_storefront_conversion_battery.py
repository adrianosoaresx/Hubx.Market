from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.catalog.application.storefront_catalog_queries import storefront_catalog_queries
from app.modules.catalog.application.storefront_conversion_closure_queries import storefront_conversion_closure_queries
from app.modules.catalog.application.storefront_conversion_insights import storefront_conversion_insights
from app.modules.catalog.models import Product, ProductVariant, StorefrontDiscoveryEventLog
from app.modules.tenants.models import Tenant


class StorefrontConversionBatteryTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Conversion Tenant", slug="conversion-tenant", subdomain="conversion-tenant")
        self.other_tenant = Tenant.objects.create(name="Other Conversion", slug="other-conversion", subdomain="other-conversion")
        self.promising = self._product("Produto Promissor", "produto-promissor", stock=8, compare_price="")
        self.regular = self._product("Produto Regular", "produto-regular", stock=8, compare_price="")

    def test_baseline_counts_tenant_scoped_conversion_events(self):
        self._event("catalog.discovery_viewed", {"result_count": 2})
        self._event("catalog.product_detail_viewed", {"product_slug": "produto-promissor"})
        self._event("catalog.pdp_cta_intent", {"product_slug": "produto-promissor", "cta_result": "cart-item-added"})
        StorefrontDiscoveryEventLog.objects.create(
            tenant=self.other_tenant,
            event_name="catalog.pdp_cta_intent",
            payload={"product_slug": "other", "cta_result": "cart-item-added"},
        )

        baseline = storefront_conversion_insights.baseline(tenant_id=self.tenant.id)

        self.assertEqual(baseline["total_events"], 3)
        self.assertEqual(baseline["listing_views"], 1)
        self.assertEqual(baseline["pdp_views"], 1)
        self.assertEqual(baseline["successful_ctas"], 1)
        self.assertEqual(baseline["pdp_view_rate"], 1.0)

    def test_pdp_funnel_and_search_dropoff_are_computed_from_payloads(self):
        self._event("catalog.product_detail_viewed", {"product_slug": "produto-promissor"})
        self._event("catalog.pdp_cta_intent", {"product_slug": "produto-promissor", "cta_result": "cart-item-stock-conflict"})
        self._event("catalog.search_performed", {"query": "sem resultado", "result_count": 0})

        funnel = storefront_conversion_insights.pdp_funnel(tenant_id=self.tenant.id)
        dropoff = storefront_conversion_insights.search_facet_dropoff(tenant_id=self.tenant.id)

        self.assertEqual(funnel["products"]["produto-promissor"]["pdp_views"], 1)
        self.assertEqual(funnel["products"]["produto-promissor"]["unavailable_ctas"], 1)
        self.assertEqual(dropoff["zero_result_count"], 1)
        self.assertEqual(dropoff["zero_result_events"][0]["query"], "sem resultado")

    def test_product_card_priority_experiment_boosts_recent_conversion_signal(self):
        self._event("catalog.product_detail_viewed", {"product_slug": "produto-promissor"})
        self._event("catalog.pdp_cta_intent", {"product_slug": "produto-promissor", "cta_result": "cart-item-added"})

        products = storefront_catalog_queries.list_products(tenant_id=self.tenant.id)

        self.assertEqual(products[0]["slug"], "produto-promissor")
        self.assertEqual(products[0]["conversion_experiment_key"], "product_card_priority_v1")
        self.assertGreater(products[0]["conversion_experiment_delta"], 0)

    def test_closure_recommends_battery_j(self):
        review = storefront_conversion_closure_queries.get_review(
            baseline_ready=True,
            pdp_funnel_ready=True,
            search_facet_dropoff_ready=True,
            experiment_contract_ready=True,
            experiment_execution_ready=True,
            no_full_redesign=True,
            docs_updated=True,
            decision_recorded=True,
        )

        self.assertTrue(review["ready"])
        self.assertIn("Battery J — System Production Closure", review["next_tracks"])

    def test_management_command_closure_reports_ready(self):
        output = StringIO()
        call_command(
            "storefront_conversion",
            review="closure",
            baseline_ready=True,
            pdp_funnel_ready=True,
            search_facet_dropoff_ready=True,
            experiment_contract_ready=True,
            experiment_execution_ready=True,
            no_full_redesign=True,
            docs_updated=True,
            decision_recorded=True,
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=storefront-conversion-ready", value)
        self.assertIn("next_track=Battery J — System Production Closure", value)

    def _product(self, name: str, slug: str, *, stock: int, compare_price: str):
        product = Product.objects.create(
            tenant=self.tenant,
            name=name,
            slug=slug,
            brand_name="Hubx",
            category_label="Calçados",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku=f"{slug.upper()[:12]}-BLK-42",
            price="199.90",
            compare_price=compare_price or None,
            stock=stock,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        return product

    def _event(self, event_name: str, payload: dict[str, object]) -> StorefrontDiscoveryEventLog:
        return StorefrontDiscoveryEventLog.objects.create(
            tenant=self.tenant,
            event_name=event_name,
            path="/catalog/",
            payload=payload,
        )
