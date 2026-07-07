# Domain Model

Este documento descreve o modelo conceitual do Hubx Market.

## Plataforma
### Tenant
Representa uma loja no SaaS.
- guarda configurações institucionais leves da home tenant-owned via `storefront_hero_*`
- guarda `logo_url` como imagem pública opcional da marca da loja, usada pelos componentes de identidade
- o hero institucional pode ter título, descrição, imagem remota, CTA e flag de exibição
- quando a imagem do hero não estiver configurada, a storefront pode usar fallback visual derivado do catálogo da própria loja
- esses campos não substituem catálogo, páginas institucionais nem page builder

### Plan
Representa um plano comercial da plataforma.

### Subscription
Representa a assinatura SaaS da loja.

## Identidade
### PlatformUser
Usuário do painel da plataforma.

### OwnerUser
Usuário administrador da loja.
- pertence a um tenant
- é separado de `Customer` e `AccountProfile`
- pode ser usado como destinatário administrativo quando ativo e habilitado para notificações

### OwnerMfaFactor
Fator de MFA cadastrado para um `OwnerUser`.
- pertence ao mesmo tenant do `OwnerUser`
- representa enrollment, não autenticação ativa nesta fase
- aceita tipos iniciais `totp`, `recovery_code` e `external`
- guarda apenas referência de segredo/provider, não segredo bruto obrigatório
- só é considerado pronto quando ativo e verificado

### AccountProfile
Perfil persistido mínimo para identidade, contato e preferências da experiência de conta, com vínculo opcional para `Customer`.

### Customer
Comprador da loja, isolado por tenant, com base persistida mínima para identidade, contato e leitura operacional administrativa.
- também pode guardar flags operacionais leves para execução manual:
  - `marked_for_followup`
  - `marked_for_reengagement`
  - `marked_as_priority`

### CustomerAddress
Endereço do customer.

## Catálogo
### Brand, Category e Tag
Entidades normalizadas planejadas para evolução futura do catálogo.

No corte atual elas ainda não existem como modelos próprios. O catálogo persistido usa campos simples em `Product`, como `brand_name` e `category_label`, e tags normalizadas ainda permanecem fora.

### Product
Entidade principal de catálogo.
No corte atual, também preserva dados simples de marca/categoria por campos denormalizados.
Pode ser criado/editado no admin de catálogo; desativação operacional altera status/visibilidade e não remove o registro.

### ProductVariant
SKU e unidade efetiva de venda.
Preço e estoque continuam pertencendo à variante, inclusive no CRUD administrativo.
A variante pode carregar atributos estruturados em `option_values`, rótulo operacional, código de barras, peso, ordenação, flag de ativa/inativa e indicação de padrão.
Desativar variante é operação lógica; o produto deve manter ao menos uma variante ativa.

### ProductImage
Imagem persistida mínima do produto, baseada em URL e ordenação simples para uso em storefront/admin.

### StorefrontDiscoveryEventLog
Log bruto mínimo de descoberta storefront.
- pertence a um tenant
- registra nome de evento catalogado
- salva sessão apenas como hash
- mantém payload público allowlisted
- não deve armazenar PII
- serve como evidência inicial para busca, facets, sort e PDP views

## Compra
### Cart
Carrinho persistente do customer.

### CartItem
Item do carrinho ligado à variante.

### CheckoutSession
Snapshot transitório do checkout por tenant, com contato, entrega, métodos e totais.

### CheckoutSessionItem
Snapshot dos itens exibidos durante o checkout.
- também pode preservar `variant_sku` para manter o vínculo explícito com a unidade vendável escolhida

### CheckoutRecoveryEvent
Evento tenant-scoped gerado quando um `result` conhecido de recovery é exibido na página de checkout.
- preserva `result_code`, `family`, `severity`, `recovery_action`, `stage` e vínculo opcional com `CheckoutSession`
- não representa pagamento, pedido criado ou mutação transacional

### Order
Pedido materializado no checkout, com vínculo opcional para `Customer` e snapshots preservados de customer.
- também pode guardar `inventory_reserved_at` para registrar quando a baixa operacional de estoque já foi aplicada
- também pode guardar `inventory_recovered_at` para registrar quando a devolução operacional de estoque já foi aplicada
- também pode guardar `inventory_finalized_at` para registrar quando a reserva operacional já virou consumo final após entrega

### OrderItem
Snapshot do item comprado.
- também pode preservar `variant_sku` como snapshot explícito da variante comprada

### OrderStatusHistory
Histórico leve de transições e eventos operacionais relevantes do pedido, usado para enriquecer timelines administrativas, com atribuição opcional de origem/contexto.

