from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView, View

from app.modules.accounts.application.account_address_commands import account_address_commands
from app.modules.accounts.application.account_page_queries import account_page_queries
from app.modules.accounts.application.account_customer_area_queries import (
    account_customer_area_queries,
)
from app.modules.orders.application.customer_order_payment_commands import (
    customer_order_payment_commands,
)
from .forms import AccountAddressForm


def _quick_links() -> list[dict[str, str]]:
    return [
        {"href": reverse("accounts:account-orders"), "label": "Ver pedidos", "description": "Acompanhe status, entrega e histórico."},
        {"href": reverse("accounts:account-addresses"), "label": "Gerenciar endereços", "description": "Atualize entregas e cobrança."},
        {"href": reverse("accounts:account-profile"), "label": "Editar perfil", "description": "Revise dados pessoais e preferências."},
    ]

def _build_page_items(page_number: int, total_pages: int, base_url: str, query_params: list[str]) -> list[dict[str, object]]:
    suffix = "&".join(query_params)
    return [
        {
            "number": number,
            "url": f"{base_url}?{suffix + '&' if suffix else ''}page={number}",
        }
        for number in range(1, total_pages + 1)
    ]


def _build_account_address_management_url(action: str, address_id: int | None = None) -> str:
    if action == "create":
        return reverse("accounts:account-address-create")
    if action == "edit" and address_id is not None:
        return reverse("accounts:account-address-edit", kwargs={"address_id": address_id})
    if action == "delete" and address_id is not None:
        return reverse("accounts:account-address-delete", kwargs={"address_id": address_id})
    return reverse("accounts:account-addresses")


def _extract_address_id(address: dict[str, object]) -> int | None:
    raw_value = address.get("address_id")
    if raw_value not in (None, ""):
        try:
            return int(raw_value)
        except (TypeError, ValueError):
            return None

    for key in ("edit_href", "remove_href"):
        raw_href = str(address.get(key, "") or "")
        marker = "address-"
        if marker in raw_href:
            suffix = raw_href.split(marker, 1)[1]
            digits = ""
            for char in suffix:
                if char.isdigit():
                    digits += char
                else:
                    break
            if digits:
                return int(digits)
    return None


def _address_form_state(form: AccountAddressForm) -> dict[str, object]:
    def field_value(name: str) -> object:
        return form[name].value() if name in form.fields else ""

    def field_error(name: str) -> str:
        if name not in form.fields:
            return ""
        return form.errors.get(name, [""])[0]

    return {
        "values": {
            "label": field_value("label"),
            "recipient_name": field_value("recipient_name"),
            "line_1": field_value("line_1"),
            "line_2": field_value("line_2"),
            "district": field_value("district"),
            "city": field_value("city"),
            "state": field_value("state"),
            "postal_code": field_value("postal_code"),
            "is_default": bool(field_value("is_default")),
        },
        "errors": {
            "label": field_error("label"),
            "recipient_name": field_error("recipient_name"),
            "line_1": field_error("line_1"),
            "line_2": field_error("line_2"),
            "district": field_error("district"),
            "city": field_error("city"),
            "state": field_error("state"),
            "postal_code": field_error("postal_code"),
            "is_default": field_error("is_default"),
        },
        "non_field_errors": list(form.non_field_errors()),
        "is_bound": form.is_bound,
    }


def _build_address_form_context(request, *, form: AccountAddressForm | None = None, intent: str | None = None, address_id: int | None = None) -> dict[str, object]:
    resolved_intent = intent or request.GET.get("intent", "").strip()
    resolved_address_id = address_id
    if resolved_address_id is None:
        raw_address_id = request.GET.get("address_id", "").strip()
        if raw_address_id.isdigit():
            resolved_address_id = int(raw_address_id)

    if resolved_intent not in {"create", "edit"}:
        return {}

    if form is None:
        initial = {}
        if resolved_intent == "edit" and resolved_address_id is not None:
            initial = account_address_commands.get_address_initial(resolved_address_id) or {}
        form = AccountAddressForm(initial=initial)

    form_action = (
        reverse("accounts:account-address-create")
        if resolved_intent == "create"
        else reverse("accounts:account-address-edit", kwargs={"address_id": resolved_address_id or 0})
    )
    context = {
        "address_form": _address_form_state(form),
        "address_form_mode": resolved_intent,
        "address_form_title": "Adicionar endereço" if resolved_intent == "create" else "Editar endereço",
        "address_form_description": (
            "Cadastre um novo endereço para futuras compras."
            if resolved_intent == "create"
            else "Atualize os dados do endereço salvo."
        ),
        "address_form_action": form_action,
        "address_form_cancel_href": reverse("accounts:account-addresses"),
    }
    if form.is_bound and not form.is_valid():
        context["address_feedback"] = {
            "variant": "danger",
            "icon": "⚠️",
            "title": "Revise os campos do endereço",
            "description": "Algumas informações precisam ser corrigidas antes de salvar.",
        }
    return context


