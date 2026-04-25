# Observability

Configurações de Prometheus, Grafana e exporters.

Índice operacional:
- `../../docs/operational-runbooks.md`

## Payments
- runbook operacional:
  - `../../docs/modules/payments-operational-runbook.md`
- regras iniciais de alerta para sinais críticos de pagamento:
  - `prometheus/payments-alert-rules.yml`
- exemplo de scrape interno do exporter de `payments`:
  - `prometheus/payments-scrape.example.yml`
- dashboard inicial de Grafana:
  - `grafana/payments-alert-signals-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/payments-routing.example.yml`
- métricas principais:
  - `hubx_payments_alert_signal_total`
  - `hubx_payments_alert_signal_last_timestamp_seconds`
  - `hubx_payments_attempt_total`

## Notifications
- runbook operacional:
  - `../../docs/modules/notifications-operational-runbook.md`
- regras iniciais de alerta para logs de e-mail:
  - `prometheus/notifications-alert-rules.yml`
- exemplo de scrape interno do exporter de `notifications`:
  - `prometheus/notifications-scrape.example.yml`
- métrica principal:
  - `hubx_notifications_email_log_total`
- dashboard inicial de Grafana:
  - `grafana/notifications-email-logs-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/notifications-routing.example.yml`

## Shipping
- runbook operacional:
  - `../../docs/modules/shipping-operational-runbook.md`
- regras iniciais de alerta para polling/rastreio:
  - `prometheus/shipping-alert-rules.yml`
- exemplo de scrape interno do exporter de `shipping`:
  - `prometheus/shipping-scrape.example.yml`
- métricas principais:
  - `hubx_shipping_shipment_total`
  - `hubx_shipping_history_event_total`
  - `hubx_shipping_provider_http_status_total`
  - `hubx_shipping_provider_latency_ms_avg`
- dashboard inicial de Grafana:
  - `grafana/shipping-polling-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/shipping-routing.example.yml`

## Inventory
- runbook operacional:
  - `../../docs/modules/inventory-operational-runbook.md`
- regras iniciais de alerta para exceções de estoque:
  - `prometheus/inventory-alert-rules.yml`
- exemplo de scrape interno do exporter de inventory:
  - `prometheus/inventory-scrape.example.yml`
- métricas principais:
  - `hubx_inventory_exception_total`
  - `hubx_inventory_exception_priority_total`
  - `hubx_inventory_exception_owner_total`
  - `hubx_inventory_exception_aging_total`
- dashboard inicial de Grafana:
  - `grafana/inventory-exceptions-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/inventory-routing.example.yml`

## Catalog
- runbook operacional:
  - `../../docs/modules/catalog-operational-runbook.md`
- regras iniciais de alerta para publicação de catálogo:
  - `prometheus/catalog-alert-rules.yml`
- exemplo de scrape interno do exporter de catalog:
  - `prometheus/catalog-scrape.example.yml`
- métrica principal:
  - `hubx_catalog_publication_issue_total`
- métrica de merchandising:
  - `hubx_catalog_card_decision_signal_total`
- dashboard inicial de Grafana:
  - `grafana/catalog-publication-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/catalog-routing.example.yml`

## Customers
- runbook operacional:
  - `../../docs/modules/customers-operational-runbook.md`
- regras iniciais de alerta para qualidade de dados de clientes:
  - `prometheus/customers-alert-rules.yml`
- exemplo de scrape interno do exporter de customers:
  - `prometheus/customers-scrape.example.yml`
- métrica principal:
  - `hubx_customer_data_issue_total`
- dashboard inicial de Grafana:
  - `grafana/customers-data-issues-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/customers-routing.example.yml`

## Checkout
- runbook operacional:
  - `../../docs/modules/checkout-operational-runbook.md`
- regras iniciais de alerta para sessões de checkout:
  - `prometheus/checkout-alert-rules.yml`
- exemplo de scrape interno do exporter de checkout:
  - `prometheus/checkout-scrape.example.yml`
- métrica principal:
  - `hubx_checkout_session_issue_total`
- métrica de lifecycle:
  - `hubx_checkout_session_status_total`
- métrica info de recovery:
  - `hubx_checkout_recovery_result_info`
- métrica de eventos de recovery:
  - `hubx_checkout_recovery_event_total`
- dashboard inicial de Grafana:
  - `grafana/checkout-session-issues-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/checkout-routing.example.yml`

