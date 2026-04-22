from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Protocol

from django.db import connection
from django.utils import timezone

from app.modules.payments.application.payment_attempt_queries import payment_attempt_queries

def _customer_order_status_options() -> list[dict[str, str]]:
    return [
        {"value": "paid", "label": "Pago"},
        {"value": "processing", "label": "Em preparação"},
        {"value": "shipped", "label": "Enviado"},
    ]


def _retention_signals(*, total_orders: int, latest_recent_hint: str, persisted: bool) -> dict[str, str]:
    if not persisted or total_orders <= 0:
        return {
            "orders_page_description": "Use esta lista para localizar rapidamente o pedido certo, acompanhar a etapa atual e entender os próximos passos de cada compra.",
            "table_description": "Cada pedido mostra um resumo curto da etapa atual para ajudar você a abrir mais rápido o acompanhamento certo.",
            "row_hint": "",
            "detail_note": "Seu histórico continuará salvo na conta para facilitar novos acompanhamentos quando precisar voltar.",
            "activity_description": "Seu histórico fica salvo na conta para facilitar consultas futuras sempre que você quiser voltar.",
        }
    if total_orders > 1:
        recency_copy = f" Última movimentação: {latest_recent_hint.lower()}." if latest_recent_hint else ""
        return {
            "orders_page_description": f"Você já tem mais de um pedido salvo nesta conta, então ficou mais simples localizar o pedido mais importante do momento e retomar o acompanhamento certo.{recency_copy}",
            "table_description": "Seus pedidos continuam reunidos aqui para ajudar você a identificar a etapa principal de cada compra e abrir o detalhe certo mais rápido.",
            "row_hint": "cliente recorrente",
            "detail_note": "Você já voltou a comprar por aqui antes, então este histórico permanece salvo para facilitar sua próxima visita.",
            "activity_description": "Seu histórico mostra compras anteriores e deixa o retorno mais simples sempre que você quiser explorar de novo.",
        }
    recency_copy = f" {latest_recent_hint}." if latest_recent_hint else ""
    return {
        "orders_page_description": f"Seu primeiro pedido já está salvo nesta conta e agora pode ser acompanhado por aqui com mais clareza.{recency_copy}",
        "table_description": "Este pedido já aparece com a etapa principal da jornada para ajudar você a retomar o acompanhamento sem esforço.",
        "row_hint": "pedido recebido",
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
    if "falhou" in lowered_payment:
        return "O pagamento não avançou nesta tentativa. O pedido continua salvo e o próximo passo seguro é retomar uma nova tentativa de pagamento."
    if "confirm" in lowered_payment or "pago" in lowered_status:
        return "Seu pedido já está confirmado e a próxima atualização deve mostrar o avanço da preparação para envio."
    return "Assim que houver uma nova atualização importante, ela aparecerá aqui para você seguir acompanhando com tranquilidade."


def _customer_order_milestone_title(*, status_label: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> str:
    lowered_payment = payment_status.lower()
    lowered_shipping = shipping_status.lower()
    lowered_fulfillment = fulfillment_status_label.lower()
    lowered_status = status_label.lower()
    if "entreg" in lowered_shipping or "conclu" in lowered_fulfillment:
        return "Pedido entregue"
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return "Pedido enviado"
    if "prepar" in lowered_shipping or "separ" in lowered_fulfillment:
        return "Pedido em preparação"
    if "confirm" in lowered_payment or "pago" in lowered_status:
        return "Pagamento aprovado"
    return "Pedido recebido"


def _customer_order_continuity_hint(
    *,
    total_orders: int,
    order_index: int,
    status_label: str,
    shipping_status: str,
    recent_update_hint: str,
    fallback_hint: str,
) -> str:
    lowered_payment = recent_update_hint.lower()
    lowered_shipping = shipping_status.lower()
    lowered_status = status_label.lower()
    if "entreg" in lowered_shipping:
        return "pedido entregue"
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return "acompanhe a entrega"
    if "prepar" in lowered_shipping:
        return "pedido em preparação"
    if "pago" in lowered_status:
        return "pagamento aprovado"
    if "cancel" in lowered_status:
        return "histórico preservado"
    if total_orders > 1 and order_index == 0:
        return "pedido mais recente"
    if total_orders > 1:
        return "compra anterior salva"
    if "atualizado" in lowered_payment:
        return fallback_hint
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


def _profile_continuity_copy(
    *,
    total_orders: int,
    address_count: int,
    order_updates_opt_in: bool,
    latest_recent_hint: str,
    profile_mode: str,
) -> dict[str, str]:
    if profile_mode == "missing":
        page_description = (
            "Ainda não encontramos um perfil persistido nesta conta. "
            "Você pode preencher seus dados agora e manter pedidos, endereços e próximas compras mais organizados."
        )
        if latest_recent_hint:
            page_description = f"{page_description} {latest_recent_hint}."
        return {
            "page_description": page_description,
            "personal_info_description": (
                "Assim que você salvar seus dados, esta conta passa a manter uma identidade persistida mais clara para acompanhamento e próximas compras."
            ),
            "preferences_description": (
                "Você também pode definir como prefere receber novidades e atualizações quando esse perfil já estiver persistido."
            ),
        }
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


def _return_to_buy_readiness(*, total_orders: int, status_label: str = "", shipping_status: str = "") -> dict[str, str]:
    lowered_status = status_label.lower()
    lowered_shipping = shipping_status.lower()
    if "entreg" in lowered_shipping:
        return {
            "title": "Pronta para voltar ao catálogo",
            "description": "Este pedido já foi concluído e o histórico ficou salvo na sua conta. Quando fizer sentido, o catálogo continua sendo o melhor ponto para iniciar a próxima compra.",
        }
    if "trânsito" in lowered_shipping or "enviado" in lowered_status:
        return {
            "title": "Catálogo segue disponível",
            "description": "Enquanto esta entrega avança, você ainda pode voltar ao catálogo quando quiser explorar a próxima compra com o histórico desta conta preservado.",
        }
    if total_orders > 1:
        return {
            "title": "Conta pronta para uma nova compra",
            "description": "Seu histórico já está organizado nesta conta, então o catálogo continua disponível para uma nova compra sem perder o contexto dos pedidos anteriores.",
        }
    if total_orders == 1:
        return {
            "title": "Primeira compra já registrada",
            "description": "Seu primeiro pedido já deixou a conta pronta para um próximo retorno, e o catálogo continua disponível quando você quiser comprar de novo.",
        }
    return {
        "title": "Catálogo disponível",
        "description": "Quando quiser começar, o catálogo continua disponível para explorar produtos e iniciar sua próxima compra.",
    }


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
    milestone_title = _customer_order_milestone_title(
        status_label=status_label,
        payment_status=payment_status,
        shipping_status=shipping_status,
        fulfillment_status_label="",
    )
    return f"{milestone_title} · pagamento {payment_status.lower()} · entrega {shipping_status.lower()}"


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
    if "falhou" in lowered_payment:
        return "Recebemos uma falha na tentativa de pagamento, mas o pedido continua salvo para uma retomada segura."
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


def _payment_source_fallback(payment_status: str) -> str:
    lowered_payment = payment_status.lower()
    if "pendente" in lowered_payment:
        return "Checkout aguardando pagamento"
    if "falhou" in lowered_payment:
        return "Falha de pagamento"
    if "confirmado" in lowered_payment or "aprovado" in lowered_payment:
        return "Confirmação interna"
    return ""


def _pending_recovery_guidance(
    *,
    stale_state: str,
    stale_title: str,
    hosted_payment_available: bool,
    payment_retry_available: bool,
    provider_label: str,
) -> dict[str, str]:
    normalized_state = stale_state.lower()
    if not normalized_state:
        return {}

    provider_copy = provider_label or "gateway externo"
    variant = "danger" if normalized_state == "critical" else "warning"
    if hosted_payment_available:
        return {
            "variant": variant,
            "title": stale_title or "Tentativa pendente sem atualização recente",
            "description": (
                f"A tentativa continua aberta há mais tempo do que o esperado. "
                f"O próximo passo mais seguro agora é reabrir o pagamento hospedado em {provider_copy} "
                "antes de criar outra retomada."
            ),
            "action_label": "Retomar pagamento hospedado",
            "action_helper": (
                f"Reabra o checkout hospedado de {provider_copy} para confirmar se esta tentativa ainda pode avançar com segurança."
            ),
        }
    if payment_retry_available:
        return {
            "variant": variant,
            "title": stale_title or "Tentativa pendente sem atualização recente",
            "description": (
                "A tentativa atual já ficou tempo demais sem evolução. "
                "O próximo passo mais seguro agora é iniciar uma nova tentativa de pagamento."
            ),
            "action_label": "Tentar pagamento novamente",
            "action_helper": "Abra uma nova tentativa para seguir com um fluxo limpo e evitar retomar um estado possivelmente órfão.",
        }
    return {
        "variant": variant,
        "title": stale_title or "Tentativa pendente sem atualização recente",
        "description": (
            "A tentativa atual ficou aberta por tempo demais e não tem uma retomada automática clara agora. "
            "O pedido continua salvo, mas este estado já merece revisão operacional antes de qualquer novo passo."
        ),
        "action_label": "",
        "action_helper": "",
    }


def _order_pending_recovery_guidance(
    *,
    order_status: str,
    payment_status: str,
    updated_at_value: object,
    hosted_payment_available: bool,
    payment_retry_available: bool,
) -> dict[str, str]:
    normalized_order_status = order_status.lower()
    normalized_payment_status = payment_status.lower()
    if normalized_order_status not in {"pending", "processing"}:
        return {}
    if "confirm" in normalized_payment_status or "pago" in normalized_payment_status:
        return {}

    if not isinstance(updated_at_value, datetime):
        return {}
    updated_at = timezone.localtime(updated_at_value) if timezone.is_aware(updated_at_value) else updated_at_value
    delta = timezone.localtime(timezone.now()) - updated_at
    if delta < timedelta(days=1):
        return {}

    age_label = "há 1 dia" if delta.days == 1 else f"há {max(delta.days, 1)} dias"
    if hosted_payment_available:
        return {
            "variant": "warning",
            "title": "Pedido pendente sem avanço recente",
            "description": (
                f"Este pedido continua pendente {age_label} e ainda pode ser retomado pelo pagamento hospedado. "
                "Vale tentar essa retomada antes de tratar o caso como abandono."
            ),
        }
    if payment_retry_available:
        return {
            "variant": "warning",
            "title": "Pedido pendente sem avanço recente",
            "description": (
                f"Este pedido continua pendente {age_label} e a retomada mais segura agora é abrir uma nova tentativa de pagamento."
            ),
        }
    return {
        "variant": "warning",
        "title": "Pedido pendente sem avanço recente",
        "description": (
            f"Este pedido continua pendente {age_label} sem evolução clara de pagamento ou entrega. "
            "O caso já merece revisão operacional antes de qualquer novo passo manual."
        ),
    }


def _timeline_items(updated_at: str, *, order_status_label: str, payment_status: str, shipping_status: str, fulfillment_status_label: str) -> list[dict[str, object]]:
    milestone_title = _customer_order_milestone_title(
        status_label=order_status_label,
        payment_status=payment_status,
        shipping_status=shipping_status,
        fulfillment_status_label=fulfillment_status_label,
    )
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
            "title": milestone_title,
            "description": f"Seu pedido está {order_status_label.lower()} e a etapa operacional atual é {fulfillment_status_label.lower()}. {state_helper}",
            "timestamp": updated_at,
            "badge_label": "Entrega" if delivered else "Pedido",
            "badge_variant": "success" if delivered else "info",
        },
        {
            "title": "Jornada concluída" if delivered else "Andamento de pagamento e entrega",
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
    def get_primary_profile(self, *, tenant_id: int | None = None) -> dict[str, object] | None:
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

    def get_primary_profile(self, *, tenant_id: int | None = None) -> dict[str, object] | None:
        if not self.is_ready():
            return None
        try:
            queryset = self.profile_model._default_manager.select_related("customer").filter(is_active=True)
            if tenant_id:
                queryset = queryset.filter(tenant_id=tenant_id)
            profile = queryset.order_by("-updated_at", "-id").first()
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
        updated_at_value = getattr(order, "updated_at", None)
        updated_at = self._format_timestamp(updated_at_value)
        payment_status = self._string_value(getattr(order, "payment_status", None), default="Indisponível")
        payment_source_label = self._string_value(getattr(order, "payment_source_label", None), default="")
        if not payment_source_label:
            payment_source_label = _payment_source_fallback(payment_status)
        payment_reference = self._string_value(getattr(order, "payment_reference", None), default="")
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
            "payment_source_label": payment_source_label,
            "payment_reference": payment_reference,
            "shipping_status": shipping_status,
            "fulfillment_status_label": fulfillment_status_label,
            "updated_at": updated_at,
            "updated_at_value": updated_at_value,
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
    def get_primary_profile(self, *, tenant_id: int | None = None) -> dict[str, object]:
        return {
            "tenant_id": None,
            "customer_id": None,
            "customer_linkage_mode": "fixture",
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

    @staticmethod
    def _allow_fixture_fallback(*, tenant_id: int | None) -> bool:
        return not bool(tenant_id)

    def using_persisted_profile_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            return self.profile_repository.get_primary_profile(tenant_id=tenant_id) is not None
        except Exception:
            return False

    def using_persisted_orders_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            return bool(self.area_repository.list_orders(self._profile(tenant_id=tenant_id)))
        except Exception:
            return False

    def using_persisted_addresses_source(self, *, tenant_id: int | None = None) -> bool:
        try:
            return bool(self.area_repository.get_addresses(self._profile(tenant_id=tenant_id)))
        except Exception:
            return False

    def get_linkage_visibility(self, *, tenant_id: int | None = None) -> dict[str, str]:
        profile = self._profile(tenant_id=tenant_id)
        profile_mode = str(profile.get("customer_linkage_mode") or "fixture")
        fallback_allowed = self._allow_fixture_fallback(tenant_id=tenant_id)
        orders_mode = "fixture" if fallback_allowed else "missing"
        addresses_mode = "fixture" if fallback_allowed else "missing"
        orders = self.area_repository.list_orders(profile)
        if orders:
            orders_mode = "explicit" if all(order.get("customer_linkage_mode") == "explicit" for order in orders) else "fallback"
        elif self.using_persisted_orders_source(tenant_id=tenant_id):
            orders_mode = "fallback"
        if self.area_repository.get_addresses(profile):
            addresses_mode = "explicit" if profile_mode == "explicit" else "fallback"
        elif self.using_persisted_addresses_source(tenant_id=tenant_id):
            addresses_mode = "fallback"
        return {
            "profile_mode": profile_mode,
            "orders_mode": orders_mode,
            "addresses_mode": addresses_mode,
        }

    def _profile(self, *, tenant_id: int | None = None) -> dict[str, object]:
        persisted_profile = self.profile_repository.get_primary_profile(tenant_id=tenant_id)
        if persisted_profile is not None:
            return persisted_profile
        if self._allow_fixture_fallback(tenant_id=tenant_id):
            return self.fallback_profile_repository.get_primary_profile(tenant_id=tenant_id)
        return {
            "tenant_id": tenant_id,
            "customer_id": None,
            "customer_linkage_mode": "missing",
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "newsletter_opt_in": False,
            "order_updates_opt_in": True,
        }

    def _identity_profile(self, *, tenant_id: int | None = None) -> dict[str, object]:
        persisted_profile = self.profile_repository.get_primary_profile(tenant_id=tenant_id)
        if persisted_profile is not None:
            return persisted_profile
        return {
            "tenant_id": tenant_id,
            "customer_id": None,
            "customer_linkage_mode": "missing",
            "first_name": "",
            "last_name": "",
            "email": "",
            "phone": "",
            "newsletter_opt_in": False,
            "order_updates_opt_in": True,
        }

    def get_active_profile_context(self, *, tenant_id: int | None = None) -> dict[str, object]:
        return dict(self._identity_profile(tenant_id=tenant_id))

    def list_orders(
        self,
        *,
        tenant_id: int | None = None,
        allow_fixture_fallback: bool = True,
    ) -> list[dict[str, object]]:
        profile = self._profile(tenant_id=tenant_id)
        real_orders = self.area_repository.list_orders(profile)
        orders = real_orders
        if not orders and allow_fixture_fallback and self._allow_fixture_fallback(tenant_id=tenant_id):
            orders = self.fallback_area_repository.list_orders(profile)
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

    def get_order(self, order_number: str, *, tenant_id: int | None = None) -> dict[str, object]:
        normalized = order_number.lstrip("#")
        for order in self.list_orders(tenant_id=tenant_id):
            if str(order.get("order_number") or "") == normalized:
                return order
        profile = self._profile(tenant_id=tenant_id)
        real_order = self.area_repository.get_order(profile, order_number)
        if real_order:
            return real_order
        if self._allow_fixture_fallback(tenant_id=tenant_id):
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

    def get_orders_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        linkage_visibility = self.get_linkage_visibility(tenant_id=tenant_id)
        orders = self.list_orders(tenant_id=tenant_id, allow_fixture_fallback=False)
        if not orders and not self.using_persisted_orders_source(tenant_id=tenant_id):
            linkage_visibility = {
                **linkage_visibility,
                "orders_mode": "missing",
            }
        catalog_guidance = _return_to_catalog_guidance(total_orders=len(orders))
        return_to_buy = _return_to_buy_readiness(total_orders=len(orders))
        latest_recent_hint = str((orders[0] if orders else {}).get("recent_update_hint") or "")
        retention = _retention_signals(
            total_orders=len(orders),
            latest_recent_hint=latest_recent_hint,
            persisted=self.using_persisted_orders_source(tenant_id=tenant_id),
        )
        return {
            "page_title": "Meus pedidos",
            "page_description": _customer_orders_continuity_description(
                total_orders=len(orders),
                persisted=self.using_persisted_orders_source(tenant_id=tenant_id),
                latest_recent_hint=latest_recent_hint,
            ),
            "search_name": "q",
            "status_name": "status",
            "status_options": _customer_order_status_options(),
            "operational_linkage_visibility": linkage_visibility,
            "table_description": f'{retention["table_description"]} {catalog_guidance}'.strip(),
            "page_meta": f'{return_to_buy["title"]} · {return_to_buy["description"]}',
            "empty_description": catalog_guidance,
            "order_columns": [
                {"label": "Pedido"},
                {"label": "Status"},
                {"label": "Pagamento"},
                {"label": "Entrega"},
                {"label": "Data"},
            ],
        }

    @staticmethod
    def _build_order_detail_reorder_payload(order: dict[str, object]) -> dict[str, object]:
        reorder_available = bool(order.get("order_items"))
        return {
            "reorder_lite_available": reorder_available,
            "reorder_lite_label": "Comprar novamente" if reorder_available else "",
            "reorder_lite_helper": (
                "Use este pedido como ponto de partida para recriar uma nova sessão com os itens ainda elegíveis."
                if reorder_available
                else ""
            ),
        }

    @staticmethod
    def _build_order_detail_payment_attempt_payload(
        payment_attempt_summary: dict[str, object] | None,
    ) -> dict[str, object]:
        summary = payment_attempt_summary or {}
        return {
            "payment_attempt_status": str(summary.get("status") or ""),
            "payment_attempt_provider_label": str(summary.get("provider_label") or ""),
            "payment_attempt_external_reference": str(summary.get("external_reference") or ""),
            "payment_attempt_checkout_session_key": str(summary.get("checkout_session_key") or ""),
            "payment_attempt_status_label": str(summary.get("status_label") or ""),
            "payment_attempt_operational_title": str(summary.get("operational_title") or ""),
            "payment_attempt_operational_description": str(summary.get("operational_description") or ""),
            "payment_attempt_created_at": str(summary.get("created_at") or ""),
            "payment_attempt_latest_event_title": str(summary.get("latest_event_title") or ""),
            "payment_attempt_latest_event_description": str(summary.get("latest_event_description") or ""),
            "payment_attempt_timeline_items": list(summary.get("timeline_items") or []),
            "payment_attempt_operational_visible": bool(summary),
        }

    @staticmethod
    def _build_order_detail_recovery_guidance_payload(
        *,
        pending_recovery: dict[str, str],
        order_pending_recovery: dict[str, str],
    ) -> dict[str, object]:
        return {
            "pending_recovery_visible": bool(pending_recovery),
            "pending_recovery_variant": str(pending_recovery.get("variant") or ""),
            "pending_recovery_title": str(pending_recovery.get("title") or ""),
            "pending_recovery_description": str(pending_recovery.get("description") or ""),
            "order_pending_recovery_visible": bool(order_pending_recovery),
            "order_pending_recovery_variant": str(order_pending_recovery.get("variant") or ""),
            "order_pending_recovery_title": str(order_pending_recovery.get("title") or ""),
            "order_pending_recovery_description": str(order_pending_recovery.get("description") or ""),
        }

    @staticmethod
    def _build_order_detail_actions_payload(
        *,
        payment_progression_available: bool,
        payment_retry_available: bool,
        hosted_payment_available: bool,
        hosted_payment: dict[str, object] | None,
        pending_recovery: dict[str, str],
    ) -> dict[str, object]:
        provider_label = str((hosted_payment or {}).get("provider_label") or "gateway externo")
        return {
            "payment_progression_available": payment_progression_available,
            "payment_progression_label": "Confirmar pagamento" if payment_progression_available else "",
            "payment_progression_helper": (
                "Finalize a evolução inicial deste pedido para liberar a preparação e as próximas atualizações de envio."
                if payment_progression_available
                else ""
            ),
            "payment_retry_available": payment_retry_available,
            "payment_retry_label": "Tentar pagamento novamente" if payment_retry_available else "",
            "payment_retry_helper": (
                "Recriamos uma nova sessão com este pedido para você revisar entrega e retomar o pagamento com segurança."
                if payment_retry_available
                else ""
            ),
            "hosted_payment_available": hosted_payment_available,
            "hosted_payment_attempt_key": str((hosted_payment or {}).get("attempt_key") or ""),
            "hosted_payment_label": (
                str(pending_recovery.get("action_label") or "Abrir pagamento hospedado")
                if hosted_payment_available
                else ""
            ),
            "hosted_payment_helper": (
                str(
                    pending_recovery.get("action_helper")
                    or f"Continue o pagamento em ambiente seguro de {provider_label}."
                )
                if hosted_payment_available
                else ""
            ),
        }

    @staticmethod
    def _build_order_detail_narrative_base_payload(
        *,
        order: dict[str, object],
        next_step_hint: str,
        continuity_description: str,
        catalog_guidance: str,
        return_to_buy: dict[str, str],
    ) -> dict[str, object]:
        return {
            "page_description": f"{next_step_hint} {continuity_description} {catalog_guidance}".strip(),
            "page_meta": (
                f'{order.get("page_meta", "").strip()} · {return_to_buy["title"]}'.strip(" ·")
                if order.get("page_meta")
                else f'Área do cliente · {return_to_buy["title"].lower()} · acompanhe pagamentos, envio e entregas em um só lugar.'
            ),
            "summary_subtitle": (
                f'{order.get("recent_update_hint")} · {next_step_hint}'
                if order.get("recent_update_hint") and next_step_hint
                else order.get("recent_update_hint") or order.get("order_status_summary", "Resumo rápido do pedido.")
            ),
            "summary_note": f'{order.get("summary_note", "")} {catalog_guidance}'.strip(),
            "activity_description": f'{catalog_guidance} {return_to_buy["description"]}'.strip(),
            "return_to_buy_title": return_to_buy["title"],
            "return_to_buy_description": return_to_buy["description"],
        }

    @staticmethod
    def _apply_order_detail_payment_narrative_enrichment(
        payload: dict[str, object],
        *,
        payment_status: str,
        order: dict[str, object],
    ) -> tuple[dict[str, object], str, str]:
        payment_source_label = str(order.get("payment_source_label") or "")
        if not payment_source_label:
            payment_source_label = _payment_source_fallback(payment_status)
        payment_reference = str(order.get("payment_reference") or "")
        if payment_source_label:
            reference_copy = f" Referência atual: {payment_reference}." if payment_reference else ""
            payload["summary_note"] = (
                f'{payload.get("summary_note", "").strip()} '
                f'Origem atual do pagamento: {payment_source_label.lower()}.{reference_copy}'
            ).strip()
            existing_meta = str(payload.get("page_meta", "") or "").strip()
            payload["page_meta"] = (
                f"{existing_meta} · pagamento via {payment_source_label.lower()}".strip(" ·")
                if existing_meta
                else f"Pagamento via {payment_source_label.lower()}"
            )
        return payload, payment_source_label, payment_reference

    @staticmethod
    def _apply_order_detail_attempt_narrative_enrichment(
        payload: dict[str, object],
        *,
        payment_attempt_summary: dict[str, object] | None,
    ) -> dict[str, object]:
        payment_attempt_status = str((payment_attempt_summary or {}).get("status") or "")
        payment_attempt_provider = str((payment_attempt_summary or {}).get("provider_label") or "")
        payment_attempt_event = str((payment_attempt_summary or {}).get("latest_event_title") or "")
        payment_attempt_reference = str((payment_attempt_summary or {}).get("external_reference") or "")
        payment_attempt_session_key = str((payment_attempt_summary or {}).get("checkout_session_key") or "")
        if not payment_attempt_status:
            return payload

        attempt_copy = f"Tentativa atual: {payment_attempt_status.lower()}"
        if payment_attempt_provider:
            attempt_copy = f"{attempt_copy} via {payment_attempt_provider.lower()}"
        if payment_attempt_reference:
            attempt_copy = f"{attempt_copy}. Referência da tentativa: {payment_attempt_reference}."
        else:
            attempt_copy = f"{attempt_copy}."
        if payment_attempt_session_key:
            attempt_copy = f"{attempt_copy} Sessão de origem: {payment_attempt_session_key}."
        if payment_attempt_event:
            attempt_copy = f"{attempt_copy} Último evento: {payment_attempt_event.lower()}."

        payload["summary_note"] = f'{payload.get("summary_note", "").strip()} {attempt_copy}'.strip()
        existing_meta = str(payload.get("page_meta", "") or "").strip()
        payload["page_meta"] = (
            f"{existing_meta} · tentativa {str((payment_attempt_summary or {}).get('status_label') or payment_attempt_status).lower()}".strip(" ·")
            if existing_meta
            else f"Tentativa {str((payment_attempt_summary or {}).get('status_label') or payment_attempt_status).lower()}"
        )
        return payload

    @staticmethod
    def _build_order_detail_structural_payload(order: dict[str, object]) -> dict[str, object]:
        milestone_title = _customer_order_milestone_title(
            status_label=str(order.get("order_status_label") or ""),
            payment_status=str(order.get("payment_status") or ""),
            shipping_status=str(order.get("shipping_status") or ""),
            fulfillment_status_label=str(order.get("fulfillment_status_label") or ""),
        )
        return {
            "page_title": f'Pedido #{order["order_number"]}',
            "eyebrow": "Customer Area",
            "summary_title": milestone_title,
            "order_status_label": order["order_status_label"],
            "order_status_variant": order["order_status_variant"],
            "status_title": "Etapa atual do pedido",
            "order_number": f'#{order["order_number"]}',
            "payment_status": order["payment_status"],
            "payment_source_label": str(order.get("payment_source_label") or ""),
            "payment_reference": str(order.get("payment_reference") or ""),
            "shipping_status": order["shipping_status"],
            "summary_content": order["summary_content"],
            "order_items": order["order_items"],
            "subtotal": order["subtotal"],
            "shipping": order["shipping"],
            "discount": order["discount"],
            "installments": order["installments"],
            "total": order["total"],
            "activity_items": order["activity_items"],
            "activity_title": "Marcos do pedido",
            "operational_linkage_mode": order.get("customer_linkage_mode", "fixture"),
        }

    @staticmethod
    def _build_order_detail_confirmation_payload(
        *,
        order: dict[str, object],
        next_step_hint: str,
        payment_source_label: str,
        payment_reference: str,
    ) -> dict[str, object]:
        confirmation_payment_source_label = payment_source_label
        if "checkout" not in confirmation_payment_source_label.lower():
            confirmation_payment_source_label = "Checkout aguardando pagamento"
        confirmation_meta = (
            "Pedido iniciado no checkout · itens, entrega e pagamento já registrados · "
            "pagamento ainda pendente."
        )
        if confirmation_payment_source_label:
            confirmation_meta = f"{confirmation_meta} · origem: {confirmation_payment_source_label.lower()}"
        confirmation_summary_note = (
            f'{order.get("summary_note", "")} '
            "Este é o primeiro registro persistido do seu pedido. "
            "Pagamento, preparo e envio passam a aparecer por aqui conforme o fluxo evoluir. "
            "O pagamento ainda não foi confirmado nesta etapa."
        ).strip()
        if confirmation_payment_source_label:
            reference_copy = f" Referência atual: {payment_reference}." if payment_reference else ""
            confirmation_summary_note = (
                f"{confirmation_summary_note} "
                f"Origem atual do pagamento: {confirmation_payment_source_label.lower()}.{reference_copy}"
            ).strip()
        confirmation_step = "Seu pedido foi recebido com sucesso e agora entra em acompanhamento pela conta."
        return {
            "eyebrow": "Confirmação inicial do pedido",
            "page_description": (
                f"{confirmation_step} "
                "Itens, entrega e forma de pagamento da revisão já ficaram registrados. "
                "Esta ainda é a confirmação inicial do checkout, antes da evolução real do pagamento. "
                f"{next_step_hint}"
            ).strip(),
            "page_meta": confirmation_meta,
            "summary_title": "Pedido recebido com sucesso",
            "status_title": "Pedido recebido",
            "summary_subtitle": (
                f'{order.get("recent_update_hint")} · itens e entrega já registrados · aguardando evolução do pagamento'
                if order.get("recent_update_hint")
                else "Itens e entrega já registrados · aguardando evolução do pagamento"
            ),
            "summary_note": confirmation_summary_note,
            "activity_title": "Próximos marcos do pedido",
            "activity_description": (
                "Acompanhe aqui a confirmação do pagamento, o início da preparação e as próximas movimentações do pedido. "
                "Se nada mudou ainda, isso significa apenas que o pedido já foi registrado com segurança e aguarda a próxima evolução."
            ),
        }

    def get_order_detail_page_data(
        self,
        order_number: str,
        *,
        confirmation_mode: bool = False,
        tenant_id: int | None = None,
    ) -> dict[str, object]:
        order = self.get_order(order_number, tenant_id=tenant_id)
        total_orders = len(self.list_orders(tenant_id=tenant_id))
        next_step_hint = str(order.get("next_step_hint") or "")
        payment_status = str(order.get("payment_status") or "")
        order_status = str(order.get("status") or "")
        profile = self.get_active_profile_context(tenant_id=tenant_id)
        catalog_guidance = _return_to_catalog_guidance(
            total_orders=total_orders,
            status_label=str(order.get("order_status_label") or ""),
            shipping_status=str(order.get("shipping_status") or ""),
        )
        return_to_buy = _return_to_buy_readiness(
            total_orders=total_orders,
            status_label=str(order.get("order_status_label") or ""),
            shipping_status=str(order.get("shipping_status") or ""),
        )
        payment_progression_available = order_status in {"pending", "processing"} and "pendente" in payment_status.lower()
        payment_retry_available = order_status in {"pending", "processing"} and "falhou" in payment_status.lower()
        hosted_payment = payment_attempt_queries.get_latest_pending_hosted_payment(
            tenant_id=profile.get("tenant_id"),
            order_number=str(order.get("order_number") or order_number),
        )
        payment_attempt_summary = payment_attempt_queries.get_latest_attempt_summary(
            tenant_id=profile.get("tenant_id"),
            order_number=str(order.get("order_number") or order_number),
        )
        hosted_payment_available = (
            order_status in {"pending", "processing"}
            and hosted_payment is not None
        )
        pending_recovery = _pending_recovery_guidance(
            stale_state=str((payment_attempt_summary or {}).get("stale_state") or ""),
            stale_title=str((payment_attempt_summary or {}).get("stale_title") or ""),
            hosted_payment_available=hosted_payment_available,
            payment_retry_available=payment_retry_available,
            provider_label=str((payment_attempt_summary or {}).get("provider_label") or ""),
        )
        continuity_description = (
            "Seu histórico continua salvo nesta conta para facilitar novas consultas e uma próxima compra quando fizer sentido."
            if total_orders > 1
            else "Este pedido já deixa sua conta pronta para um próximo retorno sempre que você quiser acompanhar ou comprar de novo."
        )
        order_pending_recovery = _order_pending_recovery_guidance(
            order_status=order_status,
            payment_status=payment_status,
            updated_at_value=order.get("updated_at_value"),
            hosted_payment_available=hosted_payment_available,
            payment_retry_available=payment_retry_available,
        )
        payload = {
            **self._build_order_detail_structural_payload(order),
            **self._build_order_detail_narrative_base_payload(
                order=order,
                next_step_hint=next_step_hint,
                continuity_description=continuity_description,
                catalog_guidance=catalog_guidance,
                return_to_buy=return_to_buy,
            ),
            **self._build_order_detail_reorder_payload(order),
            **self._build_order_detail_payment_attempt_payload(payment_attempt_summary),
            **self._build_order_detail_recovery_guidance_payload(
                pending_recovery=pending_recovery,
                order_pending_recovery=order_pending_recovery,
            ),
            **self._build_order_detail_actions_payload(
                payment_progression_available=payment_progression_available,
                payment_retry_available=payment_retry_available,
                hosted_payment_available=hosted_payment_available,
                hosted_payment=hosted_payment,
                pending_recovery=pending_recovery,
            ),
        }
        payload, payment_source_label, payment_reference = self._apply_order_detail_payment_narrative_enrichment(
            payload,
            payment_status=payment_status,
            order=order,
        )
        payload = self._apply_order_detail_attempt_narrative_enrichment(
            payload,
            payment_attempt_summary=payment_attempt_summary,
        )
        if confirmation_mode:
            payload.update(
                self._build_order_detail_confirmation_payload(
                    order=order,
                    next_step_hint=next_step_hint,
                    payment_source_label=payment_source_label,
                    payment_reference=payment_reference,
                )
            )
        return payload

    def get_addresses_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        profile = self._profile(tenant_id=tenant_id)
        addresses = self.area_repository.get_addresses(profile)
        orders = self.list_orders(tenant_id=tenant_id)
        default_address_title = next(
            (
                str(address.get("title") or "")
                for address in addresses
                if "principal" in str(address.get("subtitle") or "").lower()
            ),
            "",
        )
        linkage_visibility = self.get_linkage_visibility(tenant_id=tenant_id)
        if not addresses and not self.using_persisted_addresses_source(tenant_id=tenant_id):
            linkage_visibility = {
                **linkage_visibility,
                "addresses_mode": "missing",
            }
        return {
            "page_title": "Meus endereços",
            "page_description": _addresses_continuity_description(
                address_count=len(addresses),
                total_orders=len(orders),
                default_address_title=default_address_title,
            ),
            "addresses": addresses,
            "operational_linkage_visibility": linkage_visibility,
        }

    def get_profile_page_data(self, *, tenant_id: int | None = None) -> dict[str, object]:
        profile = self._identity_profile(tenant_id=tenant_id)
        orders = self.list_orders(tenant_id=tenant_id)
        addresses = self.area_repository.get_addresses(profile)
        if not addresses and self._allow_fixture_fallback(tenant_id=tenant_id):
            addresses = self.fallback_area_repository.get_addresses(profile)
        profile_copy = _profile_continuity_copy(
            total_orders=len(orders),
            address_count=len(addresses),
            order_updates_opt_in=bool(profile["order_updates_opt_in"]),
            latest_recent_hint=str((orders[0] if orders else {}).get("recent_update_hint") or ""),
            profile_mode=str(profile.get("customer_linkage_mode") or "missing"),
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
            "operational_linkage_mode": profile.get("customer_linkage_mode", "missing"),
        }


account_customer_area_queries = AccountCustomerAreaQueryService(
    profile_repository=DjangoOrmAccountProfileRepository(),
    fallback_profile_repository=FallbackAccountProfileRepository(),
    area_repository=DjangoOrmCustomerAreaRepository(),
    fallback_area_repository=FallbackCustomerAreaRepository(),
)
