from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.catalog.application.admin_product_queries import admin_product_queries
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