## Pagamento e logística
### PaymentAttempt
Tentativa de pagamento do pedido.
- pertence a um tenant
- referencia pedido
- preserva provider, valor, status, referência externa e trilha operacional da tentativa
- o provider inicial de checkout hospedado é Asaas, com Pagar.me mantido como alternativa configurável

### PaymentRefund
Ledger de refund/estorno financeiro.
- pertence a um tenant
- referencia pedido e, quando disponível, a tentativa paga
- preserva chave idempotente por tenant, valor, status, referência externa, blockers e metadados
- começa registrando intenção/bloqueio sem chamada real ao provider
- deve ser idempotente por `(tenant, idempotency_key)`

### Shipment
Informações de envio e rastreio.
- pertence a um tenant
- vincula um pedido a status logístico, tracking code, tracking URL e carrier
- é a base para eventos `shipment.sent` e `shipment.delivered`
- possui `ShipmentStatusHistory` para registrar transições operacionais por tenant

### ShippingProviderSettings
Configuração tenant-scoped do provider de tracking.
- define provider ativo, base URL, token e timeout
- quando ausente/inativo, shipping usa provider manual/local
- possui `ShippingProviderSettingsHistory` para auditoria de alterações operacionais

## Marketing e conteúdo
### Coupon
Cupom de desconto tenant-scoped.

Contrato mínimo planejado:

- pertence a um tenant
- possui código único por tenant
- pode ser percentual ou valor fixo
- pode ter janela opcional de validade
- começa sem segmentação por cliente, produto, categoria ou limite de uso
- uso/contabilidade é modelado por ledger de resgate tenant-scoped, não por contador mutável simples no cupom

### CouponRedemption
Ledger de resgate de cupom por pedido.
- pertence a um tenant
- referencia cupom quando resolvível
- referencia pedido
- preserva snapshot de código, desconto e payload promocional
- deve ser idempotente por tenant/pedido/código
- não recalcula regra promocional

### ProductReview
Avaliação de produto.
- pertence a um tenant e a um Product
- nasce com status `pending`
- pode ser `approved` ou `rejected` por moderação
- storefront deve exibir apenas reviews aprovadas
- rating fica entre 1 e 5

### NewsletterSubscriber
Assinatura de newsletter.
- pertence a um tenant
- usa e-mail único por tenant
- registra `status` como `subscribed` ou `unsubscribed`
- preserva origem e consentimento do opt-in
- descadastro muda status e timestamp, sem deletar o registro
- não representa campanha, segmentação ou envio real

### Page
Página institucional da loja.
- pertence a um tenant
- possui `slug` único por tenant
- pode estar em `draft` ou `published`
- storefront só pode renderizar páginas publicadas do tenant resolvido
- preserva SEO básico por `seo_title` e `seo_description`
- não deve ter fallback global entre lojas

## Operação
### AuditLog
Registro de ações administrativas.
- pode pertencer a um tenant ou, explicitamente, ao escopo platform
- preserva módulo, ação, entidade, ator, resumo e metadados sanitizados
- não executa correção nem efeito colateral
- leitura admin tenant-owned deve exigir tenant resolvido

### EmailLog
Registro de envios de e-mail.
- pertence a um tenant
- guarda snapshot de evento, intent, recipient e copy
- começa como unidade planejada antes de worker/provider real

### ApiKey
Chave de integração para API pública.

Regras:

- pertence a um `Tenant`.
- pode referenciar um `OwnerUser` como owner operacional.
- armazena apenas `key_hash`; o valor claro só aparece no resultado inicial de criação.
- possui `prefix` único para lookup seguro sem expor segredo completo.
- possui `scopes` declarativos.
- pode estar `active` ou `revoked`.
- revogação usa `revoked_at` e não remove o histórico.
- autenticação runtime já existe como boundary opt-in por view/DRF para endpoints públicos de catálogo.
- não redefine tenant; o tenant continua vindo do request/host.

### ApiKeyQuota
Quota comercial mínima para API pública.

Regras:

- pertence a um `Tenant` e a uma `ApiKey` do mesmo tenant.
- é definida por `endpoint`, `scope`, `window_seconds`, `limit` e `status`.
- `limit` e `window_seconds` precisam ser positivos.
- excesso de quota bloqueia runtime público com `429`.
- não cria cobrança, subscription, plano ou billing provider.

### ApiKeyQuotaUsage
Uso agregado de quota por janela.

Regras:

- pertence a um `Tenant` e a uma `ApiKey`.
- é único por tenant, API key, endpoint, início da janela e tamanho da janela.
- incrementa contador agregado; não armazena API key, header, segredo ou hash.
- pode referenciar a quota aplicada para rastreabilidade operacional.

### SubscriptionPlan
Plano SaaS disponível para tenants.

