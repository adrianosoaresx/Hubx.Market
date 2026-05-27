from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NotificationIntent:
    intent_key: str
    source_event: str
    audience: str
    channel: str
    idempotency_key_template: str
    title: str
    description: str
    cta_label: str
    cta_target: str


_DEFAULT_IDEMPOTENCY_TEMPLATE = "{tenant_id}:{intent_key}:{entity_type}:{entity_id}:{channel}"


_INTENTS: tuple[NotificationIntent, ...] = (
    NotificationIntent(
        intent_key="customer.order.received",
        source_event="order.created",
        audience="customer",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Pedido recebido",
        description="Seu pedido foi criado e já pode ser acompanhado pela área do cliente.",
        cta_label="Acompanhar pedido",
        cta_target="customer_order_detail",
    ),
    NotificationIntent(
        intent_key="customer.payment.confirmed",
        source_event="payment.paid",
        audience="customer",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Pagamento confirmado",
        description="O pagamento foi confirmado e o pedido pode avançar para preparação.",
        cta_label="Ver pedido",
        cta_target="customer_order_detail",
    ),
    NotificationIntent(
        intent_key="customer.payment.failed",
        source_event="payment.failed",
        audience="customer",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Pagamento não concluído",
        description="A tentativa de pagamento não avançou, mas o pedido continua salvo para retomada segura.",
        cta_label="Retomar pagamento",
        cta_target="customer_order_detail",
    ),
    NotificationIntent(
        intent_key="customer.shipment.sent",
        source_event="shipment.sent",
        audience="customer",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Pedido a caminho",
        description="Seu pedido saiu para transporte e as próximas atualizações aparecerão na área do cliente.",
        cta_label="Acompanhar entrega",
        cta_target="customer_order_detail",
    ),
    NotificationIntent(
        intent_key="customer.shipment.delivered",
        source_event="shipment.delivered",
        audience="customer",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Entrega concluída",
        description="Seu pedido foi entregue e permanece salvo no histórico da conta.",
        cta_label="Ver pedido",
        cta_target="customer_order_detail",
    ),
    NotificationIntent(
        intent_key="customer.post_purchase.follow_up",
        source_event="retention.post_purchase_eligible",
        audience="customer",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Como foi sua experiência?",
        description="Obrigado pela compra. Se quiser, volte ao pedido para acompanhar histórico e próximos passos.",
        cta_label="Ver pedido",
        cta_target="customer_order_detail",
    ),
    NotificationIntent(
        intent_key="owner.order.created",
        source_event="order.created",
        audience="owner",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Nova venda recebida",
        description="Um novo pedido foi criado na loja e já pode ser revisado no admin.",
        cta_label="Abrir pedido",
        cta_target="admin_order_detail",
    ),
    NotificationIntent(
        intent_key="owner.payment.failed",
        source_event="payment.failed",
        audience="owner",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Pagamento com falha",
        description="Um pedido teve falha de pagamento e pode precisar de acompanhamento.",
        cta_label="Abrir pedido",
        cta_target="admin_order_detail",
    ),
    NotificationIntent(
        intent_key="owner.shipment.delivered",
        source_event="shipment.delivered",
        audience="owner",
        channel="email",
        idempotency_key_template=_DEFAULT_IDEMPOTENCY_TEMPLATE,
        title="Entrega concluída",
        description="Um pedido foi marcado como entregue e pode entrar em pós-venda.",
        cta_label="Abrir pedido",
        cta_target="admin_order_detail",
    ),
)


def list_notification_intents(*, audience: str | None = None, source_event: str | None = None) -> list[NotificationIntent]:
    normalized_audience = str(audience or "").strip()
    normalized_event = str(source_event or "").strip()
    intents = list(_INTENTS)
    if normalized_audience:
        intents = [intent for intent in intents if intent.audience == normalized_audience]
    if normalized_event:
        intents = [intent for intent in intents if intent.source_event == normalized_event]
    return intents


def get_notification_intent(intent_key: str) -> NotificationIntent | None:
    normalized_key = str(intent_key or "").strip()
    return next((intent for intent in _INTENTS if intent.intent_key == normalized_key), None)


def build_idempotency_key(
    *,
    intent: NotificationIntent,
    tenant_id: int | str,
    entity_type: str,
    entity_id: int | str,
) -> str:
    return intent.idempotency_key_template.format(
        tenant_id=str(tenant_id),
        intent_key=intent.intent_key,
        entity_type=str(entity_type).strip(),
        entity_id=str(entity_id).strip(),
        channel=intent.channel,
    )
