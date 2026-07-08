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
- publicar termos comerciais dos planos
- ativar assinatura
- suspender tenant
- expor aquisição pública segura

## Regras de negócio
- assinatura SaaS pertence ao tenant.
- plano define preço mensal de referência, moeda, status, quota operacional incluída, lista pública de features e termos comerciais executáveis.
- os termos comerciais do plano são `billing_model`, `platform_fee_percent`, `minimum_monthly_fee`, `product_limit`, `monthly_paid_order_limit`, `requires_hubx_checkout` e `requires_billing_method`.
- planos públicos atuais:
  - Essencial: `take_rate_only`, 2% dos pedidos pagos, mínimo R$ 0, até 100 produtos e 300 pedidos pagos/mês.
  - Pro: `minimum_commitment`, 2% dos pedidos pagos ou mínimo R$ 259,90/mês, até 500 produtos e 1.500 pedidos pagos/mês.
  - Enterprise: `custom`, termos negociados manualmente.
- estado da assinatura pode ser `trialing`, `active`, `past_due`, `suspended` ou `canceled`.
- nos planos públicos atuais, a assinatura nasce `active`; `trialing` e `trial_ends_at` ficam restritos a planos legados/compatibilidade que ainda definam `trial_days`.
- a assinatura registra provider-alvo de billing SaaS (`billing_provider_code`/`billing_provider_label`), com `asaas` como default, sem chamar API externa nesta etapa.
- enforcement real de limite deve consumir `subscriptions.application.commercial_terms` e não consultar `SubscriptionPlan` diretamente fora da boundary.
- catálogo usa `product_limit`; checkout usa `monthly_paid_order_limit`; payments usa `platform_fee_percent` e `minimum_monthly_fee`.
- Pro exige método de cobrança ativo para garantir o mínimo mensal; enquanto não houver fluxo seguro de billing method, o signup público bloqueia esse plano e direciona para onboarding assistido.
- `TenantSubscription` guarda estado do billing method em `billing_method_status`, referência externa do cliente em `billing_external_reference`, URL de cobrança/setup em `billing_checkout_url` e, quando houver token seguro externo, `billing_method_reference`.
- `billing_method_reference` nunca deve armazenar número de cartão, CVV ou dados sensíveis; apenas referência tokenizada/provider-owned.
- `/ops/subscriptions/billing-method/` é a surface tenant-scoped para acompanhar o billing method e garantir cliente Asaas quando a integração estiver habilitada; o método só muda para `active` por confirmação segura/trusted do provider.
- política de inadimplência do Pro pode atualizar `TenantSubscription.status` para `past_due` ou `suspended` a partir de ledgers complementares não pagos.
- quando todos os complementos ficam pagos/cancelados, a política pode reativar assinatura `past_due`/`suspended` para `active`.
- cupons comerciais de planos SaaS pertencem a `SubscriptionCoupon`, platform-scope, e não reutilizam `coupons.Coupon`.
- cupom SaaS válido nunca altera `SubscriptionPlan.monthly_price`; desconto e preço efetivo ficam em snapshots comerciais no lead, onboarding e assinatura.
- desconto fixo é limitado ao preço mensal do plano; desconto percentual é limitado a 100%.
- aquisição assistida em `/plans/` cria apenas `SubscriptionAcquisitionLead`; não cria tenant, owner, assinatura, invoice, pagamento ou catálogo.
- signup self-service em `/plans/signup/` fica atrás de `HUBX_PUBLIC_SIGNUP_ENABLED`, pode exigir `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN` e delega provisionamento para `tenants`.
- dados de cartão ou método de cobrança não devem ser coletados por campos livres de `/plans/` nem `/plans/signup/`.

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
- cards públicos exibem preço simples, limite de produtos, limite de pedidos pagos e recursos do plano sem linguagem interna;
- o CTA `Criar loja self-service` aparece apenas para plano público elegível, sem `requires_billing_method` e sem `billing_model=custom`;
- `SubscriptionAcquisitionLead` guarda snapshots do plano solicitado, loja, subdomínio desejado, contato e status;
- `SubscriptionAcquisitionLead`, `TenantOnboarding` e `TenantSubscription` guardam snapshots promocionais quando `coupon_code` é válido;
- `subscriptions.application.commercial_terms.get_tenant_commercial_terms(...)` entrega um contrato estável para enforcement em outros módulos;
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
- self-service cria `TenantSubscription(status=active)` para planos sem trial e mantém o tenant em `maintenance_mode`;
- a assinatura criada no self-service registra o provider-alvo de billing SaaS, por padrão `Asaas`, para posterior acompanhamento comercial;
- planos com `requires_billing_method=True` não entram no self-service público até existir fluxo seguro de captura/cobrança;
- `/plans/signup/` lista apenas planos self-service elegíveis; Pro e Enterprise ficam no onboarding assistido;
- quando o modo controlado estiver ativo, `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN` é obrigatório antes de qualquer criação;
- conflitos concorrentes de slug/subdomínio devem voltar como erro de formulário;
- cupom inválido em `/plans/` bloqueia criação de lead;
- cupom inválido em `/plans/signup/` bloqueia criação de tenant, owner e assinatura;
- conversão exige `platform.tenants.manage`;
- gestão de cupom SaaS exige `subscriptions.manage`, liberada para `owner` e `admin`;
- leitura da fila usa `platform.tenants.view`;
- metadados de auditoria não devem carregar mensagem ou PII além do necessário para rastreabilidade operacional;
- chamada real de cobrança recorrente complementar pertence a `payments` e não aceita ativação manual por formulário livre.
- cobrança complementar Asaas do Pro pertence a `payments`; `subscriptions` apenas preserva estado/referências provider-owned do billing method no tenant, sem reexibir referência sensível em template.
- comandos de inadimplência também pertencem a `payments` como orquestração financeira, mas devem alterar `TenantSubscription.status` de forma auditada.

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
- **Go para expor termos comerciais consumíveis por catálogo, checkout e payments**.
- payments pode consumir snapshot comercial para taxa Hubx sem mover cobrança de pedido para `subscriptions`.
- enforcement deve consumir `TenantSubscription`/`CommercialTerms` por contrato explícito, não por queries espalhadas.

## Integração com Platform Self-Service

- o portal `/ops/platform/onboarding/` consome `SubscriptionPlan` ativo como contrato interno de billing;
- a fila `/ops/platform/acquisitions/` pode criar uma jornada de onboarding a partir de um lead público;
- ao concluir uma jornada com os planos públicos atuais, `TenantSubscription` é criada em `active`; `trialing` só permanece para planos legados/compatibilidade com `trial_days`;
- há provider-alvo registrado para billing SaaS, por padrão Asaas;
- cobrança complementar do Pro ainda depende de fluxo seguro de método de cobrança, mas o ledger de diferença mensal já pertence a `payments`;
- pagamentos de pedidos continuam pertencendo a `payments`; `subscriptions` fornece apenas os termos comerciais.

### Próxima bateria recomendada

**Battery F — Audit Instrumentation Expansion**
