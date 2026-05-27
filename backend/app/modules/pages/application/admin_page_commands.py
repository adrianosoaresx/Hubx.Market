from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db import connection
from django.utils import timezone
from django.utils.text import slugify

from app.modules.accounts.application.admin_permissions import PERMISSION_PAGES_MANAGE, admin_permissions
from app.modules.audit.application.audit_log_commands import audit_log_commands


def _string(value: object) -> str:
    return str(value or "").strip()


def _page_slug(value: object, *, fallback: object = "") -> str:
    raw_slug = _string(value) or _string(fallback)
    return slugify(raw_slug)[:160]


class AdminPageCommandRepository(Protocol):
    def create_page(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        ...

    def update_page(
        self,
        *,
        tenant_id: int | str | None,
        page_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        ...


class DjangoOrmAdminPageCommandRepository:
    def __init__(self) -> None:
        try:
            from app.modules.pages.models import Page
            from app.modules.tenants.models import Tenant
        except Exception:
            self.page_model = None
            self.tenant_model = None
            return
        self.page_model = Page
        self.tenant_model = Tenant

    def is_ready(self) -> bool:
        try:
            table_names = {self.page_model._meta.db_table, self.tenant_model._meta.db_table}
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = set(connection.introspection.table_names(cursor))
        except Exception:
            return False
        return table_names.issubset(tables)

    def create_page(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_PAGES_MANAGE)
        if not permission.allowed:
            return {
                "result": "page-permission-denied",
                "errors": {"__all__": "Permissão insuficiente para gerenciar páginas."},
            }
        tenant = self._tenant(tenant_id)
        if tenant is None:
            return {"result": "page-tenant-required", "errors": {"__all__": "Tenant obrigatório para criar página."}}
        values, errors = self._validated_values(tenant_id=tenant.id, payload=payload)
        if errors:
            return {"result": "page-invalid", "errors": errors}
        page = self.page_model._default_manager.create(tenant=tenant, **values)
        self._record_page_event(page=page, action="page.created", summary=f"Página {page.slug} criada", actor_label=actor_label)
        return {"result": "page-created", "page": {"id": page.id, "slug": page.slug}}

    def update_page(
        self,
        *,
        tenant_id: int | str | None,
        page_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_PAGES_MANAGE)
        if not permission.allowed:
            return {
                "result": "page-permission-denied",
                "errors": {"__all__": "Permissão insuficiente para gerenciar páginas."},
            }
        if not tenant_id or not page_id or not self.is_ready():
            return {"result": "page-not-found", "errors": {"__all__": "Página não encontrada para este tenant."}}
        page = self.page_model._default_manager.filter(tenant_id=tenant_id, pk=page_id).first()
        if page is None:
            return {"result": "page-not-found", "errors": {"__all__": "Página não encontrada para este tenant."}}
        values, errors = self._validated_values(tenant_id=tenant_id, payload=payload, current_page_id=page.id)
        if errors:
            return {"result": "page-invalid", "errors": errors}
        for field_name, value in values.items():
            setattr(page, field_name, value)
        page.save(update_fields=[*values.keys(), "updated_at"])
        self._record_page_event(page=page, action="page.updated", summary=f"Página {page.slug} atualizada", actor_label=actor_label)
        return {"result": "page-updated", "page": {"id": page.id, "slug": page.slug}}

    def _record_page_event(self, *, page, action: str, summary: str, actor_label: str = "") -> None:
        audit_log_commands.record_event(
            tenant_id=page.tenant_id,
            module="pages",
            action=action,
            entity_type="Page",
            entity_id=str(page.id),
            actor_label=actor_label,
            summary=summary,
            metadata={
                "slug": page.slug,
                "status": page.status,
                "title": page.title,
            },
        )

    def _tenant(self, tenant_id: int | str | None):
        if not tenant_id or not self.is_ready():
            return None
        return self.tenant_model._default_manager.filter(pk=tenant_id).first()

    def _validated_values(
        self,
        *,
        tenant_id: int | str,
        payload: dict[str, object],
        current_page_id: int | None = None,
    ) -> tuple[dict[str, object], dict[str, str]]:
        title = _string(payload.get("title"))[:180]
        slug = _page_slug(payload.get("slug"), fallback=title)
        status = _string(payload.get("status")) or self.page_model.Status.DRAFT
        body = _string(payload.get("body"))
        seo_title = _string(payload.get("seo_title"))[:180]
        seo_description = _string(payload.get("seo_description"))[:300]
        errors: dict[str, str] = {}

        if not title:
            errors["title"] = "Informe o título da página."
        if not slug:
            errors["slug"] = "Informe um slug ou título válido."
        if status not in {self.page_model.Status.DRAFT, self.page_model.Status.PUBLISHED}:
            errors["status"] = "Status inválido."

        duplicate = self.page_model._default_manager.filter(tenant_id=tenant_id, slug=slug)
        if current_page_id:
            duplicate = duplicate.exclude(pk=current_page_id)
        if slug and duplicate.exists():
            errors["slug"] = "Já existe uma página com este slug neste tenant."

        published_at = None
        if status == self.page_model.Status.PUBLISHED:
            existing = None
            if current_page_id:
                existing = self.page_model._default_manager.filter(pk=current_page_id).first()
            published_at = getattr(existing, "published_at", None) or timezone.now()

        return (
            {
                "title": title,
                "slug": slug,
                "status": status,
                "body": body,
                "seo_title": seo_title,
                "seo_description": seo_description,
                "published_at": published_at,
            },
            errors,
        )


@dataclass
class AdminPageCommandService:
    repository: AdminPageCommandRepository

    def create_page(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        return self.repository.create_page(
            tenant_id=tenant_id,
            payload=payload,
            actor_label=actor_label,
            actor_role=actor_role,
        )

    def update_page(
        self,
        *,
        tenant_id: int | str | None,
        page_id: int | str | None,
        payload: dict[str, object],
        actor_label: str = "",
        actor_role: str = "",
    ) -> dict[str, object]:
        return self.repository.update_page(
            tenant_id=tenant_id,
            page_id=page_id,
            payload=payload,
            actor_label=actor_label,
            actor_role=actor_role,
        )


admin_page_commands = AdminPageCommandService(repository=DjangoOrmAdminPageCommandRepository())
