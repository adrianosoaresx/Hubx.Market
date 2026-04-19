from django.test import TestCase

from app.modules.accounts.models import AccountProfile
from app.modules.customers.models import Customer
from app.modules.tenants.models import Tenant


class AccountReadinessModelTests(TestCase):
    def test_account_profile_persists_identity_and_preferences(self):
        tenant = Tenant.objects.create(
            name="Hubx Demo Accounts",
            slug="hubx-demo-accounts",
            subdomain="hubx-demo-accounts",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="ana-souza",
            reference="#8821",
            full_name="Ana Souza",
            email="ana@hubx.market",
        )

        profile = AccountProfile.objects.create(
            tenant=tenant,
            customer=customer,
            email="ana@hubx.market",
            first_name="Ana",
            last_name="Souza",
            phone="(11) 99999-0000",
            newsletter_opt_in=True,
            order_updates_opt_in=True,
        )

        stored = AccountProfile.objects.get(pk=profile.pk)

        self.assertEqual(stored.tenant, tenant)
        self.assertEqual(stored.customer, customer)
        self.assertEqual(stored.email, "ana@hubx.market")
        self.assertTrue(stored.newsletter_opt_in)
        self.assertTrue(stored.order_updates_opt_in)

    def test_account_profile_auto_populates_customer_when_match_is_unambiguous(self):
        tenant = Tenant.objects.create(
            name="Hubx Auto Link Accounts",
            slug="hubx-auto-link-accounts",
            subdomain="hubx-auto-link-accounts",
        )
        customer = Customer.objects.create(
            tenant=tenant,
            slug="ana-auto-link",
            reference="#A-1",
            full_name="Ana Auto Link",
            email="ana.auto@hubx.market",
        )

        profile = AccountProfile.objects.create(
            tenant=tenant,
            email="ana.auto@hubx.market",
            first_name="Ana",
        )

        profile.refresh_from_db()
        self.assertEqual(profile.customer, customer)

    def test_account_profile_auto_populate_is_noop_when_match_is_ambiguous(self):
        tenant = Tenant.objects.create(
            name="Hubx Ambiguous Accounts",
            slug="hubx-ambiguous-accounts",
            subdomain="hubx-ambiguous-accounts",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="ana-ambiguous-a",
            reference="#A-2A",
            full_name="Ana Ambiguous",
            email="ana.ambiguous@hubx.market",
        )
        Customer.objects.create(
            tenant=tenant,
            slug="ana-ambiguous-b",
            reference="#A-2B",
            full_name="Ana Ambiguous 2",
            email="ANA.AMBIGUOUS@hubx.market",
        )

        profile = AccountProfile.objects.create(
            tenant=tenant,
            email="ana.ambiguous@hubx.market",
            first_name="Ana",
        )

        profile.refresh_from_db()
        self.assertIsNone(profile.customer)
