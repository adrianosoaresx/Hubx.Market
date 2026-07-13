
# Context Map — Hubx Market

Este documento descreve o **mapa de contexto (Context Map)** do Hubx Market.

O objetivo é organizar o domínio do sistema em **blocos bem definidos**, permitindo:

- melhor compreensão arquitetural
- modularização clara
- evolução segura do sistema
- colaboração eficiente entre desenvolvedores e agentes de IA

---

# Visão geral

Hubx Market é uma plataforma **SaaS de e-commerce multi-tenant**.

Cada loja opera isoladamente dentro do sistema.

Exemplo:

lojax.hubx.market  
minhaloja.hubx.market  

Cada tenant possui:

- catálogo próprio
- clientes próprios
- pedidos próprios
- pagamentos próprios
- configurações próprias

---

# Macro Domínios

O sistema é dividido em **3 grandes domínios**.

```
Platform
Commerce
Engagement
```

---

# Platform Domain

Responsável pela **infraestrutura do SaaS**.

Inclui:

- gerenciamento de tenants
- branding institucional leve da storefront, incluindo cor primária de conversão
- controle de usuários da plataforma
- assinaturas do SaaS
- billing da plataforma
- observabilidade
- controle administrativo

## Submódulos

```
tenants
accounts
subscriptions
platform-admin
audit
api-keys
assistant
```

## Responsabilidades

- criar novas lojas
- configurar identidade institucional básica da loja
- gerenciar owners
- controlar planos SaaS
- expor contrato público de planos com limites de produtos, pedidos pagos, take rate, mínimo mensal e elegibilidade de self-service
- gerenciar cupons comerciais platform-scope para planos SaaS
- capturar intenções públicas de aquisição SaaS
- provisionar signup self-service controlado em `/plans/signup/` quando a feature flag e o controle de acesso estiverem ativos, criando tenant em manutenção para plano elegível sem método obrigatório, com provider-alvo Asaas sem capturar cartão/token
- auditoria do sistema
- integração administrativa
- assistente operacional para owners/admins baseado na documentação interna

---

# Commerce Domain

Responsável pelo **motor de e-commerce**.

Este é o núcleo do sistema.

## Submódulos

```
catalog
customers
cart
checkout
orders
payments
shipping
coupons
```

## Responsabilidades

### Catalog
- produtos
- variantes
- categorias
- marcas
- imagens
- tags

### Customers
- clientes da loja
- endereços
- histórico de compras

### Cart
- carrinho de compras
- itens do carrinho
- cálculo de subtotal

### Checkout
- seleção de frete
- cálculo final
- criação de pedido
- analytics leve de recovery exibido ao cliente, sempre tenant-scoped

### Orders
- lifecycle do pedido
- histórico
- status

### Payments
- integração com gateway
- transações
- webhooks

### Shipping
- cálculo de frete
- rastreamento
- integração com transportadoras

### Coupons
- cupons de desconto
- regras promocionais

---

# Engagement Domain

Responsável pela **interação e retenção de clientes**.

## Submódulos

```
reviews
newsletter
notifications
pages
marketing
```

## Responsabilidades

### Reviews
- avaliações de produtos

### Newsletter
- inscrição em newsletter tenant-scoped
- opt-in público com consentimento
- base inicial para retenção, sem campanhas automáticas no primeiro corte

### Notifications
- notificações do sistema
- emails

### Pages
- páginas institucionais tenant-owned
- SEO básico do storefront
- publicação controlada por status

### Marketing
- campanhas
- promoções

---

# Fluxo principal de venda

Fluxo principal do sistema:

```
Catalog
   ↓
Product Page
   ↓
Cart
   ↓
Checkout
   ↓
Payment
   ↓
Order Created
   ↓
Shipping
   ↓
Delivery
```

---

# Dependências entre domínios

```
Platform
   ├─ Tenants
   ├─ Accounts
   └─ Audit

Commerce
   ├─ Catalog
   ├─ Customers
   ├─ Cart
   ├─ Checkout
   ├─ Orders
   ├─ Payments
   └─ Shipping

Engagement
   ├─ Reviews
   ├─ Newsletter
   └─ Notifications
```

---

# Regras importantes de domínio

Multi-tenant:

- todo dado deve respeitar `tenant_id`
- isolamento entre lojas é obrigatório

Catálogo:

- preço pertence a `ProductVariant`
- estoque pertence a `ProductVariant`
- CRUD administrativo de produto pertence a `catalog`; criação/edição gravam `Product` e variante padrão, e remoção operacional é desativação sem delete físico.

Pedidos:

- `OrderItem` guarda snapshot de preço
- estoque baixa apenas após pagamento

Pagamentos:

- PIX depende de webhook
- eventos de pagamento devem ser idempotentes

---

# Objetivo do Context Map

Este documento permite:

- entender rapidamente a arquitetura do domínio
- orientar decisões arquiteturais
- ajudar agentes de IA a localizar responsabilidades
- manter separação clara entre domínios
