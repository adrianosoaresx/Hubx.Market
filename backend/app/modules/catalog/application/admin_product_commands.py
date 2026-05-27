from __future__ import annotations

from dataclasses import dataclass

from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.catalog.models import Product


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


@dataclass
class AdminProductCommandService:
    def update_product_visibility(
        self,
        *,
        tenant_id: int | str | None,
        product_id: int | str | None,
        status: object,
        is_active: object,
        is_featured: object | None = None,
        actor_label: object = "",
    ) -> dict[str, object]:
        if not tenant_id:
            return {"result": "product-visibility-tenant-required", "errors": {"tenant_id": "required"}}
        if not product_id:
            return {"result": "product-visibility-product-required", "errors": {"product_id": "required"}}

        normalized_status = _string(status, limit=16)
        if normalized_status not in Product.Status.values:
            return {"result": "product-visibility-invalid", "errors": {"status": "invalid"}}

        product = Product.objects.filter(pk=product_id, tenant_id=tenant_id).first()
        if product is None:
            return {"result": "product-visibility-not-found", "errors": {"product_id": "not-found"}}

        previous_status = product.status
        previous_is_active = product.is_active
        previous_is_featured = product.is_featured
        product.status = normalized_status
        product.is_active = bool(is_active)
        if is_featured is not None:
            product.is_featured = bool(is_featured)
        product.save(update_fields=("status", "is_active", "is_featured", "updated_at"))

        audit_log_commands.record_event(
            tenant_id=tenant_id,
            module="catalog",
            action="product.visibility_updated",
            entity_type="Product",
            entity_id=str(product.id),
            actor_label=_string(actor_label),
            summary=f"Visibilidade do produto {product.slug} atualizada",
            metadata={
                "product_id": product.id,
                "slug": product.slug,
                "previous_status": previous_status,
                "status": product.status,
                "previous_is_active": previous_is_active,
                "is_active": product.is_active,
                "previous_is_featured": previous_is_featured,
                "is_featured": product.is_featured,
            },
        )
        return {
            "result": "product-visibility-updated",
            "product": {
                "id": product.id,
                "tenant_id": product.tenant_id,
                "slug": product.slug,
                "status": product.status,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
            },
        }


admin_product_commands = AdminProductCommandService()
