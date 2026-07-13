
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

# Eventos administrativos de catálogo

## product.created

Origem: catalog

Consumidores:
- audit

Descrição:
Produto foi criado por uma superfície administrativa tenant-scoped.

Readiness atual:

- emitido como `AuditLog` por `catalog.application.admin_product_commands`;
- payload registra produto, slug, status e tenant;
- preço e estoque iniciais são persistidos na `ProductVariant` padrão;
- não cria marca/categoria/tag normalizada.

---

## product.updated

Origem: catalog

Consumidores:
- audit

Descrição:
Produto e sua variante padrão foram atualizados por uma superfície administrativa tenant-scoped.

Readiness atual:

- emitido como `AuditLog` por `catalog.application.admin_product_commands`;
- preserva tenant-scope e registra slug/status/SKU;
- não recalcula pedidos nem altera snapshots de pedidos já criados.

---

## product.deactivated

Origem: catalog

Consumidores:
- audit

Descrição:
Produto foi desativado operacionalmente sem exclusão física.

Readiness atual:

- emitido como `AuditLog` por `catalog.application.admin_product_commands`;
- atualiza `status=inactive`, `is_active=False` e `is_featured=False`;
- não chama `delete()` e preserva histórico, variantes, imagens e referências operacionais.

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
- deve descartar execução para o tenant demo oficial configurado em `HUBX_MARKET_DEMO_TENANT_SUBDOMAIN`, porque a demo é somente leitura
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
- isso ainda não representa captura confirmada no gateway; apenas cria um contrato persistido para integração hospedada
- a partir dessa tentativa pendente, `payments` também já pode gerar um contrato idempotente de bootstrap para futura criação real de cobrança/intenção externa
- com o provider inicial `Asaas`, essa tentativa já pode materializar um checkout/invoice hospedado real quando `ASAAS_API_KEY` estiver configurada
- `Pagar.me` permanece como provider alternativo configurável

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

- para `Asaas` e `Pagar.me`, a confirmação segura continua vindo de webhook normalizado por `payments`
- a URL de retorno hospedada pode trazer apenas hint de status; ela não substitui `payment.paid`
- `payments` cria `PlatformFeeLedger(kind=order_take_rate)` de forma idempotente após a confirmação do pedido
- o ledger preserva snapshot do plano, percentual, base de cálculo e status de split/cobrança
- notifications agora cria `EmailLog` planejado customer-facing após `payment.paid` confirmado pela primeira vez
- replay/idempotência do webhook não deve gerar nova unidade de delivery para o mesmo recipient

---

## platform_fee.recorded

Origem: payments

Consumidores:
- audit
- financeiro platform

Descrição:
Taxa Hubx de um pedido pago foi registrada no ledger.

Readiness atual:

- implementado como efeito in-process idempotente do webhook `payment.paid`
- não publica fila distribuída nesta fase
- usa `PlatformFeeLedger(ledger_key=order:<id>:platform-fee)`
- Essencial e Pro usam percentual do plano ativo, normalmente 2%
- status inicial indica se o split foi solicitado ao provider ou se a coleta ficou pendente
- quando uma corrida confirma pedido acima de `monthly_paid_order_limit`, o ledger mantém o pedido pago e marca `metadata.commercial_overage=true` para tratativa comercial

---

## platform_fee.order_limit_overage_recorded

Origem: payments

Consumidores:
- audit
- financeiro platform

Descrição:
Webhook confirmou um pedido pago acima do limite mensal do plano por corrida operacional.

Readiness atual:

- implementado como `AuditLog` sobre `PlatformFeeLedger`
- não desfaz pedido pago, pagamento, estoque ou split
- usa `PlatformFeeLedger.metadata.commercial_overage=true`, `monthly_paid_order_limit`, `monthly_paid_order_count` e `overage_count`
- a tratativa é comercial/platform, fora do checkout do cliente final

---

## platform_fee.minimum_adjustment_created

Origem: payments

Consumidores:
- audit
- financeiro platform

Descrição:
Fechamento mensal criou ajuste complementar do Pro para atingir o mínimo contratado.

Readiness atual:

- implementado pelo comando `close_platform_fee_minimums`
- cria `PlatformFeeLedger(kind=pro_minimum_adjustment)` apenas quando o take rate do período fica abaixo do mínimo
- pode criar cobrança complementar Asaas quando `PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED=1` ou o comando roda com `--collect`
- a cobrança usa `externalReference=hubx-platform-fee:<ledger_key>` para conciliação por webhook
- quando o take rate supera o mínimo, não há evento nem cobrança adicional

---

## platform_fee.complementary_charge_paid

Origem: payments

Consumidores:
- audit
- financeiro platform

Descrição:
Cobrança complementar Asaas do mínimo Pro foi confirmada.

Readiness atual:

- implementado via webhook Asaas autenticado.
- identifica `PlatformFeeLedger` por `externalReference=hubx-platform-fee:<ledger_key>`.
- marca o ledger como `paid`.
- não altera pedidos, catálogo ou assinatura do tenant.

