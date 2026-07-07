from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView, View

from app.modules.accounts.application.admin_permissions import PERMISSION_ORDERS_MANAGE
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role
from app.modules.orders.application.admin_order_commands import (
    FULFILLMENT_STATUS_OPTIONS,
    ORDER_STATUS_OPTIONS,
    admin_order_commands,
)
from app.modules.orders.application.admin_order_queries import (
    STATUS_OPTIONS,
    admin_order_queries,
)
from app.modules.orders.application.inventory_exception_metrics_queries import inventory_exception_metrics_queries


def _build_page_items(page_number: int, total_pages: int, base_url: str, query_params: list[str]) -> list[dict[str, object]]:
    suffix = "&".join(query_params)
    return [
        {
            "number": number,
            "url": f"{base_url}?{suffix + '&' if suffix else ''}page={number}",
        }
        for number in range(1, total_pages + 1)
    ]


def _build_inventory_exception_quick_filter_control(*, selected_value: str) -> str:
    options = format_html_join(
        "",
        '<option value="{}"{}>{}</option>',
        (
            (
                option["value"],
                mark_safe(' selected="selected"') if option["value"] == selected_value else "",
                option["label"],
            )
            for option in admin_order_queries.get_inventory_exception_quick_filter_options()
        ),
    )
    return format_html(
        '<label class="flex w-full flex-col gap-1 text-sm text-[var(--color-text-secondary)] lg:w-56">'
        '<span>Exceção de estoque</span>'
        '<select name="quick_filter" class="min-w-44 rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm text-[var(--color-text-primary)]">'
        '<option value="">Todas as exceções</option>'
        '{}'
        '</select>'
        '</label>',
        options,
    )


def _build_orders_list_status_cell(order: dict[str, object]) -> str:
    status_label = str(order.get("order_status_label", "") or "Pendente")
    fulfillment_label = str(order.get("fulfillment_status_label", "") or "")
    inventory_state = str(order.get("inventory_exception_list_label", "") or "")
    inventory_priority = str(order.get("inventory_exception_priority_label", "") or "")
    inventory_aging = str(order.get("inventory_exception_aging_label", "") or "")
    details = " · ".join(part for part in [fulfillment_label, inventory_state, inventory_priority, inventory_aging] if part)
    if not details:
        return status_label
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        status_label,
        details,
    )


def _build_orders_list_payment_cell(order: dict[str, object]) -> str:
    payment_status = str(order.get("payment_status", "") or "Indisponível")
    aging_label = str(order.get("inventory_exception_aging_label", "") or "")
    if aging_label in {"Exceção envelhecida", "Revisão parada"}:
        helper = str(order.get("inventory_exception_aging_helper", "") or "")
    else:
        helper = str(
            order.get("inventory_exception_priority_helper", "")
            or order.get("inventory_exception_list_helper", "")
            or order.get("inventory_exception_owner_helper", "")
            or order.get("inventory_exception_aging_helper", "")
            or ""
        )
    owner_workload_helper = str(order.get("inventory_exception_owner_workload_helper", "") or "")
    if owner_workload_helper and owner_workload_helper not in helper:
        helper = f"{helper} {owner_workload_helper}".strip()
    if not helper:
        return payment_status
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        payment_status,
        helper,
    )


def _build_orders_list_updated_cell(order: dict[str, object]) -> str:
    updated_at = str(order.get("updated_at", "") or "agora")
    aging_label = str(order.get("inventory_exception_aging_label", "") or "")
    marker_label = str(order.get("inventory_exception_marker_label", "") or "")
    owner_label = str(order.get("inventory_exception_owner_label", "") or "")
    owner_workload_label = str(order.get("inventory_exception_owner_workload_label", "") or "")
    owner_secondary = ""
    if owner_label and owner_workload_label:
        owner_secondary = f"Responsável: {owner_label} · {owner_workload_label}"
    elif owner_label:
        owner_secondary = f"Responsável: {owner_label}"
    elif owner_workload_label:
        owner_secondary = owner_workload_label
    primary_secondary = aging_label or marker_label
    secondary_label = " · ".join(part for part in [primary_secondary, owner_secondary] if part)
    if not secondary_label:
        return updated_at
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        updated_at,
        secondary_label,
    )


