from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from django.db import connection
from django.utils import timezone
from django.utils.text import slugify


STATUS_OPTIONS = [
    {"value": "active", "label": "Ativo"},
    {"value": "draft", "label": "Rascunho"},
    {"value": "inactive", "label": "Inativo"},
]


FALLBACK_PRODUCT_FIXTURES = [
    {
        "slug": "tenis-hubx-runner",
        "name": "Tênis Hubx Runner",
        "sku": "RUNNER-001-BLK-42",
        "status": "active",
        "status_label": "Ativo",
        "brand": "Hubx",
        "channel_label": "Storefront",
        "sales_channel": "Storefront + Marketplace",
        "category_label": "Calçados esportivos",
        "price": "299.90",
        "compare_price": "349.90",
        "stock": "24",
        "reserved_stock": "4",
        "updated_at": "há 15 minutos",
        "summary_content": "Produto com catálogo publicado, mídia aprovada e variante principal ativa para venda.",
        "pricing_content": "Preço atual: R$ 299,90 · Preço comparativo: R$ 349,90 · Margem operacional dentro da meta.",
        "inventory_content": "Estoque disponível: 24 unidades · Reserva operacional: 4 unidades · Sem risco de ruptura no curto prazo.",
        "details_content": "Descrição pública validada, ficha operacional preenchida e canais de venda sincronizados.",
        "visibility_content": "Produto visível na loja, elegível para destaque e disponível para campanhas promocionais.",
        "description": "Produto de demonstração da trilha admin para validar a integração com o Design System.",
        "is_active": True,
        "is_featured": True,
        "track_inventory": True,
        "allow_backorder": False,
        "activity_items": [
            {
                "title": "Preço promocional atualizado",
                "description": "Equipe de catálogo ajustou o preço comparativo para a campanha da semana.",
                "timestamp": "há 15 min",
                "badge_label": "Catálogo",
                "badge_variant": "info",
            },
            {
                "title": "Estoque sincronizado",
                "description": "Saldo da variante principal atualizado após conferência operacional.",
                "timestamp": "há 42 min",
                "badge_label": "Estoque",
                "badge_variant": "success",
            },
        ],
    },
    {
        "slug": "camiseta-hubx-performance",
        "name": "Camiseta Hubx Performance",
        "sku": "TSHIRT-010-WHT-M",
        "status": "draft",
        "status_label": "Rascunho",
        "brand": "Hubx",
        "channel_label": "Storefront",
        "sales_channel": "Storefront",
        "category_label": "Vestuário",
        "price": "129.90",
        "compare_price": "149.90",
        "stock": "58",
        "reserved_stock": "6",
        "updated_at": "há 1 hora",
        "summary_content": "Produto ainda em revisão editorial, com variantes e mídia já cadastradas.",
        "pricing_content": "Preço atual: R$ 129,90 · Preço comparativo: R$ 149,90 · Campanha futura configurada.",
        "inventory_content": "Estoque disponível: 58 unidades · Reserva operacional: 6 unidades.",
        "details_content": "Página pública pendente de publicação final após revisão de conteúdo.",
        "visibility_content": "Produto ainda não publicado e sem destaque ativo.",
        "description": "Modelo técnico para treinos com tecido leve e respirável.",
        "is_active": False,
        "is_featured": False,
        "track_inventory": True,
        "allow_backorder": False,
        "activity_items": [
            {
                "title": "Conteúdo pendente de aprovação",
                "description": "Página aguarda revisão editorial antes da publicação.",
                "timestamp": "há 1 hora",
                "badge_label": "Revisão",
                "badge_variant": "warning",
            }
        ],
    },
    {
        "slug": "mochila-hubx-urban",
        "name": "Mochila Hubx Urban",
        "sku": "BAG-204-GRY-U",
        "status": "inactive",
        "status_label": "Inativo",
        "brand": "Hubx",
        "channel_label": "Marketplace",
        "sales_channel": "Marketplace",
        "category_label": "Acessórios",
        "price": "199.90",
        "compare_price": "219.90",
        "stock": "0",
        "reserved_stock": "0",
        "updated_at": "há 3 horas",
        "summary_content": "Produto pausado no canal principal após revisão comercial.",
        "pricing_content": "Preço base mantido para futuras reativações.",
        "inventory_content": "Sem estoque disponível no momento.",
        "details_content": "Item temporariamente inativo por decisão comercial.",
        "visibility_content": "Produto oculto da loja e mantido apenas para histórico operacional.",
        "description": "Mochila urbana com compartimento acolchoado para notebook.",
        "is_active": False,
        "is_featured": False,
        "track_inventory": True,
        "allow_backorder": True,
        "activity_items": [
            {
                "title": "Produto desativado",
                "description": "Time comercial pausou a publicação até reabastecimento.",
                "timestamp": "há 3 horas",
                "badge_label": "Comercial",
                "badge_variant": "neutral",
            }
        ],
    },
]


