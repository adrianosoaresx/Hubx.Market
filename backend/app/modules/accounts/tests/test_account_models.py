from django.test import TestCase

from app.modules.accounts.models import AccountProfile
from app.modules.tenants.models import Tenant


class AccountReadinessModelTests(TestCase):
    def test_account_profile_persists_identity_and_preferences(self):
        tenant = Tenant.objects.create(
            name="Hubx Demo Accounts",
            slug="hubx-demo-accounts",
            subdomain="hubx-demo-accounts",
        )

        profile = AccountProfile.objects.create(
            tenant=tenant,
            email="ana@hubx.market",
            first_name="Ana",
            last_name="Souza",
            phone="(11) 99999-0000",
            newsletter_opt_in=True,
            order_updates_opt_in=True,
        )

        stored = AccountProfile.objects.get(pk=profile.pk)

        self.assertEqual(stored.tenant, tenant)
        self.assertEqual(stored.email, "ana@hubx.market")
        self.assertTrue(stored.newsletter_opt_in)
        self.assertTrue(stored.order_updates_opt_in)
