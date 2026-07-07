from __future__ import annotations

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic import View

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_API_KEYS_MANAGE,
    PERMISSION_API_KEYS_VIEW,
)
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.api_keys.application.admin_api_key_queries import admin_api_key_queries
from app.modules.api_keys.application.api_key_commands import api_key_commands
from app.modules.api_keys.application.api_key_quota_queries import api_key_quota_queries


def _actor_label(request) -> str:
    owner = getattr(request, "owner_user", None)
    owner_email = str(getattr(owner, "email", "") or "").strip()
    if owner_email:
        return owner_email
    user = getattr(request, "user", None)
    return str(getattr(user, "email", "") or getattr(user, "username", "") or "ops-admin").strip()


def _owner_id(request):
    owner = getattr(request, "owner_user", None)
    return getattr(owner, "id", None)


def _can_manage_api_keys(request) -> bool:
    return bool(request_owner_role(request)) and request_admin_can(request, PERMISSION_API_KEYS_MANAGE)


def _feedback(value: object) -> dict[str, str]:
    status = str(value or "").strip()
    mapping = {
        "created": (
            "success",
            "API key criada",
            "Copie o segredo agora. Ele não será exibido novamente.",
        ),
        "revoked": (
            "success",
            "API key revogada",
            "A chave foi revogada e o histórico foi preservado.",
        ),
        "permission-denied": (
            "danger",
            "Permissão necessária",
            "Seu perfil pode visualizar API keys, mas não gerenciá-las.",
        ),
        "tenant-required": (
            "warning",
            "Tenant não resolvido",
            "Acesse esta tela pelo subdomínio da loja para gerenciar API keys.",
        ),
        "not-found": (
            "warning",
            "Chave não encontrada",
            "A API key não existe neste tenant ou já foi removida da visão atual.",
        ),
        "already-revoked": ("info", "API key já revogada", "Nenhuma alteração adicional foi necessária."),
        "unavailable": (
            "warning",
            "API keys indisponíveis",
            "A estrutura de API keys ainda não está pronta neste ambiente.",
        ),
    }
    variant, title, description = mapping.get(status, ("info", "", ""))
    return {"variant": variant, "title": title, "description": description} if title else {}


def _form_value(source, key: str, default: str = "") -> str:
    return str(source.get(key, default) or default).strip()