def _tenant_missing_empty_state(*, tenant_id: int | None, quick_filter_selected: str, search_value: str, status_selected: str) -> tuple[str, str] | None:
    if not tenant_id or quick_filter_selected or search_value or status_selected:
        return None
    return (
        "Nenhum pedido persistido nesta loja",
        "A loja atual ainda não possui pedidos persistidos disponíveis para esta visão administrativa.",
    )


def _append_result_to_url(url: str, result: str) -> str:
    if not url:
        return url
    split_result = urlsplit(url)
    query_items = [(key, value) for key, value in parse_qsl(split_result.query, keep_blank_values=True) if key != "result"]
    if result:
        query_items.append(("result", result))
    return urlunsplit(
        (
            split_result.scheme,
            split_result.netloc,
            split_result.path,
            urlencode(query_items),
            split_result.fragment,
        )
    )


def _build_orders_list_quick_actions_cell(order: dict[str, object], *, current_list_url: str, csrf_token: str) -> str:
    action_url = reverse("orders:admin-order-update", kwargs={"order_number": order["order_number"]})
    inventory_exception_content = str(order.get("inventory_exception_content", "") or "")
    inventory_exception_under_review_marked = bool(order.get("inventory_exception_under_review_marked"))
    inventory_exception_resolved_marked = bool(order.get("inventory_exception_resolved_marked"))
    inventory_exception_owner_label = str(order.get("inventory_exception_owner_label", "") or "").strip()

    can_mark_review = bool(inventory_exception_content) and not inventory_exception_under_review_marked
    can_mark_resolved = not inventory_exception_content and inventory_exception_under_review_marked and not inventory_exception_resolved_marked
    can_reassign_owner = (
        (bool(inventory_exception_content) or inventory_exception_under_review_marked)
        and not inventory_exception_resolved_marked
    )

    if can_mark_review:
        return format_html(
            '<form method="post" action="{}" class="flex flex-col gap-1">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<input type="hidden" name="action_type" value="mark_inventory_exception_under_review" />'
            '<input type="hidden" name="next" value="{}" />'
            '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Marcar revisão</button>'
            '<p class="text-xs text-[var(--color-text-secondary)]">Sinaliza que a exceção já está em tratamento.</p>'
            '</form>',
            action_url,
            csrf_token,
            current_list_url,
        )
    if can_mark_resolved:
        return format_html(
            '<form method="post" action="{}" class="flex flex-col gap-1">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<input type="hidden" name="action_type" value="mark_inventory_exception_resolved" />'
            '<input type="hidden" name="next" value="{}" />'
            '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Marcar resolvida</button>'
            '<p class="text-xs text-[var(--color-text-secondary)]">Fecha a trilha manual depois da normalização.</p>'
            '</form>',
            action_url,
            csrf_token,
            current_list_url,
        )
    if can_reassign_owner:
        return format_html(
            '<form method="post" action="{}" class="flex flex-col gap-1">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<input type="hidden" name="action_type" value="reassign_inventory_exception_owner" />'
            '<input type="hidden" name="next" value="{}" />'
            '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">{}</button>'
            '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
            '</form>',
            action_url,
            csrf_token,
            current_list_url,
            "Reatribuir para mim" if inventory_exception_owner_label else "Assumir exceção",
            (
                f"Troca o responsável atual ({inventory_exception_owner_label}) pelo ator desta ação."
                if inventory_exception_owner_label
                else "Registra o ator desta ação como responsável atual pela exceção."
            ),
        )
    marker_label = str(order.get("inventory_exception_marker_label", "") or "")
    helper = str(order.get("inventory_exception_list_helper", "") or "Sem ação rápida necessária nesta visão.")
    fallback_label = marker_label or "Sem ação pendente"
    return format_html(
        '<div class="space-y-1"><div>{}</div><div class="text-xs text-[var(--color-text-secondary)]">{}</div></div>',
        fallback_label,
        helper,
    )


