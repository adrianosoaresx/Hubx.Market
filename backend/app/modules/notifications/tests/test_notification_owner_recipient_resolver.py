from django.test import TestCase

from app.modules.accounts.models import OwnerUser
from app.modules.notifications.application.notification_owner_recipient_resolver import (
    resolve_owner_recipient_targets,
)
from app.modules.tenants.models import Tenant


class NotificationOwnerRecipientResolverTests(TestCase):
    def test_resolves_active_owner_targets_for_tenant(self):
        tenant = Tenant.objects.create(name="Loja Owner", slug="loja-owner", subdomain="loja-owner")
        other_tenant = Tenant.objects.create(name="Outra Owner", slug="outra-owner", subdomain="outra-owner")
        active_owner = OwnerUser.objects.create(
            tenant=tenant,
            email="owner@hubx.market",
            full_name="Owner Hubx",
        )
        OwnerUser.objects.create(
            tenant=tenant,
            email="inactive@hubx.market",
            full_name="Inactive",
            is_active=False,
        )
        OwnerUser.objects.create(
            tenant=tenant,
            email="muted@hubx.market",
            full_name="Muted",
            receives_notifications=False,
        )
        OwnerUser.objects.create(
            tenant=other_tenant,
            email="other@hubx.market",
            full_name="Other",
        )

        targets = resolve_owner_recipient_targets(tenant_id=tenant.id)

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].recipient_type, "owner_user")
        self.assertEqual(targets[0].recipient_id, str(active_owner.id))
        self.assertEqual(targets[0].email, "owner@hubx.market")
        self.assertEqual(targets[0].display_name, "Owner Hubx")

    def test_returns_empty_without_tenant(self):
        self.assertEqual(resolve_owner_recipient_targets(tenant_id=""), [])
