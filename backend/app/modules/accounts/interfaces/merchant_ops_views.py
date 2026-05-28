from __future__ import annotations

from django.http import HttpResponseRedirect
from django.utils.html import format_html, format_html_join
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_merchant_operations_queries import admin_merchant_operations_queries
from app.modules.accounts.application.admin_permissions import (
    PERMISSION_AUDIT_VIEW,
    PERMISSION_API_KEYS_VIEW,
    PERMISSION_CATALOG_VIEW,
    PERMISSION_COUPONS_MANAGE,
    PERMISSION_CUSTOMERS_VIEW,
    PERMISSION_NEWSLETTER_VIEW,
    PERMISSION_ORDERS_VIEW,
    PERMISSION_OWNERS_MANAGE,
    PERMISSION_PAGES_MANAGE,
    PERMISSION_PAYMENTS_VIEW,
    PERMISSION_PLATFORM_TENANTS_VIEW,
    PERMISSION_REVIEWS_MODERATE,
    PERMISSION_SHIPPING_VIEW,
    PERMISSION_SUBSCRIPTIONS_VIEW,
)
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


NAV_ITEMS = [
    {"label": "Pedidos", "href": "/ops/orders/", "permission": PERMISSION_ORDERS_VIEW},
    {"label": "Catálogo", "href": "/ops/catalog/products/", "permission": PERMISSION_CATALOG_VIEW},
    {"label": "Páginas", "href": "/ops/pages/", "permission": PERMISSION_PAGES_MANAGE},
    {"label": "Newsletter", "href": "/ops/newsletter/", "permission": PERMISSION_NEWSLETTER_VIEW},
    {"label": "Audit log", "href": "/ops/audit/", "permission": PERMISSION_AUDIT_VIEW},
    {"label": "API keys", "href": "/ops/api-keys/quotas/", "permission": PERMISSION_API_KEYS_VIEW},
    {"label": "Cupons", "href": "/ops/coupons/", "permission": PERMISSION_COUPONS_MANAGE},
    {"label": "Avaliações", "href": "/ops/reviews/", "permission": PERMISSION_REVIEWS_MODERATE},
    {"label": "Clientes", "href": "/ops/customers/", "permission": PERMISSION_CUSTOMERS_VIEW},
    {"label": "Financeiro", "href": "/ops/payments/finance/", "permission": PERMISSION_PAYMENTS_VIEW},
    {"label": "Refunds", "href": "/ops/payments/refunds/", "permission": PERMISSION_PAYMENTS_VIEW},
    {"label": "Owners", "href": "/ops/owners/", "permission": PERMISSION_OWNERS_MANAGE},
    {"label": "MFA owners", "href": "/ops/owners/mfa/", "permission": PERMISSION_OWNERS_MANAGE},
    {"label": "Assinatura", "href": "/ops/subscriptions/", "permission": PERMISSION_SUBSCRIPTIONS_VIEW},
    {"label": "Onboarding de lojas", "href": "/ops/platform/onboarding/", "permission": PERMISSION_PLATFORM_TENANTS_VIEW},
    {"label": "Lojas", "href": "/ops/platform/tenants/", "permission": PERMISSION_PLATFORM_TENANTS_VIEW},
]


TASK_PERMISSIONS = {
    "Pedidos": PERMISSION_ORDERS_VIEW,
    "Estoque": PERMISSION_ORDERS_VIEW,
    "Catálogo": PERMISSION_CATALOG_VIEW,
    "Clientes": PERMISSION_CUSTOMERS_VIEW,
    "Entregas": PERMISSION_SHIPPING_VIEW,
    "Owners": PERMISSION_OWNERS_MANAGE,
}


def _allowed_nav_items(request) -> list[dict[str, str]]:
    return [
        item
        for item in NAV_ITEMS
        if request_admin_can(request, str(item["permission"]))
        and (
            not str(item["href"]).startswith("/ops/platform/")
            or getattr(request, "tenant", None) is None
        )
    ]


def _dashboard_actions(items: list[dict[str, str]]) -> str:
    return format_html_join(
        "",
        '<a class="ds-btn-secondary" href="{}">{}</a>',
        ((item["href"], item["label"]) for item in items),
    )


def _filter_tasks_for_request(request, tasks: list[dict[str, object]]) -> list[dict[str, object]]:
    return [
        task
        for task in tasks
        if request_admin_can(request, TASK_PERMISSIONS.get(str(task.get("area") or ""), ""))
    ]