class ProductReadRepository(Protocol):
    def list_products(self) -> list[dict[str, object]]:
        ...

    def get_product(self, product_slug: str) -> dict[str, object] | None:
        ...


def _clone_product(product: dict[str, object]) -> dict[str, object]:
    cloned = dict(product)
    cloned["activity_items"] = [dict(item) for item in product.get("activity_items", [])]
    cloned["variants"] = [dict(item) for item in product.get("variants", [])]
    cloned["images"] = [dict(item) for item in product.get("images", [])]
    return cloned


def _fallback_product(product_slug: str) -> dict[str, object]:
    title = product_slug.replace("-", " ").title()
    return {
        "slug": product_slug,
        "name": title,
        "sku": f"{slugify(product_slug).upper()[:8]}-001",
        "status": "draft",
        "status_label": "Rascunho",
        "brand": "Hubx",
        "channel_label": "Storefront",
        "sales_channel": "Storefront",
        "category_label": "Catálogo",
        "price": "0.00",
        "compare_price": "",
        "stock": "0",
        "reserved_stock": "0",
        "updated_at": "agora",
        "summary_content": "Produto ainda sem integração com dados reais; usando fallback seguro de apresentação.",
        "pricing_content": "Preço e regras comerciais serão preenchidos quando o serviço real do catálogo for conectado.",
        "inventory_content": "Sem informações de estoque disponíveis no adapter inicial.",
        "details_content": "Página criada para estabelecer o padrão de migração real com templates oficiais do Design System.",
        "visibility_content": "Visibilidade ainda não conectada ao fluxo real de catálogo.",
        "description": "Registro temporário para estabelecer a primeira wiring real com page templates oficiais.",
        "is_active": False,
        "is_featured": False,
        "track_inventory": False,
        "allow_backorder": False,
        "activity_items": [],
    }


def _format_admin_timestamp(value: object) -> str:
    if not value:
        return "agora"
    if isinstance(value, datetime):
        aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
        return aware_value.strftime("%d/%m/%Y às %H:%M")
    return str(value)


def _safe_int(value: object) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_float_string(value: str) -> str:
    return value.replace(".", ",")


def _build_summary_content(*, name: str, brand: str, category: str, status_label: str, sku: str) -> str:
    return (
        f"{name} da marca {brand} na categoria {category}, "
        f"com SKU principal {sku} e status operacional {status_label.lower()}."
    )


def _build_pricing_content(*, price: str, compare_price: str, is_featured: bool) -> str:
    base = f"Preço atual: R$ {_safe_float_string(price)}"
    if compare_price:
        base += f" · Preço comparativo: R$ {_safe_float_string(compare_price)}"
    base += " · Fonte: variante padrão persistida."
    if is_featured:
        base += " Produto marcado como destaque."
    return base


def _build_inventory_content(*, stock: str, reserved_stock: str, track_inventory: bool, allow_backorder: bool) -> str:
    stock_value = _safe_int(stock)
    reserved_value = _safe_int(reserved_stock)
    available_value = max(stock_value - reserved_value, 0)
    tracking_label = "Controle de estoque ativo" if track_inventory else "Controle de estoque manual"
    backorder_label = "backorder permitido" if allow_backorder else "backorder desativado"
    return (
        f"Estoque disponível: {stock_value} unidade(s) · "
        f"Reserva operacional: {reserved_value} unidade(s) · "
        f"Saldo livre estimado: {available_value} unidade(s) · "
        f"{tracking_label} · {backorder_label}."
    )


