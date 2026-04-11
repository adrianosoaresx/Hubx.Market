# AGENTS.md

Este arquivo orienta **agentes de IA e contribuidores** sobre como trabalhar no repositório do **Hubx Market**.

Ele funciona como **ponto de entrada oficial para entendimento do projeto**.

Antes de implementar qualquer tarefa, agentes **devem ler a documentação abaixo**.

---

# Documentação obrigatória

Agentes devem consultar:

Core

- docs/codex-knowledge-transfer.md
- docs/ai-rules.md
- docs/engineering-principles.md
- docs/repository-guidelines.md
- docs/ai-task-template.md

Arquitetura

- docs/architecture-overview.md
- docs/context-map.md
- docs/module-boundaries.md
- docs/events-map.md
- docs/request-lifecycle.md
- docs/scalability-strategy.md
- docs/modules-index.md

Domínio e dados

- docs/domain-model.md
- docs/data/erd.md

Produto e marca

- docs/brand.md

UI

- docs/ui/design-system.md
- docs/ui/component-library.md
- docs/ui/layout-and-spacing.md
- docs/ui/forms-and-validation.md
- docs/ui/interaction-patterns.md
- docs/ui/htmx-patterns.md
- docs/ui/states-and-feedback.md
- docs/ui/page-templates.md

Esses documentos descrevem:

- arquitetura do sistema
- regras de domínio
- modelagem de dados
- padrões de interface
- comunicação entre módulos
- eventos internos
- ciclo de requisição
- estratégia de escalabilidade

---

# Projeto

Hubx Market é uma **plataforma SaaS de e-commerce multi-tenant**.

Cada loja roda em subdomínio próprio:

store.hubx.market

Cada tenant possui:

- catálogo próprio
- clientes próprios
- pedidos próprios
- pagamentos próprios
- configurações próprias

---

# Estrutura do repositório

backend/   → Django, DRF, Celery, regras de negócio  
ui/        → Django Templates, HTMX, Alpine, Tailwind  
infra/     → docker, compose, deploy  
docs/      → arquitetura, domínio, dados, módulos, UI

---

# Stack oficial

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
- S3 / R2
- Prometheus
- Grafana

---

# Regras obrigatórias

## Multi-tenant

- Todo dado de loja deve respeitar `tenant_id`
- Tenant é resolvido por **subdomínio**
- Nunca permitir acesso cruzado entre tenants

## Identidade

- `OwnerUser` e `Customer` são entidades diferentes
- `Customer` pertence a um tenant específico

## Catálogo

- Preço pertence à `ProductVariant`
- Estoque pertence à `ProductVariant`
- `Product` não é unidade de venda

## Pedidos

- `OrderItem` guarda `price_snapshot`
- Pedido nasce somente após escolha do frete e clique em pagar
- Estoque baixa apenas após pagamento confirmado

## Produtos

- Produto inativo **não deve ser deletado**

---

# Arquitetura de código

Backend segue arquitetura modular:

models.py
domain/
application/
infrastructure/
interfaces/

Responsabilidades:

models.py → persistência ORM  
domain → regras puras de negócio  
application → casos de uso  
infrastructure → integrações externas  
interfaces → views / API / admin

Regras:

- Views devem ser **finas**
- Lógica de negócio deve ficar em **application/** ou **domain/**
- Evitar lógica de negócio em controllers

---

# Comunicação entre módulos

As fronteiras entre módulos estão definidas em:

docs/module-boundaries.md

Regras principais:

- chamar regras por **application services**
- evitar importar detalhes internos de outros módulos
- não duplicar regras de negócio
- preferir eventos para efeitos colaterais

---

# Arquitetura orientada a eventos

Eventos do sistema estão definidos em:

docs/events-map.md

Exemplos:

order.created  
payment.paid  
shipment.sent  

Eventos são usados para:

- tarefas assíncronas
- integração entre módulos
- notificações
- auditoria

---

# Ciclo de requisição

Fluxo interno definido em:

docs/request-lifecycle.md

Fluxo padrão:

HTTP Request
→ Middleware
→ Tenant Resolution
→ View
→ Application Service
→ Domain Logic
→ Persistence
→ Events
→ Response

---

# Escalabilidade

Estratégia documentada em:

docs/scalability-strategy.md

Princípios:

- escalar horizontalmente
- evitar gargalos centralizados
- usar cache e workers assíncronos
- manter aplicação stateless

---

# Padrões de interface

Toda UI deve seguir documentação em:

docs/ui/

Especialmente:

- design-system
- component-library
- layout-and-spacing
- forms-and-validation
- interaction-patterns
- htmx-patterns
- states-and-feedback
- page-templates

Regras:

- reutilizar componentes
- evitar HTML duplicado
- respeitar estados de UI (loading, empty, error)

---

# HTMX

HTMX deve ser usado para:

- filtros
- paginação
- modais
- atualização parcial
- carrinho

Evitar HTMX para lógica complexa.

---

# Antes de implementar qualquer tarefa

Agentes devem sempre responder:

1. Qual módulo é responsável por essa regra?
2. Existe documentação sobre essa área?
3. Isso respeita multi-tenant?
4. Isso quebra alguma fronteira de módulo?
5. Isso afeta eventos do sistema?
6. Isso afeta o ciclo de requisição?
7. Isso exige atualização de documentação?

---

# Documentação obrigatória

Mudanças estruturais devem atualizar:

- docs/architecture-overview.md
- docs/domain-model.md
- docs/data/erd.md
- docs/context-map.md
- docs/module-boundaries.md
- docs/events-map.md
- docs/request-lifecycle.md
- docs/scalability-strategy.md
- docs/modules-index.md
- docs/modules/*
- docs/brand.md
- docs/ai-task-template.md
- docs/ui/*

---

# Registro de decisões

Decisões arquiteturais importantes devem ser registradas em:

DECISIONS.md

---

# Objetivo

Manter o Hubx Market:

- consistente
- modular
- escalável
- seguro
- previsível para agentes de IA
