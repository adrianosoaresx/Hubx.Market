# Rollback

## Princípio
Toda mudança estrutural relevante deve prever reversão.

## Casos
- falha em deploy
- migração problemática
- regressão crítica

## MVP produção controlada

Rollback inicial do MVP:

1. desligar `HUBX_PUBLIC_SIGNUP_ENABLED`;
2. manter ou religar `maintenance_mode` nos tenants afetados;
3. desativar rollout de provider de pagamento/notificação/frete;
4. pausar novos checkouts pagos se houver incerteza de pagamento ou entrega;
5. preservar logs/auditoria sem incluir secrets ou payload sensível;
6. registrar incidente e decisão em `DECISIONS.md` ou pacote de evidência operacional.

O runbook completo está em `docs/runbooks/production-mvp-release.md`.
