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


def _retention_signals(*, total_orders: int, latest_recent_hint: str, persisted: bool) -> dict[str, str]:
    if not persisted or total_orders <= 0:
        return {
            "orders_page_description": "Acompanhe o histórico das suas compras, o andamento da entrega e os próximos passos de cada pedido.",
            "table_description": "Cada pedido mostra um resumo curto do andamento para você localizar mais rápido o que precisa.",
            "row_hint": "",
            "detail_note": "Seu histórico continuará salvo na conta para facilitar novos acompanhamentos quando precisar voltar.",
            "activity_description": "Seu histórico fica salvo na conta para facilitar consultas futuras sempre que você quiser voltar.",
        }
    if total_orders > 1:
        recency_copy = f" Última movimentação: {latest_recent_hint.lower()}." if latest_recent_hint else ""
        return {
            "orders_page_description": f"Você já comprou com a gente antes e pode acompanhar cada etapa por aqui com mais confiança.{recency_copy}",
            "table_description": "Seus pedidos anteriores continuam reunidos aqui para facilitar recompras, consultas e novos acompanhamentos.",
            "row_hint": "cliente recorrente",
            "detail_note": "Você já voltou a comprar por aqui antes, então este histórico permanece salvo para facilitar sua próxima visita.",
            "activity_description": "Seu histórico mostra compras anteriores e deixa o retorno mais simples sempre que você quiser explorar de novo.",
        }
    recency_copy = f" {latest_recent_hint}." if latest_recent_hint else ""
    return {
        "orders_page_description": f"Seu histórico já está salvo nesta conta para facilitar novas compras e consultas futuras.{recency_copy}",
        "table_description": "Este pedido já fica guardado na sua conta para você retomar o acompanhamento e voltar a comprar quando quiser.",
        "row_hint": "histórico salvo",
        "detail_note": "Este pedido já fica salvo na sua conta para tornar uma próxima compra mais simples quando você quiser voltar.",
        "activity_description": "Seu primeiro pedido já fica registrado na conta, deixando o caminho pronto para uma próxima compra com mais tranquilidade.",
    }


