from django.test import TestCase, override_settings

from app.modules.customers.models import Customer
from app.modules.notifications.application.notification_cta_resolver import resolve_notification_cta
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


@override_settings(ROOT_URLCONF="config.urls", HUBX_MARKET_ROOT_DOMAIN="hubx.market")
class NotificationCtaResolverTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Loja Teste",
            slug="loja-teste-cta",
            subdomain="loja-teste-cta",
        )
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-cta",
            full_name="Cliente CTA",
            email="cliente.cta@example.com",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9101",
            customer_email="cliente.cta@example.com",
            total="99.90",
        )

    def test_resolves_customer_order_detail_cta_url(self):
        cta = resolve_notification_cta(
            tenant_id=self.tenant.id,
            cta_label="Ver pedido",
            cta_target="customer_order_detail",
            entity_type="order",
            entity_id=self.order.id,
        )

        self.assertIsNotNone(cta)
        self.assertEqual(cta.label, "Ver pedido")
        self.assertEqual(cta.url, "https://loja-teste-cta.hubx.market/accounts/account/orders/9101/")

    def test_resolves_admin_order_detail_cta_url_with_custom_domain(self):
        self.tenant.custom_domain = "loja.example.com"
        self.tenant.save(update_fields=("custom_domain", "updated_at"))

        cta = resolve_notification_cta(
            tenant_id=self.tenant.id,
            cta_label="Abrir pedido",
            cta_target="admin_order_detail",
            entity_type="order",
            entity_id=self.order.id,
        )

        self.assertIsNotNone(cta)
        self.assertEqual(cta.url, "https://loja.example.com/ops/orders/9101/")

    def test_returns_none_for_unknown_target_or_cross_tenant_order(self):
        other_tenant = Tenant.objects.create(
            name="Outra Loja",
            slug="outra-loja-cta",
            subdomain="outra-loja-cta",
        )

        self.assertIsNone(
            resolve_notification_cta(
                tenant_id=self.tenant.id,
                cta_label="Abrir",
                cta_target="unknown",
                entity_type="order",
                entity_id=self.order.id,
            )
        )
        self.assertIsNone(
            resolve_notification_cta(
                tenant_id=other_tenant.id,
                cta_label="Abrir",
                cta_target="customer_order_detail",
                entity_type="order",
                entity_id=self.order.id,
            )
        )
