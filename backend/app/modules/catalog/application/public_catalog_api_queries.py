from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 50


def _int(value: object, *, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(parsed, minimum)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def _money(value: object) -> str:
    try:
        amount = Decimal(str(value or "0")).quantize(Decimal("0.01"))
    except Exception:
        amount = Decimal("0.00")
    return str(amount)


def _stock_state(variant) -> str:
    stock = int(getattr(variant, "stock", 0) or 0)
    if stock <= 0:
        return "backorder" if bool(getattr(variant, "allow_backorder", False)) else "out_of_stock"
    if stock <= 5:
        return "low_stock"
    return "in_stock"


def _default_variant(product):
    variants = list(getattr(product, "variants").all())
    if not variants:
        return None
    for variant in variants:
        if bool(getattr(variant, "is_default", False)):
            return variant
    return variants[0]


def _primary_image(product) -> dict[str, str] | None:
    images = list(getattr(product, "images").all()) if hasattr(product, "images") else []
    if not images:
        return None
    image = images[0]
    return {
        "url": str(getattr(image, "image_url", "") or ""),
        "alt": str(getattr(image, "alt_text", "") or ""),
    }


def _serialize_image(image) -> dict[str, str]:
    return {
        "url": str(getattr(image, "image_url", "") or ""),
        "alt": str(getattr(image, "alt_text", "") or ""),
    }


def _serialize_variant(variant) -> dict[str, object]:
    return {
        "sku": str(getattr(variant, "sku", "") or ""),
        "price": _money(getattr(variant, "price", "0")),
        "compare_price": _money(getattr(variant, "compare_price", None))
        if getattr(variant, "compare_price", None) is not None
        else "",
        "availability": _stock_state(variant),
        "is_default": bool(getattr(variant, "is_default", False)),
    }


def _serialize_product(product) -> dict[str, object]:
    variant = _default_variant(product)
    image = _primary_image(product)
    return {
        "id": getattr(product, "id", None),
        "slug": str(getattr(product, "slug", "") or ""),
        "name": str(getattr(product, "name", "") or ""),
        "brand": str(getattr(product, "brand_name", "") or ""),
        "category": str(getattr(product, "category_label", "") or ""),
        "is_featured": bool(getattr(product, "is_featured", False)),
        "status": str(getattr(product, "status", "") or ""),
        "price": _money(getattr(variant, "price", "0") if variant else "0"),
        "compare_price": _money(getattr(variant, "compare_price", None)) if variant and getattr(variant, "compare_price", None) is not None else "",
        "availability": _stock_state(variant) if variant else "unavailable",
        "primary_image": image,
        "updated_at": getattr(product, "updated_at", None).isoformat() if getattr(product, "updated_at", None) else "",
    }


def _serialize_product_detail(product) -> dict[str, object]:
    payload = _serialize_product(product)
    images = list(getattr(product, "images").all()) if hasattr(product, "images") else []
    variants = list(getattr(product, "variants").all())
    payload.update(
        {
            "description": str(getattr(product, "description", "") or ""),
            "images": [_serialize_image(image) for image in images],
            "variants": [_serialize_variant(variant) for variant in variants],
        }
    )
    return payload


@dataclass
class PublicCatalogApiQueryService:
    def list_products(
        self,
        *,
        tenant_id: int | str | None,
        page: object = 1,
        page_size: object = DEFAULT_PAGE_SIZE,
    ) -> dict[str, object]:
        if not tenant_id:
            return {
                "result": "public-catalog-tenant-required",
                "count": 0,
                "page": 1,
                "page_size": DEFAULT_PAGE_SIZE,
                "results": [],
            }

        from app.modules.catalog.models import Product

        current_page = _int(page, default=1, minimum=1)
        current_page_size = _int(page_size, default=DEFAULT_PAGE_SIZE, minimum=1, maximum=MAX_PAGE_SIZE)
        queryset = (
            Product.objects.filter(
                tenant_id=tenant_id,
                status=Product.Status.ACTIVE,
                is_active=True,
            )
            .prefetch_related("variants", "images")
            .order_by("-is_featured", "name", "id")
        )
        total_count = queryset.count()
        offset = (current_page - 1) * current_page_size
        products = list(queryset[offset : offset + current_page_size])
        return {
            "result": "public-catalog-products-listed",
            "count": total_count,
            "page": current_page,
            "page_size": current_page_size,
            "results": [_serialize_product(product) for product in products],
        }

    def get_product_detail(
        self,
        *,
        tenant_id: int | str | None,
        slug: str,
    ) -> dict[str, object]:
        normalized_slug = str(slug or "").strip()
        if not tenant_id or not normalized_slug:
            return {
                "result": "public-catalog-product-not-found",
                "product": None,
            }

        from app.modules.catalog.models import Product

        product = (
            Product.objects.filter(
                tenant_id=tenant_id,
                slug=normalized_slug,
                status=Product.Status.ACTIVE,
                is_active=True,
            )
            .prefetch_related("variants", "images")
            .first()
        )
        if not product:
            return {
                "result": "public-catalog-product-not-found",
                "product": None,
            }
        return {
            "result": "public-catalog-product-retrieved",
            "product": _serialize_product_detail(product),
        }


public_catalog_api_queries = PublicCatalogApiQueryService()
