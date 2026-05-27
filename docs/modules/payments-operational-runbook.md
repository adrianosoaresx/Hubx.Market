# Payments Operational Runbook

Este runbook consolida a operação inicial do módulo `payments`: rollout do provider, webhook, retorno hospedado, observabilidade e validação sandbox.

## Escopo
- validar configuração mínima de provider
- ativar rollout controlado
- validar webhook sandbox
- expor métricas Prometheus
- carregar alertas, dashboard e routing
- diagnosticar falhas críticas de pagamento

## Pré-requisitos
- tenant criado e resolvido por subdomínio
- pedidos de teste criáveis via checkout
- `PaymentAttempt` gerada para pedido
- segredo de provider configurado em ambiente seguro
- endpoint público de webhook cadastrável no provider
- Prometheus/Grafana/Alertmanager disponíveis

## Configuração principal
Variáveis esperadas:

```bash
PAYMENTS_PROVIDER_DEFAULT=pagarme
PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=sandbox
PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=lite
PAGARME_SECRET_KEY=<secret>
PAGARME_API_BASE_URL=<https-url>
PAGARME_WEBHOOK_SIGNATURE_HEADER=X-Hub-Signature
PAYMENTS_OBSERVABILITY_TOKEN=<secret>
```

Para rollout controlado:

```bash
PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=controlled
PAYMENTS_REAL_PROVIDER_ENABLED_TENANTS=<tenant-id-list>
PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block
```

Para live global, usar somente após piloto controlado:

```bash
PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=live
PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=true
PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block
```

## Readiness sandbox
Rodar:

```bash
python manage.py payment_sandbox_readiness --webhook-url=<public-webhook-url>
```

Resultado esperado:
- `payment_sandbox_readiness=ready`
- todos os bloqueadores críticos como `OK`

Se houver `BLOCKED`, não avançar para rollout real antes de corrigir configuração.

## Readiness produção
Antes de ativar provider real em produção:

```bash
python manage.py payment_sandbox_readiness --target=production --webhook-url=<public-webhook-url>
```

Resultado esperado:
- `payment_production_readiness=ready`
- `Provider fallback mode` como `OK`
- `Live global flag` como `OK`

Critérios:
- preferir `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=controlled` com allowlist inicial de tenants.
- manter `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block` em produção para evitar fallback lite silencioso.
- se `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=live`, exigir `PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=true`.
- para rollback rápido, alterar `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=off` ou remover o tenant da allowlist controlada.

## Validação de webhook
Simular pagamento aprovado:

```bash
python manage.py payment_sandbox_validate_webhook --tenant-slug=<tenant-slug> --order-number=<number> --event=paid
```

Simular falha:

```bash
python manage.py payment_sandbox_validate_webhook --tenant-slug=<tenant-slug> --order-number=<number> --event=failed
```

Validar na saída:
- `status_code`
- `result`
- `order_status`
- `order_payment_status`
- `attempt_status`
- `charge_id`

## Triagem de tentativas
Listar tentativas recentes:

```bash
python manage.py list_payment_attempts --limit=50
```

Listar tentativas pendentes por tenant:

```bash
python manage.py list_payment_attempts --tenant-id=<id> --status=pending
```

Listar tentativas pendentes antigas:

```bash
python manage.py list_payment_attempts --stale-hours=6
```

Listar divergências financeiras entre tentativa e pedido:

```bash
python manage.py list_payment_reconciliation_issues --tenant-id=<id>
```

Também é possível revisar a mesma auditoria em UI interna:

```text
/ops/payments/finance/
```

Refunds registrados no ledger devem ganhar surface dedicada em:

```text
/ops/payments/refunds/
```

Na primeira versão, essa surface é apenas leitura para triagem do ledger antes de qualquer aprovação mutável.

Ela permite revisar:
- status do ledger
- pedido
- valor
- tentativa e referência externa
- blockers
- chave idempotente

Listar candidatos para refund/reversal sem executar estorno:

```bash
python manage.py list_payment_refund_candidates --tenant-id=<id>
```

Registrar uma intenção idempotente de refund sem executar estorno:

```bash
python manage.py request_payment_refund_intent --tenant-id=<id> --order-number=<number> --idempotency-key=<key>
```

Validar um refund sandbox específico sem propagar efeitos:

```bash
python manage.py payment_sandbox_validate_refund --tenant-id=<id> --refund-key=<uuid> --dry-run
```

Para executar a validação via adapter após conferir o dry-run:

```bash
python manage.py payment_sandbox_validate_refund --tenant-id=<id> --refund-key=<uuid>
```

Fluxo sandbox ponta a ponta recomendado:
1. confirmar que o ambiente usa credenciais sandbox do provider e tenant controlado de teste
2. criar uma cobrança sandbox paga e registrar a referência externa da charge no ledger
3. listar candidatos antes de abrir intenção:

```bash
python manage.py list_payment_refund_candidates --tenant-id=<id> --ready-only
```

4. registrar intenção idempotente com chave única por tentativa operacional
5. aprovar internamente em `/ops/payments/refunds/`, usando a ação “Aprovar internamente”
6. confirmar que o ledger ficou em `status=processing` e preservou `external_reference`
7. executar `payment_sandbox_validate_refund` com `--dry-run`
8. executar `payment_sandbox_validate_refund` sem `--dry-run` somente se o dry-run retornar `result=ready`
9. revisar `provider_refund_reference`, `metadata.provider_refund` e resposta externa do provider
10. manter o refund em triagem operacional se o adapter retornar `accepted`, pois isso ainda não confirma liquidação final

Critérios de No-Go para executar sandbox:
- tenant ausente ou diferente do tenant controlado de teste
- credenciais apontando para produção
- refund fora de `status=processing`
- `external_reference` ausente ou não associado a uma charge sandbox paga
- `idempotency_key` ausente, reaproveitada sem intenção explícita ou não rastreável
- refund de boleto que dependa de dados bancários ainda não modelados
- resposta do provider sem referência auditável ou sem payload suficiente para conciliação

Critérios de Go para avançar depois do sandbox:
- dry-run e execução usam o mesmo `tenant-id` e `refund-key`
- ledger preserva trilha auditável antes/depois da chamada
- resposta do provider fica em `metadata.provider_refund`
- nenhum efeito é propagado para order, estoque, cupom ou notification
- `payment.refunded` continua bloqueado até confirmação externa de refund concluído
- conciliação financeira consegue inspecionar o caso após a execução

Gate de produção para refund provider:
- produção permanece bloqueada até existir evidência de pelo menos um refund sandbox controlado executado pelo runbook completo
- evidência mínima exigida:
  - `tenant-id` sandbox usado no dry-run e na execução
  - `refund-key`
  - `idempotency_key`
  - `external_reference` da charge sandbox
  - saída do dry-run com `result=ready`
  - saída da execução com status do ledger e referência do provider
  - payload preservado em `metadata.provider_refund`
  - revisão de conciliação em `/ops/payments/finance/` ou comando equivalente
- Go limitado para produção só pode habilitar:
  - execução manual e explícita por refund já aprovado internamente
  - refunds de charge com referência externa conhecida
  - métodos que não exijam dados bancários adicionais ainda não modelados
  - observação pós-execução antes de qualquer propagação cross-module
- No-Go de produção:
  - execução em lote
  - botão admin que chame provider diretamente sem confirmação operacional separada
  - refund sem `external_reference`
  - boleto ou método que exija `bank_account`
  - emissão automática de `payment.refunded`
  - ajuste automático de pedido, estoque, cupom, notification ou tentativa financeira
  - ausência de trilha de conciliação financeira depois da execução
- rollback operacional:
  - se o provider aceitar a solicitação mas o ledger ficar inconsistente, congelar novas execuções
  - registrar divergência em conciliação financeira
  - não tentar “desfazer” refund via código sem procedimento financeiro externo
  - manter o ledger como fonte de auditoria e abrir correção manual documentada

