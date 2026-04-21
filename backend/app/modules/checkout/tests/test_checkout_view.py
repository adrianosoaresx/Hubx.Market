from django.test import TestCase
from django.urls import reverse

from app.modules.catalog.models import Product, ProductVariant
from app.modules.checkout.application.checkout_page_queries import checkout_page_queries
from app.modules.checkout.models import CheckoutSession, CheckoutSessionItem
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class CheckoutViewTests(TestCase):
    def test_checkout_view_renders_design_system_template(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/checkout_page.html")
        self.assertContains(response, "Finalizar compra")
        self.assertContains(response, "Tênis Hubx Runner")

    def test_checkout_view_contains_payment_and_shipping_options(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Entrega padrão")
        self.assertContains(response, "Cartão de crédito")

    def test_checkout_view_respects_back_url_when_provided(self):
        back_url = reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"})
        response = self.client.get(reverse("checkout:checkout-page"), {"back_url": back_url})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["back_url"], back_url)

    def test_checkout_query_service_returns_expected_contract(self):
        payload = checkout_page_queries.get_checkout_page_data()

        self.assertEqual(payload["page_title"], "Finalizar compra")
        self.assertEqual(payload["shipping_method_selected"], "standard")
        self.assertEqual(payload["payment_method_selected"], "credit_card")
        self.assertEqual(payload["order_items"][0]["title"], "Tênis Hubx Runner")


class CheckoutPersistedReadTests(TestCase):
    fixtures = ["checkout_minimal_seed.json"]

    def _create_checkout_variants(self, *, stock_runner: int = 6, reserved_runner: int = 1, stock_sock: int = 12, reserved_sock: int = 0) -> None:
        tenant = Tenant.objects.get(pk=2)
        runner = Product.objects.create(
            tenant=tenant,
            name="Tênis Hubx Runner Persistido",
            slug="tenis-hubx-runner-persistido-checkout",
            brand_name="Hubx Persisted",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=runner,
            sku="RUNNER-PERSIST-001",
            price="399.90",
            compare_price="449.90",
            stock=stock_runner,
            reserved_stock=reserved_runner,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        socks = Product.objects.create(
            tenant=tenant,
            name="Meia Performance Persistida",
            slug="meia-performance-persistida-checkout",
            brand_name="Hubx Persisted",
            category_label="Acessórios",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=socks,
            sku="MP-PERSIST-030",
            price="59.90",
            stock=stock_sock,
            reserved_stock=reserved_sock,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

    def test_checkout_query_service_uses_persisted_session_when_available(self):
        payload = checkout_page_queries.get_checkout_page_data()

        self.assertTrue(checkout_page_queries.using_persisted_source())
        self.assertEqual(payload["first_name"], "Ana")
        self.assertEqual(payload["email"], "ana.persisted@hubx.market")
        self.assertEqual(payload["shipping_method_selected"], "express")
        self.assertEqual(payload["payment_method_selected"], "pix")
        self.assertEqual(payload["subtotal"], "R$ 459,80")
        self.assertEqual(payload["discount_total"], "-R$ 15,00")
        self.assertEqual(payload["order_items"][0]["title"], "Tênis Hubx Runner Persistido")
        self.assertEqual(payload["order_items"][0]["price"], "R$ 399,90")
        self.assertEqual(payload["checkout_steps"][0]["state"], "complete")
        self.assertEqual(payload["checkout_steps"][1]["state"], "complete")
        self.assertEqual(payload["checkout_steps"][2]["state"], "complete")
        self.assertEqual(payload["checkout_steps"][3]["state"], "upcoming")
        self.assertIn("2 item(ns)", payload["page_description"])
        self.assertIn("Entrega expressa", payload["page_description"])
        self.assertIn("PIX", payload["page_description"])
        self.assertEqual(payload["delivery_completion_hint"]["title"], "Entrega salva")
        self.assertEqual(payload["payment_completion_hint"]["title"], "Pagamento pronto para revisão")
        self.assertEqual(payload["review_completion_hint"]["title"], "Revisão pronta")

    def test_checkout_view_renders_persisted_session_when_present(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/checkout_page.html")
        self.assertContains(response, "ana.persisted@hubx.market")
        self.assertContains(response, "Entrega expressa")
        self.assertContains(response, "PIX")
        self.assertContains(response, "Tênis Hubx Runner Persistido")
        self.assertContains(response, "Revise 2 item(ns) antes de concluir o pedido.")
        self.assertContains(response, "Contato, endereço e frete já estão salvos nesta sessão.")
        self.assertContains(response, "Forma de pagamento, parcelamento e termos já ficaram consistentes para revisão.")

    def test_checkout_view_uses_requested_session_key_when_provided(self):
        tenant = Tenant.objects.get(pk=2)
        session = CheckoutSession.objects.create(
            tenant=tenant,
            status=CheckoutSession.Status.OPEN,
            shipping_methods=[{"value": "standard", "label": "Entrega padrão"}],
            shipping_method_selected="standard",
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            payment_method_selected="credit_card",
            subtotal="199.90",
            shipping_total="24.90",
            discount_total="0.00",
            grand_total="224.80",
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto Ativado no PDP",
            subtitle="Preto · 42",
            meta="SKU PDP-001",
            price="199.90",
            quantity=1,
            sort_order=1,
        )

        response = self.client.get(reverse("checkout:checkout-page"), {"session_key": str(session.session_key)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Produto Ativado no PDP")
        self.assertNotContains(response, "Tênis Hubx Runner Persistido")

    def test_checkout_query_service_forces_delivery_stage_when_payment_requested_too_early(self):
        tenant = Tenant.objects.get(pk=2)
        session = CheckoutSession.objects.create(
            tenant=tenant,
            status=CheckoutSession.Status.OPEN,
            first_name="Clara",
            shipping_methods=[{"value": "standard", "label": "Entrega padrão", "price": "R$ 24,90"}],
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            subtotal="199.90",
            shipping_total="0.00",
            discount_total="0.00",
            grand_total="199.90",
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto em progresso",
            subtitle="Cinza · 40",
            meta="SKU PROG-001",
            price="199.90",
            quantity=1,
            sort_order=1,
        )

        payload = checkout_page_queries.get_checkout_page_data(
            session_key=str(session.session_key),
            requested_stage="payment",
        )

        self.assertEqual(payload["current_stage"], "delivery")
        self.assertEqual(payload["submit_label"], "Salvar entrega e continuar")
        self.assertIsNotNone(payload["stage_feedback"])
        self.assertIn("liberar a próxima etapa", payload["shipping_section_description"])
        self.assertIn("fica mais útil depois", payload["payment_section_description"])
        self.assertEqual(payload["delivery_completion_hint"]["title"], "Entrega ainda incompleta")
        self.assertEqual(payload["payment_completion_hint"]["title"], "Pagamento aguardando entrega")
        self.assertEqual(payload["current_stage_completion_hint"]["title"], "Entrega ainda incompleta")

    def test_checkout_post_updates_requested_session_and_recalculates_totals(self):
        session = CheckoutSession.objects.get(pk=1)
        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "back_url": reverse("storefront:product-detail", kwargs={"product_slug": "tenis-hubx-runner"}),
                "first_name": "Marina",
                "last_name": "Costa",
                "email": "marina@hubx.market",
                "phone": "(11) 96666-0000",
                "address_line_1": "Rua Nova, 300",
                "address_line_2": "Casa 2",
                "city": "Campinas",
                "state": "SP",
                "zip_code": "13010-000",
                "shipping_method": "standard",
                "payment_method": "credit_card",
                "installments": "2x",
                "accept_terms": "on",
                "current_stage": "payment",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-saved", response["Location"])
        self.assertIn(f"session_key={session.session_key}", response["Location"])
        self.assertIn("stage=review", response["Location"])

        session.refresh_from_db()
        self.assertEqual(session.first_name, "Marina")
        self.assertEqual(session.last_name, "Costa")
        self.assertEqual(session.email, "marina@hubx.market")
        self.assertEqual(session.phone, "(11) 96666-0000")
        self.assertEqual(session.address_line_1, "Rua Nova, 300")
        self.assertEqual(session.address_line_2, "Casa 2")
        self.assertEqual(session.city, "Campinas")
        self.assertEqual(session.state, "SP")
        self.assertEqual(session.zip_code, "13010-000")
        self.assertEqual(session.shipping_method_selected, "standard")
        self.assertEqual(session.payment_method_selected, "credit_card")
        self.assertEqual(str(session.shipping_total), "24.90")
        self.assertEqual(str(session.grand_total), "469.70")
        self.assertEqual(session.installments_selected, "2x")
        self.assertTrue(session.accept_terms)

    def test_checkout_post_advances_from_delivery_to_payment_when_delivery_is_saved(self):
        tenant = Tenant.objects.get(pk=2)
        session = CheckoutSession.objects.create(
            tenant=tenant,
            status=CheckoutSession.Status.OPEN,
            shipping_methods=[
                {"value": "standard", "label": "Entrega padrão", "price": "R$ 24,90"},
                {"value": "express", "label": "Entrega expressa", "price": "R$ 39,90"},
            ],
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            subtotal="199.90",
            shipping_total="0.00",
            discount_total="0.00",
            grand_total="199.90",
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto em progresso",
            subtitle="Preto · 42",
            meta="SKU PROG-002",
            price="199.90",
            quantity=1,
            sort_order=1,
        )

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "delivery",
                "first_name": "João",
                "last_name": "Progressivo",
                "email": "joao@hubx.market",
                "phone": "(11) 95555-0000",
                "address_line_1": "Rua Entrega, 10",
                "city": "São Paulo",
                "state": "SP",
                "zip_code": "01000-000",
                "shipping_method": "express",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-saved", response["Location"])
        self.assertIn("stage=payment", response["Location"])

        session.refresh_from_db()
        self.assertEqual(session.shipping_method_selected, "express")
        self.assertFalse(session.accept_terms)

    def test_checkout_view_shows_feedback_after_successful_save(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-saved", "stage": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Etapa salva")
        self.assertContains(response, "Os dados de revisão foram salvos na sua sessão atual.")

    def test_checkout_view_shows_progressive_context_for_requested_stage(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "stage": "payment"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Etapa atual: pagamento")
        self.assertContains(response, "Salvar pagamento e revisar")
        self.assertContains(response, "Com a entrega definida, use os itens e totais para revisar a compra enquanto escolhe o pagamento.")
        self.assertContains(response, "Pagamento pronto para revisão")
        self.assertContains(response, "Forma de pagamento, parcelamento e termos já ficaram consistentes para revisão.")

    def test_checkout_view_shows_inventory_conflict_feedback(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-stock-conflict", "stage": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estoque mudou durante o checkout")
        self.assertContains(response, "saldo livre da variante não é mais suficiente")

    def test_checkout_review_post_creates_order_and_redirects_to_customer_detail(self):
        self._create_checkout_variants()
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(response.status_code, 302)
        order = Order.objects.order_by("-id").first()
        self.assertIsNotNone(order)
        self.assertEqual(order.number, "1001")
        self.assertEqual(order.status, "pending")
        self.assertEqual(order.payment_status, "Pagamento pendente")
        self.assertEqual(order.shipping_status, "Aguardando confirmação")
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.items.first().variant_sku, "RUNNER-PERSIST-001")
        self.assertIn(reverse("accounts:account-order-detail", kwargs={"order_number": order.number}), response["Location"])
        self.assertIn("result=checkout-completed", response["Location"])

        session.refresh_from_db()
        self.assertEqual(session.status, "completed")

    def test_checkout_review_post_blocks_completion_when_variant_is_unavailable(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-completion-inventory-unavailable", response["Location"])
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_review_post_blocks_completion_when_free_stock_is_insufficient(self):
        self._create_checkout_variants(stock_runner=1, reserved_runner=1, stock_sock=12, reserved_sock=0)
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-completion-stock-conflict", response["Location"])
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_review_post_blocks_completion_when_review_is_not_ready(self):
        tenant = Tenant.objects.get(pk=2)
        session = CheckoutSession.objects.create(
            tenant=tenant,
            status=CheckoutSession.Status.OPEN,
            shipping_methods=[{"value": "standard", "label": "Entrega padrão", "price": "R$ 24,90"}],
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            subtotal="199.90",
            shipping_total="0.00",
            discount_total="0.00",
            grand_total="199.90",
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto incompleto",
            subtitle="Preto · 42",
            meta="SKU BLK-042",
            price="199.90",
            quantity=1,
            sort_order=1,
        )

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-completion-blocked", response["Location"])
        self.assertEqual(Order.objects.filter(tenant=tenant).count(), 0)

        follow_response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-blocked"},
        )
        self.assertContains(follow_response, "Revisão ainda incompleta")

    def test_checkout_post_fails_safely_when_session_is_unavailable(self):
        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": "00000000-0000-0000-0000-000000000000",
                "shipping_method": "standard",
                "payment_method": "credit_card",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-save-unavailable", response["Location"])

        follow_response = self.client.get(reverse("checkout:checkout-page"), {"result": "checkout-save-unavailable"})
        self.assertEqual(follow_response.status_code, 200)
        self.assertContains(follow_response, "Sessão indisponível")
        self.assertContains(
            follow_response,
            "Não foi possível salvar esta etapa agora. Tente iniciar o checkout novamente a partir do produto.",
        )
