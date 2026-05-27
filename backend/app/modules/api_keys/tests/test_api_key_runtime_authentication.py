from __future__ import annotations

from django.test import TestCase

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.application.api_key_runtime_authentication import api_key_runtime_authentication
from app.modules.api_keys.models import ApiKey
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class ApiKeyRuntimeAuthenticationTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Tenant A", slug="tenant-a", subdomain="tenant-a")
        self.other_tenant = Tenant.objects.create(name="Tenant B", slug="tenant-b", subdomain="tenant-b")

    def test_authenticates_active_key_with_required_scope_and_updates_last_used(self):
        created = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="ERP",
            scopes=["read:orders", "write:products"],
        )

        result = api_key_runtime_authentication.authenticate(
            tenant_id=self.tenant.id,
            authorization_header=f"Bearer {created['secret']}",
            required_scope="read:orders",
        )

        self.assertTrue(result["authenticated"])
        self.assertEqual(result["result"], "api-key-authenticated")
        self.assertEqual(result["api_key"]["tenant_id"], self.tenant.id)
        self.assertEqual(result["rate_limit_key"], f"tenant:{self.tenant.id}:api_key:{created['api_key']['prefix']}")
        api_key = ApiKey.objects.get(pk=created["api_key"]["id"])
        self.assertIsNotNone(api_key.last_used_at)

    def test_rejects_missing_tenant_before_key_lookup(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")

        result = api_key_runtime_authentication.authenticate(
            tenant_id=None,
            authorization_header=f"Bearer {created['secret']}",
            required_scope="read:orders",
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["result"], "api-key-auth-tenant-required")
        self.assertEqual(AuditLog.objects.filter(action="api_key.auth_failed").count(), 0)

    def test_rejects_cross_tenant_key_without_updating_last_used(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")

        result = api_key_runtime_authentication.authenticate(
            tenant_id=self.other_tenant.id,
            authorization_header=f"Bearer {created['secret']}",
            required_scope="read:orders",
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["result"], "api-key-auth-invalid")
        api_key = ApiKey.objects.get(pk=created["api_key"]["id"])
        self.assertIsNone(api_key.last_used_at)
        audit_log = AuditLog.objects.get(tenant=self.other_tenant, action="api_key.auth_failed")
        self.assertEqual(audit_log.metadata["reason"], "not-found")
        self.assertNotIn("secret", str(audit_log.metadata).lower())
        self.assertNotIn("key_hash", str(audit_log.metadata).lower())
        self.assertNotIn(created["secret"], str(audit_log.metadata))

    def test_rejects_secret_with_matching_prefix_and_invalid_hash(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")
        invalid_secret = f"{created['api_key']['prefix']}_invalid-tail"

        result = api_key_runtime_authentication.authenticate(
            tenant_id=self.tenant.id,
            authorization_header=f"Bearer {invalid_secret}",
            required_scope="read:orders",
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["result"], "api-key-auth-invalid")
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.auth_failed")
        self.assertEqual(audit_log.metadata["reason"], "hash-mismatch")
        self.assertEqual(audit_log.metadata["prefix"], created["api_key"]["prefix"])
        self.assertNotIn(invalid_secret, str(audit_log.metadata))

    def test_rejects_revoked_key(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")
        api_key_commands.revoke_key(tenant_id=self.tenant.id, key_id=created["api_key"]["id"])

        result = api_key_runtime_authentication.authenticate(
            tenant_id=self.tenant.id,
            authorization_header=f"Bearer {created['secret']}",
            required_scope="read:orders",
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["result"], "api-key-auth-revoked")
        self.assertEqual(result["api_key"]["status"], ApiKey.Status.REVOKED)

    def test_rejects_key_without_required_scope(self):
        created = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="ERP",
            scopes=["read:orders"],
        )

        result = api_key_runtime_authentication.authenticate(
            tenant_id=self.tenant.id,
            authorization_header=f"Bearer {created['secret']}",
            required_scope="write:products",
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["result"], "api-key-auth-scope-denied")
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.auth_failed")
        self.assertEqual(audit_log.metadata["reason"], "scope-denied")
        self.assertEqual(audit_log.metadata["required_scope"], "write:products")

    def test_rejects_non_bearer_header_without_leaking_header(self):
        result = api_key_runtime_authentication.authenticate(
            tenant_id=self.tenant.id,
            authorization_header="Basic hbx_should_not_be_logged",
            required_scope="read:orders",
        )

        self.assertFalse(result["authenticated"])
        self.assertEqual(result["result"], "api-key-auth-invalid")
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.auth_failed")
        self.assertEqual(audit_log.metadata["reason"], "invalid-header")
        self.assertNotIn("hbx_should_not_be_logged", str(audit_log.metadata))
