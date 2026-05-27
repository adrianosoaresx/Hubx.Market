from __future__ import annotations

from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import PERMISSION_API_KEYS_VIEW
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_tenant_id
from app.modules.api_keys.application.api_key_quota_queries import api_key_quota_queries


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