def _build_inventory_visibility_content(*, stock: str, reserved_stock: str, track_inventory: bool) -> str:
    stock_value = _safe_int(stock)
    reserved_value = _safe_int(reserved_stock)
    free_value = max(stock_value - reserved_value, 0)
    if not track_inventory:
        return "Visibilidade de estoque limitada: controle manual ativo, sem leitura operacional confiável de reserva."
    if reserved_value <= 0:
        return f"Sem impacto operacional recente de pedidos confirmado no estoque principal. Saldo livre atual: {free_value} unidade(s)."
    if free_value <= 3:
        return (
            f"Estoque comprometido: {reserved_value} unidade(s) já reservadas e apenas {free_value} livre(s) na variante principal."
        )
    return (
        f"Impacto operacional visível: {reserved_value} unidade(s) já reservadas em pedidos confirmados, com {free_value} livre(s) na variante principal."
    )


def _build_inventory_recovery_content(*, recovered_units: int, recovery_events_count: int, last_recovered_at: object) -> str:
    if recovered_units <= 0:
        return "Nenhuma devolução operacional recente de estoque foi registrada para este produto."
    return (
        f"Devolução operacional visível: {recovered_units} unidade(s) já voltaram ao estoque em "
        f"{recovery_events_count} cancelamento(s). Última recuperação em {_format_admin_timestamp(last_recovered_at)}."
    )


def _build_inventory_finalization_content(*, finalized_units: int, finalization_events_count: int, last_finalized_at: object) -> str:
    if finalized_units <= 0:
        return "Nenhum consumo final recente de reserva foi registrado para este produto."
    return (
        f"Consumo final visível: {finalized_units} unidade(s) já concluíram a reserva operacional em "
        f"{finalization_events_count} entrega(s). Última finalização em {_format_admin_timestamp(last_finalized_at)}."
    )


def _build_inventory_timeline_content(
    *,
    stock: str,
    reserved_stock: str,
    recovered_units: int,
    finalized_units: int,
    track_inventory: bool,
) -> str:
    if not track_inventory:
        return "Linha operacional do estoque indisponível: a variante principal ainda usa controle manual."
    stock_value = _safe_int(stock)
    reserved_value = _safe_int(reserved_stock)
    recovered_value = _safe_int(recovered_units)
    free_value = max(stock_value - reserved_value, 0)
    return (
        "Linha operacional do estoque: "
        f"{reserved_value} unidade(s) reservadas após pagamento confirmado · "
        f"{recovered_value} recuperada(s) por cancelamentos operacionais · "
        f"{finalized_units} finalizada(s) como consumo após entrega · "
        f"{free_value} livre(s) na variante principal agora."
    )


def _build_details_content(*, description: str, category: str, brand: str) -> str:
    if description:
        return description
    return f"Produto persistido na categoria {category}, marca {brand}, aguardando descrição editorial detalhada."


def _build_visibility_content(*, is_active: bool, is_featured: bool, sales_channel: str, status_label: str) -> str:
    publication_label = "visível no catálogo" if is_active else "não publicado no catálogo"
    featured_label = "com destaque ativo" if is_featured else "sem destaque ativo"
    return f"Produto {publication_label}, {featured_label}, no canal {sales_channel} e status {status_label.lower()}."


