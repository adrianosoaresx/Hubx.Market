from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from app.modules.accounts.models import AccountProfile
from app.modules.customers.models import Customer, CustomerAddress
from app.modules.catalog.models import Product, ProductVariant
from app.modules.accounts.application.account_customer_area_queries import (
    account_customer_area_queries,
)
from app.modules.checkout.models import CheckoutSession, CheckoutSessionItem
from app.modules.orders.models import Order, OrderItem, OrderStatusHistory
from app.modules.payments.models import PaymentAttempt
from app.modules.shipping.models import Shipment


class CustomerAreaViewTests(TestCase):
    def test_account_orders_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-orders"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/orders_page.html")
        self.assertContains(response, "Meus pedidos")
        self.assertContains(response, "Nenhum pedido encontrado")
        self.assertContains(response, "o catálogo continua disponível para explorar produtos")

    def test_account_orders_view_applies_search_filter(self):
        response = self.client.get(reverse("accounts:account-orders"), {"q": "1041"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhum pedido encontrado")
        self.assertNotContains(response, "#1041")

    def test_account_order_detail_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "1048"}))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/order_detail_page.html")
        self.assertContains(response, "Pedido #1048")
        self.assertContains(response, "Tênis Hubx Runner")

    def test_account_order_detail_view_shows_checkout_completion_feedback_when_present(self):
        response = self.client.get(
            reverse("accounts:account-order-detail", kwargs={"order_number": "1048"}),
            {"result": "checkout-completed"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedido gerado com sucesso")
        self.assertContains(response, "agora pode ser acompanhado por aqui")
        self.assertContains(response, "Confirmação inicial do pedido")
        self.assertContains(response, "Pedido recebido com sucesso")
        self.assertContains(response, "aguardando evolução do pagamento")
        self.assertContains(response, "Próximos marcos do pedido")
        self.assertContains(response, "itens, entrega e pagamento já registrados")
        self.assertContains(response, "pagamento ainda pendente")

    def test_account_addresses_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-addresses"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/addresses_page.html")
        self.assertContains(response, "Meus endereços")
        self.assertContains(response, "Nenhum endereço salvo")
        self.assertContains(response, "Adicione um endereço para agilizar futuras compras.")

    def test_account_address_readiness_routes_redirect_back_to_addresses_page(self):
        create_response = self.client.get(reverse("accounts:account-address-create"))
        edit_response = self.client.get(reverse("accounts:account-address-edit", kwargs={"address_id": 1}))
        delete_response = self.client.get(reverse("accounts:account-address-delete", kwargs={"address_id": 1}))

        self.assertRedirects(create_response, "/accounts/account/addresses/?intent=create#address-management", fetch_redirect_response=False)
        self.assertRedirects(edit_response, "/accounts/account/addresses/?intent=edit&address_id=1#address-management", fetch_redirect_response=False)
        self.assertRedirects(delete_response, "/accounts/account/addresses/?intent=delete&address_id=1#address-management", fetch_redirect_response=False)

    def test_account_addresses_page_renders_create_form_when_intent_present(self):
        response = self.client.get(reverse("accounts:account-addresses"), {"intent": "create"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Adicionar endereço")
        self.assertContains(response, 'name="line_1"')

    def test_account_addresses_page_renders_feedback_message_when_result_present(self):
        response = self.client.get(reverse("accounts:account-addresses"), {"result": "address-created"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Endereço salvo")

    def test_account_profile_view_renders_design_system_template(self):
        response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/profile_page.html")
        self.assertContains(response, "Meu perfil")
        self.assertNotContains(response, "ana@hubx.market")
        self.assertContains(response, "Ainda não encontramos um perfil persistido")

    def test_account_customer_area_query_service_returns_expected_contract(self):
        orders_payload = account_customer_area_queries.get_orders_page_data()
        addresses_payload = account_customer_area_queries.get_addresses_page_data()
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("1048")
        confirmation_payload = account_customer_area_queries.get_order_detail_page_data("1048", confirmation_mode=True)
        profile_payload = account_customer_area_queries.get_profile_page_data()

        self.assertEqual(orders_payload["page_title"], "Meus pedidos")
        self.assertEqual(order_detail_payload["order_number"], "#1048")
        self.assertEqual(confirmation_payload["eyebrow"], "Confirmação inicial do pedido")
        self.assertEqual(confirmation_payload["summary_title"], "Pedido recebido com sucesso")
        self.assertIn("itens, entrega e forma de pagamento", confirmation_payload["page_description"].lower())
        self.assertIn("pagamento ainda pendente", confirmation_payload["page_meta"].lower())
        self.assertIn("checkout aguardando pagamento", confirmation_payload["page_meta"].lower())
        self.assertEqual(addresses_payload["addresses"], [])
        self.assertEqual(addresses_payload["operational_linkage_visibility"]["addresses_mode"], "missing")
        self.assertIn("adicione um endereço", addresses_payload["page_description"].lower())
        self.assertEqual(profile_payload["email"], "")
        self.assertEqual(profile_payload["operational_linkage_mode"], "missing")
        self.assertIn("ainda não encontramos um perfil persistido", profile_payload["page_description"].lower())
        self.assertEqual(orders_payload["operational_linkage_visibility"]["orders_mode"], "missing")

    def test_customer_area_active_profile_context_is_missing_without_persisted_profile(self):
        profile_context = account_customer_area_queries.get_active_profile_context()

        self.assertEqual(profile_context["email"], "")
        self.assertEqual(profile_context["customer_linkage_mode"], "missing")


class CustomerAreaPersistedProfileTests(TestCase):
    fixtures = ["accounts_minimal_seed.json"]

    def test_customer_area_query_service_uses_persisted_profile_when_available(self):
        profile_payload = account_customer_area_queries.get_profile_page_data()

        self.assertTrue(account_customer_area_queries.using_persisted_profile_source())
        self.assertEqual(profile_payload["email"], "ana.persisted@hubx.market")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_customer_area_views_scope_active_profile_by_request_tenant(self):
        primary_profile = AccountProfile.objects.select_related("tenant", "customer").get(pk=1)
        secondary_tenant = primary_profile.tenant.__class__.objects.create(
            name="Hubx Customer Area Secondary Tenant",
            slug="hubx-customer-area-secondary-tenant",
            subdomain="hubx-customer-area-secondary-tenant",
        )
        secondary_customer = Customer.objects.create(
            tenant=secondary_tenant,
            slug="ana-secondary-customer",
            reference="#7789",
            full_name="Ana Secondary",
            email=primary_profile.email,
            phone="(21) 97777-0000",
            status="active",
            account_type="Storefront",
        )
        AccountProfile.objects.create(
            tenant=secondary_tenant,
            customer=secondary_customer,
            email=primary_profile.email,
            first_name="Ana",
            last_name="Secondary",
            phone="(21) 97777-0000",
            newsletter_opt_in=False,
            order_updates_opt_in=True,
            is_active=True,
        )
        secondary_order = Order.objects.create(
            tenant=secondary_tenant,
            customer=secondary_customer,
            number="9090",
            status="pending",
            customer_name=secondary_customer.full_name,
            customer_email=secondary_customer.email,
            customer_phone=secondary_customer.phone,
            payment_status="Pagamento pendente",
            shipping_status="Aguardando confirmação",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_address_summary="Rua Secondary, 10 · Rio de Janeiro/RJ",
            notes_content="Pedido de outra loja.",
            subtotal="90.00",
            shipping_total="10.00",
            discount_total="0.00",
            total="100.00",
            installments_summary="",
        )
        OrderItem.objects.create(
            order=secondary_order,
            title="Item Secondary",
            subtitle="Único",
            meta="SKU SECONDARY-001",
            price_snapshot="100.00",
            quantity=1,
            sort_order=1,
        )

        profile_response = self.client.get(
            reverse("accounts:account-profile"),
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )
        orders_response = self.client.get(
            reverse("accounts:account-orders"),
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )
        scoped_profile = account_customer_area_queries.get_active_profile_context(tenant_id=primary_profile.tenant_id)

        self.assertContains(profile_response, 'value="Ana"')
        self.assertContains(profile_response, 'value="Persistida"')
        self.assertNotContains(profile_response, 'value="Secondary"')
        self.assertEqual(scoped_profile["tenant_id"], primary_profile.tenant_id)
        self.assertEqual(scoped_profile["email"], primary_profile.email)
        self.assertEqual(scoped_profile["last_name"], "Persistida")
        self.assertFalse(scoped_profile["order_updates_opt_in"])
        self.assertNotContains(orders_response, "#9090")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_customer_area_tenant_scoped_requests_do_not_fallback_to_fixture_orders_or_addresses(self):
        from app.modules.tenants.models import Tenant

        empty_tenant = Tenant.objects.create(
            name="Hubx Empty Account Tenant",
            slug="hubx-empty-account-tenant",
            subdomain="hubx-empty-account-tenant",
        )

        orders_payload = account_customer_area_queries.get_orders_page_data(tenant_id=empty_tenant.id)
        addresses_payload = account_customer_area_queries.get_addresses_page_data(tenant_id=empty_tenant.id)
        profile_payload = account_customer_area_queries.get_profile_page_data(tenant_id=empty_tenant.id)

        self.assertEqual(orders_payload["operational_linkage_visibility"]["profile_mode"], "missing")
        self.assertEqual(orders_payload["operational_linkage_visibility"]["orders_mode"], "missing")
        self.assertEqual(addresses_payload["operational_linkage_visibility"]["addresses_mode"], "missing")
        self.assertEqual(profile_payload["email"], "")

        orders_response = self.client.get(
            reverse("accounts:account-orders"),
            HTTP_HOST="hubx-empty-account-tenant.hubx.market",
        )
        addresses_response = self.client.get(
            reverse("accounts:account-addresses"),
            HTTP_HOST="hubx-empty-account-tenant.hubx.market",
        )

        self.assertNotContains(orders_response, "#1048")
        self.assertNotContains(addresses_response, "Rua Persistida, 321")

    def test_account_profile_view_renders_persisted_profile_when_present(self):
        response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/profile_page.html")
        self.assertContains(response, "ana.persisted@hubx.market")
        self.assertContains(response, "Persistida")


class CustomerAreaPersistedReadTests(TestCase):
    fixtures = ["customer_area_minimal_seed.json"]

    def test_account_orders_view_renders_persisted_orders_when_available(self):
        response = self.client.get(reverse("accounts:account-orders"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#3051")
        self.assertContains(response, "Pedido em preparação · pagamento confirmado · entrega preparando envio")

    def test_account_orders_view_applies_search_filter_to_persisted_orders(self):
        response = self.client.get(reverse("accounts:account-orders"), {"q": "3051"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#3051")
        self.assertNotContains(response, "Nenhum pedido encontrado")

    def test_customer_area_query_service_uses_persisted_sources_when_available(self):
        orders_payload = account_customer_area_queries.get_orders_page_data()
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("3051")
        addresses_payload = account_customer_area_queries.get_addresses_page_data()
        profile_payload = account_customer_area_queries.get_profile_page_data()

        self.assertTrue(account_customer_area_queries.using_persisted_profile_source())
        self.assertTrue(account_customer_area_queries.using_persisted_orders_source())
        self.assertTrue(account_customer_area_queries.using_persisted_addresses_source())

        self.assertEqual(orders_payload["page_title"], "Meus pedidos")
        self.assertIn("primeiro pedido já está salvo", orders_payload["page_description"].lower())
        self.assertIn("acompanhamento mais claro agora", orders_payload["page_description"].lower())
        self.assertIn("etapa principal da jornada", orders_payload["table_description"].lower())
        self.assertIn("catálogo segue disponível", orders_payload["table_description"].lower())
        self.assertIn("catálogo segue disponível", orders_payload["empty_description"].lower())
        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(order_detail_payload["payment_status"], "Confirmado")
        self.assertEqual(order_detail_payload["shipping_status"], "Preparando envio")
        self.assertEqual(order_detail_payload["subtotal"], "R$ 249,90")
        self.assertEqual(order_detail_payload["total"], "R$ 269,80")
        self.assertEqual(order_detail_payload["order_items"][0]["title"], "Tênis Hubx Area")
        self.assertIn("pagamento confirmado", order_detail_payload["summary_content"].lower())
        self.assertIn("entrega em preparando envio", order_detail_payload["summary_content"].lower())
        self.assertIn("Atualizado há", order_detail_payload["summary_subtitle"])
        self.assertIn("confirmação do envio", order_detail_payload["summary_subtitle"].lower())
        self.assertIn("página continua sendo o melhor lugar", order_detail_payload["page_description"].lower())
        self.assertIn("catálogo segue disponível", order_detail_payload["page_description"].lower())
        self.assertIn("pagamento já foi aprovado", order_detail_payload["summary_note"].lower())
        self.assertIn("confirmação interna", order_detail_payload["summary_note"].lower())
        self.assertIn("Entrega prevista para Rua Persistida, 321", order_detail_payload["summary_note"])
        self.assertIn("próxima compra mais simples", order_detail_payload["summary_note"].lower())
        self.assertIn("confirmação do envio", order_detail_payload["summary_note"].lower())
        self.assertIn("catálogo segue disponível", order_detail_payload["summary_note"].lower())
        self.assertIn("atualizado há", order_detail_payload["page_meta"].lower())
        self.assertEqual(order_detail_payload["summary_title"], "Pedido em preparação")
        self.assertEqual(order_detail_payload["status_title"], "Etapa atual do pedido")
        self.assertEqual(order_detail_payload["activity_title"], "Marcos do pedido")
        self.assertEqual(order_detail_payload["activity_items"][0]["title"], "Pedido em preparação")
        self.assertEqual(order_detail_payload["activity_items"][1]["title"], "Andamento de pagamento e entrega")
        self.assertEqual(order_detail_payload["activity_items"][2]["title"], "Próximo passo esperado")
        self.assertIn("confirmação do envio", order_detail_payload["activity_items"][2]["description"].lower())
        self.assertIn("catálogo segue disponível", order_detail_payload["activity_description"].lower())
        self.assertEqual(order_detail_payload["activity_items"][-1]["title"], "Histórico salvo na sua conta")
        self.assertIn("primeiro pedido", order_detail_payload["activity_items"][-1]["description"].lower())

        self.assertEqual(addresses_payload["addresses"][0]["title"], "Casa")
        self.assertIn("Rua Persistida, 321", addresses_payload["addresses"][0]["content"])
        self.assertIn("CEP 01010-100", addresses_payload["addresses"][0]["footer"])
        self.assertIn("2 endereços salvos", addresses_payload["page_description"].lower())
        self.assertIn("endereço principal atual é casa", addresses_payload["page_description"].lower())

        self.assertEqual(profile_payload["email"], "ana.area@hubx.market")
        self.assertEqual(profile_payload["last_name"], "Área")
        self.assertIn("deixar seu primeiro pedido", profile_payload["page_description"].lower())
        self.assertIn("histórico da conta mais confiável", profile_payload["personal_info_description"].lower())
        self.assertIn("acompanhar o andamento do pedido atual", profile_payload["preferences_description"].lower())
        self.assertEqual(orders_payload["operational_linkage_visibility"]["profile_mode"], "explicit")
        self.assertEqual(orders_payload["operational_linkage_visibility"]["orders_mode"], "explicit")
        self.assertEqual(orders_payload["operational_linkage_visibility"]["customer_data_mode"], "ready")
        self.assertEqual(orders_payload["operational_linkage_visibility"]["customer_data_issue_codes"], "")
        self.assertEqual(addresses_payload["operational_linkage_visibility"]["addresses_mode"], "explicit")
        self.assertEqual(order_detail_payload["operational_linkage_mode"], "explicit")
        self.assertEqual(profile_payload["operational_linkage_mode"], "explicit")

    def test_customer_area_linkage_visibility_surfaces_customer_data_issues(self):
        profile = AccountProfile.objects.select_related("tenant", "customer").get(pk=2)
        Order.objects.create(
            tenant=profile.tenant,
            customer=None,
            number="3099",
            status="paid",
            customer_name="Ana Área",
            customer_email=profile.email,
            customer_phone=profile.phone,
            payment_status="Confirmado",
            shipping_status="Entregue",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            subtotal="100.00",
            shipping_total="0.00",
            discount_total="0.00",
            total="100.00",
        )
        Order.objects.filter(number="3099").update(customer=None)

        visibility = account_customer_area_queries.get_linkage_visibility(tenant_id=profile.tenant_id)

        self.assertEqual(visibility["customer_data_mode"], "needs_attention")
        self.assertIn("order_email_fallback", visibility["customer_data_issue_codes"])

    def test_customer_area_query_service_prefers_explicit_links_when_available(self):
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(order_detail_payload["payment_status"], "Confirmado")

    def test_customer_area_query_service_falls_back_to_tenant_and_email_when_links_are_absent(self):
        AccountProfile.objects.filter(pk=2).update(customer=None)
        Order.objects.filter(pk=2).update(customer=None, customer_email="ana.area@hubx.market")

        orders = account_customer_area_queries.list_orders()
        order_detail_payload = account_customer_area_queries.get_order_detail_page_data("3051")
        addresses_payload = account_customer_area_queries.get_addresses_page_data()

        self.assertEqual(len(orders), 1)
        self.assertEqual(order_detail_payload["order_number"], "#3051")
        self.assertEqual(addresses_payload["addresses"][0]["title"], "Casa")
        self.assertEqual(account_customer_area_queries.get_linkage_visibility()["profile_mode"], "fallback")
        self.assertEqual(account_customer_area_queries.get_linkage_visibility()["orders_mode"], "fallback")

    def test_customer_area_views_render_persisted_records_when_present(self):
        orders_response = self.client.get(reverse("accounts:account-orders"))
        order_detail_response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))
        addresses_response = self.client.get(reverse("accounts:account-addresses"))
        profile_response = self.client.get(reverse("accounts:account-profile"))

        self.assertEqual(orders_response.status_code, 200)
        self.assertContains(orders_response, "#3051")
        self.assertContains(orders_response, "Pedido em preparação · pagamento confirmado · entrega preparando envio")
        self.assertContains(orders_response, "pedido em preparação")
        self.assertContains(orders_response, "Atualizado em 16/04/2026")
        self.assertContains(orders_response, "primeiro pedido já está salvo")
        self.assertContains(orders_response, "acompanhamento mais claro agora")
        self.assertContains(orders_response, "catálogo continua disponível")

        self.assertEqual(order_detail_response.status_code, 200)
        self.assertContains(order_detail_response, "Pedido #3051")
        self.assertContains(order_detail_response, "Tênis Hubx Area")
        self.assertContains(order_detail_response, "Entrega em Rua Persistida, 321 · São Paulo/SP · última atualização em 16/04/2026")
        self.assertContains(order_detail_response, "atualizado há")
        self.assertContains(order_detail_response, "Entrega prevista para Rua Persistida, 321")
        self.assertContains(order_detail_response, "Etapa atual do pedido")
        self.assertContains(order_detail_response, "Pedido em preparação")
        self.assertContains(order_detail_response, "Andamento de pagamento e entrega")
        self.assertContains(order_detail_response, "Marcos do pedido")
        self.assertContains(order_detail_response, "Próximo passo esperado")
        self.assertContains(order_detail_response, "confirmação do envio")
        self.assertContains(order_detail_response, "catálogo segue disponível")
        self.assertContains(order_detail_response, "acompanhamento contínuo pela área do cliente")
        self.assertContains(order_detail_response, "Histórico salvo na sua conta")
        self.assertContains(order_detail_response, "confirmação interna")

        self.assertEqual(addresses_response.status_code, 200)
        self.assertContains(addresses_response, "2 endereços salvos")
        self.assertContains(addresses_response, "endereço principal atual é Casa")
        self.assertContains(addresses_response, "Rua Persistida, 321")
        self.assertContains(addresses_response, "Escritório")
        self.assertContains(addresses_response, '/accounts/account/addresses/1/edit/')
        self.assertContains(addresses_response, '/accounts/account/addresses/new/')

        self.assertEqual(profile_response.status_code, 200)
        self.assertContains(profile_response, "deixar seu primeiro pedido")
        self.assertContains(profile_response, "histórico da conta mais confiável")
        self.assertContains(profile_response, "acompanhar o andamento do pedido atual")
        self.assertContains(profile_response, "ana.area@hubx.market")
        self.assertContains(profile_response, "Área")

    def test_account_order_detail_view_shows_payment_confirmation_action_for_pending_order(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Confirmar pagamento")
        self.assertContains(response, "confirmado fora do fluxo automático")

    def test_account_order_detail_view_shows_payment_retry_action_for_failed_payment(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento falhou",
            payment_source_type="external_payment_failed",
            payment_source_label="Gateway Stripe",
            fulfillment_status_label="Aguardando novo pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando nova tentativa",
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tentar pagamento novamente")
        self.assertContains(response, "retomar o pagamento com segurança")

    def test_account_order_detail_view_shows_hosted_payment_action_when_pending_attempt_exists(self):
        order = Order.objects.get(pk=2)
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
        )
        attempt = PaymentAttempt.objects.create(
            tenant=order.tenant,
            order=order,
            payment_method_code="credit_card",
            provider_code="stripe",
            provider_label="Gateway Stripe",
            status=PaymentAttempt.Status.PENDING,
            amount=order.total,
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Abrir pagamento seguro")
        self.assertContains(response, "o pedido continua salvo enquanto a confirmação não chega")
        self.assertContains(response, reverse("payments:hosted-redirect", kwargs={"attempt_key": attempt.attempt_key}))

    def test_account_order_detail_view_shows_hosted_payment_return_feedback(self):
        expectations = {
            "hosted-payment-unavailable": (
                "Pagamento seguro indisponível",
                "Seu pedido continua salvo; tente novamente em instantes.",
            ),
            "hosted-payment-returned": (
                "Você voltou do pagamento seguro",
                "O pedido continua salvo enquanto aguardamos a confirmação segura.",
            ),
            "hosted-payment-return-pending-verification": (
                "Pagamento em verificação",
                "Nenhuma ação extra é necessária agora.",
            ),
            "hosted-payment-return-failed": (
                "Tentativa de pagamento não concluída",
                "Seu pedido continua salvo para você revisar e tentar novamente com segurança.",
            ),
        }

        for result, expected_parts in expectations.items():
            with self.subTest(result=result):
                response = self.client.get(
                    reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
                    {"result": result},
                )

                self.assertEqual(response.status_code, 200)
                for expected in expected_parts:
                    self.assertContains(response, expected)

    def test_account_order_detail_view_shows_payment_operational_timeline_when_attempt_exists(self):
        order = Order.objects.get(pk=2)
        PaymentAttempt.objects.create(
            tenant=order.tenant,
            order=order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount=order.total,
            metadata={
                "timeline": [
                    {
                        "code": "attempt_created",
                        "title": "Tentativa de pagamento criada",
                        "description": "A trilha foi iniciada a partir do pedido pendente.",
                        "level": "info",
                        "at": "2026-04-21T10:00:00-03:00",
                    },
                    {
                        "code": "provider_intent_created",
                        "title": "Link de pagamento criado",
                        "description": "O provider devolveu uma URL hospedada para continuar o pagamento.",
                        "level": "info",
                        "at": "2026-04-21T10:05:00-03:00",
                    },
                ]
            },
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trilha do pagamento")
        self.assertContains(response, "Pedido confirmado com tentativa ainda pendente")
        self.assertContains(response, "Tentativa de pagamento criada")
        self.assertContains(response, "Link de pagamento criado")

    def test_account_order_detail_flags_order_payment_drift_when_order_is_paid_but_attempt_is_pending(self):
        order = Order.objects.get(pk=2)
        PaymentAttempt.objects.create(
            tenant=order.tenant,
            order=order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount=order.total,
            metadata={},
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedido confirmado com tentativa ainda pendente")
        self.assertContains(response, "a tentativa de pagamento ainda não foi reconciliada")

    def test_account_order_detail_view_flags_long_lived_pending_attempt(self):
        order = Order.objects.get(pk=2)
        attempt = PaymentAttempt.objects.create(
            tenant=order.tenant,
            order=order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount=order.total,
            metadata={},
        )
        PaymentAttempt.objects.filter(pk=attempt.pk).update(
            created_at=timezone.now() - timedelta(hours=7),
            updated_at=timezone.now() - timedelta(hours=7),
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tentativa pendente há tempo demais")
        self.assertContains(response, "já merece reconciliação operacional")
        self.assertContains(response, "não há uma retomada automática segura")

    def test_account_order_detail_recommends_hosted_recovery_for_stale_pending_attempt_when_retry_path_exists(self):
        order = Order.objects.get(pk=2)
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
        )
        attempt = PaymentAttempt.objects.create(
            tenant=order.tenant,
            order=order,
            payment_method_code="pix",
            provider_code="pagarme",
            provider_label="Pagar.me",
            status=PaymentAttempt.Status.PENDING,
            amount=order.total,
            metadata={},
        )
        PaymentAttempt.objects.filter(pk=attempt.pk).update(
            created_at=timezone.now() - timedelta(hours=7),
            updated_at=timezone.now() - timedelta(hours=7),
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "vale reabrir o ambiente seguro")
        self.assertContains(response, "Retomar pagamento seguro")

    def test_account_order_detail_flags_long_lived_pending_order_without_clear_recovery(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            payment_source_type="checkout_pending",
            payment_source_label="Checkout aguardando pagamento",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
            updated_at=timezone.now() - timedelta(days=2),
        )

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pedido pendente sem avanço recente")
        self.assertContains(response, "vale revisar esse estado com suporte")

    def test_account_order_detail_view_shows_reorder_lite_action_when_items_exist(self):
        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Comprar novamente")
        self.assertContains(response, "recriar uma nova sessão")

    def test_account_order_detail_post_bootstraps_reorder_session_from_eligible_items(self):
        order = Order.objects.get(pk=2)
        product = Product.objects.create(
            tenant=order.tenant,
            name="Tênis Hubx Area Reorder",
            slug="tenis-hubx-area-reorder",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="AREA-001-WHT-39",
            price="279.90",
            compare_price="299.90",
            stock=8,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        stale_session = CheckoutSession.objects.create(
            tenant=order.tenant,
            status=CheckoutSession.Status.OPEN,
            subtotal="10.00",
            shipping_methods=[{"value": "standard", "label": "Entrega padrão", "price": "R$ 24,90"}],
            shipping_method_selected="standard",
            payment_methods=[{"value": "credit_card", "label": "Cartão de crédito"}],
            payment_method_selected="credit_card",
            shipping_total="24.90",
            grand_total="34.90",
        )
        CheckoutSessionItem.objects.create(
            checkout_session=stale_session,
            title="Item antigo",
            subtitle="Legado",
            meta="SKU OLD-001",
            variant_sku="OLD-001",
            price="10.00",
            quantity=1,
            sort_order=1,
        )

        response = self.client.post(
            reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
            {"action_type": "reorder_lite"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("checkout:checkout-page"), response["Location"])
        self.assertIn("result=reorder-lite-ready", response["Location"])
        self.assertIn("stage=cart", response["Location"])
        self.assertIn("back_url=%2Faccounts%2Faccount%2Forders%2F3051%2F", response["Location"])

        stale_session.refresh_from_db()
        self.assertEqual(stale_session.items.count(), 1)
        item = stale_session.items.first()
        self.assertEqual(item.variant_sku, "AREA-001-WHT-39")
        self.assertEqual(item.title, "Tênis Hubx Area Reorder")
        self.assertEqual(item.subtitle, "Branco · 39")
        self.assertEqual(str(item.price), "279.90")
        self.assertEqual(str(stale_session.subtotal), "279.90")
        self.assertEqual(str(stale_session.shipping_total), "24.90")
        self.assertEqual(str(stale_session.grand_total), "304.80")

        checkout_response = self.client.get(response["Location"])
        self.assertContains(checkout_response, "Nova sessão pronta")
        self.assertContains(checkout_response, "Confira seu carrinho")
        self.assertContains(checkout_response, "Tênis Hubx Area Reorder")

    def test_account_order_detail_post_bootstraps_partial_reorder_when_some_items_are_ineligible(self):
        order = Order.objects.get(pk=2)
        product = Product.objects.create(
            tenant=order.tenant,
            name="Tênis Hubx Area Reorder",
            slug="tenis-hubx-area-reorder-partial",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="AREA-001-WHT-39",
            price="279.90",
            stock=8,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )
        OrderItem.objects.create(
            order=order,
            title="Item não elegível",
            subtitle="Cinza · 40",
            meta="SKU MISSING-AREA-40",
            price_snapshot="89.90",
            quantity=1,
            quantity_readonly=True,
            sort_order=2,
        )

        response = self.client.post(
            reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
            {"action_type": "reorder_lite"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=reorder-lite-partial", response["Location"])

        session = CheckoutSession.objects.get(tenant=order.tenant, status=CheckoutSession.Status.OPEN)
        self.assertEqual(session.items.count(), 1)
        self.assertEqual(session.items.first().variant_sku, "AREA-001-WHT-39")

    def test_account_order_detail_post_blocks_reorder_when_no_item_is_eligible(self):
        response = self.client.post(
            reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
            {"action_type": "reorder_lite"},
        )

        self.assertRedirects(
            response,
            "/accounts/account/orders/3051/?result=reorder-lite-unavailable",
            fetch_redirect_response=False,
        )

    def test_account_order_detail_post_bootstraps_payment_retry_session_from_failed_order(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento falhou",
            payment_source_type="external_payment_failed",
            payment_source_label="Gateway Stripe",
            payment_reference="pi_fail_001",
            fulfillment_status_label="Aguardando novo pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando nova tentativa",
        )
        order = Order.objects.get(pk=2)
        product = Product.objects.create(
            tenant=order.tenant,
            name="Tênis Hubx Retry",
            slug="tenis-hubx-retry",
            brand_name="Hubx",
            category_label="Calçados esportivos",
            status="active",
            is_active=True,
        )
        ProductVariant.objects.create(
            product=product,
            sku="AREA-001-WHT-39",
            price="279.90",
            stock=8,
            reserved_stock=0,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        response = self.client.post(
            reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
            {"action_type": "payment_retry"},
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("checkout:checkout-page"), response["Location"])
        self.assertIn("result=payment-retry-ready", response["Location"])
        self.assertIn("stage=payment", response["Location"])

        session = CheckoutSession.objects.get(tenant=order.tenant, status=CheckoutSession.Status.OPEN)
        self.assertEqual(session.items.count(), 1)
        self.assertEqual(session.items.first().variant_sku, "AREA-001-WHT-39")

        checkout_response = self.client.get(response["Location"])
        self.assertContains(checkout_response, "Sessão pronta para nova tentativa")
        self.assertContains(checkout_response, "Escolha o pagamento")

    def test_account_order_detail_post_confirms_internal_payment_for_current_customer(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
            notes_content="Pedido iniciado a partir da revisão do checkout. Aguardando evolução do fluxo de pagamento.",
        )
        order = Order.objects.get(pk=2)
        ProductVariant.objects.create(
            product=Product.objects.create(
                tenant=order.tenant,
                name="Tênis Hubx Area Estoque",
                slug="tenis-hubx-area-estoque",
                brand_name="Hubx",
                category_label="Calçados esportivos",
                status="active",
                is_active=True,
            ),
            sku="AREA-001-WHT-39",
            price="249.90",
            stock=6,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        response = self.client.post(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}), {"action_type": "confirm_payment"})

        self.assertRedirects(response, "/accounts/account/orders/3051/?result=payment-confirmed", fetch_redirect_response=False)

        order = Order.objects.get(pk=2)
        self.assertEqual(order.status, "paid")
        self.assertEqual(order.payment_status, "Confirmado internamente")
        self.assertEqual(order.payment_source_type, "internal_confirmation")
        self.assertEqual(order.payment_source_label, "Confirmação interna")
        self.assertEqual(order.payment_reference, "")
        self.assertIsNotNone(order.payment_confirmed_at)
        self.assertEqual(order.fulfillment_status_label, "Separando itens")
        self.assertEqual(order.shipping_status, "Preparando envio")
        self.assertIsNotNone(order.inventory_reserved_at)
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="payment_confirmed_internally",
                source_type="checkout_progression",
            ).exists()
        )
        self.assertTrue(
            OrderStatusHistory.objects.filter(
                order=order,
                event_type="inventory_reserved_after_payment",
                source_type="checkout_progression",
            ).exists()
        )
        variant = ProductVariant.objects.get(sku="AREA-001-WHT-39")
        self.assertEqual(variant.stock, 5)
        self.assertEqual(variant.reserved_stock, 2)

        refreshed = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}), {"result": "payment-confirmed"})
        self.assertContains(refreshed, "Pagamento confirmado")
        self.assertContains(refreshed, "confirmação interna do pagamento")
        self.assertContains(refreshed, "Origem atual do pagamento: confirmação interna.")
        self.assertContains(refreshed, "Confirmado internamente")
        self.assertContains(refreshed, "operação em separando itens")
        self.assertNotContains(refreshed, "Confirmar pagamento")

    def test_account_order_detail_post_handles_already_confirmed_payment_safely(self):
        response = self.client.post(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}), {"action_type": "confirm_payment"})

        self.assertRedirects(response, "/accounts/account/orders/3051/?result=payment-already-confirmed", fetch_redirect_response=False)

    def test_account_order_detail_post_blocks_payment_confirmation_when_variant_is_unavailable(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
        )

        response = self.client.post(
            reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
            {"action_type": "confirm_payment"},
        )

        self.assertRedirects(
            response,
            "/accounts/account/orders/3051/?result=payment-confirmation-inventory-unavailable",
            fetch_redirect_response=False,
        )
        order = Order.objects.get(pk=2)
        self.assertEqual(order.status, "pending")
        self.assertIsNone(order.inventory_reserved_at)

    def test_account_order_detail_post_blocks_payment_confirmation_when_free_stock_is_insufficient(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
        )
        order = Order.objects.get(pk=2)
        ProductVariant.objects.create(
            product=Product.objects.create(
                tenant=order.tenant,
                name="Tênis Hubx Area Estoque Limitado",
                slug="tenis-hubx-area-estoque-limitado",
                brand_name="Hubx",
                category_label="Calçados esportivos",
                status="active",
                is_active=True,
            ),
            sku="AREA-001-WHT-39",
            price="249.90",
            stock=1,
            reserved_stock=1,
            track_inventory=True,
            allow_backorder=False,
            is_default=True,
        )

        response = self.client.post(
            reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}),
            {"action_type": "confirm_payment"},
        )

        self.assertRedirects(
            response,
            "/accounts/account/orders/3051/?result=payment-confirmation-stock-conflict",
            fetch_redirect_response=False,
        )
        order = Order.objects.get(pk=2)
        self.assertEqual(order.status, "pending")
        self.assertIsNone(order.inventory_reserved_at)

    def test_account_order_detail_polishes_completed_order_perception(self):
        Order.objects.filter(pk=2).update(
            status="shipped",
            payment_status="Confirmado internamente",
            fulfillment_status_label="Concluído",
            fulfillment_status_variant="success",
            shipping_status="Entregue",
            notes_content="Pedido concluído e disponível apenas como histórico da conta.",
        )

        payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertIn("pedido já foi concluído", payload["page_description"].lower())
        self.assertIn("pronta para voltar ao catálogo", payload["page_meta"].lower())
        self.assertIn("pedido já foi entregue", payload["summary_note"].lower())
        self.assertIn("pedido entregue", payload["activity_items"][0]["title"].lower())
        self.assertIn("jornada concluída", payload["activity_items"][1]["title"].lower())
        self.assertIn("nova compra", payload["activity_items"][2]["description"].lower())
        self.assertIn("catálogo continua sendo o melhor ponto", payload["activity_description"].lower())

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))
        self.assertContains(response, "pedido já foi concluído")
        self.assertContains(response, "Pedido entregue")
        self.assertContains(response, "Jornada concluída")
        self.assertContains(response, "Pronta para voltar ao catálogo")
        self.assertContains(response, "Entrega concluída")

    def test_account_order_detail_shows_delivery_tracking_for_preparation(self):
        payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertTrue(payload["delivery_tracking_visible"])
        self.assertEqual(payload["delivery_tracking_title"], "Preparando seu pedido")
        self.assertIn("próximo marco esperado", payload["delivery_tracking_description"].lower())

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertContains(response, "Preparando seu pedido")
        self.assertContains(response, "saída do pedido para transporte")

    def test_account_order_detail_shows_delivery_tracking_for_shipped_order(self):
        Order.objects.filter(pk=2).update(
            status="shipped",
            payment_status="Confirmado internamente",
            fulfillment_status_label="Em trânsito",
            fulfillment_status_variant="shipped",
            shipping_status="Em trânsito",
        )

        payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertTrue(payload["delivery_tracking_visible"])
        self.assertEqual(payload["delivery_tracking_title"], "Pedido a caminho")
        self.assertIn("transporte", payload["delivery_tracking_description"].lower())

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertContains(response, "Pedido a caminho")
        self.assertContains(response, "As próximas atualizações importantes aparecerão nesta página.")

    def test_account_order_detail_shows_normalized_tracking_snapshot_when_available(self):
        order = Order.objects.get(pk=2)
        order.status = "shipped"
        order.payment_status = "Confirmado internamente"
        order.fulfillment_status_label = "Em trânsito"
        order.fulfillment_status_variant = "shipped"
        order.shipping_status = "Em trânsito"
        order.save()
        Shipment.objects.create(
            tenant=order.tenant,
            order=order,
            status=Shipment.Status.SENT,
            tracking_code="BR3051",
            tracking_url="https://tracking.example/BR3051",
            carrier_name="Correios",
        )

        payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertEqual(payload["delivery_tracking_status"], "in_transit")
        self.assertEqual(payload["delivery_tracking_code"], "BR3051")
        self.assertEqual(payload["delivery_tracking_url"], "https://tracking.example/BR3051")
        self.assertEqual(payload["delivery_tracking_carrier"], "Correios")
        self.assertEqual(payload["delivery_tracking_action_label"], "Acompanhar entrega")
        self.assertIn("transportadora: Correios", payload["delivery_tracking_description"])
        self.assertIn("código: BR3051", payload["delivery_tracking_description"])

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertContains(response, "transportadora: Correios")
        self.assertContains(response, "código: BR3051")
        self.assertContains(response, 'href="https://tracking.example/BR3051"')
        self.assertContains(response, "Acompanhar entrega")

    def test_account_order_detail_hides_delivery_tracking_for_pending_payment(self):
        Order.objects.filter(pk=2).update(
            status="pending",
            payment_status="Pagamento pendente",
            fulfillment_status_label="Aguardando pagamento",
            fulfillment_status_variant="warning",
            shipping_status="Aguardando confirmação",
        )

        payload = account_customer_area_queries.get_order_detail_page_data("3051")

        self.assertFalse(payload["delivery_tracking_visible"])

        response = self.client.get(reverse("accounts:account-order-detail", kwargs={"order_number": "3051"}))

        self.assertNotContains(response, "Preparando seu pedido")
        self.assertNotContains(response, "Pedido a caminho")

    def test_account_overview_uses_retention_messaging_when_persisted_orders_exist(self):
        response = self.client.get(reverse("accounts:account-overview"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "histórico já começou")
        self.assertContains(response, "acompanhar seu pedido atual")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_account_address_create_persists_customer_address(self):
        primary_profile = AccountProfile.objects.select_related("tenant").get(pk=2)
        response = self.client.post(
            reverse("accounts:account-address-create"),
            {
                "label": "Casa nova",
                "recipient_name": "Ana Área",
                "line_1": "Rua Nova, 500",
                "line_2": "Casa 2",
                "district": "Jardins",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "01400-000",
                "is_default": "1",
            },
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-created#address-management", fetch_redirect_response=False)

        refreshed = self.client.get(
            reverse("accounts:account-addresses"),
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )
        self.assertContains(refreshed, "Casa nova")
        self.assertContains(refreshed, "Rua Nova, 500")

    def test_account_address_create_requires_tenant_context(self):
        response = self.client.post(
            reverse("accounts:account-address-create"),
            {
                "label": "Casa sem tenant",
                "recipient_name": "Ana Área",
                "line_1": "Rua Sem Tenant, 1",
                "line_2": "",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "01000-000",
                "is_default": "1",
            },
        )

        self.assertRedirects(
            response,
            "/accounts/account/addresses/?result=address-create-unavailable#address-management",
            fetch_redirect_response=False,
        )
        self.assertFalse(CustomerAddress.objects.filter(label="Casa sem tenant").exists())

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_account_address_create_scopes_command_by_request_tenant(self):
        primary_profile = (
            AccountProfile.objects.select_related("tenant", "customer").filter(is_active=True).order_by("id").first()
        )
        self.assertIsNotNone(primary_profile)
        self.assertIsNotNone(primary_profile.customer)

        from app.modules.tenants.models import Tenant

        secondary_tenant = Tenant.objects.create(
            name="Hubx Address Secondary Tenant",
            slug="hubx-address-secondary-tenant",
            subdomain="hubx-address-secondary-tenant",
        )
        secondary_customer = Customer.objects.create(
            tenant=secondary_tenant,
            slug="secondary-address-customer",
            reference="#9090",
            full_name="Ana Área Secundária",
            email=primary_profile.email,
            phone="(11) 95555-0000",
            status="active",
            account_type="Storefront",
        )
        AccountProfile.objects.create(
            tenant=secondary_tenant,
            customer=secondary_customer,
            email=primary_profile.email,
            first_name="Ana",
            last_name="Secundária",
            phone="(11) 95555-0000",
            is_active=True,
        )

        response = self.client.post(
            reverse("accounts:account-address-create"),
            {
                "label": "Casa tenant-aware",
                "recipient_name": "Ana Principal",
                "line_1": "Rua Tenant, 10",
                "line_2": "",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "01000-100",
                "is_default": "1",
            },
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-created#address-management", fetch_redirect_response=False)
        self.assertTrue(
            CustomerAddress.objects.filter(customer=primary_profile.customer, label="Casa tenant-aware").exists()
        )
        self.assertFalse(
            CustomerAddress.objects.filter(customer=secondary_customer, label="Casa tenant-aware").exists()
        )

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_account_address_edit_updates_customer_address(self):
        primary_profile = AccountProfile.objects.select_related("tenant").get(pk=2)
        response = self.client.post(
            reverse("accounts:account-address-edit", kwargs={"address_id": 1}),
            {
                "label": "Casa atualizada",
                "recipient_name": "Ana Área",
                "line_1": "Rua Persistida, 999",
                "line_2": "Apto 99",
                "district": "Centro",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "01010-100",
                "is_default": "1",
            },
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-updated#address-management", fetch_redirect_response=False)

        refreshed = self.client.get(
            reverse("accounts:account-addresses"),
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )
        self.assertContains(refreshed, "Casa atualizada")
        self.assertContains(refreshed, "Rua Persistida, 999")

    @override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "localhost", "testserver"])
    def test_account_address_delete_removes_current_customer_address(self):
        primary_profile = AccountProfile.objects.select_related("tenant").get(pk=2)
        confirmation = self.client.get(
            reverse("accounts:account-addresses"),
            {"intent": "delete", "address_id": "1"},
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )
        self.assertContains(confirmation, "Remover endereço")

        response = self.client.post(
            reverse("accounts:account-address-delete", kwargs={"address_id": 1}),
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-deleted#address-management", fetch_redirect_response=False)

        refreshed = self.client.get(
            reverse("accounts:account-addresses"),
            HTTP_HOST=f"{primary_profile.tenant.subdomain}.hubx.market",
        )
        self.assertNotContains(refreshed, "Rua Persistida, 321")
        self.assertContains(refreshed, "Escritório")

    def test_account_address_delete_does_not_remove_another_customer_address(self):
        customer = Customer.objects.create(
            tenant_id=7,
            slug="outro-customer",
            reference="#7788",
            full_name="Outro Customer",
            email="outro@hubx.market",
            phone="(11) 94444-0000",
            status="active",
            account_type="Storefront",
        )
        address = CustomerAddress.objects.create(
            customer=customer,
            label="Outro endereço",
            recipient_name="Outro Customer",
            line_1="Rua de Outro, 10",
            district="Centro",
            city="São Paulo",
            state="SP",
            postal_code="01000-000",
            is_default=False,
        )

        response = self.client.post(reverse("accounts:account-address-delete", kwargs={"address_id": address.pk}))

        self.assertRedirects(response, "/accounts/account/addresses/?result=address-delete-blocked#address-management", fetch_redirect_response=False)
        self.assertTrue(CustomerAddress.objects.filter(pk=address.pk).exists())

    def test_account_address_create_shows_inline_feedback_when_form_is_invalid(self):
        response = self.client.post(
            reverse("accounts:account-address-create"),
            {
                "label": "",
                "recipient_name": "Ana Área",
                "line_1": "",
                "city": "São Paulo",
                "state": "SP",
                "postal_code": "",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Revise os campos do endereço")
        self.assertContains(response, "Este campo é obrigatório")
