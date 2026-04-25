from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_owner_commands import admin_owner_commands
from app.modules.accounts.application.admin_owner_queries import AdminOwnerItem, admin_owner_queries


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
        "owner-notifications-enabled": "Notificações administrativas ativadas para este owner.",
        "owner-notifications-disabled": "Notificações administrativas desativadas para este owner.",
        "owner-notifications-unchanged": "Nenhuma alteração aplicada: preferência já estava nesse estado.",
        "owner-not-found": "Atualização ignorada: owner não encontrado neste tenant.",
    }.get(result, "")


def _owner_status_cell(owner: AdminOwnerItem) -> str:
    if not owner.is_active:
        return "Inativo"
    return "Ativo"


def _owner_notification_cell(owner: AdminOwnerItem) -> str:
    return "Recebe notificações" if owner.receives_notifications else "Notificações pausadas"


def _owner_actions_cell(owner: AdminOwnerItem, *, current_url: str) -> str:
    action_url = reverse("owners:admin-owner-update", kwargs={"owner_id": owner.id})
    next_value = "0" if owner.receives_notifications else "1"
    label = "Pausar notificações" if owner.receives_notifications else "Ativar notificações"
    return format_html(
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="receives_notifications" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn-secondary">{}</button>'
        "</form>",
        action_url,
        next_value,
        current_url,
        label,
    )


def _resolve_next_target(*, request, result: str) -> str:
    default_target = reverse("owners:admin-owners-list")
    next_target = str(request.POST.get("next", "") or "").strip()
    if not next_target:
        return _append_result_param(default_target, result)
    if not url_has_allowed_host_and_scheme(next_target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return _append_result_param(default_target, result)
    expected_prefix = reverse("owners:admin-owners-list")
    if not next_target.startswith(expected_prefix):
        return _append_result_param(default_target, result)
    return _append_result_param(next_target, result)


class AdminOwnersListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        result = self.request.GET.get("result", "").strip()
        owners = admin_owner_queries.list_owners(tenant_id=_request_tenant_id(self.request), search=search_value)
        paginator = Paginator(owners, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("owners:admin-owners-list")
        query_params = []
        if search_value:
            query_params.append(urlencode({"q": search_value}))

        context.update(
            {
                "page_title": "Owners",
                "page_eyebrow": "Administração",
                "page_description": "Gerencie owners administrativos habilitados para notificações operacionais.",
                "page_meta": _action_feedback(result),
                "filter_action": base_url,
                "filter_title": "Filtros",
                "filter_description": "Busque owners por e-mail.",
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar owners",
                "search_placeholder": "E-mail do owner",
                "reset_url": base_url,
                "columns": [
                    {"label": "Owner"},
                    {"label": "Papel"},
                    {"label": "Status"},
                    {"label": "Notificações"},
                    {"label": "Ações"},
                ],
                "rows": [
                    {
                        "cells": [
                            owner.email,
                            owner.role,
                            _owner_status_cell(owner),
                            _owner_notification_cell(owner),
                            _owner_actions_cell(owner, current_url=self.request.get_full_path()),
                        ]
                    }
                    for owner in page_obj.object_list
                ],
                "table_title": "Owners administrativos",
                "table_description": "Owners por tenant usados como destinatários administrativos futuros.",
                "table_count": f"{paginator.count} owner(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": None,
                "next_url": None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "empty_title": "Nenhum owner encontrado",
                "empty_description": "Este tenant ainda não possui owners administrativos persistidos para operação.",
            }
        )
        return context


class AdminOwnerActionView(View):
    def post(self, request, owner_id: int):
        receives_notifications = str(request.POST.get("receives_notifications", "")).strip() == "1"
        result = admin_owner_commands.set_notification_preference(
            tenant_id=_request_tenant_id(request),
            owner_id=owner_id,
            receives_notifications=receives_notifications,
        )
        return HttpResponseRedirect(_resolve_next_target(request=request, result=result))
