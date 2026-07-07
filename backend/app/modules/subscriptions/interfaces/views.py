from __future__ import annotations

from django.conf import settings
from django.http import Http404, HttpResponseRedirect
from django.middleware.csrf import get_token
from django.urls import reverse
from django.utils.html import format_html
from django.views.generic import TemplateView, View

from app.modules.accounts.application.admin_permissions import (
    PERMISSION_PLATFORM_TENANTS_MANAGE,
    PERMISSION_PLATFORM_TENANTS_VIEW,
    PERMISSION_SUBSCRIPTIONS_MANAGE,
    PERMISSION_SUBSCRIPTIONS_VIEW,
)
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.subscriptions.application.subscription_coupon_admin_queries import (
    COUPON_STATUS_OPTIONS,
    DISCOUNT_TYPE_OPTIONS,
    STATUS_OPTIONS,
    subscription_coupon_admin_queries,
)
from app.modules.subscriptions.application.subscription_coupon_commands import subscription_coupon_commands
from app.modules.subscriptions.application.subscription_commands import subscription_commands
from app.modules.subscriptions.application.subscription_queries import subscription_queries
from app.modules.tenants.application.public_tenant_signup_commands import public_tenant_signup_commands


def _actor_label(request, *, default: str = "public-plans") -> str:
    owner = getattr(request, "owner_user", None)
    if owner is not None:
        return str(getattr(owner, "email", "") or default)
    user = getattr(request, "user", None)
    return str(getattr(user, "email", "") or default)


def _client_ip(request) -> str:
    forwarded = str(request.META.get("HTTP_X_FORWARDED_FOR", "") or "").split(",")[0].strip()
    return forwarded or str(request.META.get("REMOTE_ADDR", "") or "")


def _status_badge(*, label: str, variant: str) -> str:
    variant_classes = {
        "success": "ds-badge-success",
        "warning": "ds-badge-warning",
        "danger": "ds-badge-danger",
    }
    return format_html(
        '<span class="ds-badge ds-badge-xs {}">{}</span>',
        variant_classes.get(variant, "ds-badge-neutral"),
        label,
    )


def _coupon_status_action_cell(*, request, coupon: dict[str, object], can_manage: bool) -> str:
    if not can_manage:
        return ""
    next_status = "inactive" if coupon["status"] == "active" else "active"
    label = "Inativar" if next_status == "inactive" else "Ativar"
    return format_html(
        '<form method="post" action="{}" class="inline-flex">'
        '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
        '<input type="hidden" name="status" value="{}">'
        '<button class="ds-btn ds-btn-secondary ds-btn-sm" type="submit">{}</button>'
        "</form>",
        reverse("subscription_coupons:platform-subscription-coupons-status", kwargs={"coupon_id": coupon["id"]}),
        get_token(request),
        next_status,
        label,
    )


class AdminSubscriptionsListView(TemplateView):
    template_name = "pages/templates/admin_subscriptions_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = request_tenant_id(self.request)
        can_view = request_admin_can(self.request, PERMISSION_SUBSCRIPTIONS_VIEW)
        subscriptions = subscription_queries.list_tenant_subscriptions(tenant_id=tenant_id) if can_view else []
        context.update(
            {
                "page_title": "Assinatura SaaS",
                "page_eyebrow": "Platform billing",
                "page_description": "Leitura tenant-scoped do plano SaaS com provider de billing preparado para onboarding.",
                "columns": [
                    {"label": "Tenant"},
                    {"label": "Plano"},
                    {"label": "Status"},
                    {"label": "Provider"},
                    {"label": "Mensalidade"},
                    {"label": "Preço efetivo"},
                    {"label": "Período"},
                    {"label": "Referência"},
                ],
                "rows": [
                    {
                        "cells": [
                            item["tenant_name"],
                            f'{item["plan_name"]} ({item["plan_code"]})',
                            item["status_label"],
                            item["billing_provider_label"],
                            item["monthly_price"],
                            item["effective_monthly_price"],
                            item["current_period_ends_at"],
                            item["external_reference"],
                        ]
                    }
                    for item in subscriptions
                ],
                "table_count": f"{len(subscriptions)} assinatura(s)",
                "empty_title": "Nenhuma assinatura SaaS",
                "empty_description": "Crie o estado de assinatura por service/command antes de ativar enforcement.",
            }
        )
        return context


