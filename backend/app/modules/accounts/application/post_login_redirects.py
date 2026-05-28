from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.admin_permissions import PERMISSION_PLATFORM_TENANTS_VIEW, admin_permissions
from app.modules.accounts.models import AccountProfile, OwnerUser


def _root_domain() -> str:
    return str(getattr(settings, "HUBX_MARKET_ROOT_DOMAIN", "hubx.market") or "hubx.market").strip().lower()


def _platform_tenant_slug() -> str:
    return str(getattr(settings, "HUBX_PLATFORM_TENANT_SLUG", "platform-system") or "platform-system").strip().lower()


def _public_port() -> str:
    port = str(getattr(settings, "HUBX_MARKET_PUBLIC_PORT", "") or "").strip()
    return f":{port}" if port else ""


def _store_url(subdomain: str, path: str = "/ops/") -> str:
    root_domain = _root_domain()
    normalized_subdomain = str(subdomain or "").strip().lower()
    normalized_path = path if str(path or "").startswith("/") else f"/{path}"
    return f"http://{normalized_subdomain}.{root_domain}{_public_port()}{normalized_path}"


@dataclass(frozen=True)
class PostLoginRedirectDecision:
    result: str
    url: str


@dataclass
class PostLoginRedirectService:
    def get_owner_login_tenant_id(self, *, email: object, next_url: object = "") -> int | None:
        normalized_email = self._normalize(email)
        if not normalized_email:
            return None
        owners = self._owner_candidates(email=normalized_email)
        if not owners:
            return None
        if str(next_url or "").startswith("/ops/platform/"):
            platform_owner = self._platform_owner(owners=owners)
            return platform_owner.tenant_id if platform_owner is not None else None
        if len(owners) == 1:
            return owners[0].tenant_id
        return self._platform_owner(owners=owners).tenant_id if self._platform_owner(owners=owners) else owners[0].tenant_id

    def decide_owner_redirect(self, *, email: object, safe_next_url: str = "") -> PostLoginRedirectDecision:
        normalized_email = self._normalize(email)
        owners = self._owner_candidates(email=normalized_email)
        platform_owner = self._platform_owner(owners=owners)
        if safe_next_url.startswith("/ops/platform/") and platform_owner is not None:
            return PostLoginRedirectDecision(result="platform-next", url=safe_next_url)
        if platform_owner is not None:
            return PostLoginRedirectDecision(result="platform-admin", url="/ops/platform/tenants/")
        if len(owners) == 1:
            return PostLoginRedirectDecision(result="single-store-owner", url=_store_url(owners[0].tenant.subdomain, "/ops/"))
        if len(owners) > 1:
            return PostLoginRedirectDecision(result="store-selection-required", url="/accounts/select-store/")
        return PostLoginRedirectDecision(result="owner-not-found", url="/accounts/login/")

    def list_owner_store_choices(self, *, email: object) -> list[dict[str, object]]:
        normalized_email = self._normalize(email)
        return [
            {
                "tenant_id": owner.tenant_id,
                "name": owner.tenant.name,
                "slug": owner.tenant.slug,
                "subdomain": owner.tenant.subdomain,
                "role": owner.role,
                "ops_url": _store_url(owner.tenant.subdomain, "/ops/"),
                "storefront_url": _store_url(owner.tenant.subdomain, "/"),
            }
            for owner in self._owner_candidates(email=normalized_email)
        ]

    def decide_customer_redirect(self, *, email: object, safe_next_url: str = "") -> PostLoginRedirectDecision:
        normalized_email = self._normalize(email)
        profiles = list(
            AccountProfile.objects.filter(email__iexact=normalized_email, is_active=True)
            .select_related("tenant")
            .order_by("tenant_id", "id")
        )
        if safe_next_url and not safe_next_url.startswith("/ops/"):
            return PostLoginRedirectDecision(result="customer-next", url=safe_next_url)
        if len(profiles) == 1:
            return PostLoginRedirectDecision(result="single-store-customer", url=_store_url(profiles[0].tenant.subdomain, "/accounts/account/"))
        return PostLoginRedirectDecision(result="customer-account", url="/accounts/account/")

    def _owner_candidates(self, *, email: str) -> list[OwnerUser]:
        return list(
            OwnerUser.objects.filter(email__iexact=email, is_active=True, tenant__is_active=True)
            .select_related("tenant")
            .order_by("tenant_id", "id")
        )

    def _platform_owner(self, *, owners: list[OwnerUser]) -> OwnerUser | None:
        platform_owners = [
            owner
            for owner in owners
            if str(getattr(owner.tenant, "slug", "") or "").strip().lower() == _platform_tenant_slug()
            and admin_permissions.check(role=owner.role, permission=PERMISSION_PLATFORM_TENANTS_VIEW).allowed
        ]
        if not platform_owners:
            return None
        return sorted(platform_owners, key=lambda owner: (0 if owner.role == "owner" else 1, owner.tenant_id, owner.id))[0]

    def _normalize(self, value: object) -> str:
        return str(value or "").strip().lower()


post_login_redirects = PostLoginRedirectService()
