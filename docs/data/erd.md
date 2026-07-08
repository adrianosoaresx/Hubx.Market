# ERD

## 1. Visão geral do banco
- PostgreSQL único
- multi-tenant por `tenant_id`
- isolamento lógico
- foco em e-commerce SaaS

## 2. Agrupamento por domínio

### Plataforma
- Tenant
- TenantOnboarding

`Tenant`

- `id`
- `name`
- `slug`
- `subdomain`
- `custom_domain`
- `logo_url`
- `conversion_primary_color`
- `storefront_hero_enabled`
- `storefront_hero_title`
- `storefront_hero_description`
- `storefront_hero_image_url`
- `storefront_hero_cta_label`
- `storefront_hero_cta_href`
- `is_active`
- `maintenance_mode`
- `created_at`
- `updated_at`

`TenantOnboarding`

- `id`
- `tenant_id → tenants.Tenant` nullable
- `status`
- `store_name`
- `store_slug`
- `store_subdomain`
- `custom_domain`
- `plan_code`
- `coupon_code_snapshot`
- `coupon_discount_type_snapshot`
- `coupon_discount_value_snapshot`
- `coupon_discount_total_snapshot`
- `effective_monthly_price_snapshot`
- `promotion_snapshot`
- `owner_email`
- `owner_name`
- `owner_role`
- `store_display_name`
- `primary_color`
- `blockers`
- `created_by_label`
- `completed_at`
- `created_at`
- `updated_at`

### Identidade
- PlatformUser
- OwnerUser
- OwnerMfaFactor
- AccountProfile
- Customer
- CustomerAddress

### Catálogo
- Product
- ProductVariant
- ProductImage
- StorefrontDiscoveryEventLog

### Carrinho / Checkout
- Cart
- CartItem
- CheckoutSession
- CheckoutSessionItem
- CheckoutRecoveryEvent

### Pedidos / Pagamentos
- Order
- OrderItem
- OrderStatusHistory
- PaymentAttempt
- PaymentRefund
- PlatformFeeLedger

### Logística
- Shipment
- ShipmentStatusHistory
- ShippingProviderSettings
- ShippingProviderSettingsHistory

### Marketing
- Coupon
- CouponRedemption
- ProductReview
- NewsletterSubscriber
- Page

### Notificações
- EmailLog

### Assinatura SaaS
- SubscriptionPlan
- SubscriptionCoupon
- TenantSubscription
- SubscriptionAcquisitionLead

### Entidades planejadas, ainda não implementadas como modelos
- Brand
- Category
- Tag
- ProductCategory
- ProductTag
- Invoice
- SubscriptionPayment

## 3. Relacionamentos principais
- Tenant 1:N OwnerUser
- Tenant 1:N OwnerMfaFactor
- OwnerUser 1:N OwnerMfaFactor
- Tenant 1:N AccountProfile
- Tenant 1:N Customer
- Customer 1:N AccountProfile (opcional)
- Tenant 1:N Product
- Product 1:N ProductVariant
- Product 1:N ProductImage
- Tenant 1:N StorefrontDiscoveryEventLog
- Customer 1:N CustomerAddress
- Tenant 1:N CheckoutSession
- CheckoutSession 1:N CheckoutSessionItem
- Tenant 1:N CheckoutRecoveryEvent
- CheckoutSession 1:N CheckoutRecoveryEvent (opcional; eventos podem existir sem sessão vinculada)
- Customer 1:N Order (opcional e preferencial para integrações da área logada)
- Order 1:N OrderItem
- Order 1:N OrderStatusHistory
- Order 1:N PaymentAttempt
- Order 1:N PaymentRefund
- Order 1:N PlatformFeeLedger
- PaymentAttempt 1:N PaymentRefund
- PaymentAttempt 1:N PlatformFeeLedger
- Order 1:1 Shipment
- Shipment 1:N ShipmentStatusHistory
- Tenant 1:1 ShippingProviderSettings
- ShippingProviderSettings 1:N ShippingProviderSettingsHistory
- Tenant 1:N Coupon
- Coupon 1:N CouponRedemption
- Order 1:N CouponRedemption
- Tenant 1:N EmailLog
- Product 1:N Review
- Tenant 1:N Page
- Tenant 1:N NewsletterSubscriber
- Tenant 1:N AuditLog (opcional; eventos platform-scope podem ter tenant vazio)
- Tenant 1:N ApiKey
- OwnerUser 1:N ApiKey (opcional)
- Tenant 1:1 TenantSubscription
- SubscriptionPlan 1:N TenantSubscription
- SubscriptionPlan 1:N SubscriptionCoupon
- SubscriptionPlan 1:N SubscriptionAcquisitionLead
- TenantOnboarding 1:0..1 SubscriptionAcquisitionLead

