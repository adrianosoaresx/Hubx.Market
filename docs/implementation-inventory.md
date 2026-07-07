# Implementation Inventory — Hubx Market

Data: 2026-07-01

Este inventário registra a fotografia atual do que está implementado no Hubx Market. Ele deve ser usado como ponto de partida antes de planejar novas waves, junto com:

- `docs/modules-index.md`
- `docs/module-boundaries.md`
- `docs/request-lifecycle.md`
- `docs/events-map.md`
- `docs/system-execution-wave-batteries.md`

## Como este inventário foi levantado

Fontes verificadas:

- documentação obrigatória em `AGENTS.md`;
- apps registrados em `backend/config/settings/base.py`;
- URLs registradas em `backend/config/urls.py`;
- introspecção Django dos modelos instalados;
- `python manage.py check`;
- `python manage.py showmigrations --plan`;
- árvore de templates, componentes, comandos, testes e observabilidade.

Validação executada:

- `python manage.py check` sem issues;
- todas as migrations dos módulos do projeto aparecem aplicadas no SQLite local;
- não foi executada a suíte completa de testes neste inventário.

## Resumo executivo

O repositório não é mais apenas blueprint documental. Existe uma aplicação Django modular funcional com:

- 17 módulos de produto registrados em `INSTALLED_APPS`;
- 40 modelos de domínio próprios;
- 54 migrations de módulos do projeto;
- 136 management commands;
- 207 arquivos de teste backend;
- 127 templates úteis em `ui/templates`;
- 41 componentes compartilhados de UI;
- dashboards, alert rules e exemplos de scrape/routing para observabilidade.

O corte atual cobre storefront, catálogo, carrinho, checkout, pedidos, pagamentos, frete, área do cliente, admin `/ops/`, portal platform, auditoria, API keys públicas de catálogo, subscriptions foundation, notifications e runbooks operacionais.

## Backend

### Configuração e runtime

- Projeto Django em `backend/`, com settings base/development/production.
- Desenvolvimento local usa SQLite em `backend/db.sqlite3`.
- Produção está configurada para PostgreSQL via variáveis de ambiente.
- DRF está instalado, mas autenticação global continua em Session/Basic; API key é opt-in por view.
- Celery está configurado em `backend/config/celery.py` e usa Redis por `CELERY_BROKER_URL`.
- Tenant resolution roda por middleware de `tenants`.
- Contexto owner/admin e gate `/ops/` rodam por middlewares de `accounts`.

### Módulos instalados

| Módulo | Modelos principais | Superfícies implementadas | Estado atual |
| --- | --- | --- | --- |
| `tenants` | `Tenant`, `TenantOnboarding` | middleware de tenant, platform tenant admin, onboarding platform, custom domain atrás de flag, hero institucional da storefront, `/ops/branding/` | operacional para gestão interna e branding leve da home; DNS/TLS/billing real fora |
| `accounts` | `AccountProfile`, `OwnerUser`, `OwnerMfaFactor`, `OwnerMfaRecoveryCode` | login owner/admin, customer area, `/ops/owners/`, MFA, RBAC, métricas owner access/MFA | amplo e sensível; depende de env/gates para produção |
| `subscriptions` | `SubscriptionPlan`, `TenantSubscription`, `SubscriptionAcquisitionLead` | `/plans/`, `/plans/signup/`, fila platform de aquisições, admin read-only e commands foundation | aquisição pública segura, trial de 30 dias/cartão obrigatório como contrato de plano; billing provider, captura de cartão e enforcement fora |
| `audit` | `AuditLog` | writer, admin read-only, export, closures/evidências | implementado para ações explícitas; sem middleware global |
| `api_keys` | `ApiKey`, `ApiKeyQuota`, `ApiKeyQuotaUsage` | criação/revogação via services, auth DRF opt-in, throttle, quotas, métricas, admin quotas | API pública de catálogo implementada; billing/UX rica fora |
| `catalog` | `Product`, `ProductVariant`, `ProductImage`, `StorefrontDiscoveryEventLog` | storefront, PDP, admin products CRUD, analytics, public API list/detail | CRUD básico de produto implementado com desativação sem delete; `Brand`, `Category` e `Tag` normalizados ainda não existem |
| `customers` | `Customer`, `CustomerAddress` | admin list/detail/actions, métricas/data issues | base operacional implementada |
| `cart` | `Cart`, `CartItem`, `CartMutation` | página de carrinho, commands, handoff para checkout | carrinho persistente implementado |
| `checkout` | `CheckoutSession`, `CheckoutSessionItem`, `CheckoutRecoveryEvent` | checkout page, completion, retry, reorder, quote integration, metrics | orquestra fluxo de compra; pedido nasce no final do checkout |
| `orders` | `Order`, `OrderItem`, `OrderStatusHistory` | admin orders, customer order detail/actions, inventory exception metrics | lifecycle base implementado |
| `payments` | `PaymentAttempt`, `PaymentRefund` | webhook, hosted redirect/return, finance/refund ops, metrics, readiness | integração real depende de provider/env/gates |
| `shipping` | `Shipment`, `ShipmentStatusHistory`, `ShippingProviderSettings`, `ShippingProviderSettingsHistory` | admin shipping, provider settings, tracking sync, quote skeleton, metrics | tracking/quote foundation implementada; transportadora real fora |
| `coupons` | `Coupon`, `CouponRedemption` | admin lite, validação, ledger e reversão | cupom mínimo implementado |
| `reviews` | `ProductReview` | submissão, elegibilidade, moderação admin, agregados PDP | prova social inicial implementada |
| `newsletter` | `NewsletterSubscriber` | opt-in público e admin read-only | base consentida implementada |
| `notifications` | `EmailLog` | event bus, delivery commands/tasks, readiness, metrics, lifecycle pós-compra | pipeline transacional implementado; campanhas avançadas fora |
| `pages` | `Page` | admin lite e storefront published-only | páginas institucionais e SEO básico implementados |

