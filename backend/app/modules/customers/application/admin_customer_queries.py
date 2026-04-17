from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from django.db import connection
from django.utils import timezone


STATUS_OPTIONS = [
    {"value": "active", "label": "Ativo"},
    {"value": "vip", "label": "VIP"},
    {"value": "inactive", "label": "Inativo"},
]


FALLBACK_CUSTOMER_FIXTURES = [
    {
        "slug": "ana-souza",
        "name": "Ana Souza",
        "email": "ana@hubx.market",
        "phone": "(11) 99999-0000",
        "status": "active",
        "customer_status_label": "Ativo",
        "account_type_label": "Storefront",
        "last_activity": "há 12 min",
        "customer_reference": "#8821",
        "customer_since": "há 8 meses",
        "last_seen": "hoje às 10:24",
        "summary_content": "Cliente ativo com perfil completo, bom histórico de compras e atendimento sem ocorrências abertas.",
        "contact_content": "Ana Souza · ana@hubx.market · (11) 99999-0000",
        "profile_content": "Cliente recorrente, aceita comunicações de pedido e tem preferência por e-mail.",
        "orders_summary_content": "12 pedidos concluídos · ticket médio de R$ 186,00 · última compra há 4 dias.",
        "account_notes_content": "Perfil saudável, sem chargebacks e com alta taxa de recompra.",
        "activity_items": [
            {
                "title": "Novo pedido concluído",
                "description": "Cliente finalizou uma compra no storefront com pagamento aprovado.",
                "timestamp": "há 12 min",
                "badge_label": "Pedido",
                "badge_variant": "paid",
            },
            {
                "title": "Perfil atualizado",
                "description": "Telefone principal foi confirmado pelo próprio cliente.",
                "timestamp": "há 2 dias",
                "badge_label": "Conta",
                "badge_variant": "info",
            },
        ],
    },
    {
        "slug": "bruno-lima",
        "name": "Bruno Lima",
        "email": "bruno@hubx.market",
        "phone": "(21) 98888-0000",
        "status": "vip",
        "customer_status_label": "VIP",
        "account_type_label": "Storefront",
        "last_activity": "há 1 h",
        "customer_reference": "#9130",
        "customer_since": "há 1 ano",
        "last_seen": "ontem às 21:10",
        "summary_content": "Cliente de alto valor com recorrência acima da média e atenção prioritária no atendimento.",
        "contact_content": "Bruno Lima · bruno@hubx.market · (21) 98888-0000",
        "profile_content": "Cliente premium, inscrito em newsletters e com histórico de compras em categorias de ticket alto.",
        "orders_summary_content": "27 pedidos concluídos · ticket médio de R$ 312,00 · última compra há 2 dias.",
        "account_notes_content": "Monitorar lançamentos da categoria favorita e campanhas de retenção.",
        "activity_items": [
            {
                "title": "Acesso recente à conta",
                "description": "Cliente navegou pela área logada e revisou pedidos recentes.",
                "timestamp": "há 1 h",
                "badge_label": "Acesso",
                "badge_variant": "neutral",
            }
        ],
    },
    {
        "slug": "mariana-costa",
        "name": "Mariana Costa",
        "email": "mariana@hubx.market",
        "phone": "(31) 97777-0000",
        "status": "inactive",
        "customer_status_label": "Inativo",
        "account_type_label": "CRM Import",
        "last_activity": "há 6 dias",
        "customer_reference": "#9322",
        "customer_since": "há 4 meses",
        "last_seen": "há 6 dias",
        "summary_content": "Conta sem atividade recente e sem novos pedidos no período atual.",
        "contact_content": "Mariana Costa · mariana@hubx.market · (31) 97777-0000",
        "profile_content": "Cadastro válido, mas com engajamento reduzido nas últimas semanas.",
        "orders_summary_content": "3 pedidos concluídos · ticket médio de R$ 142,00 · última compra há 34 dias.",
        "account_notes_content": "Candidata para campanha de reativação.",
        "activity_items": [
            {
                "title": "Sem atividade recente",
                "description": "Conta segue ativa, mas sem novos eventos relevantes desde a última compra.",
                "timestamp": "há 6 dias",
                "badge_label": "Retenção",
                "badge_variant": "warning",
            }
        ],
    },
]


class CustomerReadRepository(Protocol):
    def list_customers(self) -> list[dict[str, object]]:
        ...

    def get_customer(self, customer_slug: str) -> dict[str, object] | None:
        ...


def _clone_customer(customer: dict[str, object]) -> dict[str, object]:
    return {
        **customer,
        "activity_items": [dict(item) for item in customer.get("activity_items", [])],
    }


class FallbackCustomerRepository:
    def list_customers(self) -> list[dict[str, object]]:
        return [_clone_customer(customer) for customer in FALLBACK_CUSTOMER_FIXTURES]

    def get_customer(self, customer_slug: str) -> dict[str, object] | None:
        for customer in self.list_customers():
            if customer["slug"] == customer_slug:
                return customer
        return None


