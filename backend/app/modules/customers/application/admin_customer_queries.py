from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.utils import timezone


STATUS_OPTIONS = [
    {"value": "active", "label": "Ativo"},
    {"value": "vip", "label": "VIP"},
    {"value": "inactive", "label": "Inativo"},
]

QUICK_FILTER_OPTIONS = [
    {"value": "high_priority", "label": "Alta prioridade"},
    {"value": "at_risk", "label": "Em risco"},
    {"value": "followup", "label": "Com follow-up"},
    {"value": "repeat", "label": "Recorrentes"},
    {"value": "new", "label": "Novos"},
]


def _value_tier(total_spent: Decimal, average_ticket: Decimal, total_orders: int) -> tuple[str, str]:
    if total_orders <= 0:
        return ("Sem histórico", "Sem histórico")
    if total_spent >= Decimal("500.00") or average_ticket >= Decimal("250.00"):
        return ("Alto valor", "high")
    if total_spent >= Decimal("200.00") or average_ticket >= Decimal("120.00"):
        return ("Valor em desenvolvimento", "medium")
    return ("Valor inicial", "low")


def _engagement_label(*, recency_bucket: str, is_repeat_customer: bool, is_at_risk: bool) -> str:
    if is_at_risk:
        return "Em risco"
    if is_repeat_customer and recency_bucket == "Recente":
        return "Recorrente ativo"
    if is_repeat_customer:
        return "Recorrente"
    if recency_bucket == "Recente":
        return "Recente"
    if recency_bucket == "Atenção":
        return "Requer atenção"
    return "Sem histórico"


def _list_highlights(*, tier_label: str, is_repeat_customer: bool, is_at_risk: bool) -> str:
    highlights: list[str] = []
    if tier_label == "Alto valor":
        highlights.append("alto valor")
    if is_repeat_customer and not is_at_risk:
        highlights.append("recorrente")
    return " · ".join(highlights)


def _execution_highlights(*, followup: bool, reengagement: bool, priority_flag: bool) -> str:
    highlights: list[str] = []
    if priority_flag:
        highlights.append("prioridade manual")
    if followup:
        highlights.append("follow-up")
    if reengagement:
        highlights.append("reengajamento")
    return " · ".join(highlights)


def _extend_unique(highlights: list[str], *values: str) -> list[str]:
    seen = {item.strip().lower() for item in highlights if item.strip()}
    for value in values:
        normalized = value.strip().lower()
        if not normalized or normalized in seen:
            continue
        highlights.append(normalized)
        seen.add(normalized)
    return highlights


def _grouping_highlights(*, priority_label: str, lifecycle_stage_label: str, is_at_risk: bool) -> list[str]:
    highlights: list[str] = []
    if priority_label:
        highlights.append(priority_label.lower())
    if lifecycle_stage_label in {"Em risco", "Perdido"} or is_at_risk:
        highlights.append(lifecycle_stage_label.lower())
    elif lifecycle_stage_label in {"Ativo", "Recorrente"}:
        highlights.append("base ativa")
    elif lifecycle_stage_label:
        highlights.append(lifecycle_stage_label.lower())
    return highlights


def _revenue_signal(*, total_spent: Decimal, average_ticket: Decimal, total_orders: int, tier_label: str) -> tuple[str, str]:
    if total_orders <= 0:
        return ("sem receita realizada", "Sem receita realizada por este cliente até o momento.")
    if tier_label == "Alto valor":
        return (
            "receita relevante",
            f"Já gerou {DjangoOrmCustomerRepository._money_value(total_spent)} em receita, com contribuição acima da média da base atual.",
        )
    if tier_label == "Valor em desenvolvimento":
        return (
            "receita em desenvolvimento",
            f"Já gerou {DjangoOrmCustomerRepository._money_value(total_spent)} em receita e mantém ticket médio de {DjangoOrmCustomerRepository._money_value(average_ticket)}.",
        )
    return (
        "receita inicial",
        f"Já trouxe {DjangoOrmCustomerRepository._money_value(total_spent)} em receita, com espaço para ampliar recorrência e ticket médio.",
    )


def _lifecycle_stage(*, total_orders: int, days_since_last_order: int, is_repeat_customer: bool, is_at_risk: bool) -> str:
    if total_orders <= 0:
        return "Novo"
    if days_since_last_order >= 60:
        return "Perdido"
    if is_at_risk or days_since_last_order >= 30:
        return "Em risco"
    if is_repeat_customer:
        return "Recorrente"
    return "Ativo"


