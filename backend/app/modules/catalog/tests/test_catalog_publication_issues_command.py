from io import StringIO

from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.catalog.application.catalog_metrics_queries import catalog_metrics_queries
from app.modules.catalog.models import Product, ProductVariant
from app.modules.tenants.models import Tenant


class ListCatalogPublicationIssuesCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Catalog Ops", slug="loja-catalog-ops", subdomain="loja-catalog-ops")
        self.status_mismatch = Product.objects.create(
            tenant=self.tenant,
            name="Produto Mismatch",
            slug="produto-mismatch",
            status=Product.Status.ACTIVE,
            is_active=False,
        )
        ProductVariant.objects.create(product=self.status_mismatch, sku="CAT-MIS-001", price="10.00", stock=1, is_default=True)
        self.no_variant = Product.objects.create(
            tenant=self.tenant,
            name="Produto Sem Variante",
            slug="produto-sem-variante",
            status=Product.Status.DRAFT,
            is_active=False,
        )
        self.no_default = Product.objects.create(
            tenant=self.tenant,
            name="Produto Sem Default",
            slug="produto-sem-default",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(product=self.no_default, sku="CAT-NODEF-001", price="10.00", stock=1, is_default=False)
        self.no_stock = Product.objects.create(
            tenant=self.tenant,
            name="Produto Sem Estoque",
            slug="produto-sem-estoque",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(product=self.no_stock, sku="CAT-STOCK-001", price="0.00", stock=0, is_default=True)

    def test_list_catalog_publication_issues_outputs_detected_issues(self):
        output = StringIO()

        call_command("list_catalog_publication_issues", tenant_id=str(self.tenant.id), stdout=output)

        value = output.getvalue()
        self.assertIn("issue=status_mismatch", value)
        self.assertIn("issue=missing_variant", value)
        self.assertIn("issue=missing_default_variant", value)
        self.assertIn("issue=missing_price", value)
        self.assertIn("issue=stock_unavailable", value)

    def test_list_catalog_publication_issues_filters_by_issue(self):
        output = StringIO()

        call_command(
            "list_catalog_publication_issues",
            tenant_id=str(self.tenant.id),
            issue="missing_variant",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("slug=produto-sem-variante", value)
        self.assertNotIn("slug=produto-mismatch", value)
        self.assertIn("catalog_publication_issues=1", value)

    def test_catalog_metrics_export_prometheus_payload(self):
        payload = catalog_metrics_queries.export_prometheus_metrics()

        self.assertIn("hubx_catalog_publication_issue_total", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",issue="status_mismatch"', payload)
        self.assertIn('issue="missing_variant"', payload)
        self.assertIn("hubx_catalog_card_decision_signal_total", payload)
        self.assertIn(f'tenant_id="{self.tenant.id}",signal="acompanhar_reposicao"', payload)

    @override_settings(CATALOG_OBSERVABILITY_TOKEN="catalog-token")
    def test_catalog_metrics_view_returns_payload_with_token(self):
        response = self.client.get(
            reverse("catalog:catalog-metrics"),
            HTTP_X_HUBX_OBSERVABILITY_TOKEN="catalog-token",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response["Content-Type"])
        self.assertContains(response, "hubx_catalog_publication_issue_total")
        self.assertContains(response, "hubx_catalog_card_decision_signal_total")

    @override_settings(CATALOG_OBSERVABILITY_TOKEN="catalog-token")
    def test_catalog_metrics_view_rejects_invalid_token(self):
        response = self.client.get(reverse("catalog:catalog-metrics"))

        self.assertEqual(response.status_code, 403)

    @override_settings(CATALOG_OBSERVABILITY_TOKEN="")
    def test_catalog_metrics_view_is_not_found_without_token(self):
        response = self.client.get(reverse("catalog:catalog-metrics"))

        self.assertEqual(response.status_code, 404)
