from __future__ import annotations

from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.newsletter.application.admin_newsletter_queries import STATUS_OPTIONS, admin_newsletter_queries
from app.modules.newsletter.application.newsletter_subscription_commands import (
    DEFAULT_CONSENT_LABEL,
    newsletter_subscription_commands,
)


def _request_tenant_id(request) -> int | None:
    return getattr(getattr(request, "tenant", None), "id", None)


class AdminNewsletterListView(TemplateView):
    template_name = "pages/templates/admin_newsletter_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        subscribers = admin_newsletter_queries.list_subscribers(tenant_id=tenant_id)

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

        context.update(
            {
                "page_title": "Newsletter",
                "page_eyebrow": "Retenção",
                "page_description": "Leia opt-ins tenant-scoped sem automação de marketing nesta fase.",
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
                "table_count": f"{len(subscribers)} inscrito(s)",
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


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
