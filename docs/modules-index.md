
# Modules Index — Hubx Market

Este documento funciona como **índice oficial de todos os módulos do Hubx Market**.

Ele ajuda desenvolvedores e agentes de IA a:

- localizar rapidamente responsabilidades
- entender dependências entre módulos
- identificar entidades principais
- descobrir eventos e APIs relacionadas

---

# Estrutura geral

O sistema é organizado em três grandes domínios:

Platform
Commerce
Engagement

---

# Platform Domain

Infraestrutura do SaaS.

## tenants

Responsabilidade:
Gerenciar lojas (tenants) e resolução por subdomínio.

Entidades principais:
Tenant

Eventos:
tenant.created

Dependências:
accounts  
subscriptions

---

## accounts

Responsabilidade:
Gerenciar autenticação e usuários administrativos da loja.

Entidades principais:
AccountProfile
OwnerUser

Dependências:
tenants

---

## subscriptions

Responsabilidade:
Gerenciar planos e assinaturas SaaS da plataforma.

Entidades principais:
Subscription

Eventos:
subscription.activated  
subscription.canceled

Dependências:
tenants

---

## audit

Responsabilidade:
Registrar eventos auditáveis do sistema.

Entidades principais:
AuditLog

Dependências:
todos os módulos (apenas leitura de eventos)

---

## api-keys

Responsabilidade:
Gerenciar chaves de integração para API pública.

Entidades principais:
ApiKey

Dependências:
tenants

---

# Commerce Domain

Motor principal de e-commerce.

## catalog

Responsabilidade:
Gerenciar produtos e estrutura de catálogo.

Entidades principais:
Product  
ProductVariant  
Category  
Brand  
Tag  
ProductImage

Eventos:
product.created  
product.updated

Dependências:
tenants

---

## customers

Responsabilidade:
Gerenciar compradores e endereços.

Entidades principais:
Customer  
CustomerAddress

Dependências:
tenants

---

## cart

Responsabilidade:
Gerenciar carrinho de compras.

Entidades principais:
Cart  
CartItem

Eventos:
cart.updated

Dependências:
catalog  
customers

---

## checkout

Responsabilidade:
Orquestrar fluxo de finalização da compra.

Entidades principais:
CheckoutSession
CheckoutSessionItem
CheckoutRecoveryEvent

Dependências:
cart  
shipping  
coupons  
orders  
payments

---

## orders

Responsabilidade:
Gerenciar pedidos e lifecycle.

Entidades principais:
Order  
OrderItem

Eventos:
order.created  
order.status_changed

Dependências:
customers  
catalog  
payments  
shipping

---

## payments

Responsabilidade:
Integração com gateway e gerenciamento de transações.

Entidades principais:
Payment  
PaymentTransaction

Eventos:
payment.created  
payment.paid  
payment.failed  
payment.refunded

Dependências:
orders

---

## shipping

Responsabilidade:
Gerenciar frete e remessas.

Entidades principais:
Shipment

Eventos:
shipment.created  
shipment.sent  
shipment.delivered

Dependências:
orders  
customers

---

## coupons

Responsabilidade:
Gerenciar cupons e descontos.

Entidades principais:
Coupon

Dependências:
checkout  
orders

---

# Engagement Domain

Recursos de interação e retenção.

## reviews

Responsabilidade:
Avaliações de produtos.

Entidades principais:
Review

Eventos:
review.created

Dependências:
catalog  
customers

---

## newsletter

Responsabilidade:
Gerenciar inscrição em newsletter.

Entidades principais:
NewsletterSubscriber

Eventos:
newsletter.subscribed

Dependências:
tenants

---

## notifications

Responsabilidade:
Envio de notificações e emails.

Entidades principais:
Notification

Consumidores de eventos:
order.created  
payment.paid  
shipment.sent

Dependências:
orders  
payments  
shipping

---

## pages

Responsabilidade:
Páginas institucionais da loja.

Entidades principais:
Page

Dependências:
tenants

---

# Como usar este documento

Antes de implementar qualquer funcionalidade:

1. Identifique o módulo responsável.
2. Verifique entidades e eventos do módulo.
3. Consulte docs/module-boundaries.md.
4. Consulte docs/events-map.md.
5. Para operação/produção, consulte docs/operational-runbooks.md.

---

# Objetivo

Facilitar navegação arquitetural do Hubx Market e garantir que novos desenvolvimentos respeitem a organização modular do sistema.
