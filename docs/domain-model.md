# Domain Model

Este documento descreve o modelo conceitual do Hubx Market.

## Plataforma
### Tenant
Representa uma loja no SaaS.

### Plan
Representa um plano comercial da plataforma.

### Subscription
Representa a assinatura SaaS da loja.

## Identidade
### PlatformUser
Usuário do painel da plataforma.

### OwnerUser
Usuário administrador da loja.
- pertence a um tenant
- é separado de `Customer` e `AccountProfile`
- pode ser usado como destinatário administrativo quando ativo e habilitado para notificações

### AccountProfile
Perfil persistido mínimo para identidade, contato e preferências da experiência de conta, com vínculo opcional para `Customer`.

### Customer
Comprador da loja, isolado por tenant, com base persistida mínima para identidade, contato e leitura operacional administrativa.
- também pode guardar flags operacionais leves para execução manual:
  - `marked_for_followup`
  - `marked_for_reengagement`
  - `marked_as_priority`

### CustomerAddress
Endereço do customer.

## Catálogo
### Brand
Marca do produto.

### Category
Categoria hierárquica.

### Tag
Marcação flexível para produto.

### Product
Entidade principal de catálogo.

### ProductVariant
SKU e unidade efetiva de venda.

### ProductImage
Imagem persistida mínima do produto, baseada em URL e ordenação simples para uso em storefront/admin.

## Compra
### Cart
Carrinho persistente do customer.

### CartItem
Item do carrinho ligado à variante.

### CheckoutSession
Snapshot transitório do checkout por tenant, com contato, entrega, métodos e totais.

### CheckoutSessionItem
Snapshot dos itens exibidos durante o checkout.
- também pode preservar `variant_sku` para manter o vínculo explícito com a unidade vendável escolhida

### CheckoutRecoveryEvent
Evento tenant-scoped gerado quando um `result` conhecido de recovery é exibido na página de checkout.
- preserva `result_code`, `family`, `severity`, `recovery_action`, `stage` e vínculo opcional com `CheckoutSession`
- não representa pagamento, pedido criado ou mutação transacional

### Order
Pedido materializado no checkout, com vínculo opcional para `Customer` e snapshots preservados de customer.
- também pode guardar `inventory_reserved_at` para registrar quando a baixa operacional de estoque já foi aplicada
- também pode guardar `inventory_recovered_at` para registrar quando a devolução operacional de estoque já foi aplicada
- também pode guardar `inventory_finalized_at` para registrar quando a reserva operacional já virou consumo final após entrega

### OrderItem
Snapshot do item comprado.
- também pode preservar `variant_sku` como snapshot explícito da variante comprada

### OrderStatusHistory
Histórico leve de transições e eventos operacionais relevantes do pedido, usado para enriquecer timelines administrativas, com atribuição opcional de origem/contexto.

## Pagamento e logística
### Payment
Pagamento do pedido.

### PaymentTransaction
Eventos e transações do gateway.

### Shipment
Informações de envio e rastreio.
- pertence a um tenant
- vincula um pedido a status logístico, tracking code, tracking URL e carrier
- é a base para eventos `shipment.sent` e `shipment.delivered`
- possui `ShipmentStatusHistory` para registrar transições operacionais por tenant

### ShippingProviderSettings
Configuração tenant-scoped do provider de tracking.
- define provider ativo, base URL, token e timeout
- quando ausente/inativo, shipping usa provider manual/local
- possui `ShippingProviderSettingsHistory` para auditoria de alterações operacionais

## Marketing e conteúdo
### Coupon
Cupom de desconto.

### ProductReview
Avaliação de produto.

### NewsletterSubscriber
Assinatura de newsletter.

### Page
Página institucional da loja.

## Operação
### AuditLog
Registro de ações administrativas.

### EmailLog
Registro de envios de e-mail.
- pertence a um tenant
- guarda snapshot de evento, intent, recipient e copy
- começa como unidade planejada antes de worker/provider real

### ApiKey
Chave da API pública futura.

