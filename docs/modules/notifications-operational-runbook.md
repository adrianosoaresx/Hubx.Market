# Notifications Operational Runbook

Este runbook consolida a operação inicial do módulo `notifications`: readiness, processamento de logs, observabilidade e diagnóstico de entrega.

## Escopo
- validar readiness geral de notificações
- validar provider antes de entrega real
- listar e processar `EmailLog` por tenant
- expor métricas Prometheus
- carregar alertas, dashboard e routing
- diagnosticar backlog/falhas de e-mail

## Pré-requisitos
- tenant criado
- eventos gerando `EmailLog`
- owner/customer destinatários configurados quando aplicável
- worker Celery disponível se processamento assíncrono estiver ativo
- provider de e-mail configurado ou dry-run assumido explicitamente
- Prometheus/Grafana/Alertmanager disponíveis

## Configuração principal
Variáveis esperadas:

```bash
NOTIFICATIONS_EMAIL_DRY_RUN=true
NOTIFICATIONS_EMAIL_BACKEND=<backend>
DEFAULT_FROM_EMAIL=<from-email>
NOTIFICATIONS_EMAIL_BATCH_SIZE=25
NOTIFICATIONS_OBSERVABILITY_TOKEN=<secret>
```

Antes de desativar dry-run:

```bash
python manage.py notification_provider_readiness
```

Só avançar para entrega real quando:
- `can_attempt_real_delivery=true`
- `blockers=none`

## Readiness por tenant
Rodar:

```bash
python manage.py notification_readiness --tenant-id=<id>
```

Validar:
- total de logs
- planejados
- solicitados
- enviados
- falhos
- skipped
- pendências
- falhas

## Triagem de logs
Listar logs por tenant:

```bash
python manage.py list_email_logs --tenant-id=<id> --limit=25
```

Listar falhas:

```bash
python manage.py list_email_logs --tenant-id=<id> --status=failed --limit=25
```

Listar backlog planejado:

```bash
python manage.py list_email_logs --tenant-id=<id> --status=planned --limit=50
```

Listar logs travados/antigos:

```bash
python manage.py list_email_logs --tenant-id=<id> --status=requested --stale-hours=6 --limit=50
```

## Processamento
Processar lote planejado por tenant:

```bash
python manage.py process_email_logs --tenant-id=<id> --limit=25
```

Recomendação:
- começar com lote pequeno por tenant
- validar readiness antes/depois
- manter dry-run ligado até provider estar pronto

## Observabilidade
Endpoint:

```text
/notifications/metrics/email-logs/
```

Autenticação:
- header `Authorization: Bearer <NOTIFICATIONS_OBSERVABILITY_TOKEN>`
- ou `X-Hubx-Observability-Token`

Métrica principal:
- `hubx_notifications_email_log_total{tenant_id,status}`

Artefatos:
- `infra/observability/prometheus/notifications-scrape.example.yml`
- `infra/observability/prometheus/notifications-alert-rules.yml`
- `infra/observability/grafana/notifications-email-logs-dashboard.json`
- `infra/observability/alertmanager/notifications-routing.example.yml`

## Alertas iniciais
- `HubxNotificationsFailedLogsPresent`
- `HubxNotificationsBacklogHigh`
- `HubxNotificationsRequestedStuck`

## Diagnóstico rápido
- backlog alto em `planned`:
  - verificar worker/Celery
  - rodar `notification_readiness --tenant-id=<id>`
  - processar lote pequeno com `process_email_logs`
- logs em `requested` por muito tempo:
  - verificar provider/backend
  - confirmar se dry-run está ativo
  - revisar retorno do comando de processamento
- logs `failed`:
  - listar com `list_email_logs --status=failed`
  - revisar destinatário, provider e conteúdo renderizado
- destinatário ausente:
  - validar owner/customer do tenant
  - revisar resolver de recipients

## Limites atuais
- métrica atual é gauge por status persistido.
- não há histograma de latência de entrega.
- não há métrica de bounce/rejection do provider.
- não há pruning de `EmailLog` nesta fase.
