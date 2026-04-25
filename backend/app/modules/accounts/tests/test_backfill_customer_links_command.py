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
        self.assertIn("profiles_skipped_ambiguous=1", output.getvalue())
        self.assertIn("orders_skipped=1", output.getvalue())
        self.assertIn("orders_skipped_ambiguous=1", output.getvalue())

    def test_backfill_can_scope_to_single_tenant(self):
        secondary_tenant = Tenant.objects.create(
            name="Hubx Backfill Secondary",
            slug="hubx-backfill-secondary",
            subdomain="hubx-backfill-secondary",
        )
        primary_customer = Customer.objects.create(
            tenant=self.tenant,
            slug="primary-scoped",
            reference="#BF-4A",
            full_name="Primary Scoped",
            email="scoped@hubx.market",
        )
        secondary_customer = Customer.objects.create(
            tenant=secondary_tenant,
            slug="secondary-scoped",
            reference="#BF-4B",
            full_name="Secondary Scoped",
            email="scoped@hubx.market",
        )
        primary_profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="scoped@hubx.market",
            first_name="Primary",
        )
        secondary_profile = AccountProfile.objects.create(
            tenant=secondary_tenant,
            email="scoped@hubx.market",
            first_name="Secondary",
        )
        primary_order = Order.objects.create(
            tenant=self.tenant,
            number="5020",
            customer_email="scoped@hubx.market",
            customer_name="Primary Scoped",
        )
        secondary_order = Order.objects.create(
            tenant=secondary_tenant,
            number="5021",
            customer_email="scoped@hubx.market",
            customer_name="Secondary Scoped",
        )
        AccountProfile.objects.filter(pk__in=[primary_profile.pk, secondary_profile.pk]).update(customer=None)
        Order.objects.filter(pk__in=[primary_order.pk, secondary_order.pk]).update(customer=None)

        output = StringIO()
        call_command("backfill_customer_links", tenant_id=str(self.tenant.id), stdout=output)

        primary_profile.refresh_from_db()
        secondary_profile.refresh_from_db()
        primary_order.refresh_from_db()
        secondary_order.refresh_from_db()

        self.assertEqual(primary_profile.customer, primary_customer)
        self.assertIsNone(secondary_profile.customer)
        self.assertEqual(primary_order.customer, primary_customer)
        self.assertIsNone(secondary_order.customer)
        self.assertIn(f"tenant_id={self.tenant.id}", output.getvalue())
        self.assertIn("order_email_fallback_remaining=0", output.getvalue())
        self.assertIsNotNone(secondary_customer)

    def test_backfill_can_run_only_for_orders(self):
        customer = Customer.objects.create(
            tenant=self.tenant,
            slug="orders-only",
            reference="#BF-5",
            full_name="Orders Only",
            email="orders.only@hubx.market",
        )
        profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="orders.only@hubx.market",
            first_name="Orders",
        )
        order = Order.objects.create(
            tenant=self.tenant,
            number="5030",
            customer_email="orders.only@hubx.market",
            customer_name="Orders Only",
        )
        AccountProfile.objects.filter(pk=profile.pk).update(customer=None)
        Order.objects.filter(pk=order.pk).update(customer=None)

        output = StringIO()
        call_command("backfill_customer_links", tenant_id=str(self.tenant.id), only="orders", stdout=output)

        profile.refresh_from_db()
        order.refresh_from_db()

        self.assertIsNone(profile.customer)
        self.assertEqual(order.customer, customer)
        self.assertIn("only=orders", output.getvalue())
        self.assertIn("profiles_linked=0", output.getvalue())
        self.assertIn("orders_linked=1", output.getvalue())

    def test_backfill_reports_skip_reasons(self):
        missing_email_profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="",
            first_name="Missing",
        )
        no_match_profile = AccountProfile.objects.create(
            tenant=self.tenant,
            email="missing.customer@hubx.market",
            first_name="No",
        )
        missing_email_order = Order.objects.create(
            tenant=self.tenant,
            number="5040",
            customer_email="",
            customer_name="Missing Email",
        )
        no_match_order = Order.objects.create(
            tenant=self.tenant,
            number="5041",
            customer_email="missing.customer@hubx.market",
            customer_name="No Match",
        )
        AccountProfile.objects.filter(pk__in=[missing_email_profile.pk, no_match_profile.pk]).update(customer=None)
        Order.objects.filter(pk__in=[missing_email_order.pk, no_match_order.pk]).update(customer=None)

        output = StringIO()
        call_command("backfill_customer_links", tenant_id=str(self.tenant.id), stdout=output)

        payload = output.getvalue()
        self.assertIn("profiles_skipped=2", payload)
        self.assertIn("profiles_skipped_missing_email=1", payload)
        self.assertIn("profiles_skipped_no_match=1", payload)
        self.assertIn("orders_skipped=2", payload)
        self.assertIn("orders_skipped_missing_email=1", payload)
        self.assertIn("orders_skipped_no_match=1", payload)