def _growth_guidance(
    *,
    lifecycle_stage_label: str,
    business_tier_label: str,
    engagement_label: str,
    is_repeat_customer: bool,
    is_at_risk: bool,
) -> tuple[str, str]:
    if lifecycle_stage_label == "Perdido":
        return (
            "Recuperação seletiva",
            "Reavalie se ainda existe espaço para uma nova aproximação antes de investir esforço comercial adicional.",
        )
    if lifecycle_stage_label == "Em risco" or is_at_risk:
        return (
            "Recuperar cliente",
            "Vale tentar recuperar valor recente antes que a relação esfrie ainda mais.",
        )
    if lifecycle_stage_label == "Recorrente" or is_repeat_customer:
        return (
            "Expandir frequência de compra",
            "Cliente já demonstrou recorrência; a principal oportunidade é ampliar ritmo e valor das próximas compras.",
        )
    if lifecycle_stage_label == "Ativo":
        return (
            "Manter engajamento",
            "Cliente segue ativo; o melhor caminho é sustentar presença e observar espaço para evolução de ticket.",
        )
    if business_tier_label == "Sem histórico":
        return (
            "Incentivar primeira recompra",
            "Cliente ainda está no começo da jornada; vale estimular o primeiro retorno de forma simples e clara.",
        )
    return (
        "Desenvolver potencial de valor",
        "Existe espaço para ampliar valor ao longo do relacionamento sem forçar uma ação imediata.",
    )


def _priority_label(
    *,
    business_tier_label: str,
    lifecycle_stage_label: str,
    is_at_risk: bool,
    growth_priority_label: str,
) -> str:
    if is_at_risk or lifecycle_stage_label in {"Em risco", "Perdido"}:
        return "Alta prioridade"
    if business_tier_label == "Alto valor" or growth_priority_label in {"Expandir frequência de compra", "Recuperar cliente"}:
        return "Alta prioridade"
    if lifecycle_stage_label in {"Recorrente", "Ativo"} or business_tier_label == "Valor em desenvolvimento":
        return "Média prioridade"
    return "Baixa prioridade"


def _next_action_guidance(
    *,
    engagement_label: str,
    business_tier_label: str,
    recency_bucket: str,
    is_at_risk: bool,
    is_repeat_customer: bool,
) -> tuple[str, str]:
    if is_at_risk:
        return (
            "Revisar e reengajar",
            "Vale revisar o histórico recente e preparar uma abordagem de retorno com contexto do último pedido.",
        )
    if business_tier_label == "Alto valor":
        return (
            "Priorizar e monitorar",
            "Cliente com valor acima da média; acompanhe a próxima interação para preservar recorrência e experiência.",
        )
    if is_repeat_customer:
        return (
            "Acompanhar próxima recompra",
            "Cliente já voltou a comprar antes; observe sinais da próxima janela de recompra e mantenha contato consistente.",
        )
    if recency_bucket == "Recente" or engagement_label == "Recente":
        return (
            "Observar próxima interação",
            "Cliente teve atividade recente; vale acompanhar se o relacionamento evolui naturalmente para uma nova compra.",
        )
    return (
        "Estimular primeiro retorno",
        "Cliente ainda tem histórico leve; o melhor próximo passo é manter comunicação clara para incentivar uma nova visita.",
    )


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
    def list_customers(self, *, tenant_id: int | None = None) -> list[dict[str, object]]:
        ...

    def get_customer(self, customer_slug: str, *, tenant_id: int | None = None) -> dict[str, object] | None:
        ...


def _clone_customer(customer: dict[str, object]) -> dict[str, object]:
    return {
        **customer,
        "activity_items": [dict(item) for item in customer.get("activity_items", [])],
    }


class FallbackCustomerRepository:
    def list_customers(self, *, tenant_id: int | None = None) -> list[dict[str, object]]:
        return [_clone_customer(customer) for customer in FALLBACK_CUSTOMER_FIXTURES]

    def get_customer(self, customer_slug: str, *, tenant_id: int | None = None) -> dict[str, object] | None:
        for customer in self.list_customers(tenant_id=tenant_id):
            if customer["slug"] == customer_slug:
                return customer
        return None


