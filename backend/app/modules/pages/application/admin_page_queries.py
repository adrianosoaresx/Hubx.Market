from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection
from django.utils import timezone


STATUS_OPTIONS = [
    {"value": "", "label": "Todos"},
    {"value": "draft", "label": "Rascunho"},
    {"value": "published", "label": "Publicado"},
]

PAGE_STATUS_OPTIONS = [
    {"value": "draft", "label": "Rascunho"},
    {"value": "published", "label": "Publicado"},
]


def _string(value: object) -> str:
    return str(value or "").strip()


def _format_datetime(value: object) -> str:
    if not value:
        return "Ainda não publicado"
    try:
        return timezone.localtime(value).strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(value)


class AdminPageReadRepository(Protocol):
    def list_pages(self, *, tenant_id: int | str | None) -> list[object]:
        ...

    def get_page(self, *, tenant_id: int | str | None, page_id: int | str | None) -> object | None:
        ...


class DjangoOrmAdminPageRepository:
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

    def list_pages(self, *, tenant_id: int | str | None) -> list[object]:
        if not tenant_id or not self.is_ready():
            return []
        return list(self.page_model._default_manager.filter(tenant_id=tenant_id).order_by("title", "id")[:200])

    def get_page(self, *, tenant_id: int | str | None, page_id: int | str | None) -> object | None:
        if not tenant_id or not page_id or not self.is_ready():
            return None
        return self.page_model._default_manager.filter(tenant_id=tenant_id, pk=page_id).first()


def _serialize_page(page: object) -> dict[str, object]:
    status = _string(getattr(page, "status", ""))
    status_label = "Publicado" if status == "published" else "Rascunho"
    return {
        "id": getattr(page, "id", None),
        "slug": _string(getattr(page, "slug", "")),
        "title": _string(getattr(page, "title", "")) or "Página sem título",
        "body": _string(getattr(page, "body", "")),
        "status": status,
        "status_label": status_label,
        "seo_title": _string(getattr(page, "seo_title", "")),
        "seo_description": _string(getattr(page, "seo_description", "")),
        "published_at": _format_datetime(getattr(page, "published_at", None)),
        "updated_at": _format_datetime(getattr(page, "updated_at", None)),
    }


@dataclass
class AdminPageQueryService:
    repository: AdminPageReadRepository

    def list_pages(self, *, tenant_id: int | str | None) -> list[dict[str, object]]:
        return [_serialize_page(page) for page in self.repository.list_pages(tenant_id=tenant_id)]

    def get_page(self, *, tenant_id: int | str | None, page_id: int | str | None) -> dict[str, object] | None:
        page = self.repository.get_page(tenant_id=tenant_id, page_id=page_id)
        if page is None:
            return None
        return _serialize_page(page)

    def get_form_initial(self, *, page: dict[str, object] | None = None) -> dict[str, object]:
        if not page:
            return {
                "title": "",
                "slug": "",
                "status_selected": "draft",
                "body": "",
                "seo_title": "",
                "seo_description": "",
            }
        return {
            "title": page.get("title", ""),
            "slug": page.get("slug", ""),
            "status_selected": page.get("status", "draft"),
            "body": page.get("body", ""),
            "seo_title": page.get("seo_title", ""),
            "seo_description": page.get("seo_description", ""),
        }


admin_page_queries = AdminPageQueryService(repository=DjangoOrmAdminPageRepository())
