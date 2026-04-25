# Checkout Operational Runbook

Runbook para triagem operacional de sessões de checkout no Hubx Market.

## Objetivo
- identificar sessões abertas incompletas antes de impacto comercial
- detectar sessões concluídas cujo vínculo com pedido ficou inconsistente
- expor sinais Prometheus por tenant sem alterar dados automaticamente
- manter diagnóstico dentro da fronteira do módulo `checkout`

## Fronteira
- módulo responsável: `checkout`
- leitura auxiliar: `orders`, apenas para validar vínculo de `completed_order_number`
- não corrige sessões automaticamente
- não cria pedidos
- não altera estoque
- não dispara eventos

## Comando principal

```bash
python manage.py list_checkout_session_issues --tenant-id <tenant_id>
```

Filtros úteis:

```bash
python manage.py list_checkout_session_issues --tenant-id <tenant_id> --issue open_stale
python manage.py list_checkout_session_issues --tenant-id <tenant_id> --issue completed_order_missing
python manage.py list_checkout_session_issues --tenant-id <tenant_id> --issue total_mismatch
```

## Expiração segura de sessões abertas

Antes de ativar em cron, rode sempre em modo simulação:

```bash
python manage.py expire_checkout_sessions --tenant-id <tenant_id> --older-than-hours 24 --dry-run
```

Execução real:

```bash
python manage.py expire_checkout_sessions --tenant-id <tenant_id> --older-than-hours 24
```

Guardrails:
- `--tenant-id` é obrigatório
- `--older-than-hours` precisa ser `>= 6`
- `--limit` limita o lote e aceita no máximo `1000`
- só sessões `open` são alteradas
- sessões `completed` não são tocadas
- sessões são marcadas como `expired`; não são deletadas

## Pruning conservador de sessões expiradas

Antes de remover qualquer registro, rode em modo simulação:

```bash
python manage.py prune_expired_checkout_sessions --tenant-id <tenant_id> --older-than-days 180 --dry-run
```

Execução real:

```bash
python manage.py prune_expired_checkout_sessions --tenant-id <tenant_id> --older-than-days 180
```

Guardrails:
- `--tenant-id` é obrigatório
- `--older-than-days` precisa ser `>= 180`
- `--limit` limita o lote e aceita no máximo `1000`
- só sessões `expired` são removidas
- sessões `open` e `completed` não são tocadas
- itens da sessão são removidos por cascade do ORM
- o contador `deleted` do Django inclui a sessão e objetos relacionados removidos

## Pruning conservador de eventos de recovery

Antes de remover qualquer evento de analytics, rode em modo simulação:

```bash
python manage.py prune_checkout_recovery_events --tenant-id <tenant_id> --older-than-days 180 --dry-run
```

Execução real:

```bash
python manage.py prune_checkout_recovery_events --tenant-id <tenant_id> --older-than-days 180
```

Guardrails:
- `--tenant-id` é obrigatório
- `--older-than-days` precisa ser `>= 180`
- `--limit` limita o lote e aceita no máximo `1000`
- só eventos do tenant informado são removidos
- eventos recentes são preservados para analytics de produto

## UX de sessão expirada
- links com `session_key` de sessão `expired` não caem em showcase/fallback
- a UI mostra estado explícito:
  - `Sessão de checkout expirada`
  - recuperação para voltar ao produto
  - itens apenas como referência, sem mutation actions
- sessão inexistente com `session_key` também não usa fallback demonstrativo
- ações de submit ficam ocultas quando `checkout_session_readonly=True`

## Vocabulário de recovery
- `Voltar ao produto`
  - ação principal quando a sessão atual não é confiável para seguir
  - usado para sessão ausente, expirada, drift, indisponibilidade de completion e conflitos de estoque/variante
- `Reabrir checkout`
  - usado apenas quando a sessão atual ainda é útil para revisão segura
  - exemplo: conflito de snapshot, onde revisar itens/totais da própria sessão pode resolver a inconsistência
- `Como retomar com segurança`
  - título padrão para orientar recuperação sem sugerir que pedido/pagamento já foram confirmados

