from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from app.modules.customers.application.admin_customer_queries import admin_customer_queries
from app.modules.customers.models import Customer
from app.modules.orders.models import Order, OrderItem
from app.modules.tenants.models import Tenant


class AdminCustomerViewTests(TestCase):
    def test_customers_list_view_renders_design_system_template(self):
        response = self.client.get(reverse("customers:admin-customers-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_customers_list_page.html")
        self.assertContains(response, "Clientes")
        self.assertContains(response, "Ana Souza")

    def test_customers_list_view_applies_search_filter(self):
        response = self.client.get(reverse("customers:admin-customers-list"), {"q": "Bruno"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bruno Lima")
        self.assertNotContains(response, "Ana Souza")

    def test_customers_list_view_surfaces_active_quick_filter_clarity(self):
        response = self.client.get(reverse("customers:admin-customers-list"), {"quick_filter": "high_priority"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Visualizando clientes com filtro rápido ativo: Alta prioridade.")
        self.assertContains(
            response,
            "Filtro ativo: Alta prioridade",
        )
        self.assertContains(
            response,
            "Resultados filtrados por alta prioridade e ordenados por prioridade operacional.",
        )

    def test_customers_list_view_without_quick_filter_keeps_default_clarity(self):
        response = self.client.get(reverse("customers:admin-customers-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Acompanhe clientes, status da conta e atividade recente.")
        self.assertContains(response, "Lista ordenada por prioridade operacional e pronta para filtros rápidos de clientes.")
        self.assertNotContains(response, "Filtro ativo:")

    def test_customers_list_view_surfaces_quick_actions(self):
        response = self.client.get(reverse("customers:admin-customers-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Marcar follow-up")
        self.assertContains(response, "Marcar reengajamento")
        self.assertContains(response, "Marcar prioridade")
        self.assertNotContains(response, "item(ns) selecionado(s)")

    def test_customers_list_view_surfaces_bulk_actions_for_segmented_view(self):
        response = self.client.get(reverse("customers:admin-customers-list"), {"q": "Ana"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "item(ns) selecionado(s)")
        self.assertContains(response, "Marcar follow-up na visão")
        self.assertContains(response, "Remover follow-up na visão")
        self.assertContains(response, "Marcar reengajamento na visão")
        self.assertContains(response, "Remover reengajamento na visão")
        self.assertContains(response, "Marcar prioridade na visão")
        self.assertContains(response, "Remover prioridade na visão")

    def test_customers_list_view_shows_segment_empty_state_for_active_filter(self):
        response = self.client.get(
            reverse("customers:admin-customers-list"),
            {"quick_filter": "followup", "q": "nao-existe"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["empty_title"], "Nenhum follow-up pendente agora")
        self.assertIn("Busca atual: “nao-existe”.", response.context["empty_description"])
        self.assertContains(response, "Filtro ativo: Com follow-up · 0 cliente(s) nesta visão.")

    def test_customer_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-souza"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_customer_detail_page.html")
        self.assertContains(response, "Ana Souza")
        self.assertContains(response, "#8821")

    def test_admin_customer_query_service_returns_expected_contract(self):
        customer = admin_customer_queries.get_customer("ana-souza")

        self.assertEqual(customer["slug"], "ana-souza")
        self.assertEqual(customer["customer_status_label"], "Ativo")
        self.assertEqual(customer["email"], "ana@hubx.market")

    def test_admin_customer_query_service_reports_persisted_source_readiness(self):
        self.assertFalse(admin_customer_queries.using_persisted_source())


class AdminCustomerPersistedReadTests(TestCase):
    fixtures = ["customers_minimal_seed.json"]

    def test_admin_customer_query_service_scopes_records_by_tenant_when_requested(self):
        primary_customer = Customer.objects.get(pk=1)
        secondary_tenant = Tenant.objects.create(
            name="Hubx Customer Secondary Tenant",
            slug="hubx-customer-secondary-tenant",
            subdomain="hubx-customer-secondary-tenant",
        )
        secondary_customer = Customer.objects.create(
            tenant=secondary_tenant,
            slug="ana-persistida",
            reference="#9902",
            full_name="Ana Persistida Outra Loja",
            email="ana.outra@hubx.market",
            phone="(21) 90000-0000",
            status="inactive",
            account_type="Storefront",
        )

        scoped_customer = admin_customer_queries.get_customer("ana-persistida", tenant_id=primary_customer.tenant_id)
        secondary_scoped_customer = admin_customer_queries.get_customer("ana-persistida", tenant_id=secondary_tenant.id)
        scoped_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers(tenant_id=primary_customer.tenant_id)]
        secondary_scoped_slugs = [
            customer["slug"] for customer in admin_customer_queries.list_customers(tenant_id=secondary_tenant.id)
        ]

        self.assertEqual(scoped_customer["customer_reference"], "#9901")
        self.assertEqual(secondary_scoped_customer["customer_reference"], "#9902")
        self.assertEqual(scoped_slugs, ["ana-persistida"])
        self.assertEqual(secondary_scoped_slugs, ["ana-persistida"])

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_customer_views_do_not_fallback_to_fixture_data_when_tenant_is_resolved(self):
        empty_tenant = Tenant.objects.create(
            name="Hubx Empty Admin Customer Tenant",
            slug="hubx-empty-admin-customer-tenant",
            subdomain="hubx-empty-admin-customer-tenant",
        )

        customers = admin_customer_queries.list_customers(tenant_id=empty_tenant.id)
        missing_customer = admin_customer_queries.get_customer("ana-souza", tenant_id=empty_tenant.id)

        self.assertEqual(customers, [])
        self.assertIn("não encontrado no tenant atual", missing_customer["summary_content"].lower())
        self.assertIn("tenant atual", missing_customer["contact_content"].lower())

        list_response = self.client.get(
            reverse("customers:admin-customers-list"),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )
        detail_response = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-souza"}),
            HTTP_HOST=f"{empty_tenant.subdomain}.hubx.market",
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertNotContains(list_response, "Ana Souza")
        self.assertEqual(list_response.context["empty_title"], "Nenhum cliente persistido nesta loja")
        self.assertEqual(detail_response.status_code, 200)
        self.assertContains(detail_response, "Cliente não encontrado no tenant atual")
        self.assertNotContains(detail_response, "fallback seguro de apresentação")

    def test_admin_customer_query_service_uses_persisted_records_when_available(self):
        customer = Customer.objects.get(pk=1)
        latest_paid_order = Order.objects.create(
            tenant_id=customer.tenant_id,
            customer=customer,
            number="7001",
            status="paid",
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            shipping_address_summary="Rua Persistida, 400 · São Paulo/SP",
            notes_content="Cliente recorrente com entrega concluída.",
            subtotal="190.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="200.00",
            installments_summary="2x de R$ 100,00 sem juros",
        )
        OrderItem.objects.create(
            order=latest_paid_order,
            title="Produto Persistido",
            subtitle="Azul · M",
            meta="SKU PERSIST-001",
            price_snapshot="200.00",
            quantity=1,
            sort_order=1,
        )
        shipped_order = Order.objects.create(
            tenant_id=customer.tenant_id,
            customer=customer,
            number="7000",
            status="shipped",
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            shipping_address_summary="Rua Persistida, 400 · São Paulo/SP",
            notes_content="Pedido anterior entregue.",
            subtotal="140.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="150.00",
            installments_summary="",
        )
        Order.objects.filter(pk=shipped_order.pk).update(
            created_at=timezone.now() - timedelta(days=2),
            updated_at=timezone.now() - timedelta(days=2),
        )
        canceled_order = Order.objects.create(
            tenant_id=customer.tenant_id,
            customer=customer,
            number="6999",
            status="canceled",
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            payment_status="Estornado",
            shipping_status="Cancelado",
            fulfillment_status_label="Cancelado",
            fulfillment_status_variant="danger",
            shipping_address_summary="Rua Persistida, 400 · São Paulo/SP",
            notes_content="Pedido cancelado pelo cliente.",
            subtotal="50.00",
            shipping_total="0.00",
            discount_total="0.00",
            total="50.00",
            installments_summary="",
        )
        Order.objects.filter(pk=canceled_order.pk).update(
            created_at=timezone.now() - timedelta(days=3),
            updated_at=timezone.now() - timedelta(days=3),
        )

        customer = admin_customer_queries.get_customer("ana-persistida")

        self.assertTrue(admin_customer_queries.using_persisted_source())
        self.assertEqual(customer["slug"], "ana-persistida")
        self.assertEqual(customer["name"], "Ana Persistida")
        self.assertEqual(customer["customer_status_label"], "VIP")
        self.assertEqual(customer["account_type_label"], "Storefront")
        self.assertEqual(customer["customer_reference"], "#9901")
        self.assertEqual(customer["last_activity"], "15/04/2026 às 17:45")
        self.assertEqual(customer["customer_since"], "10/04/2026 às 12:30")
        self.assertEqual(customer["last_seen"], "15/04/2026 às 16:10")
        self.assertIn("3 pedido(s)", customer["summary_content"])
        self.assertIn("tier valor em desenvolvimento", customer["summary_content"].lower())
        self.assertIn("contribuição de receita: receita em desenvolvimento", customer["summary_content"].lower())
        self.assertIn("engajamento atual: recorrente ativo", customer["summary_content"].lower())
        self.assertIn("R$ 400,00", customer["summary_content"])
        self.assertIn("1 pago(s), 1 enviado(s) e 1 cancelado(s)", customer["summary_content"])
        self.assertIn("ana.persistida@hubx.market", customer["contact_content"])
        self.assertIn("telefone (11) 98888-1111", customer["profile_content"])
        self.assertIn("3 pedido(s) concluído(s)", customer["orders_summary_content"])
        self.assertIn("tier valor em desenvolvimento", customer["orders_summary_content"].lower())
        self.assertIn("receita acumulada de R$ 400,00", customer["orders_summary_content"])
        self.assertIn("ticket médio de R$ 133,33", customer["orders_summary_content"])
        self.assertIn("(Pago)", customer["orders_summary_content"])
        self.assertIn("último total de R$ 200,00", customer["orders_summary_content"])
        self.assertEqual(customer["total_orders"], 3)
        self.assertEqual(customer["total_spent"], "R$ 400,00")
        self.assertEqual(customer["average_ticket"], "R$ 133,33")
        self.assertEqual(customer["paid_orders_count"], 1)
        self.assertEqual(customer["shipped_orders_count"], 1)
        self.assertEqual(customer["canceled_orders_count"], 1)
        self.assertEqual(customer["last_order_status"], "Pago")
        self.assertEqual(customer["last_order_total"], "R$ 200,00")
        self.assertEqual(customer["recency_bucket"], "Recente")
        self.assertFalse(customer["is_at_risk"])
        self.assertTrue(customer["is_repeat_customer"])
        self.assertGreaterEqual(customer["days_since_last_order"], 0)
        self.assertEqual(customer["order_linkage_mode"], "explicit")
        self.assertEqual(customer["business_tier_label"], "Valor em desenvolvimento")
        self.assertEqual(customer["engagement_label"], "Recorrente ativo")
        self.assertEqual(customer["lifecycle_stage_label"], "Recorrente")
        self.assertEqual(customer["revenue_label"], "receita em desenvolvimento")
        self.assertEqual(customer["growth_priority_label"], "Expandir frequência de compra")
        self.assertEqual(customer["priority_label"], "Alta prioridade")
        self.assertIn("ampliar ritmo", customer["next_growth_hint"])
        self.assertIn("R$ 400,00 em receita", customer["revenue_helper"])
        self.assertIn("alta prioridade", customer["list_highlights"])
        self.assertIn("base ativa", customer["list_highlights"])
        self.assertIn("recorrente", customer["list_highlights"])
        self.assertIn("expandir frequência de compra", customer["list_highlights"])
        self.assertIn("acompanhar próxima recompra", customer["list_highlights"])
        self.assertEqual(customer["next_action_label"], "Acompanhar próxima recompra")
        self.assertIn("janela de recompra", customer["next_action_helper"])
        self.assertIn("#9901", customer["account_notes_content"])
        self.assertIn("Alta prioridade", customer["account_notes_content"])
        self.assertIn("lifecycle recorrente", customer["account_notes_content"].lower())
        self.assertIn("tier valor em desenvolvimento", customer["account_notes_content"].lower())
        self.assertIn("Já gerou R$ 400,00 em receita", customer["account_notes_content"])
        self.assertIn("Direção de crescimento: expandir frequência de compra", customer["account_notes_content"])
        self.assertIn("Próxima ação sugerida: acompanhar próxima recompra", customer["account_notes_content"])
        self.assertIn("Último pedido #7001", customer["activity_items"][0]["title"])
        self.assertIn("1 pago(s), 1 enviado(s), 1 cancelado(s)", customer["activity_items"][0]["description"])
        self.assertIn("tier valor em desenvolvimento", customer["activity_items"][0]["description"].lower())
        self.assertIn("recência recente", customer["activity_items"][0]["description"].lower())

    def test_admin_customer_views_render_persisted_records_when_present(self):
        list_response = self.client.get(reverse("customers:admin-customers-list"))
        detail_response = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Ana Persistida")
        self.assertContains(list_response, "VIP")
        self.assertContains(list_response, "sem histórico")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/admin_customer_detail_page.html")
        self.assertContains(detail_response, "Ana Persistida")
        self.assertContains(detail_response, "#9901")
        self.assertContains(detail_response, "ana.persistida@hubx.market")
        self.assertContains(detail_response, "lifecycle novo")
        self.assertContains(detail_response, "Direção de crescimento: incentivar primeira recompra")
        self.assertContains(detail_response, "Próxima ação sugerida: estimular primeiro retorno")
        self.assertContains(detail_response, "sem receita realizada")
        self.assertContains(detail_response, "sem histórico")

    def test_admin_customer_mark_for_followup_updates_flag_and_feedback(self):
        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "mark_for_followup"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-followup-marked",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
            + "?result=customer-followup-marked"
        )
        self.assertContains(refreshed, "Cliente marcado para follow-up.")
        plain_detail = self.client.get(reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"}))
        self.assertContains(plain_detail, "follow-up")
        self.assertTrue(Customer.objects.get(pk=1).marked_for_followup)

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_admin_customer_mark_for_followup_scopes_command_by_request_tenant(self):
        primary_customer = Customer.objects.get(pk=1)
        secondary_tenant = Tenant.objects.create(
            name="Hubx Customer Action Secondary Tenant",
            slug="hubx-customer-action-secondary-tenant",
            subdomain="hubx-customer-action-secondary-tenant",
        )
        secondary_customer = Customer.objects.create(
            tenant=secondary_tenant,
            slug="ana-persistida",
            reference="#9910",
            full_name="Ana Persistida Ação Outra Loja",
            email="ana.acao.outra@hubx.market",
            phone="(21) 91111-0000",
            status="active",
            account_type="Storefront",
        )

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "mark_for_followup"},
            HTTP_HOST="hubx-customer-action-secondary-tenant.hubx.market",
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-followup-marked",
            fetch_redirect_response=False,
        )
        primary_customer.refresh_from_db()
        secondary_customer.refresh_from_db()
        self.assertFalse(primary_customer.marked_for_followup)
        self.assertTrue(secondary_customer.marked_for_followup)

    def test_admin_customer_mark_for_reengagement_updates_flag_and_feedback(self):
        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "mark_for_reengagement"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-reengagement-marked",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
            + "?result=customer-reengagement-marked"
        )
        self.assertContains(refreshed, "Cliente marcado para reengajamento.")
        plain_detail = self.client.get(reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"}))
        self.assertContains(plain_detail, "reengajamento")
        self.assertTrue(Customer.objects.get(pk=1).marked_for_reengagement)

    def test_admin_customer_clear_reengagement_updates_flag_and_feedback(self):
        Customer.objects.filter(pk=1).update(marked_for_reengagement=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "clear_reengagement"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-reengagement-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
            + "?result=customer-reengagement-cleared"
        )
        self.assertContains(refreshed, "Reengajamento removido do cliente.")
        self.assertFalse(Customer.objects.get(pk=1).marked_for_reengagement)

    def test_admin_customer_mark_priority_updates_flag_and_feedback(self):
        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "mark_priority"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-priority-marked",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
            + "?result=customer-priority-marked"
        )
        self.assertContains(refreshed, "Cliente marcado com prioridade manual.")
        plain_detail = self.client.get(reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"}))
        self.assertContains(plain_detail, "prioridade manual")
        self.assertTrue(Customer.objects.get(pk=1).marked_as_priority)

    def test_admin_customer_clear_followup_updates_flag_and_feedback(self):
        Customer.objects.filter(pk=1).update(marked_for_followup=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "clear_followup"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-followup-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
            + "?result=customer-followup-cleared"
        )
        self.assertContains(refreshed, "Follow-up removido do cliente.")
        self.assertFalse(Customer.objects.get(pk=1).marked_for_followup)

    def test_admin_customer_clear_priority_updates_flag_and_feedback(self):
        Customer.objects.filter(pk=1).update(marked_as_priority=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "clear_priority"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-priority-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get(
            reverse("customers:admin-customers-detail", kwargs={"customer_slug": "ana-persistida"})
            + "?result=customer-priority-cleared"
        )
        self.assertContains(refreshed, "Prioridade manual removida do cliente.")
        self.assertFalse(Customer.objects.get(pk=1).marked_as_priority)

    def test_admin_customer_list_quick_action_preserves_list_return_and_feedback(self):
        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {
                "action_type": "mark_for_followup",
                "next": "/ops/customers/?quick_filter=followup&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?quick_filter=followup&page=1&result=customer-followup-marked",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?quick_filter=followup&page=1&result=customer-followup-marked")
        self.assertContains(refreshed, "Cliente marcado para follow-up.")
        self.assertContains(refreshed, "Filtro rápido ativo: Com follow-up.")
        self.assertTrue(Customer.objects.get(pk=1).marked_for_followup)

    def test_admin_customer_list_quick_action_can_clear_priority_and_preserve_list_return(self):
        Customer.objects.filter(pk=1).update(marked_as_priority=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {
                "action_type": "clear_priority",
                "next": "/ops/customers/?page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?page=1&result=customer-priority-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?page=1&result=customer-priority-cleared")
        self.assertContains(refreshed, "Prioridade manual removida do cliente.")
        self.assertFalse(Customer.objects.get(pk=1).marked_as_priority)

    def test_admin_customer_bulk_followup_marks_segmented_view(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Bulk Followup",
            slug="hubx-customer-bulk-followup",
            subdomain="hubx-customer-bulk-followup",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="bulk-new-one",
            reference="#BF-1",
            full_name="Bulk New One",
            email="bulk.one@hubx.market",
            phone="(11) 94444-0001",
            status="active",
            account_type="Storefront",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="bulk-new-two",
            reference="#BF-2",
            full_name="Bulk New Two",
            email="bulk.two@hubx.market",
            phone="(11) 94444-0002",
            status="active",
            account_type="Storefront",
        )
        repeat_customer = Customer.objects.create(
            tenant=tenant,
            slug="bulk-repeat",
            reference="#BF-3",
            full_name="Bulk Repeat",
            email="bulk.repeat@hubx.market",
            phone="(11) 94444-0003",
            status="active",
            account_type="Storefront",
        )
        repeat_order = Order.objects.create(
            tenant=tenant,
            customer=repeat_customer,
            number="7300",
            status="paid",
            customer_name=repeat_customer.full_name,
            customer_email=repeat_customer.email,
            customer_phone=repeat_customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="120.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="130.00",
        )
        Order.objects.filter(pk=repeat_order.pk).update(
            created_at=timezone.now() - timedelta(days=2),
            updated_at=timezone.now() - timedelta(days=2),
        )

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "_bulk"}),
            {
                "action_type": "bulk_mark_for_followup",
                "next": "/ops/customers/?quick_filter=new&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?quick_filter=new&page=1&result=customer-bulk-followup-marked",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?quick_filter=new&page=1&result=customer-bulk-followup-marked")
        self.assertContains(refreshed, "Ação em lote concluída: clientes marcados para follow-up.")
        self.assertTrue(Customer.objects.get(slug="bulk-new-one").marked_for_followup)
        self.assertTrue(Customer.objects.get(slug="bulk-new-two").marked_for_followup)
        self.assertFalse(Customer.objects.get(slug="bulk-repeat").marked_for_followup)

    def test_admin_customer_bulk_clear_followup_clears_segmented_view(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Bulk Clear Followup",
            slug="hubx-customer-bulk-clear-followup",
            subdomain="hubx-customer-bulk-clear-followup",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="bulk-clear-one",
            reference="#BCF-1",
            full_name="Bulk Clear One",
            email="bulk.clear.one@hubx.market",
            phone="(11) 95555-0001",
            status="active",
            account_type="Storefront",
            marked_for_followup=True,
        )
        Customer.objects.create(
            tenant=tenant,
            slug="bulk-clear-two",
            reference="#BCF-2",
            full_name="Bulk Clear Two",
            email="bulk.clear.two@hubx.market",
            phone="(11) 95555-0002",
            status="active",
            account_type="Storefront",
            marked_for_followup=True,
        )

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "_bulk"}),
            {
                "action_type": "bulk_clear_followup",
                "next": "/ops/customers/?quick_filter=followup&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?quick_filter=followup&page=1&result=customer-bulk-followup-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?quick_filter=followup&page=1&result=customer-bulk-followup-cleared")
        self.assertContains(refreshed, "Ação em lote concluída: follow-up removido dos clientes desta visão.")
        self.assertFalse(Customer.objects.get(slug="bulk-clear-one").marked_for_followup)
        self.assertFalse(Customer.objects.get(slug="bulk-clear-two").marked_for_followup)

    def test_admin_customer_bulk_clear_priority_clears_segmented_view(self):
        Customer.objects.filter(pk=1).update(marked_as_priority=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "_bulk"}),
            {
                "action_type": "bulk_clear_priority",
                "next": "/ops/customers/?q=Ana&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?q=Ana&page=1&result=customer-bulk-priority-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?q=Ana&page=1&result=customer-bulk-priority-cleared")
        self.assertContains(refreshed, "Ação em lote concluída: prioridade manual removida dos clientes desta visão.")
        self.assertFalse(Customer.objects.get(pk=1).marked_as_priority)

    def test_admin_customer_bulk_reengagement_marks_segmented_view(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Bulk Reengagement",
            slug="hubx-customer-bulk-reengagement",
            subdomain="hubx-customer-bulk-reengagement",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="bulk-reengage-one",
            reference="#BR-1",
            full_name="Bulk Reengage One",
            email="bulk.reengage.one@hubx.market",
            phone="(11) 96666-0001",
            status="active",
            account_type="Storefront",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="bulk-reengage-two",
            reference="#BR-2",
            full_name="Bulk Reengage Two",
            email="bulk.reengage.two@hubx.market",
            phone="(11) 96666-0002",
            status="active",
            account_type="Storefront",
        )

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "_bulk"}),
            {
                "action_type": "bulk_mark_reengagement",
                "next": "/ops/customers/?q=Bulk Reengage&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?q=Bulk+Reengage&page=1&result=customer-bulk-reengagement-marked",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?q=Bulk+Reengage&page=1&result=customer-bulk-reengagement-marked")
        self.assertContains(refreshed, "Ação em lote concluída: clientes marcados para reengajamento.")
        self.assertTrue(Customer.objects.get(slug="bulk-reengage-one").marked_for_reengagement)
        self.assertTrue(Customer.objects.get(slug="bulk-reengage-two").marked_for_reengagement)

    def test_admin_customer_bulk_clear_reengagement_clears_segmented_view(self):
        Customer.objects.filter(pk=1).update(marked_for_reengagement=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "_bulk"}),
            {
                "action_type": "bulk_clear_reengagement",
                "next": "/ops/customers/?q=Ana&page=1",
            },
        )

        self.assertRedirects(
            response,
            "/ops/customers/?q=Ana&page=1&result=customer-bulk-reengagement-cleared",
            fetch_redirect_response=False,
        )

        refreshed = self.client.get("/ops/customers/?q=Ana&page=1&result=customer-bulk-reengagement-cleared")
        self.assertContains(refreshed, "Ação em lote concluída: reengajamento removido dos clientes desta visão.")
        self.assertFalse(Customer.objects.get(pk=1).marked_for_reengagement)

    def test_admin_customer_repeated_action_is_safe(self):
        Customer.objects.filter(pk=1).update(marked_for_followup=True)

        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "mark_for_followup"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-followup-already-marked",
            fetch_redirect_response=False,
        )

    def test_admin_customer_repeated_clear_action_is_safe(self):
        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "clear_priority"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-priority-already-clear",
            fetch_redirect_response=False,
        )

    def test_admin_customer_repeated_reengagement_clear_is_safe(self):
        response = self.client.post(
            reverse("customers:admin-customer-update", kwargs={"customer_slug": "ana-persistida"}),
            {"action_type": "clear_reengagement"},
        )

        self.assertRedirects(
            response,
            "/ops/customers/ana-persistida/?result=customer-reengagement-already-clear",
            fetch_redirect_response=False,
        )

    def test_admin_customer_list_highlights_surface_execution_flags_compactly(self):
        Customer.objects.filter(pk=1).update(
            marked_for_followup=True,
            marked_for_reengagement=True,
            marked_as_priority=True,
        )

        customer = admin_customer_queries.get_customer("ana-persistida")

        self.assertIn("baixa prioridade", customer["list_highlights"])
        self.assertIn("novo", customer["list_highlights"])
        self.assertIn("prioridade manual", customer["list_highlights"])
        self.assertIn("follow-up", customer["list_highlights"])
        self.assertIn("reengajamento", customer["list_highlights"])

    def test_admin_customer_query_service_preserves_safe_fallback_when_customer_has_no_orders(self):
        customer = admin_customer_queries.get_customer("ana-persistida")

        self.assertEqual(customer["total_orders"], 0)
        self.assertEqual(customer["total_spent"], "R$ 0,00")
        self.assertEqual(customer["average_ticket"], "R$ 0,00")
        self.assertEqual(customer["last_order_date"], "indisponível")
        self.assertEqual(customer["paid_orders_count"], 0)
        self.assertEqual(customer["shipped_orders_count"], 0)
        self.assertEqual(customer["canceled_orders_count"], 0)
        self.assertEqual(customer["last_order_status"], "indisponível")
        self.assertEqual(customer["days_since_last_order"], -1)
        self.assertEqual(customer["recency_bucket"], "Sem pedidos")
        self.assertFalse(customer["is_repeat_customer"])
        self.assertFalse(customer["is_at_risk"])
        self.assertEqual(customer["business_tier_label"], "Sem histórico")
        self.assertEqual(customer["engagement_label"], "Sem histórico")
        self.assertEqual(customer["lifecycle_stage_label"], "Novo")
        self.assertEqual(customer["revenue_label"], "sem receita realizada")
        self.assertEqual(customer["growth_priority_label"], "Incentivar primeira recompra")
        self.assertEqual(customer["priority_label"], "Baixa prioridade")
        self.assertIn("primeiro retorno", customer["next_growth_hint"])
        self.assertIn("Sem receita realizada", customer["revenue_helper"])
        self.assertEqual(
            customer["list_highlights"],
            "baixa prioridade · novo · incentivar primeira recompra · estimular primeiro retorno",
        )
        self.assertEqual(customer["next_action_label"], "Estimular primeiro retorno")
        self.assertIn("incentivar uma nova visita", customer["next_action_helper"])
        self.assertIn("sincronizada em", customer["summary_content"])
        self.assertIn("modo seguro de fallback", customer["orders_summary_content"])

    def test_admin_customer_query_service_falls_back_to_tenant_and_email_for_order_aggregates(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Aggregate Fallback",
            slug="hubx-customer-aggregate-fallback",
            subdomain="hubx-customer-aggregate-fallback",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="fallback-customer",
            reference="#CF-1",
            full_name="Fallback Customer",
            email="fallback.customer@hubx.market",
            phone="(11) 90000-0000",
            status="active",
            account_type="Storefront",
        )
        order = Order.objects.create(
            tenant=tenant,
            number="7002",
            status="paid",
            customer=None,
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            payment_status="Confirmado",
            shipping_status="Separando envio",
            fulfillment_status_label="Separando itens",
            fulfillment_status_variant="info",
            subtotal="150.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="160.00",
        )
        Order.objects.filter(pk=order.pk).update(customer=None)

        payload = admin_customer_queries.get_customer("fallback-customer")

        self.assertEqual(payload["total_orders"], 1)
        self.assertEqual(payload["total_spent"], "R$ 160,00")
        self.assertEqual(payload["average_ticket"], "R$ 160,00")
        self.assertEqual(payload["paid_orders_count"], 1)
        self.assertEqual(payload["shipped_orders_count"], 0)
        self.assertEqual(payload["canceled_orders_count"], 0)
        self.assertEqual(payload["last_order_status"], "Pago")
        self.assertEqual(payload["recency_bucket"], "Recente")
        self.assertFalse(payload["is_at_risk"])
        self.assertFalse(payload["is_repeat_customer"])
        self.assertEqual(payload["order_linkage_mode"], "fallback")
        self.assertEqual(payload["business_tier_label"], "Valor em desenvolvimento")
        self.assertEqual(payload["engagement_label"], "Recente")
        self.assertEqual(payload["lifecycle_stage_label"], "Ativo")
        self.assertEqual(payload["revenue_label"], "receita em desenvolvimento")
        self.assertEqual(payload["growth_priority_label"], "Manter engajamento")
        self.assertEqual(payload["priority_label"], "Média prioridade")
        self.assertEqual(payload["next_action_label"], "Observar próxima interação")
        self.assertIn("1 pedido(s) concluído(s)", payload["orders_summary_content"])

    def test_admin_customer_query_service_marks_customer_as_at_risk_when_last_order_is_stale(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Recency Risk",
            slug="hubx-customer-recency-risk",
            subdomain="hubx-customer-recency-risk",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="stale-customer",
            reference="#RC-1",
            full_name="Stale Customer",
            email="stale.customer@hubx.market",
            phone="(11) 91111-1111",
            status="active",
            account_type="Storefront",
        )
        stale_order = Order.objects.create(
            tenant=tenant,
            customer=customer,
            number="7010",
            status="paid",
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="90.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="100.00",
        )
        Order.objects.filter(pk=stale_order.pk).update(
            created_at=timezone.now() - timedelta(days=45),
            updated_at=timezone.now() - timedelta(days=45),
        )

        payload = admin_customer_queries.get_customer("stale-customer")

        self.assertEqual(payload["days_since_last_order"], 45)
        self.assertEqual(payload["recency_bucket"], "Em risco")
        self.assertTrue(payload["is_at_risk"])
        self.assertFalse(payload["is_repeat_customer"])
        self.assertEqual(payload["business_tier_label"], "Valor inicial")
        self.assertEqual(payload["engagement_label"], "Em risco")
        self.assertEqual(payload["lifecycle_stage_label"], "Em risco")
        self.assertEqual(payload["revenue_label"], "receita inicial")
        self.assertEqual(payload["growth_priority_label"], "Recuperar cliente")
        self.assertEqual(payload["priority_label"], "Alta prioridade")
        self.assertIn("em risco", payload["list_highlights"])
        self.assertIn("recuperar cliente", payload["list_highlights"])
        self.assertIn("revisar e reengajar", payload["list_highlights"])
        self.assertEqual(payload["next_action_label"], "Revisar e reengajar")
        self.assertIn("abordagem de retorno", payload["next_action_helper"])
        self.assertIn("atenção de retenção", payload["orders_summary_content"])

    def test_admin_customer_query_service_marks_customer_as_lost_after_long_inactivity(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Lost Lifecycle",
            slug="hubx-customer-lost-lifecycle",
            subdomain="hubx-customer-lost-lifecycle",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="lost-customer",
            reference="#LC-1",
            full_name="Lost Customer",
            email="lost.customer@hubx.market",
            phone="(11) 92222-2222",
            status="inactive",
            account_type="Storefront",
        )
        lost_order = Order.objects.create(
            tenant=tenant,
            customer=customer,
            number="7020",
            status="paid",
            customer_name=customer.full_name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="90.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="100.00",
        )
        Order.objects.filter(pk=lost_order.pk).update(
            created_at=timezone.now() - timedelta(days=75),
            updated_at=timezone.now() - timedelta(days=75),
        )

        payload = admin_customer_queries.get_customer("lost-customer")

        self.assertEqual(payload["days_since_last_order"], 75)
        self.assertEqual(payload["lifecycle_stage_label"], "Perdido")
        self.assertEqual(payload["growth_priority_label"], "Recuperação seletiva")
        self.assertEqual(payload["priority_label"], "Alta prioridade")
        self.assertIn("perdido", payload["list_highlights"])

    def test_admin_customer_query_service_orders_customers_by_priority_risk_and_execution_flags(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Ordering",
            slug="hubx-customer-ordering",
            subdomain="hubx-customer-ordering",
        )
        risk_customer = Customer.objects.create(
            tenant=tenant,
            slug="risk-customer",
            reference="#ORD-1",
            full_name="Risk Customer",
            email="risk.customer@hubx.market",
            phone="(11) 91111-0001",
            status="active",
            account_type="Storefront",
        )
        flagged_customer = Customer.objects.create(
            tenant=tenant,
            slug="flagged-customer",
            reference="#ORD-2",
            full_name="Flagged Customer",
            email="flagged.customer@hubx.market",
            phone="(11) 91111-0002",
            status="active",
            account_type="Storefront",
            marked_as_priority=True,
            marked_for_followup=True,
        )
        medium_customer = Customer.objects.create(
            tenant=tenant,
            slug="medium-customer",
            reference="#ORD-3",
            full_name="Medium Customer",
            email="medium.customer@hubx.market",
            phone="(11) 91111-0003",
            status="active",
            account_type="Storefront",
        )
        low_customer = Customer.objects.create(
            tenant=tenant,
            slug="low-customer",
            reference="#ORD-4",
            full_name="Low Customer",
            email="low.customer@hubx.market",
            phone="(11) 91111-0004",
            status="inactive",
            account_type="Storefront",
        )

        risk_order = Order.objects.create(
            tenant=tenant,
            customer=risk_customer,
            number="7100",
            status="paid",
            customer_name=risk_customer.full_name,
            customer_email=risk_customer.email,
            customer_phone=risk_customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="90.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="100.00",
        )
        flagged_order = Order.objects.create(
            tenant=tenant,
            customer=flagged_customer,
            number="7101",
            status="paid",
            customer_name=flagged_customer.full_name,
            customer_email=flagged_customer.email,
            customer_phone=flagged_customer.phone,
            payment_status="Confirmado",
            shipping_status="Separando envio",
            fulfillment_status_label="Separando itens",
            fulfillment_status_variant="info",
            subtotal="150.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="160.00",
        )
        medium_order = Order.objects.create(
            tenant=tenant,
            customer=medium_customer,
            number="7102",
            status="paid",
            customer_name=medium_customer.full_name,
            customer_email=medium_customer.email,
            customer_phone=medium_customer.phone,
            payment_status="Confirmado",
            shipping_status="Separando envio",
            fulfillment_status_label="Separando itens",
            fulfillment_status_variant="info",
            subtotal="210.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="220.00",
        )
        Order.objects.filter(pk=risk_order.pk).update(
            created_at=timezone.now() - timedelta(days=50),
            updated_at=timezone.now() - timedelta(days=50),
        )
        Order.objects.filter(pk=flagged_order.pk).update(
            created_at=timezone.now() - timedelta(days=5),
            updated_at=timezone.now() - timedelta(days=5),
        )
        Order.objects.filter(pk=medium_order.pk).update(
            created_at=timezone.now() - timedelta(days=3),
            updated_at=timezone.now() - timedelta(days=3),
        )

        ordered_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers()]

        self.assertLess(ordered_slugs.index("risk-customer"), ordered_slugs.index("flagged-customer"))
        self.assertLess(ordered_slugs.index("flagged-customer"), ordered_slugs.index("medium-customer"))
        self.assertLess(ordered_slugs.index("medium-customer"), ordered_slugs.index("low-customer"))

    def test_admin_customer_query_service_supports_quick_filters(self):
        tenant = Tenant.objects.create(
            name="Hubx Customer Quick Filters",
            slug="hubx-customer-quick-filters",
            subdomain="hubx-customer-quick-filters",
        )
        high_priority_customer = Customer.objects.create(
            tenant=tenant,
            slug="high-priority-customer",
            reference="#QF-1",
            full_name="High Priority Customer",
            email="high.priority@hubx.market",
            phone="(11) 93333-0001",
            status="active",
            account_type="Storefront",
        )
        repeat_customer = Customer.objects.create(
            tenant=tenant,
            slug="repeat-customer",
            reference="#QF-2",
            full_name="Repeat Customer",
            email="repeat.customer@hubx.market",
            phone="(11) 93333-0002",
            status="active",
            account_type="Storefront",
        )
        followup_customer = Customer.objects.create(
            tenant=tenant,
            slug="followup-customer",
            reference="#QF-3",
            full_name="Followup Customer",
            email="followup.customer@hubx.market",
            phone="(11) 93333-0003",
            status="active",
            account_type="Storefront",
            marked_for_followup=True,
        )
        new_customer = Customer.objects.create(
            tenant=tenant,
            slug="new-customer",
            reference="#QF-4",
            full_name="New Customer",
            email="new.customer@hubx.market",
            phone="(11) 93333-0004",
            status="inactive",
            account_type="Storefront",
        )

        at_risk_order = Order.objects.create(
            tenant=tenant,
            customer=high_priority_customer,
            number="7200",
            status="paid",
            customer_name=high_priority_customer.full_name,
            customer_email=high_priority_customer.email,
            customer_phone=high_priority_customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="90.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="100.00",
        )
        first_repeat_order = Order.objects.create(
            tenant=tenant,
            customer=repeat_customer,
            number="7201",
            status="paid",
            customer_name=repeat_customer.full_name,
            customer_email=repeat_customer.email,
            customer_phone=repeat_customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="110.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="120.00",
        )
        second_repeat_order = Order.objects.create(
            tenant=tenant,
            customer=repeat_customer,
            number="7202",
            status="paid",
            customer_name=repeat_customer.full_name,
            customer_email=repeat_customer.email,
            customer_phone=repeat_customer.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="130.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="140.00",
        )
        Order.objects.filter(pk=at_risk_order.pk).update(
            created_at=timezone.now() - timedelta(days=50),
            updated_at=timezone.now() - timedelta(days=50),
        )
        Order.objects.filter(pk=first_repeat_order.pk).update(
            created_at=timezone.now() - timedelta(days=10),
            updated_at=timezone.now() - timedelta(days=10),
        )
        Order.objects.filter(pk=second_repeat_order.pk).update(
            created_at=timezone.now() - timedelta(days=3),
            updated_at=timezone.now() - timedelta(days=3),
        )

        high_priority_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers(quick_filter="high_priority")]
        at_risk_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers(quick_filter="at_risk")]
        followup_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers(quick_filter="followup")]
        repeat_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers(quick_filter="repeat")]
        new_slugs = [customer["slug"] for customer in admin_customer_queries.list_customers(quick_filter="new")]

        self.assertIn("high-priority-customer", high_priority_slugs)
        self.assertIn("repeat-customer", high_priority_slugs)
        self.assertIn("high-priority-customer", at_risk_slugs)
        self.assertIn("followup-customer", followup_slugs)
        self.assertIn("repeat-customer", repeat_slugs)
        self.assertIn("new-customer", new_slugs)

        self.assertNotIn("followup-customer", at_risk_slugs)
        self.assertNotIn("high-priority-customer", followup_slugs)
        self.assertNotIn("new-customer", repeat_slugs)

    def test_admin_customer_query_service_ignores_unknown_quick_filter(self):
        baseline = [customer["slug"] for customer in admin_customer_queries.list_customers()]
        unknown = [customer["slug"] for customer in admin_customer_queries.list_customers(quick_filter="unknown-filter")]

        self.assertEqual(unknown, baseline)

    def test_admin_customer_list_view_applies_quick_filter_from_querystring(self):
        Customer.objects.filter(pk=1).update(marked_for_followup=True)

        response = self.client.get(reverse("customers:admin-customers-list"), {"quick_filter": "followup"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ana Persistida")
        self.assertContains(response, "follow-up")