Captura de evidência sandbox:
- a evidência deve ser anexada ao próprio `PaymentRefund.metadata`, em envelope separado de `provider_refund`
- envelope recomendado:
  - `sandbox_evidence.captured_at`
  - `sandbox_evidence.captured_by`
  - `sandbox_evidence.environment`
  - `sandbox_evidence.tenant_id`
  - `sandbox_evidence.refund_key`
  - `sandbox_evidence.dry_run_output`
  - `sandbox_evidence.execution_output`
  - `sandbox_evidence.provider_dashboard_reference`
  - `sandbox_evidence.reconciliation_reference`
  - `sandbox_evidence.decision`
  - `sandbox_evidence.notes`
- regras de captura:
  - não gravar secret keys, tokens, Authorization headers, dados de cartão ou dados bancários sensíveis
  - não substituir `provider_refund`; evidência operacional complementa a resposta técnica do adapter
  - capturar apenas evidências do tenant/refund explicitamente informado
  - manter o status do ledger inalterado ao anexar evidência
  - exigir operador/admin identificado quando a captura virar command ou action
- decisão de gate:
  - `decision=go-production-limited` só pode existir depois de sandbox executado, provider revisado e conciliação conferida
  - `decision=no-go` deve indicar blocker operacional objetivo
  - ausência de `sandbox_evidence` mantém o refund fora de qualquer gate de produção

Command para anexar evidência:
- usar o command separado de validação `capture_payment_refund_sandbox_evidence`
- argumentos obrigatórios:
  - `--tenant-id`
  - `--refund-key`
  - `--captured-by`
  - `--decision`
- argumentos opcionais:
  - `--environment`
  - `--dry-run-output`
  - `--execution-output`
  - `--provider-dashboard-reference`
  - `--reconciliation-reference`
  - `--notes`
- decisões aceitas:
  - `no-go`
  - `sandbox-observed`
  - `go-production-limited`
- comportamento:
  - carregar `PaymentRefund` por `tenant_id + refund_key`
  - anexar/atualizar apenas `metadata.sandbox_evidence`
  - preservar `metadata.provider_refund`
  - preservar `status`, `provider_refund_reference`, `completed_at` e `failed_at`
  - imprimir resumo sem secrets
- bloqueios:
  - refund inexistente ou cross-tenant
  - `captured_by` ausente
  - `decision` fora da lista permitida
  - texto contendo sinais óbvios de segredo, token, Authorization header, cartão ou dados bancários sensíveis
  - `go-production-limited` sem `provider_refund`, `provider_dashboard_reference` e `reconciliation_reference`
- fora do escopo:
  - chamar provider
  - executar refund
  - aprovar refund
  - emitir `payment.refunded`
  - alterar pedido, estoque, cupom, notification ou tentativa financeira

Exemplo de captura de evidência observada:

```bash
python manage.py capture_payment_refund_sandbox_evidence \
  --tenant-id=<id> \
  --refund-key=<uuid> \
  --captured-by="Ops Finance" \
  --decision=sandbox-observed \
  --dry-run-output="payment_sandbox_refund_validation=dry-run result=ready" \
  --execution-output="result=refund-execution-accepted status=processing" \
  --provider-dashboard-reference="pagarme:<refund-reference>" \
  --reconciliation-reference="ops-finance:<case>"
```

Exemplo de gate limitado futuro:

```bash
python manage.py capture_payment_refund_sandbox_evidence \
  --tenant-id=<id> \
  --refund-key=<uuid> \
  --captured-by="Ops Finance" \
  --decision=go-production-limited \
  --provider-dashboard-reference="pagarme:<refund-reference>" \
  --reconciliation-reference="ops-finance:<case>"
```

Enablement de produção para refund provider:
- status atual:
  - **No-Go para produção ampla**
  - **No-Go para automação**
  - **Go apenas para preparar produção manual limitada quando houver evidência sandbox real**
- pré-requisitos antes de qualquer enablement:
  - command de captura executado com `decision=go-production-limited`
  - `metadata.sandbox_evidence` presente no `PaymentRefund`
  - `metadata.provider_refund` presente e revisado
  - referência de dashboard do provider registrada
  - referência de conciliação financeira registrada
  - confirmação de que o método de pagamento não exige dados bancários adicionais
  - operador financeiro identificado
