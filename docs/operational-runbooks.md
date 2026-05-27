# Operational Runbooks — Hubx Market

Este índice reúne os runbooks operacionais críticos para ativação, monitoramento e suporte do Hubx Market.

## Objetivo
- reduzir conhecimento operacional disperso
- facilitar resposta a incidentes
- padronizar ativação por ambiente
- orientar suporte sem quebrar fronteiras de módulo

## Runbooks críticos

### Shipping
- Arquivo: `docs/modules/shipping-operational-runbook.md`
- Cobre:
  - provider de tracking
  - polling
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
  - pruning de histórico
- Comandos principais:
  - `sync_shipments_tracking`
  - `prune_shipment_history`

### Payments
- Arquivo: `docs/modules/payments-operational-runbook.md`
- Cobre:
  - rollout de provider
  - readiness sandbox
  - validação de webhook
  - triagem de `PaymentAttempt`
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
- Comandos principais:
  - `payment_sandbox_readiness`
  - `payment_sandbox_validate_webhook`
  - `list_payment_attempts`

### Notifications
- Arquivo: `docs/modules/notifications-operational-runbook.md`
- Cobre:
  - readiness por tenant
  - readiness de provider
  - triagem de `EmailLog`
  - processamento de lote
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
- Comandos principais:
  - `notification_readiness`
  - `notification_provider_readiness`
  - `list_email_logs`
  - `process_email_logs`

### Inventory/Stock
- Arquivo: `docs/modules/inventory-operational-runbook.md`
- Cobre:
  - fronteira atual entre catalog/orders
  - triagem de exceções de estoque
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
- Comandos principais:
  - `list_inventory_exceptions`

### Catalog
- Arquivo: `docs/modules/catalog-operational-runbook.md`
- Cobre:
  - status de publicação
  - variantes
  - preço
  - estoque de variante
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
- Comandos principais:
  - `list_catalog_publication_issues`

### Customers
- Arquivo: `docs/modules/customers-operational-runbook.md`
- Cobre:
  - dados mínimos de cliente
  - endereços persistidos
  - endereço default
  - vínculo explícito `Order.customer`
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
- Comandos principais:
  - `list_customer_data_issues`

### Checkout
- Arquivo: `docs/modules/checkout-operational-runbook.md`
- Cobre:
  - sessões abertas incompletas
  - sessões abertas antigas/expiradas
  - sessões concluídas sem pedido correspondente
  - inconsistência entre itens e totais
  - métricas Prometheus
  - alertas
  - dashboard
  - routing Alertmanager
- Comandos principais:
  - `list_checkout_session_issues`
  - `expire_checkout_sessions`
  - `prune_expired_checkout_sessions`

## Ordem sugerida de ativação
1. `payments`
   - validar provider e webhook antes de aceitar pagamento real
2. `notifications`
   - manter dry-run até provider de e-mail estar pronto
3. `inventory/stock`
   - monitorar exceções de estoque ligadas a pedidos pagos/pendentes
4. `catalog`
   - validar publicação, variante default, preço e estoque antes de campanhas
5. `customers`
   - validar dados mínimos, endereços e vínculos explícitos antes de ampliar pós-compra/customer area
6. `checkout`
   - validar sessões abertas, totais e vínculo com pedido antes de tráfego real amplo
7. `shipping`
   - ativar provider/polling após fluxo de pedido/pagamento estar confiável

## Observabilidade
Artefatos versionados ficam em:

```text
infra/observability/
```

Domínios cobertos:
- payments
- notifications
- shipping
- inventory
- catalog
- customers
- checkout

## Regras de segurança operacional
- sempre operar com `tenant_id` quando o comando oferecer esse filtro
- não remover registros financeiros sem política explícita
- não remover logs de comunicação sem política de retenção
- validar tokens de observability por ambiente
- carregar alert rules antes de depender de dashboard manual

## Próximas lacunas conhecidas
- runbook de conciliação financeira/backoffice
- runbook de incidentes de estoque
- política formal de retenção por domínio
- métricas de latência e provider error mais ricas para notifications

## Closure sistêmica de produção

Comando:

```bash
python manage.py system_production_closure --review=go-nogo --readiness-matrix-ready --runbooks-ready --smoke-checklist-ready --observability-ready --rollback-drill-ready --residual-risks-accepted --decision-owner-confirmed --docs-updated --decision-recorded
```

Ordem mínima:

1. `--review=matrix`
2. `--review=runbooks`
3. `--review=smoke`
4. `--review=observability`
5. `--review=rollback`
6. `--review=go-nogo`

Regras:

- não imprimir token, API key, segredo, payload provider sensível ou e-mail de customer em claro.
- `GO` exige aceite explícito de riscos residuais.
- `NO-GO` abre bateria corretiva mínima pelo maior blocker.
- rollback deve existir antes de ativar provider ou gate produtivo.
