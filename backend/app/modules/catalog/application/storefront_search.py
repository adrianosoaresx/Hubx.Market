from __future__ import annotations

import unicodedata


SEARCHABLE_STOREFRONT_PRODUCT_FIELDS = (
    "name",
    "brand",
    "sku",
    "category_label",
    "description",
    "short_description",
    "catalog_card_subtitle",
    "catalog_card_meta",
    "catalog_card_variant_summary",
    "catalog_card_curation_note",
    "catalog_card_decision_signal",
    "effective_variant_label",
)


def normalize_storefront_search_text(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    without_diacritics = "".join(character for character in normalized if not unicodedata.combining(character))
    return " ".join(without_diacritics.split())


def storefront_search_terms(query: object) -> list[str]:
    normalized_query = normalize_storefront_search_text(query)
    return [term for term in normalized_query.split(" ") if term]


def storefront_product_search_text(product: dict[str, object]) -> str:
    return normalize_storefront_search_text(
        " ".join(str(product.get(field) or "") for field in SEARCHABLE_STOREFRONT_PRODUCT_FIELDS)
    )


def storefront_product_matches_search(product: dict[str, object], query: object) -> bool:
    terms = storefront_search_terms(query)
    if not terms:
        return True
    search_text = storefront_product_search_text(product)
    return all(term in search_text for term in terms)
