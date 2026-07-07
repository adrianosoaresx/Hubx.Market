from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.catalog.application.admin_product_queries import admin_product_queries
from app.modules.catalog.models import Product, ProductVariant, StorefrontDiscoveryEventLog
from app.modules.orders.models import Order, OrderItem
from app.modules.tenants.models import Tenant


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


@override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class AdminProductCrudTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja CRUD Catálogo",
            slug="loja-crud-catalogo",
            subdomain="loja-crud-catalogo",
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"

    def _payload(self, **overrides):
        payload = {
            "name": "Produto CRUD",
            "slug": "produto-crud",
            "sku": "CRUD-001",
            "brand": "Hubx",
            "category_label": "Operacional",
            "description": "Produto criado pelo admin de catálogo.",
            "price": "129.90",
            "compare_price": "149.90",
            "stock": "12",
            "reserved_stock": "2",
            "status": Product.Status.ACTIVE,
            "is_active": "1",
            "is_featured": "1",
            "track_inventory": "1",
        }
        payload.update(overrides)
        return payload

    def _create_product(self, *, slug="produto-original", sku="ORIGINAL-001"):
        product = Product.objects.create(
            tenant=self.tenant,
            name="Produto Original",
            slug=slug,
            description="Descrição original.",
            brand_name="Marca Original",
            category_label="Categoria Original",
            status=Product.Status.DRAFT,
            is_active=False,
            is_featured=False,
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku=sku,
            price="50.00",
            compare_price=None,
            stock=5,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        return product, variant

    def test_admin_product_create_persists_product_and_default_variant(self):
        response = self.client.post(
            reverse("catalog:admin-products-create"),
            self._payload(),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(tenant=self.tenant, slug="produto-crud")
        variant = ProductVariant.objects.get(product=product, is_default=True)
        self.assertEqual(product.name, "Produto CRUD")
        self.assertEqual(product.brand_name, "Hubx")
        self.assertEqual(product.category_label, "Operacional")
        self.assertTrue(product.is_active)
        self.assertTrue(product.is_featured)
        self.assertEqual(variant.sku, "CRUD-001")
        self.assertEqual(str(variant.price), "129.90")
        self.assertEqual(variant.stock, 12)
        self.assertEqual(variant.reserved_stock, 2)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, module="catalog", action="product.created").exists())

    def test_admin_product_edit_updates_product_and_default_variant(self):
        self._create_product()

        response = self.client.post(
            reverse("catalog:admin-products-edit", kwargs={"product_slug": "produto-original"}),
            self._payload(
                name="Produto Editado",
                slug="produto-editado",
                sku="EDIT-001",
                brand="Marca Editada",
                category_label="Categoria Editada",
                price="199.90",
                compare_price="",
                stock="20",
                reserved_stock="1",
                status=Product.Status.ACTIVE,
                allow_backorder="1",
            ),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], reverse("catalog:admin-products-detail", kwargs={"product_slug": "produto-editado"}))
        product = Product.objects.get(tenant=self.tenant, slug="produto-editado")
        variant = ProductVariant.objects.get(product=product, is_default=True)
        self.assertEqual(product.name, "Produto Editado")
        self.assertEqual(product.brand_name, "Marca Editada")
        self.assertEqual(product.category_label, "Categoria Editada")
        self.assertEqual(product.status, Product.Status.ACTIVE)
        self.assertTrue(product.is_active)
        self.assertTrue(product.is_featured)
        self.assertEqual(variant.sku, "EDIT-001")
        self.assertEqual(str(variant.price), "199.90")
        self.assertIsNone(variant.compare_price)
        self.assertEqual(variant.stock, 20)
        self.assertEqual(variant.reserved_stock, 1)
        self.assertTrue(variant.allow_backorder)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, module="catalog", action="product.updated").exists())

    def test_admin_product_form_rejects_duplicate_slug_for_tenant(self):
        self._create_product(slug="produto-existente", sku="EXIST-001")

        response = self.client.post(
            reverse("catalog:admin-products-create"),
            self._payload(slug="produto-existente", sku="NOVO-001"),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Já existe um produto com este slug neste tenant.", status_code=400)
        self.assertEqual(Product.objects.filter(tenant=self.tenant, slug="produto-existente").count(), 1)

    def test_admin_product_deactivate_does_not_delete_product(self):
        product, _variant = self._create_product(slug="produto-ativo", sku="ACTIVE-001")
        Product.objects.filter(pk=product.pk).update(
            status=Product.Status.ACTIVE,
            is_active=True,
            is_featured=True,
        )

        response = self.client.post(
            reverse("catalog:admin-products-deactivate", kwargs={"product_slug": "produto-ativo"}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        product.refresh_from_db()
        self.assertEqual(Product.objects.filter(pk=product.pk).count(), 1)
        self.assertEqual(product.status, Product.Status.INACTIVE)
        self.assertFalse(product.is_active)
        self.assertFalse(product.is_featured)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, module="catalog", action="product.deactivated").exists())

    def test_admin_product_write_requires_catalog_manage_when_owner_role_is_resolved(self):
        OwnerUser.objects.create(tenant=self.tenant, email="viewer.catalog@hubx.market", role="viewer", is_active=True)
        user = User.objects.create_user(username="viewer-catalog", email="viewer.catalog@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.post(
            reverse("catalog:admin-products-create"),
            self._payload(slug="produto-negado", sku="DENIED-001"),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Permissão insuficiente para gerenciar produtos.", status_code=400)
        self.assertFalse(Product.objects.filter(tenant=self.tenant, slug="produto-negado").exists())

    def test_admin_product_detail_renders_variant_management(self):
        self._create_product(slug="produto-variantes", sku="VAR-001")

        response = self.client.get(
            reverse("catalog:admin-products-detail", kwargs={"product_slug": "produto-variantes"}),
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Variantes")
        self.assertContains(response, "VAR-001")
        self.assertContains(response, "Adicionar variante")

    def test_admin_product_variant_create_persists_advanced_fields(self):
        product, default_variant = self._create_product(slug="produto-variantes", sku="VAR-001")

        response = self.client.post(
            reverse("catalog:admin-product-variant-create", kwargs={"product_slug": "produto-variantes"}),
            {
                "sku": "VAR-002",
                "label": "Azul · M",
                "option_values": "Cor=Azul\nTamanho=M",
                "barcode": "789000000002",
                "price": "159.90",
                "compare_price": "179.90",
                "stock": "8",
                "reserved_stock": "1",
                "weight_grams": "450",
                "track_inventory": "1",
                "is_active": "1",
                "is_default": "1",
                "position": "2",
            },
            HTTP_HOST=self.host,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response["Location"],
            f"{reverse('catalog:admin-products-detail', kwargs={'product_slug': 'produto-variantes'})}?variant_result=created",
        )
        variant = ProductVariant.objects.get(product=product, sku="VAR-002")
        default_variant.refresh_from_db()
        self.assertEqual(variant.label, "Azul · M")
        self.assertEqual(variant.option_values, {"Cor": "Azul", "Tamanho": "M"})
        self.assertEqual(variant.barcode, "789000000002")
        self.assertEqual(str(variant.price), "159.90")
        self.assertEqual(str(variant.compare_price), "179.90")
        self.assertEqual(variant.stock, 8)
        self.assertEqual(variant.reserved_stock, 1)
        self.assertEqual(variant.weight_grams, 450)
        self.assertTrue(variant.is_default)
        self.assertFalse(default_variant.is_default)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, module="catalog", action="product.variant_created").exists())

    def test_admin_product_variant_default_and_deactivate_are_tenant_scoped_and_non_destructive(self):
        product, default_variant = self._create_product(slug="produto-variantes", sku="VAR-001")
        variant = ProductVariant.objects.create(
            product=product,
            sku="VAR-002",
            label="Preto · G",
            option_values={"Cor": "Preto", "Tamanho": "G"},
            price="89.90",
            stock=4,
            is_active=True,
            is_default=False,
            position=2,
        )

        default_response = self.client.post(
            reverse(
                "catalog:admin-product-variant-default",
                kwargs={"product_slug": "produto-variantes", "variant_id": variant.id},
            ),
            HTTP_HOST=self.host,
        )

        default_variant.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(default_response.status_code, 302)
        self.assertFalse(default_variant.is_default)
        self.assertTrue(variant.is_default)

        deactivate_response = self.client.post(
            reverse(
                "catalog:admin-product-variant-deactivate",
                kwargs={"product_slug": "produto-variantes", "variant_id": variant.id},
            ),
            HTTP_HOST=self.host,
        )

        default_variant.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(deactivate_response.status_code, 302)
        self.assertEqual(ProductVariant.objects.filter(pk=variant.pk).count(), 1)
        self.assertFalse(variant.is_active)
        self.assertFalse(variant.is_default)
        self.assertTrue(default_variant.is_default)
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, module="catalog", action="product.variant_deactivated").exists())

    def test_admin_product_variant_deactivate_blocks_last_active_variant(self):
        _product, variant = self._create_product(slug="produto-variantes", sku="VAR-001")

        response = self.client.post(
            reverse(
                "catalog:admin-product-variant-deactivate",
                kwargs={"product_slug": "produto-variantes", "variant_id": variant.id},
            ),
            HTTP_HOST=self.host,
        )

        variant.refresh_from_db()
        self.assertEqual(response.status_code, 302)
        self.assertIn("variant_result=blocked", response["Location"])
        self.assertTrue(variant.is_active)
        self.assertTrue(variant.is_default)


