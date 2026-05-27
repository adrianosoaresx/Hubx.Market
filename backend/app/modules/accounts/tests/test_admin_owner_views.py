from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth.models import User

from app.modules.accounts.models import OwnerUser
from app.modules.audit.models import AuditLog
from app.modules.notifications.models import EmailLog
from app.modules.tenants.models import Tenant


@override_settings(ALLOWED_HOSTS=["testserver", ".hubx.market", "localhost"])
class AdminOwnerViewTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Owner View", slug="loja-owner-view", subdomain="loja-owner-view")
        self.owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="owner.view@hubx.market",
            full_name="Owner View",
        )

    def test_admin_owner_list_renders_tenant_owners(self):
        response = self.client.get(
            reverse("owners:admin-owners-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "owner.view@hubx.market")
        self.assertContains(response, "Recebe notificações")
        self.assertContains(response, reverse("owners:admin-owner-create"))
        self.assertContains(response, reverse("owners:admin-owner-edit", kwargs={"owner_id": self.owner.id}))

    def test_admin_owner_action_toggles_notifications(self):
        response = self.client.post(
            reverse("owners:admin-owner-update", kwargs={"owner_id": self.owner.id}),
            data={"receives_notifications": "0"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.receives_notifications)

    def test_admin_owner_invite_creates_django_user_and_records_audit(self):
        actor_owner = OwnerUser.objects.create(
            tenant=self.tenant,
            email="actor.owner@hubx.market",
            role="owner",
            is_active=True,
        )
        actor_user = User.objects.create_user(username="actor-owner", email="actor.owner@hubx.market", password="secret")
        self.client.force_login(actor_user)

        response = self.client.post(
            reverse("owners:admin-owner-invite", kwargs={"owner_id": self.owner.id}),
            data={"next": reverse("owners:admin-owners-list")},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=owner-invite-created", response["Location"])
        invited_user = User.objects.get(email="owner.view@hubx.market")
        self.assertFalse(invited_user.has_usable_password())
        self.assertTrue(
            EmailLog.objects.filter(
                tenant=self.tenant,
                source_event="owner.invited",
                intent_key="owner.access.invite",
                recipient_email="owner.view@hubx.market",
            ).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.invited",
                entity_id=str(self.owner.id),
                actor_label=str(actor_user),
            ).exists()
        )
        self.assertEqual(actor_owner.email, "actor.owner@hubx.market")

    def test_admin_owner_invite_blocks_limited_role(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="support.actor@hubx.market",
            role="support",
            is_active=True,
        )
        actor_user = User.objects.create_user(username="support-actor", email="support.actor@hubx.market", password="secret")
        self.client.force_login(actor_user)

        response = self.client.post(
            reverse("owners:admin-owner-invite", kwargs={"owner_id": self.owner.id}),
            data={"next": reverse("owners:admin-owners-list")},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("result=owner-invite-permission-denied", response["Location"])
        self.assertFalse(User.objects.filter(email="owner.view@hubx.market").exists())

    def test_admin_owner_create_view_creates_owner_for_current_tenant(self):
        response = self.client.post(
            reverse("owners:admin-owner-create"),
            data={
                "email": "support@hubx.market",
                "full_name": "Support",
                "role": "support",
                "is_active": "1",
                "receives_notifications": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        owner = OwnerUser.objects.get(email="support@hubx.market")
        self.assertEqual(owner.tenant, self.tenant)
        self.assertEqual(owner.role, "support")

    def test_admin_owner_edit_view_updates_access(self):
        response = self.client.post(
            reverse("owners:admin-owner-edit", kwargs={"owner_id": self.owner.id}),
            data={
                "email": "owner.updated@hubx.market",
                "full_name": "Owner Updated",
                "role": "admin",
                "is_active": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertEqual(self.owner.email, "owner.updated@hubx.market")
        self.assertEqual(self.owner.role, "admin")
        self.assertFalse(self.owner.receives_notifications)

    def test_owner_context_middleware_blocks_ops_action_for_limited_role(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="marketing@hubx.market",
            role="marketing",
            is_active=True,
        )
        user = User.objects.create_user(username="marketing", email="marketing@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.post(
            reverse("owners:admin-owner-create"),
            data={
                "email": "blocked@hubx.market",
                "role": "support",
                "is_active": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 400)
        self.assertContains(response, "Permissão insuficiente", status_code=400)
        self.assertFalse(OwnerUser.objects.filter(email="blocked@hubx.market").exists())

    def test_owner_context_middleware_allows_ops_action_for_owner_role(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="admin.owner@hubx.market",
            role="owner",
            is_active=True,
        )
        user = User.objects.create_user(username="admin-owner", email="admin.owner@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.post(
            reverse("owners:admin-owner-create"),
            data={
                "email": "allowed@hubx.market",
                "role": "support",
                "is_active": "1",
            },
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(OwnerUser.objects.filter(tenant=self.tenant, email="allowed@hubx.market").exists())

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_ops_auth_gate_redirects_anonymous_user_to_login(self):
        response = self.client.get(
            reverse("owners:admin-owners-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response["Location"].startswith("/accounts/login/?next="))

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_ops_auth_gate_rejects_authenticated_user_without_active_owner(self):
        user = User.objects.create_user(username="outsider", email="outsider@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get(
            reverse("owners:admin-owners-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 403)

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_ops_auth_gate_allows_authenticated_active_owner(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="active.owner@hubx.market",
            role="owner",
            is_active=True,
        )
        user = User.objects.create_user(username="active-owner", email="active.owner@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get(
            reverse("owners:admin-owners-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_ops_permission_gate_rejects_direct_url_without_permission(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="support.direct@hubx.market",
            role="support",
            is_active=True,
        )
        user = User.objects.create_user(username="support-direct", email="support.direct@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get(
            reverse("coupons:admin-coupons-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 403)
        self.assertTrue(
            AuditLog.objects.filter(
                tenant=self.tenant,
                module="accounts",
                action="owner.ops_permission_denied",
                actor_label="support.direct@hubx.market",
            ).exists()
        )

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_ops_permission_gate_allows_direct_url_with_permission(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="marketing.direct@hubx.market",
            role="marketing",
            is_active=True,
        )
        user = User.objects.create_user(username="marketing-direct", email="marketing.direct@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get(
            reverse("coupons:admin-coupons-list"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)

    @override_settings(HUBX_OPS_AUTH_GATE_ENFORCED=True)
    def test_ops_permission_gate_allows_dashboard_for_limited_role(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="viewer.dashboard@hubx.market",
            role="viewer",
            is_active=True,
        )
        user = User.objects.create_user(username="viewer-dashboard", email="viewer.dashboard@hubx.market", password="secret")
        self.client.force_login(user)

        response = self.client.get(
            reverse("merchant_ops:admin-dashboard"),
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 200)