class PublicPlansView(TemplateView):
    template_name = "pages/templates/public_plans_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._base_context())
        return context

    def post(self, request, *args, **kwargs):
        result = subscription_commands.create_public_acquisition_lead(
            payload={
                "plan_code": request.POST.get("plan_code"),
                "store_name": request.POST.get("store_name"),
                "desired_subdomain": request.POST.get("desired_subdomain"),
                "contact_name": request.POST.get("contact_name"),
                "contact_email": request.POST.get("contact_email"),
                "contact_phone": request.POST.get("contact_phone"),
                "coupon_code": request.POST.get("coupon_code"),
                "message": request.POST.get("message"),
                "source": "public-plans",
            },
            actor_label="public-plans",
        )
        context = self._base_context()
        context["values"] = {
            "plan_code": request.POST.get("plan_code", ""),
            "store_name": request.POST.get("store_name", ""),
            "desired_subdomain": request.POST.get("desired_subdomain", ""),
            "contact_name": request.POST.get("contact_name", ""),
            "contact_email": request.POST.get("contact_email", ""),
            "contact_phone": request.POST.get("contact_phone", ""),
            "coupon_code": request.POST.get("coupon_code", ""),
            "message": request.POST.get("message", ""),
        }
        if result.get("result") == "subscription-acquisition-lead-created":
            context["success"] = True
            context["lead"] = result.get("lead") or {}
            context["values"] = {}
        else:
            errors = result.get("errors") or {}
            context["errors"] = errors
            context["form_error"] = errors.get("__all__", "")
        return self.render_to_response(context)

    def _base_context(self) -> dict[str, object]:
        selected_plan = str(self.request.GET.get("plan", "") or "")
        return {
            "page_title": "Planos Hubx Market",
            "page_description": "Escolha um plano SaaS e solicite a criação assistida da sua loja.",
            "plans": subscription_queries.list_public_plans(),
            "selected_plan": selected_plan,
            "values": {"plan_code": selected_plan},
            "errors": {},
            "form_error": "",
            "success": False,
            "portal_href": "/",
            "login_href": "/accounts/login/",
            "demo_href": "/demo/",
            "public_signup_enabled": bool(getattr(settings, "HUBX_PUBLIC_SIGNUP_ENABLED", False)),
            "signup_href": "/plans/signup/",
        }


class PublicSignupView(TemplateView):
    template_name = "pages/templates/public_signup_page.html"

    def dispatch(self, request, *args, **kwargs):
        if not bool(getattr(settings, "HUBX_PUBLIC_SIGNUP_ENABLED", False)):
            raise Http404("Signup self-service indisponivel")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._base_context())
        context.update(kwargs)
        return context

    def post(self, request, *args, **kwargs):
        values = {
            "plan_code": request.POST.get("plan_code", ""),
            "store_name": request.POST.get("store_name", ""),
            "desired_subdomain": request.POST.get("desired_subdomain", ""),
            "owner_name": request.POST.get("owner_name", ""),
            "owner_email": request.POST.get("owner_email", ""),
            "contact_phone": request.POST.get("contact_phone", ""),
            "coupon_code": request.POST.get("coupon_code", ""),
            "access_token": request.POST.get("access_token", ""),
            "accept_terms": request.POST.get("accept_terms", ""),
        }
        result = public_tenant_signup_commands.create_signup(
            payload={
                **values,
                "password": request.POST.get("password", ""),
                "password_confirm": request.POST.get("password_confirm", ""),
                "website": request.POST.get("website", ""),
            },
            ip_address=_client_ip(request),
            actor_label="public-signup",
        )
        context = self._base_context()
        context["values"] = values
        if result.get("result") in {"public-tenant-signup-created", "public-tenant-signup-already-created"}:
            context["success"] = True
            context["signup"] = result
            context["values"] = {}
        else:
            errors = result.get("errors") or {}
            context["errors"] = errors
            context["form_error"] = errors.get("__all__", "")
        return self.render_to_response(context)

    def _base_context(self) -> dict[str, object]:
        selected_plan = str(self.request.GET.get("plan", "") or "")
        return {
            "page_title": "Criar loja Hubx Market",
            "page_description": "Crie uma loja em modo manutencao e inicie o trial interno sem billing SaaS automatico.",
            "plans": subscription_queries.list_public_plans(),
            "selected_plan": selected_plan,
            "values": {"plan_code": selected_plan},
            "errors": {},
            "form_error": "",
            "success": False,
            "access_token_required": bool(getattr(settings, "HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN", True)),
            "portal_href": "/",
            "login_href": "/accounts/login/",
            "plans_href": "/plans/",
            "demo_href": "/demo/",
        }