---

## tenant_subscription.marked_past_due

Origem: payments

Consumidores:
- subscriptions
- audit
- operadores/plataforma

Descrição:
Assinatura Pro entrou em atraso por complemento mensal não pago após tolerância configurada.

Readiness atual:

- implementado pelo comando `enforce_platform_fee_delinquency`.
- usa ledgers `PlatformFeeLedger(kind=pro_minimum_adjustment)` pendentes.
- janela vem de `SUBSCRIPTIONS_PRO_DELINQUENCY_GRACE_DAYS`.
- altera apenas `TenantSubscription.status`; não altera pedidos ou catálogo diretamente.

---

## tenant_subscription.suspended_for_delinquency

Origem: payments

Consumidores:
- subscriptions
- audit
- operadores/plataforma

Descrição:
Assinatura Pro foi suspensa por complemento mensal não pago após prazo de suspensão configurado.

Readiness atual:

- implementado pelo comando `enforce_platform_fee_delinquency`.
- janela vem de `SUBSCRIPTIONS_PRO_DELINQUENCY_SUSPEND_DAYS`.
- a reativação para `active` ocorre quando não há complemento Pro pendente.

---

## platform_fee.adjustment_required

Origem: payments

Consumidores:
- audit
- financeiro platform

Descrição:
Um ledger de taxa Hubx precisa de ajuste por refund, chargeback ou falha posterior.

Readiness atual:

- implementado como mudança de status/metadados no `PlatformFeeLedger`
- não reabre pedido pago nem cria cobrança duplicada
- tratativa financeira posterior deve reconciliar o lançamento original

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

- para `Asaas` e `Pagar.me`, `payment.failed` também entra por webhook autenticado/assinado
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
- Battery F adiciona `AuditLog` para `refund.approved` e `refund.execution_recorded`, mas isso não equivale a evento de domínio `payment.refunded`.
- audit de execução de refund não inclui `payload_snapshot` do provider nem `external_reference`; a evidência financeira completa continua no módulo `payments`.

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

## tenant.storefront_branding_updated

Origem: tenants

Consumidores:
- audit

Branding institucional do storefront foi alterado por uma superfície administrativa tenant-scoped.

Observações:
- emitido como `AuditLog` por `tenants.application.storefront_branding_commands`;
- payload registra tenant, flag de exibição e presença de logo, cor de conversão validada, título, descrição, imagem e CTA;
- não deve carregar URL secreta, arquivo binário, dados de catálogo, pedidos, clientes ou pagamentos;
- não deve carregar CSS arbitrário; a cor de conversão precisa chegar validada pelo command service;
- exige tenant resolvido e permissão administrativa `storefront.branding.manage`.

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

## subscription.acquisition_requested

Origem: subscriptions

Consumidores:
- audit
- platform-admin

Descrição:
Intenção pública de aquisição de plano SaaS foi recebida por `/plans/`.

Payload mínimo:

{
  "lead_id": "...",
  "plan_code": "...",
  "desired_subdomain": "...",
  "coupon_code": "opcional",
  "effective_monthly_price": "opcional"
}

Readiness atual:

- evento é registrado como `AuditLog` platform-scope.
- não cria tenant, owner, assinatura, invoice, pagamento ou catálogo.
- quando houver cupom SaaS válido, metadata pode incluir código, desconto total e preço efetivo snapshotado.
- metadata não deve carregar mensagem livre nem PII desnecessária.

---

## tenant.self_service_created

Origem: tenants

Consumidores:
- audit
- platform-admin

Descrição:
Tenant foi criado pelo signup público controlado de `/plans/signup/`.

Readiness atual:

- evento é registrado como `AuditLog` tenant-scoped.
- tenant nasce ativo em `maintenance_mode`.
- metadata pode incluir `plan_code`, limites comerciais e snapshots promocionais; não deve incluir token ou dado de cartão.
- metadata pode incluir `coupon_code` e `effective_monthly_price` quando o signup aplicar cupom SaaS válido.
- quando configurado, o signup exige token de acesso antes da criação.
- storefront/checkout do tenant em manutenção retornam 503 até publicação operacional.
- não cria customer, catálogo, pedido, pagamento, invoice ou domínio customizado.
- não registra dados de cartão ou token de método de cobrança.

---

## tenant.self_service_signup_completed

Origem: tenants

Consumidores:
- audit
- accounts
- subscriptions

Descrição:
Signup público concluiu a orquestração mínima: tenant, owner inicial, assinatura self-service elegível e onboarding concluído.

Readiness atual:

- exige `HUBX_PUBLIC_SIGNUP_ENABLED=1`.
- assinatura SaaS nasce conforme o plano self-service; planos com `requires_billing_method=True` não entram neste fluxo.
- metadata pode incluir `plan_code`, limites comerciais e snapshots promocionais; não deve incluir token ou dado de cartão.
- metadata pode incluir snapshots promocionais sem alterar `SubscriptionPlan.monthly_price`.
- owner inicial é `OwnerUser`, não `Customer`.
- não registra dados de cartão ou token de método de cobrança.

