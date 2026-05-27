
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

Readiness atual:

- o pedido ainda é materializado pela orquestração de checkout
- existe publisher interno em `orders.application.order_event_publisher`
- checkout publica `order.created` por essa boundary após materializar novo pedido
- notifications consome o evento por subscriber, sem checkout conhecer detalhes de notificação
- cupom aplicado não entra no payload do evento nesta fase; quando necessário, notifications deve usar snapshot tenant-scoped em `Order`
- ledger futuro de cupom deve ser registrado antes de `order.created` ou por command explícito idempotente, sem expandir o payload do evento nesta etapa
- reversão de cupom por cancelamento administrativo deve ser command explícito de `coupons`, não payload adicional de evento nesta fase

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

# Eventos de descoberta storefront

## catalog.discovery_viewed

Origem: catalog

Consumidores:
- analytics (futuro)
- audit (opcional)

Descrição:
Cliente visualizou a listagem pública de catálogo com o conjunto atual de busca, facets, sort e paginação.

Payload mínimo futuro:

{
  "tenant_id": "...",
  "session_key": "...",
  "path": "...",
  "query": "...",
  "category": "...",
  "availability": "...",
  "offer": "...",
  "price_min": "...",
  "price_max": "...",
  "quick_filter": "...",
  "sort": "...",
  "result_count": 0,
  "page": 1
}

Readiness atual:

- evento agora possui log persistente mínimo em `StorefrontDiscoveryEventLog`
- publisher persistente salva apenas payload allowlisted e `session_key_hash`
- deve descartar execução sem tenant resolvido
- não deve armazenar PII
- não deve bloquear renderização do storefront

---

## catalog.search_performed

Origem: catalog

Consumidores:
- analytics (futuro)

Descrição:
Cliente executou busca textual pública no catálogo.

Readiness atual:

- deve ser derivado de `q=` normalizado
- deve registrar `result_count`
- pode ser persistido como evento bruto tenant-scoped
- não deve registrar dados pessoais nem querystring bruta com parâmetros sensíveis

---

## catalog.facets_applied

Origem: catalog

Consumidores:
- analytics (futuro)

Descrição:
Cliente aplicou uma ou mais facets públicas de catálogo.

Readiness atual:

- cobre `category`, `availability`, `offer`, `price_min`, `price_max` e `quick_filter`
- deve preservar tenant-scope
- pode ser persistido como evento bruto tenant-scoped
- não deve criar contagens cross-tenant

---

## catalog.sort_changed

Origem: catalog

Consumidores:
- analytics (futuro)

Descrição:
Cliente escolheu ordenação pública diferente do default recomendado.

Readiness atual:

- cobre `sort=price_asc`, `sort=price_desc` e `sort=name_asc`
- `recommended` é default e não precisa ser tratado como mudança
- pode ser persistido como evento bruto tenant-scoped

---

## catalog.product_card_clicked

Origem: catalog

Consumidores:
- analytics (futuro)

Descrição:
Cliente clicou em um card de produto a partir da listagem pública.

Readiness atual:

- requer instrumentação futura de clique ou rota intermediária
- deve carregar `product_id`/`product_slug` e contexto de descoberta
- não deve depender de provider externo

---

## catalog.product_detail_viewed

Origem: catalog

Consumidores:
- analytics (futuro)

Descrição:
Cliente visualizou o PDP público de um produto.

Readiness atual:

- pode ser emitido server-side após resolver tenant e produto
- deve carregar `tenant_id`, `product_id`/`product_slug` e contexto de entrada quando disponível
- pode ser persistido como evento bruto tenant-scoped sem PII

---

## catalog.pdp_cta_intent

Origem: catalog

Consumidores:
- analytics

Descrição:
Cliente submeteu uma intenção de CTA no PDP, como adicionar ao carrinho, comprar agora ou tentar uma combinação indisponível.

Payload mínimo:

{
  "tenant_id": "...",
  "session_key": "...",
  "path": "...",
  "product_id": "...",
  "product_slug": "...",
  "cta_intent": "add_to_cart|buy_now",
  "cta_result": "...",
  "quantity": 1,
  "variant_sku": "..."
}

Readiness atual:

- emitido server-side no POST do PDP
- cobre `add_to_cart`, `buy_now` e indisponibilidade antes da mutação
- pode ser persistido como evento bruto tenant-scoped
- não depende de JavaScript
- não armazena PII
- não deve alterar ranking ou fluxo de checkout

---

# Eventos de pagamento

## payment.created

Origem: payments

Consumidores:
- orders
- audit

