# Auditoria dos planos Hubx Market - 2026-07-08

## Escopo

- Revisao da alteracao comercial Essencial, Pro e Enterprise.
- Testes automatizados focados em subscriptions, catalog, checkout e payments.
- Validacao E2E/browser de planos publicos, signup controlado, admin de assinatura e billing method.

## Evidencias

- `01-public-plans-desktop.png`
- `02-public-plans-mobile.png`
- `03-public-signup-starter.png`
- `04-public-signup-pro-blocked.png`
- `05-public-signup-essential-success.png`
- `06-admin-subscriptions-list.png`
- `07-admin-subscriptions-essential.png`
- `08-admin-billing-method-essential.png`
- `09-admin-billing-method-fake-active.png`
- snapshots de acessibilidade: `01-public-plans-desktop-snapshot.md`, `02-public-plans-mobile-snapshot.md`, `03-public-signup-starter-snapshot.md`

## Testes executados

- `python backend/manage.py test ...` com 123 testes focados: OK.
- `python backend/manage.py check`: OK.
- `python backend/manage.py makemigrations --check --dry-run`: OK.
- `python backend/manage.py local_e2e_smoke --fail-on-blockers`: READY, 136 checks, 0 blockers.
- `python backend/manage.py system_template_regression_smoke --host hubx-demo.localhost:8002 --owner-email admin@hubx-demo.market --fail-on-blockers`: BLOCKED por marcador antigo da home central (`href="/accounts/login/"`), fora do fluxo especifico dos planos.
- `git diff --check`: OK, somente avisos CRLF.

## Achados principais

1. P1 - Billing method pode ser ativado por owner tenant com referencia falsa.
   - Evidencia: `09-admin-billing-method-fake-active.png`.
   - Resultado observado: owner da loja marcou `billing_method_status=active`, `billing_external_reference=cus_fake_audit` e `billing_method_reference=tok_fake_audit_secret` sem validacao provider.

2. P1 - Referencia tokenizada e enviada de volta para HTML.
   - Evidencia: `09-admin-billing-method-fake-active.png`.
   - Risco: token/reference usado para cobranca complementar fica visivel no input e no source da pagina.

3. P1 - Snapshot de payload Asaas pode persistir `creditCardToken`.
   - `provider_adapters.py` inclui `creditCardToken` no payload e retorna `payload_snapshot.request`.
   - `platform_billing_commands.py` grava `provider_response` no metadata do ledger.

4. P2 - Signup mostra Pro/Enterprise mesmo bloqueando esses planos no POST.
   - Pro foi bloqueado corretamente com mensagem de onboarding assistido e sem criar tenant.
   - UX fica confusa porque a opcao aparece como selecionavel em um fluxo que nao a aceita.

5. P2 - Sucesso do signup Essencial exibe `plano starter`.
   - Evidencia: `05-public-signup-essential-success.png`.
   - Risco: vazamento de nomenclatura interna e desalinhamento com posicionamento comercial.

6. P2 - Admin mostra Billing method para Essencial.
   - Evidencia: `07-admin-subscriptions-essential.png` e `08-admin-billing-method-essential.png`.
   - Essencial nao exige billing method; a acao induz configuracao desnecessaria.

7. P2 - Excesso por corrida acima do limite mensal nao tem marcador/auditoria especifica.
   - Checkout bloqueia novo pagamento quando o limite ja foi atingido.
   - Webhook cria ledger normal, mas nao registra explicitamente overage para tratativa comercial.

8. P2 - Documentacao obrigatoria ainda tem trechos do modelo antigo.
   - Foram encontrados textos sobre `trial de 30 dias`, `cartao obrigatorio` e `requires_payment_method` em docs obrigatorios e DECISIONS antigas sem supersedencia clara.

## Pontos positivos

- Pagina publica de planos esta clara, com 3 planos, sem "30 dias", "cartao obrigatorio", "trial", "Starter" ou "Escala" na copy visivel.
- Desktop e mobile sem overflow horizontal.
- Pro no signup controlado nao cria tenant sem billing method.
- Essencial cria tenant em modo manutencao com assinatura ativa.
- Limites de catalogo e pedidos possuem testes focados passando.
