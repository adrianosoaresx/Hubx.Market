from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from urllib.parse import urlencode

from app.modules.accounts.models import AccountProfile
from app.modules.cart.models import Cart, CartItem, CartMutation
from app.modules.catalog.models import Product, ProductVariant, StorefrontDiscoveryEventLog
from app.modules.catalog.application.storefront_catalog_queries import storefront_catalog_queries
from app.modules.catalog.application.storefront_discovery_analytics import (
    DjangoStorefrontDiscoveryEventLogPublisher,
    NoopStorefrontDiscoveryAnalyticsPublisher,
    StorefrontDiscoveryEvent,
    storefront_discovery_analytics,
)
from app.modules.checkout.models import CheckoutSession
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.reviews.models import ProductReview
from app.modules.tenants.models import Tenant


def _create_storefront_product(
    tenant: Tenant,
    *,
    name: str,
    slug: str,
    sku: str,
    brand_name: str = "Hubx",
    category_label: str = "Catálogo",
    description: str = "",
    status: str = Product.Status.ACTIVE,
    is_active: bool = True,
    is_featured: bool = False,
    price: str = "99.90",
    compare_price: str | None = None,
    stock: int = 10,
    reserved_stock: int = 0,
    allow_backorder: bool = False,
) -> Product:
    product = Product.objects.create(
        tenant=tenant,
        name=name,
        slug=slug,
        brand_name=brand_name,
        category_label=category_label,
        description=description,
        status=status,
        is_active=is_active,
        is_featured=is_featured,
    )
    ProductVariant.objects.create(
        product=product,
        sku=sku,
        label="Padrão",
        price=price,
        compare_price=compare_price,
        stock=stock,
        reserved_stock=reserved_stock,
        allow_backorder=allow_backorder,
        is_default=True,
        is_active=True,
    )
    return product


