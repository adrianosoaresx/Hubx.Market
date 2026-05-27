from __future__ import annotations

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import PERMISSION_COUPONS_MANAGE
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.coupons.application.admin_coupon_commands import admin_coupon_commands
from app.modules.coupons.application.admin_coupon_queries import (
    COUPON_STATUS_OPTIONS,
    DISCOUNT_TYPE_OPTIONS,
    STATUS_OPTIONS,
    admin_coupon_queries,
)


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _request_owner_role(request) -> str:
    return request_owner_role(request)


class AdminCouponsListView(TemplateView):
    template_name = "pages/templates/admin_coupons_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        can_manage_coupons = request_admin_can(self.request, PERMISSION_COUPONS_MANAGE)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        coupons = admin_coupon_queries.list_coupons(tenant_id=tenant_id)

        if search_value:
            lowered_search = search_value.lower()
            coupons = [
                coupon
                for coupon in coupons
                if lowered_search in str(coupon["code"]).lower() or lowered_search in str(coupon["name"]).lower()
            ]
        if status_selected:
            coupons = [coupon for coupon in coupons if coupon["status"] == status_selected]

        empty_title = "Nenhum cupom encontrado"
        empty_description = "Crie um cupom percentual ou fixo simples para este tenant."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para listar cupons tenant-scoped."

        context.update(
            {
                "page_title": "Cupons",
                "page_eyebrow": "Promoções",
                "page_description": "Gerencie cupons simples por tenant sem regras promocionais avançadas.",
                "create_href": reverse("coupons:admin-coupons-create") if can_manage_coupons else "",
                "filter_action": reverse("coupons:admin-coupons-list"),
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar cupons",
                "search_placeholder": "Código ou nome",
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": reverse("coupons:admin-coupons-list"),
                "columns": [
                    {"label": "Código"},
                    {"label": "Nome"},
                    {"label": "Status"},
                    {"label": "Desconto"},
                    {"label": "Validade"},
                    {"label": "Resgates"},
                    {"label": "Atualização"},
                ],
                "rows": [
                    {
                        "cells": [
                            coupon["code"],
                            coupon["name"],
                            coupon["status_label"],
                            f'{coupon["discount_type_label"]} · {coupon["discount_label"]}',
                            coupon["validity_label"],
                            coupon["redemption_label"],
                            coupon["updated_at"],
                        ]
                    }
                    for coupon in coupons
                ],
                "table_count": f"{len(coupons)} cupom(ns)",
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


class AdminCouponCreateView(TemplateView):
    template_name = "pages/templates/admin_coupon_form_page.html"

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None):
        initial = admin_coupon_queries.get_form_initial()
        if values:
            initial.update(
                {
                    "code": values.get("code", initial["code"]),
                    "name": values.get("name", initial["name"]),
                    "status_selected": values.get("status", initial["status_selected"]),
                    "discount_type_selected": values.get("discount_type", initial["discount_type_selected"]),
                    "discount_value": values.get("discount_value", initial["discount_value"]),
                    "starts_at": values.get("starts_at", initial["starts_at"]),
                    "ends_at": values.get("ends_at", initial["ends_at"]),
                }
            )
        return {
            "page_title": "Novo cupom",
            "page_eyebrow": "Promoções",
            "page_description": "Crie um cupom simples por tenant. Regras avançadas ficam fora deste primeiro corte.",
            "form_action": self.request.path,
            "cancel_href": reverse("coupons:admin-coupons-list"),
            "status_options": COUPON_STATUS_OPTIONS,
            "discount_type_options": DISCOUNT_TYPE_OPTIONS,
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            **initial,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        result = admin_coupon_commands.create_coupon(
            tenant_id=_request_tenant_id(request),
            payload=request.POST,
            actor_label=str(getattr(request, "user", "") or ""),
            actor_role=_request_owner_role(request),
        )
        if result.get("result") == "coupon-created":
            return HttpResponseRedirect(reverse("coupons:admin-coupons-list"))
        context = self.get_context_data(**kwargs)
        context.update(self._context(values=request.POST, errors=result.get("errors") or {}))
        return self.render_to_response(context, status=400)
