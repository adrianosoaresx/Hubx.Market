from django.test import TestCase
from django.urls import reverse

from app.modules.orders.application.admin_order_queries import admin_order_queries
from app.modules.orders.models import Order, OrderStatusHistory


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

    def test_admin_order_query_service_uses_persisted_records_when_available(self):
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

    def test_admin_order_views_render_persisted_records_when_present(self):
        list_response = self.client.get(reverse("orders:admin-orders-list"))
        detail_response = self.client.get(reverse("orders:admin-orders-detail", kwargs={"order_number": "2048"}))

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "#2048")
        self.assertContains(list_response, "Ana Persistida")
        self.assertContains(list_response, "vínculo explícito")

        self.assertEqual(detail_response.status_code, 200)
        self.assertTemplateUsed(detail_response, "pages/templates/admin_order_detail_page.html")
        self.assertContains(detail_response, "Pedido #2048")
        self.assertContains(detail_response, "Ana Persistida")
        self.assertContains(detail_response, "Rua Persistida, 200")
        self.assertContains(detail_response, "Order.customer")

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
