
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
- custom domain cadastrado em `Tenant` e resolvido por middleware apenas atrás de flag;
- Battery J adiciona closure sistêmica de produção e Go/No-Go por comando `system_production_closure`;
- closure não altera runtime, settings, providers ou tenants.
- Platform Store Management define contrato inicial para `/ops/platform/tenants/`, ainda sem surface HTTP implementada.
- Platform Store Management read-only implementa `/ops/platform/tenants/` com inventário operacional e permissão `platform.tenants.view`.
- Tenant Create Contract fixa `/ops/platform/tenants/new/` como write platform-only mínimo, sem owner/bootstrap/billing automático.
- Tenant Create Command implementa criação auditável via `platform_tenant_admin_commands`, exigindo `platform.tenants.manage`.
- Tenant Create Admin Surface conecta `/ops/platform/tenants/new/` ao command service e redireciona sucesso para o detalhe read-only.
- Tenant State Management Contract fixa ações `activate`, `deactivate`, `maintenance-on` e `maintenance-off`, ainda sem command execution.
- Tenant State Command implementa essas ações com audit platform-scope obrigatório e sem side effects em commerce.
- Tenant State Admin Surface expõe essas ações no detalhe do tenant via POST fino e redirect para o detalhe.
- Custom Domain Update Contract fixa edição contract-only de `custom_domain`, sem resolver HTTP/DNS/TLS.
- Custom Domain Command implementa atualização/limpeza auditável de `custom_domain`, com normalização e unicidade entre tenants.
- Custom Domain Admin Surface expõe o POST no detalhe platform-only do tenant sem ativar resolver HTTP.
- Tenant Ops Closure fecha o recorte inicial como operação interna controlada, mantendo owner bootstrap e custom-domain runtime como trilhas futuras.
- Owner Bootstrap Review define bootstrap invitation-only de `OwnerUser`, orquestrado por `tenants` e persistido por `accounts`.
- Custom Domain Runtime Resolver Review define ativação futura de `custom_domain` por match exato no middleware, sem DNS/TLS automáticos.
- Owner Bootstrap Command implementa orquestração platform-only para primeiro owner, delegando persistência a `accounts`.
- Custom Domain Runtime Resolver implementa resolução por `custom_domain` atrás de flag, sem fallback global.
- Owner Bootstrap Admin Surface Review define a action HTTP futura no detalhe do tenant sem campo de senha.
- Custom Domain Runtime Resolver Admin Evidence Review define evidências mínimas de flag on/off, safe miss, inativo e rollback.
- Owner Bootstrap Admin Surface Execution expõe o form no detalhe platform-only e delega o write para o command service.
- Custom Domain Runtime Resolver Activation Runbook gera checklist operacional, sem mudar ambiente automaticamente.
- Owner Bootstrap Admin Surface Closure fecha a surface para uso interno controlado.
- Custom Domain Runtime Staging Activation Evidence prepara o gate produtivo com evidências declarativas.
- Owner Bootstrap Production Evidence define evidência produtiva declarativa para owner inicial.
- Custom Domain Runtime Production Gate Review retorna GO/NO-GO antes de ativação real.
- Owner Bootstrap Production Closure fecha a trilha produtiva de owner inicial.
- Custom Domain Runtime Production Activation Evidence registra evidência pós-GO de ativação por flag.
- Custom Domain Runtime Production Closure fecha o runtime produtivo de domínio customizado com rollback por flag.
- Store Management Track Closure encerra a trilha Platform Store Management e retorna para re-seleção de ROI.
- System ROI Re-Selection executável em `tenants` recomenda `System Validation Pass 2 — Storefront/Admin Smoke & Template Regression` quando há regressão visível confirmada.
- System Validation Pass 2 adiciona `system_template_regression_smoke` para validar Home, Loja, Login, Meus pedidos, `/ops/` e `/ops/platform/tenants/` contra 404/link legado/template quebrado.
- Platform Self-Service Tenant Onboarding adiciona `/ops/platform/onboarding/` com wizard controlado para loja, plano interno, owner, branding mínimo, domínio e conclusão auditável.
- Storefront Institutional Hero adiciona campos `storefront_hero_*` em `Tenant` e query service de branding para renderizar hero tenant-owned na home da loja, com fallback visual para imagem de produto do próprio tenant.
- Storefront Branding Settings adiciona `/ops/branding/` para lojistas configurarem `Tenant.logo_url`, `Tenant.conversion_primary_color` e campos `Tenant.storefront_hero_*`, com permissão `storefront.branding.manage` e auditoria tenant-scoped.

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
audit

Readiness:
- customer area, auth pages e reset/forgot password
- login owner/admin tenant-scoped com rate limit e política de sessão
- `OwnerUser` separado de `Customer`
- `/ops/owners/` com CRUD administrativo, convite/reset e RBAC
- MFA owner/admin com fatores, recovery codes, challenge e readiness operacional
- métricas protegidas para owner access e MFA provider health
- platform owner context para portal central `hubx.market`

