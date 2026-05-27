from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from app.modules.catalog.models import Product, ProductVariant
from app.modules.coupons.models import Coupon, CouponRedemption
from app.modules.orders.application.admin_order_queries import DjangoOrmOrderRepository, admin_order_queries
from app.modules.orders.models import Order, OrderStatusHistory
from app.modules.shipping.models import Shipment
from app.modules.tenants.models import Tenant


class AdminOrderViewTests(TestCase):
    def test_orders_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("orders:admin-orders-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_orders_list_page.html")
        self.assertContains(response, "Pedidos")
        self.assertContains(response, "#1048")

    def test_orders_list_view_applies_search_filter(self):
        response = self.client.get(reverse("orders:admin-orders-list"), {"q": "Bruno"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#1049")
        self.assertNotContains(response, "#1048")

    def test_orders_list_view_renders_inventory_exception_quick_filter(self):
        response = self.client.get(reverse("orders:admin-orders-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="quick_filter"')
        self.assertContains(response, "Exceção ativa")
        self.assertContains(response, "Em revisão")
        self.assertContains(response, "Resolvidas")
        self.assertContains(response, "Alta prioridade")
        self.assertContains(response, "Média prioridade")
        self.assertContains(response, "Baixa prioridade")
        self.assertContains(response, "Sem responsável")
        self.assertContains(response, "Com responsável")
        self.assertContains(response, "Ações")

    def test_order_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "1048"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_order_detail_page.html")
        self.assertContains(response, "Pedido #1048")
        self.assertContains(response, "Ana Souza")

    def test_admin_order_query_service_returns_expected_contract(self):
        order = admin_order_queries.get_order("1048")

        self.assertEqual(order["order_number"], "1048")
        self.assertEqual(order["order_status_label"], "Pago")
        self.assertEqual(order["customer"], "Ana Souza")

    def test_admin_order_query_service_reports_persisted_source_readiness(self):
        self.assertFalse(admin_order_queries.using_persisted_source())

    def test_admin_order_query_service_reports_fallback_visibility_note(self):
        self.assertIn("fallback de apresentação", admin_order_queries.get_operational_visibility_note())


class AdminOrderPersistedReadTests(TestCase):
    fixtures = ["orders_minimal_seed.json"]

    def test_admin_order_query_service_scopes_records_by_tenant_when_requested(self):
        primary_order = Order.objects.get(number="2048")
        secondary_tenant = Tenant.objects.create(
            name="Hubx Order Secondary Tenant",
            slug="hubx-order-secondary-tenant",
            subdomain="hubx-order-secondary-tenant",
        )
        secondary_order = Order.objects.create(
            tenant=secondary_tenant,
            number="2048",
            status="pending",
            customer_name="Cliente Outra Loja",
            customer_email="outra-loja@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            subtotal="10.00",
            total="10.00",
        )
        secondary_order.items.create(
            title="Item Outra Loja",
            subtitle="Único",
            meta="SKU OTHER-001",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        scoped_order = admin_order_queries.get_order("2048", tenant_id=primary_order.tenant_id)
        secondary_scoped_order = admin_order_queries.get_order("2048", tenant_id=secondary_tenant.id)
        scoped_numbers = [order["order_number"] for order in admin_order_queries.list_orders(tenant_id=primary_order.tenant_id)]
        secondary_scoped_numbers = [order["order_number"] for order in admin_order_queries.list_orders(tenant_id=secondary_tenant.id)]

        self.assertEqual(scoped_order["customer"], "Ana Persistida")
        self.assertEqual(secondary_scoped_order["customer"], "Cliente Outra Loja")
        self.assertEqual(scoped_numbers, ["2048"])
        self.assertEqual(secondary_scoped_numbers, ["2048"])

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_order_views_do_not_fallback_to_fixture_data_when_tenant_is_resolved(self):
        empty_tenant = Tenant.objects.create(
            name="Hubx Empty Admin Order Tenant",
            slug="hubx-empty-admin-order-tenant",
            subdomain="hubx-empty-admin-order-tenant",
        )

        orders = admin_order_queries.list_orders(tenant_id=empty_tenant.id)
        missing_order = admin_order_queries.get_order("1048", tenant_id=empty_tenant.id)

        self.assertEqual(orders, [])
        self.assertIn("não encontrado no tenant atual", missing_order["summary_content"].lower())
        self.assertEqual(missing_order["customer_linkage_mode"], "missing")

        list_response = self.client.get(
            reverse("orders:admin-orders-list"),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )
        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "1048"}),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "#1048")
        self.assertContains(list_response, "Nenhum pedido persistido nesta loja")
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Pedido não encontrado no tenant atual")
        self.assertNotContains(detail_response, "fallback seguro de apresentação")

    def test_admin_order_query_service_uses_persisted_records_when_available(self):
        Order.objects.filter(number="2048").update(inventory_reserved_at=timezone.now())
        order_model = Order.objects.get(number="2048")
        first_item = order_model.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])
        order = admin_order_queries.get_order("2048")

        self.assertTrue(admin_order_queries.using_persisted_source())
        self.assertEqual(order["order_number"], "2048")
        self.assertEqual(order["customer"], "Ana Persistida")
        self.assertEqual(order["payment_status"], "Confirmado")
        self.assertEqual(order["shipping_status"], "Preparando envio")
        self.assertEqual(order["subtotal"], "R$ 399,90")
        self.assertEqual(order["discount"], "-R$ 10,00")
        self.assertEqual(order["order_items"][0]["title"], "Tênis Hubx Runner Persistido")
        self.assertIn("Pedido #2048 de Ana Persistida", order["summary_content"])
        self.assertIn("ana.persisted@hubx.market", order["customer_content"])
        self.assertIn("Rua Persistida, 200", order["shipping_content"])
        self.assertEqual(order["updated_at"], "14/04/2026 às 12:00")
        self.assertGreaterEqual(len(order["activity_items"]), 2)
        self.assertEqual(order["next_step_label"], "Separar e preparar envio")
        self.assertIn("Priorize picking", order["next_step_helper"])
        self.assertIn("Estoque impactado após pagamento", order["inventory_visibility_content"])

    def test_admin_order_views_render_persisted_records_when_present(self):
        Order.objects.filter(number="2048").update(inventory_reserved_at=timezone.now())
        first_item = Order.objects.get(number="2048").items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])
        list_response = self.client.get(reverse("orders:admin-orders-list"))
        detail_response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "#2048")
        self.assertContains(list_response, "Ana Persistida")
        self.assertContains(list_response, "vínculo explícito")
        self.assertContains(list_response, "Impacto de estoque já visível")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/admin_order_detail_page.html")
        self.assertContains(detail_response, "Pedido #2048")
        self.assertContains(detail_response, "Ana Persistida")
        self.assertContains(detail_response, "Rua Persistida, 200")
        self.assertContains(detail_response, "Order.customer")
        self.assertContains(detail_response, "Estoque impactado após pagamento")

    def test_admin_order_detail_surfaces_applied_coupon_snapshot(self):
        Order.objects.filter(number="2048").update(
            coupon_code="PROMO10",
            discount_total="10.00",
            promotion_snapshot={
                "coupon_code": "PROMO10",
                "discount_total": "10.00",
                "source": "cart",
                "validation_result": "coupon-valid",
            },
        )

        order = admin_order_queries.get_order("2048")
        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertTrue(order["coupon_visible"])
        self.assertEqual(order["coupon_code"], "PROMO10")
        self.assertEqual(order["coupon_title"], "Cupom aplicado: PROMO10")
        self.assertEqual(order["coupon_description"], "-R$ 10,00 · origem: cart · validação: coupon-valid")
        self.assertContains(response, "Cupom aplicado: PROMO10")
        self.assertContains(response, "-R$ 10,00 · origem: cart · validação: coupon-valid")

    def test_admin_order_detail_hides_coupon_without_valid_snapshot(self):
        Order.objects.filter(number="2048").update(
            coupon_code="PROMO10",
            discount_total="10.00",
            promotion_snapshot={},
        )

        order = admin_order_queries.get_order("2048")

        self.assertFalse(order["coupon_visible"])
        self.assertEqual(order["coupon_code"], "")

    def test_admin_orders_list_shows_inventory_exception_backlog_summary(self):
        order = Order.objects.get(number="2048")
        conflict_product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Backlog Alta Prioridade",
            slug="produto-backlog-alta-prioridade-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=conflict_product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = ""
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        review_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3098",
            status="pending",
            customer_name="Cliente Revisão",
            customer_email="revisao@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        review_order.items.create(
            title="Item Revisão",
            subtitle="Único",
            meta="SKU REVIEW-001",
            variant_sku="SKU-AUSENTE-REVIEW",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        resolved_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3099",
            status="pending",
            customer_name="Cliente Resolvido",
            customer_email="resolvido@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_reserved_at=timezone.now(),
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_resolved_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        resolved_order.items.create(
            title="Item Resolvido",
            subtitle="Único",
            meta="SKU RESOLVED-001",
            variant_sku="",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        response = self.client.get(reverse("orders:admin-orders-list"))

        self.assertContains(response, "Backlog de exceções:")
        self.assertContains(response, "1 ativa(s), 1 em revisão e 1 resolvida(s)")
        self.assertContains(response, "1 alta, 1 média e 1 baixa")
        self.assertContains(response, "Responsável já visível em 2 pedido(s)")
        self.assertContains(response, "Casos envelhecidos visíveis em 0 pedido(s)")
        self.assertContains(response, "Carga atual por responsável: Operação interna (1).")
        self.assertContains(response, "1 pedido(s) aberto(s) ainda sem responsável.")

    def test_admin_orders_list_shows_owner_backlog_summary_with_aged_cases(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now() - timedelta(days=3)
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = "Operação interna"
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        second_owner_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3104",
            status="pending",
            customer_name="Cliente Owner 2",
            customer_email="owner2@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        second_owner_order.items.create(
            title="Item Owner 2",
            subtitle="Único",
            meta="SKU OWNER2-001",
            variant_sku="SKU-AUSENTE-OWNER2",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        third_owner_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3105",
            status="pending",
            customer_name="Cliente Logística",
            customer_email="logistica@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now() - timedelta(days=4),
            inventory_exception_owner_label="Logística",
            subtotal="10.00",
            total="10.00",
        )
        third_owner_order.items.create(
            title="Item Logística",
            subtitle="Único",
            meta="SKU LOG-001",
            variant_sku="SKU-AUSENTE-LOG",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        response = self.client.get(reverse("orders:admin-orders-list"))

        self.assertContains(response, "Carga atual por responsável: Operação interna (2), Logística (1).")
        self.assertContains(response, "Casos envelhecidos por responsável: Logística (1 envelhecido(s)), Operação interna (1 envelhecido(s)).")

    def test_admin_order_query_service_sorts_inventory_exception_queue_by_state_priority_and_aging(self):
        order = Order.objects.get(number="2048")
        conflict_product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Ordenacao Excecao",
            slug="produto-ordenacao-excecao-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=conflict_product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = ""
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        Order.objects.filter(pk=order.pk).update(updated_at=timezone.now() - timedelta(days=3))
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        review_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3098",
            status="pending",
            customer_name="Cliente Revisão",
            customer_email="revisao@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now() - timedelta(days=3),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        review_order.items.create(
            title="Item Revisão",
            subtitle="Único",
            meta="SKU REVIEW-001",
            variant_sku="SKU-AUSENTE-REVIEW",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        resolved_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3099",
            status="pending",
            customer_name="Cliente Resolvido",
            customer_email="resolvido@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_reserved_at=timezone.now(),
            inventory_exception_under_review_at=timezone.now() - timedelta(hours=2),
            inventory_exception_resolved_at=timezone.now() - timedelta(hours=1),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        resolved_order.items.create(
            title="Item Resolvido",
            subtitle="Único",
            meta="SKU RESOLVED-001",
            variant_sku="",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        no_exception_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3100",
            status="paid",
            customer_name="Cliente Estável",
            customer_email="estavel@hubx.market",
            payment_status="Confirmado",
            shipping_status="Preparando envio",
            fulfillment_status_label="Separando itens",
            fulfillment_status_variant="info",
            inventory_reserved_at=timezone.now(),
            subtotal="10.00",
            total="10.00",
        )
        no_exception_order.items.create(
            title="Item Estável",
            subtitle="Único",
            meta="SKU ESTAVEL-001",
            variant_sku="RUNNER-ESTAVEL-001",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        orders = admin_order_queries.list_orders()
        visible_numbers = [str(item["order_number"]) for item in orders if str(item["order_number"]) in {"2048", "3098", "3099", "3100"}]

        self.assertEqual(visible_numbers[:4], ["2048", "3098", "3099", "3100"])

    def test_admin_order_query_service_groups_assigned_cases_by_owner_and_prioritizes_within_owner(self):
        base_order = Order.objects.get(number="2048")
        base_order.status = "pending"
        base_order.payment_status = "Pagamento pendente"
        base_order.fulfillment_status_label = "Aguardando pagamento"
        base_order.fulfillment_status_variant = "warning"
        base_order.shipping_status = "Aguardando confirmação"
        base_order.inventory_reserved_at = None
        base_order.inventory_recovered_at = None
        base_order.inventory_finalized_at = None
        base_order.inventory_exception_under_review_at = timezone.now() - timedelta(days=3)
        base_order.inventory_exception_resolved_at = None
        base_order.inventory_exception_owner_label = "Operação interna"
        base_order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        base_item = base_order.items.order_by("id").first()
        base_item.variant_sku = "SKU-AUSENTE-BASE"
        base_item.save(update_fields=["variant_sku", "updated_at"])

        operation_recent_order = Order.objects.create(
            tenant=base_order.tenant,
            customer=base_order.customer,
            number="3106",
            status="pending",
            customer_name="Cliente Operacao Recente",
            customer_email="operacao-recente@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        operation_recent_order.items.create(
            title="Item Operacao Recente",
            subtitle="Único",
            meta="SKU OPER-RECENT-001",
            variant_sku="SKU-AUSENTE-OPER-RECENT",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        logistic_order = Order.objects.create(
            tenant=base_order.tenant,
            customer=base_order.customer,
            number="3107",
            status="pending",
            customer_name="Cliente Logistica",
            customer_email="logistica-prioridade@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now() - timedelta(days=4),
            inventory_exception_owner_label="Logística",
            subtotal="10.00",
            total="10.00",
        )
        logistic_order.items.create(
            title="Item Logistica",
            subtitle="Único",
            meta="SKU LOG-PRIORITY-001",
            variant_sku="SKU-AUSENTE-LOG-PRIORITY",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        orders = admin_order_queries.list_orders()
        visible_numbers = [
            str(item["order_number"])
            for item in orders
            if str(item["order_number"]) in {"2048", "3106", "3107"}
        ]

        self.assertEqual(visible_numbers[:3], ["2048", "3106", "3107"])

    def test_admin_order_list_shows_inventory_exception_owner_workload_visibility(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = "Operação interna"
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        second_review_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3101",
            status="pending",
            customer_name="Cliente Owner Load",
            customer_email="owner-load@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        second_review_order.items.create(
            title="Item Owner Load",
            subtitle="Único",
            meta="SKU OWNER-LOAD-001",
            variant_sku="SKU-AUSENTE-OWNER-LOAD",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        response = self.client.get(reverse("orders:admin-orders-list"))

        self.assertContains(response, "Carga atual por responsável: Operação interna (2).")
        self.assertContains(response, "Operação interna conduz 2 caso(s) aberto(s) nesta fila.")
        self.assertContains(response, "Responsável: Operação interna · 2 caso(s) aberto(s)")

    def test_admin_order_list_quick_filter_returns_only_unassigned_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = ""
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        assigned_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3102",
            status="pending",
            customer_name="Cliente Assigned",
            customer_email="assigned@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_owner_label="Operação interna",
            subtotal="10.00",
            total="10.00",
        )
        assigned_order.items.create(
            title="Item Assigned",
            subtitle="Único",
            meta="SKU ASSIGNED-001",
            variant_sku="SKU-AUSENTE-ASSIGNED",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "unassigned"})

        self.assertContains(response, "#2048")
        self.assertNotContains(response, "#3102")
        self.assertContains(response, "Mostrando pedidos com exceção aberta que ainda não receberam responsável operacional.")
        self.assertContains(response, "Filtro rápido ativo: Sem responsável.")

    def test_admin_order_list_quick_filter_returns_only_assigned_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = "Operação interna"
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        unassigned_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3103",
            status="pending",
            customer_name="Cliente Unassigned",
            customer_email="unassigned@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            subtotal="10.00",
            total="10.00",
        )
        unassigned_order.items.create(
            title="Item Unassigned",
            subtitle="Único",
            meta="SKU UNASSIGNED-001",
            variant_sku="SKU-AUSENTE-UNASSIGNED",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "assigned"})

        self.assertContains(response, "#2048")
        self.assertNotContains(response, "#3103")
        self.assertContains(response, "Mostrando pedidos com exceção aberta que já têm responsável operacional visível.")
        self.assertContains(response, "Filtro rápido ativo: Com responsável.")

    def test_admin_order_list_unassigned_quick_filter_shows_useful_empty_state(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = ""
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = ""
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "unassigned"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma exceção sem responsável")
        self.assertContains(response, "sem responsável operacional visível")
        self.assertContains(response, "Filtro rápido ativo: Sem responsável. 0 pedido(s) nesta visão.")

    def test_admin_order_query_service_reports_inventory_exception_when_variant_is_missing(self):
        order_model = Order.objects.get(number="2048")
        order_model.status = "pending"
        order_model.payment_status = "Pagamento pendente"
        order_model.fulfillment_status_label = "Aguardando pagamento"
        order_model.fulfillment_status_variant = "warning"
        order_model.shipping_status = "Aguardando confirmação"
        order_model.inventory_reserved_at = None
        order_model.inventory_recovered_at = None
        order_model.inventory_finalized_at = None
        order_model.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "updated_at",
            ]
        )
        first_item = order_model.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])
        Order.objects.filter(pk=order_model.pk).update(updated_at=timezone.now() - timedelta(days=3))

        order = admin_order_queries.get_order("2048")

        self.assertIn("Exceção de estoque: variante SKU-AUSENTE-001 não pôde ser resolvida", order["inventory_exception_content"])
        self.assertEqual(order["activity_items"][0]["title"], "Exceção de estoque identificada")
        self.assertEqual(order["inventory_exception_guidance_label"], "Revisar vínculo da variante")
        self.assertIn("Confirme o SKU do item", order["inventory_exception_guidance_helper"])
        self.assertEqual(order["inventory_exception_priority_label"], "Média prioridade")
        self.assertIn("Confirme o SKU correto", order["inventory_exception_priority_helper"])

    def test_admin_order_views_render_inventory_exception_when_stock_conflicts(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Conflito Estoque",
            slug="produto-conflito-estoque-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        list_response = self.client.get(reverse("orders:admin-orders-list"))
        detail_response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(list_response, "Exceções de estoque visíveis em 1 pedido(s)")
        self.assertContains(detail_response, "Exceção de estoque: variante RUNNER-PERSIST-001 tem apenas 0 unidade(s) livre(s)")
        self.assertContains(detail_response, "Exceção de estoque identificada")
        self.assertContains(detail_response, "Tratar conflito de estoque")
        self.assertContains(detail_response, "Revise saldo livre, prioridade operacional")
        self.assertContains(list_response, "Exceção ativa")
        self.assertContains(list_response, "Alta prioridade")
        self.assertContains(list_response, "Saldo livre insuficiente para o pedido")

    def test_admin_order_query_service_marks_old_active_exception_as_aged(self):
        order_model = Order.objects.get(number="2048")
        order_model.updated_at = timezone.now() - timedelta(days=3)
        label, helper = DjangoOrmOrderRepository._build_inventory_exception_aging(
            order=order_model,
            inventory_exception_content="Exceção de estoque: variante SKU-AUSENTE-001 não pôde ser resolvida no tenant atual.",
            inventory_exception_marker_label="",
        )

        self.assertEqual(label, "Exceção envelhecida")
        self.assertIn("Priorize tratamento", helper)

    def test_admin_order_detail_shows_stale_review_aging_when_exception_is_old(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now() - timedelta(days=3)
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(response, "Vale reavaliar prioridade, owner e fechamento manual")

    def test_admin_order_detail_shows_recent_resolution_aging(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.inventory_exception_under_review_at = timezone.now() - timedelta(hours=2)
        order.inventory_exception_resolved_at = timezone.now() - timedelta(hours=1)
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(response, "Exceção resolvida há 1 h")
        self.assertContains(response, "Mantenha apenas conferência leve")

    def test_admin_order_list_quick_filter_returns_only_active_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Quick Filter Excecao",
            slug="produto-quick-filter-excecao-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        resolved_order = Order.objects.create(
            tenant=order.tenant,
            customer=order.customer,
            number="3099",
            status="pending",
            customer_name="Cliente Resolvido",
            customer_email="resolvido@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            inventory_reserved_at=timezone.now(),
            inventory_exception_under_review_at=timezone.now(),
            inventory_exception_resolved_at=timezone.now(),
            subtotal="10.00",
            total="10.00",
        )
        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "active"})

        self.assertContains(response, "#2048")
        self.assertNotContains(response, "#3099")
        self.assertContains(response, "Mostrando pedidos com exceção de estoque ainda ativa")
        self.assertContains(response, "Filtro rápido ativo: Exceção ativa.")
        self.assertContains(response, "1 pedido(s) nesta visão")
        self.assertContains(response, "Use Limpar para voltar à lista completa.")
        self.assertContains(response, "Marcar revisão na visão")

    def test_admin_order_list_quick_filter_returns_only_reviewed_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "review"})

        self.assertContains(response, "#2048")
        self.assertContains(response, "Mostrando pedidos com exceção já marcada em revisão")
        self.assertContains(response, "Visão atual: Em revisão · 1 pedido(s).")

    def test_admin_order_list_quick_filter_returns_only_resolved_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = timezone.now()
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "resolved"})

        self.assertContains(response, "#2048")
        self.assertContains(response, "Mostrando pedidos com exceção já normalizada")
        self.assertContains(response, "Filtro rápido ativo: Resolvidas.")

    def test_admin_order_list_quick_filter_returns_only_high_priority_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Quick Filter Alta Prioridade",
            slug="produto-quick-filter-alta-prioridade-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "high_priority"})

        self.assertContains(response, "#2048")
        self.assertContains(response, "Mostrando pedidos com exceção de estoque em alta prioridade operacional.")
        self.assertContains(response, "Filtro rápido ativo: Alta prioridade.")

    def test_admin_order_list_quick_filter_returns_only_medium_priority_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "medium_priority"})

        self.assertContains(response, "#2048")
        self.assertContains(response, "Mostrando pedidos com exceção de estoque em média prioridade operacional.")
        self.assertContains(response, "Filtro rápido ativo: Média prioridade.")

    def test_admin_order_list_quick_filter_returns_only_low_priority_inventory_exceptions(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = timezone.now()
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "low_priority"})

        self.assertContains(response, "#2048")
        self.assertContains(response, "Mostrando pedidos com exceção já estável ou de baixa urgência operacional.")
        self.assertContains(response, "Filtro rápido ativo: Baixa prioridade.")

    def test_admin_order_list_ignores_unknown_inventory_exception_quick_filter(self):
        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "unknown"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#2048")
        self.assertNotContains(response, "Filtro rápido ativo:")

    def test_admin_order_list_active_exception_quick_filter_shows_useful_empty_state(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.save(update_fields=["inventory_reserved_at", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "active"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma exceção ativa agora")
        self.assertContains(response, "A fila não tem pedidos com exceção de estoque ainda aberta")
        self.assertContains(response, "Filtro rápido ativo: Exceção ativa. 0 pedido(s) nesta visão.")

    def test_admin_order_list_review_exception_quick_filter_empty_state_includes_search_context(self):
        response = self.client.get(
            reverse("orders:admin-orders-list"),
            {"quick_filter": "review", "q": "inexistente"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma exceção em revisão")
        self.assertContains(response, "Busca atual:")
        self.assertContains(response, "inexistente")
        self.assertContains(response, "Filtro rápido ativo: Em revisão. 0 pedido(s) nesta visão.")

    def test_admin_order_list_high_priority_quick_filter_shows_useful_empty_state(self):
        response = self.client.get(reverse("orders:admin-orders-list"), {"quick_filter": "high_priority"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma exceção de alta prioridade")
        self.assertContains(response, "tratamento prioritário")
        self.assertContains(response, "Filtro rápido ativo: Alta prioridade. 0 pedido(s) nesta visão.")

    def test_admin_order_mark_inventory_exception_under_review_works(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "mark_inventory_exception_under_review"},
        )

        self.assertRedirects(
            response,
            "/ops/orders/2048/?result=inventory-exception-under-review",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNotNone(order.inventory_exception_under_review_at)
        self.assertEqual(order.inventory_exception_owner_label, "Operação interna")
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="inventory_exception_marked_under_review",
                source_type="admin_action",
            ).exists()
        )

        detail_response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))
        self.assertContains(detail_response, "Exceção em revisão")
        self.assertContains(detail_response, "Vínculo da variante já está em revisão")
        self.assertContains(detail_response, "Última marcação de revisão")
        self.assertContains(detail_response, "Responsável atual pela exceção: Operação interna.")

        list_response = self.client.get(reverse("orders:admin-orders-list"))
        self.assertContains(list_response, "Em revisão")
        self.assertContains(list_response, "Responsável: Operação interna")

    def test_admin_order_list_quick_action_marks_inventory_exception_under_review_and_returns_to_list(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {
                "action_type": "mark_inventory_exception_under_review",
                "next": "/ops/orders/?quick_filter=active&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/orders/?quick_filter=active&page=1&result=inventory-exception-under-review",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNotNone(order.inventory_exception_under_review_at)

        list_response = self.client.get(
            reverse("orders:admin-orders-list"),
            {"quick_filter": "active", "result": "inventory-exception-under-review"},
        )
        self.assertContains(list_response, "Exceção de estoque marcada em revisão.")

    def test_admin_order_list_bulk_action_marks_inventory_exception_under_review(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = None
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {
                "action_type": "bulk_mark_inventory_exception_under_review",
                "order_numbers": "2048",
                "next": "/ops/orders/?quick_filter=active&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/orders/?quick_filter=active&page=1&result=bulk-inventory-exception-under-review",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNotNone(order.inventory_exception_under_review_at)

        list_response = self.client.get(
            reverse("orders:admin-orders-list"),
            {"quick_filter": "active", "result": "bulk-inventory-exception-under-review"},
        )
        self.assertContains(list_response, "Ação em lote concluída: exceções elegíveis marcadas em revisão")

    def test_admin_order_mark_inventory_exception_resolved_requires_exception_to_be_cleared(self):
        order = Order.objects.get(number="2048")
        order.inventory_exception_under_review_at = timezone.now()
        order.save(update_fields=["inventory_exception_under_review_at", "updated_at"])
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "mark_inventory_exception_resolved"},
        )

        self.assertRedirects(
            response,
            "/ops/orders/2048/?result=inventory-exception-still-active",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNone(order.inventory_exception_resolved_at)

    def test_admin_order_mark_inventory_exception_resolved_works_after_normalization(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Excecao Resolvida",
            slug="produto-excecao-resolvida-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=3,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.inventory_reserved_at = timezone.now()
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "mark_inventory_exception_resolved"},
        )

        self.assertRedirects(
            response,
            "/ops/orders/2048/?result=inventory-exception-resolved",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNotNone(order.inventory_exception_resolved_at)
        self.assertEqual(order.inventory_exception_owner_label, "Operação interna")
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="inventory_exception_marked_resolved",
                source_type="admin_action",
            ).exists()
        )

        detail_response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))
        self.assertContains(detail_response, "Exceção resolvida")
        self.assertContains(detail_response, "Exceção já normalizada")
        self.assertContains(detail_response, "Tratamento manual concluído")
        self.assertContains(detail_response, "Responsável atual pela exceção: Operação interna.")

        list_response = self.client.get(reverse("orders:admin-orders-list"))
        self.assertContains(list_response, "Resolvida")
        self.assertContains(list_response, "Último responsável: Operação interna.")

    def test_admin_order_list_quick_action_marks_inventory_exception_resolved_and_returns_to_list(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Quick Action Resolvida",
            slug="produto-quick-action-resolvida-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=2,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.inventory_reserved_at = timezone.now()
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {
                "action_type": "mark_inventory_exception_resolved",
                "next": "/ops/orders/?quick_filter=resolved&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/orders/?quick_filter=resolved&page=1&result=inventory-exception-resolved",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNotNone(order.inventory_exception_resolved_at)

        list_response = self.client.get(
            reverse("orders:admin-orders-list"),
            {"quick_filter": "resolved", "result": "inventory-exception-resolved"},
        )
        self.assertContains(list_response, "Exceção de estoque marcada como resolvida.")

    def test_admin_order_reassign_inventory_exception_owner_works(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="maria.ops", password="secret123", first_name="Maria", last_name="Ops")
        self.client.force_login(user)

        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = "Operação interna"
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "reassign_inventory_exception_owner"},
        )

        self.assertRedirects(
            response,
            "/ops/orders/2048/?result=inventory-exception-owner-reassigned",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertEqual(order.inventory_exception_owner_label, "Maria Ops")
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="inventory_exception_owner_reassigned",
                actor_label="Maria Ops",
            ).exists()
        )

    def test_admin_order_list_quick_action_reassigns_inventory_exception_owner_and_returns_to_list(self):
        user_model = get_user_model()
        user = user_model.objects.create_user(username="joao.ops", password="secret123", first_name="João", last_name="Ops")
        self.client.force_login(user)

        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.inventory_reserved_at = None
        order.inventory_recovered_at = None
        order.inventory_finalized_at = None
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.inventory_exception_owner_label = "Operação interna"
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "inventory_recovered_at",
                "inventory_finalized_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "inventory_exception_owner_label",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "SKU-AUSENTE-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {
                "action_type": "reassign_inventory_exception_owner",
                "next": "/ops/orders/?quick_filter=assigned&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/orders/?quick_filter=assigned&page=1&result=inventory-exception-owner-reassigned",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertEqual(order.inventory_exception_owner_label, "João Ops")

        list_response = self.client.get(
            reverse("orders:admin-orders-list"),
            {"quick_filter": "assigned", "result": "inventory-exception-owner-reassigned"},
        )
        self.assertContains(list_response, "Responsável da exceção atualizado.")

    def test_admin_order_list_bulk_action_marks_inventory_exception_resolved(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Bulk Resolvida",
            slug="produto-bulk-resolvida-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=2,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.inventory_reserved_at = timezone.now()
        order.inventory_exception_under_review_at = timezone.now()
        order.inventory_exception_resolved_at = None
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_exception_under_review_at",
                "inventory_exception_resolved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {
                "action_type": "bulk_mark_inventory_exception_resolved",
                "order_numbers": "2048",
                "next": "/ops/orders/?quick_filter=resolved&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/orders/?quick_filter=resolved&page=1&result=bulk-inventory-exception-resolved",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertIsNotNone(order.inventory_exception_resolved_at)

        list_response = self.client.get(
            reverse("orders:admin-orders-list"),
            {"quick_filter": "resolved", "result": "bulk-inventory-exception-resolved"},
        )
        self.assertContains(list_response, "Ação em lote concluída: exceções elegíveis marcadas como resolvidas")

    def test_admin_order_status_update_works(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "order_status", "status": "canceled"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-status-updated", fetch_redirect_response=False)
        order = Order.objects.get(number="2048")
        self.assertEqual(order.status, "canceled")
        history = OrderStatusHistory.objects.get(order=order, event_type="order_status_updated")
        self.assertEqual(history.source_type, "admin_action")
        self.assertEqual(history.source_label, "Admin Orders")
        self.assertEqual(history.actor_label, "Operação interna")

    def test_admin_order_fulfillment_status_update_works(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "fulfillment_status", "fulfillment_status": "completed"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=fulfillment-status-updated", fetch_redirect_response=False)
        order = Order.objects.get(number="2048")
        self.assertEqual(order.fulfillment_status_label, "Concluído")
        self.assertEqual(order.fulfillment_status_variant, "success")
        history = OrderStatusHistory.objects.get(order=order, event_type="fulfillment_status_updated")
        self.assertEqual(history.source_type, "admin_action")
        self.assertEqual(history.source_label, "Admin Orders")
        self.assertEqual(history.actor_label, "Operação interna")

    def test_admin_order_invalid_updates_are_handled_safely(self):
        original = Order.objects.get(number="2048")

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "order_status", "status": "unsafe-status"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-status-invalid", fetch_redirect_response=False)
        order = Order.objects.get(number="2048")
        self.assertEqual(order.status, original.status)

    def test_admin_order_detail_view_shows_action_feedback_and_forms(self):
        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}), {"result": "order-status-updated"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status do pedido atualizado com sucesso.")
        self.assertContains(response, 'name="action_type" value="order_status"')
        self.assertContains(response, 'name="action_type" value="fulfillment_status"')
        self.assertContains(response, 'name="action_type" value="start_fulfillment"')
        self.assertContains(response, 'name="action_type" value="start_shipping"')
        self.assertContains(response, 'name="action_type" value="complete_delivery"')
        self.assertContains(response, 'name="action_type" value="cancel_order"')
        self.assertContains(response, "Ação simples para interromper o pedido")

    def test_admin_order_detail_shows_next_step_guidance_for_paid_order(self):
        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Próximo passo: Separar e preparar envio.")
        self.assertContains(response, "Priorize picking, conferência e atualização da operação")

    def test_admin_order_cancel_action_works(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-canceled", fetch_redirect_response=False)
        order = Order.objects.get(number="2048")
        self.assertEqual(order.status, "canceled")
        history = OrderStatusHistory.objects.get(order=order, event_type="order_canceled")
        self.assertEqual(history.source_type, "admin_action")
        self.assertEqual(history.title, "Pedido cancelado")

    def test_admin_order_cancel_reverses_coupon_redemption(self):
        order = Order.objects.get(number="2048")
        coupon = Coupon.objects.create(
            tenant=order.tenant,
            code="PROMO10",
            status=Coupon.Status.ACTIVE,
            discount_type=Coupon.DiscountType.FIXED,
            discount_value="10.00",
        )
        redemption = CouponRedemption.objects.create(
            tenant=order.tenant,
            coupon=coupon,
            order=order,
            customer_id=order.customer_id,
            coupon_code_snapshot="PROMO10",
            discount_total_snapshot="10.00",
            promotion_snapshot={"coupon_code": "PROMO10"},
            source_type="application_command",
            source_label="Coupon Redemption Commands",
        )

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-canceled", fetch_redirect_response=False)
        redemption.refresh_from_db()
        self.assertEqual(redemption.status, CouponRedemption.Status.REVERSED)
        self.assertIsNotNone(redemption.reversed_at)
        self.assertEqual(redemption.source_label, "Admin Orders")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_order_cancel_action_scopes_command_by_request_tenant(self):
        primary_order = Order.objects.get(number="2048")
        secondary_tenant = Tenant.objects.create(
            name="Hubx Ops Secondary Tenant",
            slug="hubx-ops-secondary-tenant",
            subdomain="hubx-ops-secondary-tenant",
        )
        secondary_order = Order.objects.create(
            tenant=secondary_tenant,
            number="2048",
            status="pending",
            customer_name="Cliente Operação Secundária",
            customer_email="secundaria@hubx.market",
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            subtotal="10.00",
            total="10.00",
        )
        secondary_order.items.create(
            title="Item Secundário",
            subtitle="Único",
            meta="SKU OTHER-OPS-001",
            price_snapshot="10.00",
            quantity=1,
            quantity_readonly=True,
        )

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
            HTTP_HOST="hubx-ops-secondary-tenant.hubx.market",
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-canceled", fetch_redirect_response=False)
        primary_order.refresh_from_db()
        secondary_order.refresh_from_db()
        self.assertEqual(primary_order.status, "paid")
        self.assertEqual(secondary_order.status, "canceled")
        self.assertTrue(
            OrderStatusHistory.objects.filter(order=secondary_order, event_type="order_canceled").exists()
        )

    def test_admin_order_cancel_recovers_inventory_when_reservation_exists(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Restock",
            slug="produto-restock-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=4,
            reserved_stock=3,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.inventory_reserved_at = timezone.now()
        order.save(update_fields=["inventory_reserved_at", "updated_at"])
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-canceled", fetch_redirect_response=False)
        order.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(order.status, "canceled")
        self.assertIsNotNone(order.inventory_recovered_at)
        self.assertEqual(variant.stock, 5)
        self.assertEqual(variant.reserved_stock, 2)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="inventory_recovered_after_cancel",
                source_type="admin_action",
            ).exists()
        )

    def test_admin_order_detail_reports_inventory_recovery_when_present(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.inventory_recovered_at = timezone.now()
        order.status = "canceled"
        order.save(update_fields=["inventory_reserved_at", "inventory_recovered_at", "status", "updated_at"])
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(response, "Estoque devolvido após cancelamento")

    def test_admin_order_complete_delivery_finalizes_inventory_reservation(self):
        order = Order.objects.get(number="2048")
        product = Product.objects.create(
            tenant=order.tenant,
            name="Produto Finalização",
            slug="produto-finalizacao-admin",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        variant = ProductVariant.objects.create(
            product=product,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            stock=4,
            reserved_stock=3,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        order.status = "shipped"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.shipping_status = "Em trânsito"
        order.inventory_reserved_at = timezone.now()
        order.save(
            update_fields=[
                "status",
                "payment_status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "inventory_reserved_at",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "complete_delivery"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=delivery-completed", fetch_redirect_response=False)
        order.refresh_from_db()
        variant.refresh_from_db()
        self.assertEqual(order.fulfillment_status_label, "Concluído")
        self.assertEqual(order.shipping_status, "Entregue")
        self.assertIsNotNone(order.inventory_finalized_at)
        self.assertEqual(variant.stock, 4)
        self.assertEqual(variant.reserved_stock, 2)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="inventory_finalized_after_delivery",
                source_type="admin_action",
            ).exists()
        )

    def test_admin_order_detail_reports_inventory_finalization_when_present(self):
        order = Order.objects.get(number="2048")
        order.inventory_reserved_at = timezone.now()
        order.inventory_finalized_at = timezone.now()
        order.status = "shipped"
        order.fulfillment_status_label = "Concluído"
        order.fulfillment_status_variant = "success"
        order.shipping_status = "Entregue"
        order.save(
            update_fields=[
                "inventory_reserved_at",
                "inventory_finalized_at",
                "status",
                "fulfillment_status_label",
                "fulfillment_status_variant",
                "shipping_status",
                "updated_at",
            ]
        )
        first_item = order.items.order_by("id").first()
        first_item.variant_sku = "RUNNER-PERSIST-001"
        first_item.save(update_fields=["variant_sku", "updated_at"])

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(response, "Estoque finalizado após entrega")

    def test_admin_order_status_update_is_blocked_after_inventory_finalization(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.inventory_finalized_at = timezone.now()
        order.save(update_fields=["status", "inventory_finalized_at", "updated_at"])

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "order_status", "status": "canceled"},
        )

        self.assertRedirects(
            response,
            "/ops/orders/2048/?result=order-status-finalized-blocked",
            fetch_redirect_response=False,
        )
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertFalse(OrderStatusHistory.objects.filter(order=order, event_type="order_status_updated").exists())

    def test_admin_order_repeated_cancel_is_handled_safely(self):
        order = Order.objects.get(number="2048")
        order.status = "canceled"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-already-canceled", fetch_redirect_response=False)
        self.assertEqual(OrderStatusHistory.objects.filter(order=order, event_type="order_canceled").count(), 0)

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "order-already-canceled"},
        )
        self.assertContains(detail_response, "Cancelamento ignorado: o pedido já estava cancelado.")
        self.assertContains(detail_response, "Esse pedido já está cancelado; nenhuma nova ação é necessária.")

    def test_admin_order_cancel_rejects_shipped_orders_safely(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-cancel-blocked", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertEqual(OrderStatusHistory.objects.filter(order=order, event_type="order_canceled").count(), 0)

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "order-cancel-blocked"},
        )
        self.assertContains(detail_response, "pedidos enviados exigem fluxo operacional específico")
        self.assertContains(detail_response, "Pedido já enviado exige tratamento operacional específico")

    def test_admin_order_start_fulfillment_works_after_payment_confirmation(self):
        order = Order.objects.get(number="2048")
        order.status = "paid"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Pagamento confirmado"
        order.fulfillment_status_variant = "success"
        order.shipping_status = "Aguardando preparação"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_fulfillment"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=fulfillment-started", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.fulfillment_status_label, "Separando itens")
        self.assertEqual(order.fulfillment_status_variant, "info")
        self.assertEqual(order.shipping_status, "Preparando envio")
        history = OrderStatusHistory.objects.get(order=order, event_type="fulfillment_started")
        self.assertEqual(history.source_type, "admin_action")
        self.assertEqual(history.title, "Preparação iniciada")

    def test_admin_order_start_fulfillment_is_safe_when_already_started(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_fulfillment"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=fulfillment-already-started", fetch_redirect_response=False)
        self.assertEqual(OrderStatusHistory.objects.filter(order__number="2048", event_type="fulfillment_started").count(), 0)

    def test_admin_order_start_fulfillment_blocks_pending_payment(self):
        order = Order.objects.get(number="2048")
        order.status = "pending"
        order.payment_status = "Pagamento pendente"
        order.fulfillment_status_label = "Aguardando pagamento"
        order.fulfillment_status_variant = "warning"
        order.shipping_status = "Aguardando confirmação"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_fulfillment"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=fulfillment-start-blocked", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.fulfillment_status_label, "Aguardando pagamento")

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "fulfillment-start-blocked"},
        )
        self.assertContains(detail_response, "confirme pagamento")
        self.assertContains(detail_response, "antes de liberar expedição")

    def test_admin_order_start_shipping_works_after_preparation(self):
        order = Order.objects.get(number="2048")
        order.status = "paid"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Separando itens"
        order.fulfillment_status_variant = "info"
        order.shipping_status = "Preparando envio"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_shipping"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=shipping-started", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertEqual(order.fulfillment_status_label, "Em trânsito")
        self.assertEqual(order.fulfillment_status_variant, "shipped")
        self.assertEqual(order.shipping_status, "Em trânsito")
        self.assertEqual(order.shipment.status, Shipment.Status.SENT)
        history = OrderStatusHistory.objects.get(order=order, event_type="shipping_started")
        self.assertEqual(history.source_type, "admin_action")
        self.assertEqual(history.title, "Envio iniciado")

    def test_admin_order_start_shipping_is_safe_when_already_in_transit(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.shipping_status = "Em trânsito"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_shipping"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=shipping-start-blocked", fetch_redirect_response=False)
        self.assertEqual(OrderStatusHistory.objects.filter(order__number="2048", event_type="shipping_started").count(), 0)

    def test_admin_order_start_shipping_blocks_before_preparation(self):
        order = Order.objects.get(number="2048")
        order.status = "paid"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Pagamento confirmado"
        order.fulfillment_status_variant = "success"
        order.shipping_status = "Aguardando preparação"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_shipping"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=shipping-start-blocked", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.status, "paid")

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "shipping-start-blocked"},
        )
        self.assertContains(detail_response, "conclua pagamento e preparo")
        self.assertContains(detail_response, "antes de liberar trânsito")

    def test_admin_order_complete_delivery_works_after_transit(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.shipping_status = "Em trânsito"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "complete_delivery"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=delivery-completed", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.status, "shipped")
        self.assertEqual(order.fulfillment_status_label, "Concluído")
        self.assertEqual(order.fulfillment_status_variant, "success")
        self.assertEqual(order.shipping_status, "Entregue")
        self.assertEqual(order.shipment.status, Shipment.Status.DELIVERED)
        history = OrderStatusHistory.objects.get(order=order, event_type="delivery_completed")
        self.assertEqual(history.source_type, "admin_action")
        self.assertEqual(history.title, "Entrega confirmada")

    def test_admin_order_complete_delivery_is_safe_when_already_completed(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.fulfillment_status_label = "Concluído"
        order.fulfillment_status_variant = "success"
        order.shipping_status = "Entregue"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "complete_delivery"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=delivery-already-completed", fetch_redirect_response=False)
        self.assertEqual(OrderStatusHistory.objects.filter(order__number="2048", event_type="delivery_completed").count(), 0)

    def test_admin_order_complete_delivery_blocks_before_transit(self):
        order = Order.objects.get(number="2048")
        order.status = "paid"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Separando itens"
        order.fulfillment_status_variant = "info"
        order.shipping_status = "Preparando envio"
        order.save()

        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "complete_delivery"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=delivery-completion-blocked", fetch_redirect_response=False)
        order.refresh_from_db()
        self.assertEqual(order.fulfillment_status_label, "Separando itens")

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "delivery-completion-blocked"},
        )
        self.assertContains(detail_response, "leve o pedido a trânsito")
        self.assertContains(detail_response, "antes de encerrar a operação")

    def test_admin_order_detail_shows_terminal_guidance_for_shipped_order(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.shipping_status = "Em trânsito"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.save()

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(response, "Próximo passo: Acompanhar transporte.")
        self.assertContains(response, "monitorar rastreio e tratar exceções de entrega")

    def test_admin_order_detail_shows_terminal_guidance_for_canceled_order(self):
        order = Order.objects.get(number="2048")
        order.status = "canceled"
        order.save()

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertContains(response, "Próximo passo: Pedido encerrado.")
        self.assertContains(response, "Nenhuma nova ação operacional é necessária")

    def test_admin_order_repeated_status_update_gives_safe_feedback(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "order_status", "status": "paid"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=order-status-unchanged", fetch_redirect_response=False)
        self.assertEqual(OrderStatusHistory.objects.filter(order__number="2048", event_type="order_status_updated").count(), 0)

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "order-status-unchanged"},
        )
        self.assertContains(detail_response, "o pedido já estava nesse status")

    def test_admin_order_repeated_fulfillment_update_gives_safe_feedback(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "fulfillment_status", "fulfillment_status": "picking"},
        )

        self.assertRedirects(response, "/ops/orders/2048/?result=fulfillment-status-unchanged", fetch_redirect_response=False)
        self.assertEqual(OrderStatusHistory.objects.filter(order__number="2048", event_type="fulfillment_status_updated").count(), 0)

        detail_response = self.client.get(
            reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}),
            {"result": "fulfillment-status-unchanged"},
        )
        self.assertContains(detail_response, "a operação já estava nesse status")

    def test_admin_order_status_change_appears_in_timeline(self):
        order = Order.objects.get(number="2048")
        OrderStatusHistory.objects.create(
            order=order,
            event_type="order_status_updated",
            source_type="admin_action",
            source_label="Admin Orders",
            actor_label="Operação interna",
            title="Status do pedido atualizado",
            description="Status alterado de Pago para Cancelado.",
            badge_label="Pedido",
            badge_variant="danger",
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status do pedido atualizado")
        self.assertContains(response, "Status alterado de Pago para Cancelado.")
        self.assertContains(response, "Origem: Admin Orders.")
        self.assertContains(response, "Responsável: Operação interna.")

    def test_admin_order_fulfillment_change_appears_in_timeline(self):
        order = Order.objects.get(number="2048")
        OrderStatusHistory.objects.create(
            order=order,
            event_type="fulfillment_status_updated",
            source_type="admin_action",
            source_label="Admin Orders",
            actor_label="Operação interna",
            title="Status operacional atualizado",
            description="Operação alterada de Separando itens para Concluído.",
            badge_label="Operação",
            badge_variant="success",
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status operacional atualizado")
        self.assertContains(response, "Operação alterada de Separando itens para Concluído.")
        self.assertContains(response, "Origem: Admin Orders.")
        self.assertContains(response, "Responsável: Operação interna.")

    def test_admin_order_fulfillment_start_appears_in_timeline(self):
        order = Order.objects.get(number="2048")
        order.status = "paid"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Pagamento confirmado"
        order.fulfillment_status_variant = "success"
        order.shipping_status = "Aguardando preparação"
        order.save()

        self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_fulfillment"},
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Preparação iniciada")
        self.assertContains(response, "Pedido liberado para separação")
        self.assertContains(response, "Origem: Admin Orders.")

    def test_admin_order_shipping_start_appears_in_timeline(self):
        order = Order.objects.get(number="2048")
        order.status = "paid"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Separando itens"
        order.fulfillment_status_variant = "info"
        order.shipping_status = "Preparando envio"
        order.save()

        self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "start_shipping"},
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Envio iniciado")
        self.assertContains(response, "Pedido liberado para trânsito")
        self.assertContains(response, "Origem: Admin Orders.")

    def test_admin_order_delivery_completion_appears_in_timeline(self):
        order = Order.objects.get(number="2048")
        order.status = "shipped"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.shipping_status = "Em trânsito"
        order.save()

        self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "complete_delivery"},
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrega confirmada")
        self.assertContains(response, "encerrado operacionalmente")
        self.assertContains(response, "Origem: Admin Orders.")

    def test_admin_order_timeline_keeps_old_history_rows_safe_without_attribution(self):
        order = Order.objects.get(number="2048")
        OrderStatusHistory.objects.create(
            order=order,
            event_type="order_status_updated",
            title="Status do pedido atualizado",
            description="Status alterado de Pago para Cancelado.",
            badge_label="Pedido",
            badge_variant="danger",
        )

        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status alterado de Pago para Cancelado.")
        self.assertNotContains(response, "Origem:")
        self.assertNotContains(response, "Responsável:")

    def test_admin_order_cancel_appears_in_timeline(self):
        response = self.client.post(
            reverse("orders:admin-order-update", kwargs={"order_number": "2048"}),
            {"action_type": "cancel_order"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedido cancelado")
        self.assertContains(response, "Pedido cancelado a partir do status")
        self.assertContains(response, "Origem: Admin Orders.")

    def test_admin_order_timeline_stays_safe_when_no_history_exists(self):
        response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Snapshot persistido sincronizado")
        self.assertContains(response, "Fila operacional atualizada")
