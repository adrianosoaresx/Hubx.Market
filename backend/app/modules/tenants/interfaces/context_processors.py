from __future__ import annotations

from app.modules.tenants.domain.branding_colors import conversion_theme_inline_style


def tenant_branding_context(request) -> dict[str, object]:
    tenant = getattr(request, "tenant", None)
    if tenant is None:
        return {"tenant_branding_style": ""}
    return {
        "tenant_branding_style": conversion_theme_inline_style(
            getattr(tenant, "conversion_primary_color", "")
        )
    }