class AdminApiKeyQuotaListView(TemplateView):
    template_name = "pages/templates/admin_api_key_quotas_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = request_tenant_id(self.request)
        can_view_api_keys = request_admin_can(self.request, PERMISSION_API_KEYS_VIEW)
        quotas = api_key_quota_queries.list_quotas(tenant_id=tenant_id) if can_view_api_keys else []
        empty_title = "Nenhuma quota configurada"
        empty_description = "Crie quotas por API key via serviço interno antes de ativar enforcement comercial."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para listar quotas tenant-scoped."
        elif not can_view_api_keys:
            empty_title = "Permissão necessária"
            empty_description = "Seu perfil não possui permissão para visualizar quotas de API keys."

        context.update(
            {
                "page_title": "Quotas de API keys",
                "page_eyebrow": "API pública",
                "page_description": "Visibilidade read-only de quotas comerciais por tenant, API key, endpoint e janela.",
                "columns": [
                    {"label": "API key"},
                    {"label": "Prefixo"},
                    {"label": "Endpoint"},
                    {"label": "Escopo"},
                    {"label": "Status"},
                    {"label": "Uso"},
                    {"label": "Janela"},
                    {"label": "Atualização"},
                ],
                "rows": [
                    {
                        "cells": [
                            quota["api_key_name"],
                            quota["prefix"],
                            quota["endpoint"],
                            quota["scope"],
                            quota["status_label"],
                            quota["usage_label"],
                            quota["window_label"],
                            quota["updated_at"],
                        ]
                    }
                    for quota in quotas
                ],
                "table_count": f"{len(quotas)} quota(s)",
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


class AdminApiKeyListView(TemplateView):
    template_name = "pages/templates/admin_api_keys_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._page_context())
        return context

    def _page_context(
        self,
        *,
        form_data=None,
        errors=None,
        created_secret: str = "",
        feedback=None,
    ) -> dict[str, object]:
        tenant_id = request_tenant_id(self.request)
        can_view_api_keys = request_admin_can(self.request, PERMISSION_API_KEYS_VIEW)
        can_manage_api_keys = _can_manage_api_keys(self.request)
        api_keys = admin_api_key_queries.list_keys(tenant_id=tenant_id) if can_view_api_keys else []
        empty_title = "Nenhuma API key criada"
        empty_description = "Crie a primeira chave para integrações aprovadas deste tenant."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para listar API keys tenant-scoped."
        elif not can_view_api_keys:
            empty_title = "Permissão necessária"
            empty_description = "Seu perfil não possui permissão para visualizar API keys."
        elif not can_manage_api_keys:
            empty_description = "Seu perfil pode auditar chaves, mas não criar ou revogar API keys."

        return {
            "page_title": "API keys",
            "page_eyebrow": "Governança",
            "page_description": "Criação, revogação e auditoria tenant-scoped de chaves da API pública.",
            "page_actions": [
                {"href": reverse("api_keys_ops:admin-api-key-quotas-list"), "label": "Ver quotas"},
            ],
            "api_keys": api_keys,
            "table_count": f"{len(api_keys)} chave(s)",
            "empty_title": empty_title,
            "empty_description": empty_description,
            "can_manage_api_keys": can_manage_api_keys and bool(tenant_id),
            "created_secret": created_secret,
            "feedback": feedback or _feedback(self.request.GET.get("status")),
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            "form": {
                "name": _form_value(form_data or {}, "name"),
                "scopes": _form_value(form_data or {}, "scopes", "read:catalog"),
            },
        }


class AdminApiKeyCreateView(View):
    template_name = "pages/templates/admin_api_keys_page.html"

    def post(self, request, *args, **kwargs):
        tenant_id = request_tenant_id(request)
        if not tenant_id:
            return self._render(form_data=request.POST, feedback=_feedback("tenant-required"))
        if not _can_manage_api_keys(request):
            return self._render(form_data=request.POST, feedback=_feedback("permission-denied"), status=403)
        result = api_key_commands.create_key(
            tenant_id=tenant_id,
            name=request.POST.get("name"),
            scopes=request.POST.get("scopes"),
            owner_id=_owner_id(request),
            actor_label=_actor_label(request),
        )
        if result.get("result") == "api-key-created":
            return self._render(
                created_secret=str(result.get("secret") or ""),
                feedback=_feedback("created"),
            )
        if result.get("result") == "api-key-tenant-required":
            feedback = _feedback("tenant-required")
        elif result.get("result") == "api-key-unavailable":
            feedback = _feedback("unavailable")
        else:
            feedback = {
                "variant": "danger",
                "title": "Não foi possível criar a API key",
                "description": "Revise os campos destacados e tente novamente.",
            }
        return self._render(form_data=request.POST, errors=result.get("errors") or {}, feedback=feedback, status=400)

    def _render(self, *, form_data=None, errors=None, created_secret: str = "", feedback=None, status: int = 200):
        view = AdminApiKeyListView()
        view.setup(self.request)
        context = view._page_context(
            form_data=form_data,
            errors=errors,
            created_secret=created_secret,
            feedback=feedback,
        )
        return render(self.request, self.template_name, context=context, status=status)


class AdminApiKeyRevokeView(View):
    def post(self, request, *args, **kwargs):
        tenant_id = request_tenant_id(request)
        if not tenant_id:
            return HttpResponseRedirect(f'{reverse("api_keys_ops:admin-api-keys-list")}?status=tenant-required')
        if not _can_manage_api_keys(request):
            return HttpResponseRedirect(f'{reverse("api_keys_ops:admin-api-keys-list")}?status=permission-denied')
        result = api_key_commands.revoke_key(
            tenant_id=tenant_id,
            key_id=kwargs.get("key_id"),
            actor_label=_actor_label(request),
        )
        result_status = {
            "api-key-revoked": "revoked",
            "api-key-already-revoked": "already-revoked",
            "api-key-not-found": "not-found",
            "api-key-tenant-required": "tenant-required",
            "api-key-unavailable": "unavailable",
        }.get(str(result.get("result") or ""), "not-found")
        return HttpResponseRedirect(f'{reverse("api_keys_ops:admin-api-keys-list")}?status={result_status}')
