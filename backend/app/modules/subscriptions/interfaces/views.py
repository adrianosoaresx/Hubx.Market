from __future__ import annotations

from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import PERMISSION_SUBSCRIPTIONS_VIEW
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_tenant_id
from app.modules.subscriptions.application.subscription_queries import subscription_queries


class AdminSubscriptionsListView(TemplateView):
    template_name = "pages/templates/admin_subscriptions_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = request_tenant_id(self.request)
        can_view = request_admin_can(self.request, PERMISSION_SUBSCRIPTIONS_VIEW)
        subscriptions = subscription_queries.list_tenant_subscriptions(tenant_id=tenant_id) if can_view else []
        context.update(
            {
                "page_title": "Assinatura SaaS",
                "page_eyebrow": "Platform billing",
                "page_description": "Leitura tenant-scoped do plano SaaS sem cobrança provider acoplada.",
                "columns": [
                    {"label": "Tenant"},
                    {"label": "Plano"},
                    {"label": "Status"},
                    {"label": "Mensalidade"},
                    {"label": "Período"},
                    {"label": "Referência"},
                ],
                "rows": [
                    {
                        "cells": [
                            item["tenant_name"],
                            f'{item["plan_name"]} ({item["plan_code"]})',
                            item["status_label"],
                            item["monthly_price"],
                            item["current_period_ends_at"],
                            item["external_reference"],
                        ]
                    }
                    for item in subscriptions
                ],
                "table_count": f"{len(subscriptions)} assinatura(s)",
                "empty_title": "Nenhuma assinatura SaaS",
                "empty_description": "Crie o estado de assinatura por service/command antes de ativar enforcement.",
            }
        )
        return context
