# Codex Knowledge Transfer
Hubx Market

Este documento contém os prompts usados para transferir conhecimento do projeto para agentes de IA como Codex.

O objetivo é fazer com que o agente compreenda profundamente:

- produto
- arquitetura
- domínio
- modelagem de dados
- UI
- APIs
- pagamentos
- segurança
- performance
- testes

Esses prompts devem ser executados **na ordem definida abaixo**.

---

# ORDEM DE EXECUÇÃO

1. Prompt 1 — visão geral do projeto
2. Prompt 2 — arquitetura e regras de negócio
3. Prompt 3 — UI e design system
4. Prompt 4 — módulos do sistema
5. Prompt 5 — revisão geral
6. Prompt 6 — contrato operacional
7. Prompt 8 — regras de arquitetura de código
8. Prompt 9 — regras de modelagem de dados
9. Prompt 10 — regras de UI
10. Prompt 11 — regras de API
11. Prompt 12 — pagamentos e webhooks
12. Prompt 13 — performance
13. Prompt 14 — segurança
14. Prompt 15 — testes automatizados

---

# PROMPT 1 — visão geral do projeto

Hubx Market é uma plataforma SaaS de e-commerce multi-tenant.

Cada loja opera em um subdomínio:

lojax.hubx.market  
nike.hubx.market  
demo.hubx.market  

Arquitetura:

Backend
- Python
- Django
- Django REST Framework

Frontend
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

Infraestrutura
- PostgreSQL
- Redis
- Celery
- S3 / Cloudflare R2
- Prometheus
- Grafana

Estrutura do repositório:

backend/  
ui/  
infra/  
docs/  

Documentos principais:

README.md  
AGENTS.md  
PROJECT_MAP.md  
ARCHITECTURE.md  
PRODUCT_RULES.md  
DECISIONS.md  

docs/domain-model.md  
docs/data/erd.md  
docs/modules/  
docs/ui/

Tarefa do agente:

1. ler documentação
2. entender arquitetura
3. identificar entidades principais
4. identificar módulos principais
5. listar riscos arquiteturais

Não implementar código.

---

# PROMPT 2 — arquitetura e regras de negócio

Regras fundamentais:

Multi-tenant
- tenant resolvido por subdomínio
- banco único
- isolamento por tenant_id

Usuários
- PlatformUser
- OwnerUser
- Customer

Catálogo
- Product
- ProductVariant
- Category
- Tag
- Brand

Regras:

- preço pertence à ProductVariant
- estoque pertence à ProductVariant
- OrderItem guarda snapshot de preço

Checkout

pedido nasce após:

- escolha do frete
- clique em pagar

Pagamentos

gateway inicial:

Pagar.me

métodos:

- PIX
- cartão de crédito

Parcelamento:

até 12x

Pedido lifecycle:

pending_payment  
paid  
preparing  
shipped  
delivered  
canceled  

---

# PROMPT 3 — UI e design system

Stack UI:

Django Templates  
HTMX  
Alpine.js  
Tailwind CSS  

Documentação UI:

docs/ui/design-system.md  
docs/ui/component-library.md  
docs/ui/layout-and-spacing.md  
docs/ui/forms-and-validation.md  
docs/ui/interaction-patterns.md  
docs/ui/htmx-patterns.md  
docs/ui/states-and-feedback.md  
docs/ui/page-templates.md  

Estrutura de templates:

ui/templates/

layouts/  
shared/components/  
shared/forms/  
shared/partials/  
patterns/  
<module>/

Componentes reutilizáveis:

botões  
cards  
inputs  
selects  
badges  
alerts  
modals  
tables  
pagination  

Nunca duplicar HTML desnecessariamente.

---

# PROMPT 4 — módulos do sistema

accounts  
tenants  
catalog  
cart  
checkout  
orders  
payments  
shipping  
coupons  
reviews  
subscriptions  
notifications  
pages  
newsletter  
audit  
api-keys  

O agente deve:

- mapear responsabilidades
- identificar dependências
- identificar regras críticas

---

# PROMPT 5 — revisão geral

O agente deve responder:

1. resumo do produto
2. resumo da arquitetura
3. resumo da UI
4. entidades centrais
5. módulos críticos
6. regras que não podem ser quebradas

---

# PROMPT 6 — contrato operacional

Regras obrigatórias:

- seguir AGENTS.md
- seguir PRODUCT_RULES.md
- seguir docs/ui/*
- respeitar multi-tenant
- respeitar design system
- atualizar documentação quando necessário

---

# PROMPT 8 — arquitetura de código

Estrutura backend por módulo:

models.py

domain/
regras puras

application/
casos de uso

infrastructure/
integrações externas

interfaces/
views, api, admin

Views devem ser finas.

Lógica complexa deve ficar em application.

---

# PROMPT 9 — modelagem de dados

Banco:

PostgreSQL único

Multi-tenant:

tenant_id obrigatório

Regras:

ProductVariant contém preço e estoque

OrderItem contém snapshot de preço

Customer pertence ao tenant

Constraints por tenant:

slug único por tenant  
cupom único por tenant  

---

# PROMPT 10 — implementação de UI

Componentes reutilizáveis obrigatórios.

Não duplicar HTML.

Estados obrigatórios:

loading  
empty  
success  
error  

HTMX usado para:

filtros  
paginação  
modais  
carrinho  

---

# PROMPT 11 — API

API REST.

Endpoints:

/api/products  
/api/orders  
/api/customers  

Regras:

- paginação obrigatória
- filtros por querystring
- views finas
- lógica em application

---

# PROMPT 12 — pagamentos

Gateway:

Pagar.me

Métodos:

PIX  
cartão  

PIX depende de webhook.

Regras:

- idempotência
- PaymentTransaction registra eventos

---

# PROMPT 13 — performance

Evitar:

N+1 queries

Usar:

select_related  
prefetch_related  

Indexar:

tenant_id  
slug  
status  

Celery para:

emails  
webhooks  
tarefas pesadas

---

# PROMPT 14 — segurança

Proteções:

CSRF  
XSS  
SQL injection  
IDOR  

Nunca permitir acesso entre tenants.

Webhooks devem:

validar assinatura  
ser idempotentes

Nunca armazenar dados de cartão.

---

# PROMPT 15 — testes

Tipos de testes:

unit tests  
integration tests  

Fluxos críticos:

checkout  
pagamento  
pedido  
cupom  

Testes obrigatórios:

multi-tenant isolation

Testes de webhook devem validar:

idempotência  
status updates

---

# Objetivo final

Após executar esses prompts o agente deve:

- compreender profundamente o Hubx Market
- respeitar arquitetura
- respeitar regras de negócio
- respeitar design system
- evitar erros comuns de SaaS