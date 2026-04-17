from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.utils import timezone


def _customer_order_status_options() -> list[dict[str, str]]:
    return [
        {"value": "paid", "label": "Pago"},
        {"value": "processing", "label": "Em preparação"},
        {"value": "shipped", "label": "Enviado"},
    ]


def _fallback_customer_order_fixtures() -> list[dict[str, object]]:
    return [
        {
            "order_number": "1048",
            "status": "paid",
            "order_status_label": "Pago",
            "order_status_variant": "paid",
            "payment_status": "Confirmado",
            "shipping_status": "Preparando envio",
            "updated_at": "12/04/2026",
            "summary_content": "Pedido confirmado com pagamento aprovado e envio em preparação.",
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
                    "description": "Seu pagamento foi aprovado e o pedido entrou na fila de separação.",
                    "timestamp": "há 4 min",
                    "badge_label": "Pagamento",
                    "badge_variant": "paid",
                },
                {
                    "title": "Separação iniciada",
                    "description": "Nossa equipe já começou a preparar os itens para envio.",
                    "timestamp": "há 12 min",
                    "badge_label": "Pedido",
                    "badge_variant": "info",
                },
            ],
        },
        {
            "order_number": "1041",
            "status": "shipped",
            "order_status_label": "Enviado",
            "order_status_variant": "shipped",
            "payment_status": "Confirmado",
            "shipping_status": "Em trânsito",
            "updated_at": "02/04/2026",
            "summary_content": "Pedido coletado pela transportadora e em rota de entrega.",
            "subtotal": "R$ 159,90",
            "shipping": "R$ 19,90",
            "discount": "-R$ 10,00",
            "installments": "",
            "total": "R$ 169,80",
            "order_items": [
                {
                    "title": "Camiseta Hubx Performance",
                    "subtitle": "Branca · M",
                    "meta": "SKU TSHIRT-010-WHT-M",
                    "price": "R$ 129,90",
                    "quantity": "1",
                    "quantity_readonly": True,
                },
                {
                    "title": "Boné Hubx Active",
                    "subtitle": "Preto · Único",
                    "meta": "SKU CAP-001-BLK-U",
                    "price": "R$ 30,00",
                    "quantity": "1",
                    "quantity_readonly": True,
                },
            ],
            "activity_items": [
                {
                    "title": "Pedido em trânsito",
                    "description": "A transportadora atualizou o envio e o pacote está a caminho.",
                    "timestamp": "há 1 dia",
                    "badge_label": "Entrega",
                    "badge_variant": "shipped",
                }
            ],
        },
        {
            "order_number": "1033",
            "status": "processing",
            "order_status_label": "Em preparação",
            "order_status_variant": "warning",
            "payment_status": "Confirmado",
            "shipping_status": "Separando itens",
            "updated_at": "28/03/2026",
            "summary_content": "Pedido aprovado e aguardando conclusão da separação no centro de distribuição.",
            "subtotal": "R$ 89,90",
            "shipping": "R$ 14,90",
            "discount": "",
            "installments": "",
            "total": "R$ 104,80",
            "order_items": [
                {
                    "title": "Garrafa Hubx Move",
                    "subtitle": "Azul · 750ml",
                    "meta": "SKU BOT-220-BLU-750",
                    "price": "R$ 89,90",
                    "quantity": "1",
                    "quantity_readonly": True,
                }
            ],
            "activity_items": [
                {
                    "title": "Pedido em preparação",
                    "description": "Estamos separando seus itens para o envio.",
                    "timestamp": "há 2 dias",
                    "badge_label": "Pedido",
                    "badge_variant": "warning",
                }
            ],
        },
    ]


def _fallback_address_fixtures() -> list[dict[str, object]]:
    return [
        {
            "title": "Casa",
            "subtitle": "Entrega principal",
            "content": "Rua das Laranjeiras, 100 · Apto 42 · Bela Vista · São Paulo/SP",
            "footer": "CEP 01310-100",
            "edit_href": "#edit-home-address",
            "remove_href": "#remove-home-address",
        },
        {
            "title": "Escritório",
            "subtitle": "Entrega alternativa",
            "content": "Av. Paulista, 900 · 12º andar · São Paulo/SP",
            "footer": "CEP 01310-200",
            "edit_href": "#edit-office-address",
            "remove_href": "#remove-office-address",
        },
    ]


class AccountProfileReadRepository(Protocol):
    def get_primary_profile(self) -> dict[str, object] | None:
        ...


