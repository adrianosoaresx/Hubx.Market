from __future__ import annotations

from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import TemplateView

from app.modules.customers.application.admin_customer_commands import admin_customer_commands
from app.modules.customers.application.admin_customer_queries import (
    QUICK_FILTER_OPTIONS,
    admin_customer_queries,
)


def _build_page_items(page_number: int, total_pages: int, base_url: str, query_params: list[str]) -> list[dict[str, object]]:
    suffix = "&".join(query_params)
    return [
        {
            "number": number,
            "url": f"{base_url}?{suffix + '&' if suffix else ''}page={number}",
        }
        for number in range(1, total_pages + 1)
    ]


def _build_action_feedback(result: str) -> str | None:
    mapping = {
        "customer-followup-marked": "Cliente marcado para follow-up.",
        "customer-followup-already-marked": "Nenhuma alteração aplicada: o cliente já estava marcado para follow-up.",
        "customer-reengagement-marked": "Cliente marcado para reengajamento.",
        "customer-reengagement-already-marked": "Nenhuma alteração aplicada: o cliente já estava marcado para reengajamento.",
        "customer-priority-marked": "Cliente marcado com prioridade manual.",
        "customer-priority-already-marked": "Nenhuma alteração aplicada: o cliente já estava com prioridade manual.",
        "customer-not-found": "Atualização ignorada: cliente não encontrado.",
        "customer-action-invalid": "Atualização ignorada: ação inválida.",
    }
    return mapping.get(result)


def _build_customer_action_forms(*, customer: dict[str, object], back_href: str, customer_slug: str) -> str:
    action_url = reverse("customers:admin-customer-update", kwargs={"customer_slug": customer_slug})
    followup_hint = "Sinaliza que este cliente precisa de acompanhamento manual."
    reengagement_hint = "Sinaliza que vale tentar recuperar a relação com uma nova abordagem."
    priority_hint = "Sinaliza destaque manual para acompanhamento prioritário."
    return format_html(
        '<div class="flex flex-wrap items-end gap-3">'
        '<a href="{}" class="ds-btn-secondary">Voltar</a>'
        '<form method="post" action="{}" class="flex flex-col gap-1">'
        '<input type="hidden" name="action_type" value="mark_for_followup" />'
        '<button type="submit" class="ds-btn-primary">Marcar follow-up</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</form>"
        '<form method="post" action="{}" class="flex flex-col gap-1">'
        '<input type="hidden" name="action_type" value="mark_for_reengagement" />'
        '<button type="submit" class="ds-btn-primary">Marcar reengajamento</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</form>"
        '<form method="post" action="{}" class="flex flex-col gap-1">'
        '<input type="hidden" name="action_type" value="mark_priority" />'
        '<button type="submit" class="ds-btn-primary">Marcar prioridade</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</form>"
        "</div>",
        back_href,
        action_url,
        followup_hint,
        action_url,
        reengagement_hint,
        action_url,
        priority_hint,
    )


class AdminCustomersListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        quick_filter_selected = self.request.GET.get("quick_filter", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        customers = admin_customer_queries.list_customers(quick_filter=quick_filter_selected)
        if search_value:
            lowered = search_value.lower()
            customers = [
                customer
                for customer in customers
                if lowered in str(customer["name"]).lower()
                or lowered in str(customer["email"]).lower()
                or lowered in str(customer["customer_reference"]).lower()
            ]

        paginator = Paginator(customers, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("customers:admin-customers-list")

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if quick_filter_selected:
            query_params.append(f"quick_filter={quick_filter_selected}")

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        context.update(
            {
                "page_title": "Clientes",
                "page_description": "Acompanhe clientes, status da conta e atividade recente.",
                "export_href": "#export-customers",
                "filter_action": base_url,
                "search_name": "q",
                "search_value": search_value,
                "status_name": "quick_filter",
                "status_options": QUICK_FILTER_OPTIONS,
                "status_selected": quick_filter_selected,
                "status_label": "Filtro rápido",
                "status_placeholder": "Todos os clientes",
                "reset_url": base_url,
                "columns": [
                    {"label": "Cliente"},
                    {"label": "Contato"},
                    {"label": "Status"},
                    {"label": "Conta"},
                    {"label": "Última atividade"},
                ],
                "rows": [
                    {
                        "cells": [
                            customer["name"],
                            customer["email"],
                            (
                                customer["customer_status_label"]
                                + (f' · {customer["list_highlights"]}' if customer.get("list_highlights") else "")
                            ),
                            customer["account_type_label"],
                            (
                                customer["last_activity"]
                                + (
                                    f' · {customer["engagement_label"].lower()}'
                                    if customer.get("engagement_label")
                                    else ""
                                )
                            ),
                        ]
                    }
                    for customer in page_obj.object_list
                ],
                "table_count": f"{paginator.count} cliente(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "page_note": (
                    "Lista ordenada por prioridade operacional e pronta para filtros rápidos de clientes."
                ),
            }
        )
        return context


class AdminCustomerDetailView(TemplateView):
    template_name = "pages/templates/admin_customer_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = admin_customer_queries.get_customer(kwargs["customer_slug"])
        back_href = reverse("customers:admin-customers-list")
        feedback = _build_action_feedback(self.request.GET.get("result", "").strip())
        context.update(
            {
                "page_title": customer["name"],
                "page_description": (
                    f'Resumo operacional com lifecycle {customer.get("lifecycle_stage_label", "Novo").lower()}, {customer.get("business_tier_label", "Sem histórico").lower()}'
                    f', {customer.get("revenue_label", "sem receita realizada")} '
                    f'e engajamento {customer.get("engagement_label", "sem histórico").lower()}. '
                    f'Direção de crescimento: {customer.get("growth_priority_label", "acompanhar manualmente").lower()}. '
                    f'Próxima ação sugerida: {customer.get("next_action_label", "acompanhar manualmente").lower()}.'
                ),
                "page_meta": feedback,
                "customer_status_label": customer["customer_status_label"],
                "customer_status_variant": customer["status"],
                "account_type_label": customer["account_type_label"],
                "back_href": back_href,
                "page_actions": _build_customer_action_forms(
                    customer=customer,
                    back_href=back_href,
                    customer_slug=kwargs["customer_slug"],
                ),
                "customer_reference": customer["customer_reference"],
                "customer_since": customer["customer_since"],
                "last_seen": customer["last_seen"],
                "summary_content": customer["summary_content"],
                "contact_content": customer["contact_content"],
                "profile_content": customer["profile_content"],
                "orders_summary_content": customer["orders_summary_content"],
                "account_notes_content": customer["account_notes_content"],
                "activity_items": customer["activity_items"],
            }
        )
        return context


class AdminCustomerActionView(View):
    def post(self, request, *args, **kwargs):
        customer_slug = kwargs["customer_slug"]
        action_type = str(request.POST.get("action_type", "") or "").strip()
        if action_type == "mark_for_followup":
            _, result = admin_customer_commands.mark_for_followup(customer_slug=customer_slug)
        elif action_type == "mark_for_reengagement":
            _, result = admin_customer_commands.mark_for_reengagement(customer_slug=customer_slug)
        elif action_type == "mark_priority":
            _, result = admin_customer_commands.mark_priority(customer_slug=customer_slug)
        else:
            result = "customer-action-invalid"
        return HttpResponseRedirect(
            f'{reverse("customers:admin-customers-detail", kwargs={"customer_slug": customer_slug})}?result={result}'
        )
