
# AI Task Template — Hubx Market

Este documento define um **template padrão para solicitar tarefas a agentes de IA**
(Codex, ChatGPT, etc.) no projeto Hubx Market.

O objetivo é garantir que a IA:

- entenda o contexto correto
- respeite a arquitetura do sistema
- não quebre regras de domínio
- produza código consistente com o projeto

---

# Template de tarefa

Sempre que pedir uma tarefa para a IA, use a seguinte estrutura:

## Task
Descrição clara do que deve ser implementado.

Exemplo:
Criar funcionalidade de cadastro de produto.

---

## Context
Explicar o cenário da tarefa.

Exemplo:
Estamos implementando o módulo de catálogo do Hubx Market.
Produtos pertencem a um tenant e possuem variantes.

---

## Affected Modules
Quais módulos do sistema serão afetados.

Exemplo:

catalog  
tenants  
reviews

---

## Domain Rules
Regras de domínio relevantes.

Exemplo:

- preço pertence à ProductVariant
- estoque pertence à ProductVariant
- produto pertence a um tenant
- produto inativo não deve ser deletado

---

## UI Impact
Descrever impacto na interface.

Exemplo:

- página de criação de produto
- formulário de variantes
- lista de produtos do tenant

---

## Data Impact
Mudanças no modelo de dados.

Exemplo:

Novas entidades:

Product
ProductVariant

Campos importantes:

tenant_id
price
stock

---

## API Impact
Se a tarefa envolve endpoints.

Exemplo:

POST /api/products
GET /api/products

---

## Events
Eventos que podem ser emitidos.

Exemplo:

product.created
product.updated
product.deactivated

---

## Expected Output
Descrever o que a IA deve gerar.

Exemplo:

- models Django
- application services
- views
- templates
- testes básicos

---

# Boas práticas ao pedir tarefas

Sempre:

- especificar módulo
- citar regras de domínio
- citar documentos relevantes
- citar impacto em UI
- citar impacto em dados

Evitar pedidos vagos como:

"crie um sistema de pedidos"

Prefira:

"implemente o módulo orders seguindo docs/module-boundaries.md e docs/request-lifecycle.md"

---

# Documentação relacionada

Antes de executar tarefas, a IA deve considerar:

docs/AGENTS.md
docs/implementation-inventory.md
docs/context-map.md
docs/module-boundaries.md
docs/events-map.md
docs/request-lifecycle.md
docs/scalability-strategy.md

---

# Objetivo

Garantir que tarefas executadas por IA mantenham:

- consistência arquitetural
- qualidade de código
- respeito às regras do domínio
- integração correta com o restante do sistema
