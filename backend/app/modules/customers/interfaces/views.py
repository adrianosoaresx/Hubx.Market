from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.http import HttpResponseRedirect
from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
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
        "customer-followup-cleared": "Follow-up removido do cliente.",
        "customer-followup-already-clear": "Nenhuma alteração aplicada: o cliente já estava sem follow-up ativo.",
        "customer-reengagement-marked": "Cliente marcado para reengajamento.",
        "customer-reengagement-already-marked": "Nenhuma alteração aplicada: o cliente já estava marcado para reengajamento.",
        "customer-reengagement-cleared": "Reengajamento removido do cliente.",
        "customer-reengagement-already-clear": "Nenhuma alteração aplicada: o cliente já estava sem reengajamento ativo.",
        "customer-priority-marked": "Cliente marcado com prioridade manual.",
        "customer-priority-already-marked": "Nenhuma alteração aplicada: o cliente já estava com prioridade manual.",
        "customer-priority-cleared": "Prioridade manual removida do cliente.",
        "customer-priority-already-clear": "Nenhuma alteração aplicada: o cliente já estava sem prioridade manual.",
        "customer-bulk-followup-marked": "Ação em lote concluída: clientes marcados para follow-up.",
        "customer-bulk-followup-unchanged": "Nenhuma alteração em lote aplicada: todos os clientes desta visão já estavam com follow-up.",
        "customer-bulk-followup-cleared": "Ação em lote concluída: follow-up removido dos clientes desta visão.",
        "customer-bulk-followup-already-clear": "Nenhuma alteração em lote aplicada: todos os clientes desta visão já estavam sem follow-up.",
        "customer-bulk-reengagement-marked": "Ação em lote concluída: clientes marcados para reengajamento.",
        "customer-bulk-reengagement-unchanged": "Nenhuma alteração em lote aplicada: todos os clientes desta visão já estavam com reengajamento.",
        "customer-bulk-reengagement-cleared": "Ação em lote concluída: reengajamento removido dos clientes desta visão.",
        "customer-bulk-reengagement-already-clear": "Nenhuma alteração em lote aplicada: todos os clientes desta visão já estavam sem reengajamento.",
        "customer-bulk-priority-marked": "Ação em lote concluída: clientes marcados com prioridade manual.",
        "customer-bulk-priority-unchanged": "Nenhuma alteração em lote aplicada: todos os clientes desta visão já estavam com prioridade manual.",
        "customer-bulk-priority-cleared": "Ação em lote concluída: prioridade manual removida dos clientes desta visão.",
        "customer-bulk-priority-already-clear": "Nenhuma alteração em lote aplicada: todos os clientes desta visão já estavam sem prioridade manual.",
        "customer-not-found": "Atualização ignorada: cliente não encontrado.",
        "customer-action-invalid": "Atualização ignorada: ação inválida.",
    }
    return mapping.get(result)


def _quick_filter_label(quick_filter_value: str) -> str | None:
    normalized = str(quick_filter_value or "").strip()
    for option in QUICK_FILTER_OPTIONS:
        if option["value"] == normalized:
            return str(option["label"])
    return None


def _empty_state_for_quick_filter(*, quick_filter_value: str, active_filter_label: str | None) -> tuple[str, str]:
    mapping = {
        "high_priority": (
            "Nenhum cliente crítico agora",
            "Não há clientes em alta prioridade nesta visão. Use “Limpar” para voltar à base completa.",
        ),
        "at_risk": (
            "Nenhum cliente em risco encontrado",
            "Não há clientes em risco nesta visão. Vale limpar o filtro para revisar outros segmentos.",
        ),
        "followup": (
            "Nenhum follow-up pendente agora",
            "Nenhum cliente marcado para follow-up apareceu nesta visão. Limpe o filtro para revisar toda a base.",
        ),
        "repeat": (
            "Nenhum cliente recorrente nesta visão",
            "Não há clientes recorrentes com os critérios atuais. Limpe o filtro para ampliar a análise.",
        ),
        "new": (
            "Nenhum cliente novo encontrado",
            "Não há clientes novos nesta visão no momento. Use “Limpar” para voltar à lista completa.",
        ),
    }
    if quick_filter_value in mapping:
        return mapping[quick_filter_value]
    if active_filter_label:
        return (
            f"Nenhum cliente em {active_filter_label.lower()}",
            "Não encontramos registros para este segmento no momento. Limpe o filtro para ampliar a visão.",
        )
    return (
        "Nenhum cliente encontrado",
        "Ajuste a busca ou os filtros para localizar clientes relevantes.",
    )


