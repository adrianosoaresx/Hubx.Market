
# Architecture Overview — Hubx Market

Este documento apresenta uma **visão geral da arquitetura do Hubx Market**.

O objetivo é permitir que desenvolvedores e agentes de IA entendam rapidamente:

- a estrutura do sistema
- os domínios principais
- os módulos centrais
- o fluxo de dados
- a infraestrutura

---

# Visão geral do sistema

Hubx Market é uma **plataforma SaaS de e-commerce multi-tenant**.

Cada loja funciona de forma isolada dentro do sistema e é acessada por subdomínio:

exemplo:

lojax.hubx.market

No contrato atual, esse acesso por subdomínio é também a única forma oficial de resolução HTTP de tenant. O campo `custom_domain` já existe no modelo de `tenants`, mas permanece como readiness de domínio até que exista suporte explícito no middleware e nas regras operacionais associadas.

Cada tenant possui:

- catálogo próprio
- clientes próprios
- pedidos próprios
- pagamentos próprios
- configurações próprias

---

# Camadas do sistema

A arquitetura segue um modelo em camadas:

UI Layer  
→ Application Layer  
→ Domain Layer  
→ Infrastructure Layer

---

# UI Layer

Responsável pela interface do usuário.

Tecnologias:

- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

Funções:

- renderização de páginas
- interação dinâmica via HTMX
- formulários
- componentes reutilizáveis

Documentação:

docs/ui/

---

# Application Layer

Camada responsável por **casos de uso do sistema**.

Local típico:

application/

Responsabilidades:

- orquestrar fluxos de negócio
- coordenar módulos
- iniciar eventos

Exemplo:

checkout/create_order

---

# Domain Layer

Camada que contém **regras de negócio puras**.

Local típico:

domain/

Exemplos:

- cálculo de preço
- validação de cupom
- mudança de status de pedido

Essa camada deve ser isolada de infraestrutura.

---

# Infrastructure Layer

Responsável por integrações externas.

Exemplos:

- gateway de pagamento
- envio de emails
- storage
- serviços externos

Local típico:

infrastructure/

---

# Domínios principais

O sistema é dividido em três domínios principais.

Platform  
Commerce  
Engagement

---

# Platform Domain

Responsável pela infraestrutura do SaaS.

Módulos principais:

tenants  
accounts  
subscriptions  
audit  
api-keys

Responsabilidades:

- gerenciamento de lojas
- autenticação de usuários administrativos
- planos SaaS
- auditoria

---

# Commerce Domain

Responsável pelo motor de e-commerce.

Módulos principais:

catalog  
customers  
cart  
checkout  
orders  
payments  
shipping  
coupons

Fluxo principal:

Catalog  
→ Cart  
→ Checkout  
→ Payment  
→ Order  
→ Shipping

---

# Engagement Domain

Responsável pela interação com clientes.

Módulos principais:

reviews  
newsletter  
notifications  
pages

Funções:

- avaliações
- emails
- notificações
- páginas institucionais

---

# Arquitetura de dados

Banco principal:

PostgreSQL

Modelo:

- banco único
- multi-tenant por tenant_id
- isolamento lógico

Regras importantes:

- todo registro deve ter tenant_id
- consultas devem filtrar tenant_id

Documentação:

docs/data/erd.md

---

# Infraestrutura

Componentes principais:

Backend

Django + Django REST Framework

Workers

Celery

Cache / fila

Redis

Banco

PostgreSQL

Storage

S3 ou Cloudflare R2

Observabilidade

Prometheus  
Grafana

---

# Comunicação entre módulos

Comunicação preferencial:

Application Services

Ou via:

Domain Events

Eventos documentados em:

docs/events-map.md

---

# Fluxo de requisição

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

Documentação detalhada:

docs/request-lifecycle.md

---

# Escalabilidade

A aplicação foi projetada para:

- escalar horizontalmente
- manter serviços stateless
- usar workers para tarefas pesadas

Estratégia completa:

docs/scalability-strategy.md

---

# Documentação relacionada

Arquitetura:

docs/context-map.md  
docs/module-boundaries.md  
docs/events-map.md  
docs/request-lifecycle.md  
docs/scalability-strategy.md  

Domínio:

docs/domain-model.md  
docs/data/erd.md  

Interface:

docs/ui/

---

# Objetivo

Garantir que qualquer pessoa ou agente de IA possa entender rapidamente:

- como o Hubx Market é estruturado
- como os módulos se relacionam
- como novas funcionalidades devem ser implementadas
