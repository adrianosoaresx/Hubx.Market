# Hubx Market

Hubx Market é uma plataforma SaaS de e-commerce multi-tenant para criação e operação de lojas online.

## Produto
- Marca: Hubx Market
- Domínio principal: `hubx.market`
- Modelo: SaaS multi-tenant por subdomínio
- Exemplo de tenant: `lojax.hubx.market`

## Stack principal
- Backend: Python + Django + Django REST Framework
- UI: Django Templates + HTMX + Alpine.js + Tailwind CSS
- Banco: PostgreSQL
- Desenvolvimento local: SQLite
- Cache/Fila: Redis + Celery
- Storage: S3 / Cloudflare R2
- Observabilidade: Prometheus + Grafana

## Estrutura do repositório
- `backend/` → backend Django
- `ui/` → assets, templates e design system
- `infra/` → docker, deploy e operação
- `docs/` → documentação técnica, produto, dados, módulos e UI

## Documentos principais
- `AGENTS.md`
- `ARCHITECTURE.md`
- `PRODUCT_RULES.md`
- `docs/implementation-inventory.md`
- `docs/brand.md`
- `docs/domain-model.md`
- `docs/data/erd.md`
- `docs/ui/design-system.md`

## Status
Este repositório já contém uma aplicação Django modular funcional, com storefront, admin `/ops/`, checkout, catálogo, carrinho, pedidos, pagamentos, frete, API pública de catálogo, auditoria, subscriptions foundation, notifications e design system.

A fotografia atual do que está implementado vive em `docs/implementation-inventory.md`.
