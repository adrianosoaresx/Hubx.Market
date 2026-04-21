from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.utils import timezone

STATUS_OPTIONS = [
    {"value": "paid", "label": "Pago"},
    {"value": "pending", "label": "Pendente"},
    {"value": "shipped", "label": "Enviado"},
    {"value": "canceled", "label": "Cancelado"},
]

INVENTORY_EXCEPTION_QUICK_FILTER_OPTIONS = [
    {"value": "active", "label": "Exceção ativa"},
    {"value": "review", "label": "Em revisão"},
    {"value": "resolved", "label": "Resolvidas"},
    {"value": "high_priority", "label": "Alta prioridade"},
    {"value": "medium_priority", "label": "Média prioridade"},
    {"value": "low_priority", "label": "Baixa prioridade"},
    {"value": "unassigned", "label": "Sem responsável"},
    {"value": "assigned", "label": "Com responsável"},
]


FALLBACK_ORDER_FIXTURES = [
    {
        "order_number": "1048",
        "customer": "Ana Souza",
        "status": "paid",
        "order_status_label": "Pago",
        "fulfillment_status_label": "Separando itens",
        "fulfillment_status_variant": "info",
        "payment_status": "Confirmado",
        "shipping_status": "Separando itens",
        "updated_at": "há 4 min",
        "summary_content": "Pedido confirmado com pagamento aprovado e separação em andamento.",
        "customer_content": "Ana Souza · ana@hubx.market · (11) 99999-0000",
        "payment_content": "Cartão de crédito · 3x sem juros · Captura confirmada.",
        "shipping_content": "Rua das Laranjeiras, 100 · São Paulo/SP · Transportadora padrão.",
        "notes_content": "Cliente solicitou entrega em horário comercial. Separação prioritária para hoje.",
        "subtotal": "R$ 299,90",
        "shipping": "R$ 24,90",
        "discount": "",
        "installments": "3x de R$ 108,26 sem juros",
        "total": "R$ 324,80",
        "order_items": [
            {
                "title": "Tênis Hubx Runner",
                "subtitle": "Preto · 42",
                "meta": "SKU RUNNER-001-BLK-42",
                "price": "R$ 299,90",
                "quantity": "1",
                "quantity_readonly": True,
            }
        ],
        "activity_items": [
            {
                "title": "Pagamento confirmado",
                "description": "Gateway confirmou a captura do valor total do pedido.",
                "timestamp": "há 4 min",
                "badge_label": "Pagamento",
                "badge_variant": "paid",
            },
            {
                "title": "Pedido enviado para separação",
                "description": "Equipe operacional recebeu o pedido na fila de picking.",
                "timestamp": "há 12 min",
                "badge_label": "Expedição",
                "badge_variant": "info",
            },
        ],
    },
    {
        "order_number": "1049",
        "customer": "Bruno Lima",
        "status": "pending",
        "order_status_label": "Pendente",
        "fulfillment_status_label": "Aguardando pagamento",
        "fulfillment_status_variant": "warning",
        "payment_status": "Aguardando PIX",
        "shipping_status": "Aguardando liberação",
        "updated_at": "há 18 min",
        "summary_content": "Pedido criado e aguardando confirmação de pagamento para seguir na operação.",
        "customer_content": "Bruno Lima · bruno@hubx.market · (21) 98888-0000",
        "payment_content": "PIX · QR Code emitido · vencimento em 30 min.",
        "shipping_content": "Frete padrão selecionado, aguardando pagamento.",
        "notes_content": "Sem observações adicionais do cliente.",
        "subtotal": "R$ 129,90",
        "shipping": "R$ 19,90",
        "discount": "",
        "installments": "",
        "total": "R$ 149,80",
        "order_items": [
            {
                "title": "Camiseta Hubx Performance",
                "subtitle": "Branca · M",
                "meta": "SKU TSHIRT-010-WHT-M",
                "price": "R$ 129,90",
                "quantity": "1",
                "quantity_readonly": True,
            }
        ],
        "activity_items": [
            {
                "title": "QR Code emitido",
                "description": "Cliente recebeu a instrução de pagamento via PIX.",
                "timestamp": "há 18 min",
                "badge_label": "Checkout",
                "badge_variant": "warning",
            }
        ],
    },
    {
        "order_number": "1050",
        "customer": "Mariana Costa",
        "status": "shipped",
        "order_status_label": "Enviado",
        "fulfillment_status_label": "Em trânsito",
        "fulfillment_status_variant": "shipped",
        "payment_status": "Confirmado",
        "shipping_status": "Em trânsito",
        "updated_at": "há 1 h",
        "summary_content": "Pedido já coletado pela transportadora, com rastreio ativo.",
        "customer_content": "Mariana Costa · mariana@hubx.market · (31) 97777-0000",
        "payment_content": "Cartão de crédito · captura confirmada.",
        "shipping_content": "Coleta realizada · transportadora expressa.",
        "notes_content": "Pedido elegível para acompanhamento proativo até entrega.",
        "subtotal": "R$ 199,90",
        "shipping": "R$ 29,90",
        "discount": "-R$ 10,00",
        "installments": "2x de R$ 109,90 sem juros",
        "total": "R$ 219,80",
        "order_items": [
            {
                "title": "Mochila Hubx Urban",
                "subtitle": "Cinza · Único",
                "meta": "SKU BAG-204-GRY-U",
                "price": "R$ 199,90",
                "quantity": "1",
                "quantity_readonly": True,
            }
        ],
        "activity_items": [
            {
                "title": "Pedido coletado",
                "description": "Transportadora retirou o pacote no centro de distribuição.",
                "timestamp": "há 1 h",
                "badge_label": "Transporte",
                "badge_variant": "shipped",
            }
        ],
    },
]


class OrderReadRepository(Protocol):
    def list_orders(self) -> list[dict[str, object]]:
        ...

    def get_order(self, order_number: str) -> dict[str, object] | None:
        ...


def _clone_order(order: dict[str, object]) -> dict[str, object]:
    return {
        **order,
        "order_items": [dict(item) for item in order.get("order_items", [])],
        "activity_items": [dict(item) for item in order.get("activity_items", [])],
    }


class FallbackOrderRepository:
    def list_orders(self) -> list[dict[str, object]]:
        return [_clone_order(order) for order in FALLBACK_ORDER_FIXTURES]

    def get_order(self, order_number: str) -> dict[str, object] | None:
        normalized = order_number.lstrip("#")
        for order in self.list_orders():
            if str(order["order_number"]) == normalized:
                return order
        return None