def _build_orders_list_bulk_actions(*, current_list_url: str, order_numbers: list[str], csrf_token: str) -> str:
    if not order_numbers:
        return ""
    action_url = reverse("orders:admin-order-update", kwargs={"order_number": order_numbers[0]})
    joined_order_numbers = ",".join(order_numbers)
    return format_html(
        '<div class="flex flex-wrap gap-2">'
        '<form method="post" action="{}">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="bulk_mark_inventory_exception_under_review" />'
        '<input type="hidden" name="order_numbers" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Marcar revisão na visão</button>'
        '</form>'
        '<form method="post" action="{}">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="bulk_mark_inventory_exception_resolved" />'
        '<input type="hidden" name="order_numbers" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Marcar resolvida na visão</button>'
        '</form>'
        '</div>',
        action_url,
        csrf_token,
        joined_order_numbers,
        current_list_url,
        action_url,
        csrf_token,
        joined_order_numbers,
        current_list_url,
    )


def _parse_bulk_order_numbers(value: str) -> list[str]:
    normalized = str(value or "").strip()
    if not normalized:
        return []
    seen: set[str] = set()
    result: list[str] = []
    for item in normalized.split(","):
        order_number = item.strip().lstrip("#")
        if not order_number or order_number in seen:
            continue
        seen.add(order_number)
        result.append(order_number)
    return result


def _build_action_feedback(result: str) -> str | None:
    mapping = {
        "delivery-completed": "Entrega confirmada com sucesso.",
        "delivery-already-completed": "Nenhuma alteração aplicada: o pedido já estava encerrado como entregue.",
        "delivery-completion-blocked": "Confirmação de entrega bloqueada: leve o pedido a trânsito antes de encerrar a operação.",
        "shipping-started": "Envio iniciado com sucesso.",
        "shipping-already-started": "Nenhuma alteração aplicada: o pedido já estava em trânsito.",
        "shipping-start-blocked": "Início de envio bloqueado: conclua pagamento e preparo antes de liberar trânsito.",
        "fulfillment-started": "Preparação do pedido iniciada com sucesso.",
        "fulfillment-already-started": "Nenhuma alteração aplicada: a preparação do pedido já estava em andamento.",
        "fulfillment-start-blocked": "Início de preparação bloqueado: confirme pagamento e estado atual do pedido antes de liberar expedição.",
        "order-canceled": "Pedido cancelado com sucesso.",
        "order-already-canceled": "Cancelamento ignorado: o pedido já estava cancelado.",
        "order-cancel-blocked": "Cancelamento ignorado: pedidos enviados exigem fluxo operacional específico.",
        "order-status-updated": "Status do pedido atualizado com sucesso.",
        "order-status-unchanged": "Nenhuma alteração aplicada: o pedido já estava nesse status.",
        "order-status-finalized-blocked": "Atualização ignorada: pedidos com estoque já finalizado na entrega exigem revisão operacional manual.",
        "order-status-canceled-blocked": "Atualização ignorada: pedidos cancelados não devem ser reabertos por atalho genérico.",
        "order-status-shipped-blocked": "Atualização ignorada: pedidos enviados exigem fluxo operacional específico para qualquer reversão.",
        "fulfillment-status-updated": "Status operacional atualizado com sucesso.",
        "fulfillment-status-unchanged": "Nenhuma alteração aplicada: a operação já estava nesse status.",
        "fulfillment-status-finalized-blocked": "Atualização ignorada: a operação já foi encerrada com estoque finalizado na entrega.",
        "fulfillment-status-canceled-blocked": "Atualização ignorada: pedidos cancelados exigem revisão manual antes de alterar a operação.",
        "order-status-invalid": "Atualização ignorada: status do pedido inválido.",
        "fulfillment-status-invalid": "Atualização ignorada: status operacional inválido.",
        "inventory-exception-under-review": "Exceção de estoque marcada em revisão.",
        "inventory-exception-already-under-review": "Nenhuma alteração aplicada: a exceção de estoque já estava em revisão.",
        "inventory-exception-review-unavailable": "Marcação ignorada: não há exceção ativa de estoque para colocar em revisão.",
        "inventory-exception-resolved": "Exceção de estoque marcada como resolvida.",
        "inventory-exception-already-resolved": "Nenhuma alteração aplicada: a exceção de estoque já estava resolvida.",
        "inventory-exception-resolution-unavailable": "Marcação ignorada: coloque a exceção em revisão antes de concluir a resolução.",
        "inventory-exception-still-active": "Resolução ignorada: a exceção de estoque ainda permanece ativa e precisa ser tratada primeiro.",
        "inventory-exception-owner-reassigned": "Responsável da exceção atualizado.",
        "inventory-exception-owner-already-assigned": "Nenhuma alteração aplicada: a exceção já estava atribuída ao responsável atual.",
        "inventory-exception-reassignment-unavailable": "Reatribuição ignorada: a exceção precisa estar aberta ou em revisão para trocar o responsável.",
        "bulk-inventory-exception-under-review": "Ação em lote concluída: exceções elegíveis marcadas em revisão na visão atual.",
        "bulk-inventory-exception-under-review-no-change": "Ação em lote sem efeito: não havia exceções elegíveis para marcar em revisão nesta visão.",
        "bulk-inventory-exception-resolved": "Ação em lote concluída: exceções elegíveis marcadas como resolvidas na visão atual.",
        "bulk-inventory-exception-resolved-no-change": "Ação em lote sem efeito: não havia exceções elegíveis para marcar como resolvidas nesta visão.",
        "order-not-found": "Atualização ignorada: pedido não encontrado.",
        "order-permission-denied": "Permissão insuficiente para alterar pedidos.",
        "order-tenant-missing": "Tenant ausente: atualização de pedido não aplicada.",
    }
    return mapping.get(result)


