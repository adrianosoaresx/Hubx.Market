# Public API

## Objetivo
Permitir integrações futuras com:
- ERP
- aplicativos mobile
- marketplaces
- ferramentas externas

## Recursos candidatos
- produtos
- pedidos
- estoque
- clientes

## Superfície ativa

O primeiro recorte público ativo é catálogo read-only por API key tenant-scoped.

- guia de onboarding: `docs/api/public-catalog-partner-onboarding.md`
- escopo obrigatório: `read:catalog`
- endpoints:
  - `GET /api/v1/catalog/products/`
  - `GET /api/v1/catalog/products/<slug>/`

Fora de escopo nesta fase:

- pedidos
- clientes
- pagamentos
- estoque bruto
- operações admin
- billing ou quotas comerciais