- escopo máximo de uma primeira habilitação:
  - um tenant controlado por vez
  - um refund por execução
  - execução manual por `refund_key`
  - somente refunds já aprovados internamente e em `processing`
  - observação pós-execução antes de qualquer nova rodada
- produção continua bloqueada para:
  - self-service do lojista
  - customer-facing refunds
  - execução em lote
  - retries automáticos
  - boleto ou método que exija `bank_account`
  - emissão automática de `payment.refunded`
  - efeitos automáticos em pedido, estoque, cupom, notification ou tentativa financeira
- recomendação operacional:
  - não criar feature flag de produção ampla ainda
  - se houver necessidade real de operação, criar primeiro uma flag restrita para execução manual limitada e reversível
  - manter rollback como congelamento de novas execuções, não como tentativa automática de desfazer refund

Status final da trilha refund/reversal:
- pronto para uso interno/controlado:
  - auditoria de candidatos
  - ledger `PaymentRefund`
  - surface admin read-only
  - aprovação interna
  - adapter/command de execução contra provider em modo controlado
  - validação sandbox por refund específico
  - captura de evidência sandbox
  - gate documental de produção
- ainda bloqueado para produção real:
  - execução financeira sem evidência sandbox externa
  - automação de retry/refund
  - self-service de lojista ou cliente
  - boleto/dados bancários adicionais
  - evento `payment.refunded`
  - propagação automática para pedido, estoque, cupom e notifications
- conclusão operacional:
  - a trilha deve ser considerada encerrada como fundação técnica
  - a trilha não deve ser considerada lançada como produto financeiro de produção
  - próximos passos só devem reabrir refund se houver evidência sandbox real ou demanda operacional concreta de produção manual limitada

Status final de operações financeiras de payments:
- pronto para operação controlada:
  - readiness sandbox/produção controlada do provider
  - hosted redirect/return com retorno tratado como hint
  - webhooks como fonte de verdade financeira
  - `PaymentAttempt` tenant-scoped com timeline e referência externa
  - auditoria read-only de divergências financeiras
  - surface `/ops/payments/finance/`
  - métricas e alertas de tentativas pendentes/stale
  - fundação de refund/reversal sem produção real
- ainda não é backoffice financeiro completo:
  - não há settlement/extrato do provider
  - não há ledger financeiro geral para liquidação
  - não há correção automática de divergência
  - não há expiração/reconciliação automática de tentativas pendentes
  - não há política formal de retenção/pruning financeiro
  - não há refund financeiro production-ready
- conclusão operacional:
  - payments está maduro para checkout/pagamento controlado, suporte e observabilidade
  - payments não deve continuar recebendo micro-waves financeiras sem evidência externa ou demanda operacional concreta
  - o próximo ciclo de maior ROI provavelmente está fora de payments, salvo ativação real de provider/sandbox

Uso recomendado:
- usar para suporte e conciliação operacional
- investigar pendências longas antes de orientar nova tentativa manual
- investigar divergências antes de qualquer ajuste manual de pedido/tentativa
- usar candidatos de refund apenas como pré-check; o comando não executa estorno nem altera pedido
- registrar intenção de refund no ledger antes de qualquer integração futura com provider
- tratar `status=blocked` como evidência operacional, não como estorno executado
- tratar `status=requested` como candidato à triagem/admin, não como aprovação automática
- aprovação futura deve apenas preparar execução e manter `provider_call=not-executed` até existir adapter real de refund
- aprovação interna passa a representar somente `requested → processing`; ainda não significa refund executado
- a action admin usa POST tenant-scoped e deixa claro que “aprovar internamente” não executa estorno
- provider adapter de refund ainda deve ser tratado como integração sandbox-first até a estratégia de confirmação estar validada
- o adapter lite segue retornando `accepted`, e o adapter Pagar.me já chama o endpoint real de cancelamento/estorno de cobrança em modo conservador
- execução futura do refund deve começar registrando resposta do adapter no ledger; `accepted` ainda não significa refund concluído
- execution command skeleton já registra `accepted`, `succeeded` ou `failed` no ledger, mas não propaga efeitos para outros módulos
- endpoint oficial Pagar.me V5 para cancelamento/estorno de cobrança é `DELETE /core/v5/charges/{charge_id}`; validar em sandbox antes de produção
- boleto pode exigir dados bancários do comprador, ainda não suportados pelo ledger atual
- adapter Pagar.me já possui implementação conservadora mockada/testada para `DELETE /charges/{charge_id}`, mas produção continua bloqueada sem validação sandbox real
- validação sandbox de refund deve exigir `tenant-id`, `refund-key` e status `processing`
- usar `--dry-run` antes da primeira execução real com credenciais sandbox
- não chamar provider real para refund sem aprovação/admin explícito e transição auditável do ledger
- considerar `payment.refunded` válido somente após confirmação externa de refund concluído
- não remover tentativas financeiras sem política específica de retenção/legal/financeiro