class InventoryExceptionMetricsView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        configured_token = str(getattr(settings, "INVENTORY_OBSERVABILITY_TOKEN", "") or "").strip()
        if not configured_token:
            configured_token = str(getattr(settings, "ORDERS_OBSERVABILITY_TOKEN", "") or "").strip()
        if not configured_token:
            return HttpResponseNotFound("Métricas de estoque indisponíveis.")

        provided_token = str(request.headers.get("X-Hubx-Observability-Token", "") or "").strip()
        if not provided_token:
            authorization_header = str(request.headers.get("Authorization", "") or "").strip()
            if authorization_header.lower().startswith("bearer "):
                provided_token = authorization_header[7:].strip()
        if provided_token != configured_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

        return HttpResponse(
            inventory_exception_metrics_queries.export_prometheus_metrics(),
            status=200,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )


def _build_order_action_forms(*, order: dict[str, object], back_href: str, order_number: str, csrf_token: str) -> str:
    action_url = reverse("orders:admin-order-update", kwargs={"order_number": order_number})
    status = str(order.get("status", "") or "")
    payment_status = str(order.get("payment_status", "") or "")
    fulfillment_label = str(order.get("fulfillment_status_label", "") or "")
    shipping_status = str(order.get("shipping_status", "") or "")
    can_start_fulfillment = (
        status == "paid"
        and "confirm" in payment_status.lower()
        and not (fulfillment_label == "Separando itens" and shipping_status == "Preparando envio")
    )
    start_fulfillment_hint = (
        "Libera picking e preparação de envio agora que o pagamento já está confirmado."
        if can_start_fulfillment
        else "A preparação já foi iniciada ou o pedido ainda não está pronto para entrar em expedição."
    )
    can_start_shipping = (
        status == "paid"
        and "confirm" in payment_status.lower()
        and fulfillment_label == "Separando itens"
        and shipping_status == "Preparando envio"
    )
    start_shipping_hint = (
        "Leva o pedido para trânsito depois da separação, sem depender de integração logística externa."
        if can_start_shipping
        else "O envio só pode começar depois que o pedido estiver pago e já estiver em preparação."
    )
    can_complete_delivery = status == "shipped" and fulfillment_label == "Em trânsito" and shipping_status == "Em trânsito"
    complete_delivery_hint = (
        "Fecha o ciclo operacional do pedido quando a entrega já pode ser confirmada com segurança."
        if can_complete_delivery
        else "A confirmação de entrega só fica disponível depois que o pedido já estiver em trânsito."
    )
    can_cancel = status not in {"canceled", "shipped"}
    inventory_exception_content = str(order.get("inventory_exception_content", "") or "")
    inventory_exception_marker_label = str(order.get("inventory_exception_marker_label", "") or "")
    inventory_exception_marker_helper = str(order.get("inventory_exception_marker_helper", "") or "")
    inventory_exception_under_review_marked = bool(order.get("inventory_exception_under_review_marked"))
    inventory_exception_resolved_marked = bool(order.get("inventory_exception_resolved_marked"))
    inventory_exception_owner_label = str(order.get("inventory_exception_owner_label", "") or "")
    can_mark_inventory_exception_under_review = bool(inventory_exception_content) and not inventory_exception_under_review_marked
    can_mark_inventory_exception_resolved = (
        not inventory_exception_content and inventory_exception_under_review_marked and not inventory_exception_resolved_marked
    )
    can_reassign_inventory_exception_owner = (
        (bool(inventory_exception_content) or inventory_exception_under_review_marked)
        and not inventory_exception_resolved_marked
    )
    inventory_exception_under_review_hint = (
        "Registra que a exceção já está sendo tratada manualmente pela operação."
        if can_mark_inventory_exception_under_review
        else "Só fica disponível quando existe uma exceção ativa ainda sem marcação de revisão."
    )
    inventory_exception_resolved_hint = (
        "Fecha a trilha manual da exceção depois que vínculo e saldo já estiverem normalizados."
        if can_mark_inventory_exception_resolved
        else "Disponível quando a exceção já saiu do estado ativo e a operação quer registrar o fechamento manual."
    )
    inventory_exception_reassign_hint = (
        (
            f"Troca o responsável atual ({inventory_exception_owner_label}) pelo ator desta ação."
            if inventory_exception_owner_label
            else "Registra o ator desta ação como responsável atual pela exceção aberta."
        )
        if can_reassign_inventory_exception_owner
        else "Disponível enquanto a exceção ainda estiver aberta ou em revisão, antes da resolução final."
    )
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
        '<a href="{}" class="ds-btn ds-btn-secondary ds-btn-md">Voltar</a>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="order_status" />'
        '<label class="flex flex-col gap-1 text-sm text-[var(--color-text-secondary)]">'
        '<span>Status do pedido</span>'
        '<select name="status" class="min-w-40 rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm text-[var(--color-text-primary)]">'
        '{}'
        '</select>'
        '</label>'
        '<button type="submit" class="ds-btn ds-btn-primary ds-btn-md">Salvar status</button>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="fulfillment_status" />'
        '<label class="flex flex-col gap-1 text-sm text-[var(--color-text-secondary)]">'
        '<span>Status operacional</span>'
        '<select name="fulfillment_status" class="min-w-44 rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm text-[var(--color-text-primary)]">'
        '{}'
        '</select>'
        '</label>'
        '<button type="submit" class="ds-btn ds-btn-primary ds-btn-md">Salvar operação</button>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="start_fulfillment" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="ds-btn ds-btn-primary ds-btn-md"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="start_shipping" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="ds-btn ds-btn-primary ds-btn-md"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="complete_delivery" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="ds-btn ds-btn-primary ds-btn-md"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="cancel_order" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="{}"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="mark_inventory_exception_under_review" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-md"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="mark_inventory_exception_resolved" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-md"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '<form method="post" action="{}" class="flex flex-wrap items-end gap-2">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="action_type" value="reassign_inventory_exception_owner" />'
        '<div class="flex flex-col gap-1">'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-md"{}>{}</button>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</form>'
        '</div>',
        back_href,
        action_url,
        csrf_token,
        order_status_options,
        action_url,
        csrf_token,
        fulfillment_status_options,
        action_url,
        csrf_token,
        mark_safe("") if can_start_fulfillment else mark_safe(' disabled="disabled"'),
        "Iniciar preparo",
        start_fulfillment_hint,
        action_url,
        csrf_token,
        mark_safe("") if can_start_shipping else mark_safe(' disabled="disabled"'),
        "Iniciar envio",
        start_shipping_hint,
        action_url,
        csrf_token,
        mark_safe("") if can_complete_delivery else mark_safe(' disabled="disabled"'),
        "Confirmar entrega",
        complete_delivery_hint,
        action_url,
        csrf_token,
        "ds-btn ds-btn-secondary ds-btn-md" if can_cancel else "ds-btn ds-btn-secondary ds-btn-md",
        mark_safe("") if can_cancel else mark_safe(' disabled="disabled"'),
        cancel_label,
        cancel_hint,
        action_url,
        csrf_token,
        mark_safe("") if can_mark_inventory_exception_under_review else mark_safe(' disabled="disabled"'),
        "Marcar exceção em revisão" if can_mark_inventory_exception_under_review else inventory_exception_marker_label or "Exceção sem revisão",
        inventory_exception_under_review_hint,
        action_url,
        csrf_token,
        mark_safe("") if can_mark_inventory_exception_resolved else mark_safe(' disabled="disabled"'),
        "Marcar exceção resolvida" if can_mark_inventory_exception_resolved else inventory_exception_marker_label or "Sem resolução pendente",
        inventory_exception_resolved_hint,
        action_url,
        csrf_token,
        mark_safe("") if can_reassign_inventory_exception_owner else mark_safe(' disabled="disabled"'),
        "Reatribuir exceção para mim" if inventory_exception_owner_label else "Assumir exceção",
        inventory_exception_reassign_hint,
    )


