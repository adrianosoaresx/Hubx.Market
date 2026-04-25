# Shipping Operational Runbook

Este runbook consolida a ativação operacional do módulo `shipping` para provider de rastreio, polling, observabilidade e retenção.

## Escopo
- configurar provider de tracking por tenant
- ativar polling de shipments não terminais
- expor métricas Prometheus
- carregar alertas, dashboard e routing
- executar retenção segura do histórico operacional

## Pré-requisitos
- tenant criado e resolvido por subdomínio
- pedidos pagos/preparados com `Shipment`
- worker Celery disponível
- Prometheus com acesso ao app interno
- Grafana com datasource Prometheus
- Alertmanager ou roteador equivalente

## Configuração do provider
1. acessar `/ops/shipping/provider/`
2. selecionar tenant
3. configurar:
   - `provider_name=http`
   - `base_url`
   - `api_token`, quando aplicável
   - `timeout_seconds`
   - `is_active=true`
4. salvar e validar que o token aparece como configurado sem ser ecoado.

## Polling
Executar manualmente:

```bash
python manage.py sync_shipments_tracking --limit=100
```

Executar por tenant:

```bash
python manage.py sync_shipments_tracking --tenant-id=<id> --limit=100
```

Agendamento recomendado:
- a cada 10–15 minutos em produção
- task Celery: `shipping.sync_pending_shipments_tracking`
- limite inicial: `100`

## Observabilidade
Configurar token:

```bash
SHIPPING_OBSERVABILITY_TOKEN=<secret>
```

Endpoint:

```text
/ops/shipping/metrics/
```

Métricas principais:
- `hubx_shipping_shipment_total`
- `hubx_shipping_history_event_total`
- `hubx_shipping_provider_http_status_total`
- `hubx_shipping_provider_latency_ms_avg`

Artefatos:
- `infra/observability/prometheus/shipping-scrape.example.yml`
- `infra/observability/prometheus/shipping-alert-rules.yml`
- `infra/observability/grafana/shipping-polling-dashboard.json`
- `infra/observability/alertmanager/shipping-routing.example.yml`

## Alertas iniciais
- `HubxShippingCreatedBacklogHigh`
- `HubxShippingCanceledShipmentsPresent`
- `HubxShippingNoTrackingSyncActivity`
- `HubxShippingProviderFailuresPresent`
- `HubxShippingProviderHttp5xxPresent`
- `HubxShippingProviderLatencyHigh`

## Retenção
Simular pruning:

```bash
python manage.py prune_shipment_history --days=90 --dry-run
```

Executar pruning global:

```bash
python manage.py prune_shipment_history --days=90
```

Executar pruning por tenant:

```bash
python manage.py prune_shipment_history --tenant-id=<id> --days=90
```

Regra de segurança:
- `--days` precisa ser maior ou igual a `30`

## Diagnóstico rápido
- backlog alto em `created`:
  - verificar scheduler/worker Celery
  - rodar `sync_shipments_tracking --dry-run` não existe; usar limite baixo em tenant controlado
- ausência de `shipment_tracking_synced`:
  - verificar task `shipping.sync_pending_shipments_tracking`
  - validar provider ativo por tenant
  - validar `base_url`, token e timeout
- HTTP 5xx:
  - revisar disponibilidade do provider
  - verificar incidentes externos
  - reduzir frequência se houver rate limit
- latência alta:
  - revisar rede e timeout
  - comparar tenants afetados
  - confirmar se o provider está degradado

## Limites atuais
- não há histograma de latência.
- não há arquivamento frio antes do pruning.
- o token do provider ainda depende de hardening futuro com secret manager ou criptografia em repouso.
