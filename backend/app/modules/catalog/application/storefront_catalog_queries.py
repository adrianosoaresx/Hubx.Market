from __future__ import annotations

from dataclasses import dataclass

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
    if state == "low_stock":
        return f"Restam {stock} unidades"
    if state == "out_of_stock":
        return "Indisponível no momento"
    if state == "backorder":
        return "Envio sob encomenda"
    return "Pronta entrega"


def _badge(product: dict[str, object]) -> tuple[str | None, str]:
    state = _stock_state(product)
    status = str(product.get("status"))
    if status == "draft":
        return "Em breve", "neutral"
    if state == "low_stock":
        return "Últimas unidades", "warning"
    if state == "backorder":
        return "Sob encomenda", "neutral"
    return "Destaque", "info"


def _price_helper(product: dict[str, object]) -> str:
    compare_price = str(product.get("compare_price", "") or "")
    if compare_price:
        return "ou 3x sem juros"
    if product.get("allow_backorder"):
        return "parcelamento disponível e envio sob encomenda"
    return "parcelamento disponível"


def _purchase_note(product: dict[str, object]) -> str:
    state = _stock_state(product)
    if state == "low_stock":
        return "Poucas unidades disponíveis para compra imediata."
    if state == "backorder":
        return "Produto disponível por encomenda, com prazo informado na entrega."
    if state == "out_of_stock":
        return "Produto indisponível no momento. Cadastre-se para acompanhar reposição."
    if product.get("is_featured"):
        return "Produto em destaque com disponibilidade imediata no storefront."
    return "Selecione a variante desejada e avance para o checkout."


def _gallery_items(product: dict[str, object]) -> list[dict[str, object]]:
    slug = str(product["slug"])
    name = str(product["name"])
    return [
        {"url": f"https://placehold.co/900x900?text={slug}-1", "alt": f"{name} imagem 1", "active": True},
        {"url": f"https://placehold.co/900x900?text={slug}-2", "alt": f"{name} imagem 2"},
        {"url": f"https://placehold.co/900x900?text={slug}-3", "alt": f"{name} imagem 3"},
        {"url": f"https://placehold.co/900x900?text={slug}-4", "alt": f"{name} imagem 4"},
    ]


def _variant_groups(product: dict[str, object]) -> list[dict[str, object]]:
    stock = _safe_int(product.get("stock"))
    main_size = "42" if stock > 0 else "40"
    return [
        {
            "variant": "buttons",
            "name": "size",
            "label": "Tamanho",
            "selected": main_size,
            "help_text": "Selecione a grade desejada.",
            "options": [
                {"value": "40", "label": "40", "selected": main_size == "40"},
                {"value": "41", "label": "41", "selected": main_size == "41"},
                {"value": "42", "label": "42", "selected": main_size == "42"},
                {"value": "43", "label": "43", "out_of_stock": stock <= 5},
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
                {"value": "azul", "label": "Azul", "color": "#3b82f6", "out_of_stock": stock <= 0},
            ],
        },
    ]


def _enrich_product(product: dict[str, object]) -> dict[str, object]:
    enriched = dict(product)
    badge_label, badge_variant = _badge(product)
    gallery_items = _gallery_items(product)
    enriched.update(
        {
            "stock_state": _stock_state(product),
            "stock_helper": _stock_helper(product),
            "badge_label": badge_label,
            "badge_variant": badge_variant,
            "price_helper": _price_helper(product),
            "product_gallery_items": gallery_items,
            "main_image_url": gallery_items[0]["url"],
            "main_image_alt": gallery_items[0]["alt"],
            "variant_groups": _variant_groups(product),
            "short_description": str(product.get("description", "") or ""),
            "purchase_note": _purchase_note(product),
            "primary_action_label": "Adicionar ao carrinho",
            "secondary_action_label": "Comprar agora",
            "secondary_action_href": "#checkout",
            "quantity": 1,
            "eyebrow": product["brand"],
        }
    )
    return enriched


@dataclass
class StorefrontCatalogQueryService:
    orm_repository: ProductReadRepository
    fallback_repository: ProductReadRepository

    def using_persisted_source(self) -> bool:
        try:
            return bool(self.orm_repository.list_products())
        except Exception:
            return False

    def list_products(self) -> list[dict[str, object]]:
        real_products = self.orm_repository.list_products()
        source = real_products or self.fallback_repository.list_products()
        return [_enrich_product(product) for product in source]

    def get_product(self, product_slug: str) -> dict[str, object]:
        real_product = self.orm_repository.get_product(product_slug)
        if real_product:
            return _enrich_product(real_product)

        fallback_product = self.fallback_repository.get_product(product_slug)
        if fallback_product:
            return _enrich_product(fallback_product)

        return _enrich_product(admin_product_queries.get_product(product_slug))


storefront_catalog_queries = StorefrontCatalogQueryService(
    orm_repository=DjangoOrmProductRepository(),
    fallback_repository=FallbackProductRepository(),
)
