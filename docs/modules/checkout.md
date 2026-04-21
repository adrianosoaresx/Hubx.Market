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

## Continuidade com o PDP
- o checkout agora aceita `back_url` por querystring para preservar o retorno ao produto quando o usuário avança a partir do PDP
- isso permite um fluxo mais coerente entre:
  - detalhe do produto
  - checkout
  - retorno ao produto
- a responsabilidade continua fina na view, apenas como adaptação HTTP da navegação
- além disso, o checkout também aceita `session_key` por querystring para abrir a sessão ativada pelo PDP quando ela existir
- quando houver `AccountProfile` ativo e endereço do mesmo tenant, a sessão ativada pelo PDP também pode nascer com:
  - contato básico
  - endereço principal
  preenchidos de forma segura

## Write path da sessão
- o checkout agora também persiste edições básicas da `CheckoutSession` via `application/checkout_session_commands.py`
- a view continua fina: apenas adapta `POST`, encaminha `session_key` e redireciona com feedback por querystring
- o write path cobre, de forma mínima e segura:
  - contato
  - endereço
  - método de frete selecionado
  - método de pagamento selecionado
  - parcelas selecionadas
  - aceite de termos
- o recálculo de `shipping_total`, `grand_total` e `installments_summary` acontece na camada de aplicação
- quando a sessão não existir ou não puder ser resolvida, o fluxo falha com segurança e preserva fallback visual

## Progressão por etapa
- o checkout agora também aceita `stage` por querystring e usa esse contexto para manter a sessão mais progressiva em uma única página
- as etapas continuam leves e sem engine de pagamento:
  - `delivery`
  - `payment`
  - `review`
- a query layer decide a etapa corrente com base no estado salvo da `CheckoutSession`
- quando uma etapa ainda não puder ser trabalhada com segurança, o fluxo volta para a etapa anterior necessária sem quebrar a navegação
- após salvar com sucesso, a view redireciona para a próxima etapa coerente dentro da mesma sessão

## Clareza de conclusão
- a query layer também expõe hints de conclusão por etapa para deixar mais claro:
  - o que já foi salvo
  - o que ainda falta
  - qual etapa está realmente pronta para seguir
- esses sinais continuam derivados apenas do estado atual da `CheckoutSession`
- a página usa esses hints como reforço visual leve, sem mudar o contrato estrutural do checkout

## Completion readiness
- a etapa `review` agora pode materializar um `Order` mínimo e persistido quando a sessão estiver pronta
- essa conclusão continua honesta:
  - não confirma pagamento real
  - não baixa estoque
  - não depende de gateway externo
- o pedido nasce com snapshot suficiente para acompanhamento:
  - customer snapshot
  - endereço
  - itens
  - totais
  - `payment_status` pendente
- após a conclusão:
  - a `CheckoutSession` passa para `completed`
  - o usuário é redirecionado para o detalhe do pedido na área do cliente

## Payment progression readiness
- depois que o pedido inicial nasce do checkout, a evolução do pagamento ainda continua explícita e honesta
- a área do cliente agora pode acionar uma confirmação interna mínima de pagamento para pedidos ainda pendentes
- essa confirmação:
  - não depende de gateway externo
  - não simula captura real
  - apenas move o pedido para um estado interno confirmado, destravando a preparação
- a evolução atualiza:
  - `Order.status`
  - `payment_status`
  - `fulfillment_status`
  - `shipping_status`
  - `OrderStatusHistory`

## Inventory / post-payment readiness
- `CheckoutSessionItem` agora também pode preservar `variant_sku` como snapshot explícito da variante escolhida no PDP
- ao concluir o checkout, `OrderItem` herda esse mesmo `variant_sku` para manter o vínculo seguro com a unidade vendável
- isso prepara a trilha para impactos de estoque posteriores ao pagamento sem depender apenas de parsing textual de `meta`

## Checkout / inventory consistency guardrails
- a conclusão do checkout agora valida se cada item ainda está coerente com o estoque vivo antes de gerar o pedido
- os guardrails atuais cobrem:
  - item sem `variant_sku` seguro
  - variante inexistente no mesmo tenant
  - produto/variante indisponível para confirmação segura
  - saldo livre insuficiente quando não houver `backorder`
- a intenção é evitar que a sessão avance para pedido quando a variante já não puder mais sustentar a próxima reserva operacional com segurança
