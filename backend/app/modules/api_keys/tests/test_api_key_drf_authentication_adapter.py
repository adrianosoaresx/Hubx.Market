from __future__ import annotations

from django.conf import settings
from django.test import TestCase
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory
from rest_framework.views import APIView

from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.interfaces.authentication import ApiKeyAuthentication, HasApiKeyScope
from app.modules.api_keys.models import ApiKey
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


class ApiKeyProtectedView(APIView):
    authentication_classes = (ApiKeyAuthentication,)
    permission_classes = (HasApiKeyScope,)
    required_api_key_scope = "read:orders"

    def get(self, request):
        return Response(
            {
                "api_key_id": request.user.api_key_id,
                "tenant_id": request.user.tenant_id,
                "prefix": request.user.prefix,
                "scopes": request.user.scopes,
                "rate_limit_key": request.auth["rate_limit_key"],
                "has_secret": hasattr(request.user, "secret"),
                "has_key_hash": hasattr(request.user, "key_hash"),
            }
        )


class ApiKeyWriteProtectedView(ApiKeyProtectedView):
    required_api_key_scope = "write:products"


class ApiKeyDrfAuthenticationAdapterTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.tenant = Tenant.objects.create(name="DRF Tenant", slug="drf-tenant", subdomain="drf-tenant")
        self.other_tenant = Tenant.objects.create(
            name="Other DRF Tenant",
            slug="other-drf-tenant",
            subdomain="other-drf-tenant",
        )

    def test_adapter_authenticates_opt_in_view_with_safe_principal(self):
        created = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="ERP",
            scopes=["read:orders"],
        )

        response = self._request(ApiKeyProtectedView, tenant=self.tenant, secret=created["secret"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["tenant_id"], self.tenant.id)
        self.assertEqual(response.data["api_key_id"], created["api_key"]["id"])
        self.assertEqual(response.data["prefix"], created["api_key"]["prefix"])
        self.assertEqual(response.data["scopes"], ("read:orders",))
        self.assertEqual(response.data["rate_limit_key"], f"tenant:{self.tenant.id}:api_key:{created['api_key']['prefix']}")
        self.assertFalse(response.data["has_secret"])
        self.assertFalse(response.data["has_key_hash"])
        api_key = ApiKey.objects.get(pk=created["api_key"]["id"])
        self.assertIsNotNone(api_key.last_used_at)

    def test_adapter_does_not_register_global_drf_authentication(self):
        configured_classes = settings.REST_FRAMEWORK["DEFAULT_AUTHENTICATION_CLASSES"]

        self.assertNotIn("app.modules.api_keys.interfaces.authentication.ApiKeyAuthentication", configured_classes)
        self.assertNotIn("modules.api_keys.interfaces.authentication.ApiKeyAuthentication", configured_classes)

    def test_adapter_rejects_invalid_key_without_leaking_sensitive_material(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")
        invalid_secret = f"{created['api_key']['prefix']}_invalid-tail"

        response = self._request(ApiKeyProtectedView, tenant=self.tenant, secret=invalid_secret)

        self.assertEqual(response.status_code, 401)
        audit_log = AuditLog.objects.get(tenant=self.tenant, action="api_key.auth_failed")
        self.assertEqual(audit_log.metadata["reason"], "hash-mismatch")
        self.assertNotIn(invalid_secret, str(audit_log.metadata))
        self.assertNotIn("key_hash", str(audit_log.metadata).lower())

    def test_adapter_rejects_cross_tenant_key(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")

        response = self._request(ApiKeyProtectedView, tenant=self.other_tenant, secret=created["secret"])

        self.assertEqual(response.status_code, 401)
        api_key = ApiKey.objects.get(pk=created["api_key"]["id"])
        self.assertIsNone(api_key.last_used_at)
        audit_log = AuditLog.objects.get(tenant=self.other_tenant, action="api_key.auth_failed")
        self.assertEqual(audit_log.metadata["reason"], "not-found")

    def test_permission_rejects_missing_required_scope(self):
        created = api_key_commands.create_key(
            tenant_id=self.tenant.id,
            name="ERP",
            scopes=["read:orders"],
        )

        response = self._request(ApiKeyWriteProtectedView, tenant=self.tenant, secret=created["secret"])

        self.assertEqual(response.status_code, 403)
        self.assertEqual(AuditLog.objects.filter(tenant=self.tenant, action="api_key.auth_failed").count(), 0)

    def test_permission_rejects_view_without_explicit_scope(self):
        class MissingScopeView(ApiKeyProtectedView):
            required_api_key_scope = ""

        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP")

        response = self._request(MissingScopeView, tenant=self.tenant, secret=created["secret"])

        self.assertEqual(response.status_code, 403)

    def test_missing_bearer_credentials_do_not_authenticate(self):
        request = self.factory.get("/")
        request.tenant = self.tenant

        response = ApiKeyProtectedView.as_view()(request)

        self.assertEqual(response.status_code, 401)
        self.assertEqual(AuditLog.objects.filter(action="api_key.auth_failed").count(), 0)

    def _request(self, view_class, *, tenant: Tenant, secret: str):
        request = self.factory.get(
            "/",
            HTTP_AUTHORIZATION=f"Bearer {secret}",
            HTTP_X_REQUEST_ID="req-api-key-test",
            REMOTE_ADDR="127.0.0.1",
        )
        request.tenant = tenant
        return view_class.as_view()(request)
