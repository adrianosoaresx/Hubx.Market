from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.orders.models import Order
from app.modules.shipping.models import Shipment
from app.modules.tenants.models import Tenant


class SyncShipmentsTrackingCommandTests(TestCase):
    def test_command_syncs_non_terminal_shipments_with_optional_tenant_scope(self):
        tenant = Tenant.objects.create(name="Loja Cmd Tracking", slug="loja-cmd-tracking", subdomain="loja-cmd-tracking")
        other_tenant = Tenant.objects.create(name="Outra Cmd Tracking", slug="outra-cmd-tracking", subdomain="outra-cmd-tracking")
        order = Order.objects.create(tenant=tenant, number="9931", customer_email="cmd-tracking@example.com")
        other_order = Order.objects.create(tenant=other_tenant, number="9932", customer_email="other-cmd-tracking@example.com")
        Shipment.objects.create(
            tenant=tenant,
            order=order,
            status=Shipment.Status.SENT,
            tracking_code="BR9931",
        )
        Shipment.objects.create(
            tenant=other_tenant,
            order=other_order,
            status=Shipment.Status.SENT,
            tracking_code="BR9932",
        )
        stdout = StringIO()

        call_command("sync_shipments_tracking", tenant_id=str(tenant.id), stdout=stdout)

        output = stdout.getvalue()
        self.assertIn("Tracking sync concluído", output)
        self.assertIn("processed=1", output)
        self.assertIn("tracking-sync-unchanged=1", output)
