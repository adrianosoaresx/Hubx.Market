from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.paginator import Paginator
from django.conf import settings
from django.http import HttpResponseRedirect
from django.http import HttpResponse, HttpResponseNotFound
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.safestring import mark_safe
from django.views import View
from django.views.generic import TemplateView

from app.modules.shipping.application.admin_shipment_queries import AdminShipmentItem, admin_shipment_queries
from app.modules.shipping.application.admin_provider_settings import admin_provider_settings
from app.modules.shipping.application.shipment_commands import shipment_commands
from app.modules.shipping.application.shipping_metrics_queries import shipping_metrics_queries


def _request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)


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


def _build_page_items(page_number: int, total_pages: int, base_url: str, query_params: list[str]) -> list[dict[str, object]]:
    suffix = "&".join(query_params)
    return [
        {
            "number": number,
            "url": f"{base_url}?{suffix + '&' if suffix else ''}page={number}",
        }
        for number in range(1, total_pages + 1)
    ]


def _action_feedback(result: str) -> str:
    return {
        "shipment-sent": "Remessa marcada como enviada e evento logístico publicado.",
        "shipment-sent-already-recorded": "Nenhuma alteração aplicada: remessa já estava enviada ou entregue.",
        "shipment-delivered": "Entrega confirmada e evento logístico publicado.",
        "shipment-delivered-already-recorded": "Nenhuma alteração aplicada: entrega já estava confirmada.",
        "shipment-delivery-blocked": "Entrega bloqueada: marque a remessa como enviada antes de concluir.",
        "shipment-order-not-found": "Ação ignorada: pedido não encontrado neste tenant.",
        "shipment-not-found": "Ação ignorada: shipment ainda não existe para este pedido.",
        "shipment-action-invalid": "Ação ignorada: operação logística inválida.",
        "provider-settings-updated": "Configuração do provider de tracking atualizada.",
        "provider-settings-base-url-required": "Informe a base URL para ativar o provider HTTP.",
        "provider-settings-timeout-invalid": "Timeout inválido: informe um número maior que zero.",
        "provider-settings-invalid-provider": "Provider inválido.",
        "provider-settings-tenant-missing": "Tenant ausente: configuração não aplicada.",
    }.get(result, "")


def _shipment_status_label(status: str) -> str:
    return {
        "missing": "Sem shipment",
        "created": "Criado",
        "in_transit": "Em trânsito",
        "sent": "Enviado",
        "delivered": "Entregue",
        "canceled": "Cancelado",
        "unknown": "Status externo não mapeado",
    }.get(status, status or "Indisponível")


def _shipment_tracking_cell(item: AdminShipmentItem) -> str:
    details = " · ".join(part for part in [item.carrier_name, item.tracking_code] if part)
    return details or "Sem rastreio"


def _shipment_history_cell(item: AdminShipmentItem) -> str:
    if not item.history_summary:
        return "Sem histórico"
    return format_html(
        '<div class="space-y-1">{}</div>',
        format_html_join(
            "",
            '<div class="text-xs text-[var(--color-text-secondary)]">{}</div>',
            ((entry,) for entry in item.history_summary),
        ),
    )


def _shipment_actions_cell(item: AdminShipmentItem, *, current_url: str) -> str:
    action_url = reverse("shipping:admin-shipping-action", kwargs={"order_number": item.order_number})
    if item.shipment_status in {"missing", "created"}:
        return format_html(
            '<form method="post" action="{}" class="flex flex-col gap-2">'
            '<input type="hidden" name="action_type" value="mark_sent" />'
            '<input type="hidden" name="next" value="{}" />'
            '<input name="tracking_code" class="rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm" placeholder="Código de rastreio" />'
            '<input name="carrier_name" class="rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm" placeholder="Transportadora" />'
            '<button type="submit" class="ds-btn-secondary">Marcar enviado</button>'
            "</form>",
            action_url,
            current_url,
        )
    if item.shipment_status == "sent":
        return format_html(
            '<form method="post" action="{}" class="inline-flex">'
            '<input type="hidden" name="action_type" value="mark_delivered" />'
            '<input type="hidden" name="next" value="{}" />'
            '<button type="submit" class="ds-btn-secondary">Confirmar entrega</button>'
            "</form>",
            action_url,
            current_url,
        )
    return "Sem ação pendente"


