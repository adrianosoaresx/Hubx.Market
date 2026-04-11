# ARCHITECTURE.md

## Visão geral
Hubx Market é uma plataforma SaaS de e-commerce multi-tenant com foco em lojas online independentes executando dentro da mesma base de produto.

## Domínios oficiais
- `hubx.market` → site institucional
- `app.hubx.market` → painel da plataforma
- `api.hubx.market` → API
- `<tenant>.hubx.market` → loja do cliente

## Princípios
- multi-tenant por subdomínio
- banco único com isolamento lógico por `tenant_id`
- backend modular em Django
- UI server-rendered com HTMX
- design system documentado
- componentes reutilizáveis
- filas assíncronas para tarefas lentas

## Stack
- Django + DRF
- PostgreSQL
- SQLite local
- Redis
- Celery
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS
- S3/R2
- Prometheus + Grafana

## Domínios principais do sistema
- plataforma / tenants
- contas administrativas
- customers
- catálogo
- carrinho
- checkout
- pedidos
- pagamentos
- shipping
- coupons
- reviews
- subscriptions
- notifications
- audit

## Arquitetura da UI
Padrões de interface são regidos por:
- `docs/ui/design-system.md`
- `docs/ui/component-library.md`
- `docs/ui/forms-and-validation.md`
- `docs/ui/interaction-patterns.md`
- `docs/ui/htmx-patterns.md`

## Diretriz
Nenhuma implementação de UI deve fugir do design system sem atualização da documentação correspondente.
