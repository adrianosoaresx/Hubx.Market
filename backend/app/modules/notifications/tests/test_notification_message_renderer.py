from django.test import TestCase, override_settings

from app.modules.notifications.application.notification_message_renderer import render_email_log_message
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


@override_settings(ROOT_URLCONF="config.urls", HUBX_MARKET_ROOT_DOMAIN="hubx.market")
class NotificationMessageRendererTests(TestCase):
    def test_renders_plain_text_message_with_resolved_cta(self):
        tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-render",
            subdomain="loja-teste-render",
        )
        order = Order.objects.create(
            tenant=tenant,
            number="9201",
            customer_email="cliente.render@example.com",
            total="10.00",
        )
        log = EmailLog.objects.create(
            tenant=tenant,
            source_event="payment.paid",
            intent_key="customer.payment.confirmed",
            audience="customer",
            entity_type="order",
            entity_id=str(order.id),
            idempotency_key=f"{tenant.id}:customer.payment.confirmed:order:{order.id}:email",
            recipient_delivery_key=f"{tenant.id}:customer.payment.confirmed:order:{order.id}:email:customer:99",
            recipient_type="customer",
            recipient_id="99",
            recipient_email="customer@example.com",
            title="Pagamento confirmado",
            description="O pagamento foi confirmado.",
            cta_label="Ver pedido",
            cta_target="customer_order_detail",
        )

        rendered = render_email_log_message(log=log)

        self.assertEqual(rendered.subject, "Pagamento confirmado")
        self.assertIn("O pagamento foi confirmado.", rendered.plain_text)
        self.assertIn("Ver pedido: https://loja-teste-render.hubx.market/accounts/account/orders/9201/", rendered.plain_text)
        self.assertEqual(rendered.cta_url, "https://loja-teste-render.hubx.market/accounts/account/orders/9201/")
