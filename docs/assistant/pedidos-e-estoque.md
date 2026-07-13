# Pedidos e estoque

## Quando um pedido nasce

O pedido nasce somente depois que o cliente escolhe frete, escolhe pagamento e clica para pagar no checkout.

Carrinho e checkout ainda não são pedido.

## Quando o estoque baixa

O estoque baixa apenas após pagamento confirmado.

Isso evita consumir estoque para carrinhos abandonados, sessões incompletas ou pagamentos que ainda não foram confirmados.

## Pedido pendente já baixa estoque?

Não. Pedido pendente ainda não deve baixar estoque.

O estoque só deve ser consumido quando o pagamento for confirmado com segurança.

Enquanto o pagamento estiver pendente, acompanhe o pedido e aguarde a confirmação antes de separar ou enviar o produto.

## Por que o pedido guarda snapshot de preço

Cada `OrderItem` guarda o preço usado no momento da compra.

Se o lojista alterar o preço do produto depois, o pedido antigo continua mostrando o valor correto da venda original.

## Como acompanhar pedidos

Use a área de pedidos no admin em `/ops/orders/`.

Ali o admin acompanha status, histórico e ações operacionais disponíveis para o perfil atual.

## O que significa pagamento pendente

Pagamento pendente significa que o pedido ou tentativa de pagamento ainda aguarda confirmação do provider ou retorno seguro por webhook.

Não trate retorno visual do cliente como confirmação definitiva de pagamento.

## Posso preparar pedido com pagamento pendente?

Evite preparar como venda concluída.

Você pode acompanhar o pedido, mas a preparação definitiva deve esperar pagamento confirmado para evitar separação indevida de estoque.

## Boas práticas para operação de pedidos

- Confira status antes de separar o produto.
- Não altere estoque manualmente para pedidos pendentes.
- Use histórico e auditoria para entender mudanças.
- Espere confirmação de pagamento antes de iniciar preparação definitiva.
