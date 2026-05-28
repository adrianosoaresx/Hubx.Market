from __future__ import annotations

from django.conf import settings

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_VIEW,
    admin_permissions,
)


def _platform_tenant_slug() -> str:
    return str(getattr(settings, "HUBX_PLATFORM_TENANT_SLUG", "platform-system") or "platform-system").strip().lower()


def admin_shell_context(request) -> dict[str, bool]:
    path = str(getattr(request, "path", "") or "")
    owner = getattr(request, "owner_user", None)
    platform_allowed = bool(
        owner
        and str(getattr(getattr(owner, "tenant", None), "slug", "") or "").strip().lower() == _platform_tenant_slug()
        and admin_permissions.check(
            role=getattr(owner, "role", ""),
            permission=PERMISSION_PLATFORM_TENANTS_VIEW,
        ).allowed
    )
    is_platform_path = path == "/ops/platform" or path.startswith("/ops/platform/")
    is_central_ops = path in {"/ops", "/ops/"} and getattr(request, "tenant", None) is None
    return {
        "is_platform_admin_shell": bool(is_platform_path or (is_central_ops and platform_allowed)),
    }