## Taxonomia de result codes
- `checkout_result_taxonomy.family`
  - `progress`
  - `session`
  - `readiness`
  - `inventory`
  - `snapshot`
  - `cart_mutation`
  - `reorder`
  - `payment_retry`
- `checkout_result_taxonomy.recovery_action`
  - `continue_session`
  - `restart_from_product`
  - `review_current_session`
  - `view_order`
- objetivo:
  - apoiar analytics futuros de recovery
  - evitar que copy e ação recomendada sigam por caminhos divergentes

## Origem segura de nova sessão
- retomada pelo produto chama `checkout_activation_commands.activate_from_product`
- uma sessão `open` só é reutilizada quando:
  - pertence ao mesmo `tenant_id`
  - não está expirada por `expires_at`
  - foi atualizada há menos de 24 horas
- sessões `open` antigas/vencidas encontradas na ativação são marcadas como `expired`
- em seguida uma nova sessão `open` é criada para o produto atual

## Issues monitoradas
- `open_empty`
  - sessão aberta sem itens
- `open_missing_contact`
  - sessão aberta com itens, mas sem nome ou e-mail mínimos
- `open_missing_delivery`
  - sessão aberta com itens, mas sem endereço/frete mínimo
- `open_missing_payment`
  - sessão aberta com itens, mas sem método de pagamento ou aceite de termos
- `open_stale`
  - sessão aberta expirada ou sem atualização há mais de 24 horas
- `completed_order_missing`
  - sessão concluída sem pedido correspondente no mesmo tenant
- `total_mismatch`
  - subtotal/total da sessão diverge do snapshot dos itens

## Métrica Prometheus

```text
hubx_checkout_session_issue_total{tenant_id,issue}
hubx_checkout_session_status_total{tenant_id,status}
hubx_checkout_recovery_result_info{code,family,severity,recovery_action}
hubx_checkout_recovery_event_total{tenant_id,code,family,severity,recovery_action}
```

Endpoint:

```text
/ops/checkout/metrics/session-issues/
```

Autenticação:
- configurar `CHECKOUT_OBSERVABILITY_TOKEN`
- enviar `Authorization: Bearer <token>`
- alternativa: `X-Hubx-Observability-Token: <token>`

## Alertas iniciais
- `open_stale`
  - indica abandono operacional ou sessão candidata a `expire_checkout_sessions`
- `completed_order_missing`
  - indica possível drift entre checkout e pedidos
- `total_mismatch`
  - indica snapshot inconsistente antes/depois de mutação de itens
- `expired`
  - indica estoque crescente de sessões expiradas retidas para futura política de arquivamento

## Triagem segura
1. rodar o comando com `--tenant-id`
2. confirmar `session_key` no admin ou shell
3. validar se há pedido em `orders` no mesmo tenant
4. revisar itens e totais da sessão
5. expirar sessões abertas antigas primeiro com `--dry-run`
6. revisar volume de `status=expired`
7. só rodar pruning após dry-run e janela longa validada
8. só corrigir dados por rotina explícita e registrada

## Limites
- a métrica é gauge derivado de leitura
- `list_checkout_session_issues` é diagnóstico
- `expire_checkout_sessions` só altera `open` para `expired`
- `prune_expired_checkout_sessions` só remove `expired` antigas
- `prune_checkout_recovery_events` só remove eventos antigos de analytics por tenant
- sessão `expired` é read-only na UI
- ativação pelo produto não reutiliza sessão stale ou vencida
- `hubx_checkout_session_status_total{status="expired"}` diferencia retenção expirada de backlog `open_stale`
- recovery copy diferencia recriar pelo produto versus revisar sessão atual
- result codes expõem família e ação recomendada em `checkout_result_taxonomy`
- `hubx_checkout_recovery_result_info` expõe a taxonomia como métrica info, não como contador de ocorrências
- `hubx_checkout_recovery_event_total` conta eventos persistidos de recovery e deve ser lida como analytics de produto
- sessões legadas podem aparecer enquanto não houver política formal de expiração/retention
