from __future__ import annotations

from urllib.parse import urlencode

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
from app.modules.checkout.application.checkout_reorder_commands import (
    checkout_reorder_commands,
)
from app.modules.checkout.application.checkout_payment_retry_commands import (
    checkout_payment_retry_commands,
)
from app.modules.orders.application.customer_order_payment_commands import (
    customer_order_payment_commands,
)
from .forms import AccountAddressForm


def _quick_links() -> list[dict[str, str]]:
    return [
        {"href": reverse("accounts:account-orders"), "label": "Ver pedidos", "description": "Acompanhe status, entrega e histórico."},
        {"href": reverse("storefront:catalog-list"), "label": "Voltar ao catálogo", "description": "Retome a navegação e inicie a próxima compra."},
        {"href": reverse("accounts:account-addresses"), "label": "Gerenciar endereços", "description": "Atualize entregas e cobrança."},
        {"href": reverse("accounts:account-profile"), "label": "Editar perfil", "description": "Revise dados pessoais e preferências."},
    ]


def _request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)

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
            initial = account_address_commands.get_address_initial(
                resolved_address_id,
                tenant_id=_request_tenant_id(request),
            ) or {}
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
    summary = account_address_commands.get_address_summary(address_id, tenant_id=_request_tenant_id(request))
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
        "address-create-unavailable": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Não foi possível salvar o endereço",
            "description": "A operação exige uma loja válida vinculada à conta atual antes de salvar um endereço.",
        },
        "address-update-unavailable": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Não foi possível atualizar o endereço",
            "description": "A operação exige uma loja válida vinculada à conta atual antes de atualizar um endereço.",
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
        "reorder-lite-ready": {
            "variant": "success",
            "icon": "🛒",
            "title": "Nova sessão pronta",
            "description": "Recriamos uma nova sessão com os itens elegíveis deste pedido para você revisar e seguir comprando.",
        },
        "reorder-lite-partial": {
            "variant": "info",
            "icon": "🧺",
            "title": "Nova sessão criada parcialmente",
            "description": "Alguns itens deste pedido não puderam voltar, mas os elegíveis já foram recriados em uma nova sessão para revisão.",
        },
        "reorder-lite-unavailable": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Não foi possível recriar este pedido",
            "description": "Nenhum item elegível pôde ser usado para uma nova compra agora. Revise o catálogo para montar uma nova sessão.",
        },
        "payment-retry-unavailable": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Não foi possível retomar o pagamento",
            "description": "Não encontramos um pedido elegível para nova tentativa agora. Recarregue a página ou tente novamente mais tarde.",
        },
        "payment-retry-blocked": {
            "variant": "warning",
            "icon": "🧾",
            "title": "Nova tentativa não disponível",
            "description": "Só pedidos pendentes com falha de pagamento podem abrir uma nova sessão segura nesta etapa.",
        },
        "hosted-payment-unavailable": {
            "variant": "warning",
            "icon": "ℹ️",
            "title": "Pagamento hospedado indisponível",
            "description": "Não foi possível abrir o ambiente externo de pagamento agora. Recarregue a página ou tente novamente em instantes.",
        },
        "hosted-payment-returned": {
            "variant": "info",
            "icon": "↩️",
            "title": "Retorno de pagamento recebido",
            "description": "Recebemos seu retorno do ambiente de pagamento. Agora seguimos aguardando a confirmação segura do provider.",
        },
        "hosted-payment-return-pending-verification": {
            "variant": "info",
            "icon": "🧾",
            "title": "Pagamento em verificação",
            "description": "O provider indicou sucesso no retorno, mas o pedido só avança depois da confirmação segura do evento de pagamento.",
        },
        "hosted-payment-return-failed": {
            "variant": "warning",
            "icon": "⚠️",
            "title": "Tentativa de pagamento não concluída",
            "description": "O retorno hospedado indicou falha ou cancelamento. Você pode revisar o pedido e tentar novamente com segurança.",
        },
    }
    if result not in mapping:
        return {}
    return {"page_feedback": mapping[result]}


