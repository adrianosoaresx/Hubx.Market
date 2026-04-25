from django.test import TestCase

from app.modules.accounts.application.admin_owner_commands import admin_owner_commands
from app.modules.accounts.application.admin_owner_queries import admin_owner_queries
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


class AdminOwnerServiceTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Owner UI", slug="loja-owner-ui", subdomain="loja-owner-ui")
        self.other_tenant = Tenant.objects.create(name="Outra Owner UI", slug="outra-owner-ui", subdomain="outra-owner-ui")

    def test_lists_owners_for_tenant_only(self):
        owner = OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market", full_name="Owner")
        OwnerUser.objects.create(tenant=self.other_tenant, email="other@hubx.market", full_name="Other")

        owners = admin_owner_queries.list_owners(tenant_id=self.tenant.id)

        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0].id, owner.id)
        self.assertEqual(owners[0].email, "owner@hubx.market")

    def test_toggles_owner_notification_preference_tenant_scoped(self):
        owner = OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market", receives_notifications=True)

        result = admin_owner_commands.set_notification_preference(
            tenant_id=self.tenant.id,
            owner_id=owner.id,
            receives_notifications=False,
        )

        owner.refresh_from_db()
        self.assertEqual(result, "owner-notifications-disabled")
        self.assertFalse(owner.receives_notifications)
        self.assertEqual(
            admin_owner_commands.set_notification_preference(
                tenant_id=self.other_tenant.id,
                owner_id=owner.id,
                receives_notifications=True,
            ),
            "owner-not-found",
        )
