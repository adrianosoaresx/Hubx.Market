# Pagamentos

## Como o Hubx confirma pagamento

Pagamentos são confirmados por integração com provider e webhooks autenticados.

O retorno de uma página hospedada pode ajudar o cliente, mas não substitui a confirmação segura do webhook.

## O que é tentativa de pagamento

`PaymentAttempt` representa uma tentativa de pagamento de um pedido.

Ela guarda provider, valor, status, referência externa e trilha operacional da tentativa.

## O que acontece quando o pagamento é confirmado

Quando o pagamento é confirmado:

- o pedido pode avançar para pago;
- o estoque é baixado de forma operacional;
- a taxa Hubx pode ser registrada no ledger;
- notificações planejadas podem ser criadas.

## Como lidar com pagamento falho

Pagamento falho não deve ser tratado como venda concluída.

O cliente pode precisar tentar novamente, e o admin deve acompanhar a trilha do pedido e da tentativa de pagamento.

## Reembolsos

Reembolso é operação financeira sensível e deve seguir a área de pagamentos/reembolsos do admin.

O MVP do assistente apenas explica o fluxo; ele não executa reembolso.

