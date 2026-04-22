# Observability

Configurações de Prometheus, Grafana e exporters.

## Payments
- regras iniciais de alerta para sinais críticos de pagamento:
  - `prometheus/payments-alert-rules.yml`
- exemplo de scrape interno do exporter de `payments`:
  - `prometheus/payments-scrape.example.yml`
- dashboard inicial de Grafana:
  - `grafana/payments-alert-signals-dashboard.json`
- exemplo de roteamento no Alertmanager:
  - `alertmanager/payments-routing.example.yml`

## Runbook curto de ativação
1. configurar `PAYMENTS_OBSERVABILITY_TOKEN` no app
2. publicar o scrape no Prometheus com `prometheus/payments-scrape.example.yml`
3. carregar as regras de alerta de `prometheus/payments-alert-rules.yml`
4. configurar o roteamento inicial no Alertmanager usando `alertmanager/payments-routing.example.yml`
5. importar `grafana/payments-alert-signals-dashboard.json` no Grafana
6. validar:
   - scrape retornando `200`
   - métricas `hubx_payments_alert_signal_total`
   - alertas carregados sem erro
   - dashboard com dados
