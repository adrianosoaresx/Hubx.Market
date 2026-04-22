from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from app.modules.catalog.application.admin_product_queries import (
    FallbackProductRepository,
    DjangoOrmProductRepository,
    ProductReadRepository,
    admin_product_queries,
)


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _stock_state(product: dict[str, object]) -> str:
    stock = _safe_int(product.get("stock"))
    if stock <= 0:
        return "backorder" if product.get("allow_backorder") else "out_of_stock"
    if stock <= 5:
        return "low_stock"
    return "in_stock"


def _stock_helper(product: dict[str, object]) -> str:
    state = _stock_state(product)
    stock = _safe_int(product.get("stock"))
    variant_context = _variant_context_label(product)
    if state == "low_stock":
        return f"Restam {stock} unidades para envio imediato{variant_context}"
    if state == "out_of_stock":
        return f"Variante indisponível no momento{variant_context}, sujeita a reposição"
    if state == "backorder":
        return f"Variante disponível por encomenda{variant_context}, com prazo confirmado antes do pagamento"
    if stock <= 12:
        return f"{stock} unidades em pronta entrega{variant_context}"
    return f"Pronta entrega com envio rápido{variant_context}"


def _stock_label(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "low_stock":
        return "Estoque baixo"
    if state == "out_of_stock":
        return "Sem estoque"
    if state == "backorder":
        return "Sob encomenda"
    return "Em estoque"


def _badge(product: dict[str, object]) -> tuple[str | None, str]:
    state = _stock_state(product)
    status = str(product.get("status"))
    has_compare_price = bool(str(product.get("compare_price", "") or "").strip())
    selected_variant = _selected_variant_label(product)
    if status == "draft":
        return "Em breve", "neutral"
    if state == "low_stock":
        return f"Últimas unidades{selected_variant}", "warning"
    if state == "out_of_stock":
        return f"Reposição em acompanhamento{selected_variant}", "neutral"
    if state == "backorder":
        return "Sob encomenda", "neutral"
    if has_compare_price:
        return f"Oferta ativa{selected_variant}", "success"
    if product.get("is_featured"):
        return "Destaque da semana", "info"
    return f"Disponível agora{selected_variant}", "info"


def _price_helper(product: dict[str, object]) -> str:
    compare_price = str(product.get("compare_price", "") or "")
    state = _stock_state(product)
    variant_copy = _variant_copy(product)
    if state == "low_stock":
        return f"compra rápida{variant_copy}, com poucas unidades restantes para envio imediato"
    if compare_price:
        return f"oferta disponível{variant_copy}, com economia frente ao valor anterior e parcelamento em até 3x sem juros"
    if product.get("allow_backorder"):
        return f"parcelamento disponível com reserva imediata{variant_copy}"
    return f"parcelamento disponível{variant_copy} e disponibilidade pronta para compra"


def _purchase_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    category_label = str(product.get("category_label", "") or "").strip()
    selected_variant = _selected_variant_label(product)
    if state == "low_stock":
        return f"Poucas unidades disponíveis{selected_variant}, com saída rápida no catálogo atual."
    if state == "backorder":
        return f"Produto disponível por encomenda{selected_variant}, com confirmação de prazo antes de finalizar a compra."
    if state == "out_of_stock":
        return f"Produto indisponível no momento{selected_variant}. Ative o acompanhamento para saber quando houver reposição."
    if product.get("is_featured"):
        return f"Combinação em destaque{selected_variant}, com disponibilidade imediata e compra segura no storefront."
    if category_label:
        return f"Escolha sua combinação ideal{selected_variant} de {category_label.lower()} e avance para o checkout com segurança."
    return f"Selecione a variante desejada{selected_variant} e avance para o checkout com segurança."


def _variant_copy(product: dict[str, object]) -> str:
    selected = _selected_variant_label(product)
    if not selected:
        return ""
    return f" para {selected.lstrip(' · ')}"


def _variant_context_label(product: dict[str, object]) -> str:
    selected = _selected_variant_label(product)
    return selected if selected else ""


def _variant_emphasis_copy(product: dict[str, object]) -> str:
    selected = _selected_variant_label(product)
    if not selected:
        return "a variante padrão atual"
    return selected.lstrip(" · ")


def _catalog_card_subtitle(product: dict[str, object]) -> str:
    category = str(product.get("category_label", "") or "").strip()
    variant = _variant_emphasis_copy(product)
    if category and variant != "a variante padrão atual":
        return f"{category} · {variant}"
    return category or variant


def _catalog_card_meta(product: dict[str, object]) -> str:
    sku = str(product.get("sku", "") or "").strip()
    state = _stock_state(product)
    if state == "low_stock":
        context = "saída rápida"
    elif state == "backorder":
        context = "reserva disponível"
    elif state == "out_of_stock":
        context = "reposição em acompanhamento"
    elif str(product.get("compare_price", "") or "").strip():
        context = "oferta ativa"
    else:
        context = "compra pronta"
    if sku:
        return f"SKU {sku} · {context}"
    return context.capitalize()


def _catalog_card_variant_summary(product: dict[str, object]) -> str:
    variant = _variant_emphasis_copy(product)
    return f"Combinação em destaque: {variant}."


def _catalog_card_availability_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    variant = _variant_emphasis_copy(product)
    stock = _safe_int(product.get("stock"))
    if state == "low_stock":
        return f"{variant} com {stock} unidade(s) pronta(s) para envio."
    if state == "backorder":
        return f"{variant} disponível por encomenda."
    if state == "out_of_stock":
        return f"{variant} indisponível no momento."
    return f"{variant} pronta para compra imediata."


def _catalog_card_click_helper(product: dict[str, object]) -> str:
    state = _stock_state(product)
    variant = _variant_emphasis_copy(product)
    if state == "low_stock":
        return f"Abra o produto para confirmar {variant} antes de seguir para checkout."
    if state == "backorder":
        return f"Abra o produto para revisar {variant} e confirmar o prazo da reserva."
    if state == "out_of_stock":
        return f"Abra o produto para revisar {variant} e acompanhar a reposição."
    return f"Abra o produto para revisar {variant} e seguir para checkout com confiança."


def _catalog_card_curation_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    has_offer = bool(str(product.get("compare_price", "") or "").strip())
    is_featured = bool(product.get("is_featured"))
    quick_buy = state in {"in_stock", "low_stock"}
    if is_featured and has_offer and quick_buy:
        return "Destaque atual com oferta ativa e compra rápida disponível."
    if is_featured and quick_buy:
        return "Destaque atual da vitrine com compra rápida disponível."
    if has_offer and quick_buy:
        return "Oferta pronta para compra rápida nesta vitrine."
    if is_featured:
        return "Destaque atual da vitrine para explorar no detalhe."
    if quick_buy:
        return "Compra rápida disponível nesta combinação."
    if has_offer:
        return "Oferta ativa com revisão completa no detalhe do produto."
    return ""


def _catalog_initial_order_key(product: dict[str, object]) -> tuple[int, int, int, str, str]:
    status = str(product.get("status") or "").strip().lower()
    stock_state = str(product.get("stock_state") or _stock_state(product))
    status_rank = 1 if status == "draft" else 0
    stock_rank = {
        "low_stock": 0,
        "in_stock": 1,
        "backorder": 2,
        "out_of_stock": 3,
    }.get(stock_state, 4)
    offer_rank = 0 if bool(str(product.get("compare_price") or "").strip()) else 1
    featured_rank = 0 if bool(product.get("is_featured")) else 1
    return (
        status_rank,
        stock_rank,
        offer_rank,
        featured_rank,
        str(product.get("name") or "").lower(),
    )


def _catalog_card_price_helper(product: dict[str, object]) -> str:
    state = _stock_state(product)
    variant_copy = _variant_copy(product)
    compare_price = str(product.get("compare_price", "") or "").strip()
    if state == "low_stock":
        return f"economia pronta para checkout{variant_copy}, com poucas unidades restantes"
    if state == "backorder":
        return f"reserva confirmada{variant_copy}, com parcelamento disponível"
    if state == "out_of_stock":
        return f"acompanhe a reposição{variant_copy} e volte quando houver estoque"
    if compare_price:
        return f"oferta ativa{variant_copy}, com parcelamento em até 3x sem juros"
    return f"compra pronta{variant_copy}, com parcelamento e envio rápido"


def _catalog_to_pdp_continuity_note(product: dict[str, object]) -> str:
    variant = _variant_emphasis_copy(product)
    state = _stock_state(product)
    if variant == "a variante padrão atual":
        return "Os sinais comerciais exibidos no catálogo continuam alinhados com esta página do produto."
    if state == "backorder":
        return f"A combinação destacada no catálogo continua sendo {variant}, agora com o mesmo contexto de reserva e prazo nesta página."
    if state == "out_of_stock":
        return f"A combinação destacada no catálogo continua sendo {variant}, com o mesmo contexto de reposição mostrado aqui."
    if state == "low_stock":
        return f"A combinação destacada no catálogo continua sendo {variant}, com a mesma leitura de poucas unidades disponível nesta página."
    return f"A combinação destacada no catálogo continua sendo {variant}, com preço, mídia e disponibilidade alinhados aqui também."


def _pdp_subtitle(product: dict[str, object]) -> str:
    description = str(product.get("description", "") or "").strip()
    continuity_note = _catalog_to_pdp_continuity_note(product)
    if description:
        return f"{description} {continuity_note}"
    return continuity_note


def _pdp_short_description(product: dict[str, object]) -> str:
    base = str(product.get("description", "") or "").strip()
    continuity_note = _catalog_to_pdp_continuity_note(product)
    if base and continuity_note not in base:
        return f"{base} {continuity_note}"
    return continuity_note or base


def _pdp_purchase_note(product: dict[str, object]) -> str:
    purchase_note = _purchase_note(product)
    continuity_note = _catalog_to_pdp_continuity_note(product)
    return f"{purchase_note} {continuity_note}".strip()


def _effective_variant_summary(product: dict[str, object]) -> str:
    variant_label = _variant_emphasis_copy(product)
    sku = str(product.get("sku", "") or "").strip()
    if sku:
        return f"Variante em destaque agora: {variant_label} · SKU {sku}."
    return f"Variante em destaque agora: {variant_label}."


def _availability_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    variant_label = _variant_emphasis_copy(product)
    stock = _safe_int(product.get("stock"))
    if state == "low_stock":
        return f"A disponibilidade desta compra reflete {variant_label}, com {stock} unidade(s) pronta(s) para envio imediato."
    if state == "out_of_stock":
        return f"A disponibilidade desta compra reflete {variant_label}, que está sem estoque no momento."
    if state == "backorder":
        return f"A disponibilidade desta compra reflete {variant_label}, liberada por encomenda com prazo confirmado antes do pagamento."
    return f"A disponibilidade desta compra reflete {variant_label}, pronta para seguir ao checkout agora."


def _cta_helper(product: dict[str, object]) -> str:
    state = _stock_state(product)
    variant_label = _variant_emphasis_copy(product)
    if state == "out_of_stock":
        return f"Esta combinação ({variant_label}) não segue para checkout agora; o caminho mais seguro é revisar o catálogo ou acompanhar a reposição."
    if state == "backorder":
        return f"Esta combinação ({variant_label}) já pode seguir para checkout como reserva, com prazo confirmado antes do pagamento."
    if state == "low_stock":
        return f"Esta combinação ({variant_label}) já pode seguir para checkout agora, com poucas unidades restantes."
    return f"Esta combinação ({variant_label}) já pode seguir para checkout com o mesmo preço e disponibilidade exibidos nesta página."


def _checkout_continuity_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    variant = _variant_emphasis_copy(product)
    if state == "out_of_stock":
        return f"A combinação {variant} ainda não segue para checkout, então o próximo passo mais seguro é acompanhar a reposição ou voltar ao catálogo."
    if state == "backorder":
        return f"A combinação {variant} já pode seguir para checkout com o mesmo contexto de reserva e prazo mostrado aqui."
    if state == "low_stock":
        return f"A combinação {variant} já pode seguir para checkout agora, com o mesmo contexto de poucas unidades destacado nesta página."
    return f"A combinação {variant} já pode seguir para checkout com o mesmo preço e disponibilidade vistos aqui."

def _gallery_seed(product: dict[str, object]) -> str:
    brand = str(product.get("brand", "") or "").strip()
    category = str(product.get("category_label", "") or "").strip()
    return " ".join(part for part in [brand, category, str(product.get("name", ""))] if part).strip()


def _gallery_items(product: dict[str, object]) -> list[dict[str, object]]:
    slug = str(product["slug"])
    name = str(product["name"])
    seed = quote_plus(_gallery_seed(product) or slug)
    palette = [
        ("studio", "principal"),
        ("angle", "ângulo lateral"),
        ("detail", "detalhe do material"),
        ("lifestyle", "uso em contexto"),
    ]
    return [
        {
            "url": f"https://placehold.co/900x900/f8fafc/0f172a?text={seed}+{quote_plus(label)}",
            "alt": f"{name} · vista {alt_label}",
            "active": index == 0,
        }
        for index, (label, alt_label) in enumerate(palette)
    ]


def _variant_tokens(product: dict[str, object]) -> tuple[str, str]:
    variant = _effective_variant(product)
    return _color_token(variant), _size_token(variant)


def _image_relevance_score(image: dict[str, object], product: dict[str, object]) -> tuple[int, int, int, str]:
    color_token, size_token = _variant_tokens(product)
    haystack = " ".join(
        [
            str(image.get("image_url", "") or "").upper(),
            str(image.get("alt_text", "") or "").upper(),
        ]
    )
    color_match = 0 if color_token and color_token in haystack else 1
    size_match = 0 if size_token and size_token in haystack else 1
    primary_rank = 0 if image.get("is_primary") else 1
    return (
        color_match,
        size_match,
        primary_rank,
        f"{int(image.get('position') or 0):04d}-{str(image.get('image_url', ''))}",
    )


def _persisted_gallery_items(product: dict[str, object]) -> list[dict[str, object]]:
    images = list(product.get("images") or [])
    if not images:
        return []
    ordered = sorted(images, key=lambda item: _image_relevance_score(item, product))
    name = str(product["name"])
    return [
        {
            "url": str(image.get("image_url") or ""),
            "alt": str(image.get("alt_text") or f"{name} · imagem {index + 1}"),
            "active": index == 0,
        }
        for index, image in enumerate(ordered)
        if str(image.get("image_url") or "").strip()
    ]


def _variant_attribute(variant: dict[str, object], index_from_end: int) -> str:
    sku = str(variant.get("sku", "") or "").strip()
    if not sku:
        return ""
    parts = [part for part in sku.split("-") if part]
    if len(parts) < abs(index_from_end):
        return ""
    return str(parts[index_from_end]).strip().upper()


def _size_token(variant: dict[str, object]) -> str:
    token = _variant_attribute(variant, -1)
    if not token:
        return ""
    valid_sizes = {"PP", "P", "M", "G", "GG", "XG", "U"}
    if token in valid_sizes:
        return token
    if token.isdigit():
        return token
    return ""


def _color_token(variant: dict[str, object]) -> str:
    token = _variant_attribute(variant, -2)
    if not token:
        return ""
    if token.isalpha():
        return token
    return ""


def _color_option(token: str) -> dict[str, str]:
    palette = {
        "BLK": {"label": "Preto", "color": "#111827"},
        "WHT": {"label": "Branco", "color": "#e5e7eb"},
        "GRY": {"label": "Grafite", "color": "#6b7280"},
        "NAV": {"label": "Marinho", "color": "#1e3a8a"},
        "RED": {"label": "Vermelho", "color": "#b91c1c"},
        "GRN": {"label": "Verde", "color": "#166534"},
    }
    return palette.get(token, {"label": token.title(), "color": "#9ca3af"})


def _normalize_variant_selection_value(value: object) -> str:
    return str(value or "").strip().lower()


def _apply_variant_selection(product: dict[str, object], *, size: object = "", color: object = "", sku: object = "") -> dict[str, object]:
    variants = list(product.get("variants") or [])
    if not variants:
        return dict(product)

    requested_size = _normalize_variant_selection_value(size)
    requested_color = _normalize_variant_selection_value(color)
    requested_sku = str(sku or "").strip().upper()
    if not any([requested_size, requested_color, requested_sku]):
        return dict(product)

    matched_variant = None
    if requested_sku:
        matched_variant = next(
            (variant for variant in variants if str(variant.get("sku") or "").strip().upper() == requested_sku),
            None,
        )
    else:
        for variant in variants:
            variant_size = _normalize_variant_selection_value(_size_token(variant))
            variant_color = _normalize_variant_selection_value(_color_token(variant))
            if requested_size and variant_size != requested_size:
                continue
            if requested_color and variant_color != requested_color:
                continue
            matched_variant = variant
            break

    selected = dict(product)
    selected["selected_variant_size"] = requested_size
    selected["selected_variant_color"] = requested_color
    selected["selected_variant_sku_requested"] = requested_sku
    if matched_variant is None:
        selected["selected_variant_invalid"] = True
        return selected

    selected["selected_variant_sku"] = str(matched_variant.get("sku") or "").strip()
    selected["selected_variant_invalid"] = False
    return selected


def _effective_variant(product: dict[str, object]) -> dict[str, object]:
    variants = list(product.get("variants") or [])
    if variants:
        selected_sku = str(product.get("selected_variant_sku") or "").strip().upper()
        if selected_sku:
            for variant in variants:
                if str(variant.get("sku") or "").strip().upper() == selected_sku:
                    return dict(variant)
        for variant in variants:
            if variant.get("is_default"):
                return dict(variant)
        return dict(variants[0])
    return {
        "sku": product.get("sku", ""),
        "price": product.get("price", ""),
        "compare_price": product.get("compare_price", ""),
        "stock": product.get("stock", ""),
        "reserved_stock": product.get("reserved_stock", ""),
        "track_inventory": product.get("track_inventory", True),
        "allow_backorder": product.get("allow_backorder", False),
        "is_default": True,
    }


def _selected_variant_label(product: dict[str, object]) -> str:
    variant = _effective_variant(product)
    size = _size_token(variant)
    color = _color_token(variant)
    parts = []
    if color:
        parts.append(_color_option(color)["label"])
    if size:
        parts.append(size)
    if not parts:
        return ""
    return " · " + " · ".join(parts)


def _variant_groups(product: dict[str, object]) -> list[dict[str, object]]:
    real_variants = list(product.get("variants") or [])
    if real_variants:
        real_groups = _persisted_variant_groups(product, real_variants)
        if real_groups:
            return real_groups
    stock = _safe_int(product.get("stock"))
    status = _stock_state(product)
    category_label = str(product.get("category_label", "") or "").lower()
    uses_apparel_sizes = any(keyword in category_label for keyword in ["camiseta", "jaqueta", "moletom"])
    base_size = "M" if uses_apparel_sizes and stock > 0 else "P" if uses_apparel_sizes else "42" if stock > 0 else "40"
    size_options = (
        [
            {"value": "P", "label": "P", "selected": base_size == "P"},
            {"value": "M", "label": "M", "selected": base_size == "M"},
            {"value": "G", "label": "G", "selected": base_size == "G"},
            {"value": "GG", "label": "GG", "out_of_stock": status == "low_stock"},
        ]
        if uses_apparel_sizes
        else [
            {"value": "39", "label": "39", "selected": base_size == "39"},
            {"value": "40", "label": "40", "selected": base_size == "40"},
            {"value": "41", "label": "41", "selected": base_size == "41"},
            {"value": "42", "label": "42", "selected": base_size == "42"},
            {"value": "43", "label": "43", "out_of_stock": status in {"low_stock", "out_of_stock"}},
        ]
    )
    default_color = "preto" if product.get("is_featured") else "grafite"
    return [
        {
            "variant": "buttons",
            "name": "size",
            "label": "Tamanho disponível",
            "selected": base_size,
            "help_text": "Escolha o tamanho com disponibilidade imediata para envio.",
            "options": size_options,
        },
        {
            "variant": "swatches",
            "name": "color",
            "label": "Cor",
            "selected": default_color,
            "options": [
                {"value": "preto", "label": "Preto", "color": "#111827", "selected": default_color == "preto"},
                {"value": "grafite", "label": "Grafite", "color": "#6b7280", "selected": default_color == "grafite"},
                {"value": "offwhite", "label": "Off-white", "color": "#e5e7eb", "out_of_stock": status == "out_of_stock"},
            ],
        },
    ]


def _persisted_variant_groups(product: dict[str, object], variants: list[dict[str, object]]) -> list[dict[str, object]]:
    effective_variant = _effective_variant(product)
    size_values = []
    for variant in variants:
        size = _size_token(variant)
        if size and size not in size_values:
            size_values.append(size)
    color_values = []
    for variant in variants:
        color = _color_token(variant)
        if color and color not in color_values:
            color_values.append(color)

    groups: list[dict[str, object]] = []
    selected_size = _size_token(effective_variant)
    invalid_selection = bool(product.get("selected_variant_invalid"))
    explicit_selection = bool(product.get("selected_variant_sku"))
    if size_values:
        groups.append(
            {
                "variant": "buttons",
                "name": "size",
                "label": "Tamanho disponível",
                "selected": selected_size or size_values[0],
                "help_text": (
                    (
                        f"Preço e estoque exibidos refletem a variante selecionada {_variant_emphasis_copy(product)}."
                        if explicit_selection
                        else f"Preço e estoque exibidos refletem a variante padrão {_variant_emphasis_copy(product)}."
                    )
                    if not invalid_selection
                    else f"A combinação pedida não pôde ser aplicada; mantivemos {_variant_emphasis_copy(product)} como fallback seguro."
                ),
                "error_text": (
                    "A combinação escolhida não está disponível nesta página agora. Revise tamanho e cor."
                    if invalid_selection
                    else ""
                ),
                "invalid": invalid_selection,
                "options": [
                    {
                        "value": size,
                        "label": size,
                        "selected": size == (selected_size or size_values[0]),
                        "out_of_stock": not any(
                            _size_token(variant) == size
                            and (_safe_int(variant.get("stock")) > 0 or variant.get("allow_backorder"))
                            for variant in variants
                        ),
                    }
                    for size in size_values
                ],
            }
        )

    selected_color = _color_token(effective_variant)
    if color_values:
        groups.append(
            {
                "variant": "swatches",
                "name": "color",
                "label": "Cor",
                "selected": (selected_color or color_values[0]).lower(),
                "help_text": (
                    f"A mídia principal e os textos comerciais priorizam {_variant_emphasis_copy(product)}."
                    if not invalid_selection
                    else f"A mídia principal continua priorizando {_variant_emphasis_copy(product)} enquanto você revisa uma combinação válida."
                ),
                "options": [
                    {
                        "value": color.lower(),
                        "label": _color_option(color)["label"],
                        "color": _color_option(color)["color"],
                        "selected": color == (selected_color or color_values[0]),
                        "out_of_stock": not any(
                            _color_token(variant) == color
                            and (_safe_int(variant.get("stock")) > 0 or variant.get("allow_backorder"))
                            for variant in variants
                        ),
                    }
                    for color in color_values
                ],
            }
        )

    return groups


def _enrich_product(product: dict[str, object]) -> dict[str, object]:
    enriched = dict(product)
    effective_variant = _effective_variant(product)
    enriched.update(
        {
            "sku": str(effective_variant.get("sku") or product.get("sku") or ""),
            "price": str(effective_variant.get("price") or product.get("price") or ""),
            "compare_price": str(effective_variant.get("compare_price") or product.get("compare_price") or ""),
            "stock": str(effective_variant.get("stock") or product.get("stock") or ""),
            "reserved_stock": str(effective_variant.get("reserved_stock") or product.get("reserved_stock") or ""),
            "track_inventory": bool(effective_variant.get("track_inventory", product.get("track_inventory", True))),
            "allow_backorder": bool(effective_variant.get("allow_backorder", product.get("allow_backorder", False))),
        }
    )
    badge_label, badge_variant = _badge(enriched)
    gallery_items = _persisted_gallery_items(enriched) or _gallery_items(enriched)
    stock_state = _stock_state(enriched)
    enriched.update(
        {
            "stock_state": stock_state,
            "stock_label": _stock_label(enriched),
            "stock_helper": _stock_helper(enriched),
            "badge_label": badge_label,
            "badge_variant": badge_variant,
            "price_helper": _price_helper(enriched),
            "catalog_card_subtitle": _catalog_card_subtitle(enriched),
            "catalog_card_meta": _catalog_card_meta(enriched),
            "catalog_card_price_helper": _catalog_card_price_helper(enriched),
            "catalog_card_variant_summary": _catalog_card_variant_summary(enriched),
            "catalog_card_availability_note": _catalog_card_availability_note(enriched),
            "catalog_card_click_helper": _catalog_card_click_helper(enriched),
            "catalog_card_curation_note": _catalog_card_curation_note(enriched),
            "product_gallery_items": gallery_items,
            "main_image_url": gallery_items[0]["url"],
            "main_image_alt": gallery_items[0]["alt"],
            "variant_groups": _variant_groups(enriched),
            "product_subtitle": _pdp_subtitle(enriched),
            "short_description": _pdp_short_description(enriched),
            "purchase_note": f'{_pdp_purchase_note(enriched)} {_checkout_continuity_note(enriched)}'.strip(),
            "effective_variant_summary": _effective_variant_summary(enriched),
            "availability_note": _availability_note(enriched),
            "cta_helper": _cta_helper(enriched),
            "primary_action_label": (
                "Avise-me da reposição"
                if stock_state == "out_of_stock"
                else "Reservar e ir para checkout"
                if stock_state == "backorder"
                else "Ir para checkout"
            ),
            "primary_action_disabled": stock_state == "out_of_stock",
            "secondary_action_label": "Ver catálogo" if stock_state == "out_of_stock" else "Ir para checkout",
            "secondary_action_target": "catalog" if stock_state == "out_of_stock" else "checkout",
            "secondary_action_href": "#catalog" if stock_state == "out_of_stock" else "#checkout",
            "quantity": 1,
            "eyebrow": product["brand"],
            "effective_variant_label": _variant_emphasis_copy(enriched),
        }
    )
    return enriched


@dataclass
class StorefrontCatalogQueryService:
    orm_repository: ProductReadRepository
    fallback_repository: ProductReadRepository

    def using_persisted_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            return bool(self.orm_repository.list_products(tenant_id=tenant_id))
        except Exception:
            return False

    def list_products(self, *, tenant_id: int | None = None) -> list[dict[str, object]]:
        if not tenant_id:
            return []
        real_products = self.orm_repository.list_products(tenant_id=tenant_id)
        source = real_products or self.fallback_repository.list_products()
        enriched = [_enrich_product(product) for product in source]
        return sorted(enriched, key=_catalog_initial_order_key)

    def get_product(
        self,
        product_slug: str,
        *,
        tenant_id: int | None = None,
        size: object = "",
        color: object = "",
        sku: object = "",
    ) -> dict[str, object]:
        if not tenant_id:
            return {}

        real_product = self.orm_repository.get_product(product_slug, tenant_id=tenant_id)
        if real_product:
            return _enrich_product(_apply_variant_selection(real_product, size=size, color=color, sku=sku))

        fallback_product = self.fallback_repository.get_product(product_slug, tenant_id=tenant_id)
        if fallback_product:
            return _enrich_product(_apply_variant_selection(fallback_product, size=size, color=color, sku=sku))

        return {}


storefront_catalog_queries = StorefrontCatalogQueryService(
    orm_repository=DjangoOrmProductRepository(),
    fallback_repository=FallbackProductRepository(),
)
