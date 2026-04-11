# Payments Architecture

## Gateway inicial
Pagar.me

## Métodos iniciais
- PIX
- cartão de crédito

## Regras
- parcelamento até 12x
- PIX depende de webhook
- pagamentos exigem idempotência
- PaymentTransaction guarda eventos do provedor

## Entidades
- Payment
- PaymentTransaction
