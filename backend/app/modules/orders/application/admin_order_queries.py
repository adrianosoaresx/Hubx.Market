from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
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
        except Exception:
            self.order_model = None
            return

        self.order_model = getattr(order_models, "Order", None)

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
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_names.issubset(set(tables))

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
                "price": DjangoOrmOrderRepository._money_value(getattr(item, "price_snapshot", None)),
                "quantity": str(getattr(item, "quantity", 1) or 1),
                "quantity_readonly": bool(getattr(item, "quantity_readonly", True)),
            }
            for item in items
        ]

    @staticmethod
    def _build_activity_items(*, order: object, updated_at: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> list[dict[str, object]]:
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
        try:
            history_items = list(getattr(order, "status_history").all())
        except Exception:
            history_items = []
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
        return (
            "Visibilidade operacional: "
            f"{explicit_count} pedido(s) com vínculo explícito `Order.customer` e "
            f"{fallback_count} ainda resolvido(s) por snapshot/fallback."
        )

    def get_order_operational_visibility(self, order_number: str) -> str:
        order = self.get_order(order_number)
        mode = order.get("customer_linkage_mode")
        if mode == "explicit":
            return "Visibilidade operacional: cliente resolvido por vínculo explícito `Order.customer`."
        if mode == "fallback":
            return "Visibilidade operacional: cliente resolvido por snapshot/fallback (`customer_email`)."
        return "Visibilidade operacional: pedido ainda fora da trilha persistida principal."

    def list_orders(self) -> list[dict[str, object]]:
        real_orders = self.orm_repository.list_orders()
        return real_orders or self.fallback_repository.list_orders()

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
