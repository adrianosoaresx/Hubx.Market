from django.test import TestCase
from django.urls import reverse

from app.modules.catalog.application.storefront_catalog_queries import storefront_catalog_queries


class StorefrontViewTests(TestCase):
    def test_catalog_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("storefront:catalog-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/catalog_page.html")
        self.assertContains(response, "Catálogo")
        self.assertContains(response, "Tênis Hubx Runner")

    def test_catalog_list_view_applies_search_filter(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "mochila"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mochila Hubx Urban")
        self.assertNotContains(response, "Tênis Hubx Runner")

    def test_product_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/product_detail_page.html")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Adicionar ao carrinho")

    def test_storefront_catalog_query_service_returns_expected_contract(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner")
        products = storefront_catalog_queries.list_products()

        self.assertEqual(product["slug"], "tenis-hubx-runner")
        self.assertEqual(product["brand"], "Hubx")
        self.assertTrue(any(item["slug"] == "tenis-hubx-runner" for item in products))


class StorefrontPersistedReadTests(TestCase):
    fixtures = ["catalog_minimal_seed.json"]

    def test_storefront_query_service_uses_persisted_records_when_available(self):
        products = storefront_catalog_queries.list_products()
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido")

        self.assertTrue(storefront_catalog_queries.using_persisted_source())
        self.assertTrue(any(item["slug"] == "tenis-hubx-runner-persistido" for item in products))
        self.assertEqual(product["name"], "Tênis Hubx Runner Persistido")
        self.assertEqual(product["brand"], "Hubx Persisted")
        self.assertEqual(product["sku"], "RUNNER-PERSIST-001")
        self.assertEqual(product["price"], "399.90")
        self.assertEqual(product["compare_price"], "449.90")
        self.assertEqual(product["stock_state"], "in_stock")
        self.assertEqual(product["stock_helper"], "Pronta entrega")
        self.assertEqual(product["price_helper"], "ou 3x sem juros")
        self.assertEqual(product["eyebrow"], "Hubx Persisted")
        self.assertEqual(product["primary_action_label"], "Adicionar ao carrinho")
        self.assertEqual(product["secondary_action_href"], "#checkout")
        self.assertEqual(product["product_gallery_items"][0]["url"], "https://placehold.co/900x900?text=tenis-hubx-runner-persistido-1")
        self.assertEqual(product["main_image_alt"], "Tênis Hubx Runner Persistido imagem 1")
        self.assertEqual(product["variant_groups"][0]["selected"], "42")
        self.assertIn("disponibilidade imediata", product["purchase_note"])

    def test_storefront_views_render_persisted_records_when_present(self):
        list_response = self.client.get(reverse("storefront:catalog-list"))
        detail_response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Tênis Hubx Runner Persistido")
        self.assertContains(list_response, "Hubx Persisted")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/product_detail_page.html")
        self.assertContains(detail_response, "Tênis Hubx Runner Persistido")
        self.assertContains(detail_response, "R$ 399,90")
        self.assertContains(detail_response, "Hubx Persisted")
        self.assertContains(detail_response, "Pronta entrega")
        self.assertContains(detail_response, "ou 3x sem juros")
        self.assertContains(detail_response, "Produto em destaque com disponibilidade imediata no storefront.")
