
# Request Lifecycle — Hubx Market

Este documento descreve o **ciclo completo de uma requisição** dentro do Hubx Market.

O objetivo é padronizar como requests HTTP percorrem o sistema, desde a entrada
até a resposta final, garantindo consistência arquitetural.

---

# Visão geral

Fluxo padrão:

HTTP Request
→ Middleware
→ Tenant Resolution
→ View / Controller
→ Application Service
→ Domain Logic
→ Persistence
→ Domain Events
→ Response

---

# 1. HTTP Request

Uma requisição chega ao sistema através de:

- navegador (UI)
- API externa
- webhook de integração

Exemplos:

GET /products
POST /checkout
POST /api/orders

---

# 2. Middleware

Antes de chegar à view, middlewares executam tarefas transversais.

Exemplos:

- logging
- autenticação
- rate limit
- tenant resolution preliminar

---

# 3. Tenant Resolution

O tenant é identificado, no contrato atual, pelo **subdomínio**.

Exemplo:

store.hubx.market

O sistema resolve:

tenant_id

Esse tenant passa a acompanhar todo o fluxo da requisição.

Regras:

- nenhum dado pode ser acessado sem tenant
- isolamento entre tenants é obrigatório
- hosts fora de `*.hubx.market` não resolvem tenant por padrão neste estágio
- `custom_domain` ainda não participa da resolução HTTP; quando aparecer no modelo, ele não deve ser interpretado como capability ativa sem suporte explícito no middleware

---

# 4. View / Controller

Responsável por:

- validar entrada
- chamar serviço de aplicação
- preparar resposta

Views devem ser **finas**.

Evitar lógica de negócio em views.

---

# 5. Application Service

Camada responsável por orquestrar casos de uso.

Exemplo:

checkout/create_order.py

Responsabilidades:

- coordenar módulos
- aplicar regras de fluxo
- iniciar eventos

Regra adicional para superfícies tenant-owned:

- quando o middleware já resolveu a loja, `tenant_id` deve seguir explicitamente da `view` para os services de `application/`
- query/command services não devem voltar a inferir tenant por contexto global se ele já estiver disponível na requisição
- quando um fluxo ainda operar sem tenant explícito por compatibilidade, isso deve ser tratado como exceção documentada, não como padrão implícito

---

# 6. Domain Logic

Contém regras puras de negócio.

Exemplo:

- cálculo de preço
- validação de cupom
- mudança de status de pedido

Essa camada deve ser isolada de infraestrutura.

---

# 7. Persistence

Camada responsável por persistência via ORM.

Local típico:

models.py

Regras:

- sempre incluir tenant_id
- evitar queries pesadas sem índice

---

# 8. Domain Events

Após ações importantes, eventos podem ser emitidos.

Exemplo:

order.created
payment.paid
shipment.sent

Eventos permitem:

- desacoplamento
- tarefas assíncronas
- integrações externas

---

# 9. Response

Por fim, a resposta retorna ao cliente.

Tipos comuns:

- HTML (UI)
- JSON (API)
- redirect

---

# Fluxo exemplo: criação de pedido

Request:

POST /checkout

Fluxo:

Request
→ Middleware
→ Tenant resolution
→ Checkout view
→ Checkout application service
→ Domain validation
→ Order persistence
→ order.created event
→ Response

---

# Fluxo exemplo: webhook de pagamento

Request:

POST /payments/webhook

Fluxo:

Webhook request
→ Middleware
→ Signature validation
→ Payment service
→ Update payment status
→ Emit payment.paid event
→ Order update
→ Response 200

---

# Boas práticas

- manter views simples
- mover lógica para application/domain
- emitir eventos para efeitos colaterais
- respeitar isolamento multi-tenant
- evitar acesso cruzado entre módulos

---

# Objetivo

Padronizar o fluxo interno do sistema para:

- previsibilidade arquitetural
- facilidade de manutenção
- integração com agentes de IA
