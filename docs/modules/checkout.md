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
- checkout é uma superfície tenant-required quando não houver `session_key` explícita
- sem tenant resolvido e sem `session_key`, a página deve falhar fechado em vez de abrir um checkout genérico

## Readiness de persistência
- o módulo agora possui `CheckoutSession` para armazenar snapshot operacional de contato, endereço, métodos selecionados e totais
- `CheckoutSessionItem` guarda os itens exibidos no checkout como snapshot local de leitura, sem acoplar a UI diretamente a `cart` ou `orders`
- essa estrutura é propositalmente mínima e existe para desbloquear futuras leituras persistidas honestas na query layer
- a query layer do checkout já consome `CheckoutSession` e `CheckoutSessionItem` quando houver registros persistidos disponíveis
- o fallback visual atual continua intencionalmente ativo até existirem migrations aplicadas e dados reais carregados
- esse fallback continua restrito a contexto de tenant válido; ele não deve mascarar ausência de loja

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

## Completion / post-order confidence polish
- a etapa `review` agora deixa mais explícito o que acontece ao concluir:
  - será criado um pedido inicial na conta
  - itens, entrega e pagamento revisados já ficam registrados
  - o pagamento real continua pendente nesta etapa
- o próprio checkout também reforça esse handoff com:
  - `page_meta`
  - `summary_note`
  - hint de revisão pronto para gerar pedido
- o CTA final da etapa `review` também ficou mais explícito:
  - `Gerar pedido inicial`
  - guidance curto do que será criado
  - helper claro do que ainda não foi confirmado
- a intenção é reduzir ambiguidade no momento final sem criar página nova de sucesso

## Session completion review
- a etapa `review` agora também expõe um checklist curto de prontidão antes de gerar o pedido inicial
- esse checklist usa apenas sinais já presentes na sessão:
  - itens confirmados
  - entrega e frete salvos
  - pagamento e termos revisados
  - totais prontos para virar pedido
- a intenção é deixar mais explícito, no próprio checkout:
  - o que já está pronto
  - por que a sessão pode gerar um pedido inicial com segurança
  - o que ainda bloquearia a conclusão, quando houver pendências

## Completion robustness guardrails
- antes de gerar o pedido inicial, o checkout agora também valida se o snapshot salvo da sessão continua coerente com os próprios itens e totais persistidos
- esse guardrail bloqueia a conclusão quando encontrar inconsistências como:
  - sessão sem itens válidos
  - item com título vazio
  - item com preço inválido
  - subtotal salvo diferente da soma atual dos itens
  - total final salvo diferente da composição de subtotal, frete e desconto
- quando isso acontecer, a UI orienta reabrir o checkout e revisar a sessão antes de tentar gerar o pedido inicial novamente
- a intenção é evitar que uma sessão desatualizada ou incoerente materialize um pedido com snapshot inseguro

## Completion idempotency guardrails
- a conclusão do checkout agora também protege a sessão contra dupla submissão e retry logo após sucesso
- `CheckoutSession` passa a guardar `completed_order_number` depois que o pedido inicial é criado com sucesso
- quando a mesma sessão já concluída tenta finalizar de novo:
  - o fluxo reaproveita o pedido já criado
  - redireciona novamente para o mesmo detalhe do pedido
  - não materializa pedido duplicado
- esse reaproveitamento agora só acontece quando `completed_order_number` ainda resolve para um `Order` real do mesmo tenant
- se a sessão concluída continuar apontando para um pedido que já não existe mais, o fluxo retorna `checkout-completion-session-drift` e orienta reabrir o checkout com segurança
- a leitura da sessão também acontece com lock leve no momento da conclusão para reduzir corrida entre requests concorrentes
- a alocação de `Order.number` continua simples, mas agora tolera colisão transitória com retry seguro antes de desistir

## Multi-item cart readiness
- a ativação `PDP → CheckoutSession` agora também consegue reaproveitar uma sessão `open` do mesmo tenant em vez de sempre criar uma sessão nova
- o comportamento mínimo atual é:
  - mesma variante adicionada novamente → incrementa `quantity`
  - variante diferente adicionada à mesma sessão → cria um novo `CheckoutSessionItem`
  - `subtotal`, `grand_total` e parcelamento são recalculados a partir do snapshot multi-item
- isso ainda não abre uma página completa de carrinho, mas já prepara o checkout para deixar de depender de sessão single-item

## Cart item mutation guardrails
- a própria `CheckoutSession` agora já suporta mutações básicas e seguras por item antes de existir uma superfície dedicada de carrinho
- o comportamento mínimo atual cobre:
  - `increment` → aumenta a quantidade do item
  - `decrement` → reduz a quantidade e remove a linha quando ela chegaria a zero
  - `remove` → elimina o item explicitamente da sessão
- toda mutação recalcula:
  - `subtotal`
  - `shipping_total`
  - `grand_total`
  - parcelamento
- quando o último item sai da sessão:
  - a sessão continua `open`
  - os totais voltam para zero
  - o checkout passa a tratar a sessão como vazia até novos itens entrarem
