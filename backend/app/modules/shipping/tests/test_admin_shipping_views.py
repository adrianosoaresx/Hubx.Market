from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.customers.models import Customer
from app.modules.notifications.models import EmailLog
from app.modules.orders.models import Order
from app.modules.shipping.models import Shipment, ShipmentStatusHistory
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class AdminShippingViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Ship Admin", slug="loja-ship-admin", subdomain="loja-ship-admin")
        self.customer = Customer.objects.create(
            tenant=self.tenant,
            slug="cliente-ship-admin",
            full_name="Cliente Ship Admin",
            email="cliente.ship.admin@example.com",
        )
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.ship.admin@example.com",
            full_name="Owner Ship Admin",
        )
        self.order = Order.objects.create(
            tenant=self.tenant,
            customer=self.customer,
            number="9001",
            customer_name="Cliente Ship Admin",
            customer_email="cliente.ship.admin@example.com",
        )

    def test_admin_shipping_list_renders_tenant_orders(self):
        response = self.client.get(
            reverse("shipping:admin-shipping-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "#9001")
        self.assertContains(response, "Sem shipment")
        self.assertContains(response, "Marcar enviado")

    def test_admin_shipping_list_renders_shipment_history_summary(self):
        shipment = Shipment.objects.create(tenant=self.tenant, order=self.order, status=Shipment.Status.SENT)
        ShipmentStatusHistory.objects.create(
            shipment=shipment,
            tenant=self.tenant,
            event_type="shipment_sent",
            title="Shipment enviado",
            source_label="Shipping Commands",
        )

        response = self.client.get(
            reverse("shipping:admin-shipping-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Histórico")
        self.assertContains(response, "Shipment enviado")

    def test_admin_shipping_list_uses_normalized_tracking_status_label(self):
        Shipment.objects.create(tenant=self.tenant, order=self.order, status=Shipment.Status.SENT)

        response = self.client.get(
            reverse("shipping:admin-shipping-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Em trânsito")

    def test_admin_shipping_mark_sent_creates_shipment_and_customer_log(self):
        response = self.client.post(
            reverse("shipping:admin-shipping-action", kwargs={"order_number": "9001"}),
            data={"action_type": "mark_sent", "tracking_code": "BR9001", "carrier_name": "Correios"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/?result=shipment-sent", fetch_redirect_response=False)
        shipment = Shipment.objects.get(order=self.order)
        self.assertEqual(shipment.status, Shipment.Status.SENT)
        self.assertEqual(shipment.tracking_code, "BR9001")
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="shipment.sent",
                intent_key="customer.shipment.sent",
            ).exists()
        )

    def test_admin_shipping_mark_delivered_creates_customer_and_owner_logs(self):
        Shipment.objects.create(tenant=self.tenant, order=self.order, status=Shipment.Status.SENT)

        response = self.client.post(
            reverse("shipping:admin-shipping-action", kwargs={"order_number": "9001"}),
            data={"action_type": "mark_delivered"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/?result=shipment-delivered", fetch_redirect_response=False)
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="shipment.delivered",
                intent_key="customer.shipment.delivered",
            ).exists()
        )
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="shipment.delivered",
                intent_key="owner.shipment.delivered",
                recipient_id=str(self.owner.id),
            ).exists()
        )

    def test_admin_shipping_action_does_not_cross_tenants(self):
        other_tenant = Tenant.objects.create(name="Outra Ship", slug="outra-ship", subdomain="outra-ship")

        response = self.client.post(
            reverse("shipping:admin-shipping-action", kwargs={"order_number": "9001"}),
            data={"action_type": "mark_sent"},
            HTTP_HOST=f"{other_tenant.subdomain}.hubx.market",
        )

        self.assertRedirects(response, "/ops/shipping/?result=shipment-order-not-found", fetch_redirect_response=False)
        self.assertEqual(Shipment.objects.filter(tenant=other_tenant).count(), 0)