class CustomerAreaReadRepository(Protocol):
    def list_orders(self, profile: dict[str, object]) -> list[dict[str, object]]:
        ...

    def get_order(self, profile: dict[str, object], order_number: str) -> dict[str, object] | None:
        ...

    def get_addresses(self, profile: dict[str, object]) -> list[dict[str, object]]:
        ...


class DjangoOrmAccountProfileRepository:
    def __init__(self) -> None:
        try:
            from app.modules.accounts import models as account_models
        except Exception:
            self.profile_model = None
            return

        self.profile_model = getattr(account_models, "AccountProfile", None)

    def is_ready(self) -> bool:
        if self.profile_model is None:
            return False
        try:
            table_name = self.profile_model._meta.db_table
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_name in set(tables)

    def get_primary_profile(self) -> dict[str, object] | None:
        if not self.is_ready():
            return None
        try:
            profile = self.profile_model._default_manager.filter(is_active=True).order_by("-updated_at", "-id").first()
        except Exception:
            return None
        if not profile:
            return None
        return {
            "tenant_id": getattr(profile, "tenant_id", None),
            "email": str(getattr(profile, "email", "") or ""),
            "first_name": str(getattr(profile, "first_name", "") or ""),
            "last_name": str(getattr(profile, "last_name", "") or ""),
            "phone": str(getattr(profile, "phone", "") or ""),
            "newsletter_opt_in": bool(getattr(profile, "newsletter_opt_in", False)),
            "order_updates_opt_in": bool(getattr(profile, "order_updates_opt_in", True)),
        }