def _append_result_param(target_url: str, result: str) -> str:
    split_target = urlsplit(target_url)
    query_items = [(key, value) for key, value in parse_qsl(split_target.query, keep_blank_values=True) if key != "result"]
    query_items.append(("result", result))
    return urlunsplit(
        (
            split_target.scheme,
            split_target.netloc,
            split_target.path,
            urlencode(query_items),
            split_target.fragment,
        )
    )


def _resolve_next_target(*, request, customer_slug: str, result: str) -> str:
    default_target = reverse("customers:admin-customers-detail", kwargs={"customer_slug": customer_slug})
    next_target = str(request.POST.get("next", "") or "").strip()
    if not next_target:
        return _append_result_param(default_target, result)
    if not url_has_allowed_host_and_scheme(next_target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return _append_result_param(default_target, result)
    expected_prefix = reverse("customers:admin-customers-list")
    if not next_target.startswith(expected_prefix):
        return _append_result_param(default_target, result)
    return _append_result_param(next_target, result)


def _resolve_bulk_next_target(*, request, result: str) -> str:
    default_target = reverse("customers:admin-customers-list")
    next_target = str(request.POST.get("next", "") or "").strip()
    if not next_target:
        return _append_result_param(default_target, result)
    if not url_has_allowed_host_and_scheme(next_target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return _append_result_param(default_target, result)
    expected_prefix = reverse("customers:admin-customers-list")
    if not next_target.startswith(expected_prefix):
        return _append_result_param(default_target, result)
    return _append_result_param(next_target, result)


def _filters_from_next(next_target: str) -> tuple[str, str]:
    split_target = urlsplit(next_target or "")
    query_items = dict(parse_qsl(split_target.query, keep_blank_values=True))
    return str(query_items.get("quick_filter", "") or "").strip(), str(query_items.get("q", "") or "").strip()


def _apply_search(customers: list[dict[str, object]], search_value: str) -> list[dict[str, object]]:
    if not search_value:
        return customers
    lowered = search_value.lower()
    return [
        customer
        for customer in customers
        if lowered in str(customer["name"]).lower()
        or lowered in str(customer["email"]).lower()
        or lowered in str(customer["customer_reference"]).lower()
    ]


def _build_customer_action_forms(*, customer: dict[str, object], back_href: str, customer_slug: str) -> str:
    action_url = reverse("customers:admin-customer-update", kwargs={"customer_slug": customer_slug})
    followup_active = bool(customer.get("marked_for_followup"))
    reengagement_active = bool(customer.get("marked_for_reengagement"))
    priority_active = bool(customer.get("marked_as_priority"))
    followup_hint = (
        "Remove o follow-up manual ativo deste cliente."
        if followup_active
        else "Sinaliza que este cliente precisa de acompanhamento manual."
    )
    reengagement_hint = (
        "Remove a sinalização manual de reengajamento deste cliente."
        if reengagement_active
        else "Sinaliza que vale tentar recuperar a relação com uma nova abordagem."
    )
    priority_hint = (
        "Remove o destaque manual de prioridade deste cliente."
        if priority_active
        else "Sinaliza destaque manual para acompanhamento prioritário."
    )
    return format_html(
        '<div class="flex flex-wrap items-end gap-3">'
        '<a href="{}" class="ds-btn-secondary">Voltar</a>'
        '<form method="post" action="{}" class="flex flex-col gap-1">'
        '<input type="hidden" name="action_type" value="{}" />'
        '<button type="submit" class="ds-btn-primary">{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</form>"
        '<form method="post" action="{}" class="flex flex-col gap-1">'
        '<input type="hidden" name="action_type" value="mark_for_reengagement" />'
        '<button type="submit" class="ds-btn-primary">Marcar reengajamento</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</form>"
        '<form method="post" action="{}" class="flex flex-col gap-1">'
        '<input type="hidden" name="action_type" value="{}" />'
        '<button type="submit" class="ds-btn-primary">{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</form>"
        "</div>",
        back_href,
        action_url,
        "clear_followup" if followup_active else "mark_for_followup",
        "Remover follow-up" if followup_active else "Marcar follow-up",
        followup_hint,
        action_url,
        "clear_reengagement" if reengagement_active else "mark_for_reengagement",
        "Remover reengajamento" if reengagement_active else "Marcar reengajamento",
        reengagement_hint,
        action_url,
        "clear_priority" if priority_active else "mark_priority",
        "Remover prioridade" if priority_active else "Marcar prioridade",
        priority_hint,
    )


def _build_customer_list_quick_actions(*, customer: dict[str, object], next_url: str) -> str:
    action_url = reverse("customers:admin-customer-update", kwargs={"customer_slug": customer["slug"]})
    followup_active = bool(customer.get("marked_for_followup"))
    reengagement_active = bool(customer.get("marked_for_reengagement"))
    priority_active = bool(customer.get("marked_as_priority"))
    followup_label = "Remover follow-up" if followup_active else "Marcar follow-up"
    reengagement_label = "Remover reengajamento" if reengagement_active else "Marcar reengajamento"
    priority_label = "Remover prioridade" if priority_active else "Marcar prioridade"
    return format_html(
        '<div class="flex flex-wrap gap-2">'
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">{}</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">{}</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">{}</button>'
        "</form>"
        "</div>",
        action_url,
        "clear_followup" if followup_active else "mark_for_followup",
        next_url,
        followup_label,
        action_url,
        "clear_reengagement" if reengagement_active else "mark_for_reengagement",
        next_url,
        reengagement_label,
        action_url,
        "clear_priority" if priority_active else "mark_priority",
        next_url,
        priority_label,
    )


def _build_customer_bulk_actions(*, next_url: str, selection_count: int) -> str:
    if selection_count <= 0:
        return ""
    action_url = reverse("customers:admin-customer-update", kwargs={"customer_slug": "_bulk"})
    return format_html(
        '<div class="flex flex-wrap gap-2">'
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="bulk_mark_for_followup" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">Marcar follow-up na visão</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="bulk_clear_followup" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">Remover follow-up na visão</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="bulk_mark_reengagement" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">Marcar reengajamento na visão</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="bulk_clear_reengagement" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">Remover reengajamento na visão</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="bulk_mark_priority" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">Marcar prioridade na visão</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="action_type" value="bulk_clear_priority" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary text-xs">Remover prioridade na visão</button>'
        "</form>"
        "</div>",
        action_url,
        next_url,
        action_url,
        next_url,
        action_url,
        next_url,
        action_url,
        next_url,
        action_url,
        next_url,
        action_url,
        next_url,
    )


class AdminCustomersListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        quick_filter_selected = self.request.GET.get("quick_filter", "").strip()
        active_filter_label = _quick_filter_label(quick_filter_selected)
        feedback = _build_action_feedback(self.request.GET.get("result", "").strip())
        page_number = int(self.request.GET.get("page", "1") or "1")

        customers = admin_customer_queries.list_customers(quick_filter=quick_filter_selected)
        customers = _apply_search(customers, search_value)

        paginator = Paginator(customers, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("customers:admin-customers-list")
        empty_title, empty_description = _empty_state_for_quick_filter(
            quick_filter_value=quick_filter_selected,
            active_filter_label=active_filter_label,
        )

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if quick_filter_selected:
            query_params.append(f"quick_filter={quick_filter_selected}")

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        current_list_url = page_url(page_obj.number)
        page_meta = feedback
        if not page_meta and active_filter_label:
            page_meta = (
                f"Filtro ativo: {active_filter_label} · {paginator.count} cliente(s) nesta visão. "
                "Use “Limpar” para voltar à lista completa."
            )
        bulk_scope_active = bool(active_filter_label or search_value)

        context.update(
            {
                "page_title": "Clientes",
                "page_description": (
                    f"Visualizando clientes com filtro rápido ativo: {active_filter_label}."
                    if active_filter_label
                    else "Acompanhe clientes, status da conta e atividade recente."
                ),
                "page_meta": page_meta,
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
                "filter_description": (
                    f"Filtro rápido ativo: {active_filter_label}. Ajuste a busca ou limpe o filtro para ampliar a visão."
                    if active_filter_label
                    else "Busque clientes e refine a visão operacional."
                ),
                "columns": [
                    {"label": "Cliente"},
                    {"label": "Contato"},
                    {"label": "Status"},
                    {"label": "Conta"},
                    {"label": "Última atividade"},
                    {"label": "Ações"},
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
                            _build_customer_list_quick_actions(customer=customer, next_url=current_list_url),
                        ]
                    }
                    for customer in page_obj.object_list
                ],
                "table_count": f"{paginator.count} cliente(s)",
                "selection_count": paginator.count if bulk_scope_active and paginator.count else None,
                "bulk_actions": (
                    _build_customer_bulk_actions(
                        next_url=current_list_url,
                        selection_count=paginator.count,
                    )
                    if bulk_scope_active
                    else None
                ),
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "empty_title": empty_title,
                "empty_description": (
                    f"{empty_description} Busca atual: “{search_value}”."
                    if search_value and paginator.count == 0
                    else empty_description
                ),
                "page_note": (
                    (
                        f"Resultados filtrados por {active_filter_label.lower()} e ordenados por prioridade operacional."
                        if active_filter_label
                        else "Lista ordenada por prioridade operacional e pronta para filtros rápidos de clientes."
                    )
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
        elif action_type == "clear_followup":
            _, result = admin_customer_commands.clear_followup(customer_slug=customer_slug)
        elif action_type == "mark_for_reengagement":
            _, result = admin_customer_commands.mark_for_reengagement(customer_slug=customer_slug)
        elif action_type == "clear_reengagement":
            _, result = admin_customer_commands.clear_reengagement(customer_slug=customer_slug)
        elif action_type == "mark_priority":
            _, result = admin_customer_commands.mark_priority(customer_slug=customer_slug)
        elif action_type == "clear_priority":
            _, result = admin_customer_commands.clear_priority(customer_slug=customer_slug)
        elif action_type in {
            "bulk_mark_for_followup",
            "bulk_clear_followup",
            "bulk_mark_reengagement",
            "bulk_clear_reengagement",
            "bulk_mark_priority",
            "bulk_clear_priority",
        }:
            next_target = str(request.POST.get("next", "") or "").strip()
            quick_filter_selected, search_value = _filters_from_next(next_target)
            customers = admin_customer_queries.list_customers(quick_filter=quick_filter_selected)
            customers = _apply_search(customers, search_value)
            customer_slugs = [str(customer["slug"]) for customer in customers]
            if action_type == "bulk_mark_for_followup":
                _, result = admin_customer_commands.bulk_mark_for_followup(customer_slugs=customer_slugs)
            elif action_type == "bulk_clear_followup":
                _, result = admin_customer_commands.bulk_clear_followup(customer_slugs=customer_slugs)
            elif action_type == "bulk_mark_reengagement":
                _, result = admin_customer_commands.bulk_mark_reengagement(customer_slugs=customer_slugs)
            elif action_type == "bulk_clear_reengagement":
                _, result = admin_customer_commands.bulk_clear_reengagement(customer_slugs=customer_slugs)
            elif action_type == "bulk_mark_priority":
                _, result = admin_customer_commands.bulk_mark_priority(customer_slugs=customer_slugs)
            else:
                _, result = admin_customer_commands.bulk_clear_priority(customer_slugs=customer_slugs)
            return HttpResponseRedirect(_resolve_bulk_next_target(request=request, result=result))
        else:
            result = "customer-action-invalid"
        return HttpResponseRedirect(_resolve_next_target(request=request, customer_slug=customer_slug, result=result))
