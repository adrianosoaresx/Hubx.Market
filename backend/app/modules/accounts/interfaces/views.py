from __future__ import annotations

from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.views.generic import TemplateView, View

from app.modules.accounts.application.account_page_queries import account_page_queries
from app.modules.accounts.application.account_customer_area_queries import (
    account_customer_area_queries,
)


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
                            order["order_status_label"],
                            order["payment_status"],
                            order["shipping_status"],
                            order["updated_at"],
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

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(account_customer_area_queries.get_order_detail_page_data(kwargs["order_number"]))
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


class AccountAddressCreateReadyView(_AccountAddressReadyRedirectView):
    intent = "create"


class AccountAddressEditReadyView(_AccountAddressReadyRedirectView):
    intent = "edit"


class AccountAddressDeleteReadyView(_AccountAddressReadyRedirectView):
    intent = "delete"
