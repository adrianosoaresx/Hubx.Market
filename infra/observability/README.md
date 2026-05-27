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
  - inclui sinais críticos, tentativas por status e idade da tentativa pendente mais antiga por tenant
- exemplo de roteamento no Alertmanager:
  - `alertmanager/payments-routing.example.yml`
- métricas principais:
  - `hubx_payments_alert_signal_total`
  - `hubx_payments_alert_signal_last_timestamp_seconds`
  - `hubx_payments_attempt_total`
  - `hubx_payments_pending_attempt_oldest_age_seconds`

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
# Hubx Observability

## Accounts owner access

- Scrape example: `infra/observability/prometheus/accounts-scrape.example.yml`
- Alert rules: `infra/observability/prometheus/accounts-alert-rules.yml`
- MFA provider dashboard: `infra/observability/grafana/accounts-owner-mfa-provider-health-dashboard.json`
- Endpoint: `/accounts/metrics/owner-access/`
- MFA provider endpoint: `/accounts/metrics/owner-mfa-provider-health/`

## API Keys public endpoints

- Endpoint: `/api-keys/metrics/public-endpoints/`
- Token env: `API_KEYS_OBSERVABILITY_TOKEN`
- Metrics:
  - `hubx_api_key_public_request_total`
  - `hubx_api_key_auth_failure_total`
  - `hubx_api_key_rate_limited_total`
  - `hubx_api_key_public_endpoint_enabled`
- Dashboard review:
  - título recomendado: `Hubx API Key Public Endpoints`
  - slug recomendado: `api-key-public-endpoints`
  - datasource: `DS_PROMETHEUS`
  - painéis mínimos: requests, auth failures, rate limit, endpoint enabled e top tenants
  - sem segredo, hash, header ou valor claro de API key
- Dashboard:
  - `infra/observability/grafana/api-key-public-endpoints-dashboard.json`
  - importar depois de validar scrape de `/api-keys/metrics/public-endpoints/`
  - selecionar datasource Prometheus em `DS_PROMETHEUS`
- Alert rules review:
  - `HubxApiKeyPublicAuthFailuresHigh`
  - `HubxApiKeyPublicRateLimitedHigh`
  - `HubxApiKeyPublicEndpointDisabled`
  - primeira severidade recomendada: `warning`
- Alert rules:
  - `infra/observability/prometheus/api-keys-alert-rules.yml`
  - carregar no Prometheus somente depois de validar scrape e dashboard
  - Alertmanager real permanece configuração de ambiente
- Closure:
  - `python manage.py api_key_public_endpoint_observability_closure --rollout-ready`
  - confirma artefatos versionados antes de rollout ampliado
  - não ativa Prometheus, Grafana ou Alertmanager automaticamente
- Production rollout review:
  - `python manage.py api_key_public_endpoint_production_rollout_review --observability-closure-ready --production-token-configured --prometheus-scrape-planned --dashboard-import-planned --alert-rules-load-planned --smoke-metrics-planned --rollback-plan-available --evidence-capture-required --owner-approval-required --no-secret-exposure-required`
  - revisar token, scrape, dashboard, alertas, smoke, evidência e rollback antes de ativar ambiente real
  - não registrar token, header, hash ou API key em claro
- Production activation evidence:
  - `python manage.py api_key_public_endpoint_production_activation_evidence --environment=production --evidence-reference=<ref-sanitizada> --rollout-review-ready --token-redacted --metrics-endpoint-reachable --metrics-payload-valid --prometheus-scrape-active --dashboard-imported --alert-rules-loaded --endpoint-enabled-metric-present --request-metric-present --auth-failure-metric-present --rate-limit-metric-present --rollback-rehearsed`
  - registrar somente sinais sanitizados da ativação
  - não executar chamada real nem armazenar token/header/API key
- Post-activation monitoring review:
  - `python manage.py api_key_public_endpoint_post_activation_monitoring_review --activation-evidence-ready --monitoring-window-observed --dashboard-reviewed --auth-failure-rate-acceptable --rate-limit-rate-acceptable --endpoint-enabled-stable --alert-noise-acceptable --threshold-tuning-needed-logged --rollback-not-required --expansion-decision-deferred --no-sensitive-data-observed`
  - revisar estabilidade antes de expandir endpoints públicos
  - não alterar thresholds, token, scrape ou endpoints nesta review