class AdminProductPersistedReadTests(TestCase):
    fixtures = ["catalog_minimal_seed.json"]

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_product_views_do_not_fallback_to_fixture_data_when_tenant_is_resolved(self):
        empty_tenant = Tenant.objects.create(
            name="Hubx Empty Admin Product Tenant",
            slug="hubx-empty-admin-product-tenant",
            subdomain="hubx-empty-admin-product-tenant",
        )

        products = admin_product_queries.list_products(tenant_id=empty_tenant.id)
        missing_product = admin_product_queries.get_product("tenis-hubx-runner", tenant_id=empty_tenant.id)
        form_initial = admin_product_queries.get_form_initial("tenis-hubx-runner", tenant_id=empty_tenant.id)

        self.assertEqual(products, [])
        self.assertIn("não encontrado no tenant atual", missing_product["summary_content"].lower())
        self.assertIn("tenant atual", missing_product["inventory_content"].lower())
        self.assertEqual(form_initial["name"], "Tenis Hubx Runner")

        list_response = self.client.get(
            reverse("catalog:admin-products-list"),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )
        detail_response = self.client.get(
            reverse("catalog:admin-products-detail", kwargs={"product_slug": "tenis-hubx-runner"}),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "Tênis Hubx Runner")
        self.assertEqual(list_response.context["empty_title"], "Nenhum produto persistido nesta loja")
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Produto não encontrado no tenant atual")
        self.assertNotContains(detail_response, "fallback seguro de apresentação")

    def _create_inventory_recovery(self) -> None:
        order = Order.objects.create(
            tenant_id=1,
            number="2999",
            status="canceled",
            customer_name="Cliente Recuperação",
            customer_email="recuperacao@hubx.market",
            payment_status="Confirmado internamente",
            fulfillment_status_label="Cancelado",
            fulfillment_status_variant="danger",
            shipping_status="Cancelado",
            subtotal="399.90",
            shipping_total="0.00",
            discount_total="0.00",
            total="399.90",
        )
        OrderItem.objects.create(
            order=order,
            title="Tênis Hubx Runner Persistido",
            subtitle="Preto · 42",
            meta="SKU RUNNER-PERSIST-BLK-42",
            variant_sku="RUNNER-PERSIST-BLK-42",
            price_snapshot="399.90",
            quantity=1,
            quantity_readonly=True,
            sort_order=1,
        )
        order.inventory_recovered_at = order.updated_at
        order.save(update_fields=["inventory_recovered_at", "updated_at"])

    def _create_inventory_finalization(self) -> None:
        order = Order.objects.create(
            tenant_id=1,
            number="3000",
            status="shipped",
            customer_name="Cliente Finalização",
            customer_email="finalizacao@hubx.market",
            payment_status="Confirmado internamente",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            shipping_status="Entregue",
            subtotal="399.90",
            shipping_total="0.00",
            discount_total="0.00",
            total="399.90",
        )
        OrderItem.objects.create(
            order=order,
            title="Tênis Hubx Runner Persistido",
            subtitle="Preto · 42",
            meta="SKU RUNNER-PERSIST-BLK-42",
            variant_sku="RUNNER-PERSIST-BLK-42",
            price_snapshot="399.90",
            quantity=1,
            quantity_readonly=True,
            sort_order=1,
        )
        order.inventory_finalized_at = order.updated_at
        order.save(update_fields=["inventory_finalized_at", "updated_at"])

    def test_admin_product_query_service_uses_persisted_records_when_available(self):
        self._create_inventory_recovery()
        self._create_inventory_finalization()
        product = admin_product_queries.get_product("tenis-hubx-runner-persistido")
        form_initial = admin_product_queries.get_form_initial("tenis-hubx-runner-persistido")

        self.assertTrue(admin_product_queries.using_persisted_source())
        self.assertEqual(product["name"], "Tênis Hubx Runner Persistido")
        self.assertEqual(product["brand"], "Hubx Persisted")
        self.assertEqual(product["sku"], "RUNNER-PERSIST-BLK-42")
        self.assertEqual(product["price"], "399.90")
        self.assertEqual(form_initial["name"], "Tênis Hubx Runner Persistido")
        self.assertIn("Hubx Persisted", product["summary_content"])
        self.assertIn("SKU principal RUNNER-PERSIST-BLK-42", product["summary_content"])
        self.assertIn("Preço atual: R$ 399,90", product["pricing_content"])
        self.assertIn("Estoque disponível: 12 unidade(s)", product["inventory_content"])
        self.assertIn("Impacto operacional visível: 2 unidade(s) já reservadas", product["inventory_visibility_content"])
        self.assertIn("Devolução operacional visível: 1 unidade(s) já voltaram ao estoque", product["inventory_recovery_content"])
        self.assertIn("Consumo final visível: 1 unidade(s) já concluíram a reserva operacional", product["inventory_finalization_content"])
        self.assertIn("Linha operacional do estoque:", product["inventory_timeline_content"])
        self.assertIn("2 unidade(s) reservadas", product["inventory_timeline_content"])
        self.assertIn("1 recuperada(s)", product["inventory_timeline_content"])
        self.assertIn("1 finalizada(s)", product["inventory_timeline_content"])
        self.assertIn("visível no catálogo", product["visibility_content"])
        self.assertEqual(product["updated_at"], "14/04/2026 às 12:00")
        self.assertGreaterEqual(len(product["activity_items"]), 2)
        self.assertEqual(product["activity_items"][0]["badge_label"], "Catálogo")
        self.assertTrue(any(item["title"] == "Devolução operacional registrada" for item in product["activity_items"]))
        self.assertTrue(any(item["title"] == "Consumo final registrado" for item in product["activity_items"]))
        self.assertTrue(any(item["title"] == "Saldo livre atual" for item in product["activity_items"]))

    def test_admin_product_list_view_renders_persisted_records_when_present(self):
        self._create_inventory_recovery()
        self._create_inventory_finalization()
        response = self.client.get(reverse("catalog:admin-products-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tênis Hubx Runner Persistido")
        self.assertContains(response, "RUNNER-PERSIST-BLK-42")
        self.assertContains(response, "reservadas 2")
        self.assertContains(response, "recuperadas 1")
        self.assertContains(response, "finalizadas 1")
        self.assertContains(response, "14/04/2026 às 12:00")
        self.assertContains(response, "Visibilidade de estoque:")
        self.assertContains(response, "Recuperação operacional já visível em 1 produto(s)")
        self.assertContains(response, "Consumo final já visível em 1 produto(s)")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_product_list_view_renders_tenant_discovery_observability(self):
        response = self.client.get(reverse("catalog:admin-products-list"), HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Descoberta")
        self.assertContains(response, "Score 1450")
        self.assertContains(response, "oferta ativa com destaque editorial")
        self.assertContains(response, "status 1000")
        self.assertContains(response, "estoque 320")
        self.assertContains(response, "sinal 30")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_conversion_analytics_view_renders_tenant_scoped_events(self):
        tenant = Tenant.objects.get(subdomain="hubx-demo")
        other_tenant = Tenant.objects.create(
            name="Hubx Analytics Other Tenant",
            slug="hubx-analytics-other-tenant",
            subdomain="hubx-analytics-other-tenant",
        )
        StorefrontDiscoveryEventLog.objects.create(
            tenant=tenant,
            event_name="catalog.search_performed",
            path="/catalog/",
            payload={"query": "runner", "result_count": 1},
            session_key_hash="tenant-session-hash",
        )
        StorefrontDiscoveryEventLog.objects.create(
            tenant=tenant,
            event_name="catalog.pdp_cta_intent",
            path="/products/tenis-hubx-runner-persistido/",
            payload={
                "product_slug": "tenis-hubx-runner-persistido",
                "cta_intent": "add_to_cart",
                "cta_result": "cart-item-added",
                "variant_sku": "RUNNER-PERSIST-BLK-42",
            },
            session_key_hash="tenant-session-hash",
        )
        StorefrontDiscoveryEventLog.objects.create(
            tenant=other_tenant,
            event_name="catalog.search_performed",
            path="/catalog/",
            payload={"query": "other-tenant", "result_count": 0},
            session_key_hash="other-session-hash",
        )

        response = self.client.get(reverse("catalog:admin-conversion-analytics"), HTTP_HOST="hubx-demo.hubx.market")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_conversion_analytics_page.html")
        self.assertContains(response, "Analytics de conversão")
        self.assertContains(response, "2 evento(s) tenant-scoped")
        self.assertContains(response, "Busca realizada")
        self.assertContains(response, "CTA do PDP")
        self.assertContains(response, "busca “runner”")
        self.assertContains(response, "CTA add_to_cart")
        self.assertContains(response, "SKU RUNNER-PERSIST-BLK-42")
        self.assertNotContains(response, "other-tenant")
        self.assertNotContains(response, "tenant-session-hash")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_conversion_analytics_view_filters_by_event_name(self):
        tenant = Tenant.objects.get(subdomain="hubx-demo")
        StorefrontDiscoveryEventLog.objects.create(
            tenant=tenant,
            event_name="catalog.search_performed",
            path="/catalog/",
            payload={"query": "runner", "result_count": 1},
        )
        StorefrontDiscoveryEventLog.objects.create(
            tenant=tenant,
            event_name="catalog.pdp_cta_intent",
            path="/products/tenis-hubx-runner-persistido/",
            payload={"product_slug": "tenis-hubx-runner-persistido", "cta_intent": "add_to_cart"},
        )

        response = self.client.get(
            reverse("catalog:admin-conversion-analytics"),
            {"event_name": "catalog.pdp_cta_intent"},
            HTTP_HOST="hubx-demo.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2 evento(s) tenant-scoped")
        self.assertContains(response, "1 evento(s) neste recorte")
        self.assertContains(response, "CTA do PDP")
        self.assertContains(response, "CTA add_to_cart")
        self.assertNotContains(response, "busca “runner”")

    def test_admin_product_detail_view_renders_enriched_persisted_content(self):
        self._create_inventory_recovery()
        self._create_inventory_finalization()
        response = self.client.get(
            reverse("catalog:admin-products-detail", kwargs={"product_slug": "tenis-hubx-runner-persistido"})
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SKU principal RUNNER-PERSIST-BLK-42")
        self.assertContains(response, "Estoque disponível: 12 unidade(s)")
        self.assertContains(response, "Impacto operacional visível: 2 unidade(s) já reservadas")
        self.assertContains(response, "Devolução operacional visível: 1 unidade(s) já voltaram ao estoque")
        self.assertContains(response, "Consumo final visível: 1 unidade(s) já concluíram a reserva operacional")
        self.assertContains(response, "Linha operacional do estoque:")
        self.assertContains(response, "Saldo livre atual")
        self.assertContains(response, "Consumo final registrado")
        self.assertContains(response, "com destaque ativo")