---

## subscriptions

Responsabilidade:
Gerenciar planos e assinaturas SaaS da plataforma.

Entidades principais:
SubscriptionPlan
SubscriptionCoupon
TenantSubscription
SubscriptionAcquisitionLead

Eventos:
subscription.acquisition_requested
subscription.acquisition_converted
subscription.acquisition_discarded
subscription.coupon_created
subscription.coupon_status_changed
subscription.coupon_applied
tenant.self_service_created
tenant.self_service_signup_completed
subscription.activated  
subscription.canceled

Dependências:
tenants
accounts
audit

Readiness:
- modelo `SubscriptionPlan` com preço de referência, modelo comercial, take rate, mínimo mensal, limites de produto/pedido e features públicas
- modelo `SubscriptionCoupon` platform-scope para descontos comerciais de planos SaaS
- modelo `TenantSubscription` com estado tenant-scoped, provider-alvo de billing e snapshots promocionais
- modelo `SubscriptionAcquisitionLead`
- snapshots promocionais em lead, onboarding e assinatura sem alterar `SubscriptionPlan.monthly_price`
- setup auditável por `subscription_commands`
- admin read-only em `/ops/subscriptions/`
- gestão platform de cupons SaaS em `/ops/platform/subscription-coupons/` com `subscriptions.manage`
- planos públicos em `/plans/` com Essencial, Pro e Enterprise em linguagem de produtos/pedidos/take rate
- `/plans/` e `/plans/signup/` aceitam `coupon_code` opcional validado por `subscriptions`
- signup público controlado por feature flag/token em `/plans/signup/`
- Pro exige método de cobrança e segue onboarding assistido até existir fluxo seguro
- `TenantSubscription` preserva estado/referências externas do billing method sem dados sensíveis de cartão
- `/ops/subscriptions/billing-method/` acompanha o billing method por tenant, garante cliente Asaas e só marca o método como ativo após confirmação trusted do provider
- fila platform de aquisições em `/ops/platform/acquisitions/`
- `commercial_terms` expõe contrato estável para catalog, checkout e payments

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
ProductImage
StorefrontDiscoveryEventLog

Observação:
`Brand`, `Category`, `Tag`, `ProductCategory` e `ProductTag` ainda não existem como modelos normalizados. O corte atual usa campos simples em `Product`, como `brand_name` e `category_label`.

Eventos:
product.created
product.updated
product.deactivated
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
- CRUD administrativo básico de produtos implementado em `/ops/catalog/products/`, com create/update em `Product` + variante padrão e desativação sem exclusão física;
- limite comercial de produtos aplicado em criação/reativação, contando `active` e `draft` e ignorando `inactive`;
- analytics brutos de discovery/PDP/CTA;
- Battery I adiciona baseline de conversão, funil PDP/CTA, drop-off de busca/facet e experimento `product_card_priority_v1`;
- o experimento altera ranking de cards com base em sinais recentes, sem redesenhar storefront inteiro.
- API pública read-only list/detail protegida por API key `read:catalog`.

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
subscriptions

Readiness:
- bloqueio de início de pagamento quando `monthly_paid_order_limit` do plano ativo foi atingido no mês;
- contagem usa pedidos `paid` por `payment_confirmed_at`;
- pedidos pendentes, cancelados e carrinhos não contam.

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
Integração com gateway, tentativas de pagamento, conciliação financeira, refund e taxa Hubx.

Entidades principais:
PaymentAttempt
PaymentRefund
PlatformFeeLedger

Eventos:
payment.created  
payment.paid  
payment.failed  
payment.refunded
platform_fee.recorded
platform_fee.minimum_adjustment_created
platform_fee.adjustment_required

Dependências:
orders
subscriptions

Readiness:
- provider Asaas para checkout hospedado de pedidos, com Pagar.me como alternativa configurável
- split Asaas para taxa Hubx quando `PAYMENTS_HUBX_SPLIT_ENABLED` e `ASAAS_HUBX_WALLET_ID` estão configurados
- ledger idempotente da taxa Hubx por pedido pago
- fechamento mensal do Pro cria ajuste complementar quando 2% do mês não atinge R$ 259,90
- cobrança complementar Asaas do Pro via `close_platform_fee_minimums --collect` ou flag `PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED`
- validação sandbox via `payment_sandbox_validate_platform_billing`
- política de inadimplência Pro via `enforce_platform_fee_delinquency`
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
- modelo tenant-scoped
- agregados approved-only para PDP por application query
- submissão customer e elegibilidade inicial
- moderação admin/ops implementada em `/ops/reviews/`

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
8. Para a fotografia atual da implementação, consulte docs/implementation-inventory.md.

---

# Objetivo

Facilitar navegação arquitetural do Hubx Market e garantir que novos desenvolvimentos respeitem a organização modular do sistema.
