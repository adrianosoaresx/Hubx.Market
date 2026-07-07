# Production MVP Release Runbook

## Objetivo

Guiar a liberação do MVP Hubx Market como SaaS self-service controlado, com checkout de loja em produção somente após evidência real. Billing SaaS recorrente permanece fora deste MVP.

## Estado de release

- Release candidate funcional pode avançar para validação controlada.
- Produção real permanece `NO-GO` enquanto qualquer gate P0 estiver bloqueado.
- Novos tenants criados por self-service devem nascer em `maintenance_mode`.
- Rollout deve ser controlado por tenant, nunca global e irrestrito.

## Variáveis obrigatórias

```text
HUBX_OPS_AUTH_GATE_ENFORCED=1
HUBX_PUBLIC_SIGNUP_ENABLED=0|1
HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN=1
HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN=<secret-operacional>
HUBX_MARKET_ROOT_DOMAIN=hubx.market
ALLOWED_HOSTS=.hubx.market,hubx.market
```

`HUBX_PUBLIC_SIGNUP_ENABLED` só deve virar `1` quando houver dono operacional online e token distribuído por canal privado. O token nunca deve ser registrado em issue, audit log, screenshot ou documento.

## Pré-flight técnico

Execute a partir de `backend/`, exceto o teste visual:

```powershell
python manage.py check
python manage.py test
python manage.py system_template_regression_smoke --fail-on-blockers
python manage.py local_e2e_smoke --fail-on-blockers
python manage.py ops_auth_gate_readiness --fail-on-blockers
$env:HUBX_OPS_AUTH_GATE_ENFORCED='1'; python manage.py ops_rbac_production_readiness --fail-on-blockers
```

Na raiz do repositório:

```powershell
npm run test:visual
```

Critério: todos verdes antes de qualquer validação produtiva.

## Accounts e RBAC

1. Confirmar `OwnerUser` ativo para cada tenant ativo.
2. Confirmar `User` Django ativo para cada owner/admin de produção.
3. Confirmar ausência de e-mail duplicado ou owner sem usuário.
4. Confirmar `HUBX_OPS_AUTH_GATE_ENFORCED=1`.
5. Validar login owner/admin pelo host correto:
   - platform: `hubx.market`
   - loja: `{tenant}.hubx.market`

Rollback: definir `HUBX_OPS_AUTH_GATE_ENFORCED=0` apenas durante incidente autenticado e temporário, registrar decisão e reativar após correção.

## Signup self-service

1. Manter `HUBX_PUBLIC_SIGNUP_ENABLED=0` até o piloto.
2. Configurar `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN`.
3. Validar `GET /plans/signup/` e POST com token em staging.
4. Confirmar que POST sem token não cria tenant.
5. Confirmar que tenant criado nasce com `maintenance_mode=True`.
6. Confirmar que storefront/checkout retornam `503` enquanto manutenção estiver ligada.
7. Confirmar que `/accounts/` e `/ops/` seguem acessíveis para configuração.

Rollback: desligar `HUBX_PUBLIC_SIGNUP_ENABLED`, rotacionar token e manter tenants recém-criados em manutenção.

## Payments

Produção só pode avançar quando:

```powershell
python manage.py payments_production_readiness --review closure --fail-on-blockers
```

estiver verde com evidência real:

- credenciais/provider em modo produção configurados;
- webhook pago/falho observado;
- assinatura/idempotência confirmadas;
- pedido, pagamento e estoque conciliados;
- refund manual controlado validado ou No-Go registrado;
- relatório de reconciliação anexado;
- runbook, rollback, janela de monitoramento e dono de incidente confirmados;
- nenhuma credencial, header, token ou payload sensível registrado.

Rollback: desativar rollout do provider, manter pedidos pendentes em triagem manual, bloquear novos checkouts pagos e preservar auditoria.

## Notifications

Produção só pode avançar quando:

```powershell
python manage.py notification_production_delivery --review closure --fail-on-blockers
```

estiver verde com:

- provider real configurado;
- domínio remetente confirmado;
- smoke transacional enviado;
- referência de mensagem registrada de forma redigida;
- bounce/failure handling definido;
- dashboard, métricas e alert owner confirmados.

Rollback: trocar provider para modo seguro/dry-run, pausar automações de envio e usar comunicação manual para incidentes.

## Shipping

Produção só pode avançar quando:

```powershell
python manage.py shipping_quote_productionization --fail-on-blockers
```

estiver verde. Para MVP, quote manual/local é aceitável se:

- contrato do provider/manual quote estiver documentado;
- checkout não criar pedido sem entrega válida;
- UX de falha estiver clara;
- observabilidade e rollback estiverem definidos;
- não houver segredo/header de provider em log/evidence.

Rollback: desativar checkout de pedidos com entrega incerta e retornar tenants afetados para `maintenance_mode`.

## Go/No-Go final

Executar:

```powershell
python manage.py system_production_closure --review go-nogo --fail-on-blockers
```

Critério Go:

- readiness matrix atualizada;
- runbooks completos;
- smoke checklist verde;
- observabilidade confirmada;
- rollback drill executado;
- riscos residuais aceitos;
- dono de decisão confirmado;
- docs atualizadas;
- decisão registrada em `DECISIONS.md`.

## Evidência

Registrar evidências em `docs/audits/` ou no sistema operacional externo com referência sanitizada. Nunca anexar:

- token;
- segredo;
- Authorization header;
- payload completo de pagamento;
- dados de cartão;
- dados bancários;
- PII desnecessária.

