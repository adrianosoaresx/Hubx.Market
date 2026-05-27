from __future__ import annotations

from app.modules.accounts.application.admin_owner_queries import admin_owner_queries
from app.modules.accounts.application.admin_permissions import AdminPermissionDecision, admin_permissions


def request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)


def request_owner_role(request) -> str:
    owner_user = getattr(request, "owner_user", None)
    if owner_user is not None:
        return str(getattr(owner_user, "role", "") or "").strip()
    user = getattr(request, "user", None)
    user_email = getattr(user, "email", "") or ""
    return admin_owner_queries.get_owner_role_by_email(tenant_id=request_tenant_id(request), email=user_email)


def request_admin_permission(request, permission: str) -> AdminPermissionDecision:
    return admin_permissions.check(role=request_owner_role(request), permission=permission)


def request_admin_can(request, permission: str) -> bool:
    return request_admin_permission(request, permission).allowed
