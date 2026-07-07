# Deploy

## Diretriz
- build reproduzível
- migrações controladas
- rollback definido
- storage externo
- config por ambiente

## MVP produção controlada

Antes de liberar tráfego real, seguir `docs/runbooks/production-mvp-release.md`.

Critérios mínimos:

- `python manage.py check`
- `python manage.py test`
- `npm run test:visual`
- smokes locais e template regression verdes
- gates de accounts/RBAC verdes com `HUBX_OPS_AUTH_GATE_ENFORCED=1`
- gates de payments, notifications, shipping e `system_production_closure` verdes com evidência real

Sem esses critérios, a decisão permanece `NO-GO`.
