# Inventory/Stock Operational Runbook

Este runbook consolida a operação inicial de estoque no Hubx Market.

## Escopo
- entender onde o estoque vive hoje
- listar exceções operacionais por tenant
- expor métricas Prometheus
- carregar alertas, dashboard e routing
- diagnosticar conflitos de estoque ligados a pedidos

## Fronteira atual
- estoque pertence a `catalog.ProductVariant`
- exceções operacionais de estoque aparecem no fluxo de `orders`
- `Product` não é unidade de venda
- `OrderItem` preserva snapshot comercial e `variant_sku`

## Triagem CLI
Listar exceções ativas:

```bash
python manage.py list_inventory_exceptions --tenant-id=<id> --quick-filter=active
```

Listar alta prioridade:

```bash
python manage.py list_inventory_exceptions --tenant-id=<id> --quick-filter=high_priority
```

Listar sem responsável:

```bash
python manage.py list_inventory_exceptions --tenant-id=<id> --quick-filter=unassigned
```

Listar com responsável:

```bash
python manage.py list_inventory_exceptions --tenant-id=<id> --quick-filter=assigned
```

## Observabilidade
Endpoint:

```text
/ops/orders/metrics/inventory-exceptions/
```

Autenticação:
- header `Authorization: Bearer <INVENTORY_OBSERVABILITY_TOKEN>`
- ou `X-Hubx-Observability-Token`

Fallback aceito:
- `ORDERS_OBSERVABILITY_TOKEN`

Métricas principais:
- `hubx_inventory_exception_total`
- `hubx_inventory_exception_priority_total`
- `hubx_inventory_exception_owner_total`
- `hubx_inventory_exception_aging_total`

Artefatos:
- `infra/observability/prometheus/inventory-scrape.example.yml`
- `infra/observability/prometheus/inventory-alert-rules.yml`
- `infra/observability/grafana/inventory-exceptions-dashboard.json`
- `infra/observability/alertmanager/inventory-routing.example.yml`

## Alertas iniciais
- `HubxInventoryActiveExceptionsPresent`
- `HubxInventoryHighPriorityExceptionsPresent`
- `HubxInventoryUnassignedExceptionsPresent`

## Diagnóstico rápido
- exceção ativa:
  - revisar `variant_sku` do `OrderItem`
  - validar se a variante existe no tenant correto
  - validar `stock`, `reserved_stock`, `track_inventory` e `allow_backorder`
- alta prioridade:
  - checar saldo livre da variante
  - verificar produto inativo/indisponível
  - decidir se pedido entra em revisão manual
- sem responsável:
  - assumir ou reatribuir pela fila de Admin Orders
  - usar quick filter `unassigned`
- exceção resolvida:
  - garantir que vínculo/saldo foi normalizado antes de marcar resolução

## Limites atuais
- não há módulo `inventory` separado.
- não há ledger/auditoria dedicada de movimento de estoque.
- métricas são derivadas da fila de pedidos, não de uma tabela própria de eventos de estoque.
- não há política de SLA para aging além dos hints já exibidos na fila.