def _seed_storefront_catalog(tenant: Tenant, *, sku_prefix: str = "") -> None:
    _create_storefront_product(
        tenant,
        name="Tênis Hubx Runner",
        slug="tenis-hubx-runner",
        sku=f"{sku_prefix}RUNNER-001-BLK-42",
        brand_name="Hubx",
        category_label="Calçados esportivos",
        description="Produto com catálogo publicado, mídia aprovada e variante principal preta 42 ativa para venda.",
        status=Product.Status.ACTIVE,
        is_active=True,
        is_featured=True,
        price="299.90",
        compare_price="349.90",
        stock=24,
        reserved_stock=4,
    )
    _create_storefront_product(
        tenant,
        name="Camiseta Hubx Performance",
        slug="camiseta-hubx-performance",
        sku=f"{sku_prefix}TSHIRT-010-WHT-M",
        brand_name="Hubx",
        category_label="Vestuário",
        description="Modelo técnico para treinos com tecido leve e respirável.",
        status=Product.Status.DRAFT,
        is_active=False,
        is_featured=False,
        price="129.90",
        compare_price="149.90",
        stock=58,
        reserved_stock=6,
    )
    _create_storefront_product(
        tenant,
        name="Mochila Hubx Urban",
        slug="mochila-hubx-urban",
        sku=f"{sku_prefix}BAG-204-GRY-U",
        brand_name="Hubx",
        category_label="Acessórios",
        description="Mochila urbana com compartimento acolchoado para notebook.",
        status=Product.Status.INACTIVE,
        is_active=False,
        is_featured=False,
        price="199.90",
        compare_price="219.90",
        stock=0,
        reserved_stock=0,
        allow_backorder=True,
    )


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class StorefrontViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Storefront Demo",
            slug="hubx-storefront-demo",
            subdomain="hubx-storefront-demo",
        )
        _seed_storefront_catalog(self.tenant)
        self.storefront_host = f"{self.tenant.subdomain}.hubx.market"
        self.client.defaults["HTTP_HOST"] = self.storefront_host

    def tearDown(self):
        storefront_discovery_analytics.publisher = NoopStorefrontDiscoveryAnalyticsPublisher()

    def test_storefront_home_view_renders_home_template(self):
        response = self.client.get(reverse("storefront-home"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/home_page.html")
        self.assertContains(response, "Hubx Storefront Demo")
        self.assertContains(response, 'href="/"')
        self.assertContains(response, 'href="/catalog/"')
        self.assertNotContains(response, 'href="/cart/"')
        self.assertNotContains(response, "Carrinho")
        self.assertNotContains(response, '<a href="/accounts/account/" class="storefront-side-nav-link')
        self.assertNotContains(response, '<a href="/accounts/account/orders/" class="storefront-side-nav-link')
        self.assertContains(response, "Produtos para começar")
        self.assertContains(response, "Entrar")
        self.assertNotContains(response, "/plans/")
        self.assertNotContains(response, "/demo/")

    def test_storefront_home_renders_tenant_institutional_hero(self):
        self.tenant.storefront_hero_title = "Destaques da estação"
        self.tenant.storefront_hero_description = "Uma curadoria institucional exclusiva desta loja."
        self.tenant.storefront_hero_image_url = "https://cdn.example.com/store/hero.jpg"
        self.tenant.storefront_hero_cta_label = "Explorar vitrine"
        self.tenant.storefront_hero_cta_href = "/catalog/?quick_filter=featured"
        self.tenant.save()

        response = self.client.get(reverse("storefront-home"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "storefront-institutional-hero")
        self.assertContains(response, "Destaques da estação")
        self.assertContains(response, "Uma curadoria institucional exclusiva desta loja.")
        self.assertContains(response, "https://cdn.example.com/store/hero.jpg")
        self.assertContains(response, "Explorar vitrine")
        self.assertContains(response, 'href="/catalog/?quick_filter=featured"')

    def test_storefront_home_uses_tenant_hero_image_for_social_preview(self):
        self.tenant.storefront_hero_title = "Móveis rústicos com história"
        self.tenant.storefront_hero_description = "Peças selecionadas para ambientes com presença."
        self.tenant.storefront_hero_image_url = "https://cdn.example.com/arnaldo/share.jpg"
        self.tenant.save(
            update_fields=[
                "storefront_hero_title",
                "storefront_hero_description",
                "storefront_hero_image_url",
            ]
        )

        response = self.client.get(reverse("storefront-home"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta property="og:image" content="https://cdn.example.com/arnaldo/share.jpg">')
        self.assertContains(response, '<meta name="twitter:image" content="https://cdn.example.com/arnaldo/share.jpg">')
        self.assertContains(response, '<meta property="og:title" content="Móveis rústicos com história">')
        self.assertContains(response, '<meta property="og:url" content="http://hubx-storefront-demo.hubx.market/">')

    def test_catalog_list_social_preview_falls_back_to_tenant_scoped_product_image(self):
        product = Product.objects.get(tenant=self.tenant, slug="tenis-hubx-runner")
        product.images.create(
            image_url="/media/catalog/runner-share.jpg",
            alt_text="Tênis Hubx Runner em destaque",
            position=1,
            is_primary=True,
        )

        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<meta property="og:image" content="http://hubx-storefront-demo.hubx.market/media/catalog/runner-share.jpg">',
        )
        self.assertContains(response, '<link rel="canonical" href="http://hubx-storefront-demo.hubx.market/catalog/">')

    def test_storefront_shell_renders_configured_tenant_logo(self):
        self.tenant.logo_url = "https://cdn.example.com/store/logo.png"
        self.tenant.save(update_fields=["logo_url"])

        response = self.client.get(reverse("storefront-home"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "https://cdn.example.com/store/logo.png")
        self.assertContains(response, "brand-identity-logo")

    def test_central_home_view_renders_public_entrypoints_without_platform_links(self):
        response = self.client.get(reverse("storefront-home"), HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/portal_home_page.html")
        self.assertContains(response, "Crie sua loja virtual com uma operação pronta para vender.")
        self.assertContains(response, "Iniciar onboarding")
        self.assertContains(response, "Loja por subdomínio")
        self.assertContains(response, 'href="/accounts/login/"')
        self.assertContains(response, 'href="/plans/"')
        self.assertContains(response, 'href="/plans/#aquisicao"')
        self.assertContains(response, 'href="/demo/"')
        self.assertContains(response, "Acessar demo")
        self.assertNotContains(response, "Entrar no portal")
        self.assertNotContains(response, "/ops/platform/")

    def test_public_demo_renders_profile_choice_for_active_demo_tenant(self):
        Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo", is_active=True)

        response = self.client.get(reverse("public-demo"), HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/public_demo_access_page.html")
        self.assertContains(response, "Escolha como deseja acessar a loja demo.")
        self.assertContains(response, "Admin da loja")
        self.assertContains(response, "Cliente da loja")
        self.assertContains(response, "admin@hubx-demo.market")
        self.assertContains(response, "cliente@hubx-demo.market")
        storefront_query = urlencode({"return_url": "http://hubx.market/demo/"}).replace("&", "&amp;")
        admin_query = urlencode({"profile": "admin", "return_url": "http://hubx.market/demo/"}).replace("&", "&amp;")
        customer_query = urlencode({"profile": "customer", "return_url": "http://hubx.market/demo/"}).replace("&", "&amp;")
        self.assertContains(response, f"http://hubx-demo.hubx.market/?{storefront_query}")
        self.assertContains(response, f"http://hubx-demo.hubx.market/accounts/demo-session/?{admin_query}")
        self.assertContains(response, f"http://hubx-demo.hubx.market/accounts/demo-session/?{customer_query}")

    @override_settings(
        HUBX_MARKET_ROOT_DOMAIN="hubx.market",
        HUBX_MARKET_PUBLIC_PORT="",
        ALLOWED_HOSTS=[".localhost", "localhost", "testserver"],
    )
    def test_public_demo_profile_links_use_localhost_request_host(self):
        Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo", is_active=True)

        response = self.client.get(reverse("public-demo"), HTTP_HOST="localhost:8002")

        self.assertEqual(response.status_code, 200)
        storefront_query = urlencode({"return_url": "http://localhost:8002/demo/"}).replace("&", "&amp;")
        admin_query = urlencode({"profile": "admin", "return_url": "http://localhost:8002/demo/"}).replace("&", "&amp;")
        customer_query = urlencode({"profile": "customer", "return_url": "http://localhost:8002/demo/"}).replace("&", "&amp;")
        self.assertContains(response, f"http://hubx-demo.localhost:8002/?{storefront_query}")
        self.assertContains(response, f"http://hubx-demo.localhost:8002/accounts/demo-session/?{admin_query}")
        self.assertContains(response, f"http://hubx-demo.localhost:8002/accounts/demo-session/?{customer_query}")

    @override_settings(
        HUBX_MARKET_ROOT_DOMAIN="hubx.market",
        HUBX_MARKET_PUBLIC_PORT="",
        ALLOWED_HOSTS=["127.0.0.1", ".localhost", "localhost", "testserver"],
    )
    def test_public_demo_profile_links_preserve_127_return_host(self):
        Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo", is_active=True)

        response = self.client.get(reverse("public-demo"), HTTP_HOST="127.0.0.1:8002")

        self.assertEqual(response.status_code, 200)
        storefront_query = urlencode({"return_url": "http://127.0.0.1:8002/demo/"}).replace("&", "&amp;")
        admin_query = urlencode({"profile": "admin", "return_url": "http://127.0.0.1:8002/demo/"}).replace("&", "&amp;")
        self.assertContains(response, f"http://hubx-demo.localhost:8002/?{storefront_query}")
        self.assertContains(response, f"http://hubx-demo.localhost:8002/accounts/demo-session/?{admin_query}")

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="missing-demo")
    def test_public_demo_returns_404_for_missing_demo_tenant(self):
        response = self.client.get(reverse("public-demo"), HTTP_HOST="hubx.market")

        self.assertEqual(response.status_code, 404)

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_demo_storefront_uses_demo_theme_logo_and_read_only_banner(self):
        Tenant.objects.create(name="Hubx Market Demo", slug="hubx-demo", subdomain="hubx-demo", is_active=True)

        response = self.client.get(reverse("storefront-home"), HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-tenant="hubx-demo"')
        self.assertContains(response, "hubx-logo-gold.png")
        self.assertContains(response, "Demo somente leitura")
        self.assertContains(response, "Ações de compra, cadastro e edição ficam bloqueadas")
        self.assertContains(response, "storefront-topbar")
        self.assertContains(response, 'aria-label="Navegação da loja"')
        self.assertContains(response, "Carrinho")
        self.assertContains(response, 'href="/cart/?demo_flow=cart"')
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertContains(response, "Sair")
        self.assertNotContains(response, 'href="/accounts/login/"')

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_demo_storefront_logout_form_preserves_return_url(self):
        Tenant.objects.create(name="Hubx Market Demo", slug="hubx-demo", subdomain="hubx-demo", is_active=True)
        return_url = "http://hubx.market/demo/"

        response = self.client.get(
            reverse("storefront-home"),
            {"return_url": return_url},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertContains(response, f'name="return_url" value="{return_url}"')
        self.assertNotContains(response, 'href="/accounts/login/"')

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_demo_product_detail_links_to_simulated_purchase_flow(self):
        demo_tenant = Tenant.objects.create(
            name="Hubx Market Demo",
            slug="hubx-demo",
            subdomain="hubx-demo",
            is_active=True,
        )
        _seed_storefront_catalog(demo_tenant, sku_prefix="DEMO-")

        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}),
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Simular carrinho")
        self.assertContains(response, "Simular checkout")
        self.assertContains(response, 'href="/cart/?demo_flow=cart"')
        self.assertContains(response, 'href="/checkout/?demo_flow=checkout&amp;stage=review"')
        self.assertContains(response, "nenhuma alteração é gravada")
        self.assertNotContains(response, "compras e edições estão bloqueadas")

    def test_storefront_navbar_shows_logout_for_authenticated_user(self):
        user = get_user_model().objects.create_user(
            username="navbar.customer@hubx.market",
            email="navbar.customer@hubx.market",
            password="secret-pass",
        )
        self.client.force_login(user)

        response = self.client.get(reverse("storefront-home"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'action="/accounts/logout/"')
        self.assertContains(response, "Sair")
        self.assertContains(response, 'href="/cart/"')
        self.assertContains(response, "Carrinho")
        self.assertContains(response, '<a href="/accounts/account/" class="storefront-side-nav-link')
        self.assertContains(response, '<a href="/accounts/account/orders/" class="storefront-side-nav-link')
        self.assertNotContains(response, '<a href="/accounts/login/" class="rounded-lg')

    def test_catalog_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/catalog_page.html")
        self.assertContains(response, "Loja")
        self.assertContains(response, "storefront-topbar")
        self.assertContains(response, 'aria-label="Navegação da loja"')
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Explore a loja, compare opções disponíveis")
        self.assertNotContains(response, "curadoria leve")

    def test_catalog_list_view_exposes_infinite_scroll_product_fragment(self):
        for index in range(10):
            product = Product.objects.create(
                tenant=self.tenant,
                name=f"Produto Scroll {index:02d}",
                slug=f"produto-scroll-{index:02d}",
                brand_name="Hubx",
                category_label="Acessórios",
                description="Produto criado para validar a paginação progressiva.",
                status=Product.Status.ACTIVE,
                is_active=True,
            )
            ProductVariant.objects.create(
                product=product,
                sku=f"SCROLL-{index:02d}-UN",
                label="Único",
                price="99.90",
                stock=10,
                is_default=True,
                is_active=True,
            )

        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/catalog_page.html")
        self.assertContains(response, "storefront-product-load-more")
        self.assertContains(response, 'hx-trigger="revealed"')
        self.assertContains(response, "fragment=products")

        fragment_response = self.client.get(
            reverse("storefront:catalog-list"),
            {"page": 2, "fragment": "products"},
            HTTP_HOST=self.storefront_host,
            HTTP_HX_REQUEST="true",
        )

        self.assertEqual(fragment_response.status_code, 200)
        self.assertTemplateUsed(fragment_response, "pages/partials/catalog_product_page.html")
        self.assertContains(fragment_response, "Produto Scroll")
        self.assertNotContains(fragment_response, "storefront-catalog-meta")

    def test_catalog_list_view_applies_search_filter(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "mochila"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mochila Hubx Urban")
        self.assertNotContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "busca atual: “mochila”")
        self.assertContains(response, "Resultados para “mochila”")
        self.assertContains(response, "produtos que mais combinam com sua busca")

    def test_catalog_list_view_search_matches_category_without_accents(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "acessorios"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mochila Hubx Urban")
        self.assertNotContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "nome, marca, categoria e descrição dos produtos")

    def test_catalog_list_view_search_matches_description_terms(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "tecido respiravel"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Camiseta Hubx Performance")
        self.assertNotContains(response, "Mochila Hubx Urban")

    def test_catalog_list_view_search_matches_public_card_terms(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "preto 42"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertNotContains(response, "Mochila Hubx Urban")

    def test_catalog_list_view_applies_category_context(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"category": "calcados"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "categoria atual: Calçados")
        self.assertContains(response, "Explore produtos de calçados")
        self.assertContains(response, "Use a categoria atual para ver produtos de calçados")

    def test_catalog_list_view_shows_search_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"q": "nada-aqui"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto encontrado para esta busca")
        self.assertContains(response, "Não encontramos resultados para “nada-aqui”")
        self.assertContains(response, "em nome, marca, categoria ou descrição")

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
        self.assertContains(response, "produtos em destaque da loja")
        self.assertContains(response, "produtos selecionados para aparecer primeiro na vitrine")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Oferta")
        self.assertContains(response, "Comprar")

    def test_catalog_list_view_applies_quick_filter_quick_buy(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "quick_buy"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro rápido ativo: Compra rápida")
        self.assertContains(response, "produtos disponíveis para comprar com menos passos")
        self.assertContains(response, "itens disponíveis agora ou com poucas unidades")
        self.assertContains(response, "Use Limpar para voltar à vitrine completa")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Pronta entrega")
        self.assertContains(response, "Comprar")
        self.assertContains(response, "Produtos disponíveis para você conferir os detalhes")

    def test_catalog_list_view_applies_quick_filter_offer(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "offer"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Filtro rápido ativo: Em oferta")
        self.assertContains(response, "ofertas disponíveis agora")
        self.assertContains(response, "preço promocional visível na vitrine")
        self.assertContains(response, "Tênis Hubx Runner")
        self.assertContains(response, "Oferta ativa")
        self.assertContains(response, "Comprar")
        self.assertContains(response, "Use Limpar para voltar à vitrine completa")

    def test_catalog_list_view_applies_availability_facet(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"availability": "backorder"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Disponibilidade")
        self.assertContains(response, "facets: disponibilidade: Sob encomenda")
        self.assertContains(response, "Mochila Hubx Urban")
        self.assertNotContains(response, "Tênis Hubx Runner")

    def test_catalog_list_view_applies_price_facets(self):
        response = self.client.get(
            reverse("storefront:catalog-list"),
            {"price_min": "150", "price_max": "250"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preço mín.")
        self.assertContains(response, "Preço máx.")
        self.assertContains(response, "preço mínimo: R$ 150,00")
        self.assertContains(response, "preço máximo: R$ 250,00")
        self.assertContains(response, "Mochila Hubx Urban")
        self.assertNotContains(response, "Tênis Hubx Runner")

    def test_catalog_list_view_applies_offer_facet(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"offer": "1"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Somente ofertas")
        self.assertContains(response, "facets: somente ofertas")
        self.assertIsNone(response.context["next_url"])

    def test_catalog_list_view_ignores_invalid_facet_values(self):
        response = self.client.get(
            reverse("storefront:catalog-list"),
            {"availability": "all", "price_min": "-10", "price_max": "abc"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "facets:")
        self.assertEqual(
            [product["title"] for product in response.context["products"]],
            ["Tênis Hubx Runner", "Mochila Hubx Urban", "Camiseta Hubx Performance"],
        )

    def test_catalog_list_view_records_discovery_analytics_events(self):
        class SpyPublisher:
            def __init__(self):
                self.events = []

            def publish(self, event):
                self.events.append(event)

        spy = SpyPublisher()
        storefront_discovery_analytics.publisher = spy

        response = self.client.get(
            reverse("storefront:catalog-list"),
            {
                "q": "runner",
                "category": "calcados",
                "availability": "in_stock",
                "offer": "1",
                "price_min": "100",
                "sort": "price_desc",
            },
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [event.name for event in spy.events],
            [
                "catalog.discovery_viewed",
                "catalog.search_performed",
                "catalog.facets_applied",
                "catalog.sort_changed",
            ],
        )
        payload = spy.events[0].payload
        self.assertEqual(payload["tenant_id"], self.tenant.id)
        self.assertEqual(payload["query"], "runner")
        self.assertEqual(payload["category"], "calcados")
        self.assertEqual(payload["availability"], "in_stock")
        self.assertTrue(payload["offer"])
        self.assertEqual(payload["price_min"], "100")
        self.assertEqual(payload["sort"], "price_desc")
        self.assertEqual(payload["result_count"], 1)

    def test_catalog_list_view_does_not_block_when_discovery_analytics_fails(self):
        class FailingPublisher:
            def publish(self, event):
                raise RuntimeError("analytics unavailable")

        storefront_discovery_analytics.publisher = FailingPublisher()

        response = self.client.get(reverse("storefront:catalog-list"), {"q": "runner"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tênis Hubx Runner")

    def test_product_detail_view_records_discovery_analytics_event(self):
        class SpyPublisher:
            def __init__(self):
                self.events = []

            def publish(self, event):
                self.events.append(event)

        spy = SpyPublisher()
        storefront_discovery_analytics.publisher = spy

        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}),
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual([event.name for event in spy.events], ["catalog.product_detail_viewed"])
        self.assertEqual(spy.events[0].payload["tenant_id"], self.tenant.id)
        self.assertEqual(spy.events[0].payload["product_slug"], "tenis-hubx-runner")

    def test_discovery_analytics_persistent_publisher_stores_sanitized_event(self):
        publisher = DjangoStorefrontDiscoveryEventLogPublisher()

        publisher.publish(
            StorefrontDiscoveryEvent(
                name="catalog.discovery_viewed",
                payload={
                    "tenant_id": self.tenant.id,
                    "session_key": "raw-session-key",
                    "path": "/catalog/",
                    "query": "runner",
                    "result_count": 1,
                    "email": "customer@example.com",
                },
            )
        )

        event_log = StorefrontDiscoveryEventLog.objects.get()
        self.assertEqual(event_log.tenant, self.tenant)
        self.assertEqual(event_log.event_name, "catalog.discovery_viewed")
        self.assertEqual(event_log.path, "/catalog/")
        self.assertEqual(len(event_log.session_key_hash), 40)
        self.assertNotEqual(event_log.session_key_hash, "raw-session-key")
        self.assertEqual(event_log.payload["query"], "runner")
        self.assertEqual(event_log.payload["result_count"], 1)
        self.assertNotIn("email", event_log.payload)
        self.assertNotIn("session_key", event_log.payload)

    def test_discovery_analytics_persistent_publisher_discards_missing_tenant(self):
        publisher = DjangoStorefrontDiscoveryEventLogPublisher()

        publisher.publish(
            StorefrontDiscoveryEvent(
                name="catalog.discovery_viewed",
                payload={"tenant_id": None, "path": "/catalog/", "query": "runner"},
            )
        )

        self.assertFalse(StorefrontDiscoveryEventLog.objects.exists())

    @override_settings(HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="hubx-demo")
    def test_discovery_analytics_skips_demo_tenant_read_only(self):
        demo_tenant = Tenant.objects.create(name="Hubx Demo", slug="hubx-demo", subdomain="hubx-demo", is_active=True)

        storefront_discovery_analytics.record_listing_view(
            tenant_id=demo_tenant.id,
            session_key="demo-session",
            path="/catalog/",
            query="runner",
            result_count=1,
        )

        self.assertFalse(StorefrontDiscoveryEventLog.objects.filter(tenant=demo_tenant).exists())

    def test_catalog_list_view_applies_public_sort_by_lowest_price(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"sort": "price_asc"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ordenar por")
        self.assertContains(response, "ordenação: Menor preço")
        self.assertEqual(
            [product["title"] for product in response.context["products"]],
            ["Camiseta Hubx Performance", "Mochila Hubx Urban", "Tênis Hubx Runner"],
        )

    def test_catalog_list_view_applies_public_sort_by_highest_price(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"sort": "price_desc"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ordenação: Maior preço")
        self.assertEqual(
            [product["title"] for product in response.context["products"]],
            ["Tênis Hubx Runner", "Mochila Hubx Urban", "Camiseta Hubx Performance"],
        )

    def test_catalog_list_view_applies_public_sort_by_name(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"sort": "name_asc"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "ordenação: Nome A-Z")
        self.assertEqual(
            [product["title"] for product in response.context["products"]],
            ["Camiseta Hubx Performance", "Mochila Hubx Urban", "Tênis Hubx Runner"],
        )
        self.assertIsNone(response.context["next_url"])

    def test_catalog_list_view_falls_back_to_recommended_for_invalid_sort(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"sort": "rating_desc"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "ordenação: rating_desc")
        self.assertEqual(
            [product["title"] for product in response.context["products"]],
            ["Tênis Hubx Runner", "Mochila Hubx Urban", "Camiseta Hubx Performance"],
        )

    def test_catalog_list_view_shows_quick_filter_empty_state_for_backorder(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "backorder", "q": "runner"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto sob encomenda")
        self.assertContains(response, "Não há produtos sob encomenda nesta visão. Use Limpar")

    def test_catalog_list_view_shows_quick_buy_empty_state_guidance(self):
        response = self.client.get(reverse("storefront:catalog-list"), {"quick_filter": "quick_buy", "q": "mochila"}, HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum produto pronto para compra rápida")
        self.assertContains(response, "Não há produtos disponíveis para compra rápida neste recorte")

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
        self.assertContains(response, "Adicionar ao carrinho")
        self.assertContains(response, "Comprar agora")

    def test_storefront_catalog_query_service_returns_expected_contract(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner", tenant_id=self.tenant.id)
        products = storefront_catalog_queries.list_products(tenant_id=self.tenant.id)

        self.assertEqual(product["slug"], "tenis-hubx-runner")
        self.assertEqual(product["brand"], "Hubx")
        self.assertIsInstance(product["discovery_rank_score"], int)
        self.assertGreater(product["discovery_rank_score"], 0)
        self.assertEqual(
            set(product["discovery_rank_components"]),
            {"status", "stock", "offer", "featured", "decision_signal"},
        )
        self.assertTrue(product["discovery_rank_reason"])
        self.assertTrue(any(item["slug"] == "tenis-hubx-runner" for item in products))

    def test_storefront_catalog_query_service_orders_persisted_products_by_discovery_score(self):
        products = storefront_catalog_queries.list_products(tenant_id=self.tenant.id)

        self.assertEqual(
            [product["slug"] for product in products],
            ["tenis-hubx-runner", "mochila-hubx-urban", "camiseta-hubx-performance"],
        )
        self.assertEqual(
            [product["discovery_rank_score"] for product in products],
            sorted([product["discovery_rank_score"] for product in products], reverse=True),
        )

    def test_empty_storefront_tenant_does_not_use_demo_fallback_products(self):
        empty_tenant = Tenant.objects.create(
            name="Loja Vazia",
            slug="loja-vazia",
            subdomain="loja-vazia",
        )

        products = storefront_catalog_queries.list_products(tenant_id=empty_tenant.id)
        product = storefront_catalog_queries.get_product("tenis-hubx-runner", tenant_id=empty_tenant.id)
        list_response = self.client.get(
            reverse("storefront:catalog-list"),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )
        detail_response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )

        self.assertEqual(products, [])
        self.assertEqual(product, {})
        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "Tênis Hubx Runner")
        self.assertNotContains(list_response, "Mochila Hubx Urban")
        self.assertEqual(detail_response.status_code, 404)

    def test_storefront_views_require_resolved_tenant(self):
        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST="ghost.hubx.market")

        self.assertEqual(response.status_code, 404)


@override_settings(
    ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"],
    HUBX_MARKET_DEMO_TENANT_SUBDOMAIN="official-demo",
)
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
        self.assertIsInstance(product["discovery_rank_score"], int)
        self.assertEqual(product["discovery_rank_components"]["status"], 1000)
        self.assertIn("oferta", product["discovery_rank_reason"])
        self.assertEqual(product["price"], "399.90")
        self.assertEqual(product["compare_price"], "449.90")
        self.assertEqual(product["stock_state"], "in_stock")
        self.assertEqual(product["stock_label"], "Em estoque")
        self.assertEqual(product["stock_helper"], "Pronta entrega")
        self.assertEqual(product["price_helper"], "Oferta ativa com parcelamento disponível")
        self.assertEqual(product["effective_variant_summary"], "")
        self.assertEqual(product["availability_note"], "Disponível para compra.")
        self.assertIn("preservados no checkout", product["cta_helper"])
        self.assertEqual(product["eyebrow"], "Hubx Persisted")
        self.assertEqual(product["primary_action_label"], "Ir para checkout")
        self.assertFalse(product["primary_action_disabled"])
        self.assertEqual(product["secondary_action_label"], "Ir para checkout")
        self.assertEqual(product["secondary_action_target"], "checkout")
        self.assertEqual(product["badge_label"], "Oferta")
        self.assertEqual(product["badge_variant"], "success")
        self.assertEqual(product["product_gallery_items"][0]["url"], "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertEqual(product["main_image_url"], "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")
        self.assertEqual(product["main_image_alt"], "Tênis Hubx Runner Persistido · imagem principal")
        self.assertEqual(product["variant_groups"][0]["selected"], "42")

    def test_storefront_query_service_orders_persisted_records_by_discovery_score(self):
        backorder_product = Product.objects.create(
            tenant=self.tenant,
            name="Mochila Persistida Backorder",
            slug="mochila-persistida-backorder",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductVariant.objects.create(
            product=backorder_product,
            sku="BAG-PERSIST-BACKORDER",
            price="199.90",
            compare_price="249.90",
            stock=0,
            allow_backorder=True,
        )
        draft_product = Product.objects.create(
            tenant=self.tenant,
            name="Camiseta Persistida Draft",
            slug="camiseta-persistida-draft",
            status=Product.Status.DRAFT,
            is_active=False,
        )
        ProductVariant.objects.create(
            product=draft_product,
            sku="TSHIRT-PERSIST-DRAFT",
            price="99.90",
            compare_price="149.90",
            stock=10,
        )

        products = storefront_catalog_queries.list_products(tenant_id=self.tenant.id)
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido", tenant_id=self.tenant.id)

        self.assertEqual(
            [product["slug"] for product in products],
            [
                "tenis-hubx-runner-persistido",
                "mochila-persistida-backorder",
                "camiseta-persistida-draft",
            ],
        )
        self.assertEqual(
            [product["discovery_rank_score"] for product in products],
            sorted([product["discovery_rank_score"] for product in products], reverse=True),
        )
        self.assertEqual(product["purchase_note"], "Selecione a opção desejada e avance com segurança.")
        self.assertEqual(product["product_subtitle"], "Produto persistido de demonstração para validar a primeira leitura real do catálogo.")
        self.assertEqual(product["short_description"], "Produto persistido de demonstração para validar a primeira leitura real do catálogo.")
        self.assertEqual(product["variant_groups"][0]["label"], "Tamanho disponível")
        self.assertEqual(product["variant_groups"][0]["help_text"], "Preço e estoque exibidos refletem a variante padrão Preto · 42.")
        self.assertEqual([option["value"] for option in product["variant_groups"][0]["options"]], ["42", "43"])
        self.assertEqual([option["label"] for option in product["variant_groups"][1]["options"]], ["Preto", "Branco"])
        self.assertEqual(product["variant_groups"][1]["help_text"], "A mídia principal e os textos comerciais priorizam Preto · 42.")
        self.assertEqual(product["catalog_card_subtitle"], "Calçados esportivos")
        self.assertEqual(product["catalog_card_meta"], "Oferta ativa")
        self.assertEqual(product["catalog_card_price_helper"], "Oferta ativa")
        self.assertEqual(product["catalog_card_variant_summary"], "")
        self.assertEqual(product["catalog_card_curation_note"], "")
        self.assertEqual(product["catalog_card_decision_signal"], "oferta_editorial")
        self.assertEqual(product["catalog_card_availability_note"], "Pronta entrega")
        self.assertEqual(product["catalog_card_click_helper"], "")
        self.assertIn("preservados no checkout", product["cta_helper"])
        self.assertEqual(product["pdp_decision_checks"][0]["title"], "Preço garantido")
        self.assertEqual(product["pdp_decision_checks"][2]["title"], "Checkout seguro")

    def test_storefront_query_service_applies_selected_variant_when_valid(self):
        product = storefront_catalog_queries.get_product("tenis-hubx-runner-persistido", tenant_id=self.tenant.id, size="42", color="wht")

        self.assertEqual(product["sku"], "RUNNER-PERSIST-WHT-42")
        self.assertEqual(product["stock_state"], "low_stock")
        self.assertEqual(product["stock_label"], "Estoque baixo")
        self.assertEqual(product["stock_helper"], "Últimas unidades")
        self.assertEqual(product["effective_variant_summary"], "")
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
        self.assertContains(list_response, "Calçados esportivos")
        self.assertContains(list_response, "Oferta ativa")
        self.assertContains(list_response, "Pronta entrega")
        self.assertContains(list_response, "Comprar")
        self.assertNotContains(list_response, "SKU RUNNER-PERSIST-BLK-42")
        self.assertNotContains(list_response, "Combinação em destaque")
        self.assertContains(list_response, "Explore a loja, compare opções disponíveis")
        self.assertContains(list_response, "preços e disponibilidade atualizados")
        self.assertContains(list_response, "Confira os produtos da loja")
        self.assertNotContains(list_response, "curadoria leve")
        self.assertNotContains(list_response, "variante efetiva")
        self.assertNotContains(list_response, "sinais leves")
        self.assertNotContains(list_response, "base comercial")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/product_detail_page.html")
        self.assertContains(detail_response, "Tênis Hubx Runner Persistido")
        self.assertContains(detail_response, "R$ 399,90")
        self.assertContains(detail_response, "Hubx Persisted")
        self.assertContains(detail_response, "Pronta entrega")
        self.assertContains(detail_response, "Disponível para compra.")
        self.assertContains(detail_response, "Oferta ativa com parcelamento disponível")
        self.assertNotContains(detail_response, "Variante em destaque agora")
        self.assertNotContains(detail_response, "SKU RUNNER-PERSIST-BLK-42")
        self.assertNotContains(detail_response, "combinação destacada")
        self.assertContains(detail_response, "Adicionar ao carrinho")
        self.assertContains(detail_response, "Comprar agora")
        self.assertContains(detail_response, "Preço e disponibilidade serão preservados no checkout")
        self.assertContains(detail_response, "Resumo para decisão de compra")
        self.assertContains(detail_response, "Preço garantido")
        self.assertContains(detail_response, "Disponibilidade atual")
        self.assertContains(detail_response, "Checkout seguro")
        self.assertContains(detail_response, "https://cdn.hubx.market/demo/catalog/runner-primary.jpg")

    def test_storefront_product_cards_render_approved_review_summary_only(self):
        product = Product.objects.get(slug="tenis-hubx-runner-persistido", tenant=self.tenant)
        other_tenant = Tenant.objects.create(name="Outra Card Reviews", slug="outra-card-reviews", subdomain="outra-card-reviews")
        other_product = Product.objects.create(
            tenant=other_tenant,
            name="Produto card outra loja",
            slug="produto-card-outra-loja",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=5,
            status=ProductReview.Status.APPROVED,
            author_name="Cliente Card",
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=1,
            status=ProductReview.Status.PENDING,
            author_name="Pendente Invisível",
        )
        ProductReview.objects.create(
            tenant=other_tenant,
            product=other_product,
            rating=1,
            status=ProductReview.Status.APPROVED,
            author_name="Outra Loja",
        )

        response = self.client.get(reverse("storefront:catalog-list"), HTTP_HOST=self.storefront_host)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "⭐ 5.0/5 · 1 avaliação(ões)")
        self.assertNotContains(response, "⭐ 1.0/5")

    def test_product_detail_view_renders_selected_variant_when_requested(self):
        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            {"size": "42", "color": "wht"},
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Últimas unidades")
        self.assertContains(response, "Últimas unidades disponíveis para envio imediato.")
        self.assertContains(response, "Preço e disponibilidade serão preservados no checkout")
        self.assertNotContains(response, "Variante em destaque agora")
        self.assertNotContains(response, "SKU RUNNER-PERSIST-WHT-42")

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

    def test_product_detail_post_add_to_cart_creates_session_cart_and_redirects_with_feedback(self):
        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"intent": "add_to_cart"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            f'{reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})}?cart_feedback=added',
        )
        self.assertEqual(CheckoutSession.objects.count(), 0)

        cart = Cart.objects.get()
        self.assertEqual(cart.tenant, self.tenant)
        self.assertEqual(cart.session_key, self.client.session.session_key)
        self.assertEqual(cart.items.count(), 1)
        self.assertEqual(cart.items.first().product_name, "Tênis Hubx Runner Persistido")
        self.assertEqual(cart.items.first().variant_sku, "RUNNER-PERSIST-BLK-42")

    def test_product_detail_post_add_to_cart_records_cta_intent_analytics(self):
        class SpyPublisher:
            def __init__(self):
                self.events = []

            def publish(self, event):
                self.events.append(event)

        spy = SpyPublisher()
        storefront_discovery_analytics.publisher = spy

        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"intent": "add_to_cart", "quantity": "2"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual([event.name for event in spy.events], ["catalog.pdp_cta_intent"])
        payload = spy.events[0].payload
        self.assertEqual(payload["tenant_id"], self.tenant.id)
        self.assertEqual(payload["product_slug"], "tenis-hubx-runner-persistido")
        self.assertEqual(payload["cta_intent"], "add_to_cart")
        self.assertEqual(payload["cta_result"], "cart-item-added")
        self.assertEqual(payload["quantity"], 2)
        self.assertEqual(payload["variant_sku"], "RUNNER-PERSIST-BLK-42")

    def test_product_detail_renders_add_to_cart_feedback(self):
        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"intent": "add_to_cart"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Produto adicionado ao carrinho")
        self.assertContains(response, "Você pode continuar revisando esta combinação")
        self.assertContains(response, "Produto adicionado ao carrinho.")

    def test_product_detail_renders_cart_idempotency_key(self):
        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="cart_idempotency_key"')

    def test_product_detail_renders_only_approved_reviews_for_current_tenant(self):
        product = Product.objects.get(slug="tenis-hubx-runner-persistido", tenant=self.tenant)
        other_tenant = Tenant.objects.create(name="Outra PDP Reviews", slug="outra-pdp-reviews", subdomain="outra-pdp-reviews")
        other_product = Product.objects.create(
            tenant=other_tenant,
            name="Produto outra loja",
            slug="produto-outra-loja",
            status=Product.Status.ACTIVE,
            is_active=True,
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=5,
            title="Compra excelente",
            body="Produto confortável e entrega correta.",
            author_name="Ana Review",
            status=ProductReview.Status.APPROVED,
        )
        ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=1,
            title="Review pendente invisível",
            status=ProductReview.Status.PENDING,
        )
        ProductReview.objects.create(
            tenant=other_tenant,
            product=other_product,
            rating=1,
            title="Outra loja invisível",
            status=ProductReview.Status.APPROVED,
        )

        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'href="#product-reviews"')
        self.assertContains(response, "5.0/5")
        self.assertContains(response, "1 avaliação(ões) aprovada(s)")
        self.assertContains(response, "Ver avaliações")
        self.assertContains(response, 'id="product-reviews"')
        self.assertContains(response, "Avaliação em destaque")
        self.assertContains(response, "ver todas as avaliações")
        self.assertContains(response, "Avaliações de clientes")
        self.assertContains(response, "Média 5.0/5 baseada em 1 avaliação")
        self.assertContains(response, "Compra excelente")
        self.assertContains(response, "Produto confortável e entrega correta.")
        self.assertContains(response, "Ana Review")
        self.assertNotContains(response, "Review pendente invisível")
        self.assertNotContains(response, "Outra loja invisível")

    def test_product_detail_omits_review_block_without_approved_reviews(self):
        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Avaliações de clientes")
        self.assertNotContains(response, "Avaliação em destaque")
        self.assertNotContains(response, 'href="#product-reviews"')
        self.assertNotContains(response, "Ver avaliações")

    def test_product_detail_featured_review_uses_safe_fallback_without_title_or_body(self):
        product = Product.objects.get(slug="tenis-hubx-runner-persistido", tenant=self.tenant)
        ProductReview.objects.create(
            tenant=self.tenant,
            product=product,
            rating=4,
            author_name="Cliente Sem Texto",
            status=ProductReview.Status.APPROVED,
        )

        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cliente recomenda este produto")
        self.assertContains(response, "Avaliação aprovada por cliente verificado nesta loja")
        self.assertContains(response, "Cliente Sem Texto")

    def test_product_detail_add_to_cart_replay_with_same_key_does_not_increment_twice(self):
        url = reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})
        payload = {"intent": "add_to_cart", "cart_idempotency_key": "pdp-add-1"}

        first_response = self.client.post(url, data=payload)
        replay_response = self.client.post(url, data=payload)

        self.assertEqual(first_response.status_code, 302)
        self.assertEqual(replay_response.status_code, 302)
        item = CartItem.objects.get()
        self.assertEqual(item.quantity, 1)
        self.assertEqual(CartMutation.objects.count(), 1)

    def test_product_detail_post_add_to_cart_preserves_selected_variant(self):
        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"intent": "add_to_cart", "size": "42", "color": "wht"},
        )

        self.assertEqual(
            response["Location"],
            f'{reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})}?size=42&color=wht&cart_feedback=added',
        )
        item = CartItem.objects.get()
        self.assertEqual(item.variant_label, "Branco · 42")
        self.assertEqual(item.variant_sku, "RUNNER-PERSIST-WHT-42")

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

    def test_product_detail_post_buy_now_records_cta_intent_analytics(self):
        class SpyPublisher:
            def __init__(self):
                self.events = []

            def publish(self, event):
                self.events.append(event)

        spy = SpyPublisher()
        storefront_discovery_analytics.publisher = spy

        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"size": "42", "color": "wht"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual([event.name for event in spy.events], ["catalog.pdp_cta_intent"])
        payload = spy.events[0].payload
        self.assertEqual(payload["cta_intent"], "buy_now")
        self.assertEqual(payload["cta_result"], "checkout-activated")
        self.assertEqual(payload["variant_sku"], "RUNNER-PERSIST-WHT-42")

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
            f'{reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})}?size=43&color=blk&cart_feedback=unavailable',
        )
        self.assertFalse(Cart.objects.exists())

    def test_product_detail_post_out_of_stock_records_cta_intent_analytics(self):
        class SpyPublisher:
            def __init__(self):
                self.events = []

            def publish(self, event):
                self.events.append(event)

        spy = SpyPublisher()
        storefront_discovery_analytics.publisher = spy

        response = self.client.post(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            data={"intent": "add_to_cart", "size": "43", "color": "blk"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual([event.name for event in spy.events], ["catalog.pdp_cta_intent"])
        payload = spy.events[0].payload
        self.assertEqual(payload["cta_intent"], "add_to_cart")
        self.assertEqual(payload["cta_result"], "unavailable")
        self.assertEqual(payload["variant_sku"], "RUNNER-PERSIST-BLK-43")

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

    def test_product_detail_uses_product_main_image_for_social_preview(self):
        product = Product.objects.get(tenant=self.tenant, slug="tenis-hubx-runner-persistido")
        product.images.create(
            image_url="https://cdn.example.com/catalog/runner-pdp.jpg",
            alt_text="Tênis Hubx Runner na vitrine",
            position=1,
            is_primary=True,
        )

        response = self.client.get(
            reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"}),
            HTTP_HOST=self.storefront_host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '<meta property="og:image" content="https://cdn.example.com/catalog/runner-pdp.jpg">')
        self.assertContains(response, '<meta property="og:title" content="Tênis Hubx Runner Persistido">')
        self.assertContains(
            response,
            '<meta property="og:url" content="http://hubx-demo.hubx.market/catalog/tenis-hubx-runner-persistido/">',
        )

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
        self.assertEqual(item["stock_helper"], "Pronta entrega")
        self.assertEqual(item["price_helper"], "Parcelamento disponível")

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
        self.assertEqual(item["catalog_card_availability_note"], "Sob encomenda")
        self.assertEqual(item["catalog_card_curation_note"], "")
        self.assertEqual(item["catalog_card_decision_signal"], "reserva_planejada")
        self.assertEqual(item["catalog_card_click_helper"], "")
        self.assertEqual(item["stock_helper"], "Sob encomenda")
        self.assertIn("Produto liberado por encomenda", item["availability_note"])
        self.assertIn("reserva segue para checkout", item["cta_helper"])
        self.assertIn("Produto disponível por encomenda", item["purchase_note"])

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
        self.assertEqual(item["secondary_action_label"], "Ver loja")
        self.assertEqual(item["secondary_action_target"], "catalog")
        self.assertEqual(item["badge_label"], "Indisponível")
        self.assertEqual(item["catalog_card_availability_note"], "Indisponível no momento")
        self.assertEqual(item["catalog_card_curation_note"], "")
        self.assertEqual(item["catalog_card_decision_signal"], "acompanhar_reposicao")
        self.assertEqual(item["catalog_card_click_helper"], "")
        self.assertEqual(item["stock_helper"], "Indisponível no momento")
        self.assertIn("sem estoque no momento", item["availability_note"])
        self.assertIn("não segue para checkout agora", item["cta_helper"])
        self.assertIn("Produto indisponível no momento", item["purchase_note"])
        self.assertEqual(item["pdp_decision_checks"][1]["title"], "Sem checkout agora")
        self.assertIn("indisponível para compra imediata", item["pdp_decision_checks"][1]["description"])

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
        self.assertEqual(item["badge_label"], "Últimas unidades")
        self.assertEqual(item["badge_variant"], "warning")
        self.assertEqual(item["catalog_card_availability_note"], "Últimas unidades para envio imediato")
        self.assertEqual(item["catalog_card_curation_note"], "")
        self.assertEqual(item["catalog_card_decision_signal"], "decisao_rapida_com_oferta")
        self.assertEqual(item["catalog_card_click_helper"], "")
        self.assertIn("Últimas unidades disponíveis", item["availability_note"])
        self.assertIn("preservados no checkout", item["cta_helper"])
        self.assertIn("Poucas unidades disponíveis", item["purchase_note"])
        self.assertIn("Poucas unidades", item["price_helper"])
        self.assertEqual(item["catalog_card_meta"], "Últimas unidades")
        self.assertEqual(item["catalog_card_price_helper"], "Últimas unidades")