## 4. Observações de modelagem
- preço pertence à ProductVariant
- estoque pertence à ProductVariant
- CRUD administrativo de `Product` grava preço/estoque na `ProductVariant` padrão
- `ProductVariant` pode preservar atributos avançados (`label`, `option_values`, `barcode`, `weight_grams`, `position`, `is_active`)
- desativação de variante é lógica e não remove histórico; o produto deve manter ao menos uma variante ativa
- `Brand`, `Category` e `Tag` normalizados ainda não existem no corte atual; `Product` preserva `brand_name` e `category_label` como campos simples
- checkout pode persistir snapshots transitórios antes da criação do pedido
- `CheckoutSessionItem` pode preservar `variant_sku` como vínculo explícito com a variante escolhida
- `Coupon` deve ser único por `(tenant, code)` e começar apenas com desconto percentual/fixo simples
- `Coupon.discount_type` inicial aceita `percent` e `fixed`; validade temporal é opcional por `starts_at`/`ends_at`
- `Order` deve receber snapshot promocional do checkout em vez de recalcular cupom após criação
- contabilidade de cupom usa entidade de resgate ligada a tenant/coupon/order, preservando snapshot de código e desconto
- `CouponRedemption` deve ser idempotente por tenant, pedido e código de cupom aplicado
- OrderItem guarda `price_snapshot`
- `OrderItem` pode preservar `variant_sku` como snapshot explícito da variante comprada
- `Order` pode guardar `inventory_reserved_at` para indicar quando a baixa operacional de estoque já foi aplicada após o pagamento
- `Order` pode guardar `inventory_recovered_at` para indicar quando a devolução operacional de estoque já foi aplicada após cancelamento seguro
- `Order` pode guardar `inventory_finalized_at` para indicar quando a reserva operacional já foi consumida de forma final após a entrega
- `PaymentRefund` é ledger tenant-scoped de refund/estorno, idempotente por `(tenant, idempotency_key)`.
- `PaymentRefund` começa registrando intenção ou bloqueio; execução real no provider fica fora do contrato inicial.
- `PlatformFeeLedger` é ledger tenant-scoped da taxa Hubx, idempotente por `ledger_key`, com vínculo opcional para pedido e tentativa de pagamento.
- `PlatformFeeLedger` registra take rate por pedido pago e ajuste mensal do Pro quando o total do percentual fica abaixo do mínimo.
- produto inativo não é deletado
- customer é isolado por tenant
- `OwnerMfaFactor` deve pertencer ao mesmo tenant do `OwnerUser` e é único por `(tenant, owner, factor_type, provider_key)`
- `OwnerMfaFactor` representa enrollment MFA; desafio/verificação real fica fora do modelo inicial
- `Customer` já possui base persistida mínima para leituras administrativas de list/detail
- `Customer` também pode guardar flags operacionais leves para execução manual no admin (`marked_for_followup`, `marked_for_reengagement`, `marked_as_priority`)
- `CustomerAddress` passa a existir como base persistida mínima para leituras futuras da área logada
- `AccountProfile.customer` e `Order.customer` são vínculos opcionais e backward-compatible; quando ausentes, o sistema ainda pode operar via `tenant + email`
- `OrderStatusHistory` pode guardar atribuição leve de origem/contexto (`source_type`, `source_label`, `actor_label`) sem virar um framework completo de auditoria
- `ProductImage` fornece mídia mínima persistida via URL, sem introduzir pipeline de upload/CDN
- `StorefrontDiscoveryEventLog` registra eventos brutos de descoberta por tenant, com `session_key_hash` e payload público allowlisted
- owner e customer são entidades diferentes
- `AccountProfile` serve como base de experiência de conta, não como substituto de `Customer`
- `EmailLog` é tenant-scoped e usa `recipient_delivery_key` para deduplicar uma unidade de entrega por destinatário/canal
- `Page` é tenant-scoped, usa `slug` único por tenant e só aparece no storefront quando `status=published`
- `NewsletterSubscriber` é tenant-scoped, único por `(tenant, email)` e preserva opt-in/opt-out por status
- `AuditLog` registra eventos tenant-scoped por padrão; tenant vazio só é válido para eventos platform-scope explícitos
- `ApiKey` é tenant-scoped, guarda apenas hash do segredo, usa prefixo único e deve ser revogada por status/timestamp, não deletada.

