from __future__ import annotations

from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import TemplateView
from django.views.generic import View

from app.modules.accounts.application.admin_permissions import PERMISSION_NEWSLETTER_MANAGE, PERMISSION_NEWSLETTER_VIEW
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.newsletter.application.admin_newsletter_queries import STATUS_OPTIONS, admin_newsletter_queries
from app.modules.newsletter.application.newsletter_campaign_commands import newsletter_campaign_commands
from app.modules.newsletter.application.newsletter_subscription_commands import (
    DEFAULT_CONSENT_LABEL,
    newsletter_subscription_commands,
)


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _actor_label(request) -> str:
    owner = getattr(request, "owner_user", None)
    owner_email = str(getattr(owner, "email", "") or "").strip()
    if owner_email:
        return owner_email
    user = getattr(request, "user", None)
    return str(getattr(user, "email", "") or getattr(user, "username", "") or "ops-admin").strip()


def _can_manage_newsletter(request) -> bool:
    return bool(request_owner_role(request)) and request_admin_can(request, PERMISSION_NEWSLETTER_MANAGE)


def _feedback(value: object) -> dict[str, str]:
    status = str(value or "").strip()
    mapping = {
        "created": ("success", "Campanha criada", "Revise a campanha e envie quando estiver pronta."),
        "sent": ("success", "Campanha enviada para outbox", "Os e-mails foram planejados em notifications.EmailLog."),
        "no-recipients": ("warning", "Sem destinatários ativos", "Não há inscritos ativos para esta campanha."),
        "already-sent": ("info", "Campanha já enviada", "A campanha preserva o envio anterior."),
        "not-found": ("warning", "Campanha não encontrada", "A campanha não existe neste tenant."),
        "permission-denied": ("danger", "Permissão necessária", "Seu perfil pode visualizar, mas não gerenciar campanhas."),
        "tenant-required": ("warning", "Tenant não resolvido", "Acesse pelo subdomínio da loja para gerenciar newsletter."),
    }
    variant, title, description = mapping.get(status, ("info", "", ""))
    return {"variant": variant, "title": title, "description": description} if title else {}


def _form_value(source, key: str) -> str:
    return str(source.get(key, "") or "").strip()


class AdminNewsletterListView(TemplateView):
    template_name = "pages/templates/admin_newsletter_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._page_context())
        return context

    def _page_context(self, *, form_data=None, errors=None, feedback=None) -> dict[str, object]:
        tenant_id = _request_tenant_id(self.request)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        can_view_newsletter = request_admin_can(self.request, PERMISSION_NEWSLETTER_VIEW)
        can_manage_newsletter = _can_manage_newsletter(self.request)
        subscribers = admin_newsletter_queries.list_subscribers(tenant_id=tenant_id) if can_view_newsletter else []
        campaigns = admin_newsletter_queries.list_campaigns(tenant_id=tenant_id) if can_view_newsletter else []

        if search_value:
            lowered_search = search_value.lower()
            subscribers = [
                subscriber
                for subscriber in subscribers
                if lowered_search in str(subscriber["email"]).lower()
                or lowered_search in str(subscriber["name"]).lower()
                or lowered_search in str(subscriber["source"]).lower()
            ]
        if status_selected:
            subscribers = [subscriber for subscriber in subscribers if subscriber["status"] == status_selected]

        empty_title = "Nenhum inscrito encontrado"
        empty_description = "Quando clientes aceitarem receber novidades, os contatos aparecerão aqui."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para listar inscrições tenant-scoped."
        elif not can_view_newsletter:
            empty_title = "Permissão necessária"
            empty_description = "Seu perfil não possui permissão para visualizar newsletter."

        return {
            "page_title": "Newsletter",
            "page_eyebrow": "Retenção",
            "page_description": "Campanhas e opt-ins tenant-scoped para relacionamento com clientes.",
            "filter_action": reverse("newsletter:admin-newsletter-list"),
            "search_name": "q",
            "search_value": search_value,
            "search_label": "Buscar inscritos",
            "search_placeholder": "E-mail, nome ou origem",
            "status_options": STATUS_OPTIONS,
            "status_selected": status_selected,
            "reset_url": reverse("newsletter:admin-newsletter-list"),
            "columns": [
                {"label": "E-mail"},
                {"label": "Nome"},
                {"label": "Status"},
                {"label": "Origem"},
                {"label": "Consentimento"},
                {"label": "Atualização"},
            ],
            "rows": [
                {
                    "cells": [
                        subscriber["email"],
                        subscriber["name"],
                        subscriber["status_label"],
                        subscriber["source"],
                        subscriber["consented_at"],
                        subscriber["updated_at"],
                    ]
                }
                for subscriber in subscribers
            ],
            "campaigns": campaigns,
            "campaign_count": f"{len(campaigns)} campanha(s)",
            "can_manage_newsletter": can_manage_newsletter and bool(tenant_id),
            "feedback": feedback or _feedback(self.request.GET.get("status")),
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            "form": {
                "title": _form_value(form_data or {}, "title"),
                "subject": _form_value(form_data or {}, "subject"),
                "body_text": _form_value(form_data or {}, "body_text"),
            },
            "table_count": f"{len(subscribers)} inscrito(s)",
            "empty_title": empty_title,
            "empty_description": empty_description,
        }