class DjangoOrmCustomerAreaRepository:
    def __init__(self) -> None:
        try:
            from app.modules.customers import models as customer_models
            from app.modules.orders import models as order_models
        except Exception:
            self.customer_model = None
            self.customer_address_model = None
            self.order_model = None
            return

        self.customer_model = getattr(customer_models, "Customer", None)
        self.customer_address_model = getattr(customer_models, "CustomerAddress", None)
        self.order_model = getattr(order_models, "Order", None)

    def is_ready(self) -> bool:
        try:
            table_names = {
                self.customer_model._meta.db_table,
                self.customer_address_model._meta.db_table,
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

    def list_orders(self, profile: dict[str, object]) -> list[dict[str, object]]:
        if not self.is_ready():
            return []
        queryset = self._orders_queryset(profile)
        if queryset is None:
            return []
        return [self._serialize_order(order) for order in queryset]

    def get_order(self, profile: dict[str, object], order_number: str) -> dict[str, object] | None:
        if not self.is_ready():
            return None
        queryset = self._orders_queryset(profile)
        if queryset is None:
            return None
        try:
            order = queryset.filter(number=order_number.lstrip("#")).first()
        except Exception:
            return None
        if not order:
            return None
        return self._serialize_order(order)

    def get_addresses(self, profile: dict[str, object]) -> list[dict[str, object]]:
        if not self.is_ready():
            return []
        customer = self._resolve_customer(profile)
        if customer is None:
            return []
        try:
            addresses = list(getattr(customer, "addresses").all())
        except Exception:
            return []
        return [self._serialize_address(address) for address in addresses]

    def _orders_queryset(self, profile: dict[str, object]):
        tenant_id = profile.get("tenant_id")
        email = str(profile.get("email") or "").strip()
        if not tenant_id or not email:
            return None
        try:
            return (
                self.order_model._default_manager.filter(tenant_id=tenant_id, customer_email=email)
                .prefetch_related("items")
                .order_by("-updated_at", "-id")
            )
        except Exception:
            return None

    def _resolve_customer(self, profile: dict[str, object]):
        tenant_id = profile.get("tenant_id")
        email = str(profile.get("email") or "").strip()
        if not tenant_id or not email:
            return None
        try:
            return (
                self.customer_model._default_manager.filter(tenant_id=tenant_id, email=email)
                .prefetch_related("addresses")
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return None

    def _serialize_order(self, order: object) -> dict[str, object]:
        status = self._string_value(getattr(order, "status", None), default="processing")
        status_map = {
            "paid": ("Pago", "paid"),
            "pending": ("Pendente", "warning"),
            "shipped": ("Enviado", "shipped"),
            "canceled": ("Cancelado", "danger"),
        }
        order_status_label, order_status_variant = status_map.get(status, ("Em preparação", "warning"))
        updated_at = self._format_timestamp(getattr(order, "updated_at", None))
        payment_status = self._string_value(getattr(order, "payment_status", None), default="Indisponível")
        shipping_status = self._string_value(getattr(order, "shipping_status", None), default="Indisponível")
        fulfillment_status_label = self._string_value(
            getattr(order, "fulfillment_status_label", None),
            default="Em preparação",
        )
        shipping_address_summary = self._string_value(
            getattr(order, "shipping_address_summary", None),
            default="Endereço de entrega indisponível.",
        )
        notes_content = self._string_value(
            getattr(order, "notes_content", None),
            default="Sem observações adicionais para este pedido.",
        )
        items = self._serialize_items(order)

        return {
            "order_number": self._string_value(getattr(order, "number", None), default="0000"),
            "status": "processing" if status == "pending" else status,
            "order_status_label": order_status_label,
            "order_status_variant": order_status_variant,
            "payment_status": payment_status,
            "shipping_status": shipping_status,
            "updated_at": updated_at,
            "summary_content": (
                f"Pedido #{getattr(order, 'number', '0000')} com pagamento {payment_status.lower()} "
                f"e andamento logístico {shipping_status.lower()}."
            ),
            "page_meta": f"Entrega em {shipping_address_summary}",
            "subtotal": self._money_value(getattr(order, "subtotal", None)),
            "shipping": self._money_value(getattr(order, "shipping_total", None)),
            "discount": self._money_value(getattr(order, "discount_total", None), allow_empty=True),
            "installments": self._string_value(getattr(order, "installments_summary", None), default=""),
            "total": self._money_value(getattr(order, "total", None)),
            "summary_note": notes_content,
            "order_items": items,
            "activity_items": [
                {
                    "title": "Pedido sincronizado",
                    "description": f"Status operacional atual: {fulfillment_status_label.lower()}.",
                    "timestamp": updated_at,
                    "badge_label": "Pedido",
                    "badge_variant": "info",
                },
                {
                    "title": "Entrega monitorada",
                    "description": f"Última atualização de envio: {shipping_status.lower()}.",
                    "timestamp": updated_at,
                    "badge_label": "Entrega",
                    "badge_variant": order_status_variant,
                },
            ],
        }

    def _serialize_address(self, address: object) -> dict[str, object]:
        label = self._string_value(getattr(address, "label", None), default="Endereço")
        recipient_name = self._string_value(getattr(address, "recipient_name", None), default="")
        line_1 = self._string_value(getattr(address, "line_1", None), default="")
        line_2 = self._string_value(getattr(address, "line_2", None), default="")
        district = self._string_value(getattr(address, "district", None), default="")
        city = self._string_value(getattr(address, "city", None), default="")
        state = self._string_value(getattr(address, "state", None), default="")
        postal_code = self._string_value(getattr(address, "postal_code", None), default="")
        content_parts = [line_1, line_2, district, f"{city}/{state}".strip("/")]
        subtitle = "Endereço principal" if bool(getattr(address, "is_default", False)) else "Endereço salvo"
        if recipient_name:
            subtitle = f"{subtitle} · {recipient_name}"
        return {
            "title": label,
            "subtitle": subtitle,
            "content": " · ".join(part for part in content_parts if part),
            "footer": f"CEP {postal_code}" if postal_code else "",
            "edit_href": f"#edit-address-{getattr(address, 'pk', 'saved')}",
            "remove_href": f"#remove-address-{getattr(address, 'pk', 'saved')}",
        }

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
                "price": DjangoOrmCustomerAreaRepository._money_value(getattr(item, "price_snapshot", None)),
                "quantity": str(getattr(item, "quantity", 1) or 1),
                "quantity_readonly": bool(getattr(item, "quantity_readonly", True)),
            }
            for item in items
        ]

    @staticmethod
    def _format_timestamp(value: object, *, default: str = "agora") -> str:
        if not value:
            return default
        if isinstance(value, datetime):
            aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
            return aware_value.strftime("%d/%m/%Y")
        return str(value)

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


class FallbackAccountProfileRepository:
    def get_primary_profile(self) -> dict[str, object]:
        return {
            "tenant_id": None,
            "first_name": "Ana",
            "last_name": "Souza",
            "email": "ana@hubx.market",
            "phone": "(11) 99999-0000",
            "newsletter_opt_in": True,
            "order_updates_opt_in": True,
        }


class FallbackCustomerAreaRepository:
    def list_orders(self, profile: dict[str, object]) -> list[dict[str, object]]:
        return [
            {
                **order,
                "order_items": [dict(item) for item in order.get("order_items", [])],
                "activity_items": [dict(item) for item in order.get("activity_items", [])],
            }
            for order in _fallback_customer_order_fixtures()
        ]

    def get_order(self, profile: dict[str, object], order_number: str) -> dict[str, object] | None:
        normalized = order_number.lstrip("#")
        for order in self.list_orders(profile):
            if str(order["order_number"]) == normalized:
                return order
        return None

    def get_addresses(self, profile: dict[str, object]) -> list[dict[str, object]]:
        return [dict(address) for address in _fallback_address_fixtures()]