Regras:

- possui `code` único, nome, preço mensal, moeda e status.
- pode definir quota operacional incluída sem acoplar cobrança real.
- pode definir `trial_days`, `requires_payment_method` e `feature_list` para o contrato público de planos.
- `requires_payment_method` sinaliza requisito comercial de cartão, mas não autoriza coletar ou armazenar dados de cartão no formulário público.
- `archived` preserva histórico e não deve apagar assinaturas existentes.
- não representa invoice, pagamento de pedido ou cobrança de loja.

### SubscriptionCoupon
Cupom comercial platform-scope para planos SaaS.

Regras:

- pertence ao módulo `subscriptions`, não ao módulo tenant-scoped `coupons`.
- possui `code` único normalizado em uppercase, nome, status, tipo de desconto e valor.
- `plan` vazio permite uso em qualquer `SubscriptionPlan` ativo; `plan` preenchido restringe o cupom àquele plano.
- desconto percentual é limitado a 100%; desconto fixo é capado ao `SubscriptionPlan.monthly_price`.
- validação pública retorna result codes explícitos por `subscriptions.application.subscription_coupon_queries.validate_plan_coupon(...)`.
- não cria invoice, cobrança externa, chamada Asaas ou alteração retroativa de assinatura.

### TenantSubscription
Estado da assinatura SaaS de um tenant.

Regras:

- pertence a exatamente um `Tenant`.
- referencia um `SubscriptionPlan`.
- status pode ser `trialing`, `active`, `past_due`, `suspended` ou `canceled`.
- quando criada como `trialing` para plano com trial, deve ter `trial_ends_at` calculado a partir de `started_at + plan.trial_days`.
- registra provider-alvo de billing SaaS (`billing_provider_code`/`billing_provider_label`), por padrão `asaas`.
- pode guardar referência externa e URL de checkout futuras, mas chamada real de cobrança recorrente fica fora da fundação.
- quando nasce com cupom SaaS, guarda snapshots promocionais (`coupon_*_snapshot`, `effective_monthly_price_snapshot`, `promotion_snapshot`) sem alterar `SubscriptionPlan.monthly_price`.
- enforcement futuro deve consultar esse estado por application service/contrato explícito.

### SubscriptionAcquisitionLead
Intenção pública de aquisição de plano SaaS.

Regras:

- pertence a um `SubscriptionPlan` ativo no momento da criação.
- guarda snapshots de código, nome, preço mensal e moeda do plano solicitado.
- pode guardar snapshots de cupom SaaS validado em `/plans/`, preservando desconto e preço mensal efetivo.
- status pode ser `new`, `converted` ou `discarded`.
- pode referenciar um `TenantOnboarding` após conversão platform.
- não cria tenant, owner, assinatura, invoice, pagamento ou catálogo.
- conversão é ação platform controlada e apenas cria/preenche a jornada de onboarding.

### PublicTenantSignup
Fluxo público controlado para criação self-service de loja.

Regras:

- não é uma entidade persistida própria; é um caso de uso em `tenants.application.public_tenant_signup_commands`.
- exige plano ativo, `HUBX_PUBLIC_SIGNUP_ENABLED=1` e, quando controlado, `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN`.
- cria `Tenant` ativo em `maintenance_mode`, `TenantOnboarding` concluído, `TenantSubscription(status=trialing)` e `OwnerUser` inicial.
- respeita `SubscriptionPlan.trial_days` para encerrar o trial interno e exibe exigência de cartão quando `requires_payment_method=True`.
- aceita `coupon_code` opcional validado por `subscriptions`; cupom inválido bloqueia a criação antes de tenant, owner ou assinatura.
- copia snapshots promocionais para `TenantOnboarding` e `TenantSubscription`.
- registra Asaas como provider-alvo padrão de billing SaaS sem chamar API externa.
- `maintenance_mode` bloqueia storefront/checkout com 503, preservando acesso a `/accounts/` e `/ops/` para configuração.
- não cria `Customer`, catálogo, pedido, pagamento, invoice ou domínio customizado.
- não coleta dados de cartão; payment method real pertence a fluxo seguro hospedado de billing SaaS.
- e-mail já associado a usuário/owner existente deve seguir aquisição assistida.

## OwnerMfaRecoveryCode

Representa códigos de recuperação de MFA para `OwnerUser`.

Regras:

- pertence a um `Tenant` e a um `OwnerUser` do mesmo tenant.
- armazena apenas `code_hash`.
- código em texto claro só pode ser exibido uma vez na geração operacional.
- `used_at` torna o código inutilizável para novos challenges.
- readiness de MFA só deve considerar recovery codes enquanto houver código não usado.