def _build_address_delete_context(request) -> dict[str, object]:
    intent = request.GET.get("intent", "").strip()
    raw_address_id = request.GET.get("address_id", "").strip()
    if intent != "delete" or not raw_address_id.isdigit():
        return {}
    address_id = int(raw_address_id)
    summary = account_address_commands.get_address_summary(address_id)
    if summary is None:
        return {}
    return {
        "address_delete": summary,
        "address_delete_action": reverse("accounts:account-address-delete", kwargs={"address_id": address_id}),
        "address_delete_cancel_href": reverse("accounts:account-addresses"),
    }


def _build_address_feedback_context(request) -> dict[str, object]:
    result = request.GET.get("result", "").strip()
    mapping = {
        "address-created": {
            "variant": "success",
            "icon": "✅",
            "title": "Endereço salvo",
            "description": "O novo endereço já está disponível para suas próximas compras.",
        },
        "address-updated": {
            "variant": "success",
            "icon": "✅",
            "title": "Endereço atualizado",
            "description": "As alterações foram salvas com sucesso.",
        },
        "address-deleted": {
            "variant": "success",
            "icon": "🗑️",
            "title": "Endereço removido",
            "description": "O endereço foi removido da sua conta.",
        },
        "address-delete-blocked": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Endereço não removido",
            "description": "Só é possível remover endereços vinculados à conta atual.",
        },
    }
    if result not in mapping:
        return {}
    return {"address_feedback": mapping[result]}


def _build_order_detail_feedback_context(request) -> dict[str, object]:
    result = request.GET.get("result", "").strip()
    mapping = {
        "checkout-completed": {
            "variant": "success",
            "icon": "✅",
            "title": "Pedido gerado com sucesso",
            "description": "Seu pedido já foi persistido e agora pode ser acompanhado por aqui enquanto o fluxo de pagamento evolui.",
        },
        "payment-confirmed": {
            "variant": "success",
            "icon": "💳",
            "title": "Pagamento confirmado",
            "description": "A confirmação interna do pagamento já liberou a preparação do pedido e as próximas atualizações de envio.",
        },
        "payment-already-confirmed": {
            "variant": "info",
            "icon": "ℹ️",
            "title": "Pagamento já confirmado",
            "description": "Este pedido já estava em um estado confirmado, então nenhuma nova alteração foi necessária.",
        },
        "payment-confirmation-blocked": {
            "variant": "warning",
            "icon": "🧩",
            "title": "Confirmação não disponível",
            "description": "Este pedido já avançou além da etapa inicial de pagamento ou não pode mais receber essa confirmação.",
        },
        "payment-confirmation-unavailable": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Não foi possível confirmar o pagamento",
            "description": "Não encontramos um pedido elegível para esta conta agora. Recarregue a página ou tente novamente mais tarde.",
        },
        "payment-confirmation-inventory-link-missing": {
            "variant": "warning",
            "icon": "🧩",
            "title": "Vínculo de estoque incompleto",
            "description": "Este pedido não possui ligação segura com a variante vendável necessária para confirmar o pagamento com impacto de estoque.",
        },
        "payment-confirmation-inventory-unavailable": {
            "variant": "warning",
            "icon": "📦",
            "title": "Variante indisponível",
            "description": "A variante ligada a este pedido não está mais disponível para confirmação segura de pagamento.",
        },
        "payment-confirmation-stock-conflict": {
            "variant": "warning",
            "icon": "⚠️",
            "title": "Estoque insuficiente para confirmar",
            "description": "O saldo livre atual da variante não é suficiente para aplicar a reserva operacional deste pedido.",
        },
    }
    if result not in mapping:
        return {}
    return {"page_feedback": mapping[result]}