def _build_order_detail_action_items(request, context: dict[str, object], *, order_number: str) -> list[dict[str, str]]:
    detail_action = reverse("accounts:account-order-detail", kwargs={"order_number": order_number})
    detail_back_url = reverse("accounts:account-order-detail", kwargs={"order_number": order_number})
    items: list[dict[str, str]] = []

    if context.get("reorder_lite_available"):
        items.append(
            {
                "kind": "form",
                "action": detail_action,
                "action_type": "reorder_lite",
                "button_class": "ds-btn-secondary",
                "label": str(context.get("reorder_lite_label") or "Comprar novamente"),
                "helper": str(context.get("reorder_lite_helper") or ""),
            }
        )

    if context.get("payment_progression_available"):
        items.append(
            {
                "kind": "form",
                "action": detail_action,
                "action_type": "confirm_payment",
                "button_class": "ds-btn-primary",
                "label": str(context.get("payment_progression_label") or "Confirmar pagamento"),
                "helper": str(context.get("payment_progression_helper") or ""),
            }
        )

    if context.get("payment_retry_available"):
        items.append(
            {
                "kind": "form",
                "action": detail_action,
                "action_type": "payment_retry",
                "button_class": "ds-btn-secondary",
                "label": str(context.get("payment_retry_label") or "Tentar pagamento novamente"),
                "helper": str(context.get("payment_retry_helper") or ""),
            }
        )

    if context.get("hosted_payment_available") and context.get("hosted_payment_attempt_key"):
        items.append(
            {
                "kind": "link",
                "href": (
                    f'{reverse("payments:hosted-redirect", kwargs={"attempt_key": context.get("hosted_payment_attempt_key")})}'
                    f'?{urlencode({"back_url": detail_back_url})}'
                ),
                "button_class": "ds-btn-secondary",
                "label": str(context.get("hosted_payment_label") or "Abrir pagamento hospedado"),
                "helper": str(context.get("hosted_payment_helper") or ""),
            }
        )

    return items


def _render_order_detail_action_item(request, item: dict[str, str]) -> str:
    helper = str(item.get("helper") or "")
    if item.get("kind") == "form":
        csrf_token = get_token(request)
        return str(
            format_html(
                '<div class="flex flex-col items-stretch gap-2 md:items-end">'
                '  <form method="post" action="{}" class="inline-flex">'
                '    <input type="hidden" name="csrfmiddlewaretoken" value="{}">'
                '    <input type="hidden" name="action_type" value="{}">'
                '    <button type="submit" class="{}">{}</button>'
                "  </form>"
                '  <p class="text-right text-xs text-[var(--color-text-secondary)]">{}</p>'
                "</div>",
                str(item.get("action") or ""),
                csrf_token,
                str(item.get("action_type") or ""),
                str(item.get("button_class") or "ds-btn-secondary"),
                str(item.get("label") or ""),
                helper,
            )
        )
    return str(
        format_html(
            '<div class="flex flex-col items-stretch gap-2 md:items-end">'
            '  <a href="{}" class="{}">{}</a>'
            '  <p class="text-right text-xs text-[var(--color-text-secondary)]">{}</p>'
            "</div>",
            str(item.get("href") or ""),
            str(item.get("button_class") or "ds-btn-secondary"),
            str(item.get("label") or ""),
            helper,
        )
    )


def _build_order_detail_actions(request, context: dict[str, object], *, order_number: str) -> dict[str, object]:
    action_items = _build_order_detail_action_items(request, context, order_number=order_number)
    action_blocks = [_render_order_detail_action_item(request, item) for item in action_items]
    if not action_blocks:
        return {}
    return {"page_actions": mark_safe("".join(str(block) for block in action_blocks))}


class LoginView(TemplateView):
    template_name = "pages/templates/login_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        context.update(account_page_queries.get_login_page_data(tenant_id=tenant_id))
        context["form_action"] = self.request.path
        context["register_href"] = reverse("accounts:register")
        context["forgot_password_href"] = reverse("accounts:forgot-password")
        return context


class RegisterView(TemplateView):
    template_name = "pages/templates/register_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        context.update(account_page_queries.get_register_page_data(tenant_id=tenant_id))
        context["form_action"] = self.request.path
        context["login_href"] = reverse("accounts:login")
        return context


class ForgotPasswordView(TemplateView):
    template_name = "pages/templates/forgot_password_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        context.update(account_page_queries.get_forgot_password_page_data(tenant_id=tenant_id))
        context["form_action"] = self.request.path
        context["login_href"] = reverse("accounts:login")
        return context


class ResetPasswordView(TemplateView):
    template_name = "pages/templates/reset_password_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        context.update(account_page_queries.get_reset_password_page_data(tenant_id=tenant_id))
        context["form_action"] = self.request.path
        context["login_href"] = reverse("accounts:login")
        return context


