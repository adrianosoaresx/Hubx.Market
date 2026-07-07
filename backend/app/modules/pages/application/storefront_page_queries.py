from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection


FOOTER_LINK_ICON_BY_SLUG = {
    "sobre-a-loja": "file-text",
    "trocas-e-devolucoes": "rotate-ccw",
    "politica-de-privacidade": "shield",
    "termos-de-uso": "scroll-text",
    "termos": "scroll-text",
    "contato": "mail",
}

FOOTER_LINK_SLUG_ORDER = (
    "sobre-a-loja",
    "trocas-e-devolucoes",
    "politica-de-privacidade",
    "termos-de-uso",
    "termos",
    "contato",
)


def _string(value: object) -> str:
    return str(value or "").strip()


class StorefrontPageReadRepository(Protocol):
    def get_published_page(self, *, tenant_id: int | str | None, slug: str) -> object | None:
        ...

    def list_published_pages(self, *, tenant_id: int | str | None) -> list[object]:
        ...


class DjangoOrmStorefrontPageRepository:
    def __init__(self) -> None:
        try:
            from app.modules.pages.models import Page
        except Exception:
            self.page_model = None
            return
        self.page_model = Page

    def is_ready(self) -> bool:
        try:
            table_name = self.page_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                return table_name in set(connection.introspection.table_names(cursor))
        except Exception:
            return False

    def get_published_page(self, *, tenant_id: int | str | None, slug: str) -> object | None:
        if not tenant_id or not slug or not self.is_ready():
            return None
        return self.page_model._default_manager.filter(
            tenant_id=tenant_id,
            slug=slug,
            status=self.page_model.Status.PUBLISHED,
        ).first()

    def list_published_pages(self, *, tenant_id: int | str | None) -> list[object]:
        if not tenant_id or not self.is_ready():
            return []
        return list(
            self.page_model._default_manager.filter(
                tenant_id=tenant_id,
                status=self.page_model.Status.PUBLISHED,
            ).order_by("title", "id")[:50]
        )


@dataclass
class StorefrontPageQueryService:
    repository: StorefrontPageReadRepository

    def get_published_page(self, *, tenant_id: int | str | None, slug: str) -> dict[str, object] | None:
        page = self.repository.get_published_page(tenant_id=tenant_id, slug=slug)
        if page is None:
            return None
        return {
            "id": getattr(page, "id", None),
            "slug": _string(getattr(page, "slug", "")),
            "title": _string(getattr(page, "title", "")),
            "body": _string(getattr(page, "body", "")),
            "seo_title": _string(getattr(page, "seo_title", "")) or _string(getattr(page, "title", "")),
            "seo_description": _string(getattr(page, "seo_description", "")),
        }

    def list_footer_links(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        pages = [_serialize_footer_page(page) for page in self.repository.list_published_pages(tenant_id=tenant_id)]
        pages.sort(key=_footer_sort_key)
        return pages[:8]


def _serialize_footer_page(page: object) -> dict[str, object]:
    slug = _string(getattr(page, "slug", ""))
    return {
        "href": f"/pages/{slug}/",
        "label": _string(getattr(page, "title", "")) or "Página",
        "slug": slug,
        "icon": FOOTER_LINK_ICON_BY_SLUG.get(slug, "file-text"),
    }


def _footer_sort_key(page: dict[str, object]) -> tuple[int, str]:
    slug = _string(page.get("slug"))
    if slug in FOOTER_LINK_SLUG_ORDER:
        return (FOOTER_LINK_SLUG_ORDER.index(slug), _string(page.get("label")).lower())
    return (len(FOOTER_LINK_SLUG_ORDER), _string(page.get("label")).lower())


storefront_page_queries = StorefrontPageQueryService(repository=DjangoOrmStorefrontPageRepository())
