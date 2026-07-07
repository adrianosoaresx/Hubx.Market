from __future__ import annotations

from app.modules.pages.application.storefront_page_queries import storefront_page_queries


def storefront_pages_context(request) -> dict[str, object]:
    path = str(getattr(request, "path", "") or "")
    if path == "/ops" or path.startswith("/ops/") or path.startswith("/__internal__/"):
        return {"storefront_footer_links": []}
    tenant = getattr(request, "tenant", None)
    tenant_id = getattr(tenant, "id", None)
    if not tenant_id:
        return {"storefront_footer_links": []}
    return {
        "storefront_footer_links": storefront_page_queries.list_footer_links(tenant_id=tenant_id),
    }
