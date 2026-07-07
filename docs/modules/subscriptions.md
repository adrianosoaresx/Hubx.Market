# Subscriptions

## Responsabilidade
Gerenciar planos e assinaturas SaaS.

## Entidades principais
- SubscriptionPlan
- SubscriptionCoupon
- TenantSubscription
- SubscriptionAcquisitionLead

Entidades fora do corte atual:
- Invoice
- SubscriptionPayment

## Casos de uso
- iniciar trial
- ativar assinatura
- suspender tenant

## Regras de negócio
- assinatura SaaS pertence ao tenant.
- plano define preço mensal, moeda, status, quota operacional incluída, dias de trial, exigência de payment method e lista pública de features.
- estado da assinatura pode ser `trialing`, `active`, `past_due`, `suspended` ou `canceled`.
- quando uma assinatura nasce `trialing` e o plano possui `trial_days`, `trial_ends_at` deve ser calculado a partir de `started_at`.
- a assinatura registra provider-alvo de billing SaaS (`billing_provider_code`/`billing_provider_label`), com `asaas` como default, sem chamar API externa nesta etapa.
- esta fundação não cria invoice/cobrança recorrente no billing provider e não acopla pagamentos de loja.
- enforcement real de plano deve passar por boundary própria.
- cupons comerciais de planos SaaS pertencem a `SubscriptionCoupon`, platform-scope, e não reutilizam `coupons.Coupon`.
- cupom SaaS válido nunca altera `SubscriptionPlan.monthly_price`; desconto e preço efetivo ficam em snapshots comerciais no lead, onboarding e assinatura.
- desconto fixo é limitado ao preço mensal do plano; desconto percentual é limitado a 100%.
- aquisição assistida em `/plans/` cria apenas `SubscriptionAcquisitionLead`; não cria tenant, owner, assinatura, invoice, pagamento ou catálogo.
- signup self-service em `/plans/signup/` fica atrás de `HUBX_PUBLIC_SIGNUP_ENABLED`, pode exigir `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN` e delega provisionamento para `tenants`.
- cartão obrigatório é contrato comercial exposto por `SubscriptionPlan.requires_payment_method`; dados de cartão não devem ser coletados por `/plans/` nem `/plans/signup/`.

## Public SaaS Acquisition

Status: **implementado como lead seguro**.

Rotas:

```text
GET  /plans/
POST /plans/
GET  /plans/signup/
POST /plans/signup/
GET  /ops/platform/acquisitions/
GET  /ops/platform/acquisitions/<lead_id>/
POST /ops/platform/acquisitions/<lead_id>/convert/
POST /ops/platform/acquisitions/<lead_id>/discard/
GET  /ops/platform/subscription-coupons/
POST /ops/platform/subscription-coupons/new/
POST /ops/platform/subscription-coupons/<coupon_id>/status/
```

Escopo entregue:

- `/plans/` lista apenas `SubscriptionPlan` ativo e recebe intenção pública de aquisição;
- `/plans/signup/` cria uma loja self-service somente quando a feature flag estiver ativa e o controle de acesso configurado for satisfeito;
- cards públicos exibem `trial_days`, `requires_payment_method`, preço após trial e `feature_list`;
- `SubscriptionAcquisitionLead` guarda snapshots do plano solicitado, loja, subdomínio desejado, contato e status;
- `SubscriptionAcquisitionLead`, `TenantOnboarding` e `TenantSubscription` guardam snapshots promocionais quando `coupon_code` é válido;
- `subscriptions.application.subscription_coupon_queries.validate_plan_coupon(plan_code, coupon_code)` retorna result codes explícitos para válido, inválido, expirado, não aplicável e indisponível;
- a fila platform permite revisar, converter ou descartar leads;
- `/ops/platform/subscription-coupons/` permite listar, criar e ativar/inativar cupons SaaS com `subscriptions.manage`;
- converter lead cria/preenche uma jornada `TenantOnboarding`, mas não conclui onboarding;
- descartar lead muda apenas o status do lead;
- eventos auditáveis platform-scope:
  - `subscription.acquisition_requested`;
  - `subscription.acquisition_converted`;
  - `subscription.acquisition_discarded`;
  - `subscription.coupon_created`;
  - `subscription.coupon_status_changed`;
  - `subscription.coupon_applied`.

