from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote_plus

from app.modules.catalog.application.admin_product_queries import (
    FallbackProductRepository,
    DjangoOrmProductRepository,
    ProductReadRepository,
    admin_product_queries,
)
from app.modules.catalog.application.storefront_conversion_insights import storefront_conversion_insights


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
    if state == "low_stock":
        return "Últimas unidades"
    if state == "out_of_stock":
        return "Indisponível no momento"
    if state == "backorder":
        return "Sob encomenda"
    return "Pronta entrega"


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
    if status == "draft":
        return "Em breve", "neutral"
    if state == "low_stock":
        return "Últimas unidades", "warning"
    if state == "out_of_stock":
        return "Indisponível", "neutral"
    if state == "backorder":
        return "Sob encomenda", "neutral"
    if has_compare_price:
        return "Oferta", "success"
    if product.get("is_featured"):
        return "Destaque", "info"
    return None, "neutral"


def _price_helper(product: dict[str, object]) -> str:
    compare_price = str(product.get("compare_price", "") or "")
    state = _stock_state(product)
    if state == "low_stock":
        return "Poucas unidades para envio imediato"
    if compare_price:
        return "Oferta ativa com parcelamento disponível"
    if product.get("allow_backorder"):
        return "Reserva com prazo confirmado antes do pagamento"
    return "Parcelamento disponível"


def _purchase_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "low_stock":
        return "Poucas unidades disponíveis para envio imediato."
    if state == "backorder":
        return "Produto disponível por encomenda, com prazo confirmado antes de finalizar."
    if state == "out_of_stock":
        return "Produto indisponível no momento."
    return "Selecione a opção desejada e avance com segurança."


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
    return category


