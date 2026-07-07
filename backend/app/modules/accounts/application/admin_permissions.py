from __future__ import annotations

from dataclasses import dataclass


PERMISSION_COUPONS_MANAGE = "coupons.manage"
PERMISSION_CATALOG_MANAGE = "catalog.manage"
PERMISSION_CATALOG_VIEW = "catalog.view"
PERMISSION_CHECKOUT_VIEW = "checkout.view"
PERMISSION_CUSTOMERS_MANAGE = "customers.manage"
PERMISSION_CUSTOMERS_VIEW = "customers.view"
PERMISSION_AUDIT_VIEW = "audit.view"
PERMISSION_API_KEYS_MANAGE = "api_keys.manage"
PERMISSION_API_KEYS_VIEW = "api_keys.view"
PERMISSION_NEWSLETTER_MANAGE = "newsletter.manage"
PERMISSION_NEWSLETTER_VIEW = "newsletter.view"
PERMISSION_ORDERS_MANAGE = "orders.manage"
PERMISSION_ORDERS_VIEW = "orders.view"
PERMISSION_OWNERS_MANAGE = "owners.manage"
PERMISSION_PAGES_MANAGE = "pages.manage"
PERMISSION_PAYMENTS_MANAGE = "payments.manage"
PERMISSION_PAYMENTS_VIEW = "payments.view"
PERMISSION_PLATFORM_TENANTS_MANAGE = "platform.tenants.manage"
PERMISSION_PLATFORM_TENANTS_VIEW = "platform.tenants.view"
PERMISSION_REVIEWS_MODERATE = "reviews.moderate"
PERMISSION_SHIPPING_MANAGE = "shipping.manage"
PERMISSION_SHIPPING_VIEW = "shipping.view"
PERMISSION_STOREFRONT_BRANDING_MANAGE = "storefront.branding.manage"
PERMISSION_SUBSCRIPTIONS_MANAGE = "subscriptions.manage"
PERMISSION_SUBSCRIPTIONS_VIEW = "subscriptions.view"

ROLE_OWNER = "owner"
ROLE_ADMIN = "admin"
ROLE_MARKETING = "marketing"
ROLE_CONTENT_EDITOR = "content_editor"
ROLE_SUPPORT = "support"
ROLE_VIEWER = "viewer"

FULL_ADMIN_PERMISSIONS = {
    PERMISSION_AUDIT_VIEW,
    PERMISSION_API_KEYS_MANAGE,
    PERMISSION_API_KEYS_VIEW,
    PERMISSION_NEWSLETTER_MANAGE,
    PERMISSION_CATALOG_MANAGE,
    PERMISSION_CATALOG_VIEW,
    PERMISSION_CHECKOUT_VIEW,
    PERMISSION_COUPONS_MANAGE,
    PERMISSION_CUSTOMERS_MANAGE,
    PERMISSION_CUSTOMERS_VIEW,
    PERMISSION_NEWSLETTER_VIEW,
    PERMISSION_ORDERS_MANAGE,
    PERMISSION_ORDERS_VIEW,
    PERMISSION_OWNERS_MANAGE,
    PERMISSION_PAGES_MANAGE,
    PERMISSION_PAYMENTS_MANAGE,
    PERMISSION_PAYMENTS_VIEW,
    PERMISSION_PLATFORM_TENANTS_MANAGE,
    PERMISSION_PLATFORM_TENANTS_VIEW,
    PERMISSION_REVIEWS_MODERATE,
    PERMISSION_SHIPPING_MANAGE,
    PERMISSION_SHIPPING_VIEW,
    PERMISSION_STOREFRONT_BRANDING_MANAGE,
    PERMISSION_SUBSCRIPTIONS_MANAGE,
    PERMISSION_SUBSCRIPTIONS_VIEW,
}

ROLE_PERMISSIONS: dict[str, set[str]] = {
    ROLE_OWNER: FULL_ADMIN_PERMISSIONS,
    ROLE_ADMIN: FULL_ADMIN_PERMISSIONS,
    ROLE_MARKETING: {
        PERMISSION_CATALOG_MANAGE,
        PERMISSION_CATALOG_VIEW,
        PERMISSION_CHECKOUT_VIEW,
        PERMISSION_COUPONS_MANAGE,
        PERMISSION_NEWSLETTER_MANAGE,
        PERMISSION_NEWSLETTER_VIEW,
        PERMISSION_PAGES_MANAGE,
        PERMISSION_REVIEWS_MODERATE,
        PERMISSION_STOREFRONT_BRANDING_MANAGE,
    },
    ROLE_CONTENT_EDITOR: {
        PERMISSION_CATALOG_MANAGE,
        PERMISSION_CATALOG_VIEW,
        PERMISSION_CHECKOUT_VIEW,
        PERMISSION_PAGES_MANAGE,
        PERMISSION_REVIEWS_MODERATE,
        PERMISSION_STOREFRONT_BRANDING_MANAGE,
    },
    ROLE_SUPPORT: {
        PERMISSION_CHECKOUT_VIEW,
        PERMISSION_CUSTOMERS_MANAGE,
        PERMISSION_CUSTOMERS_VIEW,
        PERMISSION_ORDERS_MANAGE,
        PERMISSION_ORDERS_VIEW,
        PERMISSION_REVIEWS_MODERATE,
        PERMISSION_SHIPPING_MANAGE,
        PERMISSION_SHIPPING_VIEW,
        PERMISSION_SUBSCRIPTIONS_VIEW,
    },
    ROLE_VIEWER: {
        PERMISSION_AUDIT_VIEW,
        PERMISSION_API_KEYS_VIEW,
        PERMISSION_CATALOG_VIEW,
        PERMISSION_CHECKOUT_VIEW,
        PERMISSION_CUSTOMERS_VIEW,
        PERMISSION_ORDERS_VIEW,
        PERMISSION_SHIPPING_VIEW,
    },
}


def normalize_admin_role(role: object) -> str:
    return str(role or "").strip().lower().replace("-", "_")


@dataclass(frozen=True)
class AdminPermissionDecision:
    allowed: bool
    role: str
    permission: str
    reason: str


@dataclass
class AdminPermissionService:
    role_permissions: dict[str, set[str]]

    def check(self, *, role: object, permission: object) -> AdminPermissionDecision:
        normalized_role = normalize_admin_role(role)
        normalized_permission = str(permission or "").strip()
        if not normalized_role:
            return AdminPermissionDecision(
                allowed=True,
                role="",
                permission=normalized_permission,
                reason="permission-context-missing",
            )
        allowed_permissions = self.role_permissions.get(normalized_role)
        if allowed_permissions is None:
            return AdminPermissionDecision(
                allowed=False,
                role=normalized_role,
                permission=normalized_permission,
                reason="admin-role-unknown",
            )
        if normalized_permission in allowed_permissions:
            return AdminPermissionDecision(
                allowed=True,
                role=normalized_role,
                permission=normalized_permission,
                reason="admin-permission-granted",
            )
        return AdminPermissionDecision(
            allowed=False,
            role=normalized_role,
            permission=normalized_permission,
            reason="admin-permission-denied",
        )


admin_permissions = AdminPermissionService(role_permissions=ROLE_PERMISSIONS)
