from __future__ import annotations

from math import ceil

from django.core.paginator import Paginator
from django.urls import reverse
from django.utils.text import slugify
from django.views.generic import TemplateView

from app.modules.catalog.application.admin_product_queries import (
    STATUS_OPTIONS,
    admin_product_queries,
)
from app.modules.catalog.application.storefront_catalog_queries import (
    storefront_catalog_queries,
)

def _all_products() -> list[dict[str, object]]:
    return admin_product_queries.list_products()


def _get_product(product_slug: str) -> dict[str, object]:
    return admin_product_queries.get_product(product_slug)


def _page_items(page_number: int, total_pages: int, base_url: str) -> list[dict[str, object]]:
    return [{"number": number, "url": f"{base_url}?page={number}"} for number in range(1, total_pages + 1)]


def _storefront_page_items(page_number: int, total_pages: int, base_url: str, query_params: list[str]) -> list[dict[str, object]]:
    suffix = "&".join(query_params)
    return [
        {
            "number": number,
            "url": f"{base_url}?{suffix + '&' if suffix else ''}page={number}",
        }
        for number in range(1, total_pages + 1)
    ]


def _storefront_category_options() -> list[dict[str, str]]:
    return [
        {"value": "calcados", "label": "Calçados"},
        {"value": "vestuario", "label": "Vestuário"},
        {"value": "acessorios", "label": "Acessórios"},
    ]


def _product_category_value(product: dict[str, object]) -> str:
    category = str(product.get("category_label", "")).lower()
    if "calçado" in category:
        return "calcados"
    if "vestuário" in category:
        return "vestuario"
    return "acessorios"


def _storefront_stock_state(product: dict[str, object]) -> str:
    stock = int(product.get("stock", "0") or 0)
    if stock <= 0:
        return "backorder" if product.get("allow_backorder") else "out_of_stock"
    if stock <= 5:
        return "low_stock"
    return "in_stock"


def _storefront_stock_helper(product: dict[str, object]) -> str:
    state = _storefront_stock_state(product)
    stock = int(product.get("stock", "0") or 0)
    if state == "low_stock":
        return f"Restam {stock} unidades"
    if state == "out_of_stock":
        return "Indisponível no momento"
    if state == "backorder":
        return "Envio sob encomenda"
    return "Pronta entrega"


def _storefront_badge(product: dict[str, object]) -> tuple[str | None, str]:
    state = _storefront_stock_state(product)
    status = str(product.get("status"))
    if status == "draft":
        return "Em breve", "neutral"
    if state == "low_stock":
        return "Últimas unidades", "warning"
    if state == "backorder":
        return "Sob encomenda", "neutral"
    return "Destaque", "info"


def _build_storefront_product_card(product: dict[str, object]) -> dict[str, object]:
    return {
        "href": reverse("storefront:product-detail", kwargs={"product_slug": product["slug"]}),
        "image_url": f'https://placehold.co/640x640?text={slugify(str(product["name"]))}',
        "image_alt": str(product["name"]),
        "eyebrow": product.get("eyebrow", product["brand"]),
        "title": product["name"],
        "subtitle": product["category_label"],
        "badge_label": product.get("badge_label") or _storefront_badge(product)[0],
        "badge_variant": product.get("badge_variant") or _storefront_badge(product)[1],
        "price": f'R$ {str(product["price"]).replace(".", ",")}',
        "compare_price": f'R$ {str(product["compare_price"]).replace(".", ",")}' if product.get("compare_price") else "",
        "price_helper": product.get("price_helper", "ou 3x sem juros"),
        "meta": product["sku"],
        "stock_state": product.get("stock_state", _storefront_stock_state(product)),
        "stock_helper": product.get("stock_helper", _storefront_stock_helper(product)),
        "clickable": True,
    }


def _build_product_gallery_items(product: dict[str, object]) -> list[dict[str, object]]:
    slug = str(product["slug"])
    return [
        {"url": f"https://placehold.co/900x900?text={slug}-1", "alt": f'{product["name"]} imagem 1', "active": True},
        {"url": f"https://placehold.co/900x900?text={slug}-2", "alt": f'{product["name"]} imagem 2'},
        {"url": f"https://placehold.co/900x900?text={slug}-3", "alt": f'{product["name"]} imagem 3'},
        {"url": f"https://placehold.co/900x900?text={slug}-4", "alt": f'{product["name"]} imagem 4'},
    ]