class DjangoOrmCustomerRepository:
    def __init__(self) -> None:
        try:
            from app.modules.customers import models as customer_models
        except Exception:
            self.customer_model = None
            return

        self.customer_model = getattr(customer_models, "Customer", None)

    def _has_real_model(self) -> bool:
        return self.customer_model is not None

    def is_ready(self) -> bool:
        if not self._has_real_model():
            return False
        try:
            table_name = self.customer_model._meta.db_table
        except Exception:
            return False
        try:
            with connection.cursor() as cursor:
                tables = connection.introspection.table_names(cursor)
        except Exception:
            return False
        return table_name in set(tables)

    def list_customers(self) -> list[dict[str, object]]:
        if not self.is_ready():
            return []

        try:
            queryset = self.customer_model._default_manager.all().order_by("-updated_at", "-id")
        except Exception:
            return []

        return [self._serialize_customer(customer) for customer in queryset]

    def get_customer(self, customer_slug: str) -> dict[str, object] | None:
        if not self.is_ready():
            return None

        try:
            customer = self.customer_model._default_manager.filter(slug=customer_slug).first()
        except Exception:
            return None

        if not customer:
            return None
        return self._serialize_customer(customer)

    def _serialize_customer(self, customer: object) -> dict[str, object]:
        status = self._string_value(getattr(customer, "status", None), default="active")
        status_label = dict((option["value"], option["label"]) for option in STATUS_OPTIONS).get(status, "Ativo")
        email = self._string_value(getattr(customer, "email", None), default="indisponivel@hubx.market")
        phone = self._string_value(getattr(customer, "phone", None), default="—")
        name = self._display_name(customer)
        account_type = self._string_value(getattr(customer, "account_type", None), default="Storefront")
        updated_at = self._format_timestamp(getattr(customer, "updated_at", None))
        created_at = self._format_timestamp(getattr(customer, "created_at", None))
        last_seen = self._format_timestamp(getattr(customer, "last_seen_at", None), default="indisponível")
        reference = self._string_value(getattr(customer, "reference", None), default="#0000")

        return {
            "slug": self._string_value(getattr(customer, "slug", None), default="customer"),
            "name": name,
            "email": email,
            "phone": phone,
            "status": status,
            "customer_status_label": status_label,
            "account_type_label": account_type,
            "last_activity": updated_at,
            "customer_reference": reference,
            "customer_since": created_at,
            "last_seen": last_seen,
            "summary_content": (
                f"Cliente {name} com status {status_label.lower()} e conta {account_type.lower()} "
                f"sincronizada em {updated_at}."
            ),
            "contact_content": " · ".join(filter(None, [name, email, phone])),
            "profile_content": (
                f"Perfil persistido com e-mail {email}"
                + (f" e telefone {phone}." if phone != "—" else ".")
            ),
            "orders_summary_content": "Resumo de pedidos ainda depende da integração completa do módulo.",
            "account_notes_content": (
                f"Registro persistido pronto para operação administrativa com referência {reference}."
            ),
            "activity_items": self._build_activity_items(
                updated_at=updated_at,
                last_seen=last_seen,
                status_label=status_label,
                account_type=account_type,
            ),
        }

    @staticmethod
    def _display_name(customer: object) -> str:
        for attr in ("full_name", "name"):
            value = getattr(customer, attr, None)
            if value:
                return str(value)
        first_name = getattr(customer, "first_name", "")
        last_name = getattr(customer, "last_name", "")
        combined = f"{first_name} {last_name}".strip()
        return combined or "Cliente"

    @staticmethod
    def _string_value(value: object, *, default: str) -> str:
        if value in (None, ""):
            return default
        return str(value)

    @staticmethod
    def _format_timestamp(value: object, *, default: str = "agora") -> str:
        if not value:
            return default
        if isinstance(value, datetime):
            aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
            return aware_value.strftime("%d/%m/%Y às %H:%M")
        return str(value)

    @staticmethod
    def _build_activity_items(*, updated_at: str, last_seen: str, status_label: str, account_type: str) -> list[dict[str, object]]:
        return [
            {
                "title": "Cadastro persistido sincronizado",
                "description": f"Cliente carregado com status {status_label.lower()} e conta {account_type.lower()}.",
                "timestamp": updated_at,
                "badge_label": "Conta",
                "badge_variant": "info",
            },
            {
                "title": "Última presença registrada",
                "description": f"Último acesso conhecido registrado em {last_seen}.",
                "timestamp": updated_at,
                "badge_label": "Acesso",
                "badge_variant": "neutral",
            },
        ]


def _fallback_customer(customer_slug: str) -> dict[str, object]:
    return {
        "slug": customer_slug,
        "name": customer_slug.replace("-", " ").title(),
        "email": "indisponivel@hubx.market",
        "phone": "—",
        "status": "inactive",
        "customer_status_label": "Inativo",
        "account_type_label": "Indefinido",
        "last_activity": "agora",
        "customer_reference": "#0000",
        "customer_since": "indisponível",
        "last_seen": "indisponível",
        "summary_content": "Conta ainda sem integração com dados reais; usando fallback seguro de apresentação.",
        "contact_content": "Sem dados de contato disponíveis no adapter inicial.",
        "profile_content": "Perfil ainda não conectado ao fluxo real.",
        "orders_summary_content": "Sem histórico consolidado disponível no adapter inicial.",
        "account_notes_content": "Registro temporário para estabelecer o padrão de migração real com page templates oficiais.",
        "activity_items": [],
    }


@dataclass
class AdminCustomerQueryService:
    orm_repository: CustomerReadRepository
    fallback_repository: CustomerReadRepository

    def using_persisted_source(self) -> bool:
        try:
            return bool(self.orm_repository.list_customers())
        except Exception:
            return False

    def list_customers(self) -> list[dict[str, object]]:
        real_customers = self.orm_repository.list_customers()
        return real_customers or self.fallback_repository.list_customers()

    def get_customer(self, customer_slug: str) -> dict[str, object]:
        real_customer = self.orm_repository.get_customer(customer_slug)
        if real_customer:
            return real_customer

        fallback_customer = self.fallback_repository.get_customer(customer_slug)
        if fallback_customer:
            return fallback_customer

        return _fallback_customer(customer_slug)


admin_customer_queries = AdminCustomerQueryService(
    orm_repository=DjangoOrmCustomerRepository(),
    fallback_repository=FallbackCustomerRepository(),
)
