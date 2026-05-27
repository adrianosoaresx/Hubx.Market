from __future__ import annotations

from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import PERMISSION_PAGES_MANAGE
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.pages.application.admin_page_commands import admin_page_commands
from app.modules.pages.application.admin_page_queries import PAGE_STATUS_OPTIONS, STATUS_OPTIONS, admin_page_queries
from app.modules.pages.application.storefront_page_queries import storefront_page_queries


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _request_owner_role(request) -> str:
    return request_owner_role(request)


def _edit_link(page: dict[str, object], *, can_manage: bool) -> str:
    if not can_manage:
        return "Sem permissão para editar"
    return format_html(
        '<a class="ds-btn-secondary" href="{}">Editar</a>',
        reverse("pages:admin-pages-edit", kwargs={"page_id": page["id"]}),
    )


class AdminPagesListView(TemplateView):
    template_name = "pages/templates/admin_pages_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        can_manage_pages = request_admin_can(self.request, PERMISSION_PAGES_MANAGE)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        pages = admin_page_queries.list_pages(tenant_id=tenant_id)

        if search_value:
            lowered_search = search_value.lower()
            pages = [
                page
                for page in pages
                if lowered_search in str(page["title"]).lower()
                or lowered_search in str(page["slug"]).lower()
                or lowered_search in str(page["seo_description"]).lower()
            ]
        if status_selected:
            pages = [page for page in pages if page["status"] == status_selected]

        empty_title = "Nenhuma página encontrada"
        empty_description = "Crie páginas institucionais simples para este tenant."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para listar páginas tenant-scoped."

        context.update(
            {
                "page_title": "Páginas",
                "page_eyebrow": "Conteúdo & SEO",
                "page_description": "Gerencie páginas institucionais tenant-scoped sem page builder avançado.",
                "create_href": reverse("pages:admin-pages-create") if can_manage_pages else "",
                "filter_action": reverse("pages:admin-pages-list"),
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar páginas",
                "search_placeholder": "Título, slug ou SEO",
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": reverse("pages:admin-pages-list"),
                "columns": [
                    {"label": "Título"},
                    {"label": "Slug"},
                    {"label": "Status"},
                    {"label": "Publicado em"},
                    {"label": "Atualização"},
                    {"label": "Ação"},
                ],
                "rows": [
                    {
                        "cells": [
                            page["title"],
                            f'/pages/{page["slug"]}/',
                            page["status_label"],
                            page["published_at"],
                            page["updated_at"],
                            _edit_link(page, can_manage=can_manage_pages),
                        ]
                    }
                    for page in pages
                ],
                "table_count": f"{len(pages)} página(s)",
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


class AdminPageFormView(TemplateView):
    template_name = "pages/templates/admin_page_form_page.html"

    def _page_id(self) -> int | None:
        return self.kwargs.get("page_id")

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None):
        page = admin_page_queries.get_page(tenant_id=_request_tenant_id(self.request), page_id=self._page_id())
        initial = admin_page_queries.get_form_initial(page=page)
        if values:
            initial.update(
                {
                    "title": values.get("title", initial["title"]),
                    "slug": values.get("slug", initial["slug"]),
                    "status_selected": values.get("status", initial["status_selected"]),
                    "body": values.get("body", initial["body"]),
                    "seo_title": values.get("seo_title", initial["seo_title"]),
                    "seo_description": values.get("seo_description", initial["seo_description"]),
                }
            )
        is_edit = self._page_id() is not None
        return {
            "page_title": "Editar página" if is_edit else "Nova página",
            "page_eyebrow": "Conteúdo & SEO",
            "page_description": "Publique conteúdo institucional simples por tenant. Rascunhos não aparecem no storefront.",
            "form_action": self.request.path,
            "cancel_href": reverse("pages:admin-pages-list"),
            "status_options": PAGE_STATUS_OPTIONS,
            "submit_label": "Salvar página" if is_edit else "Criar página",
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            **initial,
        }

    def get_context_data(self, **kwargs):
        if self._page_id() is not None and not admin_page_queries.get_page(
            tenant_id=_request_tenant_id(self.request),
            page_id=self._page_id(),
        ):
            raise Http404("Page not found")
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        actor_label = str(getattr(request, "user", "") or "")
        if self._page_id() is None:
            result = admin_page_commands.create_page(
                tenant_id=_request_tenant_id(request),
                payload=request.POST,
                actor_label=actor_label,
                actor_role=_request_owner_role(request),
            )
            success_result = "page-created"
        else:
            result = admin_page_commands.update_page(
                tenant_id=_request_tenant_id(request),
                page_id=self._page_id(),
                payload=request.POST,
                actor_label=actor_label,
                actor_role=_request_owner_role(request),
            )
            success_result = "page-updated"
        if result.get("result") == success_result:
            return HttpResponseRedirect(reverse("pages:admin-pages-list"))
        context = self.get_context_data(**kwargs)
        context.update(self._context(values=request.POST, errors=result.get("errors") or {}))
        return self.render_to_response(context, status=400)


class StorefrontPageDetailView(TemplateView):
    template_name = "pages/templates/storefront_page.html"

    def get_context_data(self, **kwargs):
        tenant_id = _request_tenant_id(self.request)
        page = storefront_page_queries.get_published_page(
            tenant_id=tenant_id,
            slug=kwargs.get("page_slug", ""),
        )
        if page is None:
            raise Http404("Page not found")
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "page": page,
                "page_title": page["seo_title"] or page["title"],
                "meta_description": page["seo_description"],
            }
        )
        return context
