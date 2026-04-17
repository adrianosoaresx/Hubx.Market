# Checkout

## Responsabilidade
Orquestrar endereço, frete, cupom e criação do pedido.

## Entidades principais
- CheckoutSession
- CheckoutSessionItem
- Cart
- CustomerAddress
- Order

## Casos de uso
- selecionar endereço
- calcular frete
- aplicar cupom
- confirmar compra

## Regras de negócio
- pedido nasce após frete e clique em pagar

## Integração UI
- views HTTP devem permanecer finas em `interfaces/`
- a page template oficial de checkout pode ser usada como contrato de apresentação
- adapters de contexto podem preparar entrega, pagamento e resumo sem mover regra de negócio para a view
- queries de leitura para o checkout devem viver em `application/`; fallback temporário de carrinho, frete e pagamento deve ficar nessa camada, não na view

## Readiness de persistência
- o módulo agora possui `CheckoutSession` para armazenar snapshot operacional de contato, endereço, métodos selecionados e totais
- `CheckoutSessionItem` guarda os itens exibidos no checkout como snapshot local de leitura, sem acoplar a UI diretamente a `cart` ou `orders`
- essa estrutura é propositalmente mínima e existe para desbloquear futuras leituras persistidas honestas na query layer
- a query layer do checkout já consome `CheckoutSession` e `CheckoutSessionItem` quando houver registros persistidos disponíveis
- o fallback visual atual continua intencionalmente ativo até existirem migrations aplicadas e dados reais carregados

## O que a query layer poderá consumir depois
- dados de contato e entrega (`first_name`, `last_name`, `email`, `phone`, endereço)
- métodos de frete e pagamento persistidos como snapshot
- itens do checkout via `CheckoutSessionItem`
- totais e parcelamento persistidos na sessão

## O que ainda falta
- uma fonte real de `cart` para alimentar a sessão
- integração formal com `shipping` e `payments` para métodos/opções reais
- estratégia de expiração e recuperação da sessão por tenant/usuário