class PlatformSubscriptionCouponListView(TemplateView):
    template_name = "pages/templates/admin_subscription_coupons_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_manage = bool(request_owner_role(self.request)) and request_admin_can(self.request, PERMISSION_SUBSCRIPTIONS_MANAGE)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        coupons = subscription_coupon_admin_queries.list_coupons() if can_manage else []

        if search_value:
            lowered_search = search_value.lower()
            coupons = [
                coupon
                for coupon in coupons
                if lowered_search in str(coupon["code"]).lower()
                or lowered_search in str(coupon["name"]).lower()
                or lowered_search in str(coupon["plan_label"]).lower()
            ]
        if status_selected:
            coupons = [coupon for coupon in coupons if coupon["status"] == status_selected]

        context.update(
            {
                "page_title": "Cupons SaaS",
                "page_eyebrow": "Promoções platform",
                "page_description": "Gerencie cupons comerciais de planos SaaS. Eles não validam carrinho ou pedido tenant-scoped.",
                "page_meta": "Escopo platform-only",
                "create_href": reverse("subscription_coupons:platform-subscription-coupons-create") if can_manage else "",
                "filter_action": reverse("subscription_coupons:platform-subscription-coupons-list"),
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar cupons SaaS",
                "search_placeholder": "Código, nome ou plano",
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": reverse("subscription_coupons:platform-subscription-coupons-list"),
                "columns": [
                    {"label": "Código"},
                    {"label": "Nome"},
                    {"label": "Status"},
                    {"label": "Desconto"},
                    {"label": "Plano"},
                    {"label": "Validade"},
                    {"label": "Atualização"},
                    {"label": "Ações"},
                ],
                "rows": [
                    {
                        "cells": [
                            coupon["code"],
                            coupon["name"],
                            coupon["status_label"],
                            f'{coupon["discount_type_label"]} · {coupon["discount_label"]}',
                            coupon["plan_label"],
                            coupon["validity_label"],
                            coupon["updated_at"],
                            _coupon_status_action_cell(request=self.request, coupon=coupon, can_manage=can_manage),
                        ]
                    }
                    for coupon in coupons
                ],
                "table_count": f"{len(coupons)} cupom(ns) SaaS",
                "empty_title": "Nenhum cupom SaaS encontrado",
                "empty_description": "Crie um cupom percentual ou fixo para campanhas comerciais de planos.",
            }
        )
        return context