def _catalog_card_meta(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "low_stock":
        return "Últimas unidades"
    if state == "backorder":
        return "Reserva disponível"
    if state == "out_of_stock":
        return "Reposição em acompanhamento"
    if str(product.get("compare_price", "") or "").strip():
        return "Oferta ativa"
    return "Compra pronta"


def _catalog_card_variant_summary(product: dict[str, object]) -> str:
    return ""


def _catalog_card_availability_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "low_stock":
        return "Últimas unidades para envio imediato"
    if state == "backorder":
        return "Sob encomenda"
    if state == "out_of_stock":
        return "Indisponível no momento"
    return "Pronta entrega"


def _catalog_card_click_helper(product: dict[str, object]) -> str:
    return ""


def _catalog_card_curation_note(product: dict[str, object]) -> str:
    return ""


def _catalog_card_decision_signal(product: dict[str, object]) -> str:
    state = _stock_state(product)
    has_offer = bool(str(product.get("compare_price", "") or "").strip())
    is_featured = bool(product.get("is_featured"))
    if state == "out_of_stock":
        return "acompanhar_reposicao"
    if state == "backorder":
        return "reserva_planejada"
    if state == "low_stock" and has_offer:
        return "decisao_rapida_com_oferta"
    if state == "low_stock":
        return "decisao_rapida"
    if has_offer and is_featured:
        return "oferta_editorial"
    if has_offer:
        return "oferta_para_comparar"
    if is_featured:
        return "destaque_editorial"
    return "compra_pronta"


def _discovery_rank_components(product: dict[str, object]) -> dict[str, int]:
    status = str(product.get("status") or "").strip().lower()
    stock_state = str(product.get("stock_state") or _stock_state(product))
    decision_signal = str(product.get("catalog_card_decision_signal") or _catalog_card_decision_signal(product))
    return {
        "status": 0 if status == "draft" else 1000,
        "stock": {
            "low_stock": 400,
            "in_stock": 320,
            "backorder": 180,
            "out_of_stock": 20,
        }.get(stock_state, 0),
        "offer": 60 if bool(str(product.get("compare_price") or "").strip()) else 0,
        "featured": 40 if bool(product.get("is_featured")) else 0,
        "decision_signal": {
            "decisao_rapida_com_oferta": 40,
            "decisao_rapida": 35,
            "oferta_editorial": 30,
            "oferta_para_comparar": 25,
            "destaque_editorial": 20,
            "compra_pronta": 15,
            "reserva_planejada": 10,
            "acompanhar_reposicao": 0,
        }.get(decision_signal, 0),
    }


def _discovery_rank_score(product: dict[str, object]) -> int:
    return sum(_discovery_rank_components(product).values())


def _discovery_rank_reason(product: dict[str, object]) -> str:
    stock_state = str(product.get("stock_state") or _stock_state(product))
    has_offer = bool(str(product.get("compare_price") or "").strip())
    is_featured = bool(product.get("is_featured"))
    decision_signal = str(product.get("catalog_card_decision_signal") or _catalog_card_decision_signal(product))

    if stock_state == "out_of_stock":
        return "reposição acompanhável, sem prioridade de compra imediata"
    if stock_state == "backorder":
        return "reserva planejada com disponibilidade futura"
    if decision_signal == "decisao_rapida_com_oferta":
        return "poucas unidades com oferta ativa"
    if decision_signal == "decisao_rapida":
        return "poucas unidades prontas para decisão rápida"
    if has_offer and is_featured:
        return "oferta ativa com destaque editorial"
    if has_offer:
        return "oferta ativa em produto disponível"
    if is_featured:
        return "destaque editorial disponível"
    return "produto disponível para compra pronta"


def _catalog_initial_order_key(product: dict[str, object]) -> tuple[int, int, int, int, str]:
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


def _discovery_rank_order_key(product: dict[str, object]) -> tuple[int, str]:
    return (
        -int(product.get("discovery_rank_score") or _discovery_rank_score(product)),
        str(product.get("name") or "").lower(),
    )


def _catalog_card_price_helper(product: dict[str, object]) -> str:
    state = _stock_state(product)
    compare_price = str(product.get("compare_price", "") or "").strip()
    if state == "low_stock":
        return "Últimas unidades"
    if state == "backorder":
        return "Reserva disponível"
    if state == "out_of_stock":
        return "Acompanhe a reposição"
    if compare_price:
        return "Oferta ativa"
    return "Pronta entrega"


def _catalog_to_pdp_continuity_note(product: dict[str, object]) -> str:
    return ""


def _pdp_commercial_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    compare_price = bool(str(product.get("compare_price", "") or "").strip())
    if state == "low_stock":
        return "Poucas unidades disponíveis para envio imediato."
    if state == "backorder":
        return "Disponível por encomenda, com prazo confirmado antes do pagamento."
    if state == "out_of_stock":
        return "Indisponível no momento."
    if compare_price:
        return "Oferta ativa por tempo limitado na loja."
    if product.get("is_featured"):
        return "Destaque atual da loja."
    return "Disponível para compra."


def _pdp_subtitle(product: dict[str, object]) -> str:
    description = str(product.get("description", "") or "").strip()
    commercial_note = _pdp_commercial_note(product)
    if description:
        return description
    return commercial_note.strip()


def _pdp_short_description(product: dict[str, object]) -> str:
    base = str(product.get("description", "") or "").strip()
    return base


def _pdp_purchase_note(product: dict[str, object]) -> str:
    return _purchase_note(product)


def _effective_variant_summary(product: dict[str, object]) -> str:
    return ""


def _availability_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "low_stock":
        return "Últimas unidades disponíveis para envio imediato."
    if state == "out_of_stock":
        return "Este produto está sem estoque no momento."
    if state == "backorder":
        return "Produto liberado por encomenda, com prazo confirmado antes do pagamento."
    return "Disponível para compra."


def _cta_helper(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "out_of_stock":
        return "Este item não segue para checkout agora."
    if state == "backorder":
        return "A reserva segue para checkout com prazo confirmado antes do pagamento."
    if state == "low_stock":
        return "Preço e disponibilidade serão preservados no checkout."
    return "Preço e disponibilidade serão preservados no checkout."


def _checkout_continuity_note(product: dict[str, object]) -> str:
    return ""


def _pdp_decision_checks(product: dict[str, object]) -> list[dict[str, str]]:
    state = _stock_state(product)
    if state == "out_of_stock":
        return [
            {
                "title": "Preço visível",
                "description": "Preço mantido visível para comparação.",
            },
            {
                "title": "Sem checkout agora",
                "description": "Produto indisponível para compra imediata.",
            },
            {
                "title": "Próximo passo seguro",
                "description": "Volte à loja para escolher outro item.",
            },
        ]
    return [
        {
            "title": "Preço garantido",
            "description": "O checkout usa o preço exibido aqui.",
        },
        {
            "title": "Disponibilidade atual",
            "description": "A disponibilidade acompanha a opção selecionada.",
        },
        {
            "title": "Checkout seguro",
            "description": "Compra protegida até a confirmação do pagamento.",
        },
    ]

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
    decision_signal = _catalog_card_decision_signal(enriched)
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
            "catalog_card_decision_signal": decision_signal,
            "product_gallery_items": gallery_items,
            "main_image_url": gallery_items[0]["url"],
            "main_image_alt": gallery_items[0]["alt"],
            "variant_groups": _variant_groups(enriched),
            "product_subtitle": _pdp_subtitle(enriched),
            "short_description": _pdp_short_description(enriched),
            "purchase_note": _pdp_purchase_note(enriched),
            "effective_variant_summary": _effective_variant_summary(enriched),
            "availability_note": _availability_note(enriched),
            "cta_helper": _cta_helper(enriched),
            "pdp_decision_checks": _pdp_decision_checks(enriched),
            "primary_action_label": (
                "Avise-me da reposição"
                if stock_state == "out_of_stock"
                else "Reservar e ir para checkout"
                if stock_state == "backorder"
                else "Ir para checkout"
            ),
            "primary_action_disabled": stock_state == "out_of_stock",
            "secondary_action_label": "Ver loja" if stock_state == "out_of_stock" else "Ir para checkout",
            "secondary_action_target": "catalog" if stock_state == "out_of_stock" else "checkout",
            "secondary_action_href": "#catalog" if stock_state == "out_of_stock" else "#checkout",
            "quantity": 1,
            "eyebrow": product["brand"],
            "effective_variant_label": _variant_emphasis_copy(enriched),
        }
    )
    enriched.update(
        {
            "discovery_rank_components": _discovery_rank_components(enriched),
            "discovery_rank_score": _discovery_rank_score(enriched),
            "discovery_rank_reason": _discovery_rank_reason(enriched),
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
        ranked = sorted(enriched, key=_discovery_rank_order_key)
        return storefront_conversion_insights.apply_product_card_priority_experiment(
            tenant_id=tenant_id,
            products=ranked,
        )

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
