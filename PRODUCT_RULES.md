# PRODUCT_RULES.md

## Regras de negócio principais

### Multi-tenant
- tenant resolvido por subdomínio
- todas as entidades de loja respeitam `tenant_id`
- customer é isolado por tenant
- owner da loja é distinto de customer
- onboarding cria tenant + owner no mesmo fluxo

### Catálogo
- produto pode pertencer a múltiplas categorias
- produto pode ter múltiplas tags
- produto tem marca
- produto pode ter múltiplas imagens
- produto pode ficar inativo sem ser deletado
- produto usa slug amigável

### Produto e estoque
- preço pertence à `ProductVariant`
- preço promocional pertence à `ProductVariant`
- estoque pertence à `ProductVariant`
- pode existir estoque ilimitado
- produto sem estoque continua visível como esgotado
- estoque baixa após pagamento confirmado

### Carrinho e checkout
- carrinho é persistente
- customer precisa de conta para comprar
- checkout exige endereço e frete
- pedido nasce após escolha do frete e clique em pagar

### Pedido
Status do pedido:
- `pending_payment`
- `paid`
- `preparing`
- `shipped`
- `delivered`
- `canceled`

### Pagamentos
- gateway inicial: Pagar.me
- meios no MVP: PIX + cartão de crédito
- cartão aceita parcelamento até 12x
- PIX depende de webhook
- pagamentos precisam de idempotência

### Shipping
- frete por API
- shipment com tracking code no MVP

### Marketing
- cupons existem no MVP
- reviews existem no MVP
- newsletter existe no MVP
- produtos relacionados existem no MVP
- produtos em destaque existem no MVP

### SaaS
- existe superadmin da plataforma
- existem planos de assinatura
- assinatura SaaS usa Pagar.me
- loja pode entrar em manutenção
