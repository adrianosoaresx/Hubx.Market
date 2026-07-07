# Plans and Pricing

## Estrutura conceitual
O Hubx Market terá planos de assinatura para as lojas.

## Trial comercial MVP

Status: implementado como contrato de plano, sem cobrança recorrente automática.

- os planos comerciais podem declarar `trial_days=30`.
- quando `requires_payment_method=True`, o template público exibe cartão obrigatório.
- cartão é requisito de ativação comercial, mas o formulário público não coleta nem armazena dados de cartão.
- a coleta real de cartão deve acontecer somente em fluxo seguro hospedado do provider de billing SaaS, inicialmente Asaas.
- durante o trial, a assinatura tenant-scoped fica em `TenantSubscription(status=trialing)` com `trial_ends_at` calculado pelo plano.
- a assinatura registra provider-alvo de billing, por padrão `asaas`, mas não existe cobrança SaaS automática, invoice recorrente ou enforcement comercial nesta etapa.

## Aquisição pública v1

Status: implementado como lead seguro.

- `/plans/` exibe planos ativos de `SubscriptionPlan`.
- o formulário público cria `SubscriptionAcquisitionLead`.
- o lead guarda snapshots do plano solicitado para preservar o contexto comercial.
- nenhum tenant, owner, assinatura, invoice, pagamento ou catálogo é criado pela página pública.
- a revisão acontece em `/ops/platform/acquisitions/`.
- converter um lead cria apenas uma jornada em `/ops/platform/onboarding/`.
- demo local pode ser preparada com `python manage.py seed_demo_saas_plans`.

## Cupons comerciais SaaS v1

Status: implementado sem cobrança externa.

- `/plans/` e `/plans/signup/` aceitam `coupon_code` opcional.
- o cupom é validado por `SubscriptionCoupon`, platform-scope, dentro de `subscriptions`.
- `coupons.Coupon` continua exclusivo para carrinho/pedido tenant-scoped e não valida plano SaaS.
- `plan=null` em `SubscriptionCoupon` permite qualquer plano ativo; `plan` preenchido restringe o cupom àquele plano.
- desconto percentual é limitado a 100%; desconto fixo é limitado ao preço mensal do plano.
- `SubscriptionPlan.monthly_price` nunca é alterado; preço efetivo e desconto são snapshots no lead, onboarding e assinatura.
- cupom inválido bloqueia o formulário: em `/plans/` não cria lead; em `/plans/signup/` não cria tenant, owner ou assinatura.
- gestão fica em `/ops/platform/subscription-coupons/` com permissão `subscriptions.manage`.
- limites de uso, cupom por cliente/e-mail, invoice, cobrança recorrente real e integração Asaas ficam fora do v1.

## Signup self-service MVP

Status: implementado atrás de feature flag.

- `/plans/signup/` fica disponível somente com `HUBX_PUBLIC_SIGNUP_ENABLED=1`.
- o formulário cria tenant em modo manutenção, owner inicial e assinatura trial interna de acordo com `SubscriptionPlan.trial_days`.
- o template comunica 30 dias grátis e cartão obrigatório quando o plano exigir payment method.
- billing SaaS recorrente, invoice e cobrança de assinatura continuam fora do MVP.
- o onboarding prepara Asaas como provider inicial para recebimentos da loja e billing SaaS posterior.
- dados de cartão não devem ser enviados em campos livres de `/plans/` ou `/plans/signup/`.
- a loja recém-criada deve ser configurada pelo owner antes de desligar manutenção.
- e-mails já usados por owner/usuário seguem pelo fluxo assistido.

## Exemplo de planos
### Starter
- 30 dias grátis com cartão obrigatório para ativação comercial
- domínio padrão
- limite inicial de produtos
- recursos essenciais

### Pro
- 30 dias grátis com cartão obrigatório para ativação comercial
- maior limite de produtos
- domínio customizado
- analytics avançado

### Enterprise
- 30 dias grátis com cartão obrigatório para ativação comercial
- volume maior
- recursos premium
- suporte prioritário

## Observação
Os preços reais seguem definidos comercialmente em `SubscriptionPlan`. Este documento descreve a lógica do produto, não um contrato financeiro externo.
