from __future__ import annotations

from django.middleware.csrf import get_token
from django.http import Http404, HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html
from django.views import View
from django.views.generic import TemplateView

from app.modules.accounts.application.admin_permissions import PERMISSION_REVIEWS_MODERATE
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.reviews.application.admin_review_commands import admin_review_commands
from app.modules.reviews.application.admin_review_queries import STATUS_OPTIONS, admin_review_queries
from app.modules.reviews.application.review_submission_commands import product_review_submission_commands


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _request_owner_role(request) -> str:
    return request_owner_role(request)


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _action_cell(review: dict[str, object], *, csrf_token: str, can_moderate: bool) -> str:
    if not can_moderate:
        return "Sem permissão para moderar"
    review_id = review["id"]
    action_url = reverse("reviews:admin-review-moderate", kwargs={"review_id": review_id})
    status = str(review.get("status") or "")
    approve_form = ""
    reject_form = ""
    if status != "approved":
        approve_form = format_html(
            '<form method="post" action="{}" class="inline">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<input type="hidden" name="action" value="approve">'
            '<button class="ds-btn-secondary" type="submit">Aprovar</button>'
            "</form>",
            action_url,
            csrf_token,
        )
    if status != "rejected":
        reject_form = format_html(
            '<form method="post" action="{}" class="inline">'
            '<input type="hidden" name="csrfmiddlewaretoken" value="{}">'
            '<input type="hidden" name="action" value="reject">'
            '<button class="ds-btn-secondary" type="submit">Rejeitar</button>'
            "</form>",
            action_url,
            csrf_token,
        )
    return format_html('<div class="flex flex-wrap gap-2">{}{}</div>', approve_form, reject_form)


class AdminReviewsListView(TemplateView):
    template_name = "pages/templates/admin_reviews_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = _request_tenant_id(self.request)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        reviews = admin_review_queries.list_reviews(
            tenant_id=tenant_id,
            status=status_selected,
            search=search_value,
        )
        can_moderate_reviews = request_admin_can(self.request, PERMISSION_REVIEWS_MODERATE)
        csrf_token = get_token(self.request)
        empty_title = "Nenhuma avaliação para moderar"
        empty_description = "Quando clientes enviarem avaliações, elas aparecerão aqui antes de ir para a PDP."
        if not tenant_id:
            empty_title = "Tenant não resolvido"
            empty_description = "Acesse esta tela por um subdomínio de loja para moderar reviews tenant-scoped."

        context.update(
            {
                "page_title": "Avaliações",
                "page_eyebrow": "Prova social",
                "page_description": "Modere avaliações de produto antes de qualquer exibição pública no storefront.",
                "create_href": reverse("reviews:admin-reviews-create") if can_moderate_reviews else "",
                "filter_action": reverse("reviews:admin-reviews-list"),
                "search_name": "q",
                "search_value": search_value,
                "search_label": "Buscar avaliações",
                "search_placeholder": "Produto, autor, título ou texto",
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": reverse("reviews:admin-reviews-list"),
                "columns": [
                    {"label": "Produto"},
                    {"label": "Rating"},
                    {"label": "Autor"},
                    {"label": "Título"},
                    {"label": "Status"},
                    {"label": "Criada em"},
                    {"label": "Ação"},
                ],
                "rows": [
                    {
                        "cells": [
                            review["product_name"],
                            f'{review["rating"]}/5',
                            review["author_name"],
                            review["title"],
                            review["status_label"],
                            review["created_at"],
                            _action_cell(review, csrf_token=csrf_token, can_moderate=can_moderate_reviews),
                        ]
                    }
                    for review in reviews
                ],
                "table_count": f"{len(reviews)} avaliação(ões)",
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


class AdminReviewCreateView(TemplateView):
    template_name = "pages/templates/admin_review_form_page.html"

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None):
        values = values or {}
        return {
            "page_title": "Nova avaliação",
            "page_eyebrow": "Prova social",
            "page_description": "Crie uma avaliação operacional como pendente. A publicação continua dependendo de moderação.",
            "form_action": self.request.path,
            "cancel_href": reverse("reviews:admin-reviews-list"),
            "product_slug": values.get("product_slug", ""),
            "product_id": values.get("product_id", ""),
            "rating": values.get("rating", ""),
            "title": values.get("title", ""),
            "body": values.get("body", ""),
            "author_name": values.get("author_name", ""),
            "customer_id": values.get("customer_id", ""),
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self._context())
        return context

    def post(self, request, *args, **kwargs):
        if not request_admin_can(request, PERMISSION_REVIEWS_MODERATE):
            context = self.get_context_data(**kwargs)
            context.update(self._context(values=request.POST, errors={"__all__": "Permissão insuficiente para criar avaliação."}))
            return self.render_to_response(context, status=400)
        result, _review = product_review_submission_commands.submit_product_review(
            tenant_id=_request_tenant_id(request),
            product_id=_optional_int(request.POST.get("product_id")),
            product_slug=request.POST.get("product_slug", ""),
            rating=request.POST.get("rating"),
            title=request.POST.get("title", ""),
            body=request.POST.get("body", ""),
            author_name=request.POST.get("author_name", ""),
            customer_id=_optional_int(request.POST.get("customer_id")),
            source="ops_admin",
        )
        if result == "review-submitted-pending":
            return HttpResponseRedirect(reverse("reviews:admin-reviews-list"))

        errors = {
            "review-submission-blocked": {
                "__all__": "Não foi possível criar a avaliação. Confira tenant, rating e campos informados.",
                "rating": "Informe uma nota entre 1 e 5.",
            },
            "review-product-not-found": {
                "__all__": "Produto não encontrado para este tenant.",
                "product_slug": "Informe um slug ou ID de produto deste tenant.",
            },
            "review-submission-unavailable": {
                "__all__": "Submissão de avaliação indisponível no momento.",
            },
        }.get(result, {"__all__": "Não foi possível criar a avaliação."})
        context = self.get_context_data(**kwargs)
        context.update(self._context(values=request.POST, errors=errors))
        return self.render_to_response(context, status=400)


class AdminReviewModerateView(View):
    def post(self, request, *args, **kwargs):
        review_id = kwargs.get("review_id")
        if not review_id:
            raise Http404("Review not found")
        admin_review_commands.moderate_review(
            tenant_id=_request_tenant_id(request),
            review_id=review_id,
            action=request.POST.get("action", ""),
            moderated_by=str(getattr(request, "user", "") or ""),
            actor_role=_request_owner_role(request),
        )
        return HttpResponseRedirect(reverse("reviews:admin-reviews-list"))
