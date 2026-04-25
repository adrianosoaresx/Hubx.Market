from datetime import timedelta
from io import StringIO

from django.core.management import CommandError, call_command
from django.test import TestCase
from django.utils import timezone

from app.modules.orders.models import Order
from app.modules.shipping.models import Shipment, ShipmentStatusHistory
from app.modules.tenants.models import Tenant


class PruneShipmentHistoryCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Prune", slug="loja-prune", subdomain="loja-prune")
        self.other_tenant = Tenant.objects.create(name="Outra Prune", slug="outra-prune", subdomain="outra-prune")
        self.order = Order.objects.create(tenant=self.tenant, number="9971", customer_email="prune@example.com")
        self.other_order = Order.objects.create(tenant=self.other_tenant, number="9972", customer_email="other-prune@example.com")
        self.shipment = Shipment.objects.create(tenant=self.tenant, order=self.order, status=Shipment.Status.SENT)
        self.other_shipment = Shipment.objects.create(tenant=self.other_tenant, order=self.other_order, status=Shipment.Status.SENT)
        self.old_history = self._history(self.shipment, "shipment_tracking_synced")
        self.recent_history = self._history(self.shipment, "shipment_sent")
        self.other_old_history = self._history(self.other_shipment, "shipment_tracking_synced")
        old_time = timezone.now() - timedelta(days=120)
        ShipmentStatusHistory.objects.filter(id__in=[self.old_history.id, self.other_old_history.id]).update(created_at=old_time)

    def test_prune_shipment_history_dry_run_does_not_delete(self):
        output = StringIO()

        call_command("prune_shipment_history", "--days=90", "--dry-run", stdout=output)

        self.assertIn("shipment_history_candidates=2", output.getvalue())
        self.assertEqual(ShipmentStatusHistory.objects.count(), 3)

    def test_prune_shipment_history_respects_tenant_scope(self):
        output = StringIO()

        call_command("prune_shipment_history", f"--tenant-id={self.tenant.id}", "--days=90", stdout=output)

        self.assertIn("deleted=1", output.getvalue())
        self.assertFalse(ShipmentStatusHistory.objects.filter(id=self.old_history.id).exists())
        self.assertTrue(ShipmentStatusHistory.objects.filter(id=self.other_old_history.id).exists())
        self.assertTrue(ShipmentStatusHistory.objects.filter(id=self.recent_history.id).exists())

    def test_prune_shipment_history_rejects_aggressive_window(self):
        with self.assertRaises(CommandError):
            call_command("prune_shipment_history", "--days=7")

    def _history(self, shipment, event_type):
        return ShipmentStatusHistory.objects.create(
            tenant=shipment.tenant,
            shipment=shipment,
            event_type=event_type,
            title=event_type,
        )