def _build_activity_items(
    *,
    updated_at: object,
    is_featured: bool,
    track_inventory: bool,
    allow_backorder: bool,
    stock: str,
    reserved_stock: str,
    recovered_units: int,
    last_recovered_at: object,
    finalized_units: int,
    last_finalized_at: object,
) -> list[dict[str, object]]:
    timestamp = _format_admin_timestamp(updated_at)
    reserved_value = _safe_int(reserved_stock)
    items = [
        {
            "title": "Registro persistido sincronizado",
            "description": "Dados principais do produto carregados a partir do catálogo persistido do módulo.",
            "timestamp": timestamp,
            "badge_label": "Catálogo",
            "badge_variant": "info",
        }
    ]
    if track_inventory:
        items.append(
            {
                "title": "Saldo livre atual",
                "description": (
                    f"Variante principal com {max(_safe_int(stock) - reserved_value, 0)} unidade(s) livres, "
                    f"{reserved_value} reservadas e {_safe_int(stock)} registradas no total."
                ),
                "timestamp": timestamp,
                "badge_label": "Estoque",
                "badge_variant": "success",
            }
        )
    if track_inventory and reserved_value > 0:
        items.append(
            {
                "title": "Reserva operacional visível",
                "description": f"{reserved_value} unidade(s) da variante principal já estão comprometidas por pedidos confirmados.",
                "timestamp": timestamp,
                "badge_label": "Reserva",
                "badge_variant": "warning",
            }
        )
    if track_inventory and recovered_units > 0:
        items.append(
            {
                "title": "Devolução operacional registrada",
                "description": (
                    f"{recovered_units} unidade(s) já retornaram ao estoque depois de cancelamentos operacionais. "
                    f"Última recuperação em {_format_admin_timestamp(last_recovered_at)}."
                ),
                "timestamp": _format_admin_timestamp(last_recovered_at),
                "badge_label": "Recuperação",
                "badge_variant": "success",
            }
        )
    if track_inventory and finalized_units > 0:
        items.append(
            {
                "title": "Consumo final registrado",
                "description": (
                    f"{finalized_units} unidade(s) já saíram do estado reservado e viraram consumo final após entrega. "
                    f"Última finalização em {_format_admin_timestamp(last_finalized_at)}."
                ),
                "timestamp": _format_admin_timestamp(last_finalized_at),
                "badge_label": "Finalização",
                "badge_variant": "info",
            }
        )
    if is_featured or allow_backorder:
        items.append(
            {
                "title": "Visibilidade e venda revisadas",
                "description": (
                    "Produto com destaque ativo."
                    if is_featured
                    else "Produto com política de encomenda habilitada."
                ),
                "timestamp": timestamp,
                "badge_label": "Operação",
                "badge_variant": "warning" if allow_backorder and not is_featured else "info",
            }
        )
    return items[:5]


class FallbackProductRepository:
    def list_products(self) -> list[dict[str, object]]:
        return [_clone_product(product) for product in FALLBACK_PRODUCT_FIXTURES]

    def get_product(self, product_slug: str) -> dict[str, object] | None:
        for product in self.list_products():
            if product["slug"] == product_slug:
                return product
        return None