- Expansion review:
  - `python manage.py api_key_public_endpoint_expansion_review --post-activation-monitoring-ready --candidate-endpoint-identified --read-only-required --tenant-context-required --explicit-scope-required --rate-limit-required --observability-required --payload-contract-required --no-pii-required --no-cross-module-leak-required --rollout-flag-required --expansion-deferred-until-contract`
  - candidato recomendado: `GET /api/v1/catalog/products/<slug>/`
  - execução do endpoint fica para contrato próprio no módulo `catalog`
- Product detail contract review:
  - `python manage.py api_key_public_product_detail_endpoint_contract_review --expansion-review-ready --catalog-owner-confirmed --slug-lookup-required --tenant-scope-required --active-product-only-required --read-catalog-scope-required --safe-payload-required --public-variant-summary-required --rate-limit-endpoint-required --metrics-endpoint-label-required --rollout-flag-required --no-pii-or-stock-raw-required`
  - endpoint label planejado: `catalog.products.detail`
  - rollout flag planejada: `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`
- Product detail endpoint:
  - `GET /api/v1/catalog/products/<slug>/`
  - endpoint label: `catalog.products.detail`
  - enabled gauge: `hubx_api_key_public_endpoint_enabled{endpoint="catalog.products.detail"}`
- Product detail observability review:
  - `python manage.py api_key_public_product_detail_observability_review --detail-endpoint-executed --metrics-endpoint-label-present --enabled-gauge-present --dashboard-endpoint-filter-covers-detail --alert-rules-endpoint-label-covers-detail --rate-limit-metrics-reused --auth-failure-metrics-reused --no-new-dashboard-required --no-new-alert-rules-required --no-sensitive-labels-required`
  - dashboard e alert rules existentes cobrem detalhe por label `endpoint`
  - não adicionar labels por slug/SKU
- Expansion closure:
  - `python manage.py api_key_public_endpoint_expansion_closure --list-endpoint-ready --detail-endpoint-ready --observability-ready --no-additional-endpoint-selected`
  - fecha o escopo público inicial em listagem + detalhe de produto
  - não seleciona endpoint novo nesta closure
- Governance closure:
  - `python manage.py api_key_governance_closure --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed`
  - fecha o ciclo atual de API keys públicas sem billing/quotas ou endpoint novo
- Token env: `ACCOUNTS_OBSERVABILITY_TOKEN`

### Sinais cobertos

- falhas de login owner/admin;
- rate limit acionado no login owner/admin;
- redirects anônimos do gate `/ops/`;
- bloqueios 403 do gate `/ops/`;
- negações de permissão granular em `/ops/`;
- falhas/backlog de e-mails owner access.
- saúde do provider externo TOTP MFA owner/admin;
- referências externas MFA não resolvidas;
- fatores TOTP MFA ainda em storage local/plain.

### Pós-ativação RBAC production

Comando de acompanhamento:

```bash
python manage.py ops_rbac_post_production_monitoring --tenant-id=<tenant_id> --fail-on-rollback
```

Interpretação:

- `HEALTHY`: nenhum sinal relevante na janela observada.
- `WATCH`: há ruído operacional que exige triagem, mas não rollback automático.
- `ROLLBACK`: há rate limit de login owner/admin ou falha de e-mail owner access; avaliar rollback do gate.

Alertas principais:

- `HubxAccountsOpsPermissionDenied`: warning para negações granulares recorrentes.
- `HubxAccountsRBACPostProductionRollbackSignal`: critical para sinais que podem justificar rollback.
- `HubxAccountsOwnerMfaProviderCritical`: critical para provider TOTP MFA indisponível/quebrado.
- `HubxAccountsOwnerMfaExternalReferenceUnresolved`: critical para `ref:<path>` não resolvido.
- `HubxAccountsOwnerMfaLocalPlainStillPresent`: warning para fallback local ainda presente.

### Dashboard MFA provider

Importar `grafana/accounts-owner-mfa-provider-health-dashboard.json` depois de validar:

- scrape `hubx-accounts-owner-mfa-provider-health` retornando `200`;
- métrica `hubx_accounts_owner_mfa_provider_health_status`;
- métrica `hubx_accounts_owner_mfa_provider_external_reference_total`;
- métrica `hubx_accounts_owner_mfa_secret_storage_total`;
- datasource Prometheus selecionado em `DS_PROMETHEUS`.
