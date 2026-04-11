# ERD

## 1. Visão geral do banco
- PostgreSQL único
- multi-tenant por `tenant_id`
- isolamento lógico
- foco em e-commerce SaaS

## 2. Agrupamento por domínio

### Plataforma
- Tenant
- Plan
- Subscription

### Identidade
- PlatformUser
- OwnerUser
- Customer
- CustomerAddress

### Catálogo
- Brand
- Category
- Tag
- Product
- ProductVariant
- ProductImage
- ProductCategory
- ProductTag

### Carrinho / Checkout
- Cart
- CartItem

### Pedidos / Pagamentos
- Order
- OrderItem
- OrderStatusHistory
- Payment
- PaymentTransaction

### Logística
- Shipment

### Marketing
- Coupon
- ProductReview
- NewsletterSubscriber
- Page

### Assinatura SaaS
- Subscription
- Invoice
- SubscriptionPayment

## 3. Relacionamentos principais
- Tenant 1:N OwnerUser
- Tenant 1:N Customer
- Tenant 1:N Product
- Product 1:N ProductVariant
- Product N:N Category
- Product N:N Tag
- Product 1:N ProductImage
- Customer 1:N CustomerAddress
- Customer 1:N Order
- Order 1:N OrderItem
- Order 1:1 Payment
- Order 1:1 Shipment
- Tenant 1:N Coupon
- Product 1:N Review
- Tenant 1:1 Subscription

## 4. Observações de modelagem
- preço pertence à ProductVariant
- estoque pertence à ProductVariant
- OrderItem guarda price_snapshot
- produto inativo não é deletado
- customer é isolado por tenant
- owner e customer são entidades diferentes