---

## subscription.coupon_created

Origem: subscriptions

Consumidores:
- audit
- platform-admin

Descrição:
Cupom comercial de plano SaaS foi criado em `/ops/platform/subscription-coupons/`.

Readiness atual:

- evento é registrado como `AuditLog` platform-scope.
- exige `subscriptions.manage`.
- metadata pode incluir `code`, `status`, `discount_type`, `discount_value` e `plan_code`.
- não cria invoice, cobrança recorrente, checkout externo ou alteração de preço do plano.

---

## subscription.coupon_status_changed

Origem: subscriptions

Consumidores:
- audit
- platform-admin

Descrição:
Status de cupom SaaS foi ativado ou inativado por operação platform.

Readiness atual:

- evento é registrado como `AuditLog` platform-scope.
- exige `subscriptions.manage`.
- metadata inclui código e transição de status.

---

## subscription.coupon_applied

Origem: subscriptions

Consumidores:
- audit
- platform-admin

Descrição:
Cupom SaaS válido foi aplicado a um lead público, signup self-service ou assinatura criada por onboarding.

Readiness atual:

- evento é registrado como `AuditLog` platform-scope.
- metadata inclui `coupon_code`, `plan_code`, `discount_type`, `discount_total`, `effective_monthly_price` e `source`.
- aplicação não recalcula cobrança externa e não altera `SubscriptionPlan.monthly_price`.
- cupons tenant-scoped de carrinho/pedido continuam no módulo `coupons`.

---

## subscription.acquisition_converted

Origem: subscriptions

Consumidores:
- audit
- tenants

Descrição:
Lead público de aquisição SaaS foi convertido por platform admin em uma jornada de onboarding.

Readiness atual:

- conversão cria/preenche `TenantOnboarding`.
- não conclui onboarding e não provisiona tenant/owner/assinatura.

---

## subscription.acquisition_discarded

Origem: subscriptions

Consumidores:
- audit

Descrição:
Lead público de aquisição SaaS foi descartado por platform admin.

Readiness atual:

- descarte altera apenas `SubscriptionAcquisitionLead.status`.

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

## notification.production_smoke

Origem: notifications

Consumidores:
- notifications

Descrição:
Smoke transacional controlado para validar provider real de e-mail por tenant.

Readiness atual:

- Battery G cria/reusa `EmailLog` system smoke tenant-scoped.
- a entrega só é tentada quando provider readiness permite envio real.
- evidência operacional usa recipient mascarado e status do `EmailLog`.
- o evento não representa comunicação de customer nem campanha.

## retention.post_purchase_eligible

Origem: notifications/newsletter

Consumidores:
- notifications

Descrição:
Sinal operacional interno para planejar follow-up pós-compra quando o comprador possui opt-in de newsletter no mesmo tenant.

Readiness atual:

- Battery H usa esse source event apenas para `EmailLog` planejado.
- opt-out em `NewsletterSubscriber` bloqueia criação do log.
- não há campanha recorrente, scoring, worker novo ou automação complexa.

## catalog.product_card_priority_experiment

Origem: catalog

Consumidores:
- catalog

Descrição:
Experimento interno de ranking de cards usando sinais recentes de PDP/CTA já persistidos em `StorefrontDiscoveryEventLog`.

Readiness atual:

- Battery I executa `product_card_priority_v1`.
- o experimento não cria novo evento persistido; usa os eventos existentes.
- sinais positivos de PDP/CTA aumentam prioridade de card.
- sinais de indisponibilidade reduzem prioridade e não alteram estoque/checkout.

## system.production_go_nogo

Origem: tenants

Consumidores:
- operadores/plataforma

Descrição:
Decisão declarativa de produção real após matriz, runbooks, smoke, observabilidade e rollback.

Readiness atual:

- Battery J implementa Go/No-Go por command.
- não há evento persistido nem publish assíncrono nesta fase.
- `GO` não executa rollout; apenas autoriza próxima trilha controlada.
- `NO-GO` deve abrir bateria corretiva.
- ele ainda é in-process e serve como contrato de boundary, não como fila distribuída
- Celery futuro deve substituir/consumir essa boundary sem acoplar módulos diretamente

## assistant.question_answered

Origem: assistant

Consumidores:
- audit

Descrição:
Pergunta operacional de owner/admin foi respondida pelo assistente em `/ops/assistant/`.

Readiness atual:

- registrado como `AuditLog` tenant-scoped;
- metadata inclui apenas resultado, fonte (`llm` ou `fallback`), quantidade de fontes e motivo técnico sanitizado;
- pergunta e resposta não são copiadas para metadata;
- não representa ação operacional nem consulta a dados reais da loja.

---

# Objetivo

Criar uma arquitetura orientada a eventos que permita:

- baixo acoplamento
- alta escalabilidade
- facilidade de integração
- automações futuras
