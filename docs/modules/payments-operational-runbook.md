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

Uso recomendado:
- usar para suporte e conciliação operacional
- investigar pendências longas antes de orientar nova tentativa manual
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

## Diagnóstico rápido
- falha recorrente em `provider_intent.failed`:
  - revisar `PAGARME_SECRET_KEY`
  - validar `PAGARME_API_BASE_URL`
  - checar rollout por tenant
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

## Limites atuais
- não há pruning de `PaymentAttempt` nesta fase.
- não há pruning específico de sinais em memória nesta fase.
- não há runbook de conciliação financeira/backoffice.
- refund/estorno ainda ficam fora deste recorte operacional.
