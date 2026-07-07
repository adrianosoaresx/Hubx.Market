from django.test import TestCase

from app.modules.accounts.application.admin_owner_queries import admin_owner_queries
from app.modules.accounts.application.admin_permissions import (
    PERMISSION_API_KEYS_MANAGE,
    PERMISSION_API_KEYS_VIEW,
    PERMISSION_CATALOG_MANAGE,
    PERMISSION_CATALOG_VIEW,
    PERMISSION_CHECKOUT_VIEW,
    PERMISSION_COUPONS_MANAGE,
    PERMISSION_CUSTOMERS_MANAGE,
    PERMISSION_CUSTOMERS_VIEW,
    PERMISSION_NEWSLETTER_MANAGE,
    PERMISSION_ORDERS_MANAGE,
    PERMISSION_ORDERS_VIEW,
    PERMISSION_PAGES_MANAGE,
    PERMISSION_PAYMENTS_MANAGE,
    PERMISSION_PAYMENTS_VIEW,
    PERMISSION_REVIEWS_MODERATE,
    PERMISSION_SHIPPING_MANAGE,
    PERMISSION_SUBSCRIPTIONS_MANAGE,
    admin_permissions,
)
from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


class AdminPermissionTests(TestCase):
    def setUp(self):
        self.tenant = Tenant.objects.create(name="Loja Permissões", slug="loja-permissoes", subdomain="loja-permissoes")
        self.other_tenant = Tenant.objects.create(name="Outra Permissões", slug="outra-permissoes", subdomain="outra-permissoes")

    def test_owner_and_admin_can_manage_sensitive_actions(self):
        for role in ("owner", "admin"):
            self.assertTrue(admin_permissions.check(role=role, permission=PERMISSION_COUPONS_MANAGE).allowed)
            self.assertTrue(admin_permissions.check(role=role, permission=PERMISSION_PAGES_MANAGE).allowed)
            self.assertTrue(admin_permissions.check(role=role, permission=PERMISSION_PAYMENTS_MANAGE).allowed)
            self.assertTrue(admin_permissions.check(role=role, permission=PERMISSION_REVIEWS_MODERATE).allowed)
            self.assertTrue(admin_permissions.check(role=role, permission=PERMISSION_SUBSCRIPTIONS_MANAGE).allowed)

    def test_limited_roles_have_narrow_sensitive_action_access(self):
        self.assertTrue(admin_permissions.check(role="content_editor", permission=PERMISSION_PAGES_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="content_editor", permission=PERMISSION_CATALOG_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="content_editor", permission=PERMISSION_REVIEWS_MODERATE).allowed)
        self.assertFalse(admin_permissions.check(role="content_editor", permission=PERMISSION_COUPONS_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_REVIEWS_MODERATE).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_ORDERS_VIEW).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_ORDERS_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_CUSTOMERS_VIEW).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_CUSTOMERS_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_SHIPPING_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="support", permission=PERMISSION_PAGES_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="support", permission=PERMISSION_PAYMENTS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="support", permission=PERMISSION_API_KEYS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="support", permission=PERMISSION_NEWSLETTER_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="support", permission=PERMISSION_SUBSCRIPTIONS_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="marketing", permission=PERMISSION_NEWSLETTER_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_REVIEWS_MODERATE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_CUSTOMERS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_ORDERS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_PAYMENTS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_SHIPPING_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="viewer", permission=PERMISSION_API_KEYS_VIEW).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_API_KEYS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_NEWSLETTER_MANAGE).allowed)

    def test_navigation_permissions_are_role_specific(self):
        self.assertTrue(admin_permissions.check(role="marketing", permission=PERMISSION_CATALOG_VIEW).allowed)
        self.assertTrue(admin_permissions.check(role="marketing", permission=PERMISSION_CATALOG_MANAGE).allowed)
        self.assertTrue(admin_permissions.check(role="marketing", permission=PERMISSION_COUPONS_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="marketing", permission=PERMISSION_ORDERS_VIEW).allowed)
        self.assertTrue(admin_permissions.check(role="support", permission=PERMISSION_CHECKOUT_VIEW).allowed)
        self.assertFalse(admin_permissions.check(role="support", permission=PERMISSION_PAYMENTS_VIEW).allowed)
        self.assertTrue(admin_permissions.check(role="viewer", permission=PERMISSION_CATALOG_VIEW).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_CATALOG_MANAGE).allowed)
        self.assertFalse(admin_permissions.check(role="viewer", permission=PERMISSION_COUPONS_MANAGE).allowed)

    def test_missing_role_context_preserves_legacy_admin_compatibility(self):
        decision = admin_permissions.check(role="", permission=PERMISSION_COUPONS_MANAGE)

        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "permission-context-missing")

    def test_owner_role_lookup_is_tenant_scoped_and_active_only(self):
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="editor@hubx.market",
            role="content_editor",
            is_active=True,
        )
        OwnerUser.objects.create(
            tenant=self.other_tenant,
            email="editor@hubx.market",
            role="owner",
            is_active=True,
        )
        OwnerUser.objects.create(
            tenant=self.tenant,
            email="inactive@hubx.market",
            role="owner",
            is_active=False,
        )

        self.assertEqual(
            admin_owner_queries.get_owner_role_by_email(tenant_id=self.tenant.id, email="editor@hubx.market"),
            "content_editor",
        )
        self.assertEqual(
            admin_owner_queries.get_owner_role_by_email(tenant_id=self.other_tenant.id, email="editor@hubx.market"),
            "owner",
        )
        self.assertEqual(
            admin_owner_queries.get_owner_role_by_email(tenant_id=self.tenant.id, email="inactive@hubx.market"),
            "",
        )