## API Keys — ApiKey

`ApiKey`

- `id`
- `tenant_id → tenants.Tenant`
- `owner_id → accounts.OwnerUser` opcional
- `name`
- `prefix`
- `key_hash`
- `scopes`
- `status`
- `created_by_label`
- `created_at`
- `updated_at`
- `last_used_at`
- `revoked_at`
- `revoked_by_label`

Relacionamentos:

- `Tenant 1:N ApiKey`
- `OwnerUser 1:N ApiKey`

Notas:

- `prefix` é único.
- segredo claro não é persistido.
- `status=revoked` preserva histórico.
- runtime authentication fica fora do modelo inicial.

## API Keys — ApiKeyQuota

`ApiKeyQuota`

- `id`
- `tenant_id → tenants.Tenant`
- `api_key_id → api_keys.ApiKey`
- `endpoint`
- `scope`
- `window_seconds`
- `limit`
- `status`
- `created_by_label`
- `updated_by_label`
- `created_at`
- `updated_at`

Relacionamentos:

- `Tenant 1:N ApiKeyQuota`
- `ApiKey 1:N ApiKeyQuota`

Notas:

- único por `(tenant, api_key, endpoint)`.
- `limit` e `window_seconds` devem ser positivos.
- não representa cobrança, plano ou subscription.

## API Keys — ApiKeyQuotaUsage

`ApiKeyQuotaUsage`

- `id`
- `tenant_id → tenants.Tenant`
- `api_key_id → api_keys.ApiKey`
- `quota_id → api_keys.ApiKeyQuota` opcional
- `endpoint`
- `window_start`
- `window_seconds`
- `count`
- `created_at`
- `updated_at`

Relacionamentos:

- `Tenant 1:N ApiKeyQuotaUsage`
- `ApiKey 1:N ApiKeyQuotaUsage`
- `ApiKeyQuota 1:N ApiKeyQuotaUsage`

Notas:

- único por `(tenant, api_key, endpoint, window_start, window_seconds)`.
- registra uso agregado por janela; não guarda segredo, header, hash ou API key em claro.

## Payments — PlatformFeeLedger

`PlatformFeeLedger`

- `id`
- `tenant_id → tenants.Tenant`
- `order_id → orders.Order` nullable
- `payment_attempt_id → payments.PaymentAttempt` nullable
- `ledger_key`
- `kind`
- `status`
- `plan_code_snapshot`
- `plan_name_snapshot`
- `billing_model_snapshot`
- `platform_fee_percent_snapshot`
- `minimum_monthly_fee_snapshot`
- `billing_period_start`
- `billing_period_end`
- `basis_amount`
- `fee_amount`
- `currency_code`
- `provider_code`
- `provider_reference`
- `metadata`
- `created_at`
- `updated_at`

Relacionamentos:

- `Tenant 1:N PlatformFeeLedger`
- `Order 1:N PlatformFeeLedger`
- `PaymentAttempt 1:N PlatformFeeLedger`

Notas:

- `ledger_key` é único e garante idempotência.
- `kind=order_take_rate` representa a taxa Hubx de um pedido pago.
- `kind=pro_minimum_adjustment` representa a diferença mensal do Pro até o mínimo contratado.
- `status=split_requested` indica que o split foi enviado ao provider; `pending_collection` indica cobrança complementar ou tratativa pendente.
- refund, chargeback e falhas posteriores devem marcar ajuste no ledger existente, sem criar cobrança duplicada.

## Subscriptions — SubscriptionPlan

`SubscriptionPlan`

- `id`
- `code`
- `name`
- `description`
- `monthly_price`
- `currency_code`
- `included_api_quota`
- `trial_days`
- `requires_payment_method`
- `billing_model`
- `platform_fee_percent`
- `minimum_monthly_fee`
- `product_limit`
- `monthly_paid_order_limit`
- `requires_hubx_checkout`
- `requires_billing_method`
- `feature_list`
- `status`
- `created_at`
- `updated_at`

Relacionamentos:

- `SubscriptionPlan 1:N TenantSubscription`
- `SubscriptionPlan 1:N SubscriptionCoupon`
- `SubscriptionPlan 1:N SubscriptionAcquisitionLead`

Notas:

