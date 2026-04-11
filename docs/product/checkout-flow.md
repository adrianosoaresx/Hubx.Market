# Checkout Flow

## Fluxo oficial do checkout
1. customer autenticado
2. carrinho persistente carregado
3. seleção ou cadastro de endereço
4. cálculo de frete por API
5. seleção do frete
6. aplicação opcional de cupom
7. seleção do meio de pagamento
8. clique em pagar
9. criação de Order
10. criação de Payment
11. envio ao gateway
12. atualização de status por resposta síncrona ou webhook

## Regras
- pedido só nasce após escolha do frete e clique em pagar
- estoque só baixa após pagamento confirmado
- order item guarda snapshot de preço
