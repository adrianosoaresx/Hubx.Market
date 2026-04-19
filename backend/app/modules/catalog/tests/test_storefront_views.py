from django.test import TestCase
from django.urls import reverse

from app.modules.catalog.models import Product, ProductVariant
from app.modules.catalog.application.storefront_catalog_queries import storefront_catalog_queries
from app.modules.tenants.models import Tenant


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
        self.assertEqual(product["sku"], "RUNNER-PERSIST-BLK-42")
        self.assertEqual(product["price"], "399.90")
        self.assertEqual(product["compare_price"], "449.90")
        self.assertEqual(product["stock_state"], "in_stock")
        self.assertEqual(product["stock_helper"], "12 unidades em pronta entrega · Preto · 42")
        self.assertEqual(product["price_helper"], "oferta disponível para Preto · 42, com economia frente ao valor anterior e parcelamento em até 3x sem juros")
        self.assertEqual(product["eyebrow"], "Hubx Persisted")
        self.assertEqual(product["primary_action_label"], "Adicionar ao carrinho")
        self.assertEqual(product["secondary_action_href"], "#checkout")
        self.assertEqual(product["badge_label"], "Oferta ativa · Preto · 42")
        self.assertEqual(product["badge_variant"], "success")
        self.assertEqual(product["product_gallery_items"][0]["url"], "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertEqual(product["main_image_url"], "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertEqual(product["main_image_alt"], "Tênis Hubx Runner Persistido · imagem principal")
        self.assertEqual(product["variant_groups"][0]["selected"], "42")
        self.assertIn("Combinação em destaque · Preto · 42", product["purchase_note"])
        self.assertEqual(product["variant_groups"][0]["label"], "Tamanho disponível")
        self.assertEqual(product["variant_groups"][0]["help_text"], "Preço e estoque exibidos refletem a variante padrão Preto · 42.")
        self.assertEqual([option["value"] for option in product["variant_groups"][0]["options"]], ["42", "43"])
        self.assertEqual([option["label"] for option in product["variant_groups"][1]["options"]], ["Preto", "Branco"])
        self.assertEqual(product["variant_groups"][1]["help_text"], "A mídia principal e os textos comerciais priorizam Preto · 42.")

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
        self.assertContains(detail_response, "12 unidades em pronta entrega · Preto · 42")
        self.assertContains(detail_response, "oferta disponível para Preto · 42, com economia frente ao valor anterior e parcelamento em até 3x sem juros")
        self.assertContains(detail_response, "Combinação em destaque · Preto · 42, com disponibilidade imediata e compra segura no storefront.")
        self.assertContains(detail_response, "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")

    def test_storefront_product_detail_falls_back_safely_when_no_images_exist(self):
        tenant = Tenant.objects.create(name="Sem Mídia", slug="sem-midia", subdomain="sem-midia")
        product = Product.objects.create(
            tenant=tenant,
            name="Produto Sem Imagem",
            slug="produto-sem-imagem",
            brand_name="Hubx Fallback",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="FALLBACK-RUNNER-BLK-41",
            price="199.90",
            stock=3,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        item = storefront_catalog_queries.get_product("produto-sem-imagem")

        self.assertIn("placehold.co", item["main_image_url"])
        self.assertTrue(item["product_gallery_items"])

    def test_storefront_main_image_prefers_media_coherent_with_default_variant_when_possible(self):
        tenant = Tenant.objects.create(name="Coerência PDP", slug="coerencia-pdp", subdomain="coerencia-pdp")
        product = Product.objects.create(
            tenant=tenant,
            name="Produto Coerente",
            slug="produto-coerente",
            brand_name="Hubx Match",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="MATCH-WHT-41",
            price="219.90",
            stock=7,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="MATCH-BLK-41",
            price="219.90",
            stock=3,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=False,
        )
        product.images.create(
            image_url="https://cdn.hubx.market/demo/catalog/match-black.jpg",
            alt_text="Produto Coerente BLK 41",
            position=1,
            is_primary=True,
        )
        product.images.create(
            image_url="https://cdn.hubx.market/demo/catalog/match-white.jpg",
            alt_text="Produto Coerente WHT 41",
            position=2,
            is_primary=False,
        )

        item = storefront_catalog_queries.get_product("produto-coerente")

        self.assertEqual(item["main_image_url"], "https://cdn.hubx.market/demo/catalog/match-white.jpg")
        self.assertEqual(item["product_gallery_items"][0]["url"], "https://cdn.hubx.market/demo/catalog/match-white.jpg")
        self.assertIn("Branco · 41", item["stock_helper"])
        self.assertIn("Branco · 41", item["price_helper"])

    def test_storefront_variant_groups_reflect_real_variants_when_available(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido")

        self.assertEqual(product["variant_groups"][0]["variant"], "buttons")
        self.assertEqual(product["variant_groups"][1]["variant"], "swatches")
        self.assertTrue(any(option["out_of_stock"] for option in product["variant_groups"][0]["options"]))

    def test_storefront_pdp_uses_default_variant_backorder_hints_when_available(self):
        tenant = Tenant.objects.create(name="Sob Encomenda", slug="sob-encomenda", subdomain="sob-encomenda")
        product = Product.objects.create(
            tenant=tenant,
            name="Produto Sob Encomenda",
            slug="produto-sob-encomenda",
            brand_name="Hubx Reserve",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RESERVE-NAV-40",
            price="249.90",
            stock=0,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=True,
            is_default=True,
        )

        item = storefront_catalog_queries.get_product("produto-sob-encomenda")

        self.assertEqual(item["stock_state"], "backorder")
        self.assertEqual(item["primary_action_label"], "Reservar por encomenda")
        self.assertEqual(item["badge_label"], "Sob encomenda")
        self.assertIn("Variante disponível por encomenda · Marinho · 40", item["stock_helper"])
        self.assertIn("Produto disponível por encomenda · Marinho · 40", item["purchase_note"])

    def test_storefront_pdp_uses_default_variant_out_of_stock_hints_when_backorder_is_disabled(self):
        tenant = Tenant.objects.create(name="Sem Estoque", slug="sem-estoque", subdomain="sem-estoque")
        product = Product.objects.create(
            tenant=tenant,
            name="Produto Sem Estoque",
            slug="produto-sem-estoque",
            brand_name="Hubx Notify",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="NOTIFY-RED-39",
            price="189.90",
            stock=0,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        item = storefront_catalog_queries.get_product("produto-sem-estoque")

        self.assertEqual(item["stock_state"], "out_of_stock")
        self.assertEqual(item["primary_action_label"], "Avise-me da reposição")
        self.assertEqual(item["badge_label"], "Disponível agora · Vermelho · 39")
        self.assertIn("Variante indisponível no momento · Vermelho · 39", item["stock_helper"])

    def test_storefront_pdp_uses_low_stock_commercial_messaging_when_variant_is_scarce(self):
        tenant = Tenant.objects.create(name="Baixo Estoque", slug="baixo-estoque", subdomain="baixo-estoque")
        product = Product.objects.create(
            tenant=tenant,
            name="Produto Últimas Unidades",
            slug="produto-ultimas-unidades",
            brand_name="Hubx Sprint",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="SPRINT-BLK-38",
            price="159.90",
            compare_price="179.90",
            stock=2,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        item = storefront_catalog_queries.get_product("produto-ultimas-unidades")

        self.assertEqual(item["badge_label"], "Últimas unidades · Preto · 38")
        self.assertEqual(item["badge_variant"], "warning")
        self.assertIn("Poucas unidades disponíveis · Preto · 38", item["purchase_note"])
        self.assertIn("compra rápida para Preto · 38", item["price_helper"])