- `code` é único.
- `monthly_price` não pode ser negativo.
- `trial_days` e `requires_payment_method` permanecem no modelo por compatibilidade, mas a precificação pública atual usa `billing_model`, `platform_fee_percent`, `minimum_monthly_fee`, limites e `requires_billing_method`.
- cartão real, token, CVV e validade não são coletados por formulário público ou tenant-owned.
- `billing_model` aceita `take_rate_only`, `minimum_commitment` ou `custom`.
- `platform_fee_percent` e `minimum_monthly_fee` não podem ser negativos.
- `product_limit` conta produtos ativos e rascunhos; `monthly_paid_order_limit` conta pedidos pagos por mês.
- `requires_billing_method` bloqueia signup self-service até existir fluxo seguro de método de cobrança.
- `feature_list` guarda linhas públicas do card de plano.
- não representa invoice nem cobrança real.

## Subscriptions — SubscriptionCoupon

`SubscriptionCoupon`

- `id`
- `plan_id → subscriptions.SubscriptionPlan` nullable
- `code`
- `name`
- `status`
- `discount_type`
- `discount_value`
- `starts_at`
- `ends_at`
- `created_at`
- `updated_at`

Relacionamentos:

- `SubscriptionPlan 1:N SubscriptionCoupon`

Notas:

- `code` é único e normalizado em uppercase.
- `plan_id` nulo significa cupom aplicável a qualquer plano ativo.
- é platform-scope e não usa `coupons.Coupon`, que permanece tenant-scoped para carrinho/pedido.
- desconto fixo é capado no preço mensal do plano; percentual é capado em 100%.

## Subscriptions — TenantSubscription

`TenantSubscription`

- `id`
- `tenant_id → tenants.Tenant`
- `plan_id → subscriptions.SubscriptionPlan`
- `status`
- `started_at`
- `trial_ends_at`
- `current_period_ends_at`
- `canceled_at`
- `external_reference`
- `billing_provider_code`
- `billing_provider_label`
- `billing_external_reference`
- `billing_checkout_url`
- `billing_method_status`
- `billing_method_reference`
- `billing_method_verified_at`
- `coupon_code_snapshot`
- `coupon_discount_type_snapshot`
- `coupon_discount_value_snapshot`
- `coupon_discount_total_snapshot`
- `effective_monthly_price_snapshot`
- `promotion_snapshot`
- `notes`
- `created_at`
- `updated_at`

Relacionamentos:

- `Tenant 1:1 TenantSubscription`
- `SubscriptionPlan 1:N TenantSubscription`

Notas:

- guarda estado SaaS do tenant.
- registra provider-alvo de billing SaaS sem criar cobrança externa.
- guarda apenas referências externas provider-owned do billing method; não guarda dados de cartão nem permite inserção manual de token em formulário livre.
- guarda snapshots promocionais quando criado a partir de cupom SaaS válido.
- não acopla pagamentos de pedidos da loja.

## Subscriptions — SubscriptionAcquisitionLead

`SubscriptionAcquisitionLead`

- `id`
- `plan_id → subscriptions.SubscriptionPlan`
- `onboarding_id → tenants.TenantOnboarding` nullable
- `status`
- `plan_code_snapshot`
- `plan_name_snapshot`
- `plan_monthly_price_snapshot`
- `plan_currency_snapshot`
- `coupon_code_snapshot`
- `coupon_discount_type_snapshot`
- `coupon_discount_value_snapshot`
- `coupon_discount_total_snapshot`
- `effective_monthly_price_snapshot`
- `promotion_snapshot`
- `store_name`
- `desired_subdomain`
- `contact_name`
- `contact_email`
- `contact_phone`
- `message`
- `source`
- `converted_at`
- `discarded_at`
- `created_at`
- `updated_at`

Relacionamentos:

- `SubscriptionPlan 1:N SubscriptionAcquisitionLead`
- `TenantOnboarding 1:0..1 SubscriptionAcquisitionLead`

Notas:

- representa intenção pública de aquisição SaaS.
- preserva snapshot comercial de cupom SaaS válido antes da conversão para onboarding.
- não representa assinatura ativa, invoice, pagamento ou tenant provisionado.

## Accounts — OwnerMfaRecoveryCode

`OwnerMfaRecoveryCode`

- `id`
- `tenant_id → tenants.Tenant`
- `owner_id → accounts.OwnerUser`
- `code_hash`
- `label`
- `used_at`
- `created_at`

Relacionamentos:

- `Tenant 1:N OwnerMfaRecoveryCode`
- `OwnerUser 1:N OwnerMfaRecoveryCode`

Notas:

- o código claro não é persistido.
- `used_at IS NULL` indica código disponível.