## Runbook curto de ativação
1. configurar `PAYMENTS_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/payments-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/payments-alert-rules.yml`
4. configurar o roteamento inicial no Alertmanager usando `alertmanager/payments-routing.example.yml`
5. importar `grafana/payments-alert-signals-dashboard.json` no Grafana
6. validar:
   - scrape retornando `200`
   - métricas `hubx_payments_alert_signal_total`
   - métrica `hubx_payments_attempt_total`
   - alertas carregados sem erro
   - dashboard com dados

## Runbook curto de ativação — Notifications
1. configurar `NOTIFICATIONS_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/notifications-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/notifications-alert-rules.yml`
4. validar:
   - scrape retornando `200`
   - métrica `hubx_notifications_email_log_total`
   - labels `tenant_id` e `status`
   - alertas carregados sem erro
5. importar `grafana/notifications-email-logs-dashboard.json` no Grafana
6. configurar roteamento inicial no Alertmanager usando `alertmanager/notifications-routing.example.yml`

## Runbook curto de ativação — Shipping
1. configurar `SHIPPING_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/shipping-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/shipping-alert-rules.yml`
4. validar:
   - scrape retornando `200`
   - métrica `hubx_shipping_shipment_total`
   - métrica `hubx_shipping_history_event_total`
   - métrica `hubx_shipping_provider_http_status_total`
   - métrica `hubx_shipping_provider_latency_ms_avg`
   - labels `tenant_id`, `status` e `event_type`
   - alertas carregados sem erro
5. agendar `shipping.sync_pending_shipments_tracking` via Celery beat/cron
6. importar `grafana/shipping-polling-dashboard.json` no Grafana
7. configurar roteamento inicial no Alertmanager usando `alertmanager/shipping-routing.example.yml`

## Runbook curto de ativação — Inventory
1. configurar `INVENTORY_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/inventory-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/inventory-alert-rules.yml`
4. validar:
   - scrape retornando `200`
   - métrica `hubx_inventory_exception_total`
   - labels `tenant_id`, `state`, `priority`, `owner_state` e `aging`
   - alertas carregados sem erro
5. importar `grafana/inventory-exceptions-dashboard.json` no Grafana
6. configurar roteamento inicial no Alertmanager usando `alertmanager/inventory-routing.example.yml`

## Runbook curto de ativação — Catalog
1. configurar `CATALOG_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/catalog-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/catalog-alert-rules.yml`
4. validar:
   - scrape retornando `200`
   - métrica `hubx_catalog_publication_issue_total`
   - métrica `hubx_catalog_card_decision_signal_total`
   - labels `tenant_id`, `issue` e `status`
   - alertas carregados sem erro
5. importar `grafana/catalog-publication-dashboard.json` no Grafana
6. configurar roteamento inicial no Alertmanager usando `alertmanager/catalog-routing.example.yml`

## Runbook curto de ativação — Customers
1. configurar `CUSTOMERS_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/customers-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/customers-alert-rules.yml`
4. validar:
   - scrape retornando `200`
   - métrica `hubx_customer_data_issue_total`
   - labels `tenant_id` e `issue`
   - alertas carregados sem erro
5. importar `grafana/customers-data-issues-dashboard.json` no Grafana
6. configurar roteamento inicial no Alertmanager usando `alertmanager/customers-routing.example.yml`

## Runbook curto de ativação — Checkout
1. configurar `CHECKOUT_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/checkout-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/checkout-alert-rules.yml`
4. validar:
   - scrape retornando `200`
   - métrica `hubx_checkout_session_issue_total`
   - métrica `hubx_checkout_session_status_total`
   - métrica `hubx_checkout_recovery_result_info`
   - métrica `hubx_checkout_recovery_event_total`
   - labels `tenant_id`, `issue`, `status`, `family` e `recovery_action`
   - alertas carregados sem erro
5. importar `grafana/checkout-session-issues-dashboard.json` no Grafana
6. configurar roteamento inicial no Alertmanager usando `alertmanager/checkout-routing.example.yml`
7. opcionalmente agendar `expire_checkout_sessions --tenant-id <tenant_id> --older-than-hours 24` após validar `--dry-run`
8. opcionalmente rodar `prune_expired_checkout_sessions --tenant-id <tenant_id> --older-than-days 180 --dry-run` para estimar retenção expirada antiga
9. opcionalmente rodar `prune_checkout_recovery_events --tenant-id <tenant_id> --older-than-days 180 --dry-run` para estimar retenção de analytics de recovery
