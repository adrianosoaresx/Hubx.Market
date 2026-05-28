from io import StringIO

from django.contrib.auth.models import User
from django.core.management import call_command
from django.test import TestCase, override_settings

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.tenants.application.platform_tenant_admin_commands import platform_tenant_admin_commands
from app.modules.tenants.models import Tenant


@override_settings(HUBX_MARKET_RESERVED_SUBDOMAINS=["www", "app", "api", "docs", "cdn", "admin"])
class PlatformTenantAdminCommandTests(TestCase):
    def test_create_tenant_persists_minimal_tenant_and_platform_audit_log(self):
        result = platform_tenant_admin_commands.create_tenant(
            payload={
                "name": "Nova Loja",
                "slug": "nova-loja",
                "subdomain": "nova-loja",
                "custom_domain": "nova.example.com",
            },
            actor_label="platform@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-created")
        tenant = Tenant.objects.get(slug="nova-loja")
        self.assertEqual(tenant.subdomain, "nova-loja")
        self.assertEqual(tenant.custom_domain, "nova.example.com")
        audit_log = AuditLog.objects.get(action="platform.tenant.created")
        self.assertIsNone(audit_log.tenant)
        self.assertEqual(audit_log.module, "tenants")
        self.assertEqual(audit_log.entity_id, str(tenant.id))
        self.assertEqual(audit_log.metadata["tenant_slug"], "nova-loja")

    def test_create_tenant_rejects_role_without_manage_permission(self):
        result = platform_tenant_admin_commands.create_tenant(
            payload={"name": "Bloqueada", "slug": "bloqueada", "subdomain": "bloqueada"},
            actor_role="support",
        )

        self.assertEqual(result["result"], "platform-tenant-create-permission-denied")
        self.assertFalse(Tenant.objects.filter(slug="bloqueada").exists())

    def test_create_tenant_rejects_duplicate_slug_and_subdomain(self):
        Tenant.objects.create(name="Existente", slug="existente", subdomain="existente")

        result = platform_tenant_admin_commands.create_tenant(
            payload={"name": "Existente 2", "slug": "existente", "subdomain": "existente"},
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-create-invalid")
        self.assertIn("slug", result["errors"])
        self.assertIn("subdomain", result["errors"])
        self.assertEqual(Tenant.objects.filter(slug="existente").count(), 1)

    def test_create_tenant_rejects_reserved_subdomain(self):
        result = platform_tenant_admin_commands.create_tenant(
            payload={"name": "Admin Store", "slug": "admin-store", "subdomain": "admin"},
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-create-invalid")
        self.assertEqual(result["errors"]["subdomain"], "Este subdomínio é reservado para a plataforma.")
        self.assertFalse(Tenant.objects.filter(slug="admin-store").exists())

    def test_management_command_creates_tenant(self):
        output = StringIO()
        call_command(
            "platform_tenant_create",
            name="CLI Loja",
            slug="cli-loja",
            subdomain="cli-loja",
            actor_label="cli@hubx.market",
            actor_role="owner",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-created", value)
        self.assertIn("slug=cli-loja", value)
        self.assertTrue(Tenant.objects.filter(slug="cli-loja").exists())

    def test_update_tenant_state_deactivates_and_records_platform_audit_log(self):
        tenant = Tenant.objects.create(name="State Loja", slug="state-loja", subdomain="state-loja")

        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug=tenant.slug,
            action="deactivate",
            actor_label="platform@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-state-updated")
        tenant.refresh_from_db()
        self.assertFalse(tenant.is_active)
        audit_log = AuditLog.objects.get(action="platform.tenant.deactivate")
        self.assertIsNone(audit_log.tenant)
        self.assertEqual(audit_log.entity_id, str(tenant.id))
        self.assertTrue(audit_log.metadata["previous_is_active"])
        self.assertFalse(audit_log.metadata["is_active"])

    def test_update_tenant_state_toggles_maintenance_without_changing_active(self):
        tenant = Tenant.objects.create(name="Maintenance Loja", slug="maintenance-loja", subdomain="maintenance-loja")

        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug=tenant.slug,
            action="maintenance-on",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-state-updated")
        tenant.refresh_from_db()
        self.assertTrue(tenant.is_active)
        self.assertTrue(tenant.maintenance_mode)

    def test_update_tenant_state_rejects_role_without_manage_permission(self):
        tenant = Tenant.objects.create(name="Blocked State", slug="blocked-state", subdomain="blocked-state")

        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug=tenant.slug,
            action="deactivate",
            actor_role="support",
        )

        self.assertEqual(result["result"], "platform-tenant-state-permission-denied")
        tenant.refresh_from_db()
        self.assertTrue(tenant.is_active)

    def test_update_tenant_state_rejects_invalid_action(self):
        tenant = Tenant.objects.create(name="Invalid State", slug="invalid-state", subdomain="invalid-state")

        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug=tenant.slug,
            action="delete",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-state-invalid-action")
        tenant.refresh_from_db()
        self.assertTrue(tenant.is_active)

    def test_update_tenant_state_returns_not_found_for_unknown_slug(self):
        result = platform_tenant_admin_commands.update_tenant_state(
            tenant_slug="missing-state",
            action="activate",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-state-not-found")

    def test_management_command_updates_tenant_state(self):
        Tenant.objects.create(name="CLI State", slug="cli-state", subdomain="cli-state")
        output = StringIO()
        call_command(
            "platform_tenant_state",
            tenant_slug="cli-state",
            action="maintenance-on",
            actor_label="cli@hubx.market",
            actor_role="owner",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-state-updated", value)
        self.assertIn("maintenance=True", value)
        self.assertTrue(Tenant.objects.get(slug="cli-state").maintenance_mode)

    def test_update_custom_domain_normalizes_and_records_platform_audit_log(self):
        tenant = Tenant.objects.create(name="Domain Loja", slug="domain-loja", subdomain="domain-loja")

        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=tenant.slug,
            custom_domain="HTTPS://Loja.Example.COM/path?utm=1",
            actor_label="platform@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-custom-domain-updated")
        tenant.refresh_from_db()
        self.assertEqual(tenant.custom_domain, "loja.example.com")
        audit_log = AuditLog.objects.get(action="platform.tenant.custom_domain_updated")
        self.assertIsNone(audit_log.tenant)
        self.assertEqual(audit_log.entity_id, str(tenant.id))
        self.assertEqual(audit_log.metadata["tenant_slug"], "domain-loja")
        self.assertEqual(audit_log.metadata["previous_custom_domain"], "")
        self.assertEqual(audit_log.metadata["custom_domain"], "loja.example.com")
        self.assertTrue(audit_log.metadata["custom_domain_configured"])

    def test_update_custom_domain_can_clear_existing_domain(self):
        tenant = Tenant.objects.create(
            name="Clear Domain",
            slug="clear-domain",
            subdomain="clear-domain",
            custom_domain="clear.example.com",
        )

        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=tenant.slug,
            custom_domain="",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-custom-domain-updated")
        self.assertEqual(result["previous_custom_domain"], "clear.example.com")
        tenant.refresh_from_db()
        self.assertIsNone(tenant.custom_domain)

    def test_update_custom_domain_rejects_duplicate_case_insensitive_domain(self):
        Tenant.objects.create(
            name="Original Domain",
            slug="original-domain",
            subdomain="original-domain",
            custom_domain="loja.example.com",
        )
        tenant = Tenant.objects.create(name="Duplicate Domain", slug="duplicate-domain", subdomain="duplicate-domain")

        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=tenant.slug,
            custom_domain="LOJA.EXAMPLE.COM",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-custom-domain-invalid")
        self.assertEqual(result["errors"]["custom_domain"], "Já existe uma loja com este domínio customizado.")
        tenant.refresh_from_db()
        self.assertIsNone(tenant.custom_domain)

    def test_update_custom_domain_rejects_invalid_domain(self):
        tenant = Tenant.objects.create(name="Invalid Domain", slug="invalid-domain", subdomain="invalid-domain")

        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=tenant.slug,
            custom_domain="bad_domain",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-custom-domain-invalid")
        self.assertIn("custom_domain", result["errors"])
        tenant.refresh_from_db()
        self.assertIsNone(tenant.custom_domain)

    def test_update_custom_domain_rejects_role_without_manage_permission(self):
        tenant = Tenant.objects.create(name="Blocked Domain", slug="blocked-domain", subdomain="blocked-domain")

        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug=tenant.slug,
            custom_domain="blocked.example.com",
            actor_role="support",
        )

        self.assertEqual(result["result"], "platform-tenant-custom-domain-permission-denied")
        tenant.refresh_from_db()
        self.assertIsNone(tenant.custom_domain)

    def test_update_custom_domain_returns_not_found_for_unknown_slug(self):
        result = platform_tenant_admin_commands.update_custom_domain(
            tenant_slug="missing-domain",
            custom_domain="missing.example.com",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-custom-domain-not-found")

    def test_management_command_updates_custom_domain(self):
        Tenant.objects.create(name="CLI Domain", slug="cli-domain", subdomain="cli-domain")
        output = StringIO()
        call_command(
            "platform_tenant_custom_domain",
            tenant_slug="cli-domain",
            custom_domain="https://CLI.Example.COM:443/path",
            actor_label="cli@hubx.market",
            actor_role="owner",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-custom-domain-updated", value)
        self.assertIn("custom_domain=cli.example.com", value)
        self.assertEqual(Tenant.objects.get(slug="cli-domain").custom_domain, "cli.example.com")

    def test_bootstrap_owner_provisions_owner_user_and_platform_audit_log(self):
        tenant = Tenant.objects.create(name="Bootstrap Loja", slug="bootstrap-loja", subdomain="bootstrap-loja")

        result = platform_tenant_admin_commands.bootstrap_owner(
            tenant_slug=tenant.slug,
            payload={
                "owner_email": "first.owner@hubx.market",
                "owner_name": "First Owner",
                "owner_role": "owner",
            },
            actor_label="platform@hubx.market",
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-owner-bootstrapped")
        owner = OwnerUser.objects.get(tenant=tenant, email="first.owner@hubx.market")
        user = User.objects.get(email="first.owner@hubx.market")
        self.assertEqual(owner.role, "owner")
        self.assertFalse(user.has_usable_password())
        self.assertTrue(
            AuditLog.objects.filter(
                tenant__isnull=True,
                action="platform.tenant.owner_bootstrapped",
                entity_id=str(owner.id),
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=tenant,
                action="owner.initial_provisioned",
                entity_id=str(owner.id),
            ).exists()
        )

    def test_bootstrap_owner_rejects_when_tenant_already_has_active_owner(self):
        tenant = Tenant.objects.create(name="Owned Loja", slug="owned-loja", subdomain="owned-loja")
        OwnerUser.objects.create(tenant=tenant, email="existing@hubx.market", role="owner", is_active=True)

        result = platform_tenant_admin_commands.bootstrap_owner(
            tenant_slug=tenant.slug,
            payload={"owner_email": "new.owner@hubx.market", "owner_role": "owner"},
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-owner-bootstrap-already-has-owner")
        self.assertFalse(OwnerUser.objects.filter(tenant=tenant, email="new.owner@hubx.market").exists())

    def test_bootstrap_owner_rejects_role_without_manage_permission(self):
        tenant = Tenant.objects.create(name="Blocked Bootstrap", slug="blocked-bootstrap", subdomain="blocked-bootstrap")

        result = platform_tenant_admin_commands.bootstrap_owner(
            tenant_slug=tenant.slug,
            payload={"owner_email": "blocked.owner@hubx.market", "owner_role": "owner"},
            actor_role="support",
        )

        self.assertEqual(result["result"], "platform-tenant-owner-bootstrap-permission-denied")
        self.assertFalse(OwnerUser.objects.filter(tenant=tenant, email="blocked.owner@hubx.market").exists())

    def test_bootstrap_owner_returns_not_found_for_inactive_tenant(self):
        tenant = Tenant.objects.create(
            name="Inactive Bootstrap",
            slug="inactive-bootstrap",
            subdomain="inactive-bootstrap",
            is_active=False,
        )

        result = platform_tenant_admin_commands.bootstrap_owner(
            tenant_slug=tenant.slug,
            payload={"owner_email": "inactive.owner@hubx.market", "owner_role": "owner"},
            actor_role="owner",
        )

        self.assertEqual(result["result"], "platform-tenant-owner-bootstrap-not-found")

    def test_management_command_bootstraps_owner(self):
        Tenant.objects.create(name="CLI Bootstrap", slug="cli-bootstrap", subdomain="cli-bootstrap")
        output = StringIO()
        call_command(
            "platform_tenant_owner_bootstrap",
            tenant_slug="cli-bootstrap",
            owner_email="cli.bootstrap@hubx.market",
            owner_name="CLI Bootstrap",
            actor_label="cli@hubx.market",
            actor_role="owner",
            stdout=output,
        )

        value = output.getvalue()
        self.assertIn("result=platform-tenant-owner-bootstrapped", value)
        self.assertIn("owner_email=cli.bootstrap@hubx.market", value)
        self.assertTrue(OwnerUser.objects.filter(email="cli.bootstrap@hubx.market").exists())
