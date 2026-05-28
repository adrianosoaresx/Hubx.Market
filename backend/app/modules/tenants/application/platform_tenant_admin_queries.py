from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.models import OwnerUser
from app.modules.tenants.models import Tenant


def _root_domain() -> str:
    return str(getattr(settings, "HUBX_MARKET_ROOT_DOMAIN", "hubx.market") or "hubx.market").strip().lower()


def _status_label(*, is_active: bool, maintenance_mode: bool) -> tuple[str, str]:
    if not is_active:
        return "Inativa", "danger"
    if maintenance_mode:
        return "Manutenção", "warning"
    return "Ativa", "success"


@dataclass
class PlatformTenantAdminQueryService:
    def _serialize_tenant(self, tenant: Tenant, *, root_domain: str) -> dict[str, object]:
        status_label, status_variant = _status_label(
            is_active=tenant.is_active,
            maintenance_mode=tenant.maintenance_mode,
        )
        return {
            "id": tenant.id,
            "name": tenant.name,
            "slug": tenant.slug,
            "subdomain": tenant.subdomain,
            "storefront_host": f"{tenant.subdomain}.{root_domain}",
            "storefront_url": f"https://{tenant.subdomain}.{root_domain}",
            "custom_domain": tenant.custom_domain or "—",
            "custom_domain_configured": bool(tenant.custom_domain),
            "is_active": tenant.is_active,
            "maintenance_mode": tenant.maintenance_mode,
            "status_label": status_label,
            "status_variant": status_variant,
            "created_at": tenant.created_at.strftime("%d/%m/%Y"),
            "updated_at": tenant.updated_at.strftime("%d/%m/%Y %H:%M"),
            "active_owner_count": OwnerUser.objects.filter(tenant=tenant, is_active=True).count(),
        }

    def list_tenants(self) -> list[dict[str, object]]:
        root_domain = _root_domain()
        return [
            self._serialize_tenant(tenant, root_domain=root_domain)
            for tenant in Tenant.objects.all().order_by("slug")
        ]

    def get_tenant(self, *, slug: str) -> dict[str, object] | None:
        normalized_slug = str(slug or "").strip()
        if not normalized_slug:
            return None
        tenant = Tenant.objects.filter(slug=normalized_slug).first()
        if tenant is None:
            return None
        return self._serialize_tenant(tenant, root_domain=_root_domain())

    def get_summary(self) -> dict[str, int]:
        tenants = list(Tenant.objects.only("is_active", "maintenance_mode"))
        return {
            "total": len(tenants),
            "active": sum(1 for tenant in tenants if tenant.is_active and not tenant.maintenance_mode),
            "maintenance": sum(1 for tenant in tenants if tenant.maintenance_mode),
            "inactive": sum(1 for tenant in tenants if not tenant.is_active),
        }


platform_tenant_admin_queries = PlatformTenantAdminQueryService()