## Superfícies HTTP

Principais grupos de rota registrados:

- `/` storefront home em host tenant-owned e home pública do portal em host central;
- `/demo/` entrada pública da demo com escolha entre perfil admin e cliente, apontando para sessão direta na loja demo ativa configurada;
- `hubx-demo` tenant-owned opera em modo somente leitura por middleware, com logo/paleta Hubx e catálogo seedado com imagens raster realistas;
- `/catalog/` listagem e PDP;
- `/cart/` carrinho;
- `/checkout/` checkout;
- `/payments/` webhook, hosted payment e métricas de alert signal;
- `/accounts/` login, MFA, logout, seleção de loja, customer area, reset e métricas;
- `/newsletter/` opt-in público;
- `/pages/<slug>/` páginas públicas publicadas;
- `/api/v1/catalog/products/` e `/api/v1/catalog/products/<slug>/` API pública protegida por API key;
- `/api-keys/metrics/public-endpoints/` métricas protegidas por token;
- `/notifications/metrics/email-logs/` métricas protegidas por token;
- `/ops/...` cockpit/admin por módulo;
- `/ops/branding/` configuração tenant-scoped de logo e hero institucional da loja;
- `/ops/catalog/products/`, `/ops/catalog/products/new/`, `/ops/catalog/products/<slug>/edit/` e `/ops/catalog/products/<slug>/actions/deactivate/` para CRUD administrativo básico de produtos;
- `/ops/platform/tenants/` gestão platform de tenants;
- `/ops/platform/onboarding/` onboarding platform self-service.
- `/plans/` aquisição pública de plano SaaS como lead seguro;
- `/ops/platform/acquisitions/` revisão/conversão platform de leads SaaS.

## UI e Design System

Implementado em `ui/`:

- tokens JSON e CSS gerado;
- temas por contexto (`storefront`, `account`, `checkout`, `admin`) e tenant demo `hubx-demo`;
- shells oficiais: storefront, admin, account, checkout, auth e base;
- navegação pública central compartilhada entre portal, planos e auth central;
- componentes compartilhados para ações, commerce, composite, data display, feedback, forms, layout, navigation e overlays;
- botão compartilhado com variantes `primary`, `secondary`, `ghost`, `danger`, `success` e `link`, tamanhos `sm`, `md` e `lg`, ícones Lucide e estados `disabled/loading`;
- aliases runtime de compatibilidade para tokens legados de superfície, borda e texto, mantendo templates existentes funcionais enquanto novos templates usam tokens semânticos atuais;
- templates operacionais em `ui/templates/pages/templates/`;
- páginas internas do design system em `__internal__/design-system/`;
- baseline Playwright visual em `tests/visual`.

## Infraestrutura e observabilidade

Implementado:

- `docker-compose.yml` raiz com web, Postgres e Redis;
- `infra/docker-compose.yml` mínimo para Postgres/Redis;
- scripts locais PowerShell para hosts, demo e acesso owner/platform;
- runbooks em `docs/runbooks`;
- dashboards Grafana versionados para accounts, API keys, catalog, checkout, customers, inventory, notifications, payments e shipping;
- alert rules Prometheus e exemplos de scrape por domínio;
- exemplos de routing Alertmanager.

Ainda fora do corte:

- Dockerfile/runtime produtivo completo;
- provisionamento real de Prometheus/Grafana/Alertmanager;
- deploy automatizado completo;
- storage/CDN real para mídia.

## Dados locais de demonstração

No SQLite local inspecionado:

- `Tenant`: 3 registros;
- `OwnerUser`: 5 registros;
- `AccountProfile`: 2 registros;
- `Customer`: 2 registros;
- `CustomerAddress`: 1 registro;
- `Product`: 50 registros;
- `ProductVariant`: 150 registros;
- `ProductImage`: 200 registros;
- `StorefrontDiscoveryEventLog`: 0 registros;
- `Cart`: 5 registros;
- `CartItem`: 5 registros;
- `CheckoutSession`: 2 registros;
- `AuditLog`: 43 registros.

Os demais domínios principais existem com tabelas/migrations, mas estavam sem dados locais no momento do inventário.

## Lacunas e limites conhecidos

- `Brand`, `Category`, `Tag`, `ProductCategory` e `ProductTag` ainda não existem como entidades normalizadas; catálogo usa campos simples em `Product`.
- Billing SaaS real, invoices e pagamentos de assinatura ainda não foram implementados.
- API pública está limitada a catálogo list/detail com `read:catalog`.
- API keys não substituem tenant resolution; tenant continua vindo do host/request.
- Payment provider real, webhook produtivo e refund real dependem de env, credenciais, gates e evidência operacional.
- Shipping quote real com transportadora/token externo segue fora; o corte atual é foundation/skeleton operacional.
- Notifications têm pipeline, tasks e logs, mas campanhas recorrentes/scoring/segmentação avançada seguem fora.
- Pages não têm page builder, editor rico, menus dinâmicos ou localização.
- Audit não é middleware global nem diff genérico de model; registra ações explícitas.

## Próximo uso recomendado

Antes de evoluir uma área:

1. Localizar o módulo dono neste inventário.
2. Conferir a fronteira em `docs/module-boundaries.md`.
3. Conferir o ciclo em `docs/request-lifecycle.md`.
4. Conferir eventos em `docs/events-map.md`.
5. Atualizar este inventário se a mudança alterar modelos, endpoints, commands, infra ou readiness.