Guardrails:

- o fluxo assistido de `/plans/` não provisiona `Tenant`, `OwnerUser`, `TenantSubscription`, catálogo ou cobrança;
- o fluxo self-service não cria lead, customer, catálogo, invoice, cobrança SaaS externa ou pagamento de loja;
- self-service cria `TenantSubscription(status=trialing, trial_ends_at=started_at + plan.trial_days)` e mantém o tenant em `maintenance_mode`;
- a assinatura criada no self-service registra o provider-alvo de billing SaaS, por padrão `Asaas`, para posterior ativação comercial;
- formulários públicos devem avisar que cartão é obrigatório quando aplicável, mas bloquear a expectativa de digitar cartão em campos livres;
- quando o modo controlado estiver ativo, `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN` é obrigatório antes de qualquer criação;
- conflitos concorrentes de slug/subdomínio devem voltar como erro de formulário;
- cupom inválido em `/plans/` bloqueia criação de lead;
- cupom inválido em `/plans/signup/` bloqueia criação de tenant, owner e assinatura;
- conversão exige `platform.tenants.manage`;
- gestão de cupom SaaS exige `subscriptions.manage`, liberada para `owner` e `admin`;
- leitura da fila usa `platform.tenants.view`;
- metadados de auditoria não devem carregar mensagem ou PII além do necessário para rastreabilidade operacional;
- chamada real ao billing provider, invoice recorrente, antifraude e checkout de assinatura continuam fora desta etapa.

## Battery E — Subscriptions & Tenant Billing Foundation Closure

- o módulo `subscriptions` agora possui fundação mínima de plano e assinatura tenant-scoped.
- modelos:
  - `SubscriptionPlan`;
  - `SubscriptionCoupon`;
  - `TenantSubscription`.
- application services:
  - `subscriptions.application.subscription_commands`;
  - `subscriptions.application.subscription_coupon_queries`;
  - `subscriptions.application.subscription_coupon_commands`;
  - `subscriptions.application.subscription_queries`;
  - `subscriptions.application.subscriptions_foundation_queries`.
- surface admin:
  - `/ops/subscriptions/`.
- seed demo:
  - `python manage.py seed_demo_saas_plans`.
- comando:
  - `python manage.py subscriptions_foundation --domain-contract-ready --plan-model-ready --tenant-subscription-state-ready --admin-read-surface-review-ready --admin-read-surface-ready --enforcement-boundary-ready --audit-events-ready --no-billing-provider-created --no-store-payment-coupling --docs-updated --decision-recorded`
  - neste comando, `--no-billing-provider-created` significa não criar recurso/cobrança externa no provider; registrar `billing_provider_code=asaas` na assinatura é permitido.

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
- **Go para registrar provider-alvo de billing SaaS na assinatura**.
- **No-Go para cobrança recorrente real nesta bateria**.
- **No-Go para acoplar pagamentos de pedido/loja ao plano SaaS**.
- enforcement futuro deve consumir `TenantSubscription` por contrato explícito, não por queries espalhadas.

## Integração com Platform Self-Service

- o portal `/ops/platform/onboarding/` consome `SubscriptionPlan` ativo como contrato interno de billing;
- a fila `/ops/platform/acquisitions/` pode criar uma jornada de onboarding a partir de um lead público;
- ao concluir uma jornada, `TenantSubscription` é criada em `trialing`;
- há provider-alvo registrado para billing SaaS, por padrão Asaas, mas não há invoice real, checkout de assinatura ou enforcement de plano no MVP;
- pagamentos de pedidos continuam pertencendo a `payments`, sem acoplamento com billing SaaS.

### Próxima bateria recomendada

**Battery F — Audit Instrumentation Expansion**
