from django.test import TestCase

from app.modules.accounts.application.admin_owner_commands import admin_owner_commands
from app.modules.accounts.application.admin_owner_queries import admin_owner_queries
from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
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

    def test_creates_owner_with_role_and_audit_event(self):
        result = admin_owner_commands.create_owner(
            tenant_id=self.tenant.id,
            actor_role="owner",
            actor_label="admin@hubx.market",
            payload={
                "email": "marketing@hubx.market",
                "full_name": "Marketing",
                "role": "marketing",
                "is_active": "1",
                "receives_notifications": "1",
            },
        )

        self.assertEqual(result["result"], "owner-created")
        owner = OwnerUser.objects.get(email="marketing@hubx.market")
        self.assertEqual(owner.tenant, self.tenant)
        self.assertEqual(owner.role, "marketing")
        log = AuditLog.objects.get(action="owner.created")
        self.assertEqual(log.tenant, self.tenant)
        self.assertEqual(log.actor_label, "admin@hubx.market")
        self.assertEqual(log.metadata["role"], "marketing")

    def test_rejects_duplicate_owner_email_per_tenant(self):
        OwnerUser.objects.create(tenant=self.tenant, email="owner@hubx.market")

        result = admin_owner_commands.create_owner(
            tenant_id=self.tenant.id,
            actor_role="owner",
            payload={"email": "OWNER@hubx.market", "role": "admin", "is_active": "1"},
        )

        self.assertEqual(result["result"], "owner-invalid")
        self.assertIn("email", result["errors"])

    def test_updates_owner_access_tenant_scoped(self):
        owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="editor@hubx.market",
            role="content_editor",
            is_active=True,
            receives_notifications=True,
        )

        result = admin_owner_commands.update_owner_access(
            tenant_id=self.tenant.id,
            owner_id=owner.id,
            actor_role="admin",
            payload={
                "email": "editor.updated@hubx.market",
                "full_name": "Editor Atualizado",
                "role": "support",
                "receives_notifications": "0",
            },
        )

        owner.refresh_from_db()
        self.assertEqual(result["result"], "owner-updated")
        self.assertEqual(owner.email, "editor.updated@hubx.market")
        self.assertEqual(owner.full_name, "Editor Atualizado")
        self.assertEqual(owner.role, "support")
        self.assertFalse(owner.is_active)
        self.assertFalse(owner.receives_notifications)
        self.assertEqual(AuditLog.objects.get(action="owner.access_updated").entity_id, str(owner.id))

    def test_blocks_owner_management_without_permission(self):
        result = admin_owner_commands.create_owner(
            tenant_id=self.tenant.id,
            actor_role="marketing",
            payload={"email": "new@hubx.market", "role": "support"},
        )

        self.assertEqual(result["result"], "owner-permission-denied")
        self.assertFalse(OwnerUser.objects.filter(email="new@hubx.market").exists())
