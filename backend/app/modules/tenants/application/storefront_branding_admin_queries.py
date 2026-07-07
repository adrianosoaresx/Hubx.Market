from __future__ import annotations

from dataclasses import dataclass

from app.modules.tenants.models import Tenant


def _string(value: object) -> str:
    return str(value or "").strip()


@dataclass(frozen=True)
class StorefrontBrandingAdminQueryService:
    def get_form_initial(self, *, tenant: Tenant | None) -> dict[str, object]:
        if tenant is None:
            return {
                "logo_url": "",
                "conversion_primary_color": "",
                "storefront_hero_enabled": False,
                "storefront_hero_title": "",
                "storefront_hero_description": "",
                "storefront_hero_image_url": "",
                "storefront_hero_cta_label": "",
                "storefront_hero_cta_href": "",
            }
        return {
            "logo_url": _string(getattr(tenant, "logo_url", "")),
            "conversion_primary_color": _string(getattr(tenant, "conversion_primary_color", "")),
            "storefront_hero_enabled": bool(getattr(tenant, "storefront_hero_enabled", True)),
            "storefront_hero_title": _string(getattr(tenant, "storefront_hero_title", "")),
            "storefront_hero_description": _string(getattr(tenant, "storefront_hero_description", "")),
            "storefront_hero_image_url": _string(getattr(tenant, "storefront_hero_image_url", "")),
            "storefront_hero_cta_label": _string(getattr(tenant, "storefront_hero_cta_label", "")),
            "storefront_hero_cta_href": _string(getattr(tenant, "storefront_hero_cta_href", "")),
        }


storefront_branding_admin_queries = StorefrontBrandingAdminQueryService()
