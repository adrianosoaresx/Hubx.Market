# Frete e entregas

## Quando o frete entra no checkout

O pedido só deve ser criado depois que o cliente escolhe uma opção de frete válida.

Sem frete escolhido, o checkout não deve avançar para pagamento final.

## Como acompanhar entrega

Use a área de entregas/frete no admin, quando disponível para o pedido.

O Hubx separa pedido, pagamento e entrega para manter a operação auditável.

## O que é shipment

`Shipment` guarda informações de envio e rastreio de um pedido.

Pode incluir status logístico, código de rastreio, URL de rastreio e transportadora.

## Quando marcar pedido como enviado

Marque como enviado somente quando a remessa realmente tiver sido despachada ou quando houver confirmação operacional equivalente.

## Boas práticas

- Confira pagamento antes de envio.
- Mantenha código de rastreio atualizado.
- Use URL de rastreio quando existir.
- Não misture status de pagamento com status de entrega.