def _build_order_detail_actions(request, context: dict[str, object], *, order_number: str) -> dict[str, object]:
    if not context.get("payment_progression_available"):
        return {}
    csrf_token = get_token(request)
    action_html = format_html(
        '<div class="flex flex-col items-stretch gap-2 md:items-end">'
        '  <form method="post" action="{}" class="inline-flex">'
        '    <input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '    <input type="hidden" name="action_type" value="confirm_payment">'
        '    <button type="submit" class="ds-btn-primary">{}</button>'
        "  </form>"
        '  <p class="text-right text-xs text-[var(--color-text-secondary)]">{}</p>'
        "</div>",
        reverse("accounts:account-order-detail", kwargs={"order_number": order_number}),
        csrf_token,
        str(context.get("payment_progression_label") or "Confirmar pagamento"),
        str(context.get("payment_progression_helper") or ""),
    )
    return {"page_actions": mark_safe(action_html)}


class LoginView(TemplateView):
    template_name = "pages/templates/login_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_page_queries.get_login_page_data())
        context["form_action"] = self.request.path
        context["register_href"] = reverse("accounts:register")
        context["forgot_password_href"] = reverse("accounts:forgot-password")
        return context


class RegisterView(TemplateView):
    template_name = "pages/templates/register_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_page_queries.get_register_page_data())
        context["form_action"] = self.request.path
        context["login_href"] = reverse("accounts:login")
        return context


class ForgotPasswordView(TemplateView):
    template_name = "pages/templates/forgot_password_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_page_queries.get_forgot_password_page_data())
        context["form_action"] = self.request.path
        context["login_href"] = reverse("accounts:login")
        return context


class ResetPasswordView(TemplateView):
    template_name = "pages/templates/reset_password_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_page_queries.get_reset_password_page_data())
        context["form_action"] = self.request.path
        context["login_href"] = reverse("accounts:login")
        return context


class AccountOverviewView(TemplateView):
    template_name = "pages/templates/account_overview_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_page_queries.get_account_overview_data())
        context["quick_links"] = _quick_links()
        return context


class AccountOrdersView(TemplateView):
    template_name = "pages/templates/orders_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        base_payload = account_customer_area_queries.get_orders_page_data()
        orders = account_customer_area_queries.list_orders()
        if search_value:
            lowered = search_value.lower()
            orders = [
                order
                for order in orders
                if lowered in str(order["order_number"]).lower()
                or lowered in str(order["order_status_label"]).lower()
            ]
        if status_selected:
            orders = [order for order in orders if order["status"] == status_selected]

        paginator = Paginator(orders, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("accounts:account-orders")

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
                **base_payload,
                "search_value": search_value,
                "status_selected": status_selected,
                "reset_url": base_url,
                "rows": [
                    {
                        "cells": [
                            f'#{order["order_number"]}',
                            (
                                f'{order.get("order_status_summary", order["order_status_label"])}'
                                + (
                                    f' · {order["recent_update_hint"].lower()}'
                                    if order.get("recent_update_hint")
                                    else ""
                                )
                                + (
                                    f' · {order["reengagement_hint"]}'
                                    if order.get("reengagement_hint")
                                    else ""
                                )
                            ),
                            order["payment_status"],
                            order["shipping_status"],
                            f'Atualizado em {order["updated_at"]}',
                        ]
                    }
                    for order in page_obj.object_list
                ],
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
            }
        )
        return context


