from django.test import TestCase, override_settings
from django.urls import reverse

from app.modules.accounts.models import OwnerUser
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

    def test_admin_owner_action_toggles_notifications(self):
        response = self.client.post(
            reverse("owners:admin-owner-update", kwargs={"owner_id": self.owner.id}),
            data={"receives_notifications": "0"},
            HTTP_HOST=f"{self.tenant.subdomain}.hubx.market",
        )

        self.assertEqual(response.status_code, 302)
        self.owner.refresh_from_db()
        self.assertFalse(self.owner.receives_notifications)