class PlatformSubscriptionCouponCreateView(TemplateView):
    template_name = "pages/templates/admin_subscription_coupon_form_page.html"

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None):
        initial = subscription_coupon_admin_queries.get_form_initial()
        if values:
            initial.update(
                {
                    "code": values.get("code", initial["code"]),
                    "name": values.get("name", initial["name"]),
                    "status_selected": values.get("status", initial["status_selected"]),
                    "discount_type_selected": values.get("discount_type", initial["discount_type_selected"]),
                    "discount_value": values.get("discount_value", initial["discount_value"]),
                    "plan_code_selected": values.get("plan_code", initial["plan_code_selected"]),
                    "starts_at": values.get("starts_at", initial["starts_at"]),
                    "ends_at": values.get("ends_at", initial["ends_at"]),
                }
            )
        return {
            "page_title": "Novo cupom SaaS",
            "page_eyebrow": "Promoções platform",
            "page_description": "Crie um cupom para planos SaaS. Use plano vazio para aplicar a qualquer plano ativo.",
            "form_action": self.request.path,
            "cancel_href": reverse("subscription_coupons:platform-subscription-coupons-list"),
            "status_options": COUPON_STATUS_OPTIONS,
            "discount_type_options": DISCOUNT_TYPE_OPTIONS,
            "plan_options": subscription_coupon_admin_queries.list_plan_options(),
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            **initial,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        result = subscription_coupon_commands.create_coupon(
            payload=request.POST,
            actor_label=_actor_label(request, default="platform"),
            actor_role=request_owner_role(request),
        )
        if result.get("result") == "subscription-coupon-created":
            return HttpResponseRedirect(reverse("subscription_coupons:platform-subscription-coupons-list"))
        context = self.get_context_data(**kwargs)
        context.update(self._context(values=request.POST, errors=result.get("errors") or {}))
        return self.render_to_response(context, status=400)


class PlatformSubscriptionCouponStatusView(View):
    def post(self, request, *args, **kwargs):
        result = subscription_coupon_commands.set_coupon_status(
            coupon_id=kwargs.get("coupon_id"),
            status=request.POST.get("status"),
            actor_label=_actor_label(request, default="platform"),
            actor_role=request_owner_role(request),
        )
        query = "?result=subscription-coupon-status-updated" if result.get("result") in {
            "subscription-coupon-status-updated",
            "subscription-coupon-status-unchanged",
        } else f"?result={result.get('result')}"
        return HttpResponseRedirect(f"{reverse('subscription_coupons:platform-subscription-coupons-list')}{query}")


class PlatformAcquisitionListView(TemplateView):
    template_name = "pages/templates/admin_subscription_acquisitions_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        can_view = request_admin_can(self.request, PERMISSION_PLATFORM_TENANTS_VIEW)
        leads = subscription_queries.list_acquisition_leads() if can_view else []
        owner_role = request_owner_role(self.request)
        leads_count = len(leads)
        context.update(
            {
                "page_title": "Aquisições SaaS",
                "page_eyebrow": "Aquisição platform",
                "page_description": "Fila segura de intenções públicas de plano. Conversão cria apenas uma jornada de onboarding.",
                "page_meta": f"Escopo platform-only · perfil: {owner_role}" if owner_role else "Escopo platform-only",
                "plans_href": "/plans/",
                "table_count": f"{leads_count} lead" if leads_count == 1 else f"{leads_count} leads",
                "columns": [
                    {"label": "Loja"},
                    {"label": "Plano"},
                    {"label": "Cupom"},
                    {"label": "Contato"},
                    {"label": "Status"},
                    {"label": "Entrada"},
                ],
                "rows": [
                    {
                        "cells": [
                            format_html(
                                '<a class="font-medium text-[var(--color-action-primary-bg)] hover:underline" href="{}">{} · {}</a>',
                                lead["detail_href"],
                                lead["store_name"],
                                lead["store_url_preview"],
                            ),
                            f'{lead["plan_name"]} ({lead["plan_code"]}) · {lead["effective_monthly_price"]}',
                            lead["coupon_code"] or "—",
                            lead["contact_email"],
                            _status_badge(label=str(lead["status_label"]), variant=str(lead["status_variant"])),
                            lead["created_at"],
                        ]
                    }
                    for lead in leads
                ],
                "empty_title": "Nenhuma aquisição pública",
                "empty_description": "Leads enviados por /plans/ aparecerão aqui para revisão platform.",
            }
        )
        return context


class PlatformAcquisitionDetailView(TemplateView):
    template_name = "pages/templates/admin_subscription_acquisition_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        lead = subscription_queries.get_acquisition_lead(lead_id=kwargs.get("lead_id"))
        if lead is None:
            raise Http404("Lead de aquisição não encontrado")
        context.update(
            {
                "page_title": "Detalhe da aquisição",
                "page_eyebrow": "Aquisição platform",
                "page_description": "Revise a intenção pública antes de converter em onboarding.",
                "lead": lead,
                "status_badge": _status_badge(label=str(lead["status_label"]), variant=str(lead["status_variant"])),
                "back_href": reverse("subscription_acquisitions:platform-acquisitions-list"),
                "convert_action": reverse("subscription_acquisitions:platform-acquisitions-convert", kwargs={"lead_id": lead["id"]}),
                "discard_action": reverse("subscription_acquisitions:platform-acquisitions-discard", kwargs={"lead_id": lead["id"]}),
                "can_manage_acquisitions": bool(request_owner_role(self.request)) and request_admin_can(self.request, PERMISSION_PLATFORM_TENANTS_MANAGE),
            }
        )
        return context


class PlatformAcquisitionConvertView(View):
    def post(self, request, *args, **kwargs):
        result = subscription_commands.convert_acquisition_lead_to_onboarding(
            lead_id=kwargs.get("lead_id"),
            actor_label=_actor_label(request, default="platform"),
            actor_role=request_owner_role(request),
        )
        query = "?result=subscription-acquisition-lead-converted" if result.get("result") == "subscription-acquisition-lead-converted" else f"?result={result.get('result')}"
        return HttpResponseRedirect(
            f"{reverse('subscription_acquisitions:platform-acquisitions-detail', kwargs={'lead_id': kwargs.get('lead_id')})}{query}"
        )


class PlatformAcquisitionDiscardView(View):
    def post(self, request, *args, **kwargs):
        result = subscription_commands.discard_acquisition_lead(
            lead_id=kwargs.get("lead_id"),
            actor_label=_actor_label(request, default="platform"),
            actor_role=request_owner_role(request),
        )
        query = "?result=subscription-acquisition-lead-discarded" if result.get("result") == "subscription-acquisition-lead-discarded" else f"?result={result.get('result')}"
        return HttpResponseRedirect(
            f"{reverse('subscription_acquisitions:platform-acquisitions-detail', kwargs={'lead_id': kwargs.get('lead_id')})}{query}"
        )
