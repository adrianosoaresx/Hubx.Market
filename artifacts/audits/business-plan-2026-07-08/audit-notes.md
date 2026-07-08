# Auditoria Do Modelo Comercial Hubx Market

Data: 2026-07-08

## Escopo

Auditoria da implementacao do modelo comercial:

- Essencial: R$ 0/mes + 2% dos pedidos pagos, ate 100 produtos e 300 pedidos pagos/mes.
- Pro: minimo R$ 259,90/mes ou 2% dos pedidos pagos, ate 500 produtos e 1.500 pedidos pagos/mes, com billing method seguro.
- Enterprise: sob consulta.

## Evidencias Capturadas

1. `01-public-plans-desktop.png`
   - Saude geral: boa clareza de preco, limites e take rate.
   - Risco: CTA "Criar loja self-service" aparece tambem em Pro e Enterprise, embora esses planos sigam onboarding assistido.
   - Acessibilidade/UX: rotulos repetidos podem induzir fluxo errado; precisa diferenciar CTA self-service de CTA assistido.

2. `02-signup-pro-assisted-desktop.png`
   - Saude geral: bloqueio assistido de Pro funciona e a tela nao coleta cartao/token.
   - Risco: o usuario chegou aqui por um CTA que prometia self-service; a tela corrige depois, mas tarde demais.
   - Acessibilidade/UX: alerta visivel e compreensivel; validacao completa ainda exige teste de teclado/foco.

3. `03-admin-billing-method-desktop.png`
   - Saude geral: tela nao exibe campos livres de token/customer reference e comunica fluxo seguro do provider.
   - Risco: estado ainda depende de fluxo futuro/trusted para ativacao real.
   - Acessibilidade/UX: conteudo e estado principal estao claros; nao foi validada navegacao completa por teclado.

## Achados Tecnicos

### P1 - Assinatura suspensa pode perder os termos comerciais e afrouxar limites

Evidencia:

- `backend/app/modules/subscriptions/application/commercial_terms.py:79-83` retorna termos apenas para `trialing`, `active` e `past_due`.
- `backend/app/modules/catalog/application/admin_product_commands.py:414-421` bloqueia limite de produtos apenas se `terms.has_product_limit`.
- `backend/app/modules/checkout/application/checkout_completion_commands.py:257-260` bloqueia limite mensal apenas se `terms.has_monthly_paid_order_limit`.

Risco:

Quando Pro vira `suspended`, `get_tenant_commercial_terms()` retorna termos vazios. Em vez de ficar mais restrito, o tenant pode deixar de aplicar limite de produtos, limite de pedidos e split/taxa Hubx em fluxos que dependem desses termos.

Recomendacao:

Separar "termos comerciais do plano" de "elegibilidade operacional". Mesmo suspensa, a assinatura deve preservar termos para calculo/auditoria, e os fluxos devem bloquear por status quando necessario.

### P1 - Fechamento mensal do Pro usa `created_at` do ledger, nao o periodo comercial do pedido

Evidencia:

- `backend/app/modules/payments/application/platform_fee_ledger_commands.py:90-97` soma take rate por `PlatformFeeLedger.created_at`.
- `record_paid_order_fee()` grava `billing_period_start/end` a partir de `payment_confirmed_at`.
- `close_minimum_commitment_period()` usa esse total para calcular diferenca do minimo.

Risco:

Webhook atrasado pode criar ledger no mes seguinte para um pedido pago no mes anterior. O fechamento do mes anterior cobra complemento maior que deveria, e o mes seguinte pode receber receita que nao pertence ao periodo.

Recomendacao:

Somar por `billing_period_start/billing_period_end` ou por `order.payment_confirmed_at`, nao por `created_at`. Adicionar teste de webhook atrasado cruzando virada de mes.

### P2 - CTA publico promete self-service para planos assistidos

Evidencia:

- `ui/templates/pages/templates/public_plans_page.html:62-64` renderiza "Criar loja self-service" para todos os planos quando `public_signup_enabled`.
- `browser-evidence.json` registrou `createSelfServiceOccurrences=3`.

Risco:

Pro e Enterprise aparecem como se pudessem criar loja diretamente. A tela seguinte corrige com alerta de onboarding assistido, mas a expectativa do usuario ja foi quebrada.

Recomendacao:

Renderizar o CTA self-service apenas para planos elegiveis. Para Pro/Enterprise, usar CTA "Solicitar onboarding" ou manter apenas "Iniciar Pro/Enterprise".

### P2 - Sucesso de aquisicao assistida ainda pode exibir codigo interno do plano

Evidencia:

- `ui/templates/pages/templates/public_plans_page.html:139` usa `lead.plan_code`.
- Seed atual usa `code="starter"` para o plano exibido como Essencial.

Risco:

Depois do envio de uma intencao para Essencial, o cliente pode ver "starter" em vez de "Essencial", contrariando a decisao de remover nomenclatura interna da experiencia.

Recomendacao:

Usar `lead.plan_name` ou snapshot de nome em todas as mensagens tenant/customer-facing.

### P3 - Documentacao ainda tem trechos supersedidos sem contexto suficiente

Evidencia:

- `docs/context-map.md:79` fala em contrato publico com trial/payment method.
- `docs/module-boundaries.md:678` ainda fala em assinatura trial no self-service.
- `docs/modules-index.md:153` fala que billing method ativa referencias tokenizadas por tenant.

Risco:

Proximos agentes podem reintroduzir comportamento antigo ou interpretar a tela de billing method como ponto de ativacao manual.

Recomendacao:

Atualizar esses trechos para o modelo pay-as-you-sell e para o hardening de billing method.

## Checks Executados

- `python backend/manage.py check`: OK.
- `python backend/manage.py makemigrations --check --dry-run`: OK, sem alteracoes pendentes.
- `git diff --check`: OK, apenas avisos LF/CRLF do Git no Windows.
- Suite focada: 125 testes OK.

## Limites Da Auditoria

- Nao foi feita chamada real ao Asaas.
- Nao foi validada conformidade WCAG completa; screenshots so indicam riscos visiveis.
- Nao foi executada suite completa de todos os modulos do repositorio, apenas a bateria focada em planos, catalogo, checkout e pagamentos.
