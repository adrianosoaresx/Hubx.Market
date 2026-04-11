
# Events Map — Hubx Market

Este documento define os **eventos internos do sistema** Hubx Market.

O objetivo é padronizar comunicação assíncrona entre módulos e evitar acoplamento direto entre domínios.

Eventos são usados principalmente para:

- processamento assíncrono (Celery)
- integrações externas
- envio de notificações
- auditoria
- automações internas

---

# Estrutura de eventos

Formato recomendado:

domain.event

Exemplo:

order.created
payment.paid
shipment.sent

Cada evento possui:

- nome do evento
- módulo de origem
- módulos consumidores
- payload padrão

---

# Eventos do domínio Commerce

## cart.updated

Origem: cart

Consumidores:
- checkout

Descrição:
Carrinho foi alterado (item adicionado, removido ou quantidade alterada).

Payload exemplo:

{
  "tenant_id": "...",
  "cart_id": "...",
  "customer_id": "..."
}

---

## checkout.started

Origem: checkout

Consumidores:
- analytics (futuro)
- audit

Descrição:
Cliente iniciou processo de checkout.

---

## order.created

Origem: orders

Consumidores:
- payments
- notifications
- audit

Descrição:
Pedido foi criado após confirmação do checkout.

Payload exemplo:

{
  "tenant_id": "...",
  "order_id": "...",
  "customer_id": "...",
  "total_amount": "..."
}

---

## order.status_changed

Origem: orders

Consumidores:
- notifications
- audit
- analytics

Descrição:
Status do pedido foi alterado.

---

# Eventos de pagamento

## payment.created

Origem: payments

Consumidores:
- orders
- audit

Descrição:
Pagamento iniciado.

---

## payment.paid

Origem: payments

Consumidores:
- orders
- shipping
- notifications
- audit

Descrição:
Pagamento confirmado pelo gateway.

Efeitos comuns:

- atualizar pedido para "paid"
- reduzir estoque
- iniciar preparação do pedido

---

## payment.failed

Origem: payments

Consumidores:
- orders
- notifications
- audit

Descrição:
Pagamento falhou.

---

## payment.refunded

Origem: payments

Consumidores:
- orders
- audit

Descrição:
Pagamento foi estornado.

---

# Eventos de logística

## shipment.created

Origem: shipping

Consumidores:
- orders
- notifications
- audit

Descrição:
Remessa criada para o pedido.

---

## shipment.sent

Origem: shipping

Consumidores:
- notifications
- audit

Descrição:
Pedido foi enviado.

---

## shipment.delivered

Origem: shipping

Consumidores:
- orders
- notifications
- reviews
- audit

Descrição:
Pedido entregue ao cliente.

---

# Eventos de engajamento

## review.created

Origem: reviews

Consumidores:
- catalog
- audit

Descrição:
Cliente criou avaliação de produto.

---

## newsletter.subscribed

Origem: newsletter

Consumidores:
- notifications
- marketing

Descrição:
Cliente se inscreveu na newsletter.

---

# Eventos da plataforma

## tenant.created

Origem: tenants

Consumidores:
- accounts
- subscriptions
- notifications
- audit

Descrição:
Nova loja criada na plataforma.

---

## subscription.activated

Origem: subscriptions

Consumidores:
- tenants
- notifications
- audit

Descrição:
Plano da loja foi ativado.

---

## subscription.canceled

Origem: subscriptions

Consumidores:
- tenants
- notifications
- audit

Descrição:
Assinatura da loja foi cancelada.

---

# Boas práticas

Eventos devem ser:

- idempotentes
- pequenos
- claros
- versionáveis

Evitar payloads grandes.

Eventos não devem conter lógica de negócio.

---

# Uso com Celery

Eventos podem disparar tarefas assíncronas:

- envio de e-mail
- atualização de estoque
- integrações externas
- analytics

---

# Objetivo

Criar uma arquitetura orientada a eventos que permita:

- baixo acoplamento
- alta escalabilidade
- facilidade de integração
- automações futuras