class AdminOrdersListView(TemplateView):
    template_name = "pages/templates/admin_orders_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        quick_filter_selected = self.request.GET.get("quick_filter", "").strip()
        result = self.request.GET.get("result", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")
        can_manage_orders = request_admin_can(self.request, PERMISSION_ORDERS_MANAGE)

        orders = admin_order_queries.list_orders(tenant_id=tenant_id)
        orders = admin_order_queries.filter_orders_by_inventory_exception_state(orders, quick_filter_selected)
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
        scoped_order_numbers = [str(order["order_number"]) for order in orders]

        paginator = Paginator(orders, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("orders:admin-orders-list")

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if status_selected:
            query_params.append(f"status={status_selected}")
        if quick_filter_selected:
            query_params.append(f"quick_filter={quick_filter_selected}")

        filter_title, filter_description = admin_order_queries.get_inventory_exception_quick_filter_context(
            quick_filter_selected
        )
        quick_filter_label = admin_order_queries.get_inventory_exception_quick_filter_label(quick_filter_selected)
        filtered_count = len(orders)
        empty_title, empty_description = admin_order_queries.get_inventory_exception_empty_state(
            quick_filter_selected,
            search_value,
        )
        tenant_missing_empty_state = _tenant_missing_empty_state(
            tenant_id=tenant_id,
            quick_filter_selected=quick_filter_selected,
            search_value=search_value,
            status_selected=status_selected,
        )
        if tenant_missing_empty_state and filtered_count == 0:
            empty_title, empty_description = tenant_missing_empty_state
        active_filter_meta = (
            f"Filtro rápido ativo: {quick_filter_label}. {filtered_count} pedido(s) nesta visão. Use Limpar para voltar à lista completa."
            if quick_filter_label
            else ""
        )
        page_note = admin_order_queries.get_operational_visibility_note()
        backlog_summary = admin_order_queries.get_inventory_exception_backlog_summary()
        if quick_filter_label:
            page_note = f"Visão atual: {quick_filter_label} · {filtered_count} pedido(s). {page_note} {backlog_summary}"
            filter_description = (
                f"{filter_description} Use Limpar para voltar à lista completa."
            )
        else:
            page_note = f"{page_note} {backlog_summary}"
        if filtered_count == 0:
            filter_description = f"{empty_title}. {empty_description}"
            if quick_filter_label:
                active_filter_meta = f"{active_filter_meta} {empty_title}. {empty_description}".strip()
            else:
                active_filter_meta = f"{empty_title}. {empty_description}"

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        context.update(
            {
                "page_title": "Pedidos",
                "page_description": "Acompanhe a operação de pedidos, pagamentos e expedição.",
                "page_meta": _build_action_feedback(result) or active_filter_meta,
                "table_description": (
                    "Tabela operacional com status, pagamento, prioridade e markers rápidos para exceções de estoque."
                ),
                "export_href": "/ops/orders/",
                "filter_action": base_url,
                "filter_title": filter_title,
                "filter_description": filter_description,
                "search_name": "q",
                "search_value": search_value,
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "extra_filters": _build_inventory_exception_quick_filter_control(selected_value=quick_filter_selected),
                "reset_url": base_url,
                "columns": [
                    {"label": "Pedido"},
                    {"label": "Cliente"},
                    {"label": "Status"},
                    {"label": "Pagamento"},
                    {"label": "Atualização"},
                    {"label": "Ações"},
                ],
                "rows": [
                    {
                        "cells": [
                            f'#{order["order_number"]}',
                            order["customer"],
                            _build_orders_list_status_cell(order),
                            _build_orders_list_payment_cell(order),
                            _build_orders_list_updated_cell(order),
                            (
                                _build_orders_list_quick_actions_cell(
                                    order,
                                    current_list_url=self.request.get_full_path(),
                                    csrf_token=get_token(self.request),
                                )
                                if can_manage_orders
                                else "Sem permissão para alterar pedidos"
                            ),
                        ]
                    }
                    for order in page_obj.object_list
                ],
                "table_count": f"{paginator.count} pedido(s)",
                "selection_count": str(filtered_count) if (quick_filter_selected or search_value or status_selected) and filtered_count else "",
                "bulk_actions": _build_orders_list_bulk_actions(
                    current_list_url=self.request.get_full_path(),
                    order_numbers=scoped_order_numbers,
                    csrf_token=get_token(self.request),
                )
                if (quick_filter_selected or search_value or status_selected) and filtered_count and can_manage_orders
                else "",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "page_note": page_note,
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


class AdminOrderDetailView(TemplateView):
    template_name = "pages/templates/admin_order_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order_number = kwargs["order_number"]
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        order = admin_order_queries.get_order(order_number, tenant_id=tenant_id)
        feedback = _build_action_feedback(self.request.GET.get("result", "").strip())
        back_href = reverse("orders:admin-orders-list")
        can_manage_orders = request_admin_can(self.request, PERMISSION_ORDERS_MANAGE)
        page_description = (
            "Resumo operacional do pedido, dados do cliente e histórico de movimentações. "
            + admin_order_queries.get_order_operational_visibility(order_number, tenant_id=tenant_id)
        )
        page_meta = feedback or " ".join(
            part
            for part in [
                f'Próximo passo: {order.get("next_step_label", "Revisar operação")}.',
                order.get("inventory_visibility_content", ""),
                order.get("inventory_exception_content", ""),
                order.get("inventory_exception_aging_helper", ""),
                order.get("inventory_exception_priority_helper", ""),
                order.get("inventory_exception_marker_helper", ""),
                order.get("inventory_exception_guidance_helper", ""),
            ]
            if part
        )
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
                "page_actions": (
                    _build_order_action_forms(
                        order=order,
                        back_href=back_href,
                        order_number=order_number,
                        csrf_token=get_token(self.request),
                    )
                    if can_manage_orders
                    else format_html(
                        '<div class="flex flex-wrap items-center gap-3">'
                        '<a href="{}" class="ds-btn ds-btn-secondary ds-btn-md">Voltar</a>'
                        '<span class="text-sm text-[var(--color-text-secondary)]">Sem permissão para alterar pedidos</span>'
                        '</div>',
                        back_href,
                    )
                ),
                "order_number": f'#{order["order_number"]}',
                "summary_subtitle": order.get("inventory_exception_marker_label")
                or order.get("inventory_exception_aging_label")
                or order.get("inventory_exception_priority_label")
                or order.get("inventory_exception_guidance_label")
                or order.get("next_step_label"),
                "payment_status": order["payment_status"],
                "shipping_status": order["shipping_status"],
                "summary_content": order["summary_content"],
                "customer_content": order["customer_content"],
                "payment_content": order["payment_content"],
                "shipping_content": order["shipping_content"],
                "notes_content": " ".join(
                    part
                    for part in [
                        order.get("next_step_helper", ""),
                        order.get("inventory_visibility_content", ""),
                        order.get("inventory_exception_content", ""),
                        order.get("inventory_exception_aging_helper", ""),
                        order.get("inventory_exception_priority_helper", ""),
                        order.get("inventory_exception_marker_helper", ""),
                        order.get("inventory_exception_owner_helper", ""),
                        order.get("inventory_exception_guidance_helper", ""),
                        order.get("blocked_action_guidance", ""),
                        order["notes_content"],
                    ]
                    if part
                ),
                "order_items": order["order_items"],
                "subtotal": order["subtotal"],
                "shipping": order["shipping"],
                "discount": order["discount"],
                "coupon_visible": bool(order.get("coupon_visible")),
                "coupon_code": order.get("coupon_code", ""),
                "coupon_title": order.get("coupon_title", ""),
                "coupon_description": order.get("coupon_description", ""),
                "installments": order["installments"],
                "total": order["total"],
                "summary_note": (
                    order.get("inventory_exception_aging_helper")
                    or order.get("inventory_exception_priority_helper")
                    or order.get("inventory_exception_guidance_helper")
                    or order.get("next_step_helper")
                ),
                "activity_items": order["activity_items"],
            }
        )
        return context


class AdminOrderActionView(View):
    @staticmethod
    def _resolve_actor_label(request) -> str:
        user = getattr(request, "user", None)
        if user is None:
            return "Operação interna"
        try:
            if getattr(user, "is_authenticated", False):
                full_name = str(getattr(user, "get_full_name", lambda: "")() or "").strip()
                if full_name:
                    return full_name
                for attr in ("username", "email"):
                    value = str(getattr(user, attr, "") or "").strip()
                    if value:
                        return value
        except Exception:
            return "Operação interna"
        return "Operação interna"

    def post(self, request, *args, **kwargs):
        order_number = kwargs["order_number"]
        tenant_id = getattr(getattr(request, "tenant", None), "id", None)
        action_type = str(request.POST.get("action_type", "") or "").strip()
        next_url = str(request.POST.get("next", "") or "").strip()
        order_numbers = _parse_bulk_order_numbers(str(request.POST.get("order_numbers", "") or ""))
        actor_label = self._resolve_actor_label(request)
        actor_role = request_owner_role(request)
        if action_type == "order_status":
            _, result = admin_order_commands.update_order_status(
                order_number=order_number,
                status=str(request.POST.get("status", "") or "").strip(),
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "fulfillment_status":
            _, result = admin_order_commands.update_fulfillment_status(
                order_number=order_number,
                fulfillment_status=str(request.POST.get("fulfillment_status", "") or "").strip(),
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "start_fulfillment":
            _, result = admin_order_commands.start_fulfillment(
                order_number=order_number,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "start_shipping":
            _, result = admin_order_commands.start_shipping(
                order_number=order_number,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "complete_delivery":
            _, result = admin_order_commands.complete_delivery(
                order_number=order_number,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "cancel_order":
            _, result = admin_order_commands.cancel_order(
                order_number=order_number,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "mark_inventory_exception_under_review":
            _, result = admin_order_commands.mark_inventory_exception_under_review(
                order_number=order_number,
                actor_label=actor_label,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "mark_inventory_exception_resolved":
            _, result = admin_order_commands.mark_inventory_exception_resolved(
                order_number=order_number,
                actor_label=actor_label,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "reassign_inventory_exception_owner":
            _, result = admin_order_commands.reassign_inventory_exception_owner(
                order_number=order_number,
                actor_label=actor_label,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "bulk_mark_inventory_exception_under_review":
            _, result = admin_order_commands.bulk_mark_inventory_exception_under_review(
                order_numbers=order_numbers,
                actor_label=actor_label,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        elif action_type == "bulk_mark_inventory_exception_resolved":
            _, result = admin_order_commands.bulk_mark_inventory_exception_resolved(
                order_numbers=order_numbers,
                actor_label=actor_label,
                tenant_id=tenant_id,
                actor_role=actor_role,
            )
        else:
            result = "order-status-invalid"
        list_base_url = reverse("orders:admin-orders-list")
        if next_url and next_url.startswith(list_base_url):
            return HttpResponseRedirect(_append_result_to_url(next_url, result))
        return HttpResponseRedirect(
            f'{reverse("orders:admin-orders-detail", kwargs={"order_number": order_number})}?result={result}'
        )