def _customer_order_next_step(*, status_label: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> str:
    lowered_payment = payment_status.lower()
    lowered_shipping = shipping_status.lower()
    lowered_fulfillment = fulfillment_status_label.lower()
    lowered_status = status_label.lower()
    if "cancel" in lowered_status:
        return "Se quiser continuar comprando depois, você pode voltar ao catálogo quando for um bom momento para iniciar um novo pedido."
    if "entreg" in lowered_shipping or "conclu" in lowered_fulfillment:
        return "Seu pedido já foi concluído com segurança. Agora vale guardar este histórico na conta e voltar ao catálogo quando fizer sentido iniciar uma nova compra."
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return "Agora vale acompanhar a entrega por aqui e usar este histórico como referência sempre que quiser revisar a compra."
    if "prepar" in lowered_shipping or "separ" in lowered_fulfillment:
        return "O próximo passo é a confirmação do envio; até lá, esta página continua sendo o melhor lugar para acompanhar a preparação."
    if "confirm" in lowered_payment or "pago" in lowered_status:
        return "Seu pedido já está confirmado e a próxima atualização deve mostrar o avanço da preparação para envio."
    return "Assim que houver uma nova atualização importante, ela aparecerá aqui para você seguir acompanhando com tranquilidade."


def _customer_order_continuity_hint(
    *,
    total_orders: int,
    order_index: int,
    status_label: str,
    shipping_status: str,
    recent_update_hint: str,
    fallback_hint: str,
) -> str:
    lowered_shipping = shipping_status.lower()
    lowered_status = status_label.lower()
    if "entreg" in lowered_shipping:
        return "pedido concluído"
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return "acompanhe a entrega"
    if "cancel" in lowered_status:
        return "histórico preservado"
    if total_orders > 1 and order_index == 0:
        return "pedido mais recente"
    if total_orders > 1:
        return "compra anterior salva"
    return fallback_hint


def _customer_orders_continuity_description(*, total_orders: int, persisted: bool, latest_recent_hint: str) -> str:
    if not persisted or total_orders <= 0:
        return "Acompanhe o histórico das suas compras, o andamento da entrega e os próximos passos de cada pedido."
    if total_orders > 1:
        latest_copy = f" {latest_recent_hint}." if latest_recent_hint else ""
        return (
            f"Você já tem {total_orders} pedidos salvos nesta conta, então ficou mais fácil retomar acompanhamentos, "
            f"revisar compras anteriores e decidir quando vale voltar ao catálogo.{latest_copy}"
        )
    latest_copy = f" {latest_recent_hint}." if latest_recent_hint else ""
    return (
        "Seu primeiro pedido já está salvo nesta conta, deixando o acompanhamento mais claro agora "
        "e o caminho mais simples quando você quiser voltar a comprar."
        f"{latest_copy}"
    )


def _profile_continuity_copy(*, total_orders: int, address_count: int, order_updates_opt_in: bool, latest_recent_hint: str) -> dict[str, str]:
    if total_orders > 1:
        page_description = (
            f"Revise seus dados para manter {total_orders} pedidos e {address_count or 0} endereços salvos sempre prontos para a próxima compra."
        )
        if latest_recent_hint:
            page_description = f"{page_description} {latest_recent_hint}."
        return {
            "page_description": page_description,
            "personal_info_description": "Seus dados pessoais ajudam a manter o histórico da conta consistente entre pedidos, entregas e novas visitas.",
            "preferences_description": (
                "Suas preferências mantêm a conta alinhada ao acompanhamento dos pedidos e aos retornos futuros."
                if order_updates_opt_in
                else "Ative os avisos de pedido quando quiser acompanhar novas compras com menos esforço."
            ),
        }
    if total_orders == 1:
        page_description = "Revise seus dados para deixar seu primeiro pedido, seus contatos e sua próxima compra sempre alinhados nesta conta."
        if latest_recent_hint:
            page_description = f"{page_description} {latest_recent_hint}."
        return {
            "page_description": page_description,
            "personal_info_description": "Seus dados pessoais deixam o histórico da conta mais confiável para acompanhar o pedido atual e facilitar o próximo retorno.",
            "preferences_description": (
                "Mantenha os avisos ativos para acompanhar o andamento do pedido atual sem perder atualizações importantes."
                if order_updates_opt_in
                else "Você pode ativar avisos de pedido quando quiser receber novidades do pedido atual com mais tranquilidade."
            ),
        }
    return {
        "page_description": "Revise seus dados, mantenha o contato atualizado e escolha como prefere receber novidades e avisos dos pedidos.",
        "personal_info_description": "Dados básicos da conta do cliente.",
        "preferences_description": "Defina como deseja receber novidades e atualizações.",
    }


def _addresses_continuity_description(*, address_count: int, total_orders: int, default_address_title: str) -> str:
    default_copy = f" O endereço principal atual é {default_address_title}." if default_address_title else ""
    if address_count > 1 and total_orders > 0:
        return (
            f"Você já tem {address_count} endereços salvos nesta conta para acelerar próximas compras e acompanhar entregas com mais tranquilidade."
            f"{default_copy}"
        )
    if address_count == 1 and total_orders > 0:
        return (
            "Seu endereço salvo já ajuda a deixar o pedido atual e a próxima compra mais simples de confirmar."
            f"{default_copy}"
        )
    if address_count > 0:
        return f"Gerencie seus endereços salvos para manter entregas e futuras compras organizadas.{default_copy}"
    return "Adicione um endereço para deixar suas próximas compras mais rápidas e manter a conta pronta para novas entregas."


def _return_to_catalog_guidance(*, total_orders: int, status_label: str = "", shipping_status: str = "") -> str:
    lowered_status = status_label.lower()
    lowered_shipping = shipping_status.lower()
    if "cancel" in lowered_status:
        return "Quando fizer sentido retomar, o catálogo continua sendo o melhor ponto para começar uma nova compra com calma."
    if "entreg" in lowered_shipping:
        return "Seu pedido já foi concluído e o catálogo continua disponível para uma próxima compra quando você quiser voltar."
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return (
            "Enquanto a entrega avança, você pode voltar ao catálogo quando quiser explorar a próxima compra sem perder o histórico desta conta."
        )
    if total_orders > 1:
        return "Quando quiser comprar de novo, o catálogo continua disponível para você explorar novidades sem perder o histórico já salvo."
    if total_orders == 1:
        return "Quando quiser dar o próximo passo, o catálogo segue disponível para você explorar novos produtos com a conta já preparada."
    return "Quando estiver pronta para começar, o catálogo continua disponível para explorar produtos e iniciar sua próxima compra."


def _recency_hint(value: object) -> str:
    if not isinstance(value, datetime):
        return ""
    aware_value = timezone.localtime(value) if timezone.is_aware(value) else value
    now = timezone.localtime(timezone.now())
    delta_days = (now.date() - aware_value.date()).days
    if delta_days <= 0:
        return "Atualizado hoje"
    if delta_days == 1:
        return "Atualizado ontem"
    return f"Atualizado há {delta_days} dias"


def _customer_status_summary(status_label: str, payment_status: str, shipping_status: str) -> str:
    return f"{status_label} · pagamento {payment_status.lower()} · entrega {shipping_status.lower()}"


def _current_state_helper(*, status_label: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> str:
    lowered_payment = payment_status.lower()
    lowered_shipping = shipping_status.lower()
    lowered_fulfillment = fulfillment_status_label.lower()
    lowered_status = status_label.lower()
    if "cancel" in lowered_status:
        return "Seu pedido foi encerrado e não terá novas movimentações enquanto permanecer cancelado."
    if "entreg" in lowered_shipping or "conclu" in lowered_fulfillment:
        return "Seu pedido já foi entregue e encerrado com sucesso, então agora ele fica disponível aqui como histórico da sua conta."
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return "Seu pagamento já foi confirmado e o pedido segue em deslocamento até a entrega."
    if "prepar" in lowered_shipping or "separ" in lowered_fulfillment:
        return "Seu pagamento já foi aprovado e nosso time está preparando o pacote para envio."
    if "confirm" in lowered_payment or "pago" in lowered_status:
        return "Seu pedido está confirmado e aguardando a próxima atualização operacional."
    return "Estamos acompanhando o pedido e avisaremos assim que houver uma nova atualização importante."


def _customer_order_summary(order_number: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> str:
    return (
        f"Pedido #{order_number} com pagamento {payment_status.lower()}, "
        f"entrega em {shipping_status.lower()} e operação em {fulfillment_status_label.lower()}."
    )


def _customer_order_note(notes_content: str, shipping_address_summary: str) -> str:
    base = f"Entrega prevista para {shipping_address_summary}."
    if notes_content and notes_content != "Sem observações adicionais para este pedido.":
        return f"{base} {notes_content}"
    return base


def _timeline_items(updated_at: str, *, order_status_label: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> list[dict[str, object]]:
    state_helper = _current_state_helper(
        status_label=order_status_label,
        payment_status=payment_status,
        shipping_status=shipping_status,
        fulfillment_status_label=fulfillment_status_label,
    )
    next_step = _customer_order_next_step(
        status_label=order_status_label,
        payment_status=payment_status,
        shipping_status=shipping_status,
        fulfillment_status_label=fulfillment_status_label,
    )
    delivered = "entreg" in shipping_status.lower() or "conclu" in fulfillment_status_label.lower()
    return [
        {
            "title": "Pedido concluído" if delivered else "Status atual confirmado",
            "description": f"Seu pedido está {order_status_label.lower()} e a etapa operacional atual é {fulfillment_status_label.lower()}. {state_helper}",
            "timestamp": updated_at,
            "badge_label": "Entrega" if delivered else "Pedido",
            "badge_variant": "success" if delivered else "info",
        },
        {
            "title": "Entrega concluída" if delivered else "Pagamento e entrega acompanhados",
            "description": f"Pagamento {payment_status.lower()} e entrega em {shipping_status.lower()}, com acompanhamento contínuo pela área do cliente.",
            "timestamp": updated_at,
            "badge_label": "Entrega",
            "badge_variant": "success" if delivered else "shipped" if "trânsito" in shipping_status.lower() else "paid",
        },
        {
            "title": "Próximo passo esperado",
            "description": next_step,
            "timestamp": updated_at,
            "badge_label": "Próximo passo",
            "badge_variant": "info",
        },
    ]


def _retention_activity_item(*, updated_at: str, description: str) -> dict[str, object]:
    return {
        "title": "Histórico salvo na sua conta",
        "description": description,
        "timestamp": updated_at,
        "badge_label": "Conta",
        "badge_variant": "info",
    }


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
            profile = (
                self.profile_model._default_manager.select_related("customer")
                .filter(is_active=True)
                .order_by("-updated_at", "-id")
                .first()
            )
        except Exception:
            return None
        if not profile:
            return None
        return {
            "tenant_id": getattr(profile, "tenant_id", None),
            "customer_id": getattr(profile, "customer_id", None),
            "customer_linkage_mode": "explicit" if getattr(profile, "customer_id", None) else "fallback",
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
        if not tenant_id:
            return None
        customer = self._resolve_customer(profile)
        try:
            if customer is not None and hasattr(self.order_model, "customer_id"):
                explicit_queryset = (
                    self.order_model._default_manager.filter(tenant_id=tenant_id, customer_id=customer.pk)
                    .prefetch_related("items")
                    .order_by("-updated_at", "-id")
                )
                if explicit_queryset.exists():
                    return explicit_queryset
            if not email:
                return None
            return (
                self.order_model._default_manager.filter(tenant_id=tenant_id, customer_email=email)
                .prefetch_related("items")
                .order_by("-updated_at", "-id")
            )
        except Exception:
            return None

    def _resolve_customer(self, profile: dict[str, object]):
        tenant_id = profile.get("tenant_id")
        customer_id = profile.get("customer_id")
        email = str(profile.get("email") or "").strip()
        if not tenant_id:
            return None
        try:
            if customer_id:
                linked_customer = (
                    self.customer_model._default_manager.filter(tenant_id=tenant_id, pk=customer_id)
                    .prefetch_related("addresses")
                    .first()
                )
                if linked_customer is not None:
                    return linked_customer
            if not email:
                return None
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

        summary_content = _customer_order_summary(
            self._string_value(getattr(order, "number", None), default="0000"),
            payment_status,
            shipping_status,
            fulfillment_status_label,
        )
        order_status_summary = _customer_status_summary(order_status_label, payment_status, shipping_status)
        summary_note = _customer_order_note(notes_content, shipping_address_summary)
        state_helper = _current_state_helper(
            status_label=order_status_label,
            payment_status=payment_status,
            shipping_status=shipping_status,
            fulfillment_status_label=fulfillment_status_label,
        )
        recent_update_hint = _recency_hint(getattr(order, "updated_at", None))
        page_meta = f"Entrega em {shipping_address_summary} · última atualização em {updated_at}"
        if recent_update_hint:
            page_meta = f"{page_meta} · {recent_update_hint.lower()}"

        return {
            "order_number": self._string_value(getattr(order, "number", None), default="0000"),
            "customer_linkage_mode": "explicit" if getattr(order, "customer_id", None) else "fallback",
            "status": "processing" if status == "pending" else status,
            "order_status_label": order_status_label,
            "order_status_variant": order_status_variant,
            "order_status_summary": order_status_summary,
            "recent_update_hint": recent_update_hint,
            "current_state_helper": state_helper,
            "payment_status": payment_status,
            "shipping_status": shipping_status,
            "fulfillment_status_label": fulfillment_status_label,
            "updated_at": updated_at,
            "summary_content": summary_content,
            "page_meta": page_meta,
            "subtotal": self._money_value(getattr(order, "subtotal", None)),
            "shipping": self._money_value(getattr(order, "shipping_total", None)),
            "discount": self._money_value(getattr(order, "discount_total", None), allow_empty=True),
            "installments": self._string_value(getattr(order, "installments_summary", None), default=""),
            "total": self._money_value(getattr(order, "total", None)),
            "summary_note": f"{state_helper} {summary_note}",
            "order_items": items,
            "activity_items": _timeline_items(
                updated_at,
                order_status_label=order_status_label,
                payment_status=payment_status,
                shipping_status=shipping_status,
                fulfillment_status_label=fulfillment_status_label,
            ),
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
            "address_id": getattr(address, "pk", None),
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

    def get_linkage_visibility(self) -> dict[str, str]:
        profile = self._profile()
        profile_mode = str(profile.get("customer_linkage_mode") or "fixture")
        orders_mode = "fixture"
        addresses_mode = "fixture"
        orders = self.area_repository.list_orders(profile)
        if orders:
            orders_mode = "explicit" if all(order.get("customer_linkage_mode") == "explicit" for order in orders) else "fallback"
        elif self.using_persisted_orders_source():
            orders_mode = "fallback"
        if self.area_repository.get_addresses(profile):
            addresses_mode = "explicit" if profile_mode == "explicit" else "fallback"
        elif self.using_persisted_addresses_source():
            addresses_mode = "fallback"
        return {
            "profile_mode": profile_mode,
            "orders_mode": orders_mode,
            "addresses_mode": addresses_mode,
        }

    def _profile(self) -> dict[str, object]:
        return self.profile_repository.get_primary_profile() or self.fallback_profile_repository.get_primary_profile()

    def get_active_profile_context(self) -> dict[str, object]:
        return dict(self._profile())

    def list_orders(self) -> list[dict[str, object]]:
        profile = self._profile()
        real_orders = self.area_repository.list_orders(profile)
        orders = real_orders or self.fallback_area_repository.list_orders(profile)
        persisted = bool(real_orders)
        latest_recent_hint = str((orders[0] if orders else {}).get("recent_update_hint") or "")
        retention = _retention_signals(
            total_orders=len(orders),
            latest_recent_hint=latest_recent_hint,
            persisted=persisted,
        )
        enriched_orders: list[dict[str, object]] = []
        for index, order in enumerate(orders):
            enriched_order = dict(order)
            enriched_order["reengagement_hint"] = _customer_order_continuity_hint(
                total_orders=len(orders),
                order_index=index,
                status_label=str(enriched_order.get("order_status_label") or ""),
                shipping_status=str(enriched_order.get("shipping_status") or ""),
                recent_update_hint=str(enriched_order.get("recent_update_hint") or ""),
                fallback_hint=retention["row_hint"],
            )
            next_step = _customer_order_next_step(
                status_label=str(enriched_order.get("order_status_label") or ""),
                payment_status=str(enriched_order.get("payment_status") or ""),
                shipping_status=str(enriched_order.get("shipping_status") or ""),
                fulfillment_status_label=str(enriched_order.get("fulfillment_status_label") or ""),
            )
            enriched_order["next_step_hint"] = next_step
            if enriched_order.get("activity_items"):
                enriched_order["activity_items"] = list(enriched_order["activity_items"]) + [
                    _retention_activity_item(
                        updated_at=str(enriched_order.get("updated_at") or "agora"),
                        description=retention["activity_description"],
                    )
                ]
            enriched_order["summary_note"] = (
                f'{enriched_order.get("summary_note", "").strip()} {next_step} {retention["detail_note"]}'.strip()
            )
            enriched_orders.append(enriched_order)
        return enriched_orders

    def get_order(self, order_number: str) -> dict[str, object]:
        normalized = order_number.lstrip("#")
        for order in self.list_orders():
            if str(order.get("order_number") or "") == normalized:
                return order
        profile = self._profile()
        real_order = self.area_repository.get_order(profile, order_number)
        if real_order:
            return real_order
        fallback_order = self.fallback_area_repository.get_order(profile, order_number)
        if fallback_order:
            return fallback_order
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
        linkage_visibility = self.get_linkage_visibility()
        orders = self.list_orders()
        catalog_guidance = _return_to_catalog_guidance(total_orders=len(orders))
        latest_recent_hint = str((orders[0] if orders else {}).get("recent_update_hint") or "")
        retention = _retention_signals(
            total_orders=len(orders),
            latest_recent_hint=latest_recent_hint,
            persisted=self.using_persisted_orders_source(),
        )
        return {
            "page_title": "Meus pedidos",
            "page_description": _customer_orders_continuity_description(
                total_orders=len(orders),
                persisted=self.using_persisted_orders_source(),
                latest_recent_hint=latest_recent_hint,
            ),
            "search_name": "q",
            "status_name": "status",
            "status_options": _customer_order_status_options(),
            "operational_linkage_visibility": linkage_visibility,
            "table_description": f'{retention["table_description"]} {catalog_guidance}'.strip(),
            "empty_description": catalog_guidance,
            "order_columns": [
                {"label": "Pedido"},
                {"label": "Status"},
                {"label": "Pagamento"},
                {"label": "Entrega"},
                {"label": "Data"},
            ],
        }

    def get_order_detail_page_data(self, order_number: str, *, confirmation_mode: bool = False) -> dict[str, object]:
        order = self.get_order(order_number)
        total_orders = len(self.list_orders())
        next_step_hint = str(order.get("next_step_hint") or "")
        payment_status = str(order.get("payment_status") or "")
        order_status = str(order.get("status") or "")
        catalog_guidance = _return_to_catalog_guidance(
            total_orders=total_orders,
            status_label=str(order.get("order_status_label") or ""),
            shipping_status=str(order.get("shipping_status") or ""),
        )
        payment_progression_available = order_status in {"pending", "processing"} and "pendente" in payment_status.lower()
        continuity_description = (
            "Seu histórico continua salvo nesta conta para facilitar novas consultas e uma próxima compra quando fizer sentido."
            if total_orders > 1
            else "Este pedido já deixa sua conta pronta para um próximo retorno sempre que você quiser acompanhar ou comprar de novo."
        )
        payload = {
            "page_title": f'Pedido #{order["order_number"]}',
            "page_description": f"{next_step_hint} {continuity_description} {catalog_guidance}".strip(),
            "page_meta": order.get("page_meta") or "Área do cliente · acompanhe pagamentos, envio e entregas em um só lugar.",
            "eyebrow": "Customer Area",
            "summary_title": "Resumo do pedido",
            "order_status_label": order["order_status_label"],
            "order_status_variant": order["order_status_variant"],
            "status_title": "Status atual",
            "order_number": f'#{order["order_number"]}',
            "payment_status": order["payment_status"],
            "shipping_status": order["shipping_status"],
            "summary_subtitle": (
                f'{order.get("recent_update_hint")} · {next_step_hint}'
                if order.get("recent_update_hint") and next_step_hint
                else order.get("recent_update_hint") or order.get("order_status_summary", "Resumo rápido do pedido.")
            ),
            "summary_content": order["summary_content"],
            "order_items": order["order_items"],
            "subtotal": order["subtotal"],
            "shipping": order["shipping"],
            "discount": order["discount"],
            "installments": order["installments"],
            "total": order["total"],
            "summary_note": f'{order.get("summary_note", "")} {catalog_guidance}'.strip(),
            "activity_items": order["activity_items"],
            "activity_description": catalog_guidance,
            "activity_title": "Linha do tempo",
            "operational_linkage_mode": order.get("customer_linkage_mode", "fixture"),
            "payment_progression_available": payment_progression_available,
            "payment_progression_label": "Confirmar pagamento" if payment_progression_available else "",
            "payment_progression_helper": (
                "Finalize a evolução inicial deste pedido para liberar a preparação e as próximas atualizações de envio."
                if payment_progression_available
                else ""
            ),
        }
        if confirmation_mode:
            confirmation_step = (
                "Seu pedido foi iniciado com sucesso e agora entra em acompanhamento pela conta."
            )
            payload.update(
                {
                    "eyebrow": "Confirmação inicial do pedido",
                    "page_description": (
                        f"{confirmation_step} "
                        "Esta é a confirmação inicial do checkout, antes da evolução real do pagamento. "
                        f"{next_step_hint}"
                    ).strip(),
                    "page_meta": "Pedido iniciado no checkout · acompanhe por aqui a evolução de pagamento, preparo e entrega.",
                    "summary_title": "Pedido iniciado com sucesso",
                    "status_title": "Confirmação inicial",
                    "summary_subtitle": (
                        f'{order.get("recent_update_hint")} · aguardando evolução do pagamento'
                        if order.get("recent_update_hint")
                        else "Aguardando evolução do pagamento"
                    ),
                    "summary_note": (
                        "Este é o primeiro registro persistido do seu pedido. "
                        "Pagamento, preparo e envio passam a aparecer por aqui conforme o fluxo evoluir."
                    ),
                    "activity_title": "Próximas atualizações do pedido",
                    "activity_description": (
                        "Acompanhe aqui a confirmação do pagamento, o início da preparação e as próximas movimentações do pedido."
                    ),
                }
            )
        return payload

    def get_addresses_page_data(self) -> dict[str, object]:
        profile = self._profile()
        addresses = self.area_repository.get_addresses(profile) or self.fallback_area_repository.get_addresses(profile)
        orders = self.list_orders()
        default_address_title = next(
            (
                str(address.get("title") or "")
                for address in addresses
                if "principal" in str(address.get("subtitle") or "").lower()
            ),
            "",
        )
        return {
            "page_title": "Meus endereços",
            "page_description": _addresses_continuity_description(
                address_count=len(addresses),
                total_orders=len(orders),
                default_address_title=default_address_title,
            ),
            "addresses": addresses,
            "operational_linkage_visibility": self.get_linkage_visibility(),
        }

    def get_profile_page_data(self) -> dict[str, object]:
        profile = self._profile()
        orders = self.list_orders()
        addresses = self.area_repository.get_addresses(profile) or self.fallback_area_repository.get_addresses(profile)
        profile_copy = _profile_continuity_copy(
            total_orders=len(orders),
            address_count=len(addresses),
            order_updates_opt_in=bool(profile["order_updates_opt_in"]),
            latest_recent_hint=str((orders[0] if orders else {}).get("recent_update_hint") or ""),
        )
        return {
            "page_title": "Meu perfil",
            "page_description": profile_copy["page_description"],
            "personal_info_description": profile_copy["personal_info_description"],
            "preferences_description": profile_copy["preferences_description"],
            "first_name": profile["first_name"],
            "last_name": profile["last_name"],
            "email": profile["email"],
            "phone": profile["phone"],
            "newsletter_opt_in": profile["newsletter_opt_in"],
            "order_updates_opt_in": profile["order_updates_opt_in"],
            "operational_linkage_mode": profile.get("customer_linkage_mode", "fixture"),
        }


account_customer_area_queries = AccountCustomerAreaQueryService(
    profile_repository=DjangoOrmAccountProfileRepository(),
    fallback_profile_repository=FallbackAccountProfileRepository(),
    area_repository=DjangoOrmCustomerAreaRepository(),
    fallback_area_repository=FallbackCustomerAreaRepository(),
)
