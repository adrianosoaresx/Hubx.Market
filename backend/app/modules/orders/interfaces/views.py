from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView, View

from app.modules.orders.application.admin_order_commands import (
    FULFILLMENT_STATUS_OPTIONS,
    ORDER_STATUS_OPTIONS,
    admin_order_commands,
)
from app.modules.orders.application.admin_order_queries import (
    STATUS_OPTIONS,
    admin_order_queries,
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
        "order-canceled": "Pedido cancelado com sucesso.",
        "order-already-canceled": "Cancelamento ignorado: o pedido já estava cancelado.",
        "order-cancel-blocked": "Cancelamento ignorado: pedidos enviados exigem fluxo operacional específico.",
        "order-status-updated": "Status do pedido atualizado com sucesso.",
        "order-status-unchanged": "Nenhuma alteração aplicada: o pedido já estava nesse status.",
        "fulfillment-status-updated": "Status operacional atualizado com sucesso.",
        "fulfillment-status-unchanged": "Nenhuma alteração aplicada: a operação já estava nesse status.",
        "order-status-invalid": "Atualização ignorada: status do pedido inválido.",
        "fulfillment-status-invalid": "Atualização ignorada: status operacional inválido.",
        "order-not-found": "Atualização ignorada: pedido não encontrado.",
    }
    return mapping.get(result)


def _build_order_action_forms(*, order: dict[str, object], back_href: str, order_number: str) -> str:
    action_url = reverse("orders:admin-order-update", kwargs={"order_number": order_number})
    status = str(order.get("status", "") or "")
    can_cancel = status not in {"canceled", "shipped"}
    cancel_label = (
        "Cancelar pedido"
        if can_cancel
        else "Pedido cancelado"
        if status == "canceled"
        else "Cancelamento bloqueado"
    )
    cancel_hint = (
        "Ação simples para interromper o pedido sem acionar fluxos de estorno."
        if can_cancel
        else "Esse pedido já está cancelado; nenhuma nova ação é necessária."
        if status == "canceled"
        else "Pedido já enviado exige tratamento operacional específico antes de qualquer cancelamento."
    )
    order_status_options = format_html_join(
        "",
        '<option value="{}"{}>{}</option>',
        (
            (
                option["value"],
                mark_safe(' selected="selected"') if option["value"] == order.get("status") else "",
                option["label"],
            )
            for option in ORDER_STATUS_OPTIONS
        ),
    )
    fulfillment_status_options = format_html_join(
        "",
        '<option value="{}"{}>{}</option>',
        (
            (
                option["value"],
                mark_safe(' selected="selected"')
                if option["label"] == order.get("fulfillment_status_label")
                else "",
                option["label"],
            )
            for option in FULFILLMENT_STATUS_OPTIONS
        ),
    )
    return format_html(
        '<div class="flex flex-wrap items-end gap-3">'
        '<a href="{}" class="ds-btn-secondary">Voltar</a>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="action_type" value="order_status" />'
        '<label class="flex flex-col gap-1 text-sm text-[var(--color-text-secondary)]">'
        '<span>Status do pedido</span>'
        '<select name="status" class="min-w-40 rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm text-[var(--color-text-primary)]">'
        '{}'
        '</select>'
        '</label>'
        '<button type="submit" class="ds-btn-primary">Salvar status</button>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="action_type" value="fulfillment_status" />'
        '<label class="flex flex-col gap-1 text-sm text-[var(--color-text-secondary)]">'
        '<span>Status operacional</span>'
        '<select name="fulfillment_status" class="min-w-44 rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm text-[var(--color-text-primary)]">'
        '{}'
        '</select>'
        '</label>'
        '<button type="submit" class="ds-btn-primary">Salvar operação</button>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="action_type" value="cancel_order" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="{}"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '</div>',
        back_href,
        action_url,
        order_status_options,
        action_url,
        fulfillment_status_options,
        action_url,
        "ds-btn-secondary" if can_cancel else "ds-btn-secondary",
        mark_safe("") if can_cancel else mark_safe(' disabled="disabled"'),
        cancel_label,
        cancel_hint,
    )


