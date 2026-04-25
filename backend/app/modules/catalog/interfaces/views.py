from __future__ import annotations

from math import ceil
from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import Paginator
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.views.generic import TemplateView, View

from app.modules.catalog.application.admin_product_queries import (
    STATUS_OPTIONS,
    admin_product_queries,
)
from app.modules.catalog.application.catalog_metrics_queries import catalog_metrics_queries
from app.modules.catalog.application.storefront_catalog_queries import (
    storefront_catalog_queries,
)
from app.modules.checkout.application.checkout_activation_commands import (
    checkout_activation_commands,
)


def _require_storefront_tenant(request):
    tenant = getattr(request, "tenant", None)
    tenant_id = getattr(tenant, "id", None)
    if not tenant_id:
        raise Http404("Tenant not found")
    return tenant

def _all_products(*, tenant_id: int | None = None) -> list[dict[str, object]]:
    return admin_product_queries.list_products(tenant_id=tenant_id)


def _get_product(product_slug: str, *, tenant_id: int | None = None) -> dict[str, object]:
    return admin_product_queries.get_product(product_slug, tenant_id=tenant_id)


def _tenant_missing_empty_state(*, tenant_id: int | None, search_value: str, status_selected: str) -> tuple[str, str] | None:
    if not tenant_id or search_value or status_selected:
        return None
    return (
        "Nenhum produto persistido nesta loja",
        "A loja atual ainda não possui produtos persistidos disponíveis para esta visão administrativa.",
    )


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


CATALOG_QUICK_FILTER_OPTIONS = [
    {"value": "featured", "label": "Em destaque"},
    {"value": "quick_buy", "label": "Compra rápida"},
    {"value": "in_stock", "label": "Pronta entrega"},
    {"value": "low_stock", "label": "Estoque baixo"},
    {"value": "backorder", "label": "Sob encomenda"},
    {"value": "offer", "label": "Em oferta"},
]


def _catalog_quick_filter_label(value: str) -> str:
    return next((option["label"] for option in CATALOG_QUICK_FILTER_OPTIONS if option["value"] == value), "")


def _apply_catalog_quick_filter(products: list[dict[str, object]], quick_filter: str) -> list[dict[str, object]]:
    if quick_filter == "featured":
        return [product for product in products if bool(product.get("is_featured"))]
    if quick_filter == "quick_buy":
        return [
            product
            for product in products
            if str(product.get("status") or "").strip().lower() != "draft"
            and str(product.get("stock_state") or "") in {"in_stock", "low_stock"}
        ]
    if quick_filter == "in_stock":
        return [product for product in products if str(product.get("stock_state") or "") == "in_stock"]
    if quick_filter == "low_stock":
        return [product for product in products if str(product.get("stock_state") or "") == "low_stock"]
    if quick_filter == "backorder":
        return [product for product in products if str(product.get("stock_state") or "") == "backorder"]
    if quick_filter == "offer":
        return [product for product in products if bool(str(product.get("compare_price") or "").strip())]
    return products


def _catalog_quick_filter_empty_state(*, quick_filter: str) -> tuple[str, str] | tuple[str, str] | None:
    if quick_filter == "featured":
        return (
            "Nenhum destaque disponível agora",
            "Não há produtos em destaque neste recorte no momento. Use Limpar para voltar à vitrine completa.",
        )
    if quick_filter == "quick_buy":
        return (
            "Nenhum produto pronto para compra rápida",
            "Não há combinações ativas e disponíveis para compra rápida neste recorte. Use Limpar para explorar outras disponibilidades.",
        )
    if quick_filter == "in_stock":
        return (
            "Nenhum produto em pronta entrega",
            "Não há produtos com disponibilidade imediata nesta visão. Use Limpar para explorar outras combinações.",
        )
    if quick_filter == "low_stock":
        return (
            "Nenhum produto com estoque baixo",
            "Nenhum card desta visão está com estoque baixo agora. Use Limpar para voltar à vitrine completa.",
        )
    if quick_filter == "backorder":
        return (
            "Nenhum produto sob encomenda",
            "Não há produtos sob encomenda nesta visão. Use Limpar para revisar outras disponibilidades.",
        )
    if quick_filter == "offer":
        return (
            "Nenhuma oferta ativa agora",
            "Não há produtos com oferta ativa neste recorte no momento. Use Limpar para voltar à vitrine completa.",
        )
    return None


