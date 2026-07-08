from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils.text import slugify

from app.modules.accounts.application.admin_permissions import PERMISSION_CATALOG_MANAGE, admin_permissions
from app.modules.audit.application.audit_log_commands import audit_log_commands
from app.modules.catalog.models import Product, ProductVariant
from app.modules.subscriptions.application.commercial_terms import get_tenant_commercial_terms
from app.modules.tenants.models import Tenant


def _string(value: object, *, limit: int = 180) -> str:
    return str(value or "").strip()[:limit]


def _slug(value: object, *, fallback: object = "") -> str:
    raw_slug = _string(value, limit=255) or _string(fallback, limit=255)
    return slugify(raw_slug)[:255]


def _checkbox(payload: dict[str, object], key: str) -> bool:
    if key not in payload:
        return False
    return str(payload.get(key) or "").strip().lower() in {"1", "true", "on", "yes"}


def _checkbox_default(payload: dict[str, object], key: str, *, default: bool) -> bool:
    if key not in payload:
        return default
    return _checkbox(payload, key)


def _option_values(value: object) -> tuple[dict[str, str], str]:
    raw = str(value or "").strip()
    if not raw:
        return {}, ""
    options: dict[str, str] = {}
    for chunk in raw.replace(",", "\n").splitlines():
        line = chunk.strip()
        if not line:
            continue
        if "=" not in line and ":" not in line:
            return {}, "Use o formato Nome=Valor, uma opção por linha."
        separator = "=" if "=" in line else ":"
        key, option_value = [part.strip() for part in line.split(separator, 1)]
        if not key or not option_value:
            return {}, "Use o formato Nome=Valor, uma opção por linha."
        options[_string(key, limit=60)] = _string(option_value, limit=120)
    return options, ""


def _decimal_value(value: object, *, field: str, required: bool = False) -> tuple[Decimal | None, str]:
    normalized = str(value or "").strip().replace(",", ".")
    if not normalized:
        if required:
            return None, "Informe um valor."
        return None, ""
    try:
        parsed = Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None, "Informe um número válido."
    if parsed < 0:
        return None, "Informe um valor maior ou igual a zero."
    return parsed, ""


def _integer_value(value: object, *, required: bool = False) -> tuple[int | None, str]:
    normalized = str(value or "").strip()
    if not normalized:
        if required:
            return None, "Informe um valor."
        return 0, ""
    try:
        parsed = int(normalized)
    except (TypeError, ValueError):
        return None, "Informe um número inteiro válido."
    if parsed < 0:
        return None, "Informe um valor maior ou igual a zero."
    return parsed, ""


def _default_variant(product: Product) -> ProductVariant | None:
    variant = product.variants.filter(is_default=True).order_by("id").first()
    if variant is not None:
        return variant
    return product.variants.order_by("id").first()


COUNTED_PRODUCT_STATUSES = (Product.Status.ACTIVE, Product.Status.DRAFT)