def _build_variant_groups(product: dict[str, object]) -> list[dict[str, object]]:
    return [
        {
            "variant": "buttons",
            "name": "size",
            "label": "Tamanho",
            "selected": "42",
            "help_text": "Selecione a grade desejada.",
            "options": [
                {"value": "40", "label": "40"},
                {"value": "41", "label": "41"},
                {"value": "42", "label": "42", "selected": True},
                {"value": "43", "label": "43", "out_of_stock": True},
            ],
        },
        {
            "variant": "swatches",
            "name": "color",
            "label": "Cor",
            "selected": "preto",
            "options": [
                {"value": "preto", "label": "Preto", "color": "#111827", "selected": True},
                {"value": "cinza", "label": "Cinza", "color": "#94a3b8"},
                {"value": "azul", "label": "Azul", "color": "#3b82f6", "out_of_stock": True},
            ],
        },
    ]


class AdminProductsListView(TemplateView):
    template_name = "pages/templates/admin_products_list_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        products = _all_products()
        if search_value:
            lowered_search = search_value.lower()
            products = [
                product
                for product in products
                if lowered_search in str(product["name"]).lower() or lowered_search in str(product["sku"]).lower()
            ]
        if status_selected:
            products = [product for product in products if product["status"] == status_selected]

        paginator = Paginator(products, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("catalog:admin-products-list")

        def build_query(page: int) -> str:
            params = []
            if search_value:
                params.append(f"q={search_value}")
            if status_selected:
                params.append(f"status={status_selected}")
            params.append(f"page={page}")
            return f"{base_url}?{'&'.join(params)}"

        context.update(
            {
                "page_title": "Produtos",
                "page_description": "Gerencie catálogo, disponibilidade e status dos produtos.",
                "create_href": reverse("catalog:admin-products-create"),
                "filter_action": base_url,
                "search_name": "q",
                "search_value": search_value,
                "status_options": STATUS_OPTIONS,
                "status_selected": status_selected,
                "reset_url": base_url,
                "columns": [
                    {"label": "Produto"},
                    {"label": "SKU"},
                    {"label": "Status"},
                    {"label": "Estoque"},
                    {"label": "Atualização"},
                ],
                "rows": [
                    {
                        "cells": [
                            product["name"],
                            product["sku"],
                            product["status_label"],
                            f'{product["stock"]} un.',
                            product["updated_at"],
                        ]
                    }
                    for product in page_obj.object_list
                ],
                "table_count": f"{paginator.count} produto(s)",
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": build_query(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": build_query(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _page_items(page_obj.number, paginator.num_pages, base_url),
                "page_note": "Primeira wiring real: view fina com adapter de contexto, pronta para trocar fixtures por serviço real.",
            }
        )
        return context


class AdminProductDetailView(TemplateView):
    template_name = "pages/templates/admin_product_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = _get_product(kwargs["product_slug"])
        context.update(
            {
                "page_title": product["name"],
                "page_description": "Resumo operacional do produto com preço, estoque e atividade recente.",
                "status_label": product["status_label"],
                "status_variant": product["status"],
                "channel_label": product["channel_label"],
                "back_href": reverse("catalog:admin-products-list"),
                "edit_href": reverse("catalog:admin-products-edit", kwargs={"product_slug": product["slug"]}),
                "summary_content": product["summary_content"],
                "pricing_content": product["pricing_content"],
                "inventory_content": product["inventory_content"],
                "details_content": product["details_content"],
                "visibility_content": product["visibility_content"],
                "sku": product["sku"],
                "category_label": product["category_label"],
                "sales_channel": product["sales_channel"],
                "updated_at": product["updated_at"],
                "activity_items": product["activity_items"],
            }
        )
        return context


class AdminProductFormView(TemplateView):
    template_name = "pages/templates/admin_product_form_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_slug = kwargs.get("product_slug")
        is_create = not product_slug
        form_initial = admin_product_queries.get_form_initial(product_slug)
        product = _get_product(product_slug) if product_slug else None

        context.update(
            {
                "page_title": "Novo produto" if is_create else f'Editar {product["name"]}',
                "page_description": "Atualize informações principais, preço, estoque e visibilidade.",
                "form_action": self.request.path,
                "cancel_href": reverse("catalog:admin-products-list"),
                "name": form_initial["name"],
                "slug": form_initial["slug"],
                "sku": form_initial["sku"],
                "brand": form_initial["brand"],
                "description": form_initial["description"],
                "price": form_initial["price"],
                "compare_price": form_initial["compare_price"],
                "stock": form_initial["stock"],
                "reserved_stock": form_initial["reserved_stock"],
                "status_options": STATUS_OPTIONS,
                "status_selected": form_initial["status_selected"],
                "is_active": form_initial["is_active"],
                "is_featured": form_initial["is_featured"],
                "track_inventory": form_initial["track_inventory"],
                "allow_backorder": form_initial["allow_backorder"],
            }
        )
        return context


class CatalogListView(TemplateView):
    template_name = "pages/templates/catalog_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_value = self.request.GET.get("q", "").strip()
        category_selected = self.request.GET.get("category", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        products = storefront_catalog_queries.list_products()
        if search_value:
            lowered_search = search_value.lower()
            products = [
                product
                for product in products
                if lowered_search in str(product["name"]).lower()
                or lowered_search in str(product["brand"]).lower()
                or lowered_search in str(product["sku"]).lower()
            ]
        if category_selected:
            products = [product for product in products if _product_category_value(product) == category_selected]

        paginator = Paginator(products, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("storefront:catalog-list")

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if category_selected:
            query_params.append(f"category={category_selected}")

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        context.update(
            {
                "page_title": "Catálogo",
                "page_description": "Explore produtos, novidades e categorias disponíveis na loja.",
                "results_meta": f"{paginator.count} produto(s) encontrado(s)",
                "filter_action": base_url,
                "search_name": "q",
                "search_value": search_value,
                "status_name": "category",
                "status_label": "Categoria",
                "status_selected": category_selected,
                "status_placeholder": "Todas as categorias",
                "status_options": _storefront_category_options(),
                "reset_url": base_url,
                "products": [_build_storefront_product_card(product) for product in page_obj.object_list],
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "page_items": _storefront_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
            }
        )
        return context


class ProductDetailView(TemplateView):
    template_name = "pages/templates/product_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = storefront_catalog_queries.get_product(kwargs["product_slug"])
        gallery_items = product.get("product_gallery_items") or _build_product_gallery_items(product)
        stock_state = product.get("stock_state", _storefront_stock_state(product))
        stock_helper = product.get("stock_helper", _storefront_stock_helper(product))

        context.update(
            {
                "product_title": product["name"],
                "product_subtitle": product["description"],
                "price": f'R$ {str(product["price"]).replace(".", ",")}',
                "compare_price": f'R$ {str(product["compare_price"]).replace(".", ",")}' if product.get("compare_price") else "",
                "price_helper": product.get("price_helper", "parcelamento disponível"),
                "stock_state": stock_state,
                "stock_helper": stock_helper,
                "product_gallery_items": gallery_items,
                "main_image_url": product.get("main_image_url", gallery_items[0]["url"]),
                "main_image_alt": product.get("main_image_alt", gallery_items[0]["alt"]),
                "variant_groups": product.get("variant_groups") or _build_variant_groups(product),
                "quantity": product.get("quantity", 1),
                "primary_action_label": product.get("primary_action_label", "Adicionar ao carrinho"),
                "secondary_action_label": product.get("secondary_action_label", "Comprar agora"),
                "secondary_action_href": product.get("secondary_action_href", "#checkout"),
                "short_description": product.get("short_description", product["description"]),
                "purchase_note": product.get("purchase_note", "Seletores e estoque usam adapter de apresentação fino nesta primeira integração real."),
                "eyebrow": product.get("eyebrow", product["brand"]),
            }
        )
        return context