def _quick_buy_card_curation_note(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Compra rápida disponível para {variant}, com poucas unidades e base comercial já pronta para decisão."
    return f"Compra rápida disponível para {variant}, com combinação ativa pronta para seguir do card ao detalhe."


def _quick_buy_card_click_helper(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Abra o produto para confirmar {variant} e seguir para checkout com a mesma leitura de estoque baixo mostrada aqui."
    return f"Abra o produto para confirmar {variant} e seguir para checkout com a mesma base comercial mostrada neste card."


def _featured_card_curation_note(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Destaque editorial atual para {variant}, ainda com poucas unidades disponíveis nesta vitrine."
    if state == "out_of_stock":
        return f"Destaque editorial atual para {variant}, com contexto de reposição já sinalizado no card."
    if state == "backorder":
        return f"Destaque editorial atual para {variant}, com reserva disponível e prazo revisado no detalhe."
    return f"Destaque editorial atual para {variant}, com a mesma base comercial preservada até o detalhe."


def _featured_card_click_helper(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Abra o produto para revisar {variant} com a mesma leitura de destaque e poucas unidades mostrada neste card."
    if state == "backorder":
        return f"Abra o produto para revisar {variant} com o mesmo contexto de destaque e reserva visto aqui."
    if state == "out_of_stock":
        return f"Abra o produto para revisar {variant} com o mesmo contexto de destaque e reposição mostrado aqui."
    return f"Abra o produto para revisar {variant} com a mesma leitura de destaque editorial mostrada neste card."


def _offer_card_curation_note(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Oferta ativa para {variant}, com economia já visível e poucas unidades disponíveis nesta vitrine."
    if state == "backorder":
        return f"Oferta ativa para {variant}, com reserva disponível e valor comparativo mantido no detalhe."
    if state == "out_of_stock":
        return f"Oferta ativa para {variant}, com contexto de reposição preservado enquanto o valor comparativo segue visível."
    return f"Oferta ativa para {variant}, com economia já visível e mesma base comercial preservada até o detalhe."


def _offer_card_click_helper(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Abra o produto para revisar {variant} com a mesma leitura de oferta e estoque baixo mostrada neste card."
    if state == "backorder":
        return f"Abra o produto para revisar {variant} com o mesmo contexto de oferta e reserva visto aqui."
    if state == "out_of_stock":
        return f"Abra o produto para revisar {variant} com o mesmo contexto de oferta e reposição mostrado aqui."
    return f"Abra o produto para revisar {variant} com a mesma leitura de oferta ativa mostrada neste card."


def _apply_quick_filter_context(
    *,
    quick_filter: str,
    page_description: str,
    filter_description: str,
    results_meta: str,
    empty_title: str,
    empty_description: str,
) -> tuple[str, str, str, str, str]:
    if quick_filter == "offer":
        return (
            "Explore ofertas ativas da vitrine, com valor comparativo real, combinação efetiva e continuidade segura até o detalhe do produto.",
            "Em oferta reúne produtos com preço comparativo ativo já visível no card, sem mudar a base comercial nem a combinação efetiva ao abrir o detalhe.",
            f"{results_meta} · recorte offer: ofertas ativas com continuidade segura até o PDP",
            "Nenhuma oferta ativa agora",
            "Não há produtos com oferta ativa neste recorte no momento. Use Limpar para voltar à vitrine completa.",
        )
    if quick_filter == "featured":
        return (
            "Explore os destaques atuais da vitrine, com combinação efetiva, contexto comercial real e continuidade segura até o detalhe do produto.",
            "Em destaque reúne produtos priorizados pela vitrine usando sinais reais já visíveis no card, sem mudar a base comercial ao abrir o detalhe.",
            f"{results_meta} · recorte featured: destaques atuais com continuidade segura até o PDP",
            "Nenhum destaque disponível agora",
            "Não há produtos em destaque neste recorte no momento. Use Limpar para voltar à vitrine completa.",
        )
    if quick_filter == "quick_buy":
        return (
            "Explore produtos prontos para compra rápida, com combinação efetiva, disponibilidade real e continuidade segura até o detalhe do produto.",
            "Compra rápida reúne combinações ativas, em estoque ou com poucas unidades, já prontas para decisão sem mudar a base comercial no detalhe.",
            f"{results_meta} · recorte quick buy: combinações prontas para compra rápida e continuidade segura até o PDP",
            "Nenhum produto pronto para compra rápida",
            "Não há combinações ativas e disponíveis para compra rápida neste recorte. Use Limpar para voltar à vitrine completa.",
        )
    return page_description, filter_description, results_meta, empty_title, empty_description


def _catalog_reentry_meta(*, category_label: str, search_value: str, quick_filter: str) -> str:
    quick_filter_label = _catalog_quick_filter_label(quick_filter)
    if quick_filter == "quick_buy":
        return "Compra rápida pronta para retomar sua navegação, com a mesma base comercial do card até o detalhe."
    if quick_filter == "featured":
        return "Os destaques da vitrine continuam prontos para receber sua próxima compra com leitura consistente até o detalhe."
    if quick_filter == "offer":
        return "As ofertas da vitrine continuam alinhadas ao detalhe para facilitar uma nova decisão de compra sem surpresa."
    if quick_filter_label:
        return f"Este recorte rápido mantém a vitrine pronta para sua próxima compra enquanto você revisa {quick_filter_label.lower()}."
    if category_label and search_value:
        return "A vitrine continua pronta para sua próxima compra enquanto você refina a busca e aprofunda no detalhe as combinações mais promissoras mostradas aqui."
    if category_label:
        return f"A vitrine de {category_label.lower()} continua pronta para sua próxima compra, com continuidade clara entre card, curadoria leve e detalhe."
    if search_value:
        return "Use esta busca para retomar a navegação com mais foco; o detalhe continua aprofundando a mesma base comercial e editorial mostrada na vitrine."
    return "A vitrine continua pronta para receber sua próxima compra, com cards e detalhe alinhados pela mesma base comercial e por uma curadoria leve."


def _build_catalog_quick_filter_select(*, selected: str) -> str:
    options_html = ['<option value="">Todos os recortes</option>']
    options_html.extend(
        [
            f'<option value="{option["value"]}"{" selected" if option["value"] == selected else ""}>{option["label"]}</option>'
            for option in CATALOG_QUICK_FILTER_OPTIONS
        ]
    )
    return format_html(
        '<div class="w-full lg:w-56">'
        '<div class="space-y-2">'
        '<label for="quick_filter" class="block text-sm font-medium text-[var(--color-text-primary)]">Filtro rápido</label>'
        '<select id="quick_filter" name="quick_filter" class="ds-select">{}</select>'
        '</div>'
        '</div>',
        format_html_join("", "{}", ((option,) for option in options_html)),
    )


def _catalog_page_description(*, category_label: str, search_value: str) -> str:
    if search_value and category_label:
        return (
            f'Explore {category_label.lower()} com busca ativa para “{search_value}”, combinando disponibilidade real, combinação em destaque e uma curadoria leve para ajudar a escolher o próximo produto que vale abrir.'
        )
    if category_label:
        return (
            f"Explore {category_label.lower()} com combinações em destaque, disponibilidade atual e uma curadoria leve para descobrir os produtos mais interessantes desta vitrine com mais confiança."
        )
    if search_value:
        return (
            f'Explore resultados para “{search_value}” com disponibilidade atual, combinações em destaque e uma curadoria leve para encontrar mais rápido o produto que vale abrir agora.'
        )
    return "Explore produtos com combinações em destaque, disponibilidade atual e uma curadoria leve para encontrar com mais confiança o próximo item que vale sua atenção nesta vitrine."


def _catalog_filter_description(*, category_label: str, search_value: str) -> str:
    if search_value and category_label:
        return (
            f'Resultados para “{search_value}” dentro de {category_label.lower()}, combinando nome, marca, SKU e sinais atuais de destaque, oferta e disponibilidade já visíveis nos cards.'
        )
    if search_value:
        return f'Resultados para “{search_value}”, combinando nome, marca, SKU e sinais atuais de destaque, oferta e disponibilidade já visíveis nos cards.'
    if category_label:
        return f"Use a categoria atual para refinar a vitrine sem perder combinação em destaque, disponibilidade e curadoria comercial leve."
    return "Use busca e categoria para encontrar mais rápido produtos com combinação em destaque, disponibilidade e curadoria comercial leve."


def _catalog_results_meta(*, total_count: int, category_label: str, search_value: str) -> str:
    meta = f"{total_count} produto(s) encontrado(s)"
    if search_value:
        meta = f'{meta} · busca atual: “{search_value}”'
    if category_label:
        meta = f"{meta} · categoria atual: {category_label}"
    return f"{meta} · cards já refletem variante efetiva, disponibilidade atual e sinais leves de curadoria da vitrine"


def _catalog_empty_state(*, category_label: str, search_value: str) -> tuple[str, str]:
    if search_value and category_label:
        return (
            "Nenhum produto encontrado nesta categoria",
            f'Nenhum item de {category_label.lower()} corresponde à busca atual (“{search_value}”). Limpe a busca ou volte para todas as categorias.',
        )
    if search_value:
        return (
            "Nenhum produto encontrado para esta busca",
            f'Não encontramos resultados para “{search_value}” no nome, marca ou SKU. Tente outro termo ou limpe a busca para voltar à vitrine completa.',
        )
    if category_label:
        return (
            "Nenhum produto nesta categoria agora",
            f'Não há itens visíveis em {category_label.lower()} nesta vitrine. Volte para todas as categorias para explorar outras combinações.',
        )
    return (
        "Nenhum produto encontrado",
        "Tente ajustar a busca ou explorar outra categoria para encontrar produtos com preço, disponibilidade e combinação em destaque.",
    )


def _build_storefront_product_card(product: dict[str, object], *, active_quick_filter: str = "") -> dict[str, object]:
    curation_note = product.get("catalog_card_curation_note", "")
    click_helper = product.get("catalog_card_click_helper", "")
    if active_quick_filter == "offer":
        curation_note = _offer_card_curation_note(product)
        click_helper = _offer_card_click_helper(product)
    if active_quick_filter == "featured":
        curation_note = _featured_card_curation_note(product)
        click_helper = _featured_card_click_helper(product)
    if active_quick_filter == "quick_buy":
        curation_note = _quick_buy_card_curation_note(product)
        click_helper = _quick_buy_card_click_helper(product)
    return {
        "href": reverse("storefront:product-detail", kwargs={"product_slug": product["slug"]}),
        "image_url": product.get("main_image_url") or f'https://placehold.co/640x640?text={slugify(str(product["name"]))}',
        "image_alt": product.get("main_image_alt") or str(product["name"]),
        "eyebrow": product.get("eyebrow", product["brand"]),
        "title": product["name"],
        "subtitle": product.get("catalog_card_subtitle") or product["category_label"],
        "badge_label": product.get("badge_label") or _storefront_badge(product)[0],
        "badge_variant": product.get("badge_variant") or _storefront_badge(product)[1],
        "price": f'R$ {str(product["price"]).replace(".", ",")}',
        "compare_price": f'R$ {str(product["compare_price"]).replace(".", ",")}' if product.get("compare_price") else "",
        "price_helper": product.get("catalog_card_price_helper") or product.get("price_helper", "ou 3x sem juros"),
        "meta": product.get("catalog_card_meta") or product["sku"],
        "stock_state": product.get("stock_state", _storefront_stock_state(product)),
        "variant_summary": product.get("catalog_card_variant_summary", ""),
        "curation_note": curation_note,
        "availability_note": product.get("catalog_card_availability_note", ""),
        "click_helper": click_helper,
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
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        search_value = self.request.GET.get("q", "").strip()
        status_selected = self.request.GET.get("status", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        products = _all_products(tenant_id=tenant_id)
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
        empty_title = "Nenhum produto encontrado"
        empty_description = "Ajuste os filtros ou cadastre um novo produto."
        tenant_missing_empty_state = _tenant_missing_empty_state(
            tenant_id=tenant_id,
            search_value=search_value,
            status_selected=status_selected,
        )
        if tenant_missing_empty_state and not products:
            empty_title, empty_description = tenant_missing_empty_state

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
                            (
                                f'{product["stock"]} un. · reservadas {product.get("reserved_stock", "0")} '
                                f'· recuperadas {product.get("recovered_stock", "0")} '
                                f'· finalizadas {product.get("finalized_stock", "0")}'
                            ),
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
                "page_note": admin_product_queries.get_inventory_visibility_note(tenant_id=tenant_id),
                "empty_title": empty_title,
                "empty_description": empty_description,
            }
        )
        return context


class CatalogMetricsView(View):
    http_method_names = ["get"]

    def get(self, request, *args, **kwargs):
        configured_token = str(getattr(settings, "CATALOG_OBSERVABILITY_TOKEN", "") or "").strip()
        if not configured_token:
            return HttpResponseNotFound("Métricas de catálogo indisponíveis.")

        provided_token = str(request.headers.get("X-Hubx-Observability-Token", "") or "").strip()
        if not provided_token:
            authorization_header = str(request.headers.get("Authorization", "") or "").strip()
            if authorization_header.lower().startswith("bearer "):
                provided_token = authorization_header[7:].strip()
        if provided_token != configured_token:
            return HttpResponse("Forbidden", status=403, content_type="text/plain; charset=utf-8")

        return HttpResponse(
            catalog_metrics_queries.export_prometheus_metrics(),
            status=200,
            content_type="text/plain; version=0.0.4; charset=utf-8",
        )


class AdminProductDetailView(TemplateView):
    template_name = "pages/templates/admin_product_detail_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        product = _get_product(kwargs["product_slug"], tenant_id=tenant_id)
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
                "inventory_content": " ".join(
                    part
                    for part in [
                        product["inventory_content"],
                        product.get("inventory_visibility_content", ""),
                        product.get("inventory_recovery_content", ""),
                        product.get("inventory_finalization_content", ""),
                        product.get("inventory_timeline_content", ""),
                    ]
                    if part
                ),
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
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        product_slug = kwargs.get("product_slug")
        is_create = not product_slug
        form_initial = admin_product_queries.get_form_initial(product_slug, tenant_id=tenant_id)
        product = _get_product(product_slug, tenant_id=tenant_id) if product_slug else None

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
        tenant = _require_storefront_tenant(self.request)
        search_value = self.request.GET.get("q", "").strip()
        category_selected = self.request.GET.get("category", "").strip()
        quick_filter = self.request.GET.get("quick_filter", "").strip()
        page_number = int(self.request.GET.get("page", "1") or "1")

        products = storefront_catalog_queries.list_products(tenant_id=getattr(tenant, "id", None))
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
        products = _apply_catalog_quick_filter(products, quick_filter)

        paginator = Paginator(products, 2)
        page_obj = paginator.get_page(page_number)
        base_url = reverse("storefront:catalog-list")

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if category_selected:
            query_params.append(f"category={category_selected}")
        if quick_filter in {option["value"] for option in CATALOG_QUICK_FILTER_OPTIONS}:
            query_params.append(f"quick_filter={quick_filter}")

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        category_label = next(
            (option["label"] for option in _storefront_category_options() if option["value"] == category_selected),
            "",
        )
        quick_filter_label = _catalog_quick_filter_label(quick_filter)
        page_description = _catalog_page_description(category_label=category_label, search_value=search_value)
        filter_description = _catalog_filter_description(category_label=category_label, search_value=search_value)
        results_meta = _catalog_results_meta(
            total_count=paginator.count,
            category_label=category_label,
            search_value=search_value,
        )
        empty_title, empty_description = _catalog_empty_state(
            category_label=category_label,
            search_value=search_value,
        )
        page_description, filter_description, results_meta, empty_title, empty_description = _apply_quick_filter_context(
            quick_filter=quick_filter,
            page_description=page_description,
            filter_description=filter_description,
            results_meta=results_meta,
            empty_title=empty_title,
            empty_description=empty_description,
        )
        quick_filter_empty_state = _catalog_quick_filter_empty_state(quick_filter=quick_filter)
        if quick_filter_label:
            page_description = f"{page_description} Filtro rápido ativo: {quick_filter_label}."
            filter_description = f"{filter_description} Filtro rápido ativo: {quick_filter_label}. Use Limpar para voltar à vitrine completa."
            results_meta = f"{results_meta} · filtro rápido: {quick_filter_label} · use Limpar para remover este recorte"
        if quick_filter_empty_state and not products:
            empty_title, empty_description = quick_filter_empty_state

        context.update(
            {
                "page_title": "Catálogo",
                "page_description": page_description,
                "page_meta": _catalog_reentry_meta(
                    category_label=category_label,
                    search_value=search_value,
                    quick_filter=quick_filter,
                ),
                "results_meta": results_meta,
                "filter_action": base_url,
                "filter_description": filter_description,
                "active_quick_filter_label": quick_filter_label,
                "extra_filters": _build_catalog_quick_filter_select(selected=quick_filter),
                "search_name": "q",
                "search_value": search_value,
                "status_name": "category",
                "status_label": "Categoria",
                "status_selected": category_selected,
                "status_placeholder": "Todas as categorias",
                "status_options": _storefront_category_options(),
                "reset_url": base_url,
                "products": [
                    _build_storefront_product_card(product, active_quick_filter=quick_filter)
                    for product in page_obj.object_list
                ],
                "empty_title": empty_title,
                "empty_description": empty_description,
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

    @staticmethod
    def _selection_payload(source) -> dict[str, str]:
        return {
            "size": str(source.get("size", "") or "").strip(),
            "color": str(source.get("color", "") or "").strip(),
            "sku": str(source.get("sku", "") or "").strip(),
        }

    @staticmethod
    def _selection_query(selection: dict[str, str]) -> dict[str, str]:
        return {key: value for key, value in selection.items() if value}

    def post(self, request, *args, **kwargs):
        tenant = _require_storefront_tenant(request)
        selection = self._selection_payload(request.POST)
        product = storefront_catalog_queries.get_product(
            kwargs["product_slug"],
            tenant_id=getattr(tenant, "id", None),
            **selection,
        )
        if not product:
            raise Http404("Product not found")
        product_detail_url = reverse("storefront:product-detail", kwargs={"product_slug": kwargs["product_slug"]})
        selection_query = self._selection_query(selection)
        product_detail_href = (
            f"{product_detail_url}?{urlencode(selection_query)}" if selection_query else product_detail_url
        )
        if str(product.get("stock_state") or "") == "out_of_stock":
            return HttpResponseRedirect(product_detail_href)

        session_key = checkout_activation_commands.activate_from_product(product)
        params = {"back_url": product_detail_href, "stage": "cart"}
        if session_key:
            params["session_key"] = session_key
        return HttpResponseRedirect(f'{reverse("checkout:checkout-page")}?{urlencode(params)}')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = _require_storefront_tenant(self.request)
        selection = self._selection_payload(self.request.GET)
        product = storefront_catalog_queries.get_product(
            kwargs["product_slug"],
            tenant_id=getattr(tenant, "id", None),
            **selection,
        )
        if not product:
            raise Http404("Product not found")
        product_detail_url = reverse("storefront:product-detail", kwargs={"product_slug": kwargs["product_slug"]})
        selection_query = self._selection_query(selection)
        product_detail_href = (
            f"{product_detail_url}?{urlencode(selection_query)}" if selection_query else product_detail_url
        )
        secondary_target = str(product.get("secondary_action_target") or "checkout")
        if secondary_target == "catalog":
            secondary_action_href = reverse("storefront:catalog-list")
        else:
            secondary_action_href = f'{reverse("checkout:checkout-page")}?{urlencode({"back_url": product_detail_href})}'
        gallery_items = product.get("product_gallery_items") or _build_product_gallery_items(product)
        stock_state = product.get("stock_state", _storefront_stock_state(product))
        stock_helper = product.get("stock_helper", _storefront_stock_helper(product))

        context.update(
            {
                "product_title": product["name"],
                "product_subtitle": product.get("product_subtitle", product["description"]),
                "price": f'R$ {str(product["price"]).replace(".", ",")}',
                "compare_price": f'R$ {str(product["compare_price"]).replace(".", ",")}' if product.get("compare_price") else "",
                "price_helper": product.get("price_helper", "parcelamento disponível"),
                "stock_state": stock_state,
                "stock_label": product.get("stock_label", ""),
                "stock_helper": stock_helper,
                "product_gallery_items": gallery_items,
                "main_image_url": product.get("main_image_url", gallery_items[0]["url"]),
                "main_image_alt": product.get("main_image_alt", gallery_items[0]["alt"]),
                "variant_groups": product.get("variant_groups") or _build_variant_groups(product),
                "quantity": product.get("quantity", 1),
                "form_action": product_detail_url,
                "primary_action_label": product.get("primary_action_label", "Adicionar ao carrinho"),
                "primary_action_disabled": product.get("primary_action_disabled", False),
                "secondary_action_label": product.get("secondary_action_label", "Comprar agora"),
                "secondary_action_href": secondary_action_href,
                "short_description": product.get("short_description", product["description"]),
                "purchase_note": product.get("purchase_note", "Seletores e estoque usam adapter de apresentação fino nesta primeira integração real."),
                "effective_variant_summary": product.get("effective_variant_summary", ""),
                "availability_note": product.get("availability_note", ""),
                "cta_helper": product.get("cta_helper", ""),
                "eyebrow": product.get("eyebrow", product["brand"]),
                "selected_size": selection.get("size", ""),
                "selected_color": selection.get("color", ""),
                "selected_sku": selection.get("sku", ""),
            }
        )
        return context
