from __future__ import annotations

from django.contrib.auth.hashers import check_password
from django.test import TestCase

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.models import ApiKey
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class ApiKeyModelContractTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="API Key Tenant", slug="api-key-tenant", subdomain="api-key-tenant")
        self.other_tenant = Tenant.objects.create(
            name="Other API Key Tenant",
            slug="other-api-key-tenant",
            subdomain="other-api-key-tenant",
        )

    def test_create_key_persists_hash_and_returns_secret_once(self):
        result = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="ERP integration",
            scopes=["read:orders", "write:products"],
            actor_label="owner@hubx.market",
        )

        self.assertEqual(result["result"], "api-key-created")
        api_key = ApiKey.objects.get(pk=result["api_key"]["id"])
        self.assertEqual(api_key.tenant, self.tenant)
        self.assertEqual(api_key.status, ApiKey.Status.ACTIVE)
        self.assertEqual(api_key.scopes, ["read:orders", "write:products"])
        self.assertNotEqual(api_key.key_hash, result["secret"])
        self.assertTrue(check_password(result["secret"], api_key.key_hash))
        self.assertEqual(result["api_key"]["prefix"], api_key.prefix)
        self.assertTrue(result["secret"].startswith(api_key.prefix))

    def test_create_key_requires_tenant_and_name(self):
        missing_tenant = api_key_commands.create_key(tenant_id=None, name="ERP")
        missing_name = api_key_commands.create_key(tenant_id=self.tenant.id, name="")

        self.assertEqual(missing_tenant["result"], "api-key-tenant-required")
        self.assertEqual(missing_name["result"], "api-key-invalid")

    def test_create_key_records_audit_without_secret_or_hash(self):
        result = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="ERP integration",
            actor_label="owner@hubx.market",
        )

        audit_log = AuditLog.objects.get(tenant=self.tenant, module="api_keys", action="api_key.created")
        self.assertEqual(audit_log.entity_id, str(result["api_key"]["id"]))
        self.assertIn("prefix", audit_log.metadata)
        self.assertNotIn("secret", audit_log.metadata)
        self.assertNotIn("key_hash", audit_log.metadata)
        self.assertNotIn(result["secret"], str(audit_log.metadata))

    def test_revoke_key_is_tenant_scoped_and_keeps_history(self):
        result = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP integration")
        api_key_id = result["api_key"]["id"]

        cross_tenant = api_key_commands.revoke_key(
            tenant_id=self.other_tenant.id,
            key_id=api_key_id,
            actor_label="other@hubx.market",
        )
        revoked = api_key_commands.revoke_key(
            tenant_id=self.tenant.id,
            key_id=api_key_id,
            actor_label="owner@hubx.market",
        )

        self.assertEqual(cross_tenant["result"], "api-key-not-found")
        self.assertEqual(revoked["result"], "api-key-revoked")
        api_key = ApiKey.objects.get(pk=api_key_id)
        self.assertEqual(api_key.status, ApiKey.Status.REVOKED)
        self.assertIsNotNone(api_key.revoked_at)
        self.assertEqual(ApiKey.objects.filter(pk=api_key_id).count(), 1)

    def test_revoke_key_records_audit_event(self):
        result = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP integration")

        api_key_commands.revoke_key(
            tenant_id=self.tenant.id,
            key_id=result["api_key"]["id"],
            actor_label="owner@hubx.market",
        )

        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="api_keys",
                action="api_key.revoked",
                entity_id=str(result["api_key"]["id"]),
            ).exists()
        )
