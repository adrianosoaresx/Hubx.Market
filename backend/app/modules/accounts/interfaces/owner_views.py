from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.core.paginator import Paginator
from django.http import Http404, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import TemplateView

from app.modules.accounts.application.owner_access_recovery_commands import owner_access_recovery_commands
from app.modules.accounts.application.admin_owner_commands import admin_owner_commands
from app.modules.accounts.application.admin_owner_queries import AdminOwnerItem, admin_owner_queries
from app.modules.accounts.application.admin_permissions import PERMISSION_OWNERS_MANAGE, ROLE_PERMISSIONS
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.accounts.application.owner_mfa_admin_queries import OwnerMfaAdminFactorItem, owner_mfa_admin_queries
from app.modules.accounts.application.owner_mfa_challenge_commands import owner_mfa_challenge_commands
from app.modules.accounts.application.owner_mfa_enrollment_commands import owner_mfa_enrollment_commands


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _request_owner_role(request) -> str:
    return request_owner_role(request)


def _actor_label(request) -> str:
    return str(getattr(request, "user", "") or "")


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
        "owner-created": "Owner criado para este tenant.",
        "owner-updated": "Acesso do owner atualizado.",
        "owner-unchanged": "Nenhuma alteração aplicada: owner já estava nesse estado.",
        "owner-notifications-enabled": "Notificações administrativas ativadas para este owner.",
        "owner-notifications-disabled": "Notificações administrativas desativadas para este owner.",
        "owner-notifications-unchanged": "Nenhuma alteração aplicada: preferência já estava nesse estado.",
        "owner-not-found": "Atualização ignorada: owner não encontrado neste tenant.",
        "owner-permission-denied": "Permissão insuficiente para gerenciar owners.",
        "owner-invite-created": "Convite de acesso gerado para este owner.",
        "owner-invite-not-found": "Convite ignorado: owner ativo não encontrado neste tenant.",
        "owner-invite-permission-denied": "Permissão insuficiente para convidar owners.",
        "owner-invite-ambiguous-user": "Convite bloqueado: e-mail possui usuários duplicados.",
        "owner-invite-inactive-user": "Convite bloqueado: usuário Django existente está inativo.",
        "owner-mfa-factor-verified": "Fator MFA verificado para este owner.",
        "owner-mfa-factor-challenge-invalid": "Challenge MFA inválido; fator permanece pendente.",
        "owner-mfa-factor-deactivated": "Fator MFA desativado.",
        "owner-mfa-factor-unchanged": "Nenhuma alteração aplicada ao fator MFA.",
        "owner-mfa-factor-not-found": "Fator MFA não encontrado neste tenant.",
        "owner-mfa-permission-denied": "Permissão insuficiente para gerenciar MFA.",
    }.get(result, "")


def _owner_status_cell(owner: AdminOwnerItem) -> str:
    if not owner.is_active:
        return "Inativo"
    return "Ativo"


def _owner_notification_cell(owner: AdminOwnerItem) -> str:
    return "Recebe notificações" if owner.receives_notifications else "Notificações pausadas"


