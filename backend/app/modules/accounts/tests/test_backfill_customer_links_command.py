from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from app.modules.accounts.models import AccountProfile
from app.modules.customers.models import Customer
from app.modules.orders.models import Order
from app.modules.tenants.models import Tenant


class BackfillCustomerLinksCommandTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(
            name="Hubx Backfill Demo",
            slug="hubx-backfill-demo",
            subdomain="hubx-backfill-demo",
        )

    def test_backfill_links_profiles_and_orders_when_match_is_unambiguous(self):
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ana-backfill",
            reference="#BF-1",
            full_name="Ana Backfill",
            email="ana.backfill@hubx.market",
            phone="(11) 98888-0000",
        )
        profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="ana.backfill@hubx.market",
            first_name="Ana",
            last_name="Backfill",
        )
        order = Order.objects.create(
            tenant=self.tenant,
            number="5010",
            customer_email="ana.backfill@hubx.market",
            customer_name="Ana Backfill",
        )
        AccountProfile.objects.filter(pk=profile.pk).update(customer=None)
        Order.objects.filter(pk=order.pk).update(customer=None)

        output = StringIO()
        call_command("backfill_customer_links", stdout=output)

        profile.refresh_from_db()
        order.refresh_from_db()

        self.assertEqual(profile.customer, customer)
        self.assertEqual(order.customer, customer)
        self.assertIn("profiles_linked=1", output.getvalue())
        self.assertIn("profiles_already_linked=0", output.getvalue())
        self.assertIn("orders_linked=1", output.getvalue())
        self.assertIn("orders_already_linked=0", output.getvalue())

    def test_backfill_dry_run_reports_matches_without_persisting(self):
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="ana-dry-run",
            reference="#BF-2",
            full_name="Ana Dry Run",
            email="ana.dryrun@hubx.market",
        )
        profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="ana.dryrun@hubx.market",
            first_name="Ana",
        )
        order = Order.objects.create(
            tenant=self.tenant,
            number="5011",
            customer_email="ana.dryrun@hubx.market",
            customer_name="Ana Dry Run",
        )
        AccountProfile.objects.filter(pk=profile.pk).update(customer=None)
        Order.objects.filter(pk=order.pk).update(customer=None)

        output = StringIO()
        call_command("backfill_customer_links", "--dry-run", stdout=output)

        profile.refresh_from_db()
        order.refresh_from_db()

        self.assertIsNone(profile.customer)
        self.assertIsNone(order.customer)
        self.assertIn("[DRY-RUN]", output.getvalue())
        self.assertIn("profiles_linked=1", output.getvalue())
        self.assertIn("orders_linked=1", output.getvalue())
        self.assertIsNotNone(customer)

    def test_backfill_skips_when_match_is_ambiguous(self):
        Customer.objects.create(
            tenant=self.tenant,
            slug="ana-ambiguous-a",
            reference="#BF-3A",
            full_name="Ana Ambiguous",
            email="ana.ambiguous@hubx.market",
        )
        Customer.objects.create(
            tenant=self.tenant,
            slug="ana-ambiguous-b",
            reference="#BF-3B",
            full_name="Ana Ambiguous Upper",
            email="ANA.AMBIGUOUS@hubx.market",
        )
        profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="ana.ambiguous@hubx.market",
            first_name="Ana",
        )
        order = Order.objects.create(
            tenant=self.tenant,
            number="5012",
            customer_email="ana.ambiguous@hubx.market",
            customer_name="Ana Ambiguous",
        )
        AccountProfile.objects.filter(pk=profile.pk).update(customer=None)
        Order.objects.filter(pk=order.pk).update(customer=None)

        output = StringIO()
        call_command("backfill_customer_links", stdout=output)

        profile.refresh_from_db()
        order.refresh_from_db()

        self.assertIsNone(profile.customer)
        self.assertIsNone(order.customer)
        self.assertIn("profiles_skipped=1", output.getvalue())
        self.assertIn("orders_skipped=1", output.getvalue())