class AccountOverviewView(TemplateView):
    template_name = "pages/templates/account_overview_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        context.update(account_page_queries.get_account_overview_data(tenant_id=tenant_id))
        context["quick_links"] = _quick_links()
        return context


class AccountOrdersView(TemplateView):
    template_name = "pages/templates/orders_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        base_payload = account_customer_area_queries.get_orders_page_data(tenant_id=tenant_id)
        orders = account_customer_area_queries.list_orders(
            tenant_id=tenant_id,
            allow_fixture_fallback=False,
        )
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
        tenant_id = _request_tenant_id(request)
        action_type = request.POST.get("action_type", "").strip()
        if action_type == "reorder_lite":
            profile = account_customer_area_queries.get_active_profile_context(tenant_id=tenant_id)
            result, session_key = checkout_reorder_commands.bootstrap_from_order(
                tenant_id=profile.get("tenant_id"),
                customer_id=profile.get("customer_id"),
                email=str(profile.get("email") or ""),
                order_number=kwargs["order_number"],
            )
            if session_key:
                checkout_url = f'{reverse("checkout:checkout-page")}?{urlencode({"result": result, "stage": "cart", "session_key": session_key, "back_url": reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})})}'
                return HttpResponseRedirect(checkout_url)
            return HttpResponseRedirect(
                f'{reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})}?result={result}'
            )
        if action_type == "payment_retry":
            profile = account_customer_area_queries.get_active_profile_context(tenant_id=tenant_id)
            result, session_key = checkout_payment_retry_commands.bootstrap_from_failed_order(
                tenant_id=profile.get("tenant_id"),
                customer_id=profile.get("customer_id"),
                email=str(profile.get("email") or ""),
                order_number=kwargs["order_number"],
            )
            if session_key:
                checkout_url = f'{reverse("checkout:checkout-page")}?{urlencode({"result": result, "stage": "payment", "session_key": session_key, "back_url": reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})})}'
                return HttpResponseRedirect(checkout_url)
            return HttpResponseRedirect(
                f'{reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})}?result={result}'
            )
        if action_type != "confirm_payment":
            return HttpResponseRedirect(
                reverse("accounts:account-order-detail", kwargs={"order_number": kwargs["order_number"]})
            )
        profile = account_customer_area_queries.get_active_profile_context(tenant_id=tenant_id)
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
        tenant_id = _request_tenant_id(self.request)
        confirmation_mode = self.request.GET.get("result", "").strip() == "checkout-completed"
        context.update(
            account_customer_area_queries.get_order_detail_page_data(
                kwargs["order_number"],
                confirmation_mode=confirmation_mode,
                tenant_id=tenant_id,
            )
        )
        context.update(_build_order_detail_actions(self.request, context, order_number=kwargs["order_number"]))
        context.update(_build_order_detail_feedback_context(self.request))
        return context


class AccountAddressesView(TemplateView):
    template_name = "pages/templates/addresses_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        base_payload = account_customer_area_queries.get_addresses_page_data(tenant_id=_request_tenant_id(self.request))
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
        context.update(account_customer_area_queries.get_profile_page_data(tenant_id=_request_tenant_id(self.request)))
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
        address = account_address_commands.create_address(form.cleaned_data, tenant_id=_request_tenant_id(request))
        result = "address-created" if address is not None else "address-create-unavailable"
        return HttpResponseRedirect(f'{reverse("accounts:account-addresses")}?result={result}#address-management')


class AccountAddressEditReadyView(_AccountAddressReadyRedirectView):
    intent = "edit"

    def post(self, request, *args, **kwargs):
        address_id = int(kwargs["address_id"])
        form = AccountAddressForm(request.POST)
        if not form.is_valid():
            return self._render_form_page(request, form=form, address_id=address_id)
        address = account_address_commands.update_address(address_id, form.cleaned_data, tenant_id=_request_tenant_id(request))
        result = "address-updated" if address is not None else "address-update-unavailable"
        return HttpResponseRedirect(f'{reverse("accounts:account-addresses")}?result={result}#address-management')


class AccountAddressDeleteReadyView(_AccountAddressReadyRedirectView):
    intent = "delete"

    def post(self, request, *args, **kwargs):
        address_id = int(kwargs["address_id"])
        deleted = account_address_commands.delete_address(address_id, tenant_id=_request_tenant_id(request))
        result = "address-deleted" if deleted else "address-delete-blocked"
        return HttpResponseRedirect(f'{reverse("accounts:account-addresses")}?result={result}#address-management')
