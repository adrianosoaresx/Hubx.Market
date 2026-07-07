from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model, login as django_login

from app.modules.accounts.application.owner_login_commands import OWNER_MFA_PENDING_SESSION_KEY
from app.modules.accounts.application.owner_session_policy import (
    OWNER_SESSION_EXPIRES_AT_KEY,
    OWNER_SESSION_KIND_KEY,
    OWNER_SESSION_REMEMBERED_KEY,
    apply_owner_session_policy,
)
from app.modules.accounts.models import AccountProfile, OwnerUser


DEMO_ADMIN_EMAIL = "admin@hubx-demo.market"
DEMO_CUSTOMER_EMAIL = "cliente@hubx-demo.market"
ACCOUNT_PROFILE_SESSION_KEY = "hubx_account_profile_id"
ACCOUNT_SESSION_KIND_KEY = "hubx_account_session_kind"
DEMO_SESSION_SOURCE_KEY = "hubx_demo_session_source"
DEMO_SESSION_RETURN_URL_KEY = "hubx_demo_session_return_url"


def _demo_tenant_subdomain() -> str:
    return str(getattr(settings, "HUBX_MARKET_DEMO_TENANT_SUBDOMAIN", "hubx-demo") or "hubx-demo").strip().lower()


@dataclass
class DemoSessionLoginCommandService:
    def authenticate_demo_profile(self, *, request, tenant, profile: object, return_url: object = "") -> dict[str, object]:
        if not self._is_demo_tenant(tenant):
            return {"result": "demo-session-tenant-invalid"}

        normalized_profile = str(profile or "").strip().lower()
        if normalized_profile == "admin":
            return self._authenticate_admin(request=request, tenant=tenant, return_url=return_url)
        if normalized_profile == "customer":
            return self._authenticate_customer(request=request, tenant=tenant, return_url=return_url)
        return {"result": "demo-session-profile-invalid"}

    def _authenticate_admin(self, *, request, tenant, return_url: object = "") -> dict[str, object]:
        user = self._active_user(email=DEMO_ADMIN_EMAIL)
        owner = OwnerUser.objects.filter(
            tenant=tenant,
            email__iexact=DEMO_ADMIN_EMAIL,
            is_active=True,
        ).first()
        if user is None or owner is None:
            return {"result": "demo-session-admin-unavailable"}

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.pop(ACCOUNT_PROFILE_SESSION_KEY, None)
        request.session.pop(ACCOUNT_SESSION_KIND_KEY, None)
        request.session.pop(OWNER_MFA_PENDING_SESSION_KEY, None)
        self._set_demo_session_metadata(request=request, return_url=return_url)
        apply_owner_session_policy(request, remember_me=False)
        return {"result": "demo-session-authenticated", "profile": "admin", "redirect_url": "/ops/"}

    def _authenticate_customer(self, *, request, tenant, return_url: object = "") -> dict[str, object]:
        user = self._active_user(email=DEMO_CUSTOMER_EMAIL)
        profile = (
            AccountProfile.objects.filter(
                tenant=tenant,
                email__iexact=DEMO_CUSTOMER_EMAIL,
                is_active=True,
                customer__tenant=tenant,
                customer__status="active",
            )
            .select_related("customer")
            .first()
        )
        if user is None or profile is None:
            return {"result": "demo-session-customer-unavailable"}

        django_login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session.pop(OWNER_MFA_PENDING_SESSION_KEY, None)
        request.session.pop(OWNER_SESSION_KIND_KEY, None)
        request.session.pop(OWNER_SESSION_REMEMBERED_KEY, None)
        request.session.pop(OWNER_SESSION_EXPIRES_AT_KEY, None)
        request.session[ACCOUNT_PROFILE_SESSION_KEY] = profile.id
        request.session[ACCOUNT_SESSION_KIND_KEY] = "customer"
        self._set_demo_session_metadata(request=request, return_url=return_url)
        return {"result": "demo-session-authenticated", "profile": "customer", "redirect_url": "/"}

    def _set_demo_session_metadata(self, *, request, return_url: object = "") -> None:
        request.session[DEMO_SESSION_SOURCE_KEY] = "public-demo"
        normalized_return_url = str(return_url or "").strip()
        if normalized_return_url:
            request.session[DEMO_SESSION_RETURN_URL_KEY] = normalized_return_url
        else:
            request.session.pop(DEMO_SESSION_RETURN_URL_KEY, None)

    def _active_user(self, *, email: str):
        user_model = get_user_model()
        return user_model.objects.filter(email__iexact=email, is_active=True).first()

    def _is_demo_tenant(self, tenant) -> bool:
        return bool(
            tenant is not None
            and getattr(tenant, "is_active", False)
            and str(getattr(tenant, "subdomain", "") or "").strip().lower() == _demo_tenant_subdomain()
        )


demo_session_login_commands = DemoSessionLoginCommandService()