class AdminNewsletterCampaignCreateView(View):
    template_name = "pages/templates/admin_newsletter_list_page.html"

    def post(self, request, *args, **kwargs):
        if not _request_tenant_id(request):
            return self._render(form_data=request.POST, feedback=_feedback("tenant-required"))
        if not _can_manage_newsletter(request):
            return self._render(form_data=request.POST, feedback=_feedback("permission-denied"), status=403)
        result = newsletter_campaign_commands.create_campaign(
            tenant_id=_request_tenant_id(request),
            title=request.POST.get("title"),
            subject=request.POST.get("subject"),
            body_text=request.POST.get("body_text"),
            actor_label=_actor_label(request),
        )
        if result.get("result") == "newsletter-campaign-created":
            return HttpResponseRedirect(f'{reverse("newsletter:admin-newsletter-list")}?status=created')
        feedback = {"variant": "danger", "title": "Campanha não criada", "description": "Revise os campos e tente novamente."}
        return self._render(form_data=request.POST, errors=result.get("errors") or {}, feedback=feedback, status=400)

    def _render(self, *, form_data=None, errors=None, feedback=None, status: int = 200):
        view = AdminNewsletterListView()
        view.setup(self.request)
        context = view._page_context(form_data=form_data, errors=errors, feedback=feedback)
        return render(self.request, self.template_name, context=context, status=status)


class AdminNewsletterCampaignSendView(View):
    def post(self, request, *args, **kwargs):
        if not _request_tenant_id(request):
            return HttpResponseRedirect(f'{reverse("newsletter:admin-newsletter-list")}?status=tenant-required')
        if not _can_manage_newsletter(request):
            return HttpResponseRedirect(f'{reverse("newsletter:admin-newsletter-list")}?status=permission-denied')
        result = newsletter_campaign_commands.send_campaign(
            tenant_id=_request_tenant_id(request),
            campaign_id=kwargs.get("campaign_id"),
            actor_label=_actor_label(request),
        )
        result_status = {
            "newsletter-campaign-sent": "sent",
            "newsletter-campaign-already-sent": "already-sent",
            "newsletter-campaign-no-recipients": "no-recipients",
            "newsletter-campaign-not-found": "not-found",
            "newsletter-campaign-tenant-required": "tenant-required",
        }.get(str(result.get("result") or ""), "not-found")
        return HttpResponseRedirect(f'{reverse("newsletter:admin-newsletter-list")}?status={result_status}')


class StorefrontNewsletterSubscribeView(TemplateView):
    template_name = "pages/templates/newsletter_subscribe_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = self.request.GET.get("result", "").strip()
        context.update(
            {
                "page_title": "Receba novidades",
                "form_action": reverse("storefront_newsletter:newsletter-subscribe"),
                "email": "",
                "name": "",
                "consent_label": DEFAULT_CONSENT_LABEL,
                "feedback_result": result,
            }
        )
        return context

    def post(self, request, *args, **kwargs):
        result = newsletter_subscription_commands.subscribe(
            tenant_id=_request_tenant_id(request),
            email=request.POST.get("email", ""),
            name=request.POST.get("name", ""),
            source="storefront_newsletter_page",
            consent_label=request.POST.get("consent_label", DEFAULT_CONSENT_LABEL),
        )
        if result.get("result") in {"newsletter-subscribed", "newsletter-resubscribed"}:
            return HttpResponseRedirect(f'{reverse("storefront_newsletter:newsletter-subscribe")}?result=subscribed')

        context = self.get_context_data(**kwargs)
        context.update(
            {
                "email": request.POST.get("email", ""),
                "name": request.POST.get("name", ""),
                "form_error": (result.get("errors") or {}).get("email")
                or (result.get("errors") or {}).get("__all__")
                or "Não foi possível registrar sua inscrição.",
            }
        )
        return self.render_to_response(context, status=400)