class DjangoOrmProductRepository:
    def __init__(self) -> None:
        try:
            from app.modules.catalog import models as catalog_models
            from app.modules.orders import models as order_models
        except Exception:
            self.product_model = None
            self.image_model = None
            self.order_model = None
            self.order_item_model = None
            return

        self.product_model = getattr(catalog_models, "Product", None)
        self.image_model = getattr(catalog_models, "ProductImage", None)
        self.order_model = getattr(order_models, "Order", None)
        self.order_item_model = getattr(order_models, "OrderItem", None)

    def _has_real_model(self) -> bool:
        return self.product_model is not None

    def is_ready(self) -> bool:
        if not self._has_real_model():
            return False

        try:
            table_names = {
                self.product_model._meta.db_table,
                self.product_model._meta.get_field("variants").related_model._meta.db_table,
            }
        except Exception:
            return False

        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False

        return table_names.issubset(set(tables))

    def _images_ready(self) -> bool:
        if self.image_model is None:
            return False
        try:
            image_table = self.image_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return image_table in set(tables)

    def _orders_ready(self) -> bool:
        if self.order_model is None or self.order_item_model is None:
            return False
        try:
            table_names = {
                self.order_model._meta.db_table,
                self.order_item_model._meta.db_table,
            }
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_names.issubset(set(tables))

    def list_products(self) -> list[dict[str, object]]:
        if not self.is_ready():
            return []

        try:
            prefetches = ["variants"]
            if self._images_ready():
                prefetches.append("images")
            queryset = self.product_model._default_manager.all().prefetch_related(*prefetches).order_by("-id")
        except Exception:
            return []

        return [self._serialize_product(product) for product in queryset]

    def get_product(self, product_slug: str) -> dict[str, object] | None:
        if not self.is_ready():
            return None

        try:
            prefetches = ["variants"]
            if self._images_ready():
                prefetches.append("images")
            product = self.product_model._default_manager.filter(slug=product_slug).prefetch_related(*prefetches).first()
        except Exception:
            return None

        if not product:
            return None
        return self._serialize_product(product)

    def _inventory_recovery_snapshot(self, product: object) -> dict[str, object]:
        if not self._orders_ready():
            return {"recovered_units": 0, "recovery_events_count": 0, "last_recovered_at": None}
        variant_list = self._serialize_variants(product)
        variant_skus = [str(variant.get("sku") or "").strip() for variant in variant_list if str(variant.get("sku") or "").strip()]
        if not variant_skus:
            return {"recovered_units": 0, "recovery_events_count": 0, "last_recovered_at": None}
        try:
            order_items = (
                self.order_item_model._default_manager.filter(
                    variant_sku__in=variant_skus,
                    order__tenant_id=getattr(product, "tenant_id", None),
                    order__inventory_recovered_at__isnull=False,
                )
                .select_related("order")
                .order_by("-order__inventory_recovered_at", "-id")
            )
        except Exception:
            return {"recovered_units": 0, "recovery_events_count": 0, "last_recovered_at": None}
        recovered_units = 0
        order_ids: set[int] = set()
        last_recovered_at = None
        for item in order_items:
            recovered_units += int(getattr(item, "quantity", 0) or 0)
            order_id = getattr(item, "order_id", None)
            if order_id:
                order_ids.add(int(order_id))
            if last_recovered_at is None:
                last_recovered_at = getattr(getattr(item, "order", None), "inventory_recovered_at", None)
        return {
            "recovered_units": recovered_units,
            "recovery_events_count": len(order_ids),
            "last_recovered_at": last_recovered_at,
        }

    def _inventory_finalization_snapshot(self, product: object) -> dict[str, object]:
        if not self._orders_ready():
            return {"finalized_units": 0, "finalization_events_count": 0, "last_finalized_at": None}
        variant_list = self._serialize_variants(product)
        variant_skus = [str(variant.get("sku") or "").strip() for variant in variant_list if str(variant.get("sku") or "").strip()]
        if not variant_skus:
            return {"finalized_units": 0, "finalization_events_count": 0, "last_finalized_at": None}
        try:
            order_items = (
                self.order_item_model._default_manager.filter(
                    variant_sku__in=variant_skus,
                    order__tenant_id=getattr(product, "tenant_id", None),
                    order__inventory_finalized_at__isnull=False,
                )
                .select_related("order")
                .order_by("-order__inventory_finalized_at", "-id")
            )
        except Exception:
            return {"finalized_units": 0, "finalization_events_count": 0, "last_finalized_at": None}
        finalized_units = 0
        order_ids: set[int] = set()
        last_finalized_at = None
        for item in order_items:
            finalized_units += int(getattr(item, "quantity", 0) or 0)
            order_id = getattr(item, "order_id", None)
            if order_id:
                order_ids.add(int(order_id))
            if last_finalized_at is None:
                last_finalized_at = getattr(getattr(item, "order", None), "inventory_finalized_at", None)
        return {
            "finalized_units": finalized_units,
            "finalization_events_count": len(order_ids),
            "last_finalized_at": last_finalized_at,
        }

    def _serialize_product(self, product: object) -> dict[str, object]:
        status = self._status_value(product)
        status_label = dict((option["value"], option["label"]) for option in STATUS_OPTIONS).get(status, "Rascunho")
        brand = self._string_value(getattr(product, "brand_name", None), default="Hubx")
        category = self._string_value(getattr(product, "category_label", None), default="Catálogo")
        default_variant = self._default_variant(product)
        price = self._string_value(getattr(default_variant, "price", ""), default="0.00")
        compare_price = self._string_value(getattr(default_variant, "compare_price", ""), default="")
        stock = self._string_value(getattr(default_variant, "stock", ""), default="0")
        reserved_stock = self._string_value(getattr(default_variant, "reserved_stock", ""), default="0")
        description = self._string_value(getattr(product, "description", ""), default="")
        sku = self._string_value(getattr(default_variant, "sku", None), default="SKU-001")
        track_inventory = bool(getattr(default_variant, "track_inventory", True))
        allow_backorder = bool(getattr(default_variant, "allow_backorder", False))
        is_active = bool(getattr(product, "is_active", status == "active"))
        is_featured = bool(getattr(product, "is_featured", False))
        channel_label = "Storefront" if is_active else "Catálogo interno"
        sales_channel = "Storefront" if is_active else "Storefront não publicado"
        updated_at = _format_admin_timestamp(getattr(product, "updated_at", ""))
        inventory_recovery = self._inventory_recovery_snapshot(product)
        inventory_finalization = self._inventory_finalization_snapshot(product)

        return {
            "tenant_id": getattr(product, "tenant_id", None),
            "slug": self._string_value(getattr(product, "slug", ""), default=slugify(self._string_value(getattr(product, "name", ""), default="produto"))),
            "name": self._string_value(getattr(product, "name", ""), default="Produto"),
            "sku": sku,
            "status": status,
            "status_label": status_label,
            "brand": brand,
            "channel_label": channel_label,
            "sales_channel": sales_channel,
            "category_label": category,
            "price": price,
            "compare_price": compare_price,
            "stock": stock,
            "reserved_stock": reserved_stock,
            "recovered_stock": str(inventory_recovery["recovered_units"]),
            "finalized_stock": str(inventory_finalization["finalized_units"]),
            "recovery_events_count": inventory_recovery["recovery_events_count"],
            "finalization_events_count": inventory_finalization["finalization_events_count"],
            "updated_at": updated_at,
            "summary_content": _build_summary_content(
                name=self._string_value(getattr(product, "name", ""), default="Produto"),
                brand=brand,
                category=category,
                status_label=status_label,
                sku=sku,
            ),
            "pricing_content": _build_pricing_content(
                price=price,
                compare_price=compare_price,
                is_featured=is_featured,
            ),
            "inventory_content": _build_inventory_content(
                stock=stock,
                reserved_stock=reserved_stock,
                track_inventory=track_inventory,
                allow_backorder=allow_backorder,
            ),
            "inventory_visibility_content": _build_inventory_visibility_content(
                stock=stock,
                reserved_stock=reserved_stock,
                track_inventory=track_inventory,
            ),
            "inventory_recovery_content": _build_inventory_recovery_content(
                recovered_units=inventory_recovery["recovered_units"],
                recovery_events_count=inventory_recovery["recovery_events_count"],
                last_recovered_at=inventory_recovery["last_recovered_at"],
            ),
            "inventory_finalization_content": _build_inventory_finalization_content(
                finalized_units=inventory_finalization["finalized_units"],
                finalization_events_count=inventory_finalization["finalization_events_count"],
                last_finalized_at=inventory_finalization["last_finalized_at"],
            ),
            "inventory_timeline_content": _build_inventory_timeline_content(
                stock=stock,
                reserved_stock=reserved_stock,
                recovered_units=inventory_recovery["recovered_units"],
                finalized_units=inventory_finalization["finalized_units"],
                track_inventory=track_inventory,
            ),
            "details_content": _build_details_content(
                description=description,
                category=category,
                brand=brand,
            ),
            "visibility_content": _build_visibility_content(
                is_active=is_active,
                is_featured=is_featured,
                sales_channel=sales_channel,
                status_label=status_label,
            ),
            "description": description,
            "is_active": is_active,
            "is_featured": is_featured,
            "track_inventory": track_inventory,
            "allow_backorder": allow_backorder,
            "variants": self._serialize_variants(product),
            "images": self._serialize_images(product),
            "activity_items": _build_activity_items(
                updated_at=getattr(product, "updated_at", ""),
                is_featured=is_featured,
                track_inventory=track_inventory,
                allow_backorder=allow_backorder,
                stock=stock,
                reserved_stock=reserved_stock,
                recovered_units=inventory_recovery["recovered_units"],
                last_recovered_at=inventory_recovery["last_recovered_at"],
                finalized_units=inventory_finalization["finalized_units"],
                last_finalized_at=inventory_finalization["last_finalized_at"],
            ),
        }

    @staticmethod
    def _default_variant(product: object) -> object | None:
        variants = getattr(product, "variants", None)
        if variants is None:
            return None
        try:
            variant_list = list(variants.all())
        except Exception:
            return None
        if not variant_list:
            return None
        for variant in variant_list:
            if getattr(variant, "is_default", False):
                return variant
        return variant_list[0]

    @staticmethod
    def _status_value(product: object) -> str:
        explicit_status = getattr(product, "status", None)
        if explicit_status in {"active", "draft", "inactive"}:
            return str(explicit_status)
        return "active" if bool(getattr(product, "is_active", False)) else "inactive"

    @staticmethod
    def _serialize_variants(product: object) -> list[dict[str, object]]:
        variants = getattr(product, "variants", None)
        if variants is None:
            return []
        try:
            variant_list = list(variants.all())
        except Exception:
            return []
        return [
            {
                "sku": DjangoOrmProductRepository._string_value(getattr(variant, "sku", None), default=""),
                "price": DjangoOrmProductRepository._string_value(getattr(variant, "price", None), default="0.00"),
                "compare_price": DjangoOrmProductRepository._string_value(getattr(variant, "compare_price", None), default=""),
                "stock": DjangoOrmProductRepository._string_value(getattr(variant, "stock", None), default="0"),
                "reserved_stock": DjangoOrmProductRepository._string_value(getattr(variant, "reserved_stock", None), default="0"),
                "track_inventory": bool(getattr(variant, "track_inventory", True)),
                "allow_backorder": bool(getattr(variant, "allow_backorder", False)),
                "is_default": bool(getattr(variant, "is_default", False)),
            }
            for variant in variant_list
        ]

    @staticmethod
    def _serialize_images(product: object) -> list[dict[str, object]]:
        images = getattr(product, "images", None)
        if images is None:
            return []
        try:
            image_list = list(images.all())
        except Exception:
            return []
        return [
            {
                "image_url": DjangoOrmProductRepository._string_value(getattr(image, "image_url", None), default=""),
                "alt_text": DjangoOrmProductRepository._string_value(getattr(image, "alt_text", None), default=""),
                "position": int(getattr(image, "position", 0) or 0),
                "is_primary": bool(getattr(image, "is_primary", False)),
            }
            for image in image_list
        ]

    @staticmethod
    def _string_value(value: object, *, default: str) -> str:
        if value in (None, ""):
            return default
        return str(value)