@dataclass
class AdminProductCommandService:
    def create_product(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        permission_result = self._check_manage_permission(actor_role=actor_role)
        if permission_result:
            return permission_result
        tenant = self._tenant(tenant_id)
        if tenant is None:
            return {"result": "product-tenant-required", "errors": {"__all__": "Tenant obrigatório para criar produto."}}

        values, variant_values, errors = self._validated_values(tenant_id=tenant.id, payload=payload)
        if errors:
            return {"result": "product-invalid", "errors": errors}
        limit_error = self._product_limit_error(
            tenant_id=tenant.id,
            target_status=str(values.get("status") or ""),
        )
        if limit_error:
            return {"result": "product-plan-limit-reached", "errors": {"__all__": limit_error}}

        with transaction.atomic():
            product = Product.objects.create(tenant=tenant, **values)
            ProductVariant.objects.create(product=product, is_default=True, **variant_values)

        self._record_event(
            product=product,
            action="product.created",
            summary=f"Produto {product.slug} criado",
            actor_label=actor_label,
            metadata={"slug": product.slug, "status": product.status},
        )
        return {"result": "product-created", "product": {"id": product.id, "slug": product.slug}}

    def update_product(
        self,
        *,
        tenant_id: int | str | None,
        product_slug: str | None,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        permission_result = self._check_manage_permission(actor_role=actor_role)
        if permission_result:
            return permission_result
        if not tenant_id or not product_slug:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}
        product = Product.objects.filter(tenant_id=tenant_id, slug=product_slug).first()
        if product is None:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}

        variant = _default_variant(product)
        values, variant_values, errors = self._validated_values(
            tenant_id=tenant_id,
            payload=payload,
            current_product_id=product.id,
            current_variant_id=getattr(variant, "id", None),
        )
        if errors:
            return {"result": "product-invalid", "errors": errors}
        limit_error = self._product_limit_error(
            tenant_id=tenant_id,
            target_status=str(values.get("status") or ""),
            current_product_id=product.id,
            current_status=product.status,
        )
        if limit_error:
            return {"result": "product-plan-limit-reached", "errors": {"__all__": limit_error}}

        previous_slug = product.slug
        previous_status = product.status
        with transaction.atomic():
            for field_name, value in values.items():
                setattr(product, field_name, value)
            product.save(update_fields=[*values.keys(), "updated_at"])

            if variant is None:
                variant = ProductVariant.objects.create(product=product, is_default=True, **variant_values)
            else:
                for field_name, value in variant_values.items():
                    setattr(variant, field_name, value)
                variant.is_default = True
                variant.save(update_fields=[*variant_values.keys(), "is_default", "updated_at"])
            ProductVariant.objects.filter(product=product).exclude(pk=variant.pk).update(is_default=False)

        self._record_event(
            product=product,
            action="product.updated",
            summary=f"Produto {product.slug} atualizado",
            actor_label=actor_label,
            metadata={
                "previous_slug": previous_slug,
                "slug": product.slug,
                "previous_status": previous_status,
                "status": product.status,
                "variant_id": variant.id,
                "sku": variant.sku,
            },
        )
        return {"result": "product-updated", "product": {"id": product.id, "slug": product.slug}}

    def deactivate_product(
        self,
        *,
        tenant_id: int | str | None,
        product_slug: str | None,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        permission_result = self._check_manage_permission(actor_role=actor_role)
        if permission_result:
            return permission_result
        if not tenant_id or not product_slug:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}
        product = Product.objects.filter(tenant_id=tenant_id, slug=product_slug).first()
        if product is None:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}

        previous_status = product.status
        product.status = Product.Status.INACTIVE
        product.is_active = False
        product.is_featured = False
        product.save(update_fields=("status", "is_active", "is_featured", "updated_at"))

        self._record_event(
            product=product,
            action="product.deactivated",
            summary=f"Produto {product.slug} desativado sem exclusão física",
            actor_label=actor_label,
            metadata={
                "slug": product.slug,
                "previous_status": previous_status,
                "status": product.status,
                "is_active": product.is_active,
                "is_featured": product.is_featured,
            },
        )
        return {"result": "product-deactivated", "product": {"id": product.id, "slug": product.slug}}

    def create_product_variant(
        self,
        *,
        tenant_id: int | str | None,
        product_slug: str | None,
        payload: dict[str, object],
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        permission_result = self._check_manage_permission(actor_role=actor_role)
        if permission_result:
            return permission_result
        product = self._product_for_tenant(tenant_id=tenant_id, product_slug=product_slug)
        if product is None:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}

        variant_values, errors = self._validated_variant_values(
            tenant_id=tenant_id,
            payload=payload,
        )
        if errors:
            return {"result": "product-variant-invalid", "errors": errors}

        with transaction.atomic():
            if variant_values["is_default"]:
                ProductVariant.objects.filter(product=product).update(is_default=False)
            if not variant_values.get("position"):
                variant_values["position"] = ProductVariant.objects.filter(product=product).count()
            variant = ProductVariant.objects.create(product=product, **variant_values)
            if not ProductVariant.objects.filter(product=product, is_default=True).exists():
                variant.is_default = True
                variant.save(update_fields=["is_default", "updated_at"])

        self._record_event(
            product=product,
            action="product.variant_created",
            summary=f"Variante {variant.sku} criada para {product.slug}",
            actor_label=actor_label,
            metadata={
                "product_id": product.id,
                "slug": product.slug,
                "variant_id": variant.id,
                "sku": variant.sku,
                "is_default": variant.is_default,
                "is_active": variant.is_active,
                "option_values": dict(variant.option_values or {}),
            },
        )
        return {
            "result": "product-variant-created",
            "product": {"id": product.id, "slug": product.slug},
            "variant": {"id": variant.id, "sku": variant.sku},
        }

    def set_default_variant(
        self,
        *,
        tenant_id: int | str | None,
        product_slug: str | None,
        variant_id: int | str | None,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        permission_result = self._check_manage_permission(actor_role=actor_role)
        if permission_result:
            return permission_result
        product = self._product_for_tenant(tenant_id=tenant_id, product_slug=product_slug)
        if product is None:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}
        variant = self._variant_for_product(product=product, variant_id=variant_id)
        if variant is None:
            return {"result": "product-variant-not-found", "errors": {"variant_id": "Variante não encontrada."}}
        if not bool(getattr(variant, "is_active", True)):
            return {"result": "product-variant-default-blocked", "errors": {"variant_id": "Variante inativa não pode ser padrão."}}

        with transaction.atomic():
            ProductVariant.objects.filter(product=product).update(is_default=False)
            variant.is_default = True
            variant.save(update_fields=["is_default", "updated_at"])

        self._record_event(
            product=product,
            action="product.variant_default_set",
            summary=f"Variante padrão de {product.slug} alterada para {variant.sku}",
            actor_label=actor_label,
            metadata={"product_id": product.id, "slug": product.slug, "variant_id": variant.id, "sku": variant.sku},
        )
        return {
            "result": "product-variant-default-set",
            "product": {"id": product.id, "slug": product.slug},
            "variant": {"id": variant.id, "sku": variant.sku},
        }

    def deactivate_product_variant(
        self,
        *,
        tenant_id: int | str | None,
        product_slug: str | None,
        variant_id: int | str | None,
        actor_label: object = "",
        actor_role: object = "",
    ) -> dict[str, object]:
        permission_result = self._check_manage_permission(actor_role=actor_role)
        if permission_result:
            return permission_result
        product = self._product_for_tenant(tenant_id=tenant_id, product_slug=product_slug)
        if product is None:
            return {"result": "product-not-found", "errors": {"__all__": "Produto não encontrado para este tenant."}}
        variant = self._variant_for_product(product=product, variant_id=variant_id)
        if variant is None:
            return {"result": "product-variant-not-found", "errors": {"variant_id": "Variante não encontrada."}}
        if not bool(getattr(variant, "is_active", True)):
            return {"result": "product-variant-already-inactive", "product": {"id": product.id, "slug": product.slug}}

        active_variants = ProductVariant.objects.filter(product=product, is_active=True)
        if active_variants.count() <= 1:
            return {
                "result": "product-variant-last-active",
                "errors": {"variant_id": "O produto precisa manter ao menos uma variante ativa."},
            }

        with transaction.atomic():
            was_default = bool(variant.is_default)
            variant.is_active = False
            variant.is_default = False
            variant.save(update_fields=["is_active", "is_default", "updated_at"])
            if was_default:
                replacement = (
                    ProductVariant.objects.filter(product=product, is_active=True)
                    .exclude(pk=variant.pk)
                    .order_by("position", "id")
                    .first()
                )
                if replacement is not None:
                    replacement.is_default = True
                    replacement.save(update_fields=["is_default", "updated_at"])

        self._record_event(
            product=product,
            action="product.variant_deactivated",
            summary=f"Variante {variant.sku} desativada sem exclusão física",
            actor_label=actor_label,
            metadata={"product_id": product.id, "slug": product.slug, "variant_id": variant.id, "sku": variant.sku},
        )
        return {
            "result": "product-variant-deactivated",
            "product": {"id": product.id, "slug": product.slug},
            "variant": {"id": variant.id, "sku": variant.sku},
        }

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
        limit_error = self._product_limit_error(
            tenant_id=tenant_id,
            target_status=normalized_status,
            current_product_id=product.id,
            current_status=product.status,
        )
        if limit_error:
            return {"result": "product-plan-limit-reached", "errors": {"__all__": limit_error}}

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

    def _check_manage_permission(self, *, actor_role: object) -> dict[str, object] | None:
        permission = admin_permissions.check(role=actor_role, permission=PERMISSION_CATALOG_MANAGE)
        if permission.allowed:
            return None
        return {
            "result": "product-permission-denied",
            "errors": {"__all__": "Permissão insuficiente para gerenciar produtos."},
        }

    @staticmethod
    def _tenant(tenant_id: int | str | None) -> Tenant | None:
        if not tenant_id:
            return None
        return Tenant.objects.filter(pk=tenant_id).first()

    @staticmethod
    def _product_for_tenant(*, tenant_id: int | str | None, product_slug: str | None) -> Product | None:
        if not tenant_id or not product_slug:
            return None
        return Product.objects.filter(tenant_id=tenant_id, slug=product_slug).first()

    @staticmethod
    def _variant_for_product(*, product: Product, variant_id: int | str | None) -> ProductVariant | None:
        if not variant_id:
            return None
        return ProductVariant.objects.filter(product=product, pk=variant_id).first()

    def _validated_values(
        self,
        *,
        tenant_id: int | str,
        payload: dict[str, object],
        current_product_id: int | None = None,
        current_variant_id: int | None = None,
    ) -> tuple[dict[str, object], dict[str, object], dict[str, str]]:
        name = _string(payload.get("name"), limit=255)
        slug = _slug(payload.get("slug"), fallback=name)
        description = _string(payload.get("description"), limit=5000)
        brand_name = _string(payload.get("brand"), limit=120)
        category_label = _string(payload.get("category_label"), limit=120)
        status = _string(payload.get("status"), limit=16) or Product.Status.DRAFT
        sku = _string(payload.get("sku"), limit=120)
        price, price_error = _decimal_value(payload.get("price"), field="price", required=True)
        compare_price, compare_price_error = _decimal_value(payload.get("compare_price"), field="compare_price")
        stock, stock_error = _integer_value(payload.get("stock"), required=True)
        reserved_stock, reserved_stock_error = _integer_value(payload.get("reserved_stock"))
        errors: dict[str, str] = {}

        if not name:
            errors["name"] = "Informe o nome do produto."
        if not slug:
            errors["slug"] = "Informe um slug ou nome válido."
        if status not in Product.Status.values:
            errors["status"] = "Status inválido."
        if not sku:
            errors["sku"] = "Informe o SKU principal."
        if price_error:
            errors["price"] = price_error
        if compare_price_error:
            errors["compare_price"] = compare_price_error
        if stock_error:
            errors["stock"] = stock_error
        if reserved_stock_error:
            errors["reserved_stock"] = reserved_stock_error
        if stock is not None and reserved_stock is not None and reserved_stock > stock:
            errors["reserved_stock"] = "A reserva operacional não pode ser maior que o estoque."

        duplicate_product = Product.objects.filter(tenant_id=tenant_id, slug=slug)
        if current_product_id:
            duplicate_product = duplicate_product.exclude(pk=current_product_id)
        if slug and duplicate_product.exists():
            errors["slug"] = "Já existe um produto com este slug neste tenant."

        duplicate_variant = ProductVariant.objects.filter(sku=sku)
        if current_variant_id:
            duplicate_variant = duplicate_variant.exclude(pk=current_variant_id)
        if sku and duplicate_variant.exists():
            errors["sku"] = "Já existe uma variante com este SKU."

        return (
            {
                "name": name,
                "slug": slug,
                "description": description,
                "brand_name": brand_name,
                "category_label": category_label,
                "status": status,
                "is_active": _checkbox(payload, "is_active"),
                "is_featured": _checkbox(payload, "is_featured"),
            },
            {
                "sku": sku,
                "price": price or Decimal("0"),
                "compare_price": compare_price,
                "stock": stock or 0,
                "reserved_stock": reserved_stock or 0,
                "track_inventory": _checkbox(payload, "track_inventory"),
                "allow_backorder": _checkbox(payload, "allow_backorder"),
            },
            errors,
        )

    @staticmethod
    def _product_limit_error(
        *,
        tenant_id: int | str,
        target_status: str,
        current_product_id: int | None = None,
        current_status: str = "",
    ) -> str:
        if target_status not in COUNTED_PRODUCT_STATUSES:
            return ""
        if current_product_id and current_status in COUNTED_PRODUCT_STATUSES:
            return ""
        terms = get_tenant_commercial_terms(tenant_id=tenant_id)
        if not terms.has_product_limit:
            return ""
        current_count = Product.objects.filter(tenant_id=tenant_id, status__in=COUNTED_PRODUCT_STATUSES).count()
        if current_count < terms.product_limit:
            return ""
        plan_name = terms.plan_name or "atual"
        return (
            f"Limite do plano {plan_name} atingido: {terms.product_limit} produtos ativos ou em rascunho. "
            "Desative produtos sem uso ou revise o plano antes de criar novos itens."
        )

    def _validated_variant_values(
        self,
        *,
        tenant_id: int | str | None,
        payload: dict[str, object],
        current_variant_id: int | None = None,
    ) -> tuple[dict[str, object], dict[str, str]]:
        sku = _string(payload.get("sku"), limit=120)
        label = _string(payload.get("label"), limit=160)
        barcode = _string(payload.get("barcode"), limit=120)
        option_values, option_values_error = _option_values(payload.get("option_values"))
        price, price_error = _decimal_value(payload.get("price"), field="price", required=True)
        compare_price, compare_price_error = _decimal_value(payload.get("compare_price"), field="compare_price")
        stock, stock_error = _integer_value(payload.get("stock"), required=True)
        reserved_stock, reserved_stock_error = _integer_value(payload.get("reserved_stock"))
        weight_grams, weight_error = _integer_value(payload.get("weight_grams"))
        position, position_error = _integer_value(payload.get("position"))
        is_active = _checkbox_default(payload, "is_active", default=True)
        is_default = _checkbox(payload, "is_default")
        errors: dict[str, str] = {}

        if not sku:
            errors["sku"] = "Informe o SKU da variante."
        if option_values_error:
            errors["option_values"] = option_values_error
        if price_error:
            errors["price"] = price_error
        if compare_price_error:
            errors["compare_price"] = compare_price_error
        if stock_error:
            errors["stock"] = stock_error
        if reserved_stock_error:
            errors["reserved_stock"] = reserved_stock_error
        if weight_error:
            errors["weight_grams"] = weight_error
        if position_error:
            errors["position"] = position_error
        if stock is not None and reserved_stock is not None and reserved_stock > stock:
            errors["reserved_stock"] = "A reserva operacional não pode ser maior que o estoque."
        if is_default and not is_active:
            errors["is_default"] = "A variante padrão precisa estar ativa."

        duplicate_variant = ProductVariant.objects.filter(sku=sku)
        if current_variant_id:
            duplicate_variant = duplicate_variant.exclude(pk=current_variant_id)
        if sku and duplicate_variant.exists():
            errors["sku"] = "Já existe uma variante com este SKU."

        return (
            {
                "sku": sku,
                "label": label,
                "option_values": option_values,
                "barcode": barcode,
                "price": price or Decimal("0"),
                "compare_price": compare_price,
                "stock": stock or 0,
                "reserved_stock": reserved_stock or 0,
                "weight_grams": weight_grams or 0,
                "track_inventory": _checkbox_default(payload, "track_inventory", default=True),
                "allow_backorder": _checkbox(payload, "allow_backorder"),
                "is_active": is_active,
                "is_default": is_default,
                "position": position or 0,
            },
            errors,
        )

    @staticmethod
    def _record_event(
        *,
        product: Product,
        action: str,
        summary: str,
        actor_label: object = "",
        metadata: dict[str, object] | None = None,
    ) -> None:
        audit_log_commands.record_event(
            tenant_id=product.tenant_id,
            module="catalog",
            action=action,
            entity_type="Product",
            entity_id=str(product.id),
            actor_label=_string(actor_label),
            summary=summary,
            metadata=metadata or {},
        )


admin_product_commands = AdminProductCommandService()