- isso mantém a base multi-item previsível antes de abrir uma UI de carrinho mais rica

## Cart surface lite
- o checkout agora também pode abrir primeiro em um estágio leve de `cart`
- essa superfície:
  - mostra os itens atuais da `CheckoutSession`
  - permite ajustar quantidade e remover itens
  - exibe totais já recalculados da sessão
  - libera `delivery` só quando a pessoa decidir seguir
- a intenção é criar um ponto intermediário real entre `PDP` e `delivery`, sem ainda abrir uma página completa de carrinho
- o fluxo continua dentro da mesma página e do mesmo endpoint de checkout

## Reorder lite bootstrap
- o checkout agora também pode nascer a partir de um pedido anterior da customer area
- esse bootstrap recria uma `CheckoutSession` com:
  - itens elegíveis do pedido antigo
  - preço atual da variante
  - `variant_sku` preservado quando ainda existir
  - stage inicial em `cart`
- o comportamento atual continua conservador:
  - sessão `open` do tenant é reaproveitada e reconstruída
  - itens sem variante elegível ficam de fora
- quando nada for elegível, a sessão nova não é criada
- o bootstrap de reorder agora também exige `tenant_id` explícito:
  - não reabre compra anterior por lookup global de `order_number`
  - sem tenant resolvido, falha fechado

## Payment retry readiness lite
- o checkout agora também pode nascer de um pedido pendente com falha de pagamento
- esse bootstrap continua leve e seguro:
  - só aceita pedidos ainda pendentes
  - exige sinal explícito de falha de pagamento
  - recria a sessão com os itens ainda elegíveis
  - redireciona para o estágio `payment`
- esse retry agora também exige `tenant_id` explícito:
  - não retoma pagamento por lookup global de `order_number`
  - sem tenant resolvido, responde como indisponível
- a intenção não é reabrir um checkout completo novo, e sim:
  - preservar a compra já iniciada
  - retomar pagamento com o mesmo contexto de itens
  - manter a retomada previsível para o cliente

## Real payment readiness
- quando o pedido inicial nasce do checkout, ele agora já registra a origem de pagamento atual como:
  - `payment_source_type = checkout_pending`
  - `payment_source_label = Checkout aguardando pagamento`
- isso ajuda a separar com mais clareza:
  - pedido criado
  - pagamento ainda pendente
  - futura confirmação por fluxo interno ou gateway externo
- além disso, o checkout agora também pode abrir uma `PaymentAttempt` pendente no módulo `payments`
- essa tentativa nasce de forma leve junto do pedido inicial e usa:
  - `order_number`
  - método de pagamento escolhido na sessão
  - total atual do pedido
- a intenção é preparar, sem gateway real ainda, um contrato explícito entre:
  - criação do pedido
  - trilha pendente de pagamento
  - futura confirmação/falha por webhook
- o checkout agora também deixa um breadcrumb de rastreabilidade cross-module:
  - o `OrderStatusHistory` inicial registra a `session_key` de origem
  - a `PaymentAttempt` pendente pode guardar essa mesma `checkout_session_key` em `metadata`
- isso ajuda suporte e operação a reconstruir a cadeia real:
  - sessão de checkout
  - pedido persistido
  - tentativa de pagamento associada

## Tenant boundary hardening
- a leitura ORM do checkout não pode mais escolher uma sessão `open` global quando o tenant não estiver resolvido
- quando existir `session_key`, o fluxo ainda pode reabrir a sessão explicitamente indicada
- quando não existir `session_key`, a busca e os snapshots do checkout devem depender do tenant atual

## First real provider integration lite
- a `PaymentAttempt` aberta pelo checkout agora já nasce, por padrão, apontando para o provider configurado em `PAYMENTS_PROVIDER_DEFAULT`
- o default atual é `pagarme`
- isso permite que o fluxo:
  - `review`
  - `order created`
  - `PaymentAttempt pending`
  - `hosted payment redirect`
  siga usando a mesma boundary de `payments`, sem espalhar detalhes do provider para `checkout`

## Test environment pilot handoff
- para o piloto de pagamento em teste, o papel do checkout continua simples:
  - criar o pedido inicial
  - abrir a `PaymentAttempt`
  - deixar a continuidade em `payments`
- o checklist operacional de teste fica em `docs/modules/payments.md`
- o aceite do checkout nesse piloto é:
  - pedido inicial nasce corretamente
  - `PaymentAttempt` pendente é aberta
  - nenhum pedido duplicado é criado
  - nenhuma baixa de estoque acontece antes do webhook de confirmação

## Checkout recovery guidance
- quando houver bloqueio de estoque ou indisponibilidade de sessão, o checkout agora também mostra orientação leve de retomada
- essa guidance reutiliza a própria página atual e a URL de retorno ao produto para indicar com clareza:
  - quando vale reabrir a sessão atual
  - quando vale voltar ao produto
  - quando a retomada mais segura é reconstruir o fluxo a partir da variante vigente
- a implementação continua em camada de apresentação, sem mover regra de negócio para a template
