# Customers Operational Runbook

## Objetivo
Padronizar triagem de qualidade de dados de clientes sem misturar tenants e sem depender de fallback visual como sinal de saúde.

## Escopo
- cadastro mínimo de `Customer`
- endereços persistidos de `CustomerAddress`
- vínculo explícito entre `Order` e `Customer`
- sinais operacionais exportados para Prometheus/Grafana

## Fora de escopo
- enriquecimento de CRM externo
- limpeza automática de clientes
- alteração automática de pedidos legados

## Comando principal

```bash
python manage.py list_customer_data_issues --tenant-id <tenant_id>
```

Filtros suportados:

```bash
python manage.py list_customer_data_issues --tenant-id <tenant_id> --issue missing_address
python manage.py list_customer_data_issues --tenant-id <tenant_id> --issue missing_default_address
python manage.py list_customer_data_issues --tenant-id <tenant_id> --issue incomplete_default_address
python manage.py list_customer_data_issues --tenant-id <tenant_id> --issue order_email_fallback
```

## Issues monitoradas
- `missing_name`: cliente sem nome operacional útil
- `missing_email`: cliente sem e-mail persistido
- `duplicate_email_case`: e-mails equivalentes por caixa dentro do mesmo tenant
- `missing_address`: cliente sem endereço persistido
- `missing_default_address`: cliente possui endereço, mas nenhum default
- `incomplete_default_address`: endereço default sem campos mínimos de entrega
- `order_email_fallback`: pedidos ainda dependem de `tenant + customer_email` em vez de `Order.customer`

## Métricas
Endpoint:

```text
/ops/customers/metrics/data-issues/
```

Variável obrigatória:

```text
CUSTOMERS_OBSERVABILITY_TOKEN
```

Métrica principal:

```text
hubx_customer_data_issue_total{tenant_id,issue}
```

## Ativação
1. configurar `CUSTOMERS_OBSERVABILITY_TOKEN`
2. validar o endpoint com `Authorization: Bearer`
3. publicar `infra/observability/prometheus/customers-scrape.example.yml`
4. carregar `infra/observability/prometheus/customers-alert-rules.yml`
5. importar `infra/observability/grafana/customers-data-issues-dashboard.json`
6. configurar `infra/observability/alertmanager/customers-routing.example.yml`

## Triagem
1. começar por `order_email_fallback`, porque afeta leitura histórica e customer area
2. revisar `missing_address` antes de ativar fluxos pós-compra mais ricos
3. corrigir `missing_default_address` e `incomplete_default_address` antes de depender de endereço default
4. tratar `duplicate_email_case` como candidato a backfill/normalização controlada

## Backfill seguro de vínculos
Quando o problema for `order_email_fallback`, use o backfill de `accounts` em modo tenant-scoped:

```bash
python manage.py backfill_customer_links --tenant-id <tenant_id> --only orders --dry-run
python manage.py backfill_customer_links --tenant-id <tenant_id> --only orders
```

O resumo final inclui:

```text
order_email_fallback_remaining=<count>
```

O resumo também separa motivos de skip:

```text
orders_skipped_missing_email=<count>
orders_skipped_no_match=<count>
orders_skipped_ambiguous=<count>
```

Se o valor continuar acima de zero, revise:
- clientes ausentes para aquele e-mail
- duplicidade case-insensitive dentro do tenant
- pedidos sem `customer_email`
- divergência entre tenant do pedido e tenant do customer

## Segurança multi-tenant
- sempre usar `--tenant-id`
- nunca inferir customer global por e-mail sem tenant
- não editar pedidos legados em lote sem plano de backfill explícito