def _task_action_cell(task: dict[str, object]) -> str:
    return format_html('<a class="ds-btn-secondary" href="{}">{}</a>', task["href"], task["action"])


class MerchantOperationsDashboardView(TemplateView):
    template_name = "pages/templates/admin_dashboard_page.html"

    def get(self, request, *args, **kwargs):
        if getattr(request, "tenant", None) is None and request_admin_can(request, PERMISSION_PLATFORM_TENANTS_VIEW):
            return HttpResponseRedirect("/ops/platform/tenants/")
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        dashboard = admin_merchant_operations_queries.get_dashboard(tenant_id=_request_tenant_id(self.request))
        kpis = dashboard["kpis"]
        tasks = _filter_tasks_for_request(self.request, dashboard["tasks"])
        nav_items = _allowed_nav_items(self.request)
        activity_items = admin_merchant_operations_queries._build_activity_items(tasks)
        summary = admin_merchant_operations_queries._summary(tasks)

        context.update(
            {
                "page_title": "Operação da loja",
                "page_eyebrow": "Merchant operations",
                "page_description": "Cockpit operacional personalizado pelas permissões do owner/admin ativo.",
                "page_actions": _dashboard_actions(nav_items),
                "admin_nav_items": nav_items,
                "page_meta": f"Perfil operacional: {request_owner_role(self.request) or 'compatibilidade legada'}",
                "showcase_mode": False,
                "kpi_1_title": kpis[0]["title"],
                "kpi_1_description": kpis[0]["description"],
                "kpi_1_value": kpis[0]["value"],
                "kpi_1_delta": "atenção" if int(kpis[0]["value"]) else "ok",
                "kpi_1_trend": "negative" if int(kpis[0]["value"]) else "positive",
                "kpi_1_meta": kpis[0]["meta"],
                "kpi_2_title": kpis[1]["title"],
                "kpi_2_description": kpis[1]["description"],
                "kpi_2_value": kpis[1]["value"],
                "kpi_2_delta": "atenção" if int(kpis[1]["value"]) else "ok",
                "kpi_2_trend": "negative" if int(kpis[1]["value"]) else "positive",
                "kpi_2_meta": kpis[1]["meta"],
                "kpi_3_title": kpis[2]["title"],
                "kpi_3_description": kpis[2]["description"],
                "kpi_3_value": kpis[2]["value"],
                "kpi_3_delta": "publicado",
                "kpi_3_trend": "positive" if int(kpis[2]["value"]) else "neutral",
                "kpi_3_meta": kpis[2]["meta"],
                "kpi_4_title": kpis[3]["title"],
                "kpi_4_description": kpis[3]["description"],
                "kpi_4_value": kpis[3]["value"],
                "kpi_4_delta": "atenção" if int(kpis[3]["value"]) else "ok",
                "kpi_4_trend": "negative" if int(kpis[3]["value"]) else "positive",
                "kpi_4_meta": kpis[3]["meta"],
                "chart_title": "Prioridade operacional",
                "chart_description": "Resumo consolidado das filas internas que já existem.",
                "chart_value": summary,
                "chart_delta": "tenant-scoped",
                "chart_trend": "neutral",
                "chart_meta": "Leitura em tempo real",
                "chart_footer": "Este cockpit não cria nova regra de negócio; ele aponta para superfícies operacionais existentes.",
                "activity_title": "O que merece atenção",
                "activity_description": "Top sinais derivados de pedidos, estoque, catálogo, clientes, entregas e owners.",
                "activity_items": activity_items,
                "table_title": "Filas operacionais",
                "table_description": "Primeiro mapa para o lojista decidir a próxima ação.",
                "table_count": f"{len(tasks)} frente(s) visível(is)",
                "table_columns": [
                    {"label": "Área"},
                    {"label": "Sinal"},
                    {"label": "Quantidade"},
                    {"label": "Ação"},
                ],
                "table_rows": [
                    {
                        "cells": [
                            task["area"],
                            task["signal"],
                            str(task["count"]),
                            _task_action_cell(task),
                        ]
                    }
                    for task in tasks
                ],
                "table_empty_title": "Nenhuma fila operacional",
                "table_empty_description": "Não há sinais consolidados para este tenant no momento.",
                "audit_title": "Sinais por módulo",
                "audit_description": "Leitura consolidada dos módulos consumidos pelo cockpit.",
                "audit_entries": dashboard["audit_entries"],
            }
        )
        return context
