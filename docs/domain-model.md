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

### Customer
Comprador da loja.

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
Imagem do produto.

## Compra
### Cart
Carrinho persistente do customer.

### CartItem
Item do carrinho ligado à variante.

### Order
Pedido materializado no checkout.

### OrderItem
Snapshot do item comprado.

## Pagamento e logística
### Payment
Pagamento do pedido.

### PaymentTransaction
Eventos e transações do gateway.

### Shipment
Informações de envio e rastreio.

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

### ApiKey
Chave da API pública futura.
