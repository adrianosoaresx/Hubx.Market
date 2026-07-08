# Plans and Pricing

## Estrutura comercial atual

Status: implementado como contrato de plano e enforcement inicial.

O Hubx Market opera com 3 planos públicos:

### Essencial

- R$ 0/mês + 2% dos pedidos pagos.
- até 100 produtos publicados ou em rascunho.
- até 300 pedidos pagos por mês.
- não exige método de cobrança do lojista no signup.
- indicado para validar a operação com baixa barreira de entrada.

### Pro

- mínimo de R$ 259,90/mês ou 2% dos pedidos pagos, o que for maior.
- até 500 produtos publicados ou em rascunho.
- até 1.500 pedidos pagos por mês.
- inclui API, domínio/customização, relatórios e suporte superior.
- exige método de cobrança ativo para garantir o mínimo mensal.
- signup self-service bloqueia planos que exigem método de cobrança e direciona para onboarding assistido até a ativação segura do billing method.

### Enterprise

- sob consulta.
- limite de produtos, limite de pedidos, percentual, SLA e implantação são negociados.
- configuração manual até existir fluxo comercial próprio.

## Regra de cobrança

- `subscriptions` é a fonte dos termos comerciais do plano.
- `billing_model=take_rate_only` cobra apenas percentual dos pedidos pagos.
- `billing_model=minimum_commitment` cobra o maior valor entre take rate do mês e mínimo mensal.
- `billing_model=custom` representa negociação Enterprise.
- `platform_fee_percent` define o percentual Hubx.
- `minimum_monthly_fee` define o compromisso mínimo quando aplicável.
- `product_limit` e `monthly_paid_order_limit` são os principais critérios de escolha visíveis ao cliente.
- `requires_hubx_checkout` indica que a taxa depende do checkout Hubx para split ou conciliação.
- `requires_billing_method` indica necessidade de método de cobrança seguro para mensalidade mínima ou cobranças complementares.
- o billing method do Pro guarda referências externas restritas do provider, nunca número de cartão, CVV ou validade; referência tokenizada não deve ser enviada nem reexibida em formulário livre.

## Aquisição pública

- `/plans/` exibe planos ativos de `SubscriptionPlan`.
- a copy pública não deve falar em trial, MVP, cartão obrigatório ou termos técnicos internos.
- a página deve explicar o Essencial como "a Hubx só ganha quando a loja vende".
- a página deve explicar o Pro como "R$ 259,90/mês mínimo ou 2% das vendas, o que for maior".
- `/plans/signup/` pode criar tenant em modo manutenção, owner inicial e assinatura tenant-scoped quando o plano não exige método de cobrança.
- planos com `requires_billing_method=True` devem seguir onboarding assistido até o billing method ser confirmado por fluxo seguro do provider.
- dados de cartão nunca devem ser enviados em campos livres de `/plans/` ou `/plans/signup/`.

## Enforcement operacional

- catálogo conta produtos `active` e `draft`; produtos `inactive` não contam.
- criação ou reativação de produto deve bloquear quando o tenant estiver acima do limite do plano.
- edição e desativação continuam permitidas mesmo acima do limite.
- checkout conta pedidos pagos do mês por `payment_confirmed_at`.
- pedidos pendentes, cancelados e carrinhos não contam para limite mensal.
- quando o limite mensal de pedidos pagos estiver atingido, o início de novo pagamento deve ser bloqueado.
- se um webhook confirmar pagamento acima do limite por corrida operacional, o pedido permanece pago e o ledger marca `commercial_overage` para tratativa comercial.

## Taxa Hubx

- cada pedido pago deve gerar um ledger idempotente da taxa Hubx.
- o ledger guarda percentual, snapshot do plano, base de cálculo, valor estimado e status.
- Essencial usa o split de 2% como forma principal de recebimento.
- Pro usa o split para abater o mínimo mensal.
- no fechamento mensal do Pro, o sistema calcula o total capturado/registrado por take rate e cria ajuste complementar quando ficar abaixo de R$ 259,90.
- quando `PAYMENTS_PLATFORM_BILLING_ASAAS_ENABLED=1`, o fechamento pode criar cobrança complementar Asaas para o ajuste do Pro.
- a cobrança complementar usa cliente Asaas e página/cobrança hospedada; a Hubx armazena `provider_payment_reference`, `billing_checkout_url` e snapshots, não dados de cartão.
- se houver referência provider-owned segura obtida por fluxo confiável do provider, a cobrança pode usar essa referência sem reenviar dados sensíveis e sem persistir token em snapshots.
- `/ops/subscriptions/billing-method/` permite acompanhar o estado e garantir o cliente Asaas do tenant; ativação manual por owner tenant é bloqueada.
- `payment_sandbox_validate_platform_billing` valida o fluxo sandbox da cobrança complementar e pode simular webhook pago.
- `enforce_platform_fee_delinquency` aplica a política de inadimplência do Pro.
- após a tolerância configurada, complemento não pago move a assinatura para `past_due`; após o prazo de suspensão, move para `suspended`; quando não há complemento pendente, volta para `active`.
- se o take rate do mês superar R$ 259,90, não há cobrança adicional.
- refund, chargeback ou falha posterior devem marcar o ledger para reversão ou ajuste, sem duplicidade.

## Cupons comerciais SaaS

Status: mantido sem cobrança externa.

- `/plans/` e `/plans/signup/` aceitam `coupon_code` opcional.
- o cupom é validado por `SubscriptionCoupon`, platform-scope, dentro de `subscriptions`.
- `coupons.Coupon` continua exclusivo para carrinho/pedido tenant-scoped e não valida plano SaaS.
- `plan=null` em `SubscriptionCoupon` permite qualquer plano ativo; `plan` preenchido restringe o cupom àquele plano.
- desconto percentual é limitado a 100%; desconto fixo é limitado ao preço mensal do plano.
- `SubscriptionPlan.monthly_price` nunca é alterado; preço efetivo e desconto são snapshots no lead, onboarding e assinatura.
- cupom inválido bloqueia o formulário: em `/plans/` não cria lead; em `/plans/signup/` não cria tenant, owner ou assinatura.
- gestão fica em `/ops/platform/subscription-coupons/` com permissão `subscriptions.manage`.

## Observação

Os preços reais seguem definidos comercialmente em `SubscriptionPlan`. Este documento descreve a lógica do produto, não substitui contrato externo ou negociação Enterprise.