class DjangoOrmCustomerRepository:
    def __init__(self) -> None:
        try:
            from app.modules.customers import models as customer_models
            from app.modules.orders import models as order_models
        except Exception:
            self.customer_model = None
            self.order_model = None
            return

        self.customer_model = getattr(customer_models, "Customer", None)
        self.order_model = getattr(order_models, "Order", None)

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

    def _orders_ready(self) -> bool:
        if self.order_model is None:
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

    def list_customers(self, *, tenant_id: int | None = None) -> list[dict[str, object]]:
        if not self.is_ready():
            return []

        try:
            queryset = self.customer_model._default_manager.order_by("-updated_at", "-id")
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
        except Exception:
            return []

        return [self._serialize_customer(customer) for customer in queryset]

    def get_customer(self, customer_slug: str, *, tenant_id: int | None = None) -> dict[str, object] | None:
        if not self.is_ready():
            return None

        try:
            queryset = self.customer_model._default_manager.filter(slug=customer_slug)
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            customer = queryset.first()
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
        marked_for_followup = bool(getattr(customer, "marked_for_followup", False))
        marked_for_reengagement = bool(getattr(customer, "marked_for_reengagement", False))
        marked_as_priority = bool(getattr(customer, "marked_as_priority", False))
        order_metrics = self._build_order_metrics(customer)
        total_orders = int(order_metrics["total_orders"])
        total_spent = str(order_metrics["total_spent"])
        average_ticket = str(order_metrics["average_ticket"])
        last_order_date = str(order_metrics["last_order_date"])
        paid_orders_count = int(order_metrics["paid_orders_count"])
        shipped_orders_count = int(order_metrics["shipped_orders_count"])
        canceled_orders_count = int(order_metrics["canceled_orders_count"])
        last_order_status = str(order_metrics["last_order_status"])
        last_order_total = str(order_metrics["last_order_total"])
        days_since_last_order = int(order_metrics["days_since_last_order"])
        recency_bucket = str(order_metrics["recency_bucket"])
        is_repeat_customer = bool(order_metrics["is_repeat_customer"])
        is_at_risk = bool(order_metrics["is_at_risk"])
        order_linkage_mode = str(order_metrics["linkage_mode"])
        has_orders = total_orders > 0
        total_spent_decimal = Decimal(total_spent)
        average_ticket_decimal = Decimal(average_ticket)
        tier_label, tier_code = _value_tier(total_spent_decimal, average_ticket_decimal, total_orders)
        engagement_label = _engagement_label(
            recency_bucket=recency_bucket,
            is_repeat_customer=is_repeat_customer,
            is_at_risk=is_at_risk,
        )
        list_highlights = _list_highlights(
            tier_label=tier_label,
            is_repeat_customer=is_repeat_customer,
            is_at_risk=is_at_risk,
        )
        execution_highlights = _execution_highlights(
            followup=marked_for_followup,
            reengagement=marked_for_reengagement,
            priority_flag=marked_as_priority,
        )
        revenue_label, revenue_helper = _revenue_signal(
            total_spent=total_spent_decimal,
            average_ticket=average_ticket_decimal,
            total_orders=total_orders,
            tier_label=tier_label,
        )
        lifecycle_stage_label = _lifecycle_stage(
            total_orders=total_orders,
            days_since_last_order=days_since_last_order,
            is_repeat_customer=is_repeat_customer,
            is_at_risk=is_at_risk,
        )
        next_action_label, next_action_helper = _next_action_guidance(
            engagement_label=engagement_label,
            business_tier_label=tier_label,
            recency_bucket=recency_bucket,
            is_at_risk=is_at_risk,
            is_repeat_customer=is_repeat_customer,
        )
        growth_priority_label, next_growth_hint = _growth_guidance(
            lifecycle_stage_label=lifecycle_stage_label,
            business_tier_label=tier_label,
            engagement_label=engagement_label,
            is_repeat_customer=is_repeat_customer,
            is_at_risk=is_at_risk,
        )
        priority_label = _priority_label(
            business_tier_label=tier_label,
            lifecycle_stage_label=lifecycle_stage_label,
            is_at_risk=is_at_risk,
            growth_priority_label=growth_priority_label,
        )
        execution_summary = (
            "Execução atual: follow-up e acompanhamento interno já sinalizados. "
            if marked_for_followup and marked_for_reengagement
            else "Execução atual: follow-up interno sinalizado. "
            if marked_for_followup
            else "Execução atual: reengajamento já sinalizado. "
            if marked_for_reengagement
            else "Execução atual: prioridade manual aberta. "
            if marked_as_priority
            else ""
        )
        execution_notes = (
            "Flags atuais: prioridade manual, follow-up e reengajamento registrados. "
            if marked_as_priority and marked_for_followup and marked_for_reengagement
            else "Flags atuais: prioridade manual registrada. "
            if marked_as_priority and not marked_for_followup and not marked_for_reengagement
            else "Flags atuais: follow-up registrado. "
            if marked_for_followup and not marked_for_reengagement
            else "Flags atuais: reengajamento registrado. "
            if marked_for_reengagement and not marked_for_followup
            else "Flags atuais: follow-up e reengajamento registrados. "
            if marked_for_followup and marked_for_reengagement
            else ""
        )
        list_highlight_items = _grouping_highlights(
            priority_label=priority_label,
            lifecycle_stage_label=lifecycle_stage_label,
            is_at_risk=is_at_risk,
        )
        list_highlight_items = _extend_unique(
            list_highlight_items,
            *[item.strip() for item in list_highlights.split("·") if item.strip()],
            growth_priority_label,
            execution_highlights,
            next_action_label,
        )
        list_highlights = " · ".join(list_highlight_items)
        summary_content = (
            (
                f"Cliente {name} em estágio {lifecycle_stage_label.lower()} e tier {tier_label.lower()}, com {total_orders} pedido(s), total gasto de {self._money_value(total_spent_decimal)} "
                f"e ticket médio de {self._money_value(average_ticket_decimal)}. "
                f"Contribuição de receita: {revenue_label}. "
                f"{priority_label}. "
                f"{execution_summary}"
                f"Engajamento atual: {engagement_label.lower()}. "
                f"Direção de crescimento: {growth_priority_label.lower()}. "
                f"Próximo passo: {next_action_label.lower()}. "
                f"Mix operacional: {paid_orders_count} pago(s), {shipped_orders_count} enviado(s) e {canceled_orders_count} cancelado(s). "
                f"Recência: {recency_bucket.lower()}."
            )
            if has_orders
            else (
                f"Cliente {name} em estágio novo, com status {status_label.lower()} e conta {account_type.lower()} "
                f"sincronizada em {updated_at}. "
                f"{execution_summary}"
            )
        )
        orders_summary_content = (
            f"{total_orders} pedido(s) concluído(s) · tier {tier_label.lower()} · ticket médio de {self._money_value(average_ticket_decimal)} · "
            f"receita acumulada de {self._money_value(total_spent_decimal)} · último pedido em {last_order_date} ({last_order_status})"
            + (f" · último total de {self._money_value(last_order_total)}." if last_order_total != "0.00" else ".")
            + (
                f" Perfil {'recorrente' if is_repeat_customer else 'pontual'}"
                f" · {engagement_label.lower()}"
                f"{' · atenção de retenção' if is_at_risk else ''}."
            )
            if has_orders
            else "Cliente ainda sem pedidos persistidos vinculados; resumo segue em modo seguro de fallback."
        )

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
            "summary_content": summary_content,
            "contact_content": " · ".join(filter(None, [name, email, phone])),
            "profile_content": (
                f"Perfil persistido com e-mail {email}"
                + (f" e telefone {phone}." if phone != "—" else ".")
            ),
            "orders_summary_content": orders_summary_content,
            "account_notes_content": (
                (
                    f"Registro persistido pronto para operação administrativa com referência {reference}. "
                    f"{priority_label}, com lifecycle {lifecycle_stage_label.lower()}, tier {tier_label.lower()} e engajamento {engagement_label.lower()}, ajuda a priorizar próximos contatos. "
                    f"{revenue_helper} "
                    f"{execution_notes}"
                    f"Direção de crescimento: {growth_priority_label.lower()}. {next_growth_hint} "
                    f"Próxima ação sugerida: {next_action_label.lower()}. {next_action_helper}"
                )
                if has_orders
                else (
                    f"Registro persistido pronto para operação administrativa com referência {reference}. "
                    f"{execution_notes}"
                    "Sem sinais de valor suficientes para classificação além do cadastro atual."
                )
            ),
            "activity_items": self._build_activity_items(
                customer=customer,
                updated_at=updated_at,
                last_seen=last_seen,
                status_label=status_label,
                account_type=account_type,
                order_metrics=order_metrics,
            ),
            "total_orders": total_orders,
            "total_spent": self._money_value(total_spent),
            "average_ticket": self._money_value(average_ticket),
            "last_order_date": last_order_date,
            "paid_orders_count": paid_orders_count,
            "shipped_orders_count": shipped_orders_count,
            "canceled_orders_count": canceled_orders_count,
            "last_order_status": last_order_status,
            "last_order_total": self._money_value(last_order_total),
            "days_since_last_order": days_since_last_order,
            "recency_bucket": recency_bucket,
            "is_repeat_customer": is_repeat_customer,
            "is_at_risk": is_at_risk,
            "order_linkage_mode": order_linkage_mode,
            "business_tier_label": tier_label,
            "business_tier_code": tier_code,
            "engagement_label": engagement_label,
            "list_highlights": list_highlights,
            "next_action_label": next_action_label,
            "next_action_helper": next_action_helper,
            "revenue_label": revenue_label,
            "revenue_helper": revenue_helper,
            "lifecycle_stage_label": lifecycle_stage_label,
            "growth_priority_label": growth_priority_label,
            "next_growth_hint": next_growth_hint,
            "priority_label": priority_label,
            "marked_for_followup": marked_for_followup,
            "marked_for_reengagement": marked_for_reengagement,
            "marked_as_priority": marked_as_priority,
        }

    def _build_order_metrics(self, customer: object) -> dict[str, object]:
        empty_metrics = {
            "total_orders": 0,
            "total_spent": Decimal("0.00"),
            "average_ticket": Decimal("0.00"),
            "last_order_date": "indisponível",
            "paid_orders_count": 0,
            "shipped_orders_count": 0,
            "canceled_orders_count": 0,
            "last_order_status": "indisponível",
            "last_order_total": Decimal("0.00"),
            "days_since_last_order": -1,
            "recency_bucket": "Sem pedidos",
            "is_repeat_customer": False,
            "is_at_risk": False,
            "last_order": None,
            "linkage_mode": "none",
        }
        if not self._orders_ready():
            return empty_metrics
        queryset = self._orders_queryset(customer)
        if queryset is None:
            return empty_metrics
        try:
            orders = list(queryset.order_by("-updated_at", "-id"))
        except Exception:
            return empty_metrics
        if not orders:
            return empty_metrics
        total_spent = sum(
            ((getattr(order, "total", Decimal("0.00")) or Decimal("0.00")) for order in orders),
            Decimal("0.00"),
        )
        total_orders = len(orders)
        average_ticket = (total_spent / total_orders) if total_orders else Decimal("0.00")
        last_order = orders[0]
        paid_orders_count = sum(1 for order in orders if str(getattr(order, "status", "") or "") == "paid")
        shipped_orders_count = sum(1 for order in orders if str(getattr(order, "status", "") or "") == "shipped")
        canceled_orders_count = sum(1 for order in orders if str(getattr(order, "status", "") or "") == "canceled")
        last_order_status = self._order_status_label(str(getattr(last_order, "status", "") or ""))
        days_since_last_order = self._days_since(getattr(last_order, "updated_at", None))
        recency_bucket = self._recency_bucket(days_since_last_order)
        return {
            "total_orders": total_orders,
            "total_spent": total_spent,
            "average_ticket": average_ticket.quantize(Decimal("0.01")),
            "last_order_date": self._format_timestamp(getattr(last_order, "updated_at", None), default="indisponível"),
            "paid_orders_count": paid_orders_count,
            "shipped_orders_count": shipped_orders_count,
            "canceled_orders_count": canceled_orders_count,
            "last_order_status": last_order_status,
            "last_order_total": getattr(last_order, "total", Decimal("0.00")) or Decimal("0.00"),
            "days_since_last_order": days_since_last_order,
            "recency_bucket": recency_bucket,
            "is_repeat_customer": total_orders > 1,
            "is_at_risk": days_since_last_order >= 30,
            "last_order": last_order,
            "linkage_mode": "explicit" if getattr(last_order, "customer_id", None) else "fallback",
        }

    def _orders_queryset(self, customer: object):
        tenant_id = getattr(customer, "tenant_id", None)
        email = str(getattr(customer, "email", "") or "").strip()
        if not tenant_id:
            return None
        try:
            if hasattr(self.order_model, "customer_id"):
                explicit_queryset = self.order_model._default_manager.filter(tenant_id=tenant_id, customer_id=getattr(customer, "pk", None))
                if explicit_queryset.exists():
                    return explicit_queryset
            if not email:
                return None
            return self.order_model._default_manager.filter(tenant_id=tenant_id, customer_email=email)
        except Exception:
            return None

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
    def _order_status_label(value: str) -> str:
        mapping = {
            "paid": "Pago",
            "pending": "Pendente",
            "shipped": "Enviado",
            "canceled": "Cancelado",
        }
        return mapping.get(value, "Indisponível")

    @staticmethod
    def _days_since(value: object) -> int:
        if not isinstance(value, datetime):
            return -1
        aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
        today = timezone.localdate()
        return max((today - aware_value.date()).days, 0)

    @staticmethod
    def _recency_bucket(days_since_last_order: int) -> str:
        if days_since_last_order < 0:
            return "Sem pedidos"
        if days_since_last_order <= 7:
            return "Recente"
        if days_since_last_order <= 30:
            return "Atenção"
        return "Em risco"

    @staticmethod
    def _format_timestamp(value: object, *, default: str = "agora") -> str:
        if not value:
            return default
        if isinstance(value, datetime):
            aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
            return aware_value.strftime("%d/%m/%Y às %H:%M")
        return str(value)

    @staticmethod
    def _money_value(value: object) -> str:
        if value in (None, ""):
            return "R$ 0,00"
        if isinstance(value, Decimal):
            numeric = value
        elif isinstance(value, (int, float)):
            numeric = Decimal(str(value))
        else:
            numeric = Decimal(str(value))
        return f"R$ {numeric:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    @staticmethod
    def _build_activity_items(*, customer: object, updated_at: str, last_seen: str, status_label: str, account_type: str, order_metrics: dict[str, object]) -> list[dict[str, object]]:
        activity_items = [
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
        last_order = order_metrics.get("last_order")
        if last_order is None:
            return activity_items
        order_number = getattr(last_order, "number", "0000")
        payment_status = str(getattr(last_order, "payment_status", "") or "indisponível").lower()
        shipping_status = str(getattr(last_order, "shipping_status", "") or "indisponível").lower()
        activity_items.insert(
            0,
            {
                "title": f"Último pedido #{order_number}",
                "description": (
                    f"Cliente com pedido recente em {payment_status}, entrega {shipping_status} "
                    f"e total de {DjangoOrmCustomerRepository._money_value(getattr(last_order, 'total', Decimal('0.00')))}. "
                    f"Mix atual: {order_metrics['paid_orders_count']} pago(s), {order_metrics['shipped_orders_count']} enviado(s), "
                    f"{order_metrics['canceled_orders_count']} cancelado(s). "
                    f"Recência {str(order_metrics['recency_bucket']).lower()}"
                    f" · tier {_value_tier(order_metrics['total_spent'], order_metrics['average_ticket'], order_metrics['total_orders'])[0].lower()}"
                    + (" com atenção de retenção." if order_metrics["is_at_risk"] else ".")
                ),
                "timestamp": DjangoOrmCustomerRepository._format_timestamp(
                    getattr(last_order, "updated_at", None),
                    default=updated_at,
                ),
                "badge_label": "Pedido",
                "badge_variant": "paid" if str(getattr(last_order, "status", "") or "") == "paid" else "info",
            },
        )
        return activity_items[:3]


def _placeholder_customer(customer_slug: str, *, mode: str = "fallback") -> dict[str, object]:
    if mode == "missing":
        summary_content = "Cliente não encontrado no tenant atual; exibindo estado explícito de ausência em vez de fallback de demonstração."
        contact_content = "Sem dados de contato persistidos para este cliente no tenant atual."
        profile_content = "Nenhum perfil persistido foi localizado para este slug dentro da loja atual."
        orders_summary_content = "Sem histórico consolidado disponível para este cliente neste tenant."
        account_notes_content = "Revise o vínculo do slug, o tenant resolvido e o estado real do cadastro antes de qualquer ação operacional."
    else:
        summary_content = "Conta ainda sem integração com dados reais; usando fallback seguro de apresentação."
        contact_content = "Sem dados de contato disponíveis no adapter inicial."
        profile_content = "Perfil ainda não conectado ao fluxo real."
        orders_summary_content = "Sem histórico consolidado disponível no adapter inicial."
        account_notes_content = "Registro temporário para estabelecer o padrão de migração real com page templates oficiais."
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
        "summary_content": summary_content,
        "contact_content": contact_content,
        "profile_content": profile_content,
        "orders_summary_content": orders_summary_content,
        "account_notes_content": account_notes_content,
        "activity_items": [],
    }


