from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import urlencode

from app.modules.accounts.models import AccountProfile
from app.modules.catalog.models import Product, ProductVariant
from app.modules.catalog.application.storefront_catalog_queries import storefront_catalog_queries
from app.modules.checkout.models import CheckoutSession
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class StorefrontViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Storefront Demo",
            slug="hubx-storefront-demo",
            subdomain="hubx-storefront-demo",
        )
        self.storefront_host = f"{self.tenant.subdomain}.hubx.market"
        self.client.defaults["HTTP_HOST"] = self.storefront_host

    def test_catalog_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/catalog_page.html")
        self.assertContains(response, "Catálogo")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "curadoria leve")

    def test_catalog_list_view_applies_search_filter(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "mochila"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mochila Hubx Urban")
        self.assertNotContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "busca atual: “mochila”")
        self.assertContains(response, "Resultados para “mochila”")
        self.assertContains(response, "vale abrir agora")

    def test_catalog_list_view_applies_category_context(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"category": "calcados"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "categoria atual: Calçados")
        self.assertContains(response, "Explore calçados com combinações em destaque")
        self.assertContains(response, "Use a categoria atual para refinar a vitrine")

    def test_catalog_list_view_shows_search_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "nada-aqui"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto encontrado para esta busca")
        self.assertContains(response, "Não encontramos resultados para “nada-aqui”")

    def test_catalog_list_view_shows_category_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"category": "vestuario", "q": "runner"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto encontrado nesta categoria")
        self.assertContains(response, "Nenhum item de vestuário corresponde à busca atual")

    def test_catalog_list_view_applies_quick_filter_in_stock(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "in_stock"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro rápido ativo: Pronta entrega")
        self.assertContains(response, "filtro rápido: Pronta entrega")
        self.assertContains(response, "use Limpar para remover este recorte")
        self.assertContains(response, "Use Limpar para voltar à vitrine completa")

    def test_catalog_list_view_applies_quick_filter_featured(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "featured"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro rápido ativo: Em destaque")
        self.assertContains(response, "destaques atuais da vitrine")
        self.assertContains(response, "produtos priorizados pela vitrine usando sinais reais")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Destaque editorial atual para Preto · 42")
        self.assertContains(response, "mesma leitura de destaque editorial mostrada neste card")

    def test_catalog_list_view_applies_quick_filter_quick_buy(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "quick_buy"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro rápido ativo: Compra rápida")
        self.assertContains(response, "produtos prontos para compra rápida")
        self.assertContains(response, "combinações ativas, em estoque ou com poucas unidades")
        self.assertContains(response, "Use Limpar para voltar à vitrine completa")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Compra rápida disponível para Preto · 42")
        self.assertContains(response, "seguir para checkout com a mesma base comercial mostrada neste card")
        self.assertContains(response, "Compra rápida pronta para retomar sua navegação")

    def test_catalog_list_view_applies_quick_filter_offer(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "offer"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro rápido ativo: Em oferta")
        self.assertContains(response, "ofertas ativas da vitrine")
        self.assertContains(response, "preço comparativo ativo já visível no card")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Oferta ativa para Preto · 42")
        self.assertContains(response, "mesma leitura de oferta ativa mostrada neste card")
        self.assertContains(response, "Use Limpar para voltar à vitrine completa")

    def test_catalog_list_view_shows_quick_filter_empty_state_for_backorder(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "backorder", "q": "runner"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto sob encomenda")
        self.assertContains(response, "Não há produtos sob encomenda nesta visão. Use Limpar")

    def test_catalog_list_view_shows_quick_buy_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "quick_buy", "q": "mochila"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto pronto para compra rápida")
        self.assertContains(response, "Não há combinações ativas e disponíveis para compra rápida neste recorte")

    def test_catalog_list_view_shows_featured_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "featured", "q": "mochila"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum destaque disponível agora")
        self.assertContains(response, "Não há produtos em destaque neste recorte no momento")

    def test_catalog_list_view_shows_offer_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "offer", "q": "nada-aqui"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma oferta ativa agora")
        self.assertContains(response, "Não há produtos com oferta ativa neste recorte no momento")

    def test_product_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/product_detail_page.html")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Ir para checkout")

    def test_storefront_catalog_query_service_returns_expected_contract(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner", tenant_id=self.tenant.id)
        products = storefront_catalog_queries.list_products(tenant_id=self.tenant.id)

        self.assertEqual(product["slug"], "tenis-hubx-runner")
        self.assertEqual(product["brand"], "Hubx")
        self.assertTrue(any(item["slug"] == "tenis-hubx-runner" for item in products))

    def test_storefront_views_require_resolved_tenant(self):
        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST="ghost.hubx.market")

        self.assertEqual(response.status_code, 404)


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class StorefrontPersistedReadTests(TestCase):
    fixtures = ["catalog_minimal_seed.json"]

    def setUp(self):
        self.tenant = Tenant.objects.get(pk=1)
        self.storefront_host = f"{self.tenant.subdomain}.hubx.market"
        self.client.defaults["HTTP_HOST"] = self.storefront_host

    def test_storefront_query_service_uses_persisted_records_when_available(self):
        products = storefront_catalog_queries.list_products(tenant_id=self.tenant.id)
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido", tenant_id=self.tenant.id)

        self.assertTrue(storefront_catalog_queries.using_persisted_source(tenant_id=self.tenant.id))
        self.assertTrue(any(item["slug"] == "tenis-hubx-runner-persistido" for item in products))
        self.assertEqual(product["name"], "Tênis Hubx Runner Persistido")
        self.assertEqual(product["brand"], "Hubx Persisted")
        self.assertEqual(product["sku"], "RUNNER-PERSIST-BLK-42")
        self.assertEqual(product["price"], "399.90")
        self.assertEqual(product["compare_price"], "449.90")
        self.assertEqual(product["stock_state"], "in_stock")
        self.assertEqual(product["stock_label"], "Em estoque")
        self.assertEqual(product["stock_helper"], "12 unidades em pronta entrega · Preto · 42")
        self.assertEqual(product["price_helper"], "oferta disponível para Preto · 42, com economia frente ao valor anterior e parcelamento em até 3x sem juros")
        self.assertEqual(product["effective_variant_summary"], "Variante em destaque agora: Preto · 42 · SKU RUNNER-PERSIST-BLK-42.")
        self.assertIn("reflete Preto · 42", product["availability_note"])
        self.assertIn("já pode seguir para checkout", product["cta_helper"])
        self.assertEqual(product["eyebrow"], "Hubx Persisted")
        self.assertEqual(product["primary_action_label"], "Ir para checkout")
        self.assertFalse(product["primary_action_disabled"])
        self.assertEqual(product["secondary_action_label"], "Ir para checkout")
        self.assertEqual(product["secondary_action_target"], "checkout")
        self.assertEqual(product["badge_label"], "Oferta ativa · Preto · 42")
        self.assertEqual(product["badge_variant"], "success")
        self.assertEqual(product["product_gallery_items"][0]["url"], "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertEqual(product["main_image_url"], "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertEqual(product["main_image_alt"], "Tênis Hubx Runner Persistido · imagem principal")
        self.assertEqual(product["variant_groups"][0]["selected"], "42")
        self.assertIn("Combinação em destaque · Preto · 42", product["purchase_note"])
        self.assertIn("valor percebido mais alto", product["product_subtitle"])
        self.assertIn("valor percebido mais alto", product["short_description"])
        self.assertIn("valor percebido mais alto", product["purchase_note"])
        self.assertEqual(product["variant_groups"][0]["label"], "Tamanho disponível")
        self.assertEqual(product["variant_groups"][0]["help_text"], "Preço e estoque exibidos refletem a variante padrão Preto · 42.")
        self.assertEqual([option["value"] for option in product["variant_groups"][0]["options"]], ["42", "43"])
        self.assertEqual([option["label"] for option in product["variant_groups"][1]["options"]], ["Preto", "Branco"])
        self.assertEqual(product["variant_groups"][1]["help_text"], "A mídia principal e os textos comerciais priorizam Preto · 42.")
        self.assertEqual(product["catalog_card_subtitle"], "Calçados esportivos · Preto · 42")
        self.assertEqual(product["catalog_card_meta"], "SKU RUNNER-PERSIST-BLK-42 · oferta ativa")
        self.assertEqual(product["catalog_card_price_helper"], "oferta ativa para Preto · 42, com parcelamento em até 3x sem juros")
        self.assertEqual(product["catalog_card_variant_summary"], "Combinação em destaque: Preto · 42.")
        self.assertEqual(product["catalog_card_curation_note"], "Escolha editorial da vitrine com oferta ativa e caminho rápido para compra.")
        self.assertEqual(product["catalog_card_decision_signal"], "oferta_editorial")
        self.assertEqual(product["catalog_card_availability_note"], "Preto · 42 pronta para compra imediata.")
        self.assertIn("decidir com confiança", product["catalog_card_click_helper"])
        self.assertIn("combinação destacada no catálogo continua sendo Preto · 42", product["product_subtitle"])
        self.assertIn("combinação destacada no catálogo continua sendo Preto · 42", product["short_description"])
        self.assertIn("combinação destacada no catálogo continua sendo Preto · 42", product["purchase_note"])
        self.assertIn("já pode seguir para checkout", product["purchase_note"])
        self.assertIn("decisão segura", product["cta_helper"])

    def test_storefront_query_service_applies_selected_variant_when_valid(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido", tenant_id=self.tenant.id, size="42", color="wht")

        self.assertEqual(product["sku"], "RUNNER-PERSIST-WHT-42")
        self.assertEqual(product["stock_state"], "low_stock")
        self.assertEqual(product["stock_label"], "Estoque baixo")
        self.assertEqual(product["stock_helper"], "Restam 5 unidades para envio imediato · Branco · 42")
        self.assertEqual(product["effective_variant_summary"], "Variante em destaque agora: Branco · 42 · SKU RUNNER-PERSIST-WHT-42.")
        self.assertEqual(product["variant_groups"][0]["selected"], "42")
        self.assertEqual(product["variant_groups"][1]["selected"], "wht")
        self.assertFalse(product["variant_groups"][0].get("invalid"))

    def test_storefront_query_service_falls_back_safely_when_selected_variant_is_invalid(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido", tenant_id=self.tenant.id, size="99", color="wht")

        self.assertEqual(product["sku"], "RUNNER-PERSIST-BLK-42")
        self.assertTrue(product["variant_groups"][0]["invalid"])
        self.assertIn("fallback seguro", product["variant_groups"][0]["help_text"].lower())
        self.assertIn("combinação escolhida não está disponível", product["variant_groups"][0]["error_text"].lower())

    def test_storefront_views_render_persisted_records_when_present(self):
        list_response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST=self.storefront_host)
        detail_response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Tênis Hubx Runner Persistido")
        self.assertContains(list_response, "Hubx Persisted")
        self.assertContains(list_response, "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertContains(list_response, "Calçados esportivos · Preto · 42")
        self.assertContains(list_response, "SKU RUNNER-PERSIST-BLK-42 · oferta ativa")
        self.assertContains(list_response, "Combinação em destaque: Preto · 42.")
        self.assertContains(list_response, "Preto · 42 pronta para compra imediata.")
        self.assertContains(list_response, "decidir com confiança")
        self.assertContains(list_response, "oferta ativa para Preto · 42, com parcelamento em até 3x sem juros")
        self.assertContains(list_response, "Explore produtos com combinações em destaque, disponibilidade atual e uma curadoria leve")
        self.assertContains(list_response, "cards já refletem variante efetiva, disponibilidade atual e sinais leves de curadoria da vitrine")
        self.assertContains(list_response, "A vitrine continua pronta para receber sua próxima compra")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/product_detail_page.html")
        self.assertContains(detail_response, "Tênis Hubx Runner Persistido")
        self.assertContains(detail_response, "R$ 399,90")
        self.assertContains(detail_response, "Hubx Persisted")
        self.assertContains(detail_response, "12 unidades em pronta entrega · Preto · 42")
        self.assertContains(detail_response, "Variante em destaque agora: Preto · 42 · SKU RUNNER-PERSIST-BLK-42.")
        self.assertContains(detail_response, "A disponibilidade desta compra reflete Preto · 42")
        self.assertContains(detail_response, "oferta disponível para Preto · 42, com economia frente ao valor anterior e parcelamento em até 3x sem juros")
        self.assertContains(detail_response, "Combinação em destaque · Preto · 42, com disponibilidade imediata e compra segura no storefront.")
        self.assertContains(detail_response, "valor percebido mais alto")
        self.assertContains(detail_response, "A combinação destacada no catálogo continua sendo Preto · 42")
        self.assertContains(detail_response, "Ir para checkout")
        self.assertContains(detail_response, "decisão segura")
        self.assertContains(detail_response, "Esta combinação (Preto · 42) já pode seguir para checkout")
        self.assertContains(
            detail_response,
            f'{reverse("checkout:checkout-page")}?{urlencode({"back_url": reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})})}',
        )
        self.assertContains(detail_response, "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")

    def test_product_detail_view_renders_selected_variant_when_requested(self):
        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            {"size": "42", "color": "wht"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Restam 5 unidades para envio imediato · Branco · 42")
        self.assertContains(response, "Variante em destaque agora: Branco · 42 · SKU RUNNER-PERSIST-WHT-42.")
        self.assertContains(response, "A disponibilidade desta compra reflete Branco · 42")
        self.assertContains(response, "decisão rápida")
        self.assertContains(response, "Esta combinação (Branco · 42) já pode seguir para checkout agora")

    def test_product_detail_post_creates_checkout_session_and_redirects(self):
        response = self.client.post(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("checkout:checkout-page"), response["Location"])
        self.assertIn("session_key=", response["Location"])
        self.assertIn("back_url=", response["Location"])
        self.assertIn("stage=cart", response["Location"])

        session = CheckoutSession.objects.order_by("-id").first()
        self.assertIsNotNone(session)
        self.assertEqual(session.items.count(), 1)
        self.assertEqual(session.items.first().title, "Tênis Hubx Runner Persistido")
        self.assertEqual(session.items.first().subtitle, "Preto · 42")
        self.assertEqual(session.items.first().variant_sku, "RUNNER-PERSIST-BLK-42")

    def test_product_detail_post_creates_checkout_session_from_selected_variant(self):
        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"size": "42", "color": "wht"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("session_key=", response["Location"])
        self.assertIn("stage=cart", response["Location"])
        self.assertIn(urlencode({"back_url": f'{reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})}?size=42&color=wht'}), response["Location"])

        session = CheckoutSession.objects.order_by("-id").first()
        self.assertIsNotNone(session)
        self.assertEqual(session.items.first().subtitle, "Branco · 42")
        self.assertEqual(session.items.first().variant_sku, "RUNNER-PERSIST-WHT-42")

    def test_product_detail_post_reuses_open_session_and_adds_second_variant_item(self):
        first_response = self.client.post(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}))
        second_response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"size": "42", "color": "wht"},
        )

        first_session = CheckoutSession.objects.order_by("id").first()
        self.assertIsNotNone(first_session)
        self.assertIn(f"session_key={first_session.session_key}", first_response["Location"])
        self.assertIn(f"session_key={first_session.session_key}", second_response["Location"])
        self.assertEqual(CheckoutSession.objects.count(), 1)

        first_session.refresh_from_db()
        self.assertEqual(first_session.items.count(), 2)
        self.assertEqual(str(first_session.subtotal), "799.80")
        self.assertEqual(str(first_session.grand_total), "824.70")
        self.assertCountEqual(
            list(first_session.items.values_list("variant_sku", flat=True)),
            ["RUNNER-PERSIST-BLK-42", "RUNNER-PERSIST-WHT-42"],
        )

    def test_product_detail_post_reuses_open_session_and_increments_same_variant_quantity(self):
        self.client.post(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}))
        self.client.post(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}))

        session = CheckoutSession.objects.order_by("-id").first()
        self.assertIsNotNone(session)
        self.assertEqual(CheckoutSession.objects.count(), 1)
        self.assertEqual(session.items.count(), 1)
        item = session.items.first()
        self.assertEqual(item.variant_sku, "RUNNER-PERSIST-BLK-42")
        self.assertEqual(item.quantity, 2)
        self.assertEqual(str(session.subtotal), "799.80")
        self.assertEqual(str(session.grand_total), "824.70")

    def test_product_detail_post_redirects_back_to_selected_variant_when_it_is_out_of_stock(self):
        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"size": "43", "color": "blk"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            f'{reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})}?size=43&color=blk',
        )

    def test_product_detail_post_prefills_checkout_session_from_account_and_address_when_available(self):
        tenant = Tenant.objects.get(pk=1)
        customer = Customer.objects.create(
            tenant=tenant,
            slug="cliente-catalogo",
            reference="#9001",
            full_name="Ana Checkout",
            email="ana.checkout@hubx.market",
            phone="(11) 97777-0000",
            status="active",
            account_type="Storefront",
        )
        AccountProfile.objects.create(
            tenant=tenant,
            customer=customer,
            email="ana.checkout@hubx.market",
            first_name="Ana",
            last_name="Checkout",
            phone="(11) 97777-0000",
            is_active=True,
        )
        CustomerAddress.objects.create(
            customer=customer,
            label="Casa",
            recipient_name="Ana Checkout",
            line_1="Rua do Produto, 100",
            line_2="Apto 12",
            district="Centro",
            city="São Paulo",
            state="SP",
            postal_code="01010-000",
            is_default=True,
        )

        self.client.post(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}))

        session = CheckoutSession.objects.order_by("-id").first()
        self.assertEqual(session.first_name, "Ana")
        self.assertEqual(session.last_name, "Checkout")
        self.assertEqual(session.email, "ana.checkout@hubx.market")
        self.assertEqual(session.phone, "(11) 97777-0000")
        self.assertEqual(session.address_line_1, "Rua do Produto, 100")
        self.assertEqual(session.address_line_2, "Apto 12")
        self.assertEqual(session.city, "São Paulo")
        self.assertEqual(session.state, "SP")
        self.assertEqual(session.zip_code, "01010-000")

    def test_checkout_view_renders_multi_item_session_created_from_pdp(self):
        self.client.post(reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}))
        second_response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"size": "42", "color": "wht"},
        )

        session = CheckoutSession.objects.order_by("-id").first()
        self.assertIsNotNone(session)
        response = self.client.get(reverse("checkout:checkout-page"), {"session_key": str(session.session_key)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revise 2 item(ns) antes de concluir o pedido.")
        self.assertContains(response, "O pedido só é gerado quando a etapa atual estiver consistente.")
        self.assertContains(response, "Conferir entrega")
        self.assertContains(response, "Carrinho leve desta sessão")
        self.assertContains(response, "Preto · 42")
        self.assertContains(response, "Branco · 42")
        self.assertContains(response, "R$ 824,70")
        self.assertIn(f"session_key={session.session_key}", second_response["Location"])

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

        item = storefront_catalog_queries.get_product("produto-sem-imagem", tenant_id=tenant.id)

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

        item = storefront_catalog_queries.get_product("produto-coerente", tenant_id=tenant.id)

        self.assertEqual(item["main_image_url"], "https://cdn.hubx.market/demo/catalog/match-white.jpg")
        self.assertEqual(item["product_gallery_items"][0]["url"], "https://cdn.hubx.market/demo/catalog/match-white.jpg")
        self.assertIn("Branco · 41", item["stock_helper"])
        self.assertIn("Branco · 41", item["price_helper"])

    def test_storefront_variant_groups_reflect_real_variants_when_available(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido", tenant_id=self.tenant.id)

        self.assertEqual(product["variant_groups"][0]["variant"], "buttons")
        self.assertEqual(product["variant_groups"][1]["variant"], "swatches")
        self.assertTrue(any(option["out_of_stock"] for option in product["variant_groups"][0]["options"]))

    def test_storefront_catalog_list_orders_products_by_initial_conversion_priority(self):
        tenant = Tenant.objects.create(name="Ordering Lite", slug="ordering-lite", subdomain="ordering-lite")

        low_offer = Product.objects.create(
            tenant=tenant,
            name="Produto Low Offer",
            slug="produto-low-offer",
            brand_name="Hubx Rank",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=low_offer,
            sku="LOW-OFFER-BLK-40",
            price="199.90",
            compare_price="229.90",
            stock=2,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        in_offer = Product.objects.create(
            tenant=tenant,
            name="Produto In Offer",
            slug="produto-in-offer",
            brand_name="Hubx Rank",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=in_offer,
            sku="IN-OFFER-WHT-41",
            price="209.90",
            compare_price="249.90",
            stock=8,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        in_regular = Product.objects.create(
            tenant=tenant,
            name="Produto In Regular",
            slug="produto-in-regular",
            brand_name="Hubx Rank",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=in_regular,
            sku="IN-REG-GRY-41",
            price="189.90",
            stock=10,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        backorder = Product.objects.create(
            tenant=tenant,
            name="Produto Backorder",
            slug="produto-backorder",
            brand_name="Hubx Rank",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=backorder,
            sku="BACK-NAV-42",
            price="219.90",
            stock=0,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=True,
            is_default=True,
        )

        out = Product.objects.create(
            tenant=tenant,
            name="Produto Out",
            slug="produto-out",
            brand_name="Hubx Rank",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=out,
            sku="OUT-RED-39",
            price="179.90",
            stock=0,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        draft = Product.objects.create(
            tenant=tenant,
            name="Produto Draft",
            slug="produto-draft",
            brand_name="Hubx Rank",
            category_label="Calçados esportivos",
            status="draft",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=draft,
            sku="DRAFT-BLK-38",
            price="149.90",
            stock=6,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        products = storefront_catalog_queries.list_products(tenant_id=tenant.id)
        ordered_slugs = [product["slug"] for product in products]

        self.assertLess(ordered_slugs.index("produto-low-offer"), ordered_slugs.index("produto-in-offer"))
        self.assertLess(ordered_slugs.index("produto-in-offer"), ordered_slugs.index("produto-in-regular"))
        self.assertLess(ordered_slugs.index("produto-in-regular"), ordered_slugs.index("produto-backorder"))
        self.assertLess(ordered_slugs.index("produto-backorder"), ordered_slugs.index("produto-out"))
        self.assertLess(ordered_slugs.index("produto-out"), ordered_slugs.index("produto-draft"))

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

        item = storefront_catalog_queries.get_product("produto-sob-encomenda", tenant_id=tenant.id)

        self.assertEqual(item["stock_state"], "backorder")
        self.assertEqual(item["stock_label"], "Sob encomenda")
        self.assertEqual(item["primary_action_label"], "Reservar e ir para checkout")
        self.assertEqual(item["badge_label"], "Sob encomenda")
        self.assertEqual(item["secondary_action_label"], "Ir para checkout")
        self.assertEqual(item["catalog_card_availability_note"], "Marinho · 40 disponível por encomenda.")
        self.assertEqual(item["catalog_card_curation_note"], "")
        self.assertEqual(item["catalog_card_decision_signal"], "reserva_planejada")
        self.assertIn("confirmar o prazo da reserva", item["catalog_card_click_helper"])
        self.assertIn("Variante disponível por encomenda · Marinho · 40", item["stock_helper"])
        self.assertIn("reflete Marinho · 40", item["availability_note"])
        self.assertIn("já pode seguir para checkout como reserva", item["cta_helper"])
        self.assertIn("decisão de compra previsível", item["cta_helper"])
        self.assertIn("Produto disponível por encomenda · Marinho · 40", item["purchase_note"])
        self.assertIn("combinação comprável", item["purchase_note"])
        self.assertIn("já pode seguir para checkout", item["purchase_note"])

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

        item = storefront_catalog_queries.get_product("produto-sem-estoque", tenant_id=tenant.id)

        self.assertEqual(item["stock_state"], "out_of_stock")
        self.assertEqual(item["stock_label"], "Sem estoque")
        self.assertEqual(item["primary_action_label"], "Avise-me da reposição")
        self.assertTrue(item["primary_action_disabled"])
        self.assertEqual(item["secondary_action_label"], "Ver catálogo")
        self.assertEqual(item["secondary_action_target"], "catalog")
        self.assertEqual(item["badge_label"], "Reposição em acompanhamento · Vermelho · 39")
        self.assertEqual(item["catalog_card_availability_note"], "Vermelho · 39 indisponível no momento.")
        self.assertEqual(item["catalog_card_curation_note"], "")
        self.assertEqual(item["catalog_card_decision_signal"], "acompanhar_reposicao")
        self.assertIn("acompanhar a reposição", item["catalog_card_click_helper"])
        self.assertIn("Variante indisponível no momento · Vermelho · 39", item["stock_helper"])
        self.assertIn("está sem estoque no momento", item["availability_note"])
        self.assertIn("não segue para checkout agora", item["cta_helper"])
        self.assertIn("acompanhar a reposição com tranquilidade", item["cta_helper"])
        self.assertIn("próximo passo mais seguro é acompanhar a reposição ou voltar ao catálogo", item["purchase_note"])

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

        item = storefront_catalog_queries.get_product("produto-ultimas-unidades", tenant_id=tenant.id)

        self.assertEqual(item["stock_label"], "Estoque baixo")
        self.assertEqual(item["badge_label"], "Últimas unidades · Preto · 38")
        self.assertEqual(item["badge_variant"], "warning")
        self.assertEqual(item["catalog_card_availability_note"], "Preto · 38 com 2 unidade(s) pronta(s) para envio.")
        self.assertEqual(item["catalog_card_curation_note"], "Oferta em evidência nesta vitrine, pronta para uma decisão rápida.")
        self.assertEqual(item["catalog_card_decision_signal"], "decisao_rapida_com_oferta")
        self.assertIn("uma das mais fortes da vitrine", item["catalog_card_click_helper"])
        self.assertIn("2 unidade(s) pronta(s) para envio imediato", item["availability_note"])
        self.assertIn("poucas unidades restantes", item["cta_helper"])
        self.assertIn("Poucas unidades disponíveis · Preto · 38", item["purchase_note"])
        self.assertIn("compra rápida para Preto · 38", item["price_helper"])
        self.assertEqual(item["catalog_card_meta"], "SKU SPRINT-BLK-38 · saída rápida")
        self.assertIn("economia pronta para checkout", item["catalog_card_price_helper"])