@dataclass
class AccountCustomerAreaQueryService:
    profile_repository: AccountProfileReadRepository
    fallback_profile_repository: AccountProfileReadRepository
    area_repository: CustomerAreaReadRepository
    fallback_area_repository: CustomerAreaReadRepository

    def using_persisted_profile_source(self) -> bool:
        try:
            return self.profile_repository.get_primary_profile() is not None
        except Exception:
            return False

    def using_persisted_orders_source(self) -> bool:
        try:
            return bool(self.area_repository.list_orders(self._profile()))
        except Exception:
            return False

    def using_persisted_addresses_source(self) -> bool:
        try:
            return bool(self.area_repository.get_addresses(self._profile()))
        except Exception:
            return False

    def _profile(self) -> dict[str, object]:
        return self.profile_repository.get_primary_profile() or self.fallback_profile_repository.get_primary_profile()

    def list_orders(self) -> list[dict[str, object]]:
        profile = self._profile()
        real_orders = self.area_repository.list_orders(profile)
        return real_orders or self.fallback_area_repository.list_orders(profile)

    def get_order(self, order_number: str) -> dict[str, object]:
        profile = self._profile()
        real_order = self.area_repository.get_order(profile, order_number)
        if real_order:
            return real_order
        fallback_order = self.fallback_area_repository.get_order(profile, order_number)
        if fallback_order:
            return fallback_order
        normalized = order_number.lstrip("#")
        return {
            "order_number": normalized,
            "status": "processing",
            "order_status_label": "Em preparação",
            "order_status_variant": "warning",
            "payment_status": "Indisponível",
            "shipping_status": "Indisponível",
            "updated_at": "agora",
            "summary_content": "Pedido ainda sem integração com dados reais; usando fallback seguro de apresentação.",
            "subtotal": "R$ 0,00",
            "shipping": "R$ 0,00",
            "discount": "",
            "installments": "",
            "total": "R$ 0,00",
            "order_items": [],
            "activity_items": [],
        }

    def get_orders_page_data(self) -> dict[str, object]:
        return {
            "page_title": "Meus pedidos",
            "page_description": "Acompanhe o histórico, status e próximos passos das suas compras.",
            "search_name": "q",
            "status_name": "status",
            "status_options": _customer_order_status_options(),
            "order_columns": [
                {"label": "Pedido"},
                {"label": "Status"},
                {"label": "Pagamento"},
                {"label": "Entrega"},
                {"label": "Data"},
            ],
        }

    def get_order_detail_page_data(self, order_number: str) -> dict[str, object]:
        order = self.get_order(order_number)
        return {
            "page_title": f'Pedido #{order["order_number"]}',
            "page_description": "Veja o status atual, itens comprados e histórico de atualizações do seu pedido.",
            "page_meta": order.get("page_meta") or "Área do cliente · acompanhe pagamentos, envio e entregas em um só lugar.",
            "order_status_label": order["order_status_label"],
            "order_status_variant": order["order_status_variant"],
            "order_number": f'#{order["order_number"]}',
            "payment_status": order["payment_status"],
            "shipping_status": order["shipping_status"],
            "summary_content": order["summary_content"],
            "order_items": order["order_items"],
            "subtotal": order["subtotal"],
            "shipping": order["shipping"],
            "discount": order["discount"],
            "installments": order["installments"],
            "total": order["total"],
            "summary_note": order.get("summary_note", ""),
            "activity_items": order["activity_items"],
        }

    def get_addresses_page_data(self) -> dict[str, object]:
        profile = self._profile()
        addresses = self.area_repository.get_addresses(profile) or self.fallback_area_repository.get_addresses(profile)
        return {
            "page_title": "Meus endereços",
            "page_description": "Gerencie endereços de entrega e cobrança usados nas suas compras.",
            "addresses": addresses,
        }

    def get_profile_page_data(self) -> dict[str, object]:
        profile = self._profile()
        return {
            "page_title": "Meu perfil",
            "page_description": "Atualize seus dados pessoais, contato e preferências da conta.",
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "email": profile["email"],
            "phone": profile["phone"],
            "newsletter_opt_in": profile["newsletter_opt_in"],
            "order_updates_opt_in": profile["order_updates_opt_in"],
        }


account_customer_area_queries = AccountCustomerAreaQueryService(
    profile_repository=DjangoOrmAccountProfileRepository(),
    fallback_profile_repository=FallbackAccountProfileRepository(),
    area_repository=DjangoOrmCustomerAreaRepository(),
    fallback_area_repository=FallbackCustomerAreaRepository(),
)
