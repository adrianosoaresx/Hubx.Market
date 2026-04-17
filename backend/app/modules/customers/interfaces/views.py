from __future__ import annotations

from django.core.paginator import Paginator
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.customers.application.admin_customer_queries import (
    STATUS_OPTIONS,
    admin_customer_queries,
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


class AdminCustomersListView(TemplateView):
    template_name = "pages/templates/admin_customers_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        customers = admin_customer_queries.list_customers()
        if search_value:
            lowered = search_value.lower()
            customers = [
                customer
                for customer in customers
                if lowered in str(customer["name"]).lower()
                or lowered in str(customer["email"]).lower()
                or lowered in str(customer["customer_reference"]).lower()
            ]
        if status_selected:
            customers = [customer for customer in customers if customer["status"] == status_selected]

        paginator = Paginator(customers, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("customers:admin-customers-list")

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
                "page_title": "Clientes",
                "page_description": "Acompanhe clientes, status da conta e atividade recente.",
                "export_href": "#export-customers",
                "filter_action": base_url,
                "search_name": "q",
                "search_value": search_value,
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": base_url,
                "columns": [
                    {"label": "Cliente"},
                    {"label": "Contato"},
                    {"label": "Status"},
                    {"label": "Conta"},
                    {"label": "Última atividade"},
                ],
                "rows": [
                    {
                        "cells": [
                            customer["name"],
                            customer["email"],
                            customer["customer_status_label"],
                            customer["account_type_label"],
                            customer["last_activity"],
                        ]
                    }
                    for customer in page_obj.object_list
                ],
                "table_count": f"{paginator.count} cliente(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "page_note": "Terceira wiring real: adapter de apresentação fino para clientes, pronto para trocar fixtures por serviço real.",
            }
        )
        return context


class AdminCustomerDetailView(TemplateView):
    template_name = "pages/templates/admin_customer_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = admin_customer_queries.get_customer(kwargs["customer_slug"])
        context.update(
            {
                "page_title": customer["name"],
                "page_description": "Resumo operacional da conta, perfil e atividade recente.",
                "customer_status_label": customer["customer_status_label"],
                "customer_status_variant": customer["status"],
                "account_type_label": customer["account_type_label"],
                "back_href": reverse("customers:admin-customers-list"),
                "customer_reference": customer["customer_reference"],
                "customer_since": customer["customer_since"],
                "last_seen": customer["last_seen"],
                "summary_content": customer["summary_content"],
                "contact_content": customer["contact_content"],
                "profile_content": customer["profile_content"],
                "orders_summary_content": customer["orders_summary_content"],
                "account_notes_content": customer["account_notes_content"],
                "activity_items": customer["activity_items"],
            }
        )
        return context