def _owner_actions_cell(owner: AdminOwnerItem, *, current_url: str, csrf_token: str, can_manage: bool) -> str:
    if not can_manage:
        return "Sem permissão para gerenciar owners"
    action_url = reverse("owners:admin-owner-update", kwargs={"owner_id": owner.id})
    invite_url = reverse("owners:admin-owner-invite", kwargs={"owner_id": owner.id})
    edit_url = reverse("owners:admin-owner-edit", kwargs={"owner_id": owner.id})
    next_value = "0" if owner.receives_notifications else "1"
    label = "Pausar notificações" if owner.receives_notifications else "Ativar notificações"
    return format_html(
        '<div class="flex flex-wrap gap-2">'
        '<a class="ds-btn ds-btn-secondary ds-btn-sm" href="{}">Editar acesso</a>'
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="receives_notifications" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">{}</button>'
        "</form>"
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
        '<input type="hidden" name="next" value="{}" />'
        '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Gerar convite</button>'
        "</form>"
        "</div>",
        edit_url,
        action_url,
        csrf_token,
        next_value,
        current_url,
        label,
        invite_url,
        csrf_token,
        current_url,
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


def _resolve_mfa_next_target(*, request, result: str) -> str:
    default_target = reverse("owners:admin-owner-mfa-list")
    next_target = str(request.POST.get("next", "") or "").strip()
    if not next_target:
        return _append_result_param(default_target, result)
    if not url_has_allowed_host_and_scheme(next_target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return _append_result_param(default_target, result)
    expected_prefix = reverse("owners:admin-owner-mfa-list")
    if not next_target.startswith(expected_prefix):
        return _append_result_param(default_target, result)
    return _append_result_param(next_target, result)


def _mfa_status_cell(factor: OwnerMfaAdminFactorItem) -> str:
    if not factor.is_active:
        return "Inativo"
    if factor.is_verified:
        return "Verificado"
    return "Pendente"


def _mfa_dates_cell(factor: OwnerMfaAdminFactorItem) -> str:
    if factor.verified_at:
        return f"Verificado em {factor.verified_at:%Y-%m-%d %H:%M}"
    if factor.last_challenged_at:
        return f"Última tentativa {factor.last_challenged_at:%Y-%m-%d %H:%M}"
    return "Sem challenge"


def _mfa_actions_cell(factor: OwnerMfaAdminFactorItem, *, current_url: str, csrf_token: str, can_manage: bool) -> str:
    if not can_manage:
        return "Sem permissão para gerenciar MFA"
    verify_url = reverse("owners:admin-owner-mfa-verify", kwargs={"factor_id": factor.id})
    deactivate_url = reverse("owners:admin-owner-mfa-deactivate", kwargs={"factor_id": factor.id})
    verify_form = ""
    if factor.is_active and not factor.is_verified:
        verify_form = (
            '<form method="post" action="{}" class="flex flex-wrap items-center gap-2">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<input type="hidden" name="next" value="{}" />'
            '<input class="ds-input max-w-[8rem]" name="challenge" placeholder="000000" inputmode="numeric" />'
            '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Verificar</button>'
            "</form>"
        )
    deactivate_form = ""
    if factor.is_active:
        deactivate_form = (
            '<form method="post" action="{}" class="inline-flex">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}" />'
            '<input type="hidden" name="next" value="{}" />'
            '<button type="submit" class="ds-btn ds-btn-secondary ds-btn-sm">Desativar</button>'
            "</form>"
        )
    return format_html(
        '<div class="flex flex-wrap gap-2">{}</div>',
        format_html(verify_form, verify_url, csrf_token, current_url) if verify_form else format_html(""),
    ) + format_html(
        '<div class="mt-2 flex flex-wrap gap-2">{}</div>',
        format_html(deactivate_form, deactivate_url, csrf_token, current_url) if deactivate_form else format_html(""),
    )


class AdminOwnersListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        result = self.request.GET.get("result", "").strip()
        owners = admin_owner_queries.list_owners(tenant_id=_request_tenant_id(self.request), search=search_value)
        can_manage_owners = request_admin_can(self.request, PERMISSION_OWNERS_MANAGE)
        paginator = Paginator(owners, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("owners:admin-owners-list")
        query_params = []
        if search_value:
            query_params.append(urlencode({"q": search_value}))

        context.update(
            {
                "page_title": "Administradores",
                "page_eyebrow": "Administração",
                "page_description": "Gerencie administradores habilitados para notificações operacionais.",
                "page_meta": _action_feedback(result),
                "page_actions": format_html(
                    '<a class="ds-btn ds-btn-primary ds-btn-md" href="{}">Novo owner</a>',
                    reverse("owners:admin-owner-create"),
                )
                if can_manage_owners
                else "",
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
                            _owner_actions_cell(
                                owner,
                                current_url=self.request.get_full_path(),
                                csrf_token=get_token(self.request),
                                can_manage=can_manage_owners,
                            ),
                        ]
                    }
                    for owner in page_obj.object_list
                ],
                "table_title": "Administradores da loja",
                "table_description": "Administradores por tenant usados como destinatários administrativos futuros.",
                "table_count": f"{paginator.count} administrador(es)",
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


class AdminOwnerMfaListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        result = self.request.GET.get("result", "").strip()
        factors = owner_mfa_admin_queries.list_factors(tenant_id=_request_tenant_id(self.request), search=search_value)
        can_manage_mfa = request_admin_can(self.request, PERMISSION_OWNERS_MANAGE)
        paginator = Paginator(factors, 20)
        page_obj = paginator.get_page(self.request.GET.get("page") or 1)
        base_url = reverse("owners:admin-owner-mfa-list")
        query_params = []
        if search_value:
            query_params.append(urlencode({"q": search_value}))
        current_url = self.request.get_full_path()

        context.update(
            {
                "page_title": "MFA dos owners",
                "page_eyebrow": "Acesso administrativo",
                "page_description": "Liste, verifique e desative fatores MFA de owners neste tenant.",
                "page_meta": _action_feedback(result),
                "filter_action": base_url,
                "filter_title": "Filtros",
                "filter_description": "Busque fatores MFA por e-mail do owner.",
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar owner",
                "search_placeholder": "E-mail do owner",
                "reset_url": base_url,
                "columns": [
                    {"label": "Owner"},
                    {"label": "Fator"},
                    {"label": "Status"},
                    {"label": "Datas"},
                    {"label": "Ações"},
                ],
                "rows": [
                    {
                        "cells": [
                            factor.owner_email,
                            f"{factor.factor_type} / {factor.provider_key or 'internal'}",
                            _mfa_status_cell(factor),
                            _mfa_dates_cell(factor),
                            _mfa_actions_cell(
                                factor,
                                current_url=current_url,
                                csrf_token=get_token(self.request),
                                can_manage=can_manage_mfa,
                            ),
                        ]
                    }
                    for factor in page_obj.object_list
                ],
                "table_title": "Fatores MFA",
                "table_description": "Fatores cadastrados para owners administrativos.",
                "table_count": f"{paginator.count} fator(es)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": None,
                "next_url": None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "empty_title": "Nenhum fator MFA encontrado",
                "empty_description": "Registre fatores MFA antes de verificar ou aplicar enforcement no login.",
            }
        )
        return context


class AdminOwnerMfaVerifyView(View):
    def post(self, request, factor_id: int):
        result = owner_mfa_challenge_commands.verify_factor(
            tenant_id=_request_tenant_id(request),
            factor_id=factor_id,
            challenge=request.POST.get("challenge", ""),
            actor_label=_actor_label(request),
            actor_role=_request_owner_role(request),
        )
        return HttpResponseRedirect(_resolve_mfa_next_target(request=request, result=str(result.get("result"))))


class AdminOwnerMfaDeactivateView(View):
    def post(self, request, factor_id: int):
        result = owner_mfa_enrollment_commands.deactivate_factor(
            tenant_id=_request_tenant_id(request),
            factor_id=factor_id,
            actor_label=_actor_label(request),
            actor_role=_request_owner_role(request),
        )
        return HttpResponseRedirect(_resolve_mfa_next_target(request=request, result=str(result.get("result"))))


class AdminOwnerActionView(View):
    def post(self, request, owner_id: int):
        receives_notifications = str(request.POST.get("receives_notifications", "")).strip() == "1"
        result = admin_owner_commands.set_notification_preference(
            tenant_id=_request_tenant_id(request),
            owner_id=owner_id,
            receives_notifications=receives_notifications,
            actor_label=_actor_label(request),
            actor_role=_request_owner_role(request),
        )
        return HttpResponseRedirect(_resolve_next_target(request=request, result=result))


class AdminOwnerInviteView(View):
    def post(self, request, owner_id: int):
        result = owner_access_recovery_commands.invite_owner(
            request=request,
            tenant_id=_request_tenant_id(request),
            owner_id=owner_id,
            actor_label=_actor_label(request),
            actor_role=_request_owner_role(request),
        )
        return HttpResponseRedirect(_resolve_next_target(request=request, result=str(result.get("result"))))


ROLE_OPTIONS = [
    {"value": role, "label": role.replace("_", " ").title()}
    for role in ROLE_PERMISSIONS.keys()
]


class AdminOwnerFormView(TemplateView):
    template_name = "pages/templates/admin_owner_form_page.html"

    def _owner_id(self) -> int | None:
        return self.kwargs.get("owner_id")

    def _owner(self) -> AdminOwnerItem | None:
        if self._owner_id() is None:
            return None
        return admin_owner_queries.get_owner(tenant_id=_request_tenant_id(self.request), owner_id=self._owner_id())

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None):
        owner = self._owner()
        values = values or {}
        is_edit = self._owner_id() is not None
        email = values.get("email", getattr(owner, "email", ""))
        full_name = values.get("full_name", getattr(owner, "full_name", ""))
        role_selected = values.get("role", getattr(owner, "role", "viewer"))
        is_active = values.get("is_active", "1" if getattr(owner, "is_active", True) else "0")
        receives_notifications = values.get(
            "receives_notifications",
            "1" if getattr(owner, "receives_notifications", True) else "0",
        )
        return {
            "page_title": "Editar owner" if is_edit else "Novo owner",
            "page_eyebrow": "Acesso administrativo",
            "page_description": "Gerencie papel, status e notificações administrativas por tenant.",
            "form_action": self.request.path,
            "cancel_href": reverse("owners:admin-owners-list"),
            "submit_label": "Salvar acesso" if is_edit else "Criar owner",
            "role_options": ROLE_OPTIONS,
            "email": email,
            "full_name": full_name,
            "role_selected": role_selected,
            "is_active": str(is_active),
            "receives_notifications": str(receives_notifications),
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
        }

    def get_context_data(self, **kwargs):
        if self._owner_id() is not None and self._owner() is None:
            raise Http404("Owner not found")
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        if self._owner_id() is None:
            result = admin_owner_commands.create_owner(
                tenant_id=_request_tenant_id(request),
                payload=request.POST,
                actor_label=_actor_label(request),
                actor_role=_request_owner_role(request),
            )
            success_result = "owner-created"
        else:
            result = admin_owner_commands.update_owner_access(
                tenant_id=_request_tenant_id(request),
                owner_id=self._owner_id(),
                payload=request.POST,
                actor_label=_actor_label(request),
                actor_role=_request_owner_role(request),
            )
            success_result = "owner-updated"
        if result.get("result") in {success_result, "owner-unchanged"}:
            return HttpResponseRedirect(_append_result_param(reverse("owners:admin-owners-list"), str(result.get("result"))))
        context = self.get_context_data(**kwargs)
        context.update(self._context(values=request.POST, errors=result.get("errors") or {}))
        return self.render_to_response(context, status=400)
