# Auditoria estrategica - home, login, planos e demo

Data: 2026-07-02

## Escopo

- Rotas auditadas no navegador in-app: `/`, `/accounts/login/`, `/plans/`, `/demo/`.
- Fluxos clicados: home -> planos, planos -> demo, demo -> vitrine, demo -> admin, demo -> cliente.
- Viewport auditado: 548px de largura no in-app browser.

## Responsabilidade e arquitetura

- Modulo responsavel: camada UI/interfaces dos fluxos publicos e admin shell visual.
- Documentacao consultada: `docs/ui/*`, `docs/brand.md`, `docs/request-lifecycle.md`, `docs/module-boundaries.md`.
- Multi-tenant: preservado. Nenhuma regra de tenant, billing, assinatura, pedido ou catalogo foi alterada.
- Fronteiras de modulo: preservadas. Ajustes ficaram em templates compartilhados/publicos e CSS do design system.
- Eventos: nao afetados.
- Ciclo de requisicao: sem mudanca funcional; somente renderizacao e cache de asset CSS.
- Documentacao estrutural: nao exigida, pois nao houve mudanca de contrato de dominio ou arquitetura.

## Problemas encontrados e correcoes

1. Header publico quebrava em largura estreita porque o navegador mantinha `app.css` antigo.
   - Correcao: `site-header-inner` aplicado aos headers publicos e auth.
   - Correcao: `public-nav-label` escondido no breakpoint pequeno pelo DS.
   - Correcao: `app.css` versionado no `base.html` para evitar cache local stale.

2. Demo admin gerava overflow horizontal ao entrar em `/ops/`.
   - Correcao: filhos de `admin-ops-dashboard-grid` e `admin-ops-detail-layout` agora usam `min-width: 0` e `max-width: 100%`.
   - Resultado: tabelas continuam com scroll interno, sem expandir a pagina.

## Validacao final

- `npm run build:css`: passou.
- `python backend\manage.py check`: passou.
- Auditoria final no navegador: `green: true`.
- Console logs: vazio nas rotas publicas.
- Imagens quebradas: nenhuma.
- Overflow horizontal: nenhum nas rotas e nos destinos demo validados.

## Evidencias

- `audit-final.json`
- `screenshots-final.json`
- `final-home.png`
- `final-login.png`
- `final-plans.png`
- `final-demo.png`
- `final-demo-admin-viewport.png`

Observacao: a captura full-page de `final-demo-admin.png` apresentou artefato de costura do runtime em pagina longa. A evidencia valida para admin e `final-demo-admin-viewport.png`.
