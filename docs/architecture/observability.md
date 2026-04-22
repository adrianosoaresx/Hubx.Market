# Observability

## Stack
- Prometheus
- Grafana

## Métricas técnicas
- tempo de resposta
- erros HTTP
- uso de CPU
- uso de memória
- métricas Redis
- métricas Celery

## Métricas de negócio
- número de lojas
- número de pedidos
- GMV
- taxa de conversão

## Exporters internos mínimos
- módulos podem expor superfícies internas e protegidas para métricas operacionais específicas
- `payments` agora exporta sinais críticos de alerta em formato Prometheus por:
  - `/payments/metrics/alert-signals/`
- esse endpoint deve ser consumido apenas por monitoramento interno/autorizado
- para reduzir atrito com Prometheus, o exporter de `payments` aceita:
  - `X-Hubx-Observability-Token`
  - ou `Authorization: Bearer <token>`
- as primeiras regras de alerta da trilha ficam em:
  - `infra/observability/prometheus/payments-alert-rules.yml`
- o dashboard inicial da trilha fica em:
  - `infra/observability/grafana/payments-alert-signals-dashboard.json`
- o exemplo de roteamento do Alertmanager fica em:
  - `infra/observability/alertmanager/payments-routing.example.yml`
