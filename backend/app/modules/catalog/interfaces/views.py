from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import ceil
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseNotFound
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html, format_html_join
from django.utils.text import slugify
from django.views.generic import TemplateView, View

from app.modules.accounts.application.admin_permissions import PERMISSION_CATALOG_MANAGE
from app.modules.accounts.interfaces.admin_rbac import request_admin_can, request_owner_role, request_tenant_id
from app.modules.catalog.application.admin_product_commands import admin_product_commands
from app.modules.catalog.application.admin_product_queries import (
    STATUS_OPTIONS,
    admin_product_queries,
)
from app.modules.catalog.application.admin_conversion_analytics_queries import admin_conversion_analytics_queries
from app.modules.catalog.application.catalog_metrics_queries import catalog_metrics_queries
from app.modules.catalog.application.storefront_catalog_queries import (
    storefront_catalog_queries,
)
from app.modules.catalog.application.storefront_discovery_analytics import storefront_discovery_analytics
from app.modules.catalog.application.storefront_search import storefront_product_matches_search
from app.modules.cart.application.cart_commands import cart_commands
from app.modules.checkout.application.checkout_activation_commands import (
    checkout_activation_commands,
)
from app.modules.reviews.application.review_summary_queries import product_review_summary_queries
from app.modules.tenants.application.storefront_branding_queries import (
    StorefrontHeroDefaults,
    storefront_branding_queries,
)
from app.modules.tenants.models import Tenant


def _request_tenant_id(request) -> int | None:
    return request_tenant_id(request)


def _request_owner_role(request) -> str:
    return request_owner_role(request)


def _request_hostname_and_port(request) -> tuple[str, str]:
    host = str(request.get_host() if request is not None else "").strip().lower()
    if host.count(":") == 1:
        hostname, port = host.rsplit(":", 1)
        return hostname, port
    return host, ""


def _root_domain(request=None) -> str:
    hostname, _port = _request_hostname_and_port(request)
    if hostname in {"localhost", "127.0.0.1"}:
        return "localhost"
    return str(getattr(settings, "HUBX_MARKET_ROOT_DOMAIN", "hubx.market") or "hubx.market").strip().lower()


def _public_port(request=None) -> str:
    hostname, request_port = _request_hostname_and_port(request)
    if hostname in {"localhost", "127.0.0.1"} and request_port:
        return f":{request_port}"
    port = str(getattr(settings, "HUBX_MARKET_PUBLIC_PORT", "") or "").strip()
    return f":{port}" if port else ""


def _demo_tenant_subdomain() -> str:
    return str(getattr(settings, "HUBX_MARKET_DEMO_TENANT_SUBDOMAIN", "hubx-demo") or "hubx-demo").strip().lower()


def _public_store_url(subdomain: str, path: str = "/", request=None) -> str:
    normalized_subdomain = str(subdomain or "").strip().lower()
    normalized_path = path if str(path or "").startswith("/") else f"/{path}"
    return f"http://{normalized_subdomain}.{_root_domain(request)}{_public_port(request)}{normalized_path}"


def _demo_tenant_exists() -> bool:
    return Tenant.objects.filter(subdomain=_demo_tenant_subdomain(), is_active=True).exists()


def _storefront_hero_fallback_image(products: list[dict[str, object]]) -> str:
    for product in products:
        for key in ("main_image_url", "image_url"):
            image_url = str(product.get(key) or "").strip()
            if image_url and _is_shareable_storefront_image(image_url):
                return image_url
    return ""


def _is_shareable_storefront_image(image_url: str) -> bool:
    lowered = image_url.lower()
    return "placehold.co" not in lowered


def _absolute_public_url(request, value: object) -> str:
    url = str(value or "").strip()
    if not url:
        return ""
    if url.startswith(("http://", "https://")):
        return url
    if url.startswith("//"):
        return f"{request.scheme}:{url}"
    if url.startswith("/"):
        return request.build_absolute_uri(url)
    return ""


def _storefront_social_meta(
    request,
    *,
    title: str,
    description: str = "",
    image_url: object = "",
    image_alt: str = "",
    canonical_path: str = "",
) -> dict[str, str]:
    return {
        "meta_title": title,
        "meta_description": description,
        "meta_image_url": _absolute_public_url(request, image_url),
        "meta_image_alt": image_alt or title,
        "canonical_url": request.build_absolute_uri(canonical_path or request.path),
    }


def _require_storefront_tenant(request):
    tenant = getattr(request, "tenant", None)
    tenant_id = getattr(tenant, "id", None)
    if not tenant_id:
        raise Http404("Tenant not found")
    return tenant


def _session_key(request) -> str:
    if not request.session.session_key:
        request.session.save()
    return str(request.session.session_key or "")


def _analytics_session_key(request) -> str:
    return str(getattr(request, "session", None).session_key or "") if getattr(request, "session", None) else ""


def _all_products(*, tenant_id: int | None = None) -> list[dict[str, object]]:
    return admin_product_queries.list_products(tenant_id=tenant_id)


def _get_product(product_slug: str, *, tenant_id: int | None = None) -> dict[str, object]:
    return admin_product_queries.get_product(product_slug, tenant_id=tenant_id)


def _admin_discovery_observability_by_slug(*, tenant_id: int | None) -> dict[str, dict[str, object]]:
    if not tenant_id:
        return {}
    return {
        str(product.get("slug") or ""): product
        for product in storefront_catalog_queries.list_products(tenant_id=tenant_id)
        if product.get("slug")
    }


def _admin_discovery_observability_cell(product: dict[str, object], discovery_product: dict[str, object]) -> str:
    components = discovery_product.get("discovery_rank_components") or {}
    component_summary = " · ".join(
        f"{label} {components.get(key, 0)}"
        for key, label in [
            ("status", "status"),
            ("stock", "estoque"),
            ("offer", "oferta"),
            ("featured", "destaque"),
            ("decision_signal", "sinal"),
        ]
    )
    return (
        f'Score {discovery_product.get("discovery_rank_score", 0)} · '
        f'{discovery_product.get("discovery_rank_reason", "sem razão registrada")} · '
        f"{component_summary}"
    )


def _tenant_missing_empty_state(*, tenant_id: int | None, search_value: str, status_selected: str) -> tuple[str, str] | None:
    if not tenant_id or search_value or status_selected:
        return None
    return (
        "Nenhum produto persistido nesta loja",
        "A loja atual ainda não possui produtos persistidos disponíveis para esta visão administrativa.",
    )


def _admin_product_actions_cell(product: dict[str, object], *, can_manage: bool) -> str:
    detail_href = reverse("catalog:admin-products-detail", kwargs={"product_slug": product["slug"]})
    actions = [("secondary", detail_href, "Detalhar")]
    if can_manage:
        actions.append(("primary", reverse("catalog:admin-products-edit", kwargs={"product_slug": product["slug"]}), "Editar"))
    return format_html(
        '<div class="flex flex-wrap gap-2">{}</div>',
        format_html_join(
            "",
            '<a class="ds-btn ds-btn-{} ds-btn-sm" href="{}">{}</a>',
            actions,
        ),
    )


