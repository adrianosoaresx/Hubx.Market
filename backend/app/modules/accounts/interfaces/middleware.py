from __future__ import annotations

from typing import Callable
from urllib.parse import urlencode

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.urls import reverse

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_AUDIT_VIEW,
    PERMISSION_CATALOG_VIEW,
    PERMISSION_CHECKOUT_VIEW,
    PERMISSION_COUPONS_MANAGE,
    PERMISSION_CUSTOMERS_VIEW,
    PERMISSION_NEWSLETTER_VIEW,
    PERMISSION_ORDERS_VIEW,
    PERMISSION_OWNERS_MANAGE,
    PERMISSION_PAGES_MANAGE,
    PERMISSION_PAYMENTS_VIEW,
    PERMISSION_REVIEWS_MODERATE,
    PERMISSION_SHIPPING_VIEW,
    admin_permissions,
)
from app.modules.audit.application.audit_log_commands import audit_log_commands


OPS_PERMISSION_PREFIXES = (
    ("/ops/audit/", PERMISSION_AUDIT_VIEW),
    ("/ops/catalog/", PERMISSION_CATALOG_VIEW),
    ("/ops/checkout/", PERMISSION_CHECKOUT_VIEW),
    ("/ops/coupons/", PERMISSION_COUPONS_MANAGE),
    ("/ops/customers/", PERMISSION_CUSTOMERS_VIEW),
    ("/ops/newsletter/", PERMISSION_NEWSLETTER_VIEW),
    ("/ops/owners/", PERMISSION_OWNERS_MANAGE),
    ("/ops/orders/", PERMISSION_ORDERS_VIEW),
    ("/ops/payments/", PERMISSION_PAYMENTS_VIEW),
    ("/ops/pages/", PERMISSION_PAGES_MANAGE),
    ("/ops/reviews/", PERMISSION_REVIEWS_MODERATE),
    ("/ops/shipping/", PERMISSION_SHIPPING_VIEW),
)


class OwnerContextMiddleware:
    """Attach the active tenant-scoped OwnerUser to request.owner_user for ops surfaces."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        request.owner_user = None
        if not self._should_resolve(request):
            return self.get_response(request)

        tenant = getattr(request, "tenant", None)
        user = getattr(request, "user", None)
        user_email = str(getattr(user, "email", "") or "").strip()
        if tenant is None or not user_email or not getattr(user, "is_authenticated", False):
            return self.get_response(request)

        try:
            from app.modules.accounts.models import OwnerUser
        except Exception:
            return self.get_response(request)

        request.owner_user = OwnerUser.objects.filter(
            tenant=tenant,
            email__iexact=user_email,
            is_active=True,
        ).first()
        return self.get_response(request)

    def _should_resolve(self, request) -> bool:
        path = str(getattr(request, "path", "") or "")
        return path == "/ops" or path.startswith("/ops/")


class OpsAuthenticationGateMiddleware:
    """Optionally require an authenticated active owner for ops surfaces."""

    def __init__(self, get_response: Callable):
        self.get_response = get_response

    def __call__(self, request):
        if not self._is_enabled() or not self._should_gate(request):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if not getattr(user, "is_authenticated", False):
            self._record_gate_event(request=request, action="owner.ops_gate_redirected", actor_label="anonymous")
            return HttpResponseRedirect(self._login_url(request))

        if getattr(request, "owner_user", None) is None:
            self._record_gate_event(request=request, action="owner.ops_gate_forbidden", actor_label=str(user or ""))
            raise PermissionDenied("Owner access required")

        required_permission = self._required_permission(request)
        if required_permission:
            owner = getattr(request, "owner_user", None)
            decision = admin_permissions.check(role=getattr(owner, "role", ""), permission=required_permission)
            if not decision.allowed:
                self._record_gate_event(
                    request=request,
                    action="owner.ops_permission_denied",
                    actor_label=str(getattr(owner, "email", "") or user or ""),
                    metadata={
                        "path": str(getattr(request, "path", "") or "")[:180],
                        "permission": required_permission,
                        "role": decision.role,
                        "reason": decision.reason,
                    },
                )
                raise PermissionDenied("Owner permission required")

        return self.get_response(request)

    def _is_enabled(self) -> bool:
        return bool(getattr(settings, "HUBX_OPS_AUTH_GATE_ENFORCED", False))

    def _should_gate(self, request) -> bool:
        path = str(getattr(request, "path", "") or "")
        return path == "/ops" or path.startswith("/ops/")

    def _login_url(self, request) -> str:
        login_url = reverse("accounts:login")
        return f"{login_url}?{urlencode({'next': request.get_full_path()})}"

    def _required_permission(self, request) -> str:
        path = str(getattr(request, "path", "") or "")
        if path == "/ops" or path == "/ops/":
            return ""
        for prefix, permission in OPS_PERMISSION_PREFIXES:
            if path.startswith(prefix):
                return permission
        return ""

    def _record_gate_event(self, *, request, action: str, actor_label: str, metadata: dict[str, object] | None = None) -> None:
        tenant_id = getattr(getattr(request, "tenant", None), "id", None)
        if not tenant_id:
            return
        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="accounts",
            action=action,
            entity_type="OwnerUser",
            actor_label=actor_label,
            summary="Gate /ops/ bloqueou ou redirecionou uma request.",
            metadata=metadata or {"path": str(getattr(request, "path", "") or "")[:180]},
        )
