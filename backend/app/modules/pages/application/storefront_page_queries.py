from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection


def _string(value: object) -> str:
    return str(value or "").strip()


class StorefrontPageReadRepository(Protocol):
    def get_published_page(self, *, tenant_id: int | str | None, slug: str) -> object | None:
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


storefront_page_queries = StorefrontPageQueryService(repository=DjangoOrmStorefrontPageRepository())
