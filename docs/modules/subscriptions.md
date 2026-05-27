# Subscriptions

## Responsabilidade
Gerenciar planos e assinaturas SaaS.

## Entidades principais
- Plan
- Subscription
- Invoice

## Casos de uso
- iniciar trial
- ativar assinatura
- suspender tenant

## Regras de negócio
- assinatura SaaS pertence ao tenant.
- plano define preço mensal, moeda, status e quota operacional incluída.
- estado da assinatura pode ser `trialing`, `active`, `past_due`, `suspended` ou `canceled`.
- esta fundação não chama billing provider e não acopla pagamentos de loja.
- enforcement real de plano deve passar por boundary própria.

## Battery E — Subscriptions & Tenant Billing Foundation Closure

- o módulo `subscriptions` agora possui fundação mínima de plano e assinatura tenant-scoped.
- modelos:
  - `SubscriptionPlan`;
  - `TenantSubscription`.
- application services:
  - `subscriptions.application.subscription_commands`;
  - `subscriptions.application.subscription_queries`;
  - `subscriptions.application.subscriptions_foundation_queries`.
- surface admin:
  - `/ops/subscriptions/`.
- comando:
  - `python manage.py subscriptions_foundation --domain-contract-ready --plan-model-ready --tenant-subscription-state-ready --admin-read-surface-review-ready --admin-read-surface-ready --enforcement-boundary-ready --audit-events-ready --no-billing-provider-created --no-store-payment-coupling --docs-updated --decision-recorded`

### Ondas fechadas

1. Subscription Domain Contract Review.
2. Subscription Plan Model Execution.
3. Tenant Subscription State Execution.
4. Subscription Admin Read Surface Review.
5. Subscription Admin Read Surface Execution.
6. Subscription Enforcement Boundary Review.
7. Subscriptions Foundation Closure Review.

### Decisão

- **Go para fundação de billing SaaS tenant-scoped**.
- **No-Go para provider de cobrança real nesta bateria**.
- **No-Go para acoplar pagamentos de pedido/loja ao plano SaaS**.
- enforcement futuro deve consumir `TenantSubscription` por contrato explícito, não por queries espalhadas.

### Próxima bateria recomendada

**Battery F — Audit Instrumentation Expansion**