class DjangoOrmOrderRepository:
    def __init__(self) -> None:
        try:
            from app.modules.orders import models as order_models
            from app.modules.catalog import models as catalog_models
        except Exception:
            self.order_model = None
            self.variant_model = None
            return

        self.order_model = getattr(order_models, "Order", None)
        self.variant_model = getattr(catalog_models, "ProductVariant", None)

    def _has_real_model(self) -> bool:
        return self.order_model is not None

    def is_ready(self) -> bool:
        if not self._has_real_model():
            return False
        try:
            table_names = {
                self.order_model._meta.db_table,
                self.order_model._meta.get_field("items").related_model._meta.db_table,
            }
            if self.variant_model is not None:
                table_names.add(self.variant_model._meta.db_table)
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_names.issubset(set(tables))

    def _get_variant_snapshot(self, *, tenant_id: int | None, sku: str):
        if self.variant_model is None or not tenant_id or not sku:
            return None
        try:
            return (
                self.variant_model._default_manager.select_related("product")
                .filter(product__tenant_id=tenant_id, sku=sku)
                .first()
            )
        except Exception:
            return None

    def list_orders(self) -> list[dict[str, object]]:
        if not self.is_ready():
            return []

        try:
            queryset = (
                self.order_model._default_manager.all()
                .prefetch_related("items", "status_history")
                .order_by("-updated_at", "-id")
            )
        except Exception:
            return []

        return [self._serialize_order(order) for order in queryset]

    def get_order(self, order_number: str) -> dict[str, object] | None:
        if not self.is_ready():
            return None

        try:
            order = (
                self.order_model._default_manager.filter(number=order_number.lstrip("#"))
                .prefetch_related("items", "status_history")
                .first()
            )
        except Exception:
            return None

        if not order:
            return None
        return self._serialize_order(order)

    def _serialize_order(self, order: object) -> dict[str, object]:
        status = self._string_value(getattr(order, "status", None), default="pending")
        status_label = dict((option["value"], option["label"]) for option in STATUS_OPTIONS).get(status, "Pendente")
        order_number = self._string_value(getattr(order, "number", None), default="0000")
        customer_name = self._customer_name(order)
        updated_at = self._format_timestamp(getattr(order, "updated_at", None))
        payment_status = self._string_value(getattr(order, "payment_status", None), default="Indisponível")
        shipping_status = self._string_value(getattr(order, "shipping_status", None), default="Indisponível")
        fulfillment_status_label = self._string_value(getattr(order, "fulfillment_status_label", None), default="Em processamento")
        fulfillment_status_variant = self._string_value(getattr(order, "fulfillment_status_variant", None), default="info")
        customer_email = self._string_value(getattr(order, "customer_email", None), default="")
        customer_phone = self._string_value(getattr(order, "customer_phone", None), default="")
        shipping_address_summary = self._string_value(getattr(order, "shipping_address_summary", None), default="Endereço indisponível")
        notes_content = self._string_value(getattr(order, "notes_content", None), default="Sem observações operacionais registradas.")
        subtotal = self._money_value(getattr(order, "subtotal", None))
        shipping = self._money_value(getattr(order, "shipping_total", None))
        discount = self._money_value(getattr(order, "discount_total", None), allow_empty=True)
        total = self._money_value(getattr(order, "total", None))
        installments = self._string_value(getattr(order, "installments_summary", None), default="")
        items = self._serialize_items(order)
        inventory_visibility_content = self._build_inventory_visibility_content(order=order, items=items)
        inventory_exception_content = self._build_inventory_exception_content(order=order, items=items)
        inventory_exception_guidance_label, inventory_exception_guidance_helper = self._build_inventory_exception_guidance(
            inventory_exception_content
        )
        inventory_exception_marker_label, inventory_exception_marker_helper = self._build_inventory_exception_marker(
            order=order,
            inventory_exception_content=inventory_exception_content,
        )
        inventory_exception_owner_label, inventory_exception_owner_helper = self._build_inventory_exception_owner(order=order)
        inventory_exception_list_label, inventory_exception_list_helper = self._build_inventory_exception_list_state(
            inventory_exception_content=inventory_exception_content,
            inventory_exception_marker_label=inventory_exception_marker_label,
            inventory_exception_owner_label=inventory_exception_owner_label,
        )
        inventory_exception_priority_label, inventory_exception_priority_helper = self._build_inventory_exception_priority(
            inventory_exception_content=inventory_exception_content,
            inventory_exception_marker_label=inventory_exception_marker_label,
        )
        inventory_exception_aging_label, inventory_exception_aging_helper = self._build_inventory_exception_aging(
            order=order,
            inventory_exception_content=inventory_exception_content,
            inventory_exception_marker_label=inventory_exception_marker_label,
        )
        next_step_label, next_step_helper, blocked_action_guidance = self._build_next_step_guidance(
            status=status,
            payment_status=payment_status,
            shipping_status=shipping_status,
            fulfillment_status_label=fulfillment_status_label,
        )

        return {
            "order_number": order_number,
            "customer": customer_name,
            "customer_linkage_mode": "explicit" if getattr(order, "customer_id", None) else "fallback",
            "status": status,
            "order_status_label": status_label,
            "fulfillment_status_label": fulfillment_status_label,
            "fulfillment_status_variant": fulfillment_status_variant,
            "payment_status": payment_status,
            "shipping_status": shipping_status,
            "updated_at": updated_at,
            "summary_content": f"Pedido #{order_number} de {customer_name} com status {status_label.lower()} e atualização registrada em {updated_at}.",
            "customer_content": " · ".join(filter(None, [customer_name, customer_email, customer_phone])),
            "payment_content": f"{payment_status}" + (f" · {installments}" if installments else ""),
            "shipping_content": f"{shipping_address_summary} · {shipping_status}",
            "notes_content": notes_content,
            "subtotal": subtotal,
            "shipping": shipping,
            "discount": discount,
            "installments": installments,
            "total": total,
            "inventory_visibility_content": inventory_visibility_content,
            "inventory_exception_content": inventory_exception_content,
            "inventory_exception_guidance_label": inventory_exception_guidance_label,
            "inventory_exception_guidance_helper": inventory_exception_guidance_helper,
            "inventory_exception_marker_label": inventory_exception_marker_label,
            "inventory_exception_marker_helper": inventory_exception_marker_helper,
            "inventory_exception_owner_label": inventory_exception_owner_label,
            "inventory_exception_owner_helper": inventory_exception_owner_helper,
            "inventory_exception_list_label": inventory_exception_list_label,
            "inventory_exception_list_helper": inventory_exception_list_helper,
            "inventory_exception_priority_label": inventory_exception_priority_label,
            "inventory_exception_priority_helper": inventory_exception_priority_helper,
            "inventory_exception_aging_label": inventory_exception_aging_label,
            "inventory_exception_aging_helper": inventory_exception_aging_helper,
            "inventory_exception_under_review_marked": bool(getattr(order, "inventory_exception_under_review_at", None)),
            "inventory_exception_resolved_marked": bool(getattr(order, "inventory_exception_resolved_at", None)),
            "next_step_label": next_step_label,
            "next_step_helper": next_step_helper,
            "blocked_action_guidance": blocked_action_guidance,
            "order_items": items,
            "activity_items": self._build_activity_items(
                order=order,
                updated_at=updated_at,
                payment_status=payment_status,
                shipping_status=shipping_status,
                fulfillment_status_label=fulfillment_status_label,
                inventory_exception_content=inventory_exception_content,
                inventory_exception_guidance_label=inventory_exception_guidance_label,
                inventory_exception_guidance_helper=inventory_exception_guidance_helper,
                inventory_exception_marker_label=inventory_exception_marker_label,
                inventory_exception_marker_helper=inventory_exception_marker_helper,
            ),
        }

    @staticmethod
    def _customer_name(order: object) -> str:
        direct_name = getattr(order, "customer_name", None)
        if direct_name:
            return str(direct_name)
        customer = getattr(order, "customer", None)
        if customer is None:
            return "Cliente"
        for attr in ("full_name", "name"):
            value = getattr(customer, attr, None)
            if value:
                return str(value)
        return str(customer)

    @staticmethod
    def _string_value(value: object, *, default: str) -> str:
        if value in (None, ""):
            return default
        return str(value)

    @staticmethod
    def _money_value(value: object, *, allow_empty: bool = False) -> str:
        if value in (None, ""):
            return "" if allow_empty else "R$ 0,00"
        if isinstance(value, Decimal):
            numeric = value
        elif isinstance(value, (int, float)):
            numeric = Decimal(str(value))
        else:
            return str(value)
        prefix = "-R$ " if allow_empty and numeric > 0 else "R$ "
        return f"{prefix}{numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _format_timestamp(value: object) -> str:
        if not value:
            return "agora"
        if isinstance(value, datetime):
            aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
            return aware_value.strftime("%d/%m/%Y às %H:%M")
        return str(value)

    @staticmethod
    def _serialize_items(order: object) -> list[dict[str, object]]:
        try:
            items = list(getattr(order, "items").all())
        except Exception:
            return []
        return [
            {
                "title": str(getattr(item, "title", "") or ""),
                "subtitle": str(getattr(item, "subtitle", "") or ""),
                "meta": str(getattr(item, "meta", "") or ""),
                "variant_sku": str(getattr(item, "variant_sku", "") or ""),
                "price": DjangoOrmOrderRepository._money_value(getattr(item, "price_snapshot", None)),
                "quantity": str(getattr(item, "quantity", 1) or 1),
                "quantity_readonly": bool(getattr(item, "quantity_readonly", True)),
            }
            for item in items
        ]

    @staticmethod
    def _build_inventory_visibility_content(*, order: object, items: list[dict[str, object]]) -> str:
        inventory_reserved_at = getattr(order, "inventory_reserved_at", None)
        inventory_recovered_at = getattr(order, "inventory_recovered_at", None)
        inventory_finalized_at = getattr(order, "inventory_finalized_at", None)
        linked_items = [item for item in items if str(item.get("variant_sku", "") or "").strip()]
        linked_units = sum(int(item.get("quantity", "0") or 0) for item in linked_items)
        if inventory_finalized_at and linked_units:
            finalized_at = DjangoOrmOrderRepository._format_timestamp(inventory_finalized_at)
            return (
                f"Estoque finalizado após entrega: {linked_units} unidade(s) consumiram a reserva operacional do pedido. "
                f"Última finalização em {finalized_at}."
            )
        if inventory_recovered_at and linked_units:
            recovered_at = DjangoOrmOrderRepository._format_timestamp(inventory_recovered_at)
            return (
                f"Estoque devolvido após cancelamento: {linked_units} unidade(s) voltaram para o saldo operacional. "
                f"Última devolução em {recovered_at}."
            )
        if inventory_reserved_at and linked_units:
            reserved_at = DjangoOrmOrderRepository._format_timestamp(inventory_reserved_at)
            return (
                f"Estoque impactado após pagamento: {linked_units} unidade(s) ligadas a {len(linked_items)} item(ns) "
                f"com variante explícita. Última aplicação em {reserved_at}."
            )
        if linked_items:
            return (
                f"Pedido com {len(linked_items)} item(ns) ligados a variante explícita, pronto para visibilidade de estoque "
                "quando a baixa operacional for aplicada."
            )
        return "Pedido ainda sem vínculo explícito suficiente para expor impacto operacional de estoque com segurança."

    def _build_inventory_exception_content(self, *, order: object, items: list[dict[str, object]]) -> str:
        if (
            getattr(order, "inventory_reserved_at", None)
            or getattr(order, "inventory_recovered_at", None)
            or getattr(order, "inventory_finalized_at", None)
        ):
            return ""
        order_status = str(getattr(order, "status", "") or "")
        if order_status in {"canceled", "shipped"}:
            return ""
        linked_items = [item for item in items if str(item.get("variant_sku", "") or "").strip()]
        if not linked_items:
            return "Exceção de estoque: pedido ainda sem vínculo explícito suficiente com variante para validar reserva operacional."
        for item in linked_items:
            sku = str(item.get("variant_sku", "") or "").strip()
            variant = self._get_variant_snapshot(tenant_id=getattr(order, "tenant_id", None), sku=sku)
            if variant is None:
                return f"Exceção de estoque: variante {sku} não pôde ser resolvida no tenant atual."
            product = getattr(variant, "product", None)
            if product is None or not bool(getattr(product, "is_active", False)) or str(getattr(product, "status", "") or "") != "active":
                return f"Exceção de estoque: variante {sku} está ligada a produto indisponível para reserva segura."
            if not bool(getattr(variant, "track_inventory", True)) or bool(getattr(variant, "allow_backorder", False)):
                continue
            quantity = max(1, int(item.get("quantity", "1") or 1))
            free_stock = max(
                int(getattr(variant, "stock", 0) or 0) - int(getattr(variant, "reserved_stock", 0) or 0),
                0,
            )
            if free_stock < quantity:
                return (
                    f"Exceção de estoque: variante {sku} tem apenas {free_stock} unidade(s) livre(s) "
                    f"para {quantity} unidade(s) do pedido."
                )
        return ""

    @staticmethod
    def _build_inventory_exception_guidance(exception_content: str) -> tuple[str, str]:
        content = str(exception_content or "").lower()
        if not content:
            return "", ""
        if "não pôde ser resolvida" in content or "vínculo explícito suficiente" in content:
            return (
                "Revisar vínculo da variante",
                "Confirme o SKU do item e recarregue a ligação com a variante vendável antes de tentar nova evolução do pedido.",
            )
        if "indisponível para reserva segura" in content:
            return (
                "Revisar disponibilidade do produto",
                "Valide se o produto ou a variante ainda devem seguir ativos e só então retome pagamento ou expedição.",
            )
        if "apenas" in content and "livre(s)" in content:
            return (
                "Tratar conflito de estoque",
                "Revise saldo livre, prioridade operacional e eventual contato com o cliente antes de confirmar pagamento ou preparar envio.",
            )
        return (
            "Revisar exceção de estoque",
            "Faça uma checagem manual do vínculo da variante e do saldo operacional antes do próximo avanço do pedido.",
        )

    @staticmethod
    def _build_inventory_exception_marker(*, order: object, inventory_exception_content: str) -> tuple[str, str]:
        under_review_at = getattr(order, "inventory_exception_under_review_at", None)
        resolved_at = getattr(order, "inventory_exception_resolved_at", None)
        if inventory_exception_content and under_review_at:
            reviewed_at = DjangoOrmOrderRepository._format_timestamp(under_review_at)
            return (
                "Exceção em revisão",
                f"Caso já sinalizado para tratamento manual. Última marcação de revisão em {reviewed_at}.",
            )
        if not inventory_exception_content and resolved_at:
            resolution_at = DjangoOrmOrderRepository._format_timestamp(resolved_at)
            return (
                "Exceção resolvida",
                f"Tratamento manual concluído e normalizado na operação em {resolution_at}.",
            )
        return "", ""

    @staticmethod
    def _build_inventory_exception_owner(*, order: object) -> tuple[str, str]:
        owner_label = str(getattr(order, "inventory_exception_owner_label", "") or "").strip()
        if not owner_label:
            return "", ""
        return owner_label, f"Responsável atual pela exceção: {owner_label}."

    @staticmethod
    def _build_inventory_exception_list_state(
        *, inventory_exception_content: str, inventory_exception_marker_label: str, inventory_exception_owner_label: str
    ) -> tuple[str, str]:
        if inventory_exception_marker_label == "Exceção em revisão":
            owner_suffix = f" Responsável: {inventory_exception_owner_label}." if inventory_exception_owner_label else ""
            return "Em revisão", f"Exceção já está em tratamento manual.{owner_suffix}"
        if inventory_exception_marker_label == "Exceção resolvida":
            owner_suffix = f" Último responsável: {inventory_exception_owner_label}." if inventory_exception_owner_label else ""
            return "Resolvida", f"Exceção já foi normalizada pela operação.{owner_suffix}"
        if inventory_exception_content:
            return "Exceção ativa", "Pedido ainda exige tratamento operacional de estoque."
        return "", ""

    @staticmethod
    def _build_inventory_exception_priority(
        *, inventory_exception_content: str, inventory_exception_marker_label: str
    ) -> tuple[str, str]:
        content = str(inventory_exception_content or "").lower()
        marker = str(inventory_exception_marker_label or "").lower()
        if not content and marker == "exceção resolvida":
            return (
                "Baixa prioridade",
                "Exceção já normalizada. Mantenha apenas conferência leve do fechamento operacional.",
            )
        if "apenas" in content and "livre(s)" in content:
            if marker == "exceção em revisão":
                return (
                    "Alta prioridade",
                    "Conflito de estoque ainda ativo e já em tratamento. Priorize definição operacional antes de novo avanço do pedido.",
                )
            return (
                "Alta prioridade",
                "Saldo livre insuficiente para o pedido. Trate esse conflito antes de confirmar pagamento ou liberar expedição.",
            )
        if "indisponível para reserva segura" in content:
            return (
                "Alta prioridade",
                "Produto ou variante indisponível para reserva segura. Revise disponibilidade antes de retomar o fluxo.",
            )
        if "não pôde ser resolvida" in content or "vínculo explícito suficiente" in content:
            if marker == "exceção em revisão":
                return (
                    "Média prioridade",
                    "Vínculo da variante já está em revisão. Normalize o SKU antes de retomar evolução do pedido.",
                )
            return (
                "Média prioridade",
                "Exceção pede revisão de vínculo, mas sem urgência de saldo. Confirme o SKU correto e siga com segurança.",
            )
        if content and marker == "exceção em revisão":
            return (
                "Média prioridade",
                "Exceção operacional já está sendo tratada. Acompanhe a normalização antes do próximo avanço.",
            )
        if content:
            return (
                "Média prioridade",
                "Exceção de estoque exige revisão manual antes de continuar o fluxo do pedido.",
            )
        return "", ""

    @staticmethod
    def _relative_age_label(value: object) -> str:
        if not isinstance(value, datetime):
            return ""
        now = timezone.now()
        compare_value = value if timezone.is_aware(value) else timezone.make_aware(value, timezone.get_current_timezone())
        delta = now - compare_value
        if delta < timedelta(hours=1):
            minutes = max(int(delta.total_seconds() // 60), 1)
            return f"há {minutes} min"
        if delta < timedelta(days=1):
            hours = max(int(delta.total_seconds() // 3600), 1)
            return f"há {hours} h"
        days = max(delta.days, 1)
        return f"há {days} dia(s)"

    @staticmethod
    def _build_inventory_exception_aging(
        *, order: object, inventory_exception_content: str, inventory_exception_marker_label: str
    ) -> tuple[str, str]:
        marker = str(inventory_exception_marker_label or "").lower()
        content = str(inventory_exception_content or "").strip()
        under_review_at = getattr(order, "inventory_exception_under_review_at", None)
        resolved_at = getattr(order, "inventory_exception_resolved_at", None)
        updated_at = getattr(order, "updated_at", None)

        if marker == "exceção resolvida" and resolved_at:
            relative_age = DjangoOrmOrderRepository._relative_age_label(resolved_at)
            return (
                "Resolvida recentemente",
                f"Exceção resolvida {relative_age}. Mantenha apenas conferência leve e sem urgência adicional.",
            )
        if marker == "exceção em revisão" and under_review_at:
            relative_age = DjangoOrmOrderRepository._relative_age_label(under_review_at)
            if isinstance(under_review_at, datetime):
                compare_value = under_review_at if timezone.is_aware(under_review_at) else timezone.make_aware(
                    under_review_at, timezone.get_current_timezone()
                )
                if timezone.now() - compare_value >= timedelta(days=2):
                    return (
                        "Revisão parada",
                        f"Exceção está em revisão {relative_age}. Vale reavaliar prioridade, owner e fechamento manual.",
                    )
            return (
                "Revisão recente",
                f"Exceção entrou em revisão {relative_age} e ainda segue dentro de uma janela operacional recente.",
            )
        if content and updated_at:
            relative_age = DjangoOrmOrderRepository._relative_age_label(updated_at)
            if isinstance(updated_at, datetime):
                compare_value = updated_at if timezone.is_aware(updated_at) else timezone.make_aware(
                    updated_at, timezone.get_current_timezone()
                )
                if timezone.now() - compare_value >= timedelta(days=2):
                    return (
                        "Exceção envelhecida",
                        f"Exceção ativa {relative_age}. Priorize tratamento para evitar drift operacional maior.",
                    )
            return (
                "Exceção recente",
                f"Exceção ativa {relative_age}. Continue acompanhamento próximo até revisão ou resolução.",
            )
        return "", ""

    @staticmethod
    def _build_activity_items(
        *,
        order: object,
        updated_at: str,
        payment_status: str,
        shipping_status: str,
        fulfillment_status_label: str,
        inventory_exception_content: str,
        inventory_exception_guidance_label: str,
        inventory_exception_guidance_helper: str,
        inventory_exception_marker_label: str,
        inventory_exception_marker_helper: str,
    ) -> list[dict[str, object]]:
        derived_items = [
            {
                "title": "Snapshot persistido sincronizado",
                "description": f"Pedido carregado com pagamento {payment_status.lower()} e envio em estado {shipping_status.lower()}.",
                "timestamp": updated_at,
                "badge_label": "Pedido",
                "badge_variant": "info",
            },
            {
                "title": "Fila operacional atualizada",
                "description": f"Status de atendimento registrado como {fulfillment_status_label.lower()}.",
                "timestamp": updated_at,
                "badge_label": "Operação",
                "badge_variant": "warning" if "aguard" in fulfillment_status_label.lower() else "success",
            },
        ]
        if inventory_exception_content:
            derived_items.insert(
                0,
                {
                    "title": "Exceção de estoque identificada",
                    "description": inventory_exception_content,
                    "timestamp": updated_at,
                    "badge_label": "Estoque",
                    "badge_variant": "warning",
                },
            )
            if inventory_exception_guidance_label and inventory_exception_guidance_helper:
                derived_items.insert(
                    1,
                    {
                        "title": inventory_exception_guidance_label,
                        "description": inventory_exception_guidance_helper,
                        "timestamp": updated_at,
                        "badge_label": "Próximo passo",
                        "badge_variant": "info",
                    },
                )
        try:
            history_items = list(getattr(order, "status_history").all())
        except Exception:
            history_items = []
        if inventory_exception_marker_label and inventory_exception_marker_helper:
            derived_items.insert(
                0,
                {
                    "title": inventory_exception_marker_label,
                    "description": inventory_exception_marker_helper,
                    "timestamp": updated_at,
                    "badge_label": "Estoque",
                    "badge_variant": "success" if "resolvida" in inventory_exception_marker_label.lower() else "warning",
                },
            )
        if not history_items:
            return derived_items
        timeline_items = [
            {
                "title": str(getattr(item, "title", "") or "Atualização operacional"),
                "description": DjangoOrmOrderRepository._history_description(item),
                "timestamp": DjangoOrmOrderRepository._format_timestamp(getattr(item, "created_at", None)),
                "badge_label": str(getattr(item, "badge_label", "") or "Operação"),
                "badge_variant": str(getattr(item, "badge_variant", "") or "info"),
            }
            for item in history_items[:3]
        ]
        timeline_items.extend(derived_items)
        return timeline_items[:4]

    @staticmethod
    def _build_next_step_guidance(
        *,
        status: str,
        payment_status: str,
        shipping_status: str,
        fulfillment_status_label: str,
    ) -> tuple[str, str, str]:
        lowered_payment = payment_status.lower()
        lowered_shipping = shipping_status.lower()
        lowered_fulfillment = fulfillment_status_label.lower()

        if status == "canceled":
            return (
                "Pedido encerrado",
                "Nenhuma nova ação operacional é necessária. Mantenha apenas acompanhamento de atendimento, se houver contato do cliente.",
                "Cancelamento concluído; novas mudanças exigem revisão manual do pedido.",
            )
        if status == "shipped" or "trânsito" in lowered_shipping:
            return (
                "Acompanhar transporte",
                "Pedido já saiu da operação interna. O próximo passo é monitorar rastreio e tratar exceções de entrega, se aparecerem.",
                "Cancelamento simples fica bloqueado depois do envio; trate qualquer exceção com fluxo operacional específico.",
            )
        if "aguard" in lowered_payment or "pix" in lowered_payment and "confirm" not in lowered_payment:
            return (
                "Confirmar pagamento",
                "Aguarde a confirmação financeira antes de liberar separação, expedição ou qualquer comunicação de envio.",
                "Enquanto o pagamento estiver pendente, mantenha o pedido fora da fila de despacho.",
            )
        if "separ" in lowered_fulfillment or "picking" in lowered_fulfillment or status == "paid":
            return (
                "Separar e preparar envio",
                "Pagamento já confirmado. Priorize picking, conferência e atualização da operação para trânsito assim que o pacote estiver pronto.",
                "Se faltar estoque ou houver divergência, pause a expedição antes de avançar o status.",
            )
        if "conclu" in lowered_fulfillment:
            return (
                "Confirmar encerramento operacional",
                "A operação interna já foi concluída. Verifique se a comunicação final e o acompanhamento pós-entrega estão consistentes.",
                "Evite novas mudanças de status sem revisar primeiro o histórico recente do pedido.",
            )
        return (
            "Revisar próximo passo operacional",
            "Confira pagamento, expedição e histórico recente para decidir o próximo avanço do pedido com segurança.",
            "Quando houver dúvida no estado atual, prefira revisar a timeline antes de aplicar uma nova ação.",
        )

    @staticmethod
    def _history_description(item: object) -> str:
        base_description = str(getattr(item, "description", "") or "").strip()
        extras: list[str] = []
        source_label = str(getattr(item, "source_label", "") or "").strip()
        actor_label = str(getattr(item, "actor_label", "") or "").strip()
        if source_label:
            extras.append(f"Origem: {source_label}.")
        if actor_label:
            extras.append(f"Responsável: {actor_label}.")
        if not extras:
            return base_description
        if not base_description:
            return " ".join(extras)
        return f"{base_description} {' '.join(extras)}"


def _fallback_order(order_number: str) -> dict[str, object]:
    normalized = order_number.lstrip("#")
    return {
        "order_number": normalized,
        "customer": "Cliente não encontrado",
        "status": "pending",
        "order_status_label": "Pendente",
        "fulfillment_status_label": "Aguardando definição",
        "fulfillment_status_variant": "warning",
        "payment_status": "Indisponível",
        "shipping_status": "Indisponível",
        "updated_at": "agora",
        "summary_content": "Pedido ainda sem integração com dados reais; usando fallback seguro de apresentação.",
        "customer_content": "Sem dados do cliente disponíveis no adapter inicial.",
        "payment_content": "Pagamento ainda não conectado ao fluxo real.",
        "shipping_content": "Entrega ainda não conectada ao fluxo real.",
        "notes_content": "Registro temporário para estabelecer o padrão de migração real com page templates oficiais.",
        "subtotal": "R$ 0,00",
        "shipping": "R$ 0,00",
        "discount": "",
        "installments": "",
        "total": "R$ 0,00",
        "next_step_label": "Revisar integração do pedido",
        "next_step_helper": "Enquanto o pedido estiver em fallback, confirme manualmente pagamento, envio e operação antes de qualquer ação.",
        "blocked_action_guidance": "Sem trilha persistida suficiente para orientar bloqueios reais; mantenha revisão operacional manual.",
        "order_items": [],
        "activity_items": [],
    }


@dataclass
class AdminOrderQueryService:
    orm_repository: OrderReadRepository
    fallback_repository: OrderReadRepository

    @staticmethod
    def _inventory_exception_sort_key(
        order: dict[str, object],
        original_position: int,
        *,
        owner_workload_counts: dict[str, int] | None = None,
        owner_aged_counts: dict[str, int] | None = None,
    ) -> tuple[int, int, int, int, str, int, int]:
        state_label = str(order.get("inventory_exception_list_label", "") or "")
        priority_label = str(order.get("inventory_exception_priority_label", "") or "")
        aging_label = str(order.get("inventory_exception_aging_label", "") or "")
        owner_label = str(order.get("inventory_exception_owner_label", "") or "").strip()

        state_rank = {
            "Exceção ativa": 0,
            "Em revisão": 1,
            "Resolvida": 2,
        }.get(state_label, 3)
        priority_rank = {
            "Alta prioridade": 0,
            "Média prioridade": 1,
            "Baixa prioridade": 2,
        }.get(priority_label, 3)
        aging_rank = {
            "Exceção envelhecida": 0,
            "Revisão parada": 1,
            "Exceção recente": 2,
            "Revisão recente": 3,
            "Resolvida recentemente": 4,
        }.get(aging_label, 5)
        owner_rank = 0 if state_label in {"Exceção ativa", "Em revisão"} and not owner_label else 1
        owner_group = owner_label.lower() if state_label in {"Exceção ativa", "Em revisão"} and owner_label else ""
        owner_load_rank = 0
        owner_aged_rank = 0
        if owner_label and state_label in {"Exceção ativa", "Em revisão"}:
            owner_load_rank = -(owner_workload_counts or {}).get(owner_label, 0)
            owner_aged_rank = -(owner_aged_counts or {}).get(owner_label, 0)

        return (state_rank, owner_rank, owner_load_rank, owner_aged_rank, owner_group, priority_rank, aging_rank, original_position)

    def _sort_orders_for_inventory_exception_queue(self, orders: list[dict[str, object]]) -> list[dict[str, object]]:
        owner_workload_counts, _ = self._get_inventory_exception_owner_workload_counts(orders)
        owner_aged_counts = self._get_inventory_exception_owner_aged_counts(orders)
        return [
            order
            for _, order in sorted(
                enumerate(orders),
                key=lambda item: self._inventory_exception_sort_key(
                    item[1],
                    item[0],
                    owner_workload_counts=owner_workload_counts,
                    owner_aged_counts=owner_aged_counts,
                ),
            )
        ]

    @staticmethod
    def _get_inventory_exception_owner_workload_counts(orders: list[dict[str, object]]) -> tuple[dict[str, int], int]:
        owner_counts: dict[str, int] = {}
        unassigned_count = 0
        for order in orders:
            state_label = str(order.get("inventory_exception_list_label", "") or "")
            if state_label not in {"Exceção ativa", "Em revisão"}:
                continue
            owner_label = str(order.get("inventory_exception_owner_label", "") or "").strip()
            if owner_label:
                owner_counts[owner_label] = owner_counts.get(owner_label, 0) + 1
            else:
                unassigned_count += 1
        return owner_counts, unassigned_count

    def _attach_inventory_exception_owner_workload(self, orders: list[dict[str, object]]) -> list[dict[str, object]]:
        owner_counts, unassigned_count = self._get_inventory_exception_owner_workload_counts(orders)
        enriched_orders: list[dict[str, object]] = []
        for order in orders:
            state_label = str(order.get("inventory_exception_list_label", "") or "")
            owner_label = str(order.get("inventory_exception_owner_label", "") or "").strip()
            workload_label = ""
            workload_helper = ""
            if state_label in {"Exceção ativa", "Em revisão"}:
                if owner_label:
                    owner_load = owner_counts.get(owner_label, 0)
                    workload_label = f"{owner_load} caso(s) aberto(s)"
                    workload_helper = f"{owner_label} conduz {owner_load} caso(s) aberto(s) nesta fila."
                elif unassigned_count:
                    workload_label = "Sem responsável"
                    workload_helper = f"{unassigned_count} pedido(s) aberto(s) ainda sem responsável na fila."

            enriched_order = {
                **order,
                "inventory_exception_owner_workload_label": workload_label,
                "inventory_exception_owner_workload_helper": workload_helper,
            }
            enriched_orders.append(enriched_order)
        return enriched_orders

    @staticmethod
    def _get_inventory_exception_owner_aged_counts(orders: list[dict[str, object]]) -> dict[str, int]:
        aged_labels = {"Exceção envelhecida", "Revisão parada"}
        owner_aged_counts: dict[str, int] = {}
        for order in orders:
            owner_label = str(order.get("inventory_exception_owner_label", "") or "").strip()
            aging_label = str(order.get("inventory_exception_aging_label", "") or "")
            state_label = str(order.get("inventory_exception_list_label", "") or "")
            if not owner_label or state_label not in {"Exceção ativa", "Em revisão"} or aging_label not in aged_labels:
                continue
            owner_aged_counts[owner_label] = owner_aged_counts.get(owner_label, 0) + 1
        return owner_aged_counts

    def using_persisted_source(self) -> bool:
        try:
            return bool(self.orm_repository.list_orders())
        except Exception:
            return False

    def get_operational_visibility_note(self) -> str:
        try:
            orders = self.orm_repository.list_orders()
        except Exception:
            orders = []
        if not orders:
            return "Visibilidade operacional: listagem ainda depende de fallback de apresentação."
        explicit_count = sum(1 for order in orders if order.get("customer_linkage_mode") == "explicit")
        fallback_count = sum(1 for order in orders if order.get("customer_linkage_mode") != "explicit")
        inventory_count = sum(1 for order in orders if str(order.get("inventory_visibility_content", "")).startswith("Estoque impactado"))
        inventory_exception_count = sum(1 for order in orders if str(order.get("inventory_exception_content", "") or "").strip())
        inventory_exception_review_count = sum(
            1 for order in orders if str(order.get("inventory_exception_marker_label", "") or "").strip() == "Exceção em revisão"
        )
        inventory_exception_resolved_count = sum(
            1 for order in orders if str(order.get("inventory_exception_marker_label", "") or "").strip() == "Exceção resolvida"
        )
        return (
            "Visibilidade operacional: "
            f"{explicit_count} pedido(s) com vínculo explícito `Order.customer` e "
            f"{fallback_count} ainda resolvido(s) por snapshot/fallback. "
            f"Impacto de estoque já visível em {inventory_count} pedido(s). "
            f"Exceções de estoque visíveis em {inventory_exception_count} pedido(s). "
            f"{inventory_exception_review_count} em revisão e {inventory_exception_resolved_count} já resolvida(s)."
        )

    def get_inventory_exception_backlog_summary(self) -> str:
        try:
            orders = self.orm_repository.list_orders()
        except Exception:
            orders = []
        if not orders:
            return "Backlog de exceções: indisponível enquanto a listagem depender de fallback de apresentação."

        active_count = sum(1 for order in orders if str(order.get("inventory_exception_list_label", "") or "") == "Exceção ativa")
        review_count = sum(1 for order in orders if str(order.get("inventory_exception_list_label", "") or "") == "Em revisão")
        resolved_count = sum(1 for order in orders if str(order.get("inventory_exception_list_label", "") or "") == "Resolvida")
        high_priority_count = sum(
            1 for order in orders if str(order.get("inventory_exception_priority_label", "") or "") == "Alta prioridade"
        )
        medium_priority_count = sum(
            1 for order in orders if str(order.get("inventory_exception_priority_label", "") or "") == "Média prioridade"
        )
        low_priority_count = sum(
            1 for order in orders if str(order.get("inventory_exception_priority_label", "") or "") == "Baixa prioridade"
        )
        owner_count = sum(1 for order in orders if str(order.get("inventory_exception_owner_label", "") or "").strip())
        aging_count = sum(
            1
            for order in orders
            if str(order.get("inventory_exception_aging_label", "") or "") in {"Exceção envelhecida", "Revisão parada"}
        )
        owner_workload, unassigned_count = self._get_inventory_exception_owner_workload_counts(orders)
        owner_aged_counts = self._get_inventory_exception_owner_aged_counts(orders)
        owner_segments = [
            f"{owner_label} ({count})"
            for owner_label, count in sorted(owner_workload.items(), key=lambda item: (-item[1], item[0].lower()))
        ]
        owner_aged_segments = [
            f"{owner_label} ({count} envelhecido(s))"
            for owner_label, count in sorted(owner_aged_counts.items(), key=lambda item: (-item[1], item[0].lower()))
        ]
        owner_summary = (
            f"Carga atual por responsável: {', '.join(owner_segments[:3])}."
            if owner_segments
            else "Carga atual por responsável: nenhum responsável visível nos casos abertos."
        )
        owner_aged_summary = (
            f" Casos envelhecidos por responsável: {', '.join(owner_aged_segments[:3])}."
            if owner_aged_segments
            else ""
        )
        unassigned_summary = (
            f" {unassigned_count} pedido(s) aberto(s) ainda sem responsável."
            if unassigned_count
            else ""
        )

        return (
            "Backlog de exceções: "
            f"{active_count} ativa(s), {review_count} em revisão e {resolved_count} resolvida(s). "
            f"Prioridade atual: {high_priority_count} alta, {medium_priority_count} média e {low_priority_count} baixa. "
            f"Responsável já visível em {owner_count} pedido(s). "
            f"Casos envelhecidos visíveis em {aging_count} pedido(s). "
            f"{owner_summary}{owner_aged_summary}{unassigned_summary}"
        )

    @staticmethod
    def get_inventory_exception_quick_filter_options() -> list[dict[str, str]]:
        return [dict(option) for option in INVENTORY_EXCEPTION_QUICK_FILTER_OPTIONS]

    @staticmethod
    def filter_orders_by_inventory_exception_state(
        orders: list[dict[str, object]], quick_filter: str
    ) -> list[dict[str, object]]:
        normalized = str(quick_filter or "").strip().lower()
        if normalized == "active":
            return [order for order in orders if str(order.get("inventory_exception_list_label", "") or "") == "Exceção ativa"]
        if normalized == "review":
            return [order for order in orders if str(order.get("inventory_exception_list_label", "") or "") == "Em revisão"]
        if normalized == "resolved":
            return [order for order in orders if str(order.get("inventory_exception_list_label", "") or "") == "Resolvida"]
        if normalized == "high_priority":
            return [order for order in orders if str(order.get("inventory_exception_priority_label", "") or "") == "Alta prioridade"]
        if normalized == "medium_priority":
            return [order for order in orders if str(order.get("inventory_exception_priority_label", "") or "") == "Média prioridade"]
        if normalized == "low_priority":
            return [order for order in orders if str(order.get("inventory_exception_priority_label", "") or "") == "Baixa prioridade"]
        if normalized == "unassigned":
            return [
                order
                for order in orders
                if str(order.get("inventory_exception_list_label", "") or "") in {"Exceção ativa", "Em revisão"}
                and not str(order.get("inventory_exception_owner_label", "") or "").strip()
            ]
        if normalized == "assigned":
            return [
                order
                for order in orders
                if str(order.get("inventory_exception_list_label", "") or "") in {"Exceção ativa", "Em revisão"}
                and str(order.get("inventory_exception_owner_label", "") or "").strip()
            ]
        return orders

    @staticmethod
    def get_inventory_exception_quick_filter_context(quick_filter: str) -> tuple[str, str]:
        normalized = str(quick_filter or "").strip().lower()
        if normalized == "active":
            return (
                "Filtro rápido de exceção",
                "Mostrando pedidos com exceção de estoque ainda ativa e exigindo tratamento operacional.",
            )
        if normalized == "review":
            return (
                "Filtro rápido de exceção",
                "Mostrando pedidos com exceção já marcada em revisão pela operação.",
            )
        if normalized == "resolved":
            return (
                "Filtro rápido de exceção",
                "Mostrando pedidos com exceção já normalizada e marcada como resolvida.",
            )
        if normalized == "high_priority":
            return (
                "Filtro rápido de prioridade",
                "Mostrando pedidos com exceção de estoque em alta prioridade operacional.",
            )
        if normalized == "medium_priority":
            return (
                "Filtro rápido de prioridade",
                "Mostrando pedidos com exceção de estoque em média prioridade operacional.",
            )
        if normalized == "low_priority":
            return (
                "Filtro rápido de prioridade",
                "Mostrando pedidos com exceção já estável ou de baixa urgência operacional.",
            )
        if normalized == "unassigned":
            return (
                "Filtro rápido de ownership",
                "Mostrando pedidos com exceção aberta que ainda não receberam responsável operacional.",
            )
        if normalized == "assigned":
            return (
                "Filtro rápido de ownership",
                "Mostrando pedidos com exceção aberta que já têm responsável operacional visível.",
            )
        return (
            "Filtros",
            "Busque pedidos, refine o status e foque rapidamente em exceções de estoque.",
        )

    @staticmethod
    def get_inventory_exception_quick_filter_label(quick_filter: str) -> str:
        normalized = str(quick_filter or "").strip().lower()
        for option in INVENTORY_EXCEPTION_QUICK_FILTER_OPTIONS:
            if option["value"] == normalized:
                return str(option["label"])
        return ""

    @staticmethod
    def get_inventory_exception_empty_state(quick_filter: str, search_value: str = "") -> tuple[str, str]:
        normalized = str(quick_filter or "").strip().lower()
        search_term = str(search_value or "").strip()
        search_hint = f' Busca atual: "{search_term}".' if search_term else ""
        if normalized == "active":
            return (
                "Nenhuma exceção ativa agora",
                "A fila não tem pedidos com exceção de estoque ainda aberta neste momento." + search_hint,
            )
        if normalized == "review":
            return (
                "Nenhuma exceção em revisão",
                "Não há pedidos com exceção de estoque atualmente marcados em revisão operacional." + search_hint,
            )
        if normalized == "resolved":
            return (
                "Nenhuma exceção resolvida nesta visão",
                "Não encontramos pedidos com exceção já normalizada dentro do recorte atual." + search_hint,
            )
        if normalized == "high_priority":
            return (
                "Nenhuma exceção de alta prioridade",
                "Não há pedidos com exceção de estoque exigindo tratamento prioritário neste momento." + search_hint,
            )
        if normalized == "medium_priority":
            return (
                "Nenhuma exceção de média prioridade",
                "Não encontramos pedidos com exceção de estoque em acompanhamento de prioridade intermediária nesta visão." + search_hint,
            )
        if normalized == "low_priority":
            return (
                "Nenhuma exceção de baixa prioridade",
                "Não há pedidos com exceção já estabilizada ou de baixa urgência no recorte atual." + search_hint,
            )
        if normalized == "unassigned":
            return (
                "Nenhuma exceção sem responsável",
                "Não há pedidos com exceção aberta sem responsável operacional visível neste momento." + search_hint,
            )
        if normalized == "assigned":
            return (
                "Nenhuma exceção com responsável",
                "Não encontramos pedidos com exceção aberta já atribuídos a um responsável operacional nesta visão." + search_hint,
            )
        return (
            "Nenhum pedido encontrado",
            "Ajuste os filtros para localizar pedidos ou aguarde novas compras." + search_hint,
        )

    def get_order_operational_visibility(self, order_number: str) -> str:
        order = self.get_order(order_number)
        mode = order.get("customer_linkage_mode")
        inventory_note = str(order.get("inventory_visibility_content", "") or "")
        inventory_exception_note = str(order.get("inventory_exception_content", "") or "")
        inventory_exception_marker = str(order.get("inventory_exception_marker_helper", "") or "")
        if mode == "explicit":
            return (
                "Visibilidade operacional: cliente resolvido por vínculo explícito `Order.customer`. "
                f"{inventory_note} {inventory_exception_note} {inventory_exception_marker}"
            )
        if mode == "fallback":
            return (
                "Visibilidade operacional: cliente resolvido por snapshot/fallback (`customer_email`). "
                f"{inventory_note} {inventory_exception_note} {inventory_exception_marker}"
            )
        return f"Visibilidade operacional: pedido ainda fora da trilha persistida principal. {inventory_note} {inventory_exception_note} {inventory_exception_marker}"

    def list_orders(self) -> list[dict[str, object]]:
        real_orders = self.orm_repository.list_orders()
        if real_orders:
            return self._attach_inventory_exception_owner_workload(
                self._sort_orders_for_inventory_exception_queue(real_orders)
            )
        return self._attach_inventory_exception_owner_workload(
            self._sort_orders_for_inventory_exception_queue(self.fallback_repository.list_orders())
        )

    def get_order(self, order_number: str) -> dict[str, object]:
        real_order = self.orm_repository.get_order(order_number)
        if real_order:
            return real_order

        fallback_order = self.fallback_repository.get_order(order_number)
        if fallback_order:
            return fallback_order

        return _fallback_order(order_number)


admin_order_queries = AdminOrderQueryService(
    orm_repository=DjangoOrmOrderRepository(),
    fallback_repository=FallbackOrderRepository(),
)
