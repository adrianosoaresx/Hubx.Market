from __future__ import annotations

from django.core.paginator import Paginator
from django.urls import reverse
from django.views.generic import TemplateView

from app.modules.orders.application.admin_order_queries import (
    STATUS_OPTIONS,
    admin_order_queries,
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


class AdminOrdersListView(TemplateView):
    template_name = "pages/templates/admin_orders_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        orders = admin_order_queries.list_orders()
        if search_value:
            lowered = search_value.lower()
            orders = [
                order
                for order in orders
                if lowered in str(order["order_number"]).lower()
                or lowered in str(order["customer"]).lower()
            ]
        if status_selected:
            orders = [order for order in orders if order["status"] == status_selected]

        paginator = Paginator(orders, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("orders:admin-orders-list")

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
                "page_title": "Pedidos",
                "page_description": "Acompanhe a operação de pedidos, pagamentos e expedição.",
                "export_href": "#export-orders",
                "filter_action": base_url,
                "search_name": "q",
                "search_value": search_value,
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": base_url,
                "columns": [
                    {"label": "Pedido"},
                    {"label": "Cliente"},
                    {"label": "Status"},
                    {"label": "Pagamento"},
                    {"label": "Atualização"},
                ],
                "rows": [
                    {
                        "cells": [
                            f'#{order["order_number"]}',
                            order["customer"],
                            order["order_status_label"],
                            order["payment_status"],
                            order["updated_at"],
                        ]
                    }
                    for order in page_obj.object_list
                ],
                "table_count": f"{paginator.count} pedido(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _build_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
                "page_note": "Segunda wiring real: adapter de apresentação fino para pedidos, pronto para trocar fixtures por serviço real.",
            }
        )
        return context


class AdminOrderDetailView(TemplateView):
    template_name = "pages/templates/admin_order_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        order = admin_order_queries.get_order(kwargs["order_number"])
        context.update(
            {
                "page_title": f'Pedido #{order["order_number"]}',
                "page_description": "Resumo operacional do pedido, dados do cliente e histórico de movimentações.",
                "order_status_label": order["order_status_label"],
                "order_status_variant": order["status"],
                "fulfillment_status_label": order["fulfillment_status_label"],
                "fulfillment_status_variant": order["fulfillment_status_variant"],
                "back_href": reverse("orders:admin-orders-list"),
                "primary_href": "#update-order",
                "order_number": f'#{order["order_number"]}',
                "payment_status": order["payment_status"],
                "shipping_status": order["shipping_status"],
                "summary_content": order["summary_content"],
                "customer_content": order["customer_content"],
                "payment_content": order["payment_content"],
                "shipping_content": order["shipping_content"],
                "notes_content": order["notes_content"],
                "order_items": order["order_items"],
                "subtotal": order["subtotal"],
                "shipping": order["shipping"],
                "discount": order["discount"],
                "installments": order["installments"],
                "total": order["total"],
                "activity_items": order["activity_items"],
            }
        )
        return context