class AdminOrdersListView(TemplateView):
    template_name = "pages/templates/admin_orders_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        orders = admin_order_queries.list_orders()
        if search_value:
            lowered = search_value.lower()
            orders = [
                order
                for order in orders
                if lowered in str(order["order_number"]).lower()
                or lowered in str(order["customer"]).lower()
            ]
        if status_selected:
            orders = [order for order in orders if order["status"] == status_selected]

        paginator = Paginator(orders, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("orders:admin-orders-list")

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if status_selected:
            query_params.append(f"status={status_selected}")

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        context.update(
            {
                "page_title": "Pedidos",
                "page_description": "Acompanhe a operação de pedidos, pagamentos e expedição.",
                "export_href": "#export-orders",
                "filter_action": base_url,
                "search_name": "q",
                "search_value": search_value,
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": base_url,
                "columns": [
                    {"label": "Pedido"},
                    {"label": "Cliente"},
                    {"label": "Status"},
                    {"label": "Pagamento"},
                    {"label": "Atualização"},
                ],
                "rows": [
                    {
                        "cells": [
                            f'#{order["order_number"]}',
                            order["customer"],
                            order["order_status_label"],
                            order["payment_status"],
                            order["updated_at"],
                        ]
                    }
                    for order in page_obj.object_list
                ],
                "table_count": f"{paginator.count} pedido(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "page_note": admin_order_queries.get_operational_visibility_note(),
            }
        )
        return context


class AdminOrderDetailView(TemplateView):
    template_name = "pages/templates/admin_order_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_number = kwargs["order_number"]
        order = admin_order_queries.get_order(order_number)
        feedback = _build_action_feedback(self.request.GET.get("result", "").strip())
        back_href = reverse("orders:admin-orders-list")
        page_description = (
            "Resumo operacional do pedido, dados do cliente e histórico de movimentações. "
            + admin_order_queries.get_order_operational_visibility(order_number)
        )
        page_meta = feedback or f'Próximo passo: {order.get("next_step_label", "Revisar operação")}.'
        context.update(
            {
                "page_title": f'Pedido #{order["order_number"]}',
                "page_description": page_description,
                "page_meta": page_meta,
                "order_status_label": order["order_status_label"],
                "order_status_variant": order["status"],
                "fulfillment_status_label": order["fulfillment_status_label"],
                "fulfillment_status_variant": order["fulfillment_status_variant"],
                "back_href": back_href,
                "primary_href": "#update-order",
                "page_actions": _build_order_action_forms(order=order, back_href=back_href, order_number=order_number),
                "order_number": f'#{order["order_number"]}',
                "summary_subtitle": order.get("next_step_label"),
                "payment_status": order["payment_status"],
                "shipping_status": order["shipping_status"],
                "summary_content": order["summary_content"],
                "customer_content": order["customer_content"],
                "payment_content": order["payment_content"],
                "shipping_content": order["shipping_content"],
                "notes_content": " ".join(
                    part
                    for part in [order.get("next_step_helper", ""), order.get("blocked_action_guidance", ""), order["notes_content"]]
                    if part
                ),
                "order_items": order["order_items"],
                "subtotal": order["subtotal"],
                "shipping": order["shipping"],
                "discount": order["discount"],
                "installments": order["installments"],
                "total": order["total"],
                "summary_note": order.get("next_step_helper"),
                "activity_items": order["activity_items"],
            }
        )
        return context


class AdminOrderActionView(View):
    def post(self, request, *args, **kwargs):
        order_number = kwargs["order_number"]
        action_type = str(request.POST.get("action_type", "") or "").strip()
        if action_type == "order_status":
            _, result = admin_order_commands.update_order_status(
                order_number=order_number,
                status=str(request.POST.get("status", "") or "").strip(),
            )
        elif action_type == "fulfillment_status":
            _, result = admin_order_commands.update_fulfillment_status(
                order_number=order_number,
                fulfillment_status=str(request.POST.get("fulfillment_status", "") or "").strip(),
            )
        elif action_type == "cancel_order":
            _, result = admin_order_commands.cancel_order(order_number=order_number)
        else:
            result = "order-status-invalid"
        return HttpResponseRedirect(
            f'{reverse("orders:admin-orders-detail", kwargs={"order_number": order_number})}?result={result}'
        )