@dataclass
class AdminProductQueryService:
    orm_repository: ProductReadRepository
    fallback_repository: ProductReadRepository

    def using_persisted_source(self) -> bool:
        try:
            return bool(self.orm_repository.list_products())
        except Exception:
            return False

    def list_products(self) -> list[dict[str, object]]:
        real_products = self.orm_repository.list_products()
        return real_products or self.fallback_repository.list_products()

    def get_inventory_visibility_note(self) -> str:
        products = self.list_products()
        if not products:
            return "Visibilidade de estoque: catálogo ainda sem fonte persistida para destacar impacto de pedidos."
        reserved_products = sum(1 for product in products if _safe_int(product.get("reserved_stock")) > 0)
        recovered_products = sum(1 for product in products if _safe_int(product.get("recovered_stock")) > 0)
        finalized_products = sum(1 for product in products if _safe_int(product.get("finalized_stock")) > 0)
        constrained_products = sum(
            1
            for product in products
            if max(_safe_int(product.get("stock")) - _safe_int(product.get("reserved_stock")), 0) <= 3
            and _safe_int(product.get("reserved_stock")) > 0
        )
        return (
            "Visibilidade de estoque: "
            f"{reserved_products} produto(s) já mostram reserva operacional e "
            f"{constrained_products} com saldo livre mais sensível. "
            f"Recuperação operacional já visível em {recovered_products} produto(s). "
            f"Consumo final já visível em {finalized_products} produto(s)."
        )

    def get_product(self, product_slug: str) -> dict[str, object]:
        real_product = self.orm_repository.get_product(product_slug)
        if real_product:
            return real_product

        fallback_product = self.fallback_repository.get_product(product_slug)
        if fallback_product:
            return fallback_product

        return _fallback_product(product_slug)

    def get_form_initial(self, product_slug: str | None) -> dict[str, object]:
        if not product_slug:
            return {
                "name": "",
                "slug": "",
                "sku": "",
                "brand": "",
                "description": "",
                "price": "",
                "compare_price": "",
                "stock": "",
                "reserved_stock": "",
                "status_selected": "draft",
                "is_active": False,
                "is_featured": False,
                "track_inventory": True,
                "allow_backorder": False,
            }

        product = self.get_product(product_slug)
        return {
            "name": product["name"],
            "slug": product["slug"],
            "sku": product["sku"],
            "brand": product["brand"],
            "description": product["description"],
            "price": product["price"],
            "compare_price": product["compare_price"],
            "stock": product["stock"],
            "reserved_stock": product["reserved_stock"],
            "status_selected": product["status"],
            "is_active": product["is_active"],
            "is_featured": product["is_featured"],
            "track_inventory": product["track_inventory"],
            "allow_backorder": product["allow_backorder"],
        }


admin_product_queries = AdminProductQueryService(
    orm_repository=DjangoOrmProductRepository(),
    fallback_repository=FallbackProductRepository(),
)
