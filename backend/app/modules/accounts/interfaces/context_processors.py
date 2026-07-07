from __future__ import annotations

from django.conf import settings

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_VIEW,
    PERMISSION_SUBSCRIPTIONS_MANAGE,
    admin_permissions,
)
from app.modules.accounts.interfaces.merchant_ops_views import _allowed_nav_items


PLATFORM_NAV_ITEMS = (
    {"label": "Aquisições", "href": "/ops/platform/acquisitions/", "icon": "receipt-text", "permission": PERMISSION_PLATFORM_TENANTS_VIEW},
    {"label": "Cupons SaaS", "href": "/ops/platform/subscription-coupons/", "icon": "tag", "permission": PERMISSION_SUBSCRIPTIONS_MANAGE},
    {"label": "Lojas", "href": "/ops/platform/tenants/", "icon": "store", "permission": PERMISSION_PLATFORM_TENANTS_VIEW},
    {"label": "Onboarding", "href": "/ops/platform/onboarding/", "icon": "list", "permission": PERMISSION_PLATFORM_TENANTS_VIEW},
)


def _platform_tenant_slug() -> str:
    return str(getattr(settings, "HUBX_PLATFORM_TENANT_SLUG", "platform-system") or "platform-system").strip().lower()


def _allowed_platform_nav_items(*, role: object, path: str) -> list[dict[str, object]]:
    normalized_role = str(role or "").strip()
    if not normalized_role:
        return []
    return [
        {
            "label": item["label"],
            "href": item["href"],
            "icon": item["icon"],
            "active": path.startswith(str(item["href"])),
        }
        for item in PLATFORM_NAV_ITEMS
        if admin_permissions.check(role=normalized_role, permission=item["permission"]).allowed
    ]


def admin_shell_context(request) -> dict[str, object]:
    path = str(getattr(request, "path", "") or "")
    owner = getattr(request, "owner_user", None)
    owner_role = getattr(owner, "role", "")
    platform_allowed = bool(
        owner
        and str(getattr(getattr(owner, "tenant", None), "slug", "") or "").strip().lower() == _platform_tenant_slug()
        and admin_permissions.check(
            role=owner_role,
            permission=PERMISSION_PLATFORM_TENANTS_VIEW,
        ).allowed
    )
    is_platform_path = path == "/ops/platform" or path.startswith("/ops/platform/")
    is_central_ops = path in {"/ops", "/ops/"} and getattr(request, "tenant", None) is None
    is_platform_admin_shell = bool(is_platform_path or (is_central_ops and platform_allowed))
    is_tenant_admin_shell = bool(path == "/ops" or path.startswith("/ops/")) and not is_platform_admin_shell
    return {
        "is_platform_admin_shell": is_platform_admin_shell,
        "platform_nav_items": _allowed_platform_nav_items(role=owner_role, path=path) if is_platform_admin_shell else [],
        "admin_nav_items": _allowed_nav_items(request) if is_tenant_admin_shell else [],
    }