class AccountOrderDetailView(TemplateView):
    template_name = "pages/templates/order_detail_page.html"

    def post(self, request, *args, **kwargs):
        if request.POST.get("action_type", "").strip() != "confirm_payment":
            return HttpResponseRedirect(
                reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})
            )
        profile = account_customer_area_queries.get_active_profile_context()
        result = customer_order_payment_commands.confirm_internal_payment(
            tenant_id=profile.get("tenant_id"),
            customer_id=profile.get("customer_id"),
            email=str(profile.get("email") or ""),
            order_number=kwargs["order_number"],
        )
        return HttpResponseRedirect(
            f'{reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})}?result={result}'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        confirmation_mode = self.request.GET.get("result", "").strip() == "checkout-completed"
        context.update(
            account_customer_area_queries.get_order_detail_page_data(
                kwargs["order_number"],
                confirmation_mode=confirmation_mode,
            )
        )
        context.update(_build_order_detail_actions(self.request, context, order_number=kwargs["order_number"]))
        context.update(_build_order_detail_feedback_context(self.request))
        return context


class AccountAddressesView(TemplateView):
    template_name = "pages/templates/addresses_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_payload = account_customer_area_queries.get_addresses_page_data()
        base_url = reverse("accounts:account-addresses")
        addresses = []
        for address in base_payload["addresses"]:
            address_id = _extract_address_id(address)
            edit_href = _build_account_address_management_url("edit", address_id) if address_id else f"{base_url}#edit-address"
            remove_href = _build_account_address_management_url("delete", address_id) if address_id else f"{base_url}#remove-address"
            addresses.append(
                {
                    "title": address["title"],
                    "subtitle": address["subtitle"],
                    "content": address["content"],
                    "footer": address["footer"],
                    "actions": format_html(
                        '<div class="flex gap-3">'
                        '<a href="{}" class="text-sm font-medium text-[var(--color-action-primary-bg)] hover:underline">Editar</a>'
                        '<a href="{}" class="text-sm font-medium text-rose-600 hover:underline">Remover</a>'
                        "</div>",
                        edit_href,
                        remove_href,
                    ),
                }
            )
        context.update(
            {
                "page_title": base_payload["page_title"],
                "page_description": base_payload["page_description"],
                "page_actions": mark_safe(
                    f'<a href="{_build_account_address_management_url("create")}" class="ds-btn-primary">Adicionar endereço</a>'
                ),
                "addresses": addresses,
                "primary_action": mark_safe(
                    f'<a href="{_build_account_address_management_url("create")}" class="ds-btn-primary">Adicionar endereço</a>'
                ),
            }
        )
        context.update(_build_address_feedback_context(self.request))
        context.update(_build_address_form_context(self.request))
        context.update(_build_address_delete_context(self.request))
        return context


class AccountProfileView(TemplateView):
    template_name = "pages/templates/profile_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_customer_area_queries.get_profile_page_data())
        context["form_action"] = self.request.path
        context["secondary_href"] = reverse("accounts:account-overview")
        return context


class _AccountAddressReadyRedirectView(View):
    intent = "manage"

    def get_redirect_url(self, **kwargs) -> str:
        base_url = reverse("accounts:account-addresses")
        address_id = kwargs.get("address_id")
        if address_id is not None:
            return f"{base_url}?intent={self.intent}&address_id={address_id}#address-management"
        return f"{base_url}?intent={self.intent}#address-management"

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(self.get_redirect_url(**kwargs))

    def _render_form_page(self, request, *, form: AccountAddressForm, address_id: int | None = None):
        view = AccountAddressesView()
        view.setup(request)
        context = view.get_context_data()
        context.update(_build_address_form_context(request, form=form, intent=self.intent, address_id=address_id))
        return view.render_to_response(context)


class AccountAddressCreateReadyView(_AccountAddressReadyRedirectView):
    intent = "create"

    def post(self, request, *args, **kwargs):
        form = AccountAddressForm(request.POST)
        if not form.is_valid():
            return self._render_form_page(request, form=form)
        account_address_commands.create_address(form.cleaned_data)
        return HttpResponseRedirect(f'{reverse("accounts:account-addresses")}?result=address-created#address-management')


class AccountAddressEditReadyView(_AccountAddressReadyRedirectView):
    intent = "edit"

    def post(self, request, *args, **kwargs):
        address_id = int(kwargs["address_id"])
        form = AccountAddressForm(request.POST)
        if not form.is_valid():
            return self._render_form_page(request, form=form, address_id=address_id)
        account_address_commands.update_address(address_id, form.cleaned_data)
        return HttpResponseRedirect(f'{reverse("accounts:account-addresses")}?result=address-updated#address-management')


class AccountAddressDeleteReadyView(_AccountAddressReadyRedirectView):
    intent = "delete"

    def post(self, request, *args, **kwargs):
        address_id = int(kwargs["address_id"])
        deleted = account_address_commands.delete_address(address_id)
        result = "address-deleted" if deleted else "address-delete-blocked"
        return HttpResponseRedirect(f'{reverse("accounts:account-addresses")}?result={result}#address-management')