def _variant_feedback(value: object) -> dict[str, str]:
    status = str(value or "").strip()
    mapping = {
        "created": ("success", "Variante criada", "A variante foi adicionada ao produto."),
        "default-set": ("success", "Variante padrão atualizada", "Preço e estoque principais agora vêm desta variante."),
        "deactivated": ("success", "Variante desativada", "A variante saiu da venda sem exclusão física."),
        "invalid": ("danger", "Variante não salva", "Revise SKU, preço, estoque e atributos informados."),
        "blocked": ("warning", "Ação bloqueada", "O produto precisa manter ao menos uma variante ativa e uma variante padrão válida."),
        "permission-denied": ("danger", "Permissão necessária", "Seu perfil não pode gerenciar variantes de catálogo."),
        "not-found": ("warning", "Variante indisponível", "Produto ou variante não encontrados neste tenant."),
    }
    variant, title, description = mapping.get(status, ("info", "", ""))
    return {"variant": variant, "title": title, "description": description} if title else {}


def _variant_rows(product: dict[str, object], *, can_manage: bool) -> list[dict[str, object]]:
    product_slug = str(product.get("slug") or "")
    rows = []
    for variant in list(product.get("variants") or []):
        variant_id = variant.get("id")
        row = dict(variant)
        row["status_label"] = "Ativa" if variant.get("is_active", True) else "Inativa"
        row["status_variant"] = "success" if variant.get("is_active", True) else "neutral"
        row["default_label"] = "Padrão" if variant.get("is_default") else ""
        row["set_default_url"] = (
            reverse("catalog:admin-product-variant-default", kwargs={"product_slug": product_slug, "variant_id": variant_id})
            if can_manage and variant_id and variant.get("is_active", True) and not variant.get("is_default")
            else ""
        )
        row["deactivate_url"] = (
            reverse("catalog:admin-product-variant-deactivate", kwargs={"product_slug": product_slug, "variant_id": variant_id})
            if can_manage and variant_id and variant.get("is_active", True)
            else ""
        )
        rows.append(row)
    return rows


def _page_items(page_number: int, total_pages: int, base_url: str) -> list[dict[str, object]]:
    return _compact_page_items(
        page_number=page_number,
        total_pages=total_pages,
        url_for_page=lambda number: f"{base_url}?page={number}",
    )


def _storefront_page_items(page_number: int, total_pages: int, base_url: str, query_params: list[str]) -> list[dict[str, object]]:
    suffix = "&".join(query_params)
    return _compact_page_items(
        page_number=page_number,
        total_pages=total_pages,
        url_for_page=lambda number: f"{base_url}?{suffix + '&' if suffix else ''}page={number}",
    )


def _compact_page_items(*, page_number: int, total_pages: int, url_for_page) -> list[dict[str, object]]:
    if total_pages <= 7:
        return [{"number": number, "url": url_for_page(number)} for number in range(1, total_pages + 1)]
    visible_numbers = {1, total_pages}
    visible_numbers.update(range(max(2, page_number - 1), min(total_pages, page_number + 1) + 1))
    items: list[dict[str, object]] = []
    previous_number = 0
    for number in sorted(visible_numbers):
        if previous_number and number - previous_number > 1:
            items.append({"is_ellipsis": True})
        items.append({"number": number, "url": url_for_page(number)})
        previous_number = number
    return items


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

CATALOG_SORT_OPTIONS = [
    {
        "value": "recommended",
        "label": "Recomendados",
        "helper": "Produtos com melhor disponibilidade e ofertas primeiro.",
    },
    {"value": "price_asc", "label": "Menor preço", "helper": "Preço do produto exibido."},
    {"value": "price_desc", "label": "Maior preço", "helper": "Preço do produto exibido."},
    {"value": "name_asc", "label": "Nome A-Z", "helper": "Ordem alfabética dos produtos."},
]

CATALOG_AVAILABILITY_FACET_OPTIONS = [
    {"value": "in_stock", "label": "Pronta entrega"},
    {"value": "low_stock", "label": "Últimas unidades"},
    {"value": "backorder", "label": "Sob encomenda"},
]


def _catalog_quick_filter_label(value: str) -> str:
    return next((option["label"] for option in CATALOG_QUICK_FILTER_OPTIONS if option["value"] == value), "")


def _catalog_availability_value(value: str) -> str:
    allowed_values = {option["value"] for option in CATALOG_AVAILABILITY_FACET_OPTIONS}
    return value if value in allowed_values else ""


def _catalog_availability_label(value: str) -> str:
    availability_value = _catalog_availability_value(value)
    return next((option["label"] for option in CATALOG_AVAILABILITY_FACET_OPTIONS if option["value"] == availability_value), "")


def _catalog_offer_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _catalog_sort_value(value: str) -> str:
    allowed_values = {option["value"] for option in CATALOG_SORT_OPTIONS}
    return value if value in allowed_values else "recommended"


def _catalog_sort_label(value: str) -> str:
    sort_value = _catalog_sort_value(value)
    return next((option["label"] for option in CATALOG_SORT_OPTIONS if option["value"] == sort_value), "Recomendados")


def _catalog_sort_helper(value: str) -> str:
    sort_value = _catalog_sort_value(value)
    return next((option["helper"] for option in CATALOG_SORT_OPTIONS if option["value"] == sort_value), "")


def _catalog_price_value(product: dict[str, object]) -> Decimal:
    try:
        return Decimal(str(product.get("price") or "0"))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _catalog_price_filter_value(value: str) -> Decimal | None:
    normalized = str(value or "").strip().replace(",", ".")
    if not normalized:
        return None
    try:
        price = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None
    return price if price >= 0 else None


def _catalog_price_filter_label(value: Decimal | None) -> str:
    if value is None:
        return ""
    return f"R$ {value:.2f}".replace(".", ",")


def _apply_catalog_sort(products: list[dict[str, object]], sort_value: str) -> list[dict[str, object]]:
    sort_value = _catalog_sort_value(sort_value)
    if sort_value == "price_asc":
        return sorted(products, key=lambda product: (_catalog_price_value(product), str(product.get("name") or "").lower()))
    if sort_value == "price_desc":
        return sorted(products, key=lambda product: (-_catalog_price_value(product), str(product.get("name") or "").lower()))
    if sort_value == "name_asc":
        return sorted(products, key=lambda product: str(product.get("name") or "").lower())
    return products