## Observabilidade
Endpoint:

```text
/payments/metrics/alert-signals/
```

Autenticação:
- header `Authorization: Bearer <PAYMENTS_OBSERVABILITY_TOKEN>`
- ou `X-Hubx-Observability-Token`

Métricas principais:
- `hubx_payments_alert_signal_total`
- `hubx_payments_alert_signal_last_timestamp_seconds`
- `hubx_payments_attempt_total`
- `hubx_payments_pending_attempt_oldest_age_seconds`

Artefatos:
- `infra/observability/prometheus/payments-scrape.example.yml`
- `infra/observability/prometheus/payments-alert-rules.yml`
- `infra/observability/grafana/payments-alert-signals-dashboard.json`
- `infra/observability/alertmanager/payments-routing.example.yml`

## Alertas iniciais
- `HubxPaymentsProviderIntentFailuresHigh`
- `HubxPaymentsHostedRedirectUnavailable`
- `HubxPaymentsWebhookInvalidSignature`
- `HubxPaymentsWebhookTenantUnavailable`
- `HubxPaymentsStockConflictOnConfirmation`
- `HubxPaymentsPendingAttemptsHigh`
- `HubxPaymentsStalePendingAttempt`

## Diagnóstico rápido
- falha recorrente em `provider_intent.failed`:
  - revisar `PAGARME_SECRET_KEY`
  - validar `PAGARME_API_BASE_URL`
  - checar rollout por tenant
  - se estiver em piloto, remover tenant da allowlist ou mudar rollout para `off`
- redirect hospedado indisponível:
  - revisar criação de `PaymentAttempt`
  - validar hosted URL retornada pelo provider
  - confirmar fallback mode
- assinatura inválida de webhook:
  - revisar segredo cadastrado no provider
  - validar header configurado em `PAGARME_WEBHOOK_SIGNATURE_HEADER`
  - checar origem do tráfego
- webhook sem tenant:
  - revisar metadata enviada ao provider
  - confirmar `tenant_slug` e `order_number`
- conflito de estoque na confirmação:
  - investigar orders/catalog/inventory antes de tentar reconciliação manual
- tentativa pendente antiga:
  - identificar tenant no label `tenant_id`
  - rodar `python manage.py list_payment_attempts --tenant-id=<id> --status=pending --stale-hours=6`
  - revisar se houve retorno hospedado sem webhook, webhook bloqueado ou abandono de pagamento
  - orientar nova tentativa somente depois de confirmar que não há confirmação externa pendente
- divergência financeira:
  - rodar `python manage.py list_payment_reconciliation_issues --tenant-id=<id>`
  - investigar `attempt_paid_order_unconfirmed`, `order_confirmed_attempt_not_paid`, `attempt_amount_mismatch`, `paid_attempt_missing_external_reference` e `payment_reference_mismatch`
  - não alterar pedido pago manualmente antes de conferir provider, webhook e histórico do pedido

## Limites atuais
- não há pruning de `PaymentAttempt` nesta fase.
- não há pruning específico de sinais em memória nesta fase.
- não há runbook de conciliação financeira/backoffice.
- refund/estorno ainda ficam fora deste recorte operacional.