def _resolve_next_target(*, request, result: str) -> str:
    default_target = reverse("shipping:admin-shipping-list")
    next_target = str(request.POST.get("next", "") or "").strip()
    if not next_target:
        return _append_result_param(default_target, result)
    if not url_has_allowed_host_and_scheme(next_target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return _append_result_param(default_target, result)
    expected_prefix = reverse("shipping:admin-shipping-list")
    if not next_target.startswith(expected_prefix):
        return _append_result_param(default_target, result)
    return _append_result_param(next_target, result)


class AdminShippingListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        result = self.request.GET.get("result", "").strip()
        shipments = admin_shipment_queries.list_shipments(tenant_id=_request_tenant_id(self.request), search=search_value)
        paginator = Paginator(shipments, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("shipping:admin-shipping-list")
        query_params = []
        if search_value:
            query_params.append(urlencode({"q": search_value}))
        context.update(
            {
                "page_title": "Shipping",
                "page_eyebrow": "Operação",
                "page_description": "Marque envio e entrega a partir de shipments tenant-scoped.",
                "page_meta": _action_feedback(result),
                "filter_action": base_url,
                "filter_title": "Filtros",
                "filter_description": "Busque por número do pedido, cliente ou e-mail.",
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar pedidos",
                "search_placeholder": "Pedido, nome ou e-mail",
                "reset_url": base_url,
                "columns": [
                    {"label": "Pedido"},
                    {"label": "Cliente"},
                    {"label": "Pedido"},
                    {"label": "Shipment"},
                    {"label": "Rastreio"},
                    {"label": "Histórico"},
                    {"label": "Ações"},
                ],
                "rows": [
                    {
                        "cells": [
                            f"#{item.order_number}",
                            item.customer_email or "Cliente não informado",
                            item.order_status or "Indisponível",
                            _shipment_status_label(item.shipment_status),
                            _shipment_tracking_cell(item),
                            _shipment_history_cell(item),
                            _shipment_actions_cell(item, current_url=self.request.get_full_path()),
                        ]
                    }
                    for item in page_obj.object_list
                ],
                "table_title": "Operação logística",
                "table_description": "Ações internas que acionam os eventos shipment.sent e shipment.delivered.",
                "table_count": f"{paginator.count} pedido(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": None,
                "next_url": None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "empty_title": "Nenhum pedido encontrado",
                "empty_description": "Este tenant ainda não possui pedidos para operação logística.",
            }
        )
        return context


class AdminShippingActionView(View):
    def post(self, request, order_number: str):
        action_type = str(request.POST.get("action_type", "") or "").strip()
        if action_type == "mark_sent":
            result = shipment_commands.mark_shipment_sent(
                tenant_id=_request_tenant_id(request),
                order_number=order_number,
                tracking_code=request.POST.get("tracking_code", ""),
                tracking_url=request.POST.get("tracking_url", ""),
                carrier_name=request.POST.get("carrier_name", ""),
            )
        elif action_type == "mark_delivered":
            result = shipment_commands.mark_shipment_delivered(
                tenant_id=_request_tenant_id(request),
                order_number=order_number,
            )
        else:
            result = "shipment-action-invalid"
        return HttpResponseRedirect(_resolve_next_target(request=request, result=result))


def _provider_settings_form_cell(settings_item, *, current_url: str) -> str:
    action_url = reverse("shipping:admin-shipping-provider-update")
    active_checked = mark_safe(' checked="checked"') if settings_item.is_active else ""
    manual_selected = mark_safe(' selected="selected"') if settings_item.provider_name == "manual" else ""
    http_selected = mark_safe(' selected="selected"') if settings_item.provider_name == "http" else ""
    token_placeholder = "Token já configurado; preencha apenas para trocar" if settings_item.token_configured else "Novo token opcional"
    return format_html(
        '<form method="post" action="{}" class="grid gap-2 md:grid-cols-2">'
        '<input type="hidden" name="next" value="{}" />'
        '<label class="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">Provider'
        '<select name="provider_name" class="rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm">'
        '<option value="manual"{}>Manual/local</option>'
        '<option value="http"{}>HTTP</option>'
        '</select></label>'
        '<label class="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">Base URL'
        '<input name="base_url" value="{}" class="rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm" placeholder="https://provider.example" /></label>'
        '<label class="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">Token'
        '<input name="api_token" value="" class="rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm" placeholder="{}" /></label>'
        '<label class="flex flex-col gap-1 text-xs text-[var(--color-text-secondary)]">Timeout'
        '<input name="timeout_seconds" value="{}" class="rounded-lg border border-[var(--color-border-primary)] bg-[var(--color-surface-raised)] px-3 py-2 text-sm" /></label>'
        '<label class="flex items-center gap-2 text-sm text-[var(--color-text-primary)] md:col-span-2">'
        '<input type="checkbox" name="is_active" value="1"{} /> Ativo'
        '</label>'
        '<button type="submit" class="ds-btn-secondary md:col-span-2">Salvar provider</button>'
        '</form>',
        action_url,
        current_url,
        manual_selected,
        http_selected,
        settings_item.base_url,
        token_placeholder,
        settings_item.timeout_seconds,
        active_checked,
    )


def _provider_settings_history_cell(settings_item) -> str:
    if not settings_item.history_summary:
        return "Sem histórico"
    return format_html(
        '<div class="space-y-1">{}</div>',
        format_html_join(
            "",
            '<div class="text-xs text-[var(--color-text-secondary)]">{}</div>',
            ((entry,) for entry in settings_item.history_summary),
        ),
    )


class AdminShippingProviderSettingsView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.request.GET.get("result", "").strip()
        settings_item = admin_provider_settings.get_settings_item(tenant_id=_request_tenant_id(self.request))
        base_url = reverse("shipping:admin-shipping-provider")
        context.update(
            {
                "page_title": "Provider de tracking",
                "page_eyebrow": "Shipping",
                "page_description": "Configure o provider tenant-scoped usado pelo polling de tracking.",
                "page_meta": _action_feedback(result),
                "columns": [
                    {"label": "Modo atual"},
                    {"label": "Base URL"},
                    {"label": "Token"},
                    {"label": "Ativo"},
                    {"label": "Histórico"},
                    {"label": "Configuração"},
                ],
                "rows": [
                    {
                        "cells": [
                            settings_item.mode_label,
                            settings_item.base_url or "Provider manual/local",
                            "Configurado" if settings_item.token_configured else "Não configurado",
                            "Sim" if settings_item.is_active else "Não",
                            _provider_settings_history_cell(settings_item),
                            _provider_settings_form_cell(settings_item, current_url=self.request.get_full_path()),
                        ]
                    }
                ],
                "table_title": "Configuração de provider",
                "table_description": "Quando inativo ou incompleto, o shipping usa o provider manual/local.",
                "table_count": "1 configuração",
                "page": 1,
                "total_pages": 1,
                "prev_url": None,
                "next_url": None,
                "page_items": _build_page_items(1, 1, base_url, []),
                "empty_title": "Configuração indisponível",
                "empty_description": "Não foi possível carregar a configuração deste tenant.",
            }
        )
        return context


class AdminShippingProviderSettingsActionView(View):
    def post(self, request):
        result = admin_provider_settings.update_settings(
            tenant_id=_request_tenant_id(request),
            provider_name=request.POST.get("provider_name", ""),
            base_url=request.POST.get("base_url", ""),
            api_token=request.POST.get("api_token", ""),
            timeout_seconds=request.POST.get("timeout_seconds", ""),
            is_active=str(request.POST.get("is_active", "")).strip() == "1",
        )
        default_target = reverse("shipping:admin-shipping-provider")
        next_target = str(request.POST.get("next", "") or "").strip()
        if not next_target or not url_has_allowed_host_and_scheme(next_target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
            next_target = default_target
        if not next_target.startswith(default_target):
            next_target = default_target
        return HttpResponseRedirect(_append_result_param(next_target, result))


class ShippingMetricsView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        configured_token = str(
            getattr(settings, "SHIPPING_OBSERVABILITY_TOKEN", "")
            or getattr(settings, "NOTIFICATIONS_OBSERVABILITY_TOKEN", "")
            or ""
        ).strip()
        if not configured_token:
            return HttpResponseNotFound("Métricas de shipping indisponíveis.")

        provided_token = str(request.headers.get("X-Hubx-Observability-Token", "") or "").strip()
        if not provided_token:
            authorization_header = str(request.headers.get("Authorization", "") or "").strip()
            if authorization_header.lower().startswith("bearer "):
                provided_token = authorization_header[7:].strip()
        if provided_token != configured_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

        return HttpResponse(
            shipping_metrics_queries.export_prometheus_metrics(),
            status=200,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )
