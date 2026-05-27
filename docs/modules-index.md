
# Modules Index — Hubx Market

Este documento funciona como **índice oficial de todos os módulos do Hubx Market**.

Ele ajuda desenvolvedores e agentes de IA a:

- localizar rapidamente responsabilidades
- entender dependências entre módulos
- identificar entidades principais
- descobrir eventos e APIs relacionadas

---

# Estrutura geral

O sistema é organizado em três grandes domínios:

Platform
Commerce
Engagement

---

# Platform Domain

Infraestrutura do SaaS.

## tenants

Responsabilidade:
Gerenciar lojas (tenants) e resolução por subdomínio.

Entidades principais:
Tenant

Eventos:
tenant.created

Dependências:
accounts  
subscriptions

Readiness:
- tenant resolution por subdomínio;
- custom domain ainda contract-only;
- Battery J adiciona closure sistêmica de produção e Go/No-Go por comando `system_production_closure`;
- closure não altera runtime, settings, providers ou tenants.

---

## accounts

Responsabilidade:
Gerenciar autenticação e usuários administrativos da loja.

Entidades principais:
AccountProfile
OwnerUser
OwnerMfaFactor
OwnerMfaRecoveryCode

Dependências:
tenants
accounts
audit

Readiness:
- modelo `ApiKey` tenant-scoped
- segredo persistido apenas como hash
- command service de criação/revogação
- eventos `api_key.created` e `api_key.revoked`
- runtime authentication e API pública ainda pendentes

---

## subscriptions

Responsabilidade:
Gerenciar planos e assinaturas SaaS da plataforma.

Entidades principais:
SubscriptionPlan
TenantSubscription

Eventos:
subscription.activated  
subscription.canceled

Dependências:
tenants
accounts
audit

Readiness:
- modelo `SubscriptionPlan`
- modelo `TenantSubscription`
- setup auditável por `subscription_commands`
- admin read-only em `/ops/subscriptions/`
- provider de cobrança real e enforcement de plano fora da fundação

Readiness:
- modelo `ApiKey` tenant-scoped
- segredo persistido apenas como hash
- criação/revogação auditáveis
- contrato runtime revisado para `Authorization: Bearer`
- service runtime mínimo `api_key_runtime_authentication`
- adapter DRF revisado como opt-in por view
- adapter DRF mínimo `ApiKeyAuthentication`
- permission mínima `HasApiKeyScope`
- API key segue proibida em `DEFAULT_AUTHENTICATION_CLASSES`
- primeiro piloto público criado: `GET /api/v1/catalog/products/` com `read:catalog`
- endpoint público protegido por flag `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED`
- rate limit revisado para política `tenant+api_key+endpoint`
- rate limit real opt-in via `ApiKeyRateLimitThrottle`
- observabilidade pública revisada para métricas Prometheus e dashboard mínimos
- métricas Prometheus públicas em `/api-keys/metrics/public-endpoints/`
- contrato de dashboard Grafana público revisado com painéis mínimos e baixa cardinalidade
- dashboard Grafana público versionado em `infra/observability/grafana/api-key-public-endpoints-dashboard.json`
- contrato de alert rules Prometheus revisado para auth failures, rate limit e endpoint disabled
- alert rules Prometheus públicas versionadas em `infra/observability/prometheus/api-keys-alert-rules.yml`
- closure de observabilidade pública revisa métricas, endpoint, dashboard, alert rules e riscos residuais
- rollout produtivo de observabilidade pública possui review executável com smoke, evidência e rollback
- evidência de ativação produtiva pública possui command sanitizado sem token/API key em claro
- monitoramento pós-ativação pública possui review para estabilidade, ruído e decisão de expansão
- expansão pública recomenda contrato de detalhe de produto read-only `GET /api/v1/catalog/products/<slug>/`
- contrato do endpoint público de detalhe de produto define slug, tenant-scope, `read:catalog`, rate limit e rollout flag
- endpoint público de detalhe de produto executado em `GET /api/v1/catalog/products/<slug>/`
- observabilidade do detalhe público reaproveita dashboard/alertas por label `endpoint`, sem artefatos novos
- expansão inicial de endpoints públicos fechada com listagem + detalhe e sem novo endpoint selecionado
- governança de API keys fechada para ciclo atual com modelo, runtime auth, DRF adapter, endpoints públicos e observabilidade
- re-seleção ROI sistêmica pós-governança recomenda documentação/onboarding de parceiros antes de quotas, novos endpoints ou UX admin
- onboarding de parceiros para API pública de catálogo possui guia versionado, checklist, contrato de erro e exemplos com placeholder seguro
- execution review de documentação de parceiros valida canal de entrega, suporte, smoke evidence template e change control sem publicar credencial
- publication evidence de documentação de parceiros registra entrega sanitizada sem credencial, smoke real ou runtime activation
- closure de onboarding de parceiros fecha docs/pacote/evidência e devolve a decisão para re-seleção sistêmica de ROI
- re-seleção pós-onboarding recomenda smoke controlado de ativação de parceiro antes de quotas comerciais ou novos endpoints
- contrato de smoke de ativação de parceiro limita execução futura a list/detail, observabilidade, rollback e evidência sanitizada
- contrato de quotas comerciais define tenant/key/endpoint/window, limite diário, 429, visibilidade admin e mantém billing/enforcement runtime fora da wave

---

## audit

Responsabilidade:
Registrar eventos auditáveis administrativos e operacionais.

Entidades principais:
AuditLog

Dependências:
todos os módulos (apenas leitura de eventos)

Readiness:
- modelo `AuditLog`
- writer `audit_log_commands.record_event(...)`
- leitura admin em `/ops/audit/`
- platform-scope só com opt-in explícito
- instrumentação automática/global continua fora de escopo
- Battery F adiciona ações críticas explícitas: refund aprovado, execução de refund registrada e visibilidade de produto atualizada
- API keys mantêm auditoria para criação, revogação, quota atualizada e quota excedida
- metadata sensível de API key/provider/pagamento permanece redigida

---

## api-keys

Responsabilidade:
Gerenciar chaves de integração para API pública.

Entidades principais:
ApiKey
ApiKeyQuota
ApiKeyQuotaUsage

Dependências:
tenants
audit

Readiness:
- modelo `ApiKey` tenant-scoped com segredo persistido apenas como hash
- runtime authentication opt-in por view via `ApiKeyAuthentication`
- endpoints públicos de catálogo list/detail protegidos por `read:catalog`
- rate limit técnico via `ApiKeyRateLimitThrottle`
- observabilidade pública em `/api-keys/metrics/public-endpoints/`
- quotas comerciais mínimas por tenant/API key/endpoint/janela
- enforcement de quota após rate limit técnico, retornando `429`
- audit `api_key.quota_exceeded` e métrica `hubx_api_key_quota_exceeded_total`
- admin read-only em `/ops/api-keys/quotas/`
- billing e enforcement por plano continuam fora

---

# Commerce Domain

Motor principal de e-commerce.

## catalog

Responsabilidade:
Gerenciar produtos e estrutura de catálogo.

Entidades principais:
Product  
ProductVariant  
Category  
Brand  
Tag  
ProductImage
StorefrontDiscoveryEventLog

Eventos:
product.created
product.updated
catalog.discovery_viewed
catalog.search_performed
catalog.facets_applied
catalog.sort_changed
catalog.product_detail_viewed
catalog.pdp_cta_intent

Dependências:
tenants

Readiness:
- produtos/variantes/imagens tenant-scoped;
- storefront e admin reais;
- analytics brutos de discovery/PDP/CTA;
- Battery I adiciona baseline de conversão, funil PDP/CTA, drop-off de busca/facet e experimento `product_card_priority_v1`;
- o experimento altera ranking de cards com base em sinais recentes, sem redesenhar storefront inteiro.

---

## customers

Responsabilidade:
Gerenciar compradores e endereços.

Entidades principais:
Customer  
CustomerAddress

Dependências:
tenants

---

## cart

Responsabilidade:
Gerenciar carrinho de compras.

Entidades principais:
Cart  
CartItem

Eventos:
cart.updated

Dependências:
catalog  
customers

---

## checkout

Responsabilidade:
Orquestrar fluxo de finalização da compra.

Entidades principais:
CheckoutSession
CheckoutSessionItem
CheckoutRecoveryEvent

Dependências:
cart  
shipping  
coupons  
orders  
payments

---

## orders

Responsabilidade:
Gerenciar pedidos e lifecycle.

Entidades principais:
Order  
OrderItem

Eventos:
order.created  
order.status_changed

Dependências:
customers  
catalog  
payments  
shipping

---

## payments

Responsabilidade:
Integração com gateway, tentativas de pagamento, conciliação financeira e ledger inicial de refund.

Entidades principais:
PaymentAttempt
PaymentRefund

Eventos:
payment.created  
payment.paid  
payment.failed  
payment.refunded

Dependências:
orders

Readiness:
- provider production gate/evidence com comando `payments_production_readiness`
- webhook production smoke revisável
- refund production gate/evidence limitado e manual
- financial reconciliation production review
- closure da Battery C sem rollout amplo, self-service de refund ou correção automática

---

## shipping

Responsabilidade:
Gerenciar frete e remessas.

Entidades principais:
Shipment

Eventos:
shipment.created  
shipment.sent  
shipment.delivered

Dependências:
orders  
customers

Readiness:
- quote mínimo tenant-scoped via `shipping_quote_queries`
- aplicação de quote no checkout via `checkout_shipping_quote_commands`
- falha honesta para CEP/tenant inválido
- closure da Battery D sem transportadora real/token externo

---

## coupons

Responsabilidade:
Gerenciar cupons e descontos.

Entidades principais:
Coupon
CouponRedemption

Dependências:
checkout  
orders

Contrato:
`record_order_coupon_redemption(tenant_id, order_number)` registra ledger idempotente a partir do snapshot promocional de `Order`.

---

# Engagement Domain

Recursos de interação e retenção.

## reviews

Responsabilidade:
Avaliações de produtos.

Entidades principais:
ProductReview

Eventos:
review.created

Dependências:
catalog  
customers

Readiness:
- modelo tenant-scoped inicial
- agregados approved-only para PDP por application query
- moderação admin/ops ainda pendente

---

## newsletter

Responsabilidade:
Gerenciar opt-in de newsletter tenant-scoped.

Entidades principais:
NewsletterSubscriber

Eventos:
newsletter.subscribed

Dependências:
tenants

Readiness:
- modelo tenant-scoped
- opt-in público em `/newsletter/`
- admin read-only em `/ops/newsletter/`
- campanhas e automação fora do primeiro corte

---

## notifications

Responsabilidade:
Envio de notificações e emails.

Entidades principais:
EmailLog

Consumidores de eventos:
order.created  
payment.paid  
shipment.sent

Dependências:
orders  
payments  
shipping

Readiness:
- `EmailLog` tenant-scoped
- processamento assíncrono/dry-run-safe de logs planejados
- readiness de provider
- métricas Prometheus por tenant/status
- Battery G adiciona smoke transacional real, evidência sanitizada, classificação de falhas/bounces e closure de produção
- Battery H adiciona lifecycle mínimo pós-compra consentido por newsletter opt-in
- campanhas recorrentes, scoring e segmentação avançada continuam fora

---

## pages

Responsabilidade:
Páginas institucionais tenant-owned da loja.

Entidades principais:
Page

Dependências:
tenants

Readiness:
- modelo tenant-scoped
- admin lite para listagem/criação/edição
- storefront published-only em `/pages/<slug>/`
- SEO básico sem page builder avançado

---

# Como usar este documento

Antes de implementar qualquer funcionalidade:

1. Identifique o módulo responsável.
2. Verifique entidades e eventos do módulo.
3. Consulte docs/module-boundaries.md.
4. Consulte docs/events-map.md.
5. Para operação/produção, consulte docs/operational-runbooks.md.
6. Para priorização de evolução, consulte docs/system-module-status-audit.md.
7. Para execução por baterias de ondas, consulte docs/system-execution-wave-batteries.md.

---

# Objetivo

Facilitar navegação arquitetural do Hubx Market e garantir que novos desenvolvimentos respeitem a organização modular do sistema.
