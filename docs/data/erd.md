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
- AccountProfile
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
- CheckoutSession
- CheckoutSessionItem
- CheckoutRecoveryEvent

### Pedidos / Pagamentos
- Order
- OrderItem
- OrderStatusHistory
- Payment
- PaymentTransaction

### Logística
- Shipment
- ShipmentStatusHistory
- ShippingProviderSettings
- ShippingProviderSettingsHistory

### Marketing
- Coupon
- ProductReview
- NewsletterSubscriber
- Page

### Notificações
- EmailLog

### Assinatura SaaS
- Subscription
- Invoice
- SubscriptionPayment

## 3. Relacionamentos principais
- Tenant 1:N OwnerUser
- Tenant 1:N AccountProfile
- Tenant 1:N Customer
- Customer 1:N AccountProfile (opcional)
- Tenant 1:N Product
- Product 1:N ProductVariant
- Product N:N Category
- Product N:N Tag
- Product 1:N ProductImage
- Customer 1:N CustomerAddress
- Tenant 1:N CheckoutSession
- CheckoutSession 1:N CheckoutSessionItem
- Tenant 1:N CheckoutRecoveryEvent
- CheckoutSession 1:N CheckoutRecoveryEvent (opcional; eventos podem existir sem sessão vinculada)
- Customer 1:N Order (opcional e preferencial para integrações da área logada)
- Order 1:N OrderItem
- Order 1:N OrderStatusHistory
- Order 1:1 Payment
- Order 1:1 Shipment
- Shipment 1:N ShipmentStatusHistory
- Tenant 1:1 ShippingProviderSettings
- ShippingProviderSettings 1:N ShippingProviderSettingsHistory
- Tenant 1:N Coupon
- Tenant 1:N EmailLog
- Product 1:N Review
- Tenant 1:1 Subscription

## 4. Observações de modelagem
- preço pertence à ProductVariant
- estoque pertence à ProductVariant
- checkout pode persistir snapshots transitórios antes da criação do pedido
- `CheckoutSessionItem` pode preservar `variant_sku` como vínculo explícito com a variante escolhida
- OrderItem guarda `price_snapshot`
- `OrderItem` pode preservar `variant_sku` como snapshot explícito da variante comprada
- `Order` pode guardar `inventory_reserved_at` para indicar quando a baixa operacional de estoque já foi aplicada após o pagamento
- `Order` pode guardar `inventory_recovered_at` para indicar quando a devolução operacional de estoque já foi aplicada após cancelamento seguro
- `Order` pode guardar `inventory_finalized_at` para indicar quando a reserva operacional já foi consumida de forma final após a entrega
- produto inativo não é deletado
- customer é isolado por tenant
- `Customer` já possui base persistida mínima para leituras administrativas de list/detail
- `Customer` também pode guardar flags operacionais leves para execução manual no admin (`marked_for_followup`, `marked_for_reengagement`, `marked_as_priority`)
- `CustomerAddress` passa a existir como base persistida mínima para leituras futuras da área logada
- `CustomerAddress` passa a existir como base persistida mínima para leituras futuras da área logada
- `AccountProfile.customer` e `Order.customer` são vínculos opcionais e backward-compatible; quando ausentes, o sistema ainda pode operar via `tenant + email`
- `OrderStatusHistory` pode guardar atribuição leve de origem/contexto (`source_type`, `source_label`, `actor_label`) sem virar um framework completo de auditoria
- `ProductImage` fornece mídia mínima persistida via URL, sem introduzir pipeline de upload/CDN
- owner e customer são entidades diferentes
- `AccountProfile` serve como base de experiência de conta, não como substituto de `Customer`
- `EmailLog` é tenant-scoped e usa `recipient_delivery_key` para deduplicar uma unidade de entrega por destinatário/canal