def _apply_catalog_facets(
    products: list[dict[str, object]],
    *,
    availability: str,
    offer_only: bool,
    price_min: Decimal | None,
    price_max: Decimal | None,
) -> list[dict[str, object]]:
    if availability:
        products = [product for product in products if str(product.get("stock_state") or "") == availability]
    if offer_only:
        products = [product for product in products if bool(str(product.get("compare_price") or "").strip())]
    if price_min is not None:
        products = [product for product in products if _catalog_price_value(product) >= price_min]
    if price_max is not None:
        products = [product for product in products if _catalog_price_value(product) <= price_max]
    return products


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
            "Não há produtos disponíveis para compra rápida neste recorte. Use Limpar para explorar outras opções.",
        )
    if quick_filter == "in_stock":
        return (
            "Nenhum produto em pronta entrega",
            "Não há produtos com disponibilidade imediata nesta visão. Use Limpar para explorar outras opções.",
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
        return f"Compra rápida disponível para {variant}, com poucas unidades em estoque."
    return f"Compra rápida disponível para {variant}. Abra o produto para conferir as opções."


def _quick_buy_card_click_helper(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Abra o produto para confirmar {variant} antes que as últimas unidades acabem."
    return f"Abra o produto para confirmar {variant} e seguir com a compra."


def _featured_card_curation_note(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Destaque editorial atual para {variant}, ainda com poucas unidades disponíveis nesta vitrine."
    if state == "out_of_stock":
        return f"Destaque da loja para {variant}, no momento sem estoque disponível."
    if state == "backorder":
        return f"Destaque da loja para {variant}, disponível sob encomenda."
    return f"Destaque da loja para {variant}. Abra para ver fotos, preço e disponibilidade."


def _featured_card_click_helper(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Abra o produto para ver {variant} e conferir as últimas unidades."
    if state == "backorder":
        return f"Abra o produto para ver {variant} e conferir como funciona a encomenda."
    if state == "out_of_stock":
        return f"Abra o produto para ver {variant} e conferir a disponibilidade."
    return f"Abra o produto para ver mais detalhes de {variant}."


def _offer_card_curation_note(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Oferta ativa para {variant}, com economia já visível e poucas unidades disponíveis nesta vitrine."
    if state == "backorder":
        return f"Oferta ativa para {variant}, disponível sob encomenda."
    if state == "out_of_stock":
        return f"Oferta ativa para {variant}, no momento sem estoque disponível."
    return f"Oferta ativa para {variant}, com economia já visível."


def _offer_card_click_helper(product: dict[str, object]) -> str:
    variant = str(product.get("effective_variant_label") or "a combinação atual")
    state = str(product.get("stock_state") or "")
    if state == "low_stock":
        return f"Abra o produto para conferir {variant} e aproveitar enquanto há poucas unidades."
    if state == "backorder":
        return f"Abra o produto para conferir {variant} e ver as condições de encomenda."
    if state == "out_of_stock":
        return f"Abra o produto para conferir {variant} e acompanhar a disponibilidade."
    return f"Abra o produto para conferir {variant} e ver os detalhes da oferta."


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
            "Veja as ofertas disponíveis agora e abra o produto para conferir detalhes, tamanhos, cores e condições de compra.",
            "Em oferta reúne produtos com preço promocional visível na vitrine. Abra o item para confirmar as opções disponíveis antes de comprar.",
            f"{results_meta} · ofertas disponíveis",
            "Nenhuma oferta ativa agora",
            "Não há produtos com oferta ativa neste recorte no momento. Use Limpar para voltar à vitrine completa.",
        )
    if quick_filter == "featured":
        return (
            "Conheça os produtos em destaque da loja e encontre opções que merecem um pouco mais da sua atenção.",
            "Em destaque reúne produtos selecionados para aparecer primeiro na vitrine. Abra o item para ver fotos, preço e disponibilidade.",
            f"{results_meta} · destaques da loja",
            "Nenhum destaque disponível agora",
            "Não há produtos em destaque neste recorte no momento. Use Limpar para voltar à vitrine completa.",
        )
    if quick_filter == "quick_buy":
        return (
            "Veja produtos disponíveis para comprar com menos passos e confirme os detalhes antes de finalizar o pedido.",
            "Compra rápida reúne itens disponíveis agora ou com poucas unidades. Abra o produto para escolher as opções e seguir com segurança.",
            f"{results_meta} · prontos para compra",
            "Nenhum produto pronto para compra rápida",
            "Não há produtos disponíveis para compra rápida neste recorte. Use Limpar para voltar à vitrine completa.",
        )
    return page_description, filter_description, results_meta, empty_title, empty_description


def _catalog_reentry_meta(*, category_label: str, search_value: str, quick_filter: str) -> str:
    quick_filter_label = _catalog_quick_filter_label(quick_filter)
    if quick_filter == "quick_buy":
        return "Produtos disponíveis para você conferir os detalhes e seguir para a compra com mais agilidade."
    if quick_filter == "featured":
        return "Destaques selecionados para facilitar sua escolha, com preço e disponibilidade visíveis antes do detalhe."
    if quick_filter == "offer":
        return "Ofertas atuais da loja, prontas para você comparar e abrir o produto que fizer mais sentido."
    if quick_filter_label:
        return f"Veja {quick_filter_label.lower()} e encontre mais rápido os produtos que combinam com o que você procura."
    if category_label and search_value:
        return "Confira os resultados desta categoria e abra os produtos que mais combinam com sua busca."
    if category_label:
        return f"Veja as opções de {category_label.lower()} disponíveis nesta loja e escolha o produto que mais combina com você."
    if search_value:
        return "Use esta busca para encontrar opções mais próximas do que você quer comprar agora."
    return "Confira os produtos da loja, compare preços e disponibilidade, e abra o item que chamou sua atenção."


def _build_catalog_quick_filter_select(*, selected: str) -> str:
    options_html = ['<option value="">Todos os recortes</option>']
    options_html.extend(
        [
            f'<option value="{option["value"]}"{" selected" if option["value"] == selected else ""}>{option["label"]}</option>'
            for option in CATALOG_QUICK_FILTER_OPTIONS
        ]
    )
    return format_html(
        '<div class="min-w-0">'
        '<div class="space-y-2">'
        '<label for="quick_filter" class="block text-sm font-medium text-[var(--color-text-primary)]">Filtro rápido</label>'
        '<select id="quick_filter" name="quick_filter" class="ds-select">{}</select>'
        '</div>'
        '</div>',
        format_html_join("", "{}", ((option,) for option in options_html)),
    )


def _build_catalog_sort_select(*, selected: str) -> str:
    selected = _catalog_sort_value(selected)
    options_html = [
        f'<option value="{option["value"]}"{" selected" if option["value"] == selected else ""}>{option["label"]}</option>'
        for option in CATALOG_SORT_OPTIONS
    ]
    return format_html(
        '<div class="min-w-0">'
        '<div class="space-y-2">'
        '<label for="sort" class="block text-sm font-medium text-[var(--color-text-primary)]">Ordenar por</label>'
        '<select id="sort" name="sort" class="ds-select">{}</select>'
        '<p class="text-xs text-[var(--color-text-secondary)]">{}</p>'
        '</div>'
        '</div>',
        format_html_join("", "{}", ((option,) for option in options_html)),
        _catalog_sort_helper(selected),
    )


def _build_catalog_availability_select(*, selected: str) -> str:
    selected = _catalog_availability_value(selected)
    options_html = ['<option value="">Toda disponibilidade</option>']
    options_html.extend(
        [
            f'<option value="{option["value"]}"{" selected" if option["value"] == selected else ""}>{option["label"]}</option>'
            for option in CATALOG_AVAILABILITY_FACET_OPTIONS
        ]
    )
    return format_html(
        '<div class="min-w-0">'
        '<div class="space-y-2">'
        '<label for="availability" class="block text-sm font-medium text-[var(--color-text-primary)]">Disponibilidade</label>'
        '<select id="availability" name="availability" class="ds-select">{}</select>'
        '</div>'
        '</div>',
        format_html_join("", "{}", ((option,) for option in options_html)),
    )


def _build_catalog_offer_select(*, selected: bool) -> str:
    return format_html(
        '<div class="min-w-0">'
        '<div class="space-y-2">'
        '<label for="offer" class="block text-sm font-medium text-[var(--color-text-primary)]">Oferta</label>'
        '<select id="offer" name="offer" class="ds-select">'
        '<option value="">Todas</option>'
        '<option value="1"{}>Somente ofertas</option>'
        '</select>'
        '</div>'
        '</div>',
        format_html(' selected') if selected else "",
    )


def _build_catalog_price_input(*, name: str, label: str, value: str) -> str:
    return format_html(
        '<div class="min-w-0">'
        '<div class="space-y-2">'
        '<label for="{}" class="block text-sm font-medium text-[var(--color-text-primary)]">{}</label>'
        '<input id="{}" name="{}" value="{}" inputmode="decimal" placeholder="0,00" class="ds-input" />'
        '</div>'
        '</div>',
        name,
        label,
        name,
        name,
        value,
    )


def _build_catalog_storefront_extra_filters(
    *,
    quick_filter: str,
    sort_value: str,
    availability: str,
    offer_only: bool,
    price_min_raw: str,
    price_max_raw: str,
) -> str:
    return format_html(
        "{}{}{}{}{}{}",
        _build_catalog_availability_select(selected=availability),
        _build_catalog_offer_select(selected=offer_only),
        _build_catalog_price_input(name="price_min", label="Preço mín.", value=price_min_raw),
        _build_catalog_price_input(name="price_max", label="Preço máx.", value=price_max_raw),
        _build_catalog_quick_filter_select(selected=quick_filter),
        _build_catalog_sort_select(selected=sort_value),
    )


def _catalog_page_description(*, category_label: str, search_value: str) -> str:
    if search_value and category_label:
        return (
            f'Veja produtos de {category_label.lower()} relacionados a “{search_value}” e abra os itens que parecem combinar com o que você procura.'
        )
    if category_label:
        return (
            f"Explore produtos de {category_label.lower()}, confira preços e disponibilidade, e escolha com mais tranquilidade."
        )
    if search_value:
        return (
            f'Confira os resultados para “{search_value}” e abra os produtos que mais combinam com sua busca.'
        )
    return "Explore a loja, compare opções disponíveis e encontre o produto certo para a sua próxima compra."


def _catalog_filter_description(*, category_label: str, search_value: str) -> str:
    if search_value and category_label:
        return (
            f'Resultados para “{search_value}” dentro de {category_label.lower()}, considerando nome, marca, categoria e descrição dos produtos.'
        )
    if search_value:
        return f'Resultados para “{search_value}”, considerando nome, marca, categoria e descrição dos produtos.'
    if category_label:
        return f"Use a categoria atual para ver produtos de {category_label.lower()} e encontrar opções disponíveis com mais facilidade."
    return "Procure pelo que você precisa ou escolha uma categoria para ver as opções disponíveis na loja."


def _catalog_results_meta(*, total_count: int, category_label: str, search_value: str) -> str:
    meta = f"{total_count} produto(s) encontrado(s)"
    if search_value:
        meta = f'{meta} · busca atual: “{search_value}”'
    if category_label:
        meta = f"{meta} · categoria atual: {category_label}"
    return f"{meta} · preços e disponibilidade atualizados"


def _catalog_empty_state(*, category_label: str, search_value: str) -> tuple[str, str]:
    if search_value and category_label:
        return (
            "Nenhum produto encontrado nesta categoria",
            f'Nenhum item de {category_label.lower()} corresponde à busca atual (“{search_value}”). Limpe a busca ou volte para todas as categorias.',
        )
    if search_value:
        return (
            "Nenhum produto encontrado para esta busca",
            f'Não encontramos resultados para “{search_value}” em nome, marca, categoria ou descrição. Tente outro termo ou limpe a busca para voltar à vitrine completa.',
        )
    if category_label:
        return (
            "Nenhum produto nesta categoria agora",
            f'Não há itens visíveis em {category_label.lower()} nesta vitrine. Volte para todas as categorias para explorar outras combinações.',
        )
    return (
        "Nenhum produto encontrado",
        "Tente ajustar a busca ou explorar outra categoria para encontrar produtos disponíveis.",
    )


def _product_id(value: object) -> int | None:
    try:
        product_id = int(value)
    except (TypeError, ValueError):
        return None
    return product_id if product_id > 0 else None


def _append_query_params(url: str, params: dict[str, str]) -> str:
    filtered_params = {key: value for key, value in params.items() if value}
    if not filtered_params:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}{urlencode(filtered_params)}"


def _pdp_cart_feedback(value: object) -> dict[str, str]:
    feedback = str(value or "").strip()
    if feedback == "added":
        return {
            "variant": "success",
            "icon": "🛒",
            "title": "Produto adicionado ao carrinho",
            "description": "Você pode continuar revisando esta combinação ou abrir o carrinho quando quiser finalizar a compra.",
        }
    if feedback == "stock-conflict":
        return {
            "variant": "warning",
            "icon": "⚠️",
            "title": "Quantidade ajustada pelo estoque disponível",
            "description": "Revise a quantidade disponível antes de tentar adicionar esta combinação novamente.",
        }
    if feedback == "unavailable":
        return {
            "variant": "warning",
            "icon": "⚠️",
            "title": "Produto indisponível para carrinho",
            "description": "Esta combinação não está disponível para compra agora. Revise outra variante ou volte à loja.",
        }
    return {}


def _review_summary_label(summary: dict[str, object] | None) -> str:
    if not summary or str(summary.get("status") or "") != "ready":
        return ""
    return f'⭐ {summary.get("rating_average")}/5 · {summary.get("review_count")} avaliação(ões)'


def _build_storefront_product_card(
    product: dict[str, object],
    *,
    active_quick_filter: str = "",
    review_summary: dict[str, object] | None = None,
) -> dict[str, object]:
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
        "meta": product.get("catalog_card_meta", ""),
        "stock_state": product.get("stock_state", _storefront_stock_state(product)),
        "availability_note": product.get("catalog_card_availability_note", ""),
        "review_summary": _review_summary_label(review_summary),
        "stock_helper": product.get("stock_helper", _storefront_stock_helper(product)),
        "action_label": "Comprar",
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
        can_manage_products = request_admin_can(self.request, PERMISSION_CATALOG_MANAGE)
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

        discovery_by_slug = _admin_discovery_observability_by_slug(tenant_id=tenant_id)
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
                "create_href": reverse("catalog:admin-products-create") if can_manage_products else "",
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
                    *([{"label": "Descoberta"}] if discovery_by_slug else []),
                    {"label": "Atualização"},
                    {"label": "Ações"},
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
                            *(
                                [
                                    _admin_discovery_observability_cell(
                                        product,
                                        discovery_by_slug[str(product.get("slug") or "")],
                                    )
                                ]
                                if str(product.get("slug") or "") in discovery_by_slug
                                else []
                            ),
                            product["updated_at"],
                            _admin_product_actions_cell(product, can_manage=can_manage_products),
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


class AdminConversionAnalyticsView(TemplateView):
    template_name = "pages/templates/admin_conversion_analytics_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        event_selected = self.request.GET.get("event_name", "").strip()
        summary = admin_conversion_analytics_queries.summary(tenant_id=tenant_id, event_name=event_selected)
        event_options = admin_conversion_analytics_queries.event_options(tenant_id=tenant_id)
        base_url = reverse("catalog:admin-conversion-analytics")

        context.update(
            {
                "page_title": "Analytics de conversão",
                "page_description": "Leitura read-only dos eventos recentes de descoberta, PDP e intenção de CTA deste tenant.",
                "page_note": "Eventos brutos são tenant-scoped, sem PII e com sessão apenas em hash interno.",
                "filter_action": base_url,
                "status_name": "event_name",
                "status_label": "Evento",
                "status_placeholder": "Todos os eventos",
                "status_options": event_options,
                "status_selected": summary["event_selected"],
                "reset_url": base_url,
                "summary_cards": [
                    {
                        "title": "Eventos registrados",
                        "content": f'{summary["total_count"]} evento(s) tenant-scoped',
                    },
                    {
                        "title": "Eventos filtrados",
                        "content": f'{summary["filtered_count"]} evento(s) neste recorte',
                    },
                    {
                        "title": "Tipos observados",
                        "content": f'{len(summary["counters"])} tipo(s) com registro',
                    },
                ],
                "counter_columns": [{"label": "Evento"}, {"label": "Total"}],
                "counter_rows": [
                    {"cells": [item["label"], str(item["count"])]}
                    for item in summary["counters"]
                ],
                "event_columns": [{"label": "Evento"}, {"label": "Resumo"}, {"label": "Path"}, {"label": "Horário"}],
                "event_rows": [
                    {
                        "cells": [
                            item["label"],
                            item["payload_summary"],
                            item["path"],
                            item["occurred_at"],
                        ]
                    }
                    for item in summary["recent_events"]
                ],
                "empty_title": "Nenhum evento de conversão registrado",
                "empty_description": "Assim que clientes navegarem pela vitrine, os eventos recentes aparecerão aqui.",
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
        can_manage_products = request_admin_can(self.request, PERMISSION_CATALOG_MANAGE)
        product = _get_product(kwargs["product_slug"], tenant_id=tenant_id)
        variant_rows = _variant_rows(product, can_manage=can_manage_products)
        context.update(
            {
                "page_title": product["name"],
                "page_description": "Resumo operacional do produto com preço, estoque e atividade recente.",
                "status_label": product["status_label"],
                "status_variant": product["status"],
                "channel_label": product["channel_label"],
                "back_href": reverse("catalog:admin-products-list"),
                "edit_href": reverse("catalog:admin-products-edit", kwargs={"product_slug": product["slug"]})
                if can_manage_products
                else "",
                "deactivate_href": reverse("catalog:admin-products-deactivate", kwargs={"product_slug": product["slug"]})
                if can_manage_products and product["status"] != "inactive"
                else "",
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
                "variant_rows": variant_rows,
                "variant_count": f"{len(variant_rows)} variante(s)",
                "variant_create_action": reverse("catalog:admin-product-variant-create", kwargs={"product_slug": product["slug"]})
                if can_manage_products
                else "",
                "can_manage_variants": can_manage_products,
                "variant_feedback": _variant_feedback(self.request.GET.get("variant_result")),
            }
        )
        return context


class AdminProductVariantCreateView(View):
    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get("product_slug")
        result = admin_product_commands.create_product_variant(
            tenant_id=_request_tenant_id(request),
            product_slug=product_slug,
            payload=request.POST,
            actor_label=AdminProductFormView._actor_label(request),
            actor_role=_request_owner_role(request),
        )
        result_status = {
            "product-variant-created": "created",
            "product-variant-invalid": "invalid",
            "product-permission-denied": "permission-denied",
            "product-not-found": "not-found",
        }.get(str(result.get("result") or ""), "invalid")
        product = result.get("product") or {"slug": product_slug}
        return HttpResponseRedirect(
            f'{reverse("catalog:admin-products-detail", kwargs={"product_slug": product.get("slug")})}?variant_result={result_status}'
        )


class AdminProductVariantDefaultView(View):
    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get("product_slug")
        result = admin_product_commands.set_default_variant(
            tenant_id=_request_tenant_id(request),
            product_slug=product_slug,
            variant_id=kwargs.get("variant_id"),
            actor_label=AdminProductFormView._actor_label(request),
            actor_role=_request_owner_role(request),
        )
        result_status = {
            "product-variant-default-set": "default-set",
            "product-variant-default-blocked": "blocked",
            "product-permission-denied": "permission-denied",
            "product-not-found": "not-found",
            "product-variant-not-found": "not-found",
        }.get(str(result.get("result") or ""), "blocked")
        product = result.get("product") or {"slug": product_slug}
        return HttpResponseRedirect(
            f'{reverse("catalog:admin-products-detail", kwargs={"product_slug": product.get("slug")})}?variant_result={result_status}'
        )


class AdminProductVariantDeactivateView(View):
    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get("product_slug")
        result = admin_product_commands.deactivate_product_variant(
            tenant_id=_request_tenant_id(request),
            product_slug=product_slug,
            variant_id=kwargs.get("variant_id"),
            actor_label=AdminProductFormView._actor_label(request),
            actor_role=_request_owner_role(request),
        )
        result_status = {
            "product-variant-deactivated": "deactivated",
            "product-variant-already-inactive": "deactivated",
            "product-variant-last-active": "blocked",
            "product-permission-denied": "permission-denied",
            "product-not-found": "not-found",
            "product-variant-not-found": "not-found",
        }.get(str(result.get("result") or ""), "blocked")
        product = result.get("product") or {"slug": product_slug}
        return HttpResponseRedirect(
            f'{reverse("catalog:admin-products-detail", kwargs={"product_slug": product.get("slug")})}?variant_result={result_status}'
        )


class AdminProductFormView(TemplateView):
    template_name = "pages/templates/admin_product_form_page.html"

    def _product_slug(self) -> str | None:
        return self.kwargs.get("product_slug")

    @staticmethod
    def _actor_label(request) -> str:
        user = getattr(request, "user", None)
        if user is None:
            return "Operação interna"
        for attr in ("get_full_name", "username", "email"):
            value = getattr(user, attr, "")
            if callable(value):
                value = value()
            value = str(value or "").strip()
            if value:
                return value
        return "Operação interna"

    def _context(self, *, values: dict[str, object] | None = None, errors: dict[str, str] | None = None) -> dict[str, object]:
        tenant_id = getattr(getattr(self.request, "tenant", None), "id", None)
        product_slug = self._product_slug()
        is_create = not product_slug
        form_initial = admin_product_queries.get_form_initial(product_slug, tenant_id=tenant_id)
        product = _get_product(product_slug, tenant_id=tenant_id) if product_slug else None
        if values:
            form_initial.update(
                {
                    "name": values.get("name", form_initial["name"]),
                    "slug": values.get("slug", form_initial["slug"]),
                    "sku": values.get("sku", form_initial["sku"]),
                    "brand": values.get("brand", form_initial["brand"]),
                    "category_label": values.get("category_label", form_initial["category_label"]),
                    "description": values.get("description", form_initial["description"]),
                    "price": values.get("price", form_initial["price"]),
                    "compare_price": values.get("compare_price", form_initial["compare_price"]),
                    "stock": values.get("stock", form_initial["stock"]),
                    "reserved_stock": values.get("reserved_stock", form_initial["reserved_stock"]),
                    "status_selected": values.get("status", form_initial["status_selected"]),
                    "is_active": "is_active" in values,
                    "is_featured": "is_featured" in values,
                    "track_inventory": "track_inventory" in values,
                    "allow_backorder": "allow_backorder" in values,
                }
            )
        return {
            "page_title": "Novo produto" if is_create else f'Editar {product["name"]}',
            "page_description": "Atualize informações principais, preço, estoque e visibilidade.",
            "form_action": self.request.path,
            "cancel_href": reverse("catalog:admin-products-list"),
            "submit_label": "Criar produto" if is_create else "Salvar produto",
            "errors": errors or {},
            "form_error": (errors or {}).get("__all__", ""),
            **form_initial,
        }

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"status_options": STATUS_OPTIONS, **self._context()})
        return context

    def post(self, request, *args, **kwargs):
        product_slug = self._product_slug()
        if product_slug:
            result = admin_product_commands.update_product(
                tenant_id=_request_tenant_id(request),
                product_slug=product_slug,
                payload=request.POST,
                actor_label=self._actor_label(request),
                actor_role=_request_owner_role(request),
            )
            success_result = "product-updated"
        else:
            result = admin_product_commands.create_product(
                tenant_id=_request_tenant_id(request),
                payload=request.POST,
                actor_label=self._actor_label(request),
                actor_role=_request_owner_role(request),
            )
            success_result = "product-created"
        if result.get("result") == success_result:
            product = result.get("product") or {}
            return HttpResponseRedirect(
                reverse("catalog:admin-products-detail", kwargs={"product_slug": product.get("slug")})
            )
        context = self.get_context_data(**kwargs)
        context.update(
            {
                "status_options": STATUS_OPTIONS,
                **self._context(values=request.POST, errors=result.get("errors") or {}),
            }
        )
        return self.render_to_response(context, status=400)


class AdminProductDeactivateView(View):
    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get("product_slug")
        result = admin_product_commands.deactivate_product(
            tenant_id=_request_tenant_id(request),
            product_slug=product_slug,
            actor_label=AdminProductFormView._actor_label(request),
            actor_role=_request_owner_role(request),
        )
        if result.get("result") == "product-deactivated":
            product = result.get("product") or {}
            return HttpResponseRedirect(
                reverse("catalog:admin-products-detail", kwargs={"product_slug": product.get("slug")})
            )
        return HttpResponseRedirect(reverse("catalog:admin-products-list"))


class CatalogListView(TemplateView):
    template_name = "pages/templates/catalog_page.html"
    product_page_template_name = "pages/partials/catalog_product_page.html"

    def get_template_names(self):
        if self.request.GET.get("fragment") == "products":
            return [self.product_page_template_name]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tenant = _require_storefront_tenant(self.request)
        search_value = self.request.GET.get("q", "").strip()
        category_selected = self.request.GET.get("category", "").strip()
        quick_filter = self.request.GET.get("quick_filter", "").strip()
        availability = _catalog_availability_value(self.request.GET.get("availability", "").strip())
        offer_only = _catalog_offer_value(self.request.GET.get("offer", "").strip())
        price_min = _catalog_price_filter_value(self.request.GET.get("price_min", ""))
        price_max = _catalog_price_filter_value(self.request.GET.get("price_max", ""))
        price_min_raw = self.request.GET.get("price_min", "").strip() if price_min is not None else ""
        price_max_raw = self.request.GET.get("price_max", "").strip() if price_max is not None else ""
        sort_value = _catalog_sort_value(self.request.GET.get("sort", "").strip())
        page_number = int(self.request.GET.get("page", "1") or "1")

        products = storefront_catalog_queries.list_products(tenant_id=getattr(tenant, "id", None))
        if search_value:
            products = [product for product in products if storefront_product_matches_search(product, search_value)]
        if category_selected:
            products = [product for product in products if _product_category_value(product) == category_selected]
        products = _apply_catalog_facets(
            products,
            availability=availability,
            offer_only=offer_only,
            price_min=price_min,
            price_max=price_max,
        )
        products = _apply_catalog_quick_filter(products, quick_filter)
        products = _apply_catalog_sort(products, sort_value)

        paginator = Paginator(products, 9)
        page_obj = paginator.get_page(page_number)
        page_product_ids = [
            product_id
            for product_id in (_product_id(product.get("id")) for product in page_obj.object_list)
            if product_id is not None
        ]
        review_summaries = product_review_summary_queries.get_product_review_summaries(
            tenant_id=getattr(tenant, "id", None),
            product_ids=page_product_ids,
        )
        storefront_discovery_analytics.record_listing_view(
            tenant_id=getattr(tenant, "id", None),
            session_key=_analytics_session_key(self.request),
            path=self.request.path,
            query=search_value,
            category=category_selected,
            availability=availability,
            offer=offer_only,
            price_min=price_min_raw,
            price_max=price_max_raw,
            quick_filter=quick_filter,
            sort=sort_value,
            result_count=paginator.count,
            page=page_obj.number,
        )
        base_url = reverse("storefront:catalog-list")

        query_params = []
        if search_value:
            query_params.append(f"q={search_value}")
        if category_selected:
            query_params.append(f"category={category_selected}")
        if availability:
            query_params.append(f"availability={availability}")
        if offer_only:
            query_params.append("offer=1")
        if price_min is not None:
            query_params.append(f"price_min={price_min_raw}")
        if price_max is not None:
            query_params.append(f"price_max={price_max_raw}")
        if quick_filter in {option["value"] for option in CATALOG_QUICK_FILTER_OPTIONS}:
            query_params.append(f"quick_filter={quick_filter}")
        if sort_value != "recommended":
            query_params.append(f"sort={sort_value}")

        def page_url(number: int) -> str:
            suffix = "&".join(query_params)
            return f"{base_url}?{suffix + '&' if suffix else ''}page={number}"

        def product_page_url(number: int) -> str:
            suffix = "&".join([*query_params, f"page={number}", "fragment=products"])
            return f"{base_url}?{suffix}"

        category_label = next(
            (option["label"] for option in _storefront_category_options() if option["value"] == category_selected),
            "",
        )
        quick_filter_label = _catalog_quick_filter_label(quick_filter)
        availability_label = _catalog_availability_label(availability)
        sort_label = _catalog_sort_label(sort_value)
        active_facet_labels = []
        if availability_label:
            active_facet_labels.append(f"disponibilidade: {availability_label}")
        if offer_only:
            active_facet_labels.append("somente ofertas")
        if price_min is not None:
            active_facet_labels.append(f"preço mínimo: {_catalog_price_filter_label(price_min)}")
        if price_max is not None:
            active_facet_labels.append(f"preço máximo: {_catalog_price_filter_label(price_max)}")
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
        if active_facet_labels:
            facet_summary = ", ".join(active_facet_labels)
            filter_description = f"{filter_description} Facets ativas: {facet_summary}."
            results_meta = f"{results_meta} · facets: {facet_summary}"
        if sort_value != "recommended":
            filter_description = f"{filter_description} Ordenação ativa: {sort_label}."
            results_meta = f"{results_meta} · ordenação: {sort_label}"
        if quick_filter_empty_state and not products:
            empty_title, empty_description = quick_filter_empty_state

        filters_open = bool(
            search_value
            or category_selected
            or availability
            or offer_only
            or price_min is not None
            or price_max is not None
            or quick_filter_label
            or sort_value != "recommended"
        )

        storefront_hero = storefront_branding_queries.get_home_hero(
            tenant=tenant,
            defaults=StorefrontHeroDefaults(
                catalog_href=base_url,
                newsletter_href=reverse("storefront_newsletter:newsletter-subscribe"),
                fallback_image_url=_storefront_hero_fallback_image(products),
            ),
        )

        context.update(
            {
                "page_title": "Loja",
                "page_description": "",
                **_storefront_social_meta(
                    self.request,
                    title=f"Loja - {getattr(tenant, 'name', '') or 'Hubx Market'}",
                    description="",
                    image_url=storefront_hero.get("image_url") or getattr(tenant, "logo_url", ""),
                    image_alt=str(storefront_hero.get("title") or getattr(tenant, "name", "") or "Loja"),
                    canonical_path=base_url,
                ),
                "page_meta": "",
                "results_meta": "",
                "storefront_hero": storefront_hero,
                "filter_action": base_url,
                "filter_description": "",
                "filters_open": filters_open,
                "active_quick_filter_label": quick_filter_label,
                "extra_filters": _build_catalog_storefront_extra_filters(
                    quick_filter=quick_filter,
                    sort_value=sort_value,
                    availability=availability,
                    offer_only=offer_only,
                    price_min_raw=price_min_raw,
                    price_max_raw=price_max_raw,
                ),
                "search_name": "q",
                "search_value": search_value,
                "status_name": "category",
                "status_label": "Categoria",
                "status_selected": category_selected,
                "status_placeholder": "Todas as categorias",
                "status_options": _storefront_category_options(),
                "reset_url": base_url,
                "products": [
                    _build_storefront_product_card(
                        product,
                        active_quick_filter=quick_filter,
                        review_summary=review_summaries.get(_product_id(product.get("id")) or 0),
                    )
                    for product in page_obj.object_list
                ],
                "empty_title": empty_title,
                "empty_description": empty_description,
                "page": page_obj.number,
                "total_pages": paginator.num_pages,
                "prev_url": page_url(page_obj.previous_page_number()) if page_obj.has_previous() else None,
                "next_url": page_url(page_obj.next_page_number()) if page_obj.has_next() else None,
                "load_more_url": product_page_url(page_obj.next_page_number()) if page_obj.has_next() else "",
                "infinite_scroll_enabled": True,
                "page_items": _storefront_page_items(page_obj.number, paginator.num_pages, base_url, query_params),
            }
        )
        return context


class StorefrontHomeView(TemplateView):
    template_name = "pages/templates/home_page.html"

    def get_template_names(self):
        if getattr(self.request, "tenant", None) is None:
            return ["pages/templates/portal_home_page.html"]
        return super().get_template_names()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if getattr(self.request, "tenant", None) is None:
            context.update(
                {
                    "page_title": "Hubx Market",
                    "page_description": "Portal comercial para lojistas criarem lojas virtuais no Hubx Market.",
                    "login_href": "/accounts/login/",
                    "plans_href": "/plans/",
                    "demo_href": "/demo/",
                    "demo_available": _demo_tenant_exists(),
                }
            )
            return context
        tenant = _require_storefront_tenant(self.request)
        tenant_id = getattr(tenant, "id", None)
        products = storefront_catalog_queries.list_products(tenant_id=tenant_id)
        featured_products = products[:3]
        product_ids = [
            product_id
            for product_id in (_product_id(product.get("id")) for product in featured_products)
            if product_id is not None
        ]
        review_summaries = product_review_summary_queries.get_product_review_summaries(
            tenant_id=tenant_id,
            product_ids=product_ids,
        )

        storefront_hero = storefront_branding_queries.get_home_hero(
            tenant=tenant,
            defaults=StorefrontHeroDefaults(
                catalog_href=reverse("storefront:catalog-list"),
                newsletter_href=reverse("storefront_newsletter:newsletter-subscribe"),
                fallback_image_url=_storefront_hero_fallback_image(featured_products),
            ),
        )

        context.update(
            {
                "page_title": "Início",
                "hero_title": f"{getattr(tenant, 'name', '') or 'Hubx Market'}",
                "hero_description": "Descubra produtos em destaque, acompanhe novidades e siga para uma compra segura.",
                **_storefront_social_meta(
                    self.request,
                    title=str(storefront_hero.get("title") or getattr(tenant, "name", "") or "Loja online"),
                    description=str(storefront_hero.get("description") or ""),
                    image_url=storefront_hero.get("image_url") or getattr(tenant, "logo_url", ""),
                    image_alt=str(storefront_hero.get("title") or getattr(tenant, "name", "") or "Loja online"),
                    canonical_path=reverse("storefront-home"),
                ),
                "storefront_hero": storefront_hero,
                "featured_products": [
                    _build_storefront_product_card(
                        product,
                        active_quick_filter="featured",
                        review_summary=review_summaries.get(_product_id(product.get("id")) or 0),
                    )
                    for product in featured_products
                ],
                "catalog_href": reverse("storefront:catalog-list"),
                "newsletter_href": reverse("storefront_newsletter:newsletter-subscribe"),
            }
        )
        return context


class PublicDemoAccessView(TemplateView):
    template_name = "pages/templates/public_demo_access_page.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        demo_subdomain = _demo_tenant_subdomain()
        demo_tenant = Tenant.objects.filter(subdomain=demo_subdomain, is_active=True).first()
        if demo_tenant is None:
            raise Http404("Demo tenant not found")
        context.update(
            {
                "page_title": "Acessar demo Hubx Market",
                "page_description": "Escolha como deseja entrar na loja demo oficial.",
                "demo_store_name": getattr(demo_tenant, "name", "") or "Hubx Demo",
                "demo_storefront_href": self._demo_storefront_url(),
                "demo_admin_login_href": self._demo_session_url(profile="admin"),
                "demo_customer_login_href": self._demo_session_url(profile="customer"),
                "footer_brand_scope": "Demo oficial",
                "footer_description": "Acesse a loja demo, compare planos e conheça o portal comercial do Hubx Market.",
                "footer_links": [
                    {"href": "/", "label": "Portal", "icon": "home"},
                    {"href": "/plans/", "label": "Planos", "icon": "receipt-text"},
                    {"href": "/demo/", "label": "Demo", "icon": "store"},
                    {"href": self._demo_storefront_url(), "label": "Vitrine demo", "icon": "shopping-bag"},
                    {"href": "/accounts/login/", "label": "Entrar", "icon": "log-in"},
                ],
            }
        )
        return context

    def _demo_storefront_url(self) -> str:
        storefront_url = _public_store_url(_demo_tenant_subdomain(), "/", request=self.request)
        return f"{storefront_url}?{urlencode({'return_url': self.request.build_absolute_uri('/demo/')})}"

    def _demo_session_url(self, *, profile: str) -> str:
        session_url = _public_store_url(_demo_tenant_subdomain(), "/accounts/demo-session/", request=self.request)
        return_url = self.request.build_absolute_uri("/demo/")
        return f"{session_url}?{urlencode({'profile': profile, 'return_url': return_url})}"


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

    @staticmethod
    def _quantity(source) -> int:
        try:
            return max(1, int(source.get("quantity", 1) or 1))
        except (TypeError, ValueError):
            return 1

    def post(self, request, *args, **kwargs):
        tenant = _require_storefront_tenant(request)
        selection = self._selection_payload(request.POST)
        tenant_id = getattr(tenant, "id", None)
        product = storefront_catalog_queries.get_product(
            kwargs["product_slug"],
            tenant_id=tenant_id,
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
            storefront_discovery_analytics.record_pdp_cta_intent(
                tenant_id=tenant_id,
                session_key=_analytics_session_key(request),
                path=request.path,
                product_id=product.get("id"),
                product_slug=str(product.get("slug") or kwargs["product_slug"]),
                cta_intent=str(request.POST.get("intent") or "buy_now").strip(),
                cta_result="unavailable",
                quantity=self._quantity(request.POST),
                variant_sku=str(product.get("sku") or ""),
            )
            messages.warning(request, "Esta combinação não está disponível para compra no momento.")
            return HttpResponseRedirect(_append_query_params(product_detail_href, {"cart_feedback": "unavailable"}))

        quantity = self._quantity(request.POST)
        intent = str(request.POST.get("intent") or "buy_now").strip()
        if intent == "add_to_cart":
            result = cart_commands.add_item(
                tenant_id=tenant_id,
                session_key=_session_key(request),
                product=product,
                quantity=quantity,
                idempotency_key=str(request.POST.get("cart_idempotency_key") or ""),
            )
            if result.get("result") in {"cart-item-added", "cart-item-added-idempotent"} and "cart" in result:
                storefront_discovery_analytics.record_pdp_cta_intent(
                    tenant_id=tenant_id,
                    session_key=_analytics_session_key(request),
                    path=request.path,
                    product_id=product.get("id"),
                    product_slug=str(product.get("slug") or kwargs["product_slug"]),
                    cta_intent="add_to_cart",
                    cta_result=str(result.get("result") or "cart-item-added"),
                    quantity=quantity,
                    variant_sku=str(product.get("sku") or ""),
                )
                messages.success(request, "Produto adicionado ao carrinho.")
                return HttpResponseRedirect(_append_query_params(product_detail_href, {"cart_feedback": "added"}))
            if result.get("result") == "cart-item-stock-unavailable":
                storefront_discovery_analytics.record_pdp_cta_intent(
                    tenant_id=tenant_id,
                    session_key=_analytics_session_key(request),
                    path=request.path,
                    product_id=product.get("id"),
                    product_slug=str(product.get("slug") or kwargs["product_slug"]),
                    cta_intent="add_to_cart",
                    cta_result="cart-item-stock-unavailable",
                    quantity=quantity,
                    variant_sku=str(product.get("sku") or ""),
                )
                messages.warning(request, "Este item não está disponível para compra no momento.")
                return HttpResponseRedirect(_append_query_params(product_detail_href, {"cart_feedback": "unavailable"}))
            elif result.get("result") == "cart-item-stock-conflict":
                storefront_discovery_analytics.record_pdp_cta_intent(
                    tenant_id=tenant_id,
                    session_key=_analytics_session_key(request),
                    path=request.path,
                    product_id=product.get("id"),
                    product_slug=str(product.get("slug") or kwargs["product_slug"]),
                    cta_intent="add_to_cart",
                    cta_result="cart-item-stock-conflict",
                    quantity=quantity,
                    variant_sku=str(product.get("sku") or ""),
                )
                messages.warning(
                    request,
                    f'Temos {result.get("available_quantity", 0)} unidade(s) disponível(is) para este item agora.',
                )
                return HttpResponseRedirect(_append_query_params(product_detail_href, {"cart_feedback": "stock-conflict"}))
            return HttpResponseRedirect(product_detail_href)

        session_key = checkout_activation_commands.activate_from_product(product, quantity=quantity)
        storefront_discovery_analytics.record_pdp_cta_intent(
            tenant_id=tenant_id,
            session_key=_analytics_session_key(request),
            path=request.path,
            product_id=product.get("id"),
            product_slug=str(product.get("slug") or kwargs["product_slug"]),
            cta_intent="buy_now",
            cta_result="checkout-activated" if session_key else "checkout-activation-unavailable",
            quantity=quantity,
            variant_sku=str(product.get("sku") or ""),
        )
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
        product_id = product.get("id")
        review_summary = product_review_summary_queries.get_product_review_summary(
            tenant_id=getattr(tenant, "id", None),
            product_id=product_id,
        )
        approved_reviews = product_review_summary_queries.list_approved_product_reviews(
            tenant_id=getattr(tenant, "id", None),
            product_id=product_id,
            limit=3,
        )
        storefront_discovery_analytics.record_product_detail_view(
            tenant_id=getattr(tenant, "id", None),
            session_key=_analytics_session_key(self.request),
            path=self.request.path,
            product_id=product_id,
            product_slug=str(product.get("slug") or kwargs["product_slug"]),
        )

        is_demo_read_only = bool(getattr(self.request, "is_demo_read_only", False))
        context.update(
            {
                "pdp_feedback": _pdp_cart_feedback(self.request.GET.get("cart_feedback")),
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
                **_storefront_social_meta(
                    self.request,
                    title=str(product["name"]),
                    description=str(product.get("product_subtitle") or product.get("short_description") or product["description"] or ""),
                    image_url=product.get("main_image_url", gallery_items[0]["url"]) or getattr(tenant, "logo_url", ""),
                    image_alt=str(product.get("main_image_alt") or gallery_items[0]["alt"] or product["name"]),
                    canonical_path=product_detail_url,
                ),
                "variant_groups": product.get("variant_groups") or _build_variant_groups(product),
                "quantity": product.get("quantity", 1),
                "form_action": product_detail_url,
                "cart_idempotency_key": uuid4().hex,
                "primary_action_label": "Adicionar ao carrinho"
                if stock_state != "out_of_stock"
                else product.get("primary_action_label", "Avise-me da reposição"),
                "primary_action_name": "intent",
                "primary_action_value": "add_to_cart",
                "primary_action_disabled": product.get("primary_action_disabled", False),
                "secondary_action_label": "Comprar agora"
                if stock_state != "out_of_stock"
                else product.get("secondary_action_label", "Ver loja"),
                "secondary_action_href": secondary_action_href if secondary_target == "catalog" else "",
                "secondary_action_type": "button" if secondary_target == "catalog" else "submit",
                "secondary_action_name": "intent",
                "secondary_action_value": "buy_now",
                "short_description": product.get("short_description", product["description"]),
                "purchase_note": product.get("purchase_note", "Seletores e estoque usam adapter de apresentação fino nesta primeira integração real."),
                "effective_variant_summary": product.get("effective_variant_summary", ""),
                "availability_note": product.get("availability_note", ""),
                "cta_helper": product.get("cta_helper", ""),
                "pdp_decision_checks": product.get("pdp_decision_checks", []),
                "eyebrow": product.get("eyebrow", product["brand"]),
                "selected_size": selection.get("size", ""),
                "selected_color": selection.get("color", ""),
                "selected_sku": selection.get("sku", ""),
                "review_summary": review_summary,
                "approved_reviews": approved_reviews,
            }
        )
        if is_demo_read_only:
            context.update(
                {
                    "primary_action_label": "Simular carrinho",
                    "primary_action_href": f'{reverse("cart:cart-page")}?{urlencode({"demo_flow": "cart"})}',
                    "primary_action_type": "button",
                    "primary_action_disabled": False,
                    "secondary_action_label": "Simular checkout",
                    "secondary_action_href": f'{reverse("checkout:checkout-page")}?{urlencode({"demo_flow": "checkout", "stage": "review"})}',
                    "secondary_action_type": "button",
                    "quantity_disabled": True,
                    "purchase_note": "Esta loja demo simula a jornada de compra com dados de leitura; nenhuma alteração é gravada.",
                    "cta_helper": "Siga para carrinho ou checkout demonstrativo sem criar carrinho, pedido ou pagamento real.",
                }
            )
        return context
