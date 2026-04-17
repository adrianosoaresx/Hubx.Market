from django.test import TestCase
from django.urls import reverse

from app.modules.catalog.application.admin_product_queries import admin_product_queries


class AdminProductViewTests(TestCase):
    def test_products_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("catalog:admin-products-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_products_list_page.html")
        self.assertContains(response, "Produtos")
        self.assertContains(response, "Tênis Hubx Runner")

    def test_products_list_view_applies_search_filter(self):
        response = self.client.get(reverse("catalog:admin-products-list"), {"q": "camiseta"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Camiseta Hubx Performance")
        self.assertNotContains(response, "Tênis Hubx Runner")

    def test_product_detail_view_renders_design_system_template(self):
        response = self.client.get(
            reverse("catalog:admin-products-detail", kwargs={"product_slug": "tenis-hubx-runner"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_product_detail_page.html")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "RUNNER-001-BLK-42")

    def test_product_form_create_view_renders_design_system_template(self):
        response = self.client.get(reverse("catalog:admin-products-create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_product_form_page.html")
        self.assertContains(response, "Novo produto")

    def test_product_form_edit_view_renders_design_system_template(self):
        response = self.client.get(
            reverse("catalog:admin-products-edit", kwargs={"product_slug": "tenis-hubx-runner"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_product_form_page.html")
        self.assertContains(response, "Editar Tênis Hubx Runner")

    def test_admin_product_query_service_returns_expected_contract(self):
        product = admin_product_queries.get_product("tenis-hubx-runner")
        form_initial = admin_product_queries.get_form_initial("tenis-hubx-runner")

        self.assertEqual(product["slug"], "tenis-hubx-runner")
        self.assertEqual(product["sku"], "RUNNER-001-BLK-42")
        self.assertEqual(form_initial["name"], "Tênis Hubx Runner")
        self.assertEqual(form_initial["status_selected"], "active")

    def test_admin_product_query_service_reports_persisted_source_readiness(self):
        self.assertFalse(admin_product_queries.using_persisted_source())


class AdminProductPersistedReadTests(TestCase):
    fixtures = ["catalog_minimal_seed.json"]

    def test_admin_product_query_service_uses_persisted_records_when_available(self):
        product = admin_product_queries.get_product("tenis-hubx-runner-persistido")
        form_initial = admin_product_queries.get_form_initial("tenis-hubx-runner-persistido")

        self.assertTrue(admin_product_queries.using_persisted_source())
        self.assertEqual(product["name"], "Tênis Hubx Runner Persistido")
        self.assertEqual(product["brand"], "Hubx Persisted")
        self.assertEqual(product["sku"], "RUNNER-PERSIST-001")
        self.assertEqual(product["price"], "399.90")
        self.assertEqual(form_initial["name"], "Tênis Hubx Runner Persistido")
        self.assertIn("Hubx Persisted", product["summary_content"])
        self.assertIn("SKU principal RUNNER-PERSIST-001", product["summary_content"])
        self.assertIn("Preço atual: R$ 399,90", product["pricing_content"])
        self.assertIn("Estoque disponível: 12 unidade(s)", product["inventory_content"])
        self.assertIn("visível no catálogo", product["visibility_content"])
        self.assertEqual(product["updated_at"], "14/04/2026 às 12:00")
        self.assertGreaterEqual(len(product["activity_items"]), 2)
        self.assertEqual(product["activity_items"][0]["badge_label"], "Catálogo")

    def test_admin_product_list_view_renders_persisted_records_when_present(self):
        response = self.client.get(reverse("catalog:admin-products-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tênis Hubx Runner Persistido")
        self.assertContains(response, "RUNNER-PERSIST-001")
        self.assertContains(response, "14/04/2026 às 12:00")

    def test_admin_product_detail_view_renders_enriched_persisted_content(self):
        response = self.client.get(
            reverse("catalog:admin-products-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SKU principal RUNNER-PERSIST-001")
        self.assertContains(response, "Estoque disponível: 12 unidade(s)")
        self.assertContains(response, "Produto com destaque ativo")
