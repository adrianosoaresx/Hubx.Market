from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.catalog.models import Product, ProductVariant
from app.modules.checkout.application.checkout_page_queries import checkout_page_queries
from app.modules.checkout.models import CheckoutRecoveryEvent, CheckoutSession, CheckoutSessionItem
from app.modules.accounts.models import OwnerUser
from app.modules.customers.models import Customer
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order, OrderStatusHistory
from app.modules.payments.models import PaymentAttempt
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class CheckoutViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Checkout View Demo",
            slug="hubx-checkout-view-demo",
            subdomain="hubx-checkout-view-demo",
        )
        self.checkout_host = f"{self.tenant.subdomain}.hubx.market"
        self.client.defaults["HTTP_HOST"] = self.checkout_host

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
        payload = checkout_page_queries.get_checkout_page_data(tenant_id=self.tenant.id)

        self.assertEqual(payload["page_title"], "Finalizar compra")
        self.assertEqual(payload["shipping_method_selected"], "standard")
        self.assertEqual(payload["payment_method_selected"], "credit_card")
        self.assertEqual(payload["order_items"][0]["title"], "Tênis Hubx Runner")

    def test_checkout_query_service_marks_expired_session_as_readonly(self):
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
            status=CheckoutSession.Status.EXPIRED,
            subtotal=Decimal("100.00"),
            grand_total=Decimal("100.00"),
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto expirado",
            price=Decimal("100.00"),
            quantity=1,
        )

        payload = checkout_page_queries.get_checkout_page_data(
            tenant_id=self.tenant.id,
            session_key=str(session.session_key),
        )

        self.assertEqual(payload["page_title"], "Sessão de checkout expirada")
        self.assertEqual(payload["checkout_session_state"], "expired")
        self.assertTrue(payload["checkout_session_readonly"])
        self.assertEqual(payload["order_items"][0]["title"], "Produto expirado")
        self.assertEqual(payload["order_items"][0]["mutation_actions"], [])

    def test_checkout_query_service_does_not_fallback_for_missing_session_key(self):
        payload = checkout_page_queries.get_checkout_page_data(
            tenant_id=self.tenant.id,
            session_key="00000000-0000-0000-0000-000000000000",
        )

        self.assertEqual(payload["page_title"], "Sessão de checkout indisponível")
        self.assertEqual(payload["checkout_session_state"], "missing")
        self.assertTrue(payload["checkout_session_readonly"])
        self.assertEqual(payload["order_items"], [])

    def test_checkout_view_renders_expired_session_recovery_without_submit(self):
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
            status=CheckoutSession.Status.EXPIRED,
            subtotal=Decimal("100.00"),
            grand_total=Decimal("100.00"),
        )
        CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto expirado",
            price=Decimal("100.00"),
            quantity=1,
        )

        response = self.client.get(reverse("checkout:checkout-page"), {"session_key": str(session.session_key)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sessão de checkout expirada")
        self.assertContains(response, "Produto expirado")
        self.assertContains(response, "Voltar ao produto")
        self.assertNotContains(response, "Tênis Hubx Runner")
        self.assertNotContains(response, "Confirmar pedido")

    def test_checkout_view_requires_resolved_tenant_without_session_key(self):
        self.client.defaults.pop("HTTP_HOST", None)

        response = self.client.get(reverse("checkout:checkout-page"), HTTP_HOST="localhost:8000")

        self.assertEqual(response.status_code, 404)


@override_settings(ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
class CheckoutPersistedReadTests(TestCase):
    fixtures = ["checkout_minimal_seed.json"]

    def setUp(self):
        self.tenant = Tenant.objects.get(pk=2)
        self.checkout_host = f"{self.tenant.subdomain}.hubx.market"
        self.client.defaults["HTTP_HOST"] = self.checkout_host

    def _create_mutable_session(self, *, quantity: int = 1) -> tuple[CheckoutSession, CheckoutSessionItem]:
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
            status=CheckoutSession.Status.OPEN,
            shipping_methods=[{"value": "standard", "label": "Entrega padrão", "price": "R$ 24,90"}],
            shipping_method_selected="standard",
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            payment_method_selected="credit_card",
            subtotal=Decimal("199.90") * quantity,
            shipping_total=Decimal("24.90"),
            discount_total=Decimal("0.00"),
            grand_total=(Decimal("199.90") * quantity) + Decimal("24.90"),
        )
        item = CheckoutSessionItem.objects.create(
            checkout_session=session,
            title="Produto mutável",
            subtitle="Preto · 42",
            meta="SKU MUT-001",
            variant_sku="MUT-001",
            price="199.90",
            quantity=quantity,
            sort_order=1,
        )
        return session, item

    def _create_checkout_variants(self, *, stock_runner: int = 6, reserved_runner: int = 1, stock_sock: int = 12, reserved_sock: int = 0) -> None:
        runner = Product.objects.create(
            tenant=self.tenant,
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
            tenant=self.tenant,
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
        payload = checkout_page_queries.get_checkout_page_data(tenant_id=self.tenant.id)

        self.assertTrue(checkout_page_queries.using_persisted_source(tenant_id=self.tenant.id))
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
        self.assertEqual(payload["review_completion_hint"]["title"], "Revisão pronta para gerar pedido")
        self.assertEqual(payload["review_readiness_title"], "Pronto para gerar pedido inicial")
        self.assertEqual(len(payload["review_readiness_items"]), 4)
        self.assertEqual(payload["review_readiness_items"][0]["label"], "Itens confirmados na sessão")
        self.assertTrue(payload["review_readiness_items"][0]["ready"])

    def test_checkout_view_renders_persisted_session_when_present(self):
        response = self.client.get(reverse("checkout:checkout-page"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/checkout_page.html")
        self.assertContains(response, "ana.persisted@hubx.market")
        self.assertContains(response, "Entrega expressa")
        self.assertContains(response, "PIX")
        self.assertContains(response, "Tênis Hubx Runner Persistido")
        self.assertContains(response, "Revise 2 item(ns) antes de concluir o pedido.")
        self.assertContains(response, "Contato, endereço e frete estimado já estão salvos nesta sessão.")
        self.assertContains(response, "Forma de pagamento, parcelamento e termos já ficaram consistentes para revisão.")

    def test_checkout_view_uses_requested_session_key_when_provided(self):
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
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

    def test_checkout_defaults_to_cart_stage_when_session_has_items_but_delivery_is_not_ready(self):
        session, _item = self._create_mutable_session(quantity=1)

        response = self.client.get(reverse("checkout:checkout-page"), {"session_key": str(session.session_key)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confira seu carrinho")
        self.assertContains(response, "Carrinho pronto para seguir")
        self.assertContains(response, "Conferir entrega")
        self.assertContains(response, "Carrinho leve desta sessão")
        self.assertNotContains(response, "Nome no cartao")
        self.assertNotContains(response, "Salvar entrega e seguir")

    def test_checkout_cart_stage_advances_to_delivery_without_overwriting_session(self):
        session, _item = self._create_mutable_session(quantity=1)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "cart",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("stage=delivery", response["Location"])

        session.refresh_from_db()
        self.assertEqual(session.subtotal, Decimal("199.90"))
        self.assertEqual(session.first_name, "")

    def test_checkout_post_increments_item_and_recalculates_totals(self):
        session, item = self._create_mutable_session(quantity=1)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "delivery",
                "item_action": f"increment:{item.id}",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-item-updated", response["Location"])

        item.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(item.quantity, 2)
        self.assertEqual(str(session.subtotal), "399.80")
        self.assertEqual(str(session.shipping_total), "24.90")
        self.assertEqual(str(session.grand_total), "424.70")

    def test_checkout_post_decrements_item_and_recalculates_totals(self):
        session, item = self._create_mutable_session(quantity=2)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "delivery",
                "item_action": f"decrement:{item.id}",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-item-updated", response["Location"])

        item.refresh_from_db()
        session.refresh_from_db()
        self.assertEqual(item.quantity, 1)
        self.assertEqual(str(session.subtotal), "199.90")
        self.assertEqual(str(session.shipping_total), "24.90")
        self.assertEqual(str(session.grand_total), "224.80")

    def test_checkout_post_removes_last_item_and_leaves_empty_session(self):
        session, item = self._create_mutable_session(quantity=1)

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "delivery",
                "item_action": f"remove:{item.id}",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-item-session-empty", response["Location"])

        session.refresh_from_db()
        self.assertEqual(session.items.count(), 0)
        self.assertEqual(str(session.subtotal), "0.00")
        self.assertEqual(str(session.shipping_total), "0.00")
        self.assertEqual(str(session.grand_total), "0.00")
        self.assertEqual(session.installments_summary, "")
        self.assertEqual(session.installments_selected, "")

        follow_response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-item-session-empty"},
        )
        self.assertContains(follow_response, "Sessão agora está vazia")
        self.assertContains(follow_response, "Sua sessão de checkout está vazia no momento.")
        self.assertContains(follow_response, "Seu carrinho esta vazio")

    def test_checkout_query_service_forces_delivery_stage_when_payment_requested_too_early(self):
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
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
            tenant_id=self.tenant.id,
            session_key=str(session.session_key),
            requested_stage="payment",
        )

        self.assertEqual(payload["current_stage"], "delivery")
        self.assertEqual(payload["submit_label"], "Salvar entrega e seguir")
        self.assertIsNotNone(payload["stage_feedback"])
        self.assertIn("modalidade de frete estimada", payload["shipping_section_description"])
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
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
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
        self.assertContains(response, "Escolha o pagamento")
        self.assertContains(response, "Salvar pagamento e revisar")
        self.assertContains(response, "Com a entrega definida, use os itens e totais para revisar a compra enquanto escolhe o pagamento.")
        self.assertContains(response, "Pagamento pronto para revisão")
        self.assertContains(response, "Forma de pagamento, parcelamento e termos já ficaram consistentes para revisão.")
        self.assertContains(response, "frete estimado")
        self.assertContains(response, "prazo e envio ainda dependem de pagamento confirmado")

    def test_checkout_view_polishes_review_stage_with_completion_confidence(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "stage": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ao concluir, você verá a confirmação inicial do pedido na sua conta.")
        self.assertContains(response, "Revisão pronta para gerar pedido")
        self.assertContains(response, "Criar pedido inicial")
        self.assertContains(response, "Ação final desta etapa")
        self.assertContains(response, "abriremos a confirmação inicial")
        self.assertContains(response, "pagamento real continua pendente")
        self.assertContains(response, "pedido inicial será criado na sua conta")
        self.assertContains(response, "A confirmação real de pagamento acontece depois.")
        self.assertContains(response, "Pronto para gerar pedido inicial")
        self.assertContains(response, "Itens confirmados na sessão")
        self.assertContains(response, "Entrega e frete salvos")
        self.assertContains(response, "Pagamento e termos revisados")
        self.assertContains(response, "Totais prontos para gerar o pedido")

    def test_checkout_view_shows_inventory_conflict_feedback(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-stock-conflict", "stage": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estoque mudou durante o checkout")
        self.assertContains(response, "saldo livre da variante não é mais suficiente")
        self.assertContains(response, "Como retomar com segurança")
        self.assertContains(response, "Volte ao produto para confirmar estoque atual")
        self.assertContains(response, "Voltar ao produto")
        self.assertNotContains(response, "Reabrir checkout")
        self.assertEqual(response.context["checkout_result_taxonomy"]["family"], "inventory")
        self.assertEqual(response.context["checkout_result_taxonomy"]["recovery_action"], "restart_from_product")
        event = CheckoutRecoveryEvent.objects.get()
        self.assertEqual(event.tenant, self.tenant)
        self.assertEqual(event.checkout_session, session)
        self.assertEqual(event.result_code, "checkout-completion-stock-conflict")
        self.assertEqual(event.family, "inventory")
        self.assertEqual(event.recovery_action, "restart_from_product")
        self.assertEqual(event.stage, "review")

    def test_checkout_view_shows_snapshot_conflict_feedback(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-snapshot-conflict", "stage": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sessão mudou antes da conclusão")
        self.assertContains(response, "Itens ou totais desta sessão já não estão consistentes")
        self.assertContains(response, "Como retomar com segurança")
        self.assertContains(response, "Reabra esta sessão para revisar itens e totais")
        self.assertContains(response, "Reabrir checkout")
        self.assertEqual(response.context["checkout_result_taxonomy"]["family"], "snapshot")
        self.assertEqual(response.context["checkout_result_taxonomy"]["recovery_action"], "review_current_session")

    def test_checkout_view_completion_unavailable_recovery_points_to_product(self):
        session = CheckoutSession.objects.get(pk=1)

        response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-unavailable", "stage": "review"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não foi possível gerar o pedido")
        self.assertContains(response, "Volte ao produto para iniciar uma nova sessão de checkout")
        self.assertContains(response, "Voltar ao produto")
        self.assertNotContains(response, "Tente reabrir esta sessão primeiro")
        self.assertEqual(response.context["checkout_result_taxonomy"]["family"], "session")
        self.assertEqual(response.context["checkout_result_taxonomy"]["recovery_action"], "restart_from_product")

    def test_checkout_review_post_creates_order_and_redirects_to_customer_detail(self):
        self._create_checkout_variants()
        session = CheckoutSession.objects.get(pk=1)
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ana-persisted",
            full_name="Ana Souza",
            email="ana.persisted@hubx.market",
        )
        owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.checkout@hubx.market",
            full_name="Owner Checkout",
        )

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
        self.assertEqual(order.payment_source_type, "checkout_pending")
        self.assertEqual(order.payment_source_label, "Checkout aguardando pagamento")
        self.assertEqual(order.payment_reference, "")
        self.assertEqual(order.shipping_status, "Aguardando confirmação")
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.customer_id, customer.id)
        self.assertEqual(order.payment_attempts.count(), 1)
        self.assertEqual(order.payment_attempts.first().status, PaymentAttempt.Status.PENDING)
        self.assertEqual(order.payment_attempts.first().payment_method_code, "pix")
        self.assertEqual(
            str(order.payment_attempts.first().metadata.get("checkout_session_key") or ""),
            str(session.session_key),
        )
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="checkout_completed",
                description__contains=str(session.session_key),
            ).exists()
        )
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="order.created",
                intent_key="customer.order.received",
                recipient_type="customer",
                recipient_id=str(customer.id),
            ).exists()
        )
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="order.created",
                intent_key="owner.order.created",
                recipient_type="owner_user",
                recipient_id=str(owner.id),
            ).exists()
        )
        self.assertEqual(order.items.first().variant_sku, "RUNNER-PERSIST-001")
        self.assertIn(reverse("accounts:account-order-detail", kwargs={"order_number": order.number}), response["Location"])
        self.assertIn("result=checkout-completed", response["Location"])

        session.refresh_from_db()
        self.assertEqual(session.status, "completed")

        follow_response = self.client.get(response["Location"])
        self.assertContains(follow_response, "itens, entrega e pagamento já registrados")
        self.assertContains(follow_response, "pagamento ainda pendente")

    def test_checkout_review_post_reuses_existing_order_after_successful_completion(self):
        self._create_checkout_variants()
        session = CheckoutSession.objects.get(pk=1)

        first_response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(first_response.status_code, 302)
        first_order = Order.objects.order_by("-id").first()
        self.assertIsNotNone(first_order)
        self.assertEqual(Order.objects.count(), 1)
        self.assertEqual(EmailLog.objects.filter(source_event="order.created").count(), 0)

        second_response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(second_response.status_code, 302)
        self.assertEqual(Order.objects.count(), 1)
        session.refresh_from_db()
        self.assertEqual(session.status, CheckoutSession.Status.COMPLETED)
        self.assertEqual(session.completed_order_number, first_order.number)
        self.assertIn(
            reverse("accounts:account-order-detail", kwargs={"order_number": first_order.number}),
            second_response["Location"],
        )
        self.assertIn("result=checkout-completed", second_response["Location"])

    def test_checkout_review_post_flags_completed_session_drift_when_order_link_is_missing(self):
        self._create_checkout_variants()
        session = CheckoutSession.objects.get(pk=1)

        first_response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(first_response.status_code, 302)
        first_order = Order.objects.order_by("-id").first()
        self.assertIsNotNone(first_order)

        first_order.delete()

        second_response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(second_response.status_code, 302)
        self.assertIn("result=checkout-completion-session-drift", second_response["Location"])

        follow_response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-session-drift", "stage": "review"},
        )
        self.assertContains(follow_response, "Sessão concluída com vínculo inconsistente")
        self.assertContains(follow_response, "Voltar ao produto")
        self.assertNotContains(follow_response, "Reabrir checkout")
        self.assertEqual(follow_response.context["checkout_result_taxonomy"]["family"], "session")
        self.assertEqual(follow_response.context["checkout_result_taxonomy"]["recovery_action"], "restart_from_product")

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
        session = CheckoutSession.objects.create(
            tenant=self.tenant,
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
        self.assertEqual(Order.objects.filter(tenant=self.tenant).count(), 0)

        follow_response = self.client.get(
            reverse("checkout:checkout-page"),
            {"session_key": str(session.session_key), "result": "checkout-completion-blocked"},
        )
        self.assertContains(follow_response, "Revisão ainda incompleta")
        self.assertContains(follow_response, "Antes de gerar o pedido inicial")

    def test_checkout_review_post_blocks_completion_when_session_snapshot_is_inconsistent(self):
        self._create_checkout_variants()
        session = CheckoutSession.objects.get(pk=1)
        session.subtotal = Decimal("999.90")
        session.grand_total = Decimal("1024.80")
        session.save(update_fields=["subtotal", "grand_total", "updated_at"])

        response = self.client.post(
            reverse("checkout:checkout-page"),
            data={
                "session_key": str(session.session_key),
                "current_stage": "review",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=checkout-completion-snapshot-conflict", response["Location"])
        self.assertEqual(Order.objects.count(), 0)

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
        self.assertContains(follow_response, "Como retomar com segurança")
        self.assertContains(follow_response, "Volte ao produto para iniciar uma nova sessão de checkout")
        self.assertContains(follow_response, "Voltar ao produto")
