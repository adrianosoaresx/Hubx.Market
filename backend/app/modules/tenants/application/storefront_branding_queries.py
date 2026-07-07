from __future__ import annotations

from dataclasses import dataclass

from app.modules.tenants.models import Tenant


DEFAULT_HERO_DESCRIPTION = (
    "Explore novidades, itens essenciais e combinações selecionadas pela loja, "
    "com compra segura e disponibilidade clara desde o primeiro clique."
)


@dataclass(frozen=True)
class StorefrontHeroDefaults:
    catalog_href: str = "/catalog/"
    newsletter_href: str = "/newsletter/"
    fallback_image_url: str = ""


class StorefrontBrandingQueryService:
    def get_home_hero(self, *, tenant: Tenant, defaults: StorefrontHeroDefaults | None = None) -> dict[str, object]:
        defaults = defaults or StorefrontHeroDefaults()
        if not getattr(tenant, "storefront_hero_enabled", True):
            return {"enabled": False}

        title = _clean_text(getattr(tenant, "storefront_hero_title", "")) or str(getattr(tenant, "name", "") or "Loja")
        description = _clean_text(getattr(tenant, "storefront_hero_description", "")) or DEFAULT_HERO_DESCRIPTION
        image_url = _clean_text(getattr(tenant, "storefront_hero_image_url", "")) or defaults.fallback_image_url
        primary_href = _safe_storefront_href(
            getattr(tenant, "storefront_hero_cta_href", ""),
            default=defaults.catalog_href,
        )

        return {
            "enabled": True,
            "title": title,
            "description": description,
            "image_url": image_url,
            "primary_label": _clean_text(getattr(tenant, "storefront_hero_cta_label", "")) or "Ver produtos",
            "primary_href": primary_href,
            "secondary_label": "Receber novidades",
            "secondary_href": defaults.newsletter_href,
            "badges": ("Frete transparente", "Produtos selecionados", "Atendimento pela loja"),
        }


def _clean_text(value: object) -> str:
    return str(value or "").strip()


def _safe_storefront_href(value: object, *, default: str) -> str:
    href = _clean_text(value)
    if href.startswith("/") and not href.startswith("//"):
        return href
    return default


storefront_branding_queries = StorefrontBrandingQueryService()