Descrição:
Pagamento iniciado.

Readiness atual:

- a criação inicial de `PaymentAttempt` agora pode acontecer quando o checkout materializa o pedido e abre a trilha pendente de pagamento
- isso ainda não representa captura real no gateway; apenas cria um contrato persistido para futura integração
- a partir dessa tentativa pendente, `payments` também já pode gerar um contrato idempotente de bootstrap para futura criação real de cobrança/intenção externa
- com o provider inicial `Pagar.me`, essa tentativa já pode materializar um `payment link` hospedado real quando a chave secreta estiver configurada

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
- registrar referência/origem do evento de pagamento
- reduzir estoque
- iniciar preparação do pedido

Readiness atual:

- para `Pagar.me`, a confirmação segura continua vindo de webhook
- a URL de retorno hospedada pode trazer apenas hint de status; ela não substitui `payment.paid`
- notifications agora cria `EmailLog` planejado customer-facing após `payment.paid` confirmado pela primeira vez
- replay/idempotência do webhook não deve gerar nova unidade de delivery para o mesmo recipient

---

## payment.failed

Origem: payments

Consumidores:
- orders
- notifications
- audit

Descrição:
Pagamento falhou.

Efeitos comuns:

- manter pedido em estado pendente
- registrar origem/referência da falha
- deixar o pedido pronto para nova tentativa segura

Readiness atual:

- para `Pagar.me`, `payment.failed` também entra por webhook assinado
- a customer area pode usar esse estado para abrir um retry leve de pagamento sem gerar novo pedido
- notifications agora possui piloto idempotente para criar `EmailLog` planejado customer-facing após `payment.failed`
- esse piloto ainda não envia e-mail nem aciona worker/provider
- junto com `payment.paid`, forma o primeiro recorte real de integração notifications por eventos de pagamento

---

## payment.refunded

Origem: payments

Consumidores:
- orders
- audit

Descrição:
Pagamento foi estornado.

Readiness atual:

- `PaymentRefund` já registra intenção/bloqueio de refund por tenant.
- evento ainda não deve ser emitido para `requested`, `blocked` ou `processing`.
- resposta `accepted` do provider também não deve emitir o evento.
- o evento só deve representar refund confirmado pelo provider, com ledger em `succeeded`.
- a primeira execução do command de refund ainda pode adiar emissão do evento mesmo ao gravar `succeeded`, até que os efeitos cross-module sejam definidos.
- efeitos em pedido, estoque, cupom e notificação devem ser modelados após essa confirmação.

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

Readiness atual:

- existe publisher mínimo em `shipping.application.shipping_event_publisher`
- existe `Shipment` persistido em `shipping.models`
- `shipment_commands.mark_shipment_sent` aciona o evento a partir da transição real para `sent`
- notifications registra log customer-facing quando há customer elegível no tenant

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

Readiness atual:

- existe publisher mínimo em `shipping.application.shipping_event_publisher`
- existe `Shipment` persistido em `shipping.models`
- `shipment_commands.mark_shipment_delivered` aciona o evento a partir da transição real de `sent` para `delivered`
- notifications registra logs customer-facing e owner-facing quando há destinatários elegíveis no tenant

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

## api_key.created

Origem: api_keys

Consumidores:
- audit

Descrição:
Chave de API foi criada para um tenant. O payload não deve conter segredo claro nem hash.

---

## api_key.revoked

Origem: api_keys

Consumidores:
- audit

Descrição:
Chave de API foi revogada para um tenant sem deletar histórico.

---

## api_key.auth_failed

Origem: api_keys

Consumidores:
- audit
- observability

Descrição:
Tentativa relevante de autenticação por API key falhou. O payload deve conter apenas tenant, prefixo quando disponível, motivo classificado e contexto operacional seguro; nunca segredo claro, hash ou header completo.

---

## api_key.rate_limited

Origem: api_keys

Consumidores:
- audit
- observability

Descrição:
Chave de API excedeu limite de requisições em endpoint público. O payload deve conter tenant, key_id/prefixo, endpoint, limite, janela e contador seguro; nunca segredo claro, hash ou header completo.

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

Readiness atual:

- existe um publisher mínimo em `notifications.application.notification_event_bus`
- ele ainda é in-process e serve como contrato de boundary, não como fila distribuída
- Celery futuro deve substituir/consumir essa boundary sem acoplar módulos diretamente

---

# Objetivo

Criar uma arquitetura orientada a eventos que permita:

- baixo acoplamento
- alta escalabilidade
- facilidade de integração
- automações futuras