@dataclass
class AdminCustomerQueryService:
    orm_repository: CustomerReadRepository
    fallback_repository: CustomerReadRepository

    @staticmethod
    def _allow_fixture_fallback(*, tenant_id: int | None) -> bool:
        return not bool(tenant_id)

    @staticmethod
    def _priority_rank(priority_label: object) -> int:
        mapping = {
            "Alta prioridade": 0,
            "Média prioridade": 1,
            "Baixa prioridade": 2,
        }
        return mapping.get(str(priority_label or "").strip(), 3)

    @staticmethod
    def _execution_boost(customer: dict[str, object]) -> int:
        return sum(
            1
            for flag_name in ("marked_as_priority", "marked_for_followup", "marked_for_reengagement")
            if bool(customer.get(flag_name))
        )

    @staticmethod
    def _money_number(value: object) -> Decimal:
        normalized = (
            str(value or "0")
            .replace("R$", "")
            .replace(".", "")
            .replace(",", ".")
            .strip()
        )
        try:
            return Decimal(normalized or "0")
        except Exception:
            return Decimal("0")

    def _sort_key(self, customer: dict[str, object]) -> tuple[object, ...]:
        days_since_last_order = int(customer.get("days_since_last_order", -1) or -1)
        total_spent = self._money_number(customer.get("total_spent"))
        return (
            self._priority_rank(customer.get("priority_label")),
            -self._execution_boost(customer),
            0 if bool(customer.get("is_at_risk")) else 1,
            -days_since_last_order,
            -total_spent,
            str(customer.get("slug", "")),
        )

    @staticmethod
    def _matches_quick_filter(customer: dict[str, object], quick_filter: str) -> bool:
        if quick_filter == "high_priority":
            return str(customer.get("priority_label", "")).strip() == "Alta prioridade"
        if quick_filter == "at_risk":
            return bool(customer.get("is_at_risk")) or str(customer.get("lifecycle_stage_label", "")).strip() == "Em risco"
        if quick_filter == "followup":
            return bool(customer.get("marked_for_followup"))
        if quick_filter == "repeat":
            return bool(customer.get("is_repeat_customer"))
        if quick_filter == "new":
            return str(customer.get("lifecycle_stage_label", "")).strip() == "Novo"
        return True

    def using_persisted_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            return bool(self.orm_repository.list_customers(tenant_id=tenant_id))
        except Exception:
            return False

    def list_customers(self, quick_filter: str | None = None, *, tenant_id: int | None = None) -> list[dict[str, object]]:
        real_customers = self.orm_repository.list_customers(tenant_id=tenant_id)
        if real_customers:
            customers = real_customers
        elif self._allow_fixture_fallback(tenant_id=tenant_id):
            customers = self.fallback_repository.list_customers(tenant_id=tenant_id)
        else:
            customers = []
        normalized_quick_filter = str(quick_filter or "").strip().lower()
        if normalized_quick_filter in {option["value"] for option in QUICK_FILTER_OPTIONS}:
            customers = [
                customer
                for customer in customers
                if self._matches_quick_filter(customer, normalized_quick_filter)
            ]
        return sorted(customers, key=self._sort_key)

    def get_customer(self, customer_slug: str, *, tenant_id: int | None = None) -> dict[str, object]:
        real_customer = self.orm_repository.get_customer(customer_slug, tenant_id=tenant_id)
        if real_customer:
            return real_customer

        if self._allow_fixture_fallback(tenant_id=tenant_id):
            fallback_customer = self.fallback_repository.get_customer(customer_slug, tenant_id=tenant_id)
            if fallback_customer:
                return fallback_customer

        return _placeholder_customer(
            customer_slug,
            mode="fallback" if self._allow_fixture_fallback(tenant_id=tenant_id) else "missing",
        )


admin_customer_queries = AdminCustomerQueryService(
    orm_repository=DjangoOrmCustomerRepository(),
    fallback_repository=FallbackCustomerRepository(),
)
