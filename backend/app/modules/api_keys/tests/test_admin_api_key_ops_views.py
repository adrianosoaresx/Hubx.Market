from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.models import ApiKey
from app.modules.audit.models import AuditLog
from app.modules.tenants.models import Tenant


@override_settings(HUBX_MARKET_ROOT_DOMAIN="hubx.market", ALLOWED_HOSTS=[".hubx.market", "testserver"])
class AdminApiKeyOpsViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="API Admin Tenant", slug="api-admin-tenant", subdomain="api-admin")
        self.other_tenant = Tenant.objects.create(
            name="Other API Admin Tenant",
            slug="other-api-admin-tenant",
            subdomain="other-api-admin",
        )
        self.host = f"{self.tenant.subdomain}.hubx.market"
        self.other_host = f"{self.other_tenant.subdomain}.hubx.market"
        self.user = get_user_model().objects.create_user(
            username="owner@hubx.market",
            email="owner@hubx.market",
            password="secret",
        )
        OwnerUser.objects.create(tenant=self.tenant, email=self.user.email, role="owner", is_active=True)
        OwnerUser.objects.create(tenant=self.other_tenant, email=self.user.email, role="owner", is_active=True)
        self.client.force_login(self.user)
        self.client.defaults["HTTP_HOST"] = self.host

    def test_list_view_is_tenant_scoped_and_does_not_expose_secret_or_hash(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="ERP tenant")
        other_created = api_key_commands.create_key(tenant_id=self.other_tenant.id, name="ERP other")

        response = self.client.get(reverse("api_keys_ops:admin-api-keys-list"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "pages/templates/admin_api_keys_page.html")
        self.assertContains(response, "ERP tenant")
        self.assertNotContains(response, "ERP other")
        self.assertContains(response, created["api_key"]["prefix"])
        self.assertNotContains(response, created["secret"])
        self.assertNotContains(response, other_created["secret"])
        self.assertNotContains(response, "key_hash")

    def test_owner_can_create_key_and_secret_is_only_in_creation_response(self):
        response = self.client.post(
            reverse("api_keys_ops:admin-api-key-create"),
            {"name": "Catalog partner", "scopes": "read:catalog, read:orders"},
        )

        self.assertEqual(response.status_code, 200)
        api_key = ApiKey.objects.get(tenant=self.tenant, name="Catalog partner")
        self.assertEqual(api_key.scopes, ["read:catalog", "read:orders"])
        self.assertContains(response, "Segredo da nova API key")
        self.assertContains(response, api_key.prefix)
        self.assertNotContains(response, "key_hash")
        self.assertTrue(AuditLog.objects.filter(tenant=self.tenant, action="api_key.created").exists())

        follow_up_response = self.client.get(reverse("api_keys_ops:admin-api-keys-list"))

        self.assertEqual(follow_up_response.status_code, 200)
        self.assertContains(follow_up_response, api_key.prefix)
        self.assertNotContains(follow_up_response, "Segredo da nova API key")

    def test_viewer_can_view_but_cannot_create_or_revoke(self):
        OwnerUser.objects.filter(tenant=self.tenant, email=self.user.email).update(role="viewer")
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="Viewer visible")

        list_response = self.client.get(reverse("api_keys_ops:admin-api-keys-list"))
        create_response = self.client.post(
            reverse("api_keys_ops:admin-api-key-create"),
            {"name": "Forbidden", "scopes": "read:catalog"},
        )
        revoke_response = self.client.post(
            reverse("api_keys_ops:admin-api-key-revoke", kwargs={"key_id": created["api_key"]["id"]}),
        )

        self.assertEqual(list_response.status_code, 200)
        self.assertContains(list_response, "Viewer visible")
        self.assertNotContains(list_response, "Criar chave")
        self.assertNotContains(list_response, "Revogar")
        self.assertEqual(create_response.status_code, 403)
        self.assertEqual(revoke_response.status_code, 302)
        self.assertFalse(ApiKey.objects.filter(tenant=self.tenant, name="Forbidden").exists())
        self.assertEqual(ApiKey.objects.get(pk=created["api_key"]["id"]).status, ApiKey.Status.ACTIVE)

    def test_revoke_is_tenant_scoped(self):
        created = api_key_commands.create_key(tenant_id=self.tenant.id, name="Tenant key")
        other_client = Client()
        other_client.force_login(self.user)
        other_client.defaults["HTTP_HOST"] = self.other_host

        cross_tenant_response = other_client.post(
            reverse("api_keys_ops:admin-api-key-revoke", kwargs={"key_id": created["api_key"]["id"]}),
        )

        self.assertEqual(cross_tenant_response.status_code, 302)
        self.assertIn("status=not-found", cross_tenant_response["Location"])
        self.assertEqual(ApiKey.objects.get(pk=created["api_key"]["id"]).status, ApiKey.Status.ACTIVE)

        revoked_response = self.client.post(
            reverse("api_keys_ops:admin-api-key-revoke", kwargs={"key_id": created["api_key"]["id"]}),
        )

        self.assertEqual(revoked_response.status_code, 302)
        self.assertIn("status=revoked", revoked_response["Location"])
        self.assertEqual(ApiKey.objects.get(pk=created["api_key"]["id"]).status, ApiKey.Status.REVOKED)

    def test_csrf_is_required_for_mutating_forms(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        csrf_client.defaults["HTTP_HOST"] = self.host

        missing_csrf_response = csrf_client.post(
            reverse("api_keys_ops:admin-api-key-create"),
            {"name": "No csrf", "scopes": "read:catalog"},
        )
        form_response = csrf_client.get(reverse("api_keys_ops:admin-api-keys-list"))

        self.assertEqual(missing_csrf_response.status_code, 403)
        self.assertContains(form_response, "csrfmiddlewaretoken")
