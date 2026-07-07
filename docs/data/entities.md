# Entities

## Tenant
Loja do SaaS. Identificada por slug/subdomínio.
Guarda branding leve da loja, incluindo `logo_url`, `conversion_primary_color` e campos `storefront_hero_*`.

## OwnerUser
Usuário administrativo da loja.

## Customer
Comprador da loja. Isolado por tenant.

## Product
Entidade principal do catálogo.

## ProductVariant
SKU com preço, promoção e estoque.

## Order
Pedido formal criado após checkout.

## Payment
Pagamento associado ao pedido.

## Shipment
Envio associado ao pedido.

## Coupon
Desconto por código.

## ProductReview
Avaliação do produto.

## Subscription
Assinatura do plano SaaS.
