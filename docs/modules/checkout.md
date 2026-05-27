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

## Wave AL — Checkout Product Experience Review
- a revisão funcional do checkout mostra que a superfície já está forte em:
  - progressão por etapa
  - carrinho leve dentro da própria sessão
  - checklist de revisão
  - guidance de recuperação
  - handoff seguro para pedido inicial e pagamento pendente

### O que já funciona bem
- **clareza operacional**
  - a página já explica quando o pedido nasce e quando o pagamento ainda fica pendente
- **progressão segura**
  - etapas bloqueiam avanço inconsistente e redirecionam para a etapa trabalhável
- **cart surface lite**
  - a sessão já permite revisar itens, ajustar quantidades e remover linhas antes de seguir
- **recovery guidance**
  - conflitos de sessão, estoque e snapshot já têm orientação de retomada

### Gaps mais relevantes agora
- **experiência ainda é densa**
  - a página comunica muita coisa corretamente, mas pode exigir leitura demais do cliente
- **narrativa de etapa ainda é mais funcional do que persuasiva**
  - carrinho, entrega, pagamento e revisão já têm copy clara
  - mas ainda podem guiar melhor o cliente pelo melhor próximo passo
- **resumo lateral ainda é mais contábil do que tranquilizador**
  - totais e itens estão corretos
  - mas ainda podem reforçar melhor confiança e continuidade da sessão

### Leitura objetiva
- eu não vejo um gap crítico de fluxo no checkout neste momento
- o próximo ganho parece ser de **clareza de jornada e redução de atrito percebido**, não de arquitetura

### Decisão prática
- o eixo de checkout deve evoluir por uma revisão pequena de experiência de etapa
- sem mexer ainda em:
  - criação de pedido
  - `PaymentAttempt`
  - regras de estoque
  - retry/recovery transacional
  - layout estrutural da página

### Próxima wave
- **Wave AM — Checkout Step Clarity Review**
- foco:
  - revisar se a copy de etapa, CTA e resumo lateral já tem um primeiro ajuste pequeno e seguro

## Wave AM — Checkout Step Clarity Review
- a revisão da copy de etapa mostra que já existe um primeiro ajuste pequeno e seguro para o checkout
- o melhor ponto de entrada é:
  - `stage_title`
  - `stage_description`
  - `submit_label`
  - `final_action_description`
  - `final_action_helper`

### O que já está bom
- as etapas já estão separadas de forma previsível:
  - `cart`
  - `delivery`
  - `payment`
  - `review`
- a página já deixa claro:
  - quando o pedido ainda não foi criado
  - quando a revisão gera pedido inicial
  - quando o pagamento real continua pendente

### O que ainda pode melhorar
- a copy de etapa ainda soa um pouco operacional
- os CTAs ainda comunicam mais ação técnica do que benefício imediato
- a orientação final pode reduzir melhor a dúvida:
  - “o que acontece se eu clicar agora?”

### Recorte seguro
- a primeira execução deve mexer só em:
  - `stage_titles`
  - `stage_descriptions`
  - `submit_labels`
  - `final_action_descriptions`
  - `final_action_helpers`
- ficam fora por enquanto:
  - `completion_hints`
  - `review_readiness`
  - `summary_note`
  - template
  - regras de conclusão
  - `PaymentAttempt`

### Leitura objetiva
- esse é o menor recorte com bom retorno de clareza
- melhora a jornada sem mexer no fluxo transacional

### Próxima wave
- **Wave AN — Checkout Step Clarity Copy Execution**
- foco:
  - aplicar a primeira passada real de copy em etapa, CTA e orientação final

## Wave AN — Checkout Step Clarity Copy Execution
- aplicamos a primeira passada real de clareza de etapa no checkout
- a execução ficou restrita ao recorte seguro:
  - `stage_title`
  - `stage_description`
  - `submit_label`
  - `final_action_description`
  - `final_action_helper`

### O que mudou
- as etapas agora falam mais diretamente sobre o próximo passo do cliente:
  - conferir carrinho
  - informar entrega
  - escolher pagamento
  - revisar antes de criar o pedido
- os CTAs ficaram mais alinhados com o que acontece de fato ao clicar
- a orientação final reforça melhor:
  - quando o pedido ainda não nasce
  - quando o pedido inicial será criado
  - que a confirmação real de pagamento vem depois

### O que não mudou
- template
- regras de conclusão
- criação de pedido
- `PaymentAttempt`
- recovery transacional
- estoque
- checklist de revisão

### Leitura objetiva
- o checkout mantém o mesmo comportamento seguro
- mas agora a pessoa lê melhor:
  - onde está
  - o que fazer agora
  - o que acontece depois do clique

### Próxima wave
- **Wave AO — Checkout Summary Confidence Review**
- foco:
  - revisar se o resumo lateral já merece uma passada pequena de confiança e continuidade

## Wave AO — Checkout Summary Confidence Review
- a revisão do resumo lateral mostra que ele já está correto e útil
- hoje ele comunica bem:
  - itens
  - subtotal
  - frete
  - desconto
  - parcelamento
  - total

### O que já está bom
- o resumo é consistente com a sessão atual
- a copy já diferencia:
  - totais em andamento
  - revisão pronta para gerar pedido inicial
  - pagamento real ainda pendente
- não há necessidade de mudar o template ou a estrutura visual agora

### O que ainda pode melhorar
- `summary_description` ainda parece muito dependente da etapa atual
- `summary_note` pode tranquilizar melhor sobre:
  - o que o total representa
  - quando ele vira pedido inicial
  - que pagamento real não é confirmado nesta tela

### Recorte seguro
- a próxima execução deve mexer só em:
  - `summary_description`
  - `summary_note`
- ficam fora por enquanto:
  - template
  - itens do resumo
  - cálculo de totais
  - parcelamento
  - criação de pedido
  - `PaymentAttempt`

### Leitura objetiva
- esse é um bom próximo ajuste porque reforça confiança no momento da decisão
- melhora a lateral sem tocar em regra transacional

### Próxima wave
- **Wave AP — Checkout Summary Confidence Copy Execution**
- foco:
  - aplicar uma passada pequena em `summary_description` e `summary_note`

## Wave AP — Checkout Summary Confidence Copy Execution
- aplicamos uma passada pequena de confiança no resumo lateral do checkout
- a execução ficou restrita a:
  - `summary_description`
  - `summary_note`

### O que mudou
- o resumo agora explica melhor:
  - o que o total representa em cada etapa
  - quando os valores ainda são uma sessão em preparação
  - quando o total será levado para o pedido inicial
  - que a confirmação real de pagamento acontece depois
- a copy passa a variar por etapa:
  - carrinho
  - entrega
  - pagamento
  - revisão

### O que não mudou
- template
- itens do resumo
- cálculo de subtotal, frete, desconto e total
- parcelamento
- criação de pedido
- `PaymentAttempt`

### Leitura objetiva
- o resumo lateral ficou mais tranquilizador no momento da decisão
- o comportamento transacional permanece igual

### Próxima wave
- **Wave AQ — Checkout Product Experience Wrap-Up Review**
- foco:
  - revisar o checkout depois das passadas de etapa e resumo
  - decidir se ainda existe algum ajuste pequeno antes de encerrar este eixo

## Wave AQ — Checkout Product Experience Wrap-Up Review
- a revisão final do checkout mostra que a superfície avançou bem neste eixo de produto
- hoje o checkout comunica melhor:
  - onde a pessoa está
  - qual é o próximo passo
  - o que acontece ao clicar
  - o que o resumo lateral representa

### O que ficou mais forte
- **progressão por etapa**
  - carrinho, entrega, pagamento e revisão ficaram mais orientados ao próximo passo do cliente
- **CTA e orientação final**
  - os botões e helpers explicam melhor a consequência da ação
- **resumo lateral**
  - `summary_description` e `summary_note` agora reforçam confiança sem mudar cálculo ou estrutura
- **preservação transacional**
  - criação de pedido, `PaymentAttempt`, estoque e recovery continuaram intactos

### O que ainda pode evoluir no futuro
- refinamentos pequenos de:
  - densidade visual do checklist
  - ordem ou peso dos alertas de etapa
  - UX específica de métodos de pagamento reais
- mas isso já parece:
  - refinamento futuro
  - e não gap funcional urgente do checkout

### Leitura objetiva
- eu não vejo mais um ajuste pequeno e óbvio que justifique insistir agora neste mesmo eixo
- o checkout parece:
  - mais claro
  - mais tranquilizador
  - mais previsível para o cliente
- sem perder:
  - guardrails transacionais
  - rastreabilidade
  - isolamento multi-tenant

### Decisão prática
- o eixo de **checkout product experience** pode ser considerado **encerrado com sucesso nesta fase**

### Próxima wave
- **Wave AR — Payment Product Experience Review**
- foco:
  - revisar pagamentos como experiência de produto
  - depois dos ganhos já consolidados em descoberta, checkout e pós-compra

## Wave ZJ — Checkout Session Operational Readiness Review
- revisamos a fronteira operacional de sessões de checkout antes de tráfego real amplo
- foco:
  - sessões abertas incompletas
  - sessões antigas ou expiradas
  - sessões concluídas sem pedido correspondente
  - divergência entre itens e totais

### Decisão
- tratar inconsistências de sessão como triagem operacional tenant-scoped
- não corrigir nem expirar sessões automaticamente nesta wave
- usar `orders` apenas para validar vínculo de pedido concluído

## Wave ZK — Checkout Session Issue CLI Execution
- adicionamos o comando:
  - `list_checkout_session_issues`
- o comando exige:
  - `--tenant-id`
- filtros disponíveis:
  - `open_empty`
  - `open_missing_contact`
  - `open_missing_delivery`
  - `open_missing_payment`
  - `open_stale`
  - `completed_order_missing`
  - `total_mismatch`

### Resultado
- operações podem listar sessões problemáticas por tenant sem consulta manual ao banco
- o output inclui `session_id`, `session_key`, `status` e `issue`

## Wave ZL — Checkout Session Metrics Execution
- adicionamos exporter Prometheus para checkout:
  - `hubx_checkout_session_issue_total{tenant_id,issue}`
- adicionamos endpoint protegido por token:
  - `/ops/checkout/metrics/session-issues/`

### Segurança
- o endpoint fica desativado sem `CHECKOUT_OBSERVABILITY_TOKEN`
- aceita:
  - `Authorization: Bearer <token>`
  - `X-Hubx-Observability-Token`

## Wave ZM — Checkout Observability Pack Execution
- adicionamos pacote inicial de observabilidade:
  - alert rules
  - scrape example
  - routing Alertmanager
  - dashboard Grafana
  - runbook operacional

### Alertas iniciais
- `open_stale`
- `completed_order_missing`
- `total_mismatch`

## Wave ZN — Checkout Operational Wrap-Up Review
- checkout agora possui um eixo operacional mínimo comparável a catalog/customers
- a cobertura atual entrega:
  - diagnóstico CLI
  - métrica por tenant
  - endpoint protegido
  - alertas iniciais
  - dashboard inicial
  - runbook de triagem

### Próxima abordagem eleita
- **Checkout Expiration/Retention Policy Review**
- foco:
  - decidir se sessões abertas antigas devem ser apenas observadas, expiradas por comando, ou tratadas por job assíncrono com política explícita

## Wave ZO — Checkout Expiration/Retention Policy Review
- revisamos a evolução natural depois dos sinais `open_stale`
- decisão:
  - expirar sessões abertas antigas de forma explícita
  - não deletar sessões
  - não mexer em sessões concluídas
  - não criar job automático nesta etapa

### Regra responsável
- módulo:
  - `checkout`
- camada:
  - `application`
- comando operacional:
  - `expire_checkout_sessions`

## Wave ZP — Checkout Expiration Command Execution
- adicionamos rotina segura para expirar sessões abertas antigas
- guardrails:
  - `--tenant-id` obrigatório
  - `--older-than-hours >= 6`
  - `--dry-run`
  - `--limit`
  - somente `status=open`

### Resultado
- sessões candidatas deixam de ficar indefinidamente reutilizáveis
- a ação é reversível por intervenção manual, porque não há deleção
- o sinal `open_stale` agora tem uma ação operacional clara

## Wave ZQ — Checkout Expiration Tenant Scope Review
- a execução permanece tenant-scoped
- sessões de outros tenants não entram no lote
- sessões `completed` ficam preservadas mesmo quando antigas

### Leitura multi-tenant
- isso evita expiração global acidental
- também permite ativação gradual por loja

## Wave ZR — Checkout Retention Runbook Update
- atualizamos o runbook operacional de checkout
- a ativação recomendada começa por:
  - `expire_checkout_sessions --dry-run`
  - validação de `open_stale`
  - execução real por tenant

### Observabilidade
- alertas continuam baseados em:
  - `hubx_checkout_session_issue_total{issue="open_stale"}`
- o comando reduz o backlog operacional sem criar métrica nova nesta wave

## Wave ZS — Checkout Expiration Wrap-Up Review
- a abordagem de retention fica encerrada com uma política mínima e segura
- o sistema agora tem:
  - diagnóstico
  - alertas
  - dashboard
  - ação operacional explícita para sessões antigas

### Próxima abordagem eleita
- **Checkout Expired Session UX Review**
- foco:
  - revisar como a UI orienta o cliente quando uma sessão já foi expirada
  - evitar fallback silencioso que esconda uma sessão inválida
  - preservar retomada segura a partir do produto

## Wave ZT — Checkout Expired Session UX Review
- revisamos o comportamento quando um `session_key` explícito aponta para sessão expirada
- gap encontrado:
  - a query buscava apenas sessões `open`
  - quando não encontrava a sessão, o service podia cair no fallback demonstrativo
  - isso mascarava estado inválido com itens de showcase

### Decisão
- `session_key` explícito nunca deve virar checkout fake
- sessão `expired` deve renderizar estado read-only
- sessão inexistente deve renderizar indisponibilidade explícita

## Wave ZU — Expired Session Readonly Contract Execution
- a query de checkout agora busca a sessão por `session_key` mesmo fora de `open`
- sessões `expired` expõem:
  - `checkout_session_state=expired`
  - `checkout_session_readonly=True`
  - feedback de sessão expirada
  - recovery para voltar ao produto

### Resultado
- itens da sessão expirada podem aparecer como referência
- ações de mutação não aparecem
- submit de checkout fica oculto

## Wave ZV — Missing Session Fallback Guard Execution
- `session_key` inexistente agora retorna estado explícito:
  - `Sessão de checkout indisponível`
  - `checkout_session_state=missing`
  - `checkout_session_readonly=True`
- o fallback demonstrativo permanece apenas para cenários sem sessão persistida explícita

### Leitura objetiva
- isso reduz ambiguidade para cliente e suporte
- também impede que um link velho pareça uma compra ativa

## Wave ZW — Checkout Expired UX Test Coverage
- adicionamos cobertura para:
  - query de sessão expirada read-only
  - query de sessão inexistente sem fallback
  - renderização da UI expirada sem submit

### Segurança
- nenhuma mudança de pedido, pagamento ou estoque foi introduzida
- a mudança é de contrato de leitura e apresentação

## Wave ZX — Checkout Expired Session UX Wrap-Up Review
- a abordagem fica encerrada com estado explícito para sessões inválidas
- o checkout agora diferencia:
  - sessão ativa
  - sessão expirada
  - sessão inexistente
  - fallback/showcase sem `session_key`

### Próxima abordagem eleita
- **Checkout Session Creation Source Review**
- foco:
  - revisar de onde nasce uma sessão nova
  - garantir que retomada pelo produto cria/reutiliza sessão aberta sem reaproveitar sessão expirada
  - avaliar se `_get_reusable_open_session` ainda precisa de guardrails adicionais

## Wave ZY — Checkout Session Creation Source Review
- revisamos o ponto onde uma sessão nova nasce a partir da PDP
- fonte principal:
  - `checkout_activation_commands.activate_from_product`
- ponto crítico:
  - `_get_reusable_open_session` reutilizava qualquer sessão `open` recente ou antiga

### Risco encontrado
- uma sessão `open` stale poderia continuar sendo reaproveitada pela retomada via produto
- isso enfraquecia a política de expiração recém-criada

## Wave ZZ — Checkout Reuse Guardrails Execution
- endurecemos a reutilização de sessão aberta
- uma sessão só é reutilizada quando:
  - pertence ao mesmo tenant
  - está `open`
  - não venceu por `expires_at`
  - foi atualizada há menos de 24 horas

### Comportamento novo
- sessões `open` stale ou vencidas são marcadas como `expired`
- a ativação cria uma nova sessão `open` para o produto atual
- sessões recentes continuam sendo reutilizadas para compor carrinho multi-item

## Wave AAA — Checkout Activation Source Test Coverage
- adicionamos testes para:
  - reutilização de sessão aberta recente
  - não reutilização de sessão aberta stale
  - não reutilização de sessão aberta com `expires_at` vencido

### Segurança
- não houve mudança em pedidos
- não houve mudança em pagamentos
- não houve baixa de estoque
- a alteração fica restrita à origem/reutilização de `CheckoutSession`

## Wave AAB — Checkout Session Creation Wrap-Up Review
- a origem de sessão agora está consistente com:
  - expiração operacional
  - UX read-only para sessão expirada
  - retomada segura pelo produto

### Próxima abordagem eleita
- **Checkout Session Observability Refinement**
- foco:
  - revisar se os sinais `open_stale` e expiração automática pela ativação precisam de métrica/issue mais específica
  - diferenciar backlog operacional de sessões stale versus sessões expiradas durante retomada pelo produto

## Wave AAC — Checkout Session Observability Refinement Review
- revisamos a observabilidade depois da expiração operacional e do guardrail de ativação
- lacuna encontrada:
  - `open_stale` mostra backlog ainda aberto
  - sessões já `expired` não apareciam como lifecycle separado

### Decisão
- não criar novo campo de origem da expiração nesta etapa
- expor métrica de status para diferenciar:
  - sessões abertas
  - sessões concluídas
  - sessões expiradas retidas

## Wave AAD — Checkout Session Status Metric Execution
- adicionamos métrica:
  - `hubx_checkout_session_status_total{tenant_id,status}`
- a métrica complementa:
  - `hubx_checkout_session_issue_total{tenant_id,issue}`

### Leitura operacional
- `issue=open_stale` indica ação pendente
- `status=expired` indica estoque já retirado do fluxo ativo

## Wave AAE — Checkout Observability Dashboard Refinement
- atualizamos o dashboard de checkout com:
  - série por status
  - stat de sessões expiradas retidas
- adicionamos alerta informativo:
  - `HubxCheckoutExpiredSessionsRetained`

### Escopo
- alerta informativo, não bloqueante
- foco em indicar necessidade futura de retenção/arquivamento

## Wave AAF — Checkout Observability Refinement Test Coverage
- cobrimos o exporter e endpoint para garantir presença de:
  - `hubx_checkout_session_issue_total`
  - `hubx_checkout_session_status_total`
  - label `status="expired"`

## Wave AAG — Checkout Observability Refinement Wrap-Up Review
- a observabilidade de checkout agora separa:
  - problemas ativos de sessão
  - lifecycle/status das sessões
  - backlog aberto versus retenção expirada

### Próxima abordagem eleita
- **Checkout Retention Archive Policy Review**
- foco:
  - decidir se sessões `expired` devem permanecer indefinidamente, ser arquivadas, ou receber pruning controlado por janela longa
  - evitar deleção prematura de intenção transacional útil para suporte/auditoria

## Wave AAH — Checkout Retention Archive Policy Review
- revisamos a política para sessões `expired`
- decisão nesta fase:
  - não criar tabela de archive
  - não remover sessões recentes
  - permitir pruning explícito e conservador para sessões expiradas antigas

### Racional
- `expired` ainda pode ser útil para suporte e auditoria recente
- mas manter tudo indefinidamente aumenta ruído operacional
- pruning precisa ser tenant-scoped e com janela longa

## Wave AAI — Expired Session Pruning Command Execution
- adicionamos comando:
  - `prune_expired_checkout_sessions`
- guardrails:
  - `--tenant-id` obrigatório
  - `--older-than-days >= 180`
  - `--dry-run`
  - `--limit`
  - só `status=expired`

### Observação operacional
- `deleted` inclui objetos relacionados removidos por cascade
- portanto o número pode ser maior que a quantidade de sessões

## Wave AAJ — Checkout Retention Pruning Test Coverage
- cobrimos:
  - dry-run sem remoção
  - respeito a tenant
  - preservação de `open` e `completed`
  - preservação de `expired` recente
  - rejeição de janela curta

## Wave AAK — Checkout Retention Archive Wrap-Up Review
- a política de retenção agora tem três níveis:
  - observar via `hubx_checkout_session_status_total`
  - expirar `open` antigas com `expire_checkout_sessions`
  - remover `expired` antigas com `prune_expired_checkout_sessions`

### Próxima abordagem eleita
- **Checkout Recovery Copy Consistency Review**
- foco:
  - revisar mensagens de recovery entre sessão ausente, expirada, drift, estoque e snapshot
  - reduzir divergência de copy sem mexer em regra transacional

## Wave AAL — Checkout Recovery Copy Consistency Review
- revisamos os textos de recuperação do checkout
- gap encontrado:
  - alguns estados inseguros sugeriam `Reabrir checkout`
  - outros usavam `Revisar produto`
  - a intenção real era recriar a sessão pelo produto

### Vocabulário definido
- `Voltar ao produto`
  - recriar sessão segura a partir da origem comercial
- `Reabrir checkout`
  - revisar a sessão atual quando ela ainda é útil

## Wave AAM — Recovery Copy Alignment Execution
- alinhamos recovery para:
  - completion indisponível
  - session drift
  - vínculo de estoque ausente
  - variante indisponível
  - conflito de estoque
- esses casos agora priorizam:
  - `Voltar ao produto`

### Mantido
- conflito de snapshot continua permitindo:
  - `Reabrir checkout`
- porque a própria sessão ainda pode ser revisada para itens/totais

## Wave AAN — Recovery Copy Test Coverage
- adicionamos/ajustamos cobertura para:
  - conflito de estoque não sugerir `Reabrir checkout`
  - session drift não sugerir `Reabrir checkout`
  - completion unavailable apontar para produto
  - snapshot conflict manter `Reabrir checkout`

## Wave AAO — Checkout Recovery Copy Wrap-Up Review
- a recuperação do checkout agora diferencia melhor:
  - sessão insegura → recriar pelo produto
  - sessão revisável → reabrir checkout
  - estado bloqueado/read-only → orientar sem submit

### Próxima abordagem eleita
- **Checkout Recovery Result Taxonomy Review**
- foco:
  - revisar se os códigos `checkout-*` ainda estão coesos
  - separar melhor falha de save, falha de completion, drift e inventory conflict
  - preparar base para analytics de recovery por result code

## Wave AAP — Checkout Recovery Result Taxonomy Review
- revisamos os result codes que chegam à UI do checkout
- objetivo:
  - classificar família do evento
  - classificar severidade
  - classificar ação recomendada

### Famílias iniciais
- `progress`
- `session`
- `readiness`
- `inventory`
- `snapshot`
- `cart_mutation`
- `reorder`
- `payment_retry`

## Wave AAQ — Checkout Result Taxonomy Execution
- adicionamos `CHECKOUT_RESULT_TAXONOMY`
- a view passa a expor:
  - `checkout_result_taxonomy.code`
  - `checkout_result_taxonomy.family`
  - `checkout_result_taxonomy.severity`
  - `checkout_result_taxonomy.recovery_action`

### Ações recomendadas
- `continue_session`
- `restart_from_product`
- `review_current_session`
- `view_order`

## Wave AAR — Checkout Result Taxonomy Test Coverage
- cobrimos taxonomia para:
  - inventory conflict
  - snapshot conflict
  - completion unavailable
  - session drift

### Leitura objetiva
- a copy agora tem um contrato auxiliar para analytics futuros
- nenhuma regra transacional foi alterada

## Wave AAS — Checkout Result Taxonomy Wrap-Up Review
- a taxonomia inicial está suficiente para separar:
  - problema de sessão
  - problema de readiness
  - problema de inventário
  - problema de snapshot
  - recovery de reorder/payment retry

### Próxima abordagem eleita
- **Checkout Recovery Analytics Metrics Review**
- foco:
  - avaliar se vale expor contadores Prometheus por `family` e `recovery_action`
  - sem persistir evento novo ainda
  - mantendo a leitura derivada dos result codes quando possível

## Wave AAT — Checkout Recovery Analytics Metrics Review
- revisamos se a taxonomia de recovery já deveria virar contador Prometheus
- decisão:
  - não criar contador de ocorrência nesta etapa
  - expor primeiro uma métrica info da taxonomia conhecida

### Racional
- o endpoint atual de métricas não observa cada redirect/result code real
- contar ocorrências sem evento persistido geraria analytics enganoso
- a métrica info prepara dashboards e consultas sem inventar volume operacional

## Wave AAU — Checkout Recovery Taxonomy Info Metric Execution
- adicionamos métrica:
  - `hubx_checkout_recovery_result_info{code,family,severity,recovery_action}`
- cada result code conhecido expõe valor `1`
- a taxonomia foi centralizada na camada de application para ser reutilizada por:
  - UI
  - exporter Prometheus

## Wave AAV — Checkout Recovery Analytics Dashboard Update
- o dashboard de checkout ganhou painel:
  - `Recovery result taxonomy by family`
- objetivo:
  - visualizar cobertura da taxonomia por família e ação recomendada
  - preparar leitura futura quando eventos reais de recovery forem persistidos

## Wave AAW — Checkout Recovery Analytics Test Coverage
- cobrimos exporter e endpoint para garantir presença de:
  - `hubx_checkout_recovery_result_info`
  - `code="checkout-completion-stock-conflict"`
  - `family="inventory"`
  - `recovery_action="restart_from_product"`

## Wave AAX — Checkout Recovery Analytics Wrap-Up Review
- a base de analytics de recovery agora está explícita, mas conservadora:
  - taxonomy compartilhada em application
  - UI e métricas usam a mesma fonte
  - nenhuma tabela/evento novo foi criado
  - nenhuma ocorrência real é contada sem persistência

### Próxima abordagem eleita
- **Checkout Recovery Event Persistence Review**
- foco:
  - decidir se result codes críticos devem virar evento persistido
  - definir payload mínimo tenant-scoped para analytics real
  - evitar duplicidade entre observabilidade operacional e analytics de produto

## Wave AAY — Checkout Recovery Event Persistence Review
- revisamos a passagem de taxonomia derivada para evento persistido
- decisão:
  - persistir apenas result codes conhecidos
  - exigir `tenant_id` resolvido
  - vincular `CheckoutSession` somente quando ela pertence ao mesmo tenant

### Payload mínimo
- `result_code`
- `family`
- `severity`
- `recovery_action`
- `stage`
- `source`
- `tenant_id`
- `checkout_session_id` opcional

## Wave AAZ — Checkout Recovery Event Model Execution
- adicionamos `CheckoutRecoveryEvent`
- índices iniciais:
  - tenant + result code + data
  - tenant + família + ação recomendada
- o evento é analytics de produto, não substitui:
  - `hubx_checkout_session_issue_total`
  - `hubx_checkout_session_status_total`
  - triagem operacional de sessão

## Wave ABA — Checkout Recovery Event Command Boundary
- adicionamos `record_checkout_recovery_event`
- guardrails:
  - não grava sem tenant
  - não grava result code desconhecido
  - não associa sessão de outro tenant
- a view segue fina e delega a gravação ao application service

## Wave ABB — Checkout Recovery Event Test Coverage
- cobrimos:
  - persistência do evento com taxonomia
  - ausência de gravação sem tenant
  - ausência de gravação para result desconhecido
  - proteção contra vínculo cross-tenant de sessão
  - gravação ao renderizar feedback de recovery no checkout

## Wave ABC — Checkout Recovery Event Persistence Wrap-Up Review
- agora existe base real para analytics de recovery por tenant
- a métrica info continua documentando a taxonomia
- contadores futuros devem ser derivados de `CheckoutRecoveryEvent`, não do catálogo estático de result codes

### Próxima abordagem eleita
- **Checkout Recovery Event Metrics Review**
- foco:
  - expor contagem Prometheus a partir de eventos persistidos
  - manter baixa cardinalidade
  - separar analytics de produto de alertas operacionais

## Wave ABD — Checkout Recovery Event Metrics Review
- revisamos como expor analytics real de recovery sem inflar cardinalidade
- decisão:
  - contar eventos persistidos por tenant e taxonomia
  - não incluir `session_key`, pedido, e-mail ou identificadores sensíveis em labels

## Wave ABE — Checkout Recovery Event Metrics Execution
- adicionamos métrica:
  - `hubx_checkout_recovery_event_total{tenant_id,code,family,severity,recovery_action}`
- a métrica é derivada de `CheckoutRecoveryEvent`
- `hubx_checkout_recovery_result_info` permanece como catálogo estático da taxonomia conhecida

## Wave ABF — Checkout Recovery Event Dashboard Update
- o dashboard de checkout ganhou painel:
  - `Recovery events by tenant`
- leitura pretendida:
  - volume por tenant
  - família de recovery
  - ação recomendada

## Wave ABG — Checkout Recovery Event Metrics Test Coverage
- cobrimos exporter e endpoint para garantir:
  - presença da métrica de eventos
  - agregação de múltiplas ocorrências
  - preservação das labels de baixa cardinalidade

## Wave ABH — Checkout Recovery Event Metrics Wrap-Up Review
- a camada de analytics agora separa três leituras:
  - catálogo de taxonomia: `hubx_checkout_recovery_result_info`
  - ocorrência real: `hubx_checkout_recovery_event_total`
  - operação de sessão: `hubx_checkout_session_issue_total` e `hubx_checkout_session_status_total`

### Próxima abordagem eleita
- **Checkout Recovery Event Retention Review**
- foco:
  - decidir se `CheckoutRecoveryEvent` precisa de retenção/pruning
  - evitar crescimento indefinido de analytics de página
  - manter utilidade para diagnóstico de produto por tenant

## Wave ABI — Checkout Recovery Event Retention Review
- revisamos crescimento potencial de `CheckoutRecoveryEvent`
- decisão:
  - manter eventos recentes para analytics de produto
  - permitir pruning conservador por tenant
  - não remover automaticamente sem operação explícita

## Wave ABJ — Checkout Recovery Event Pruning Command Execution
- adicionamos comando:
  - `prune_checkout_recovery_events`
- guardrails:
  - `--tenant-id` obrigatório
  - `--older-than-days >= 180`
  - `--dry-run`
  - `--limit`
  - remoção apenas por tenant

## Wave ABK — Checkout Recovery Event Retention Test Coverage
- cobrimos:
  - dry-run sem remoção
  - remoção apenas de eventos antigos
  - preservação de eventos recentes
  - preservação de outro tenant
  - rejeição de janela curta

## Wave ABL — Checkout Recovery Event Retention Wrap-Up Review
- a trilha de recovery agora tem ciclo completo:
  - taxonomia
  - evento persistido
  - métrica derivada
  - dashboard
  - pruning conservador

### Próxima abordagem eleita
- **Checkout Recovery Final Readiness Review**
- foco:
  - revisar se a abordagem de checkout/recovery já fecha como produtiva
  - apontar apenas bloqueios reais restantes
  - evitar abrir nova feature sem necessidade objetiva

## Wave ABM — Checkout Recovery Final Readiness Review
- revisamos a trilha completa de recovery do checkout
- leitura objetiva:
  - o contrato de UI está explícito
  - a taxonomia está centralizada
  - eventos reais são persistidos por tenant
  - métricas e dashboard existem
  - retenção conservadora existe

## Wave ABN — Checkout Recovery Production Blockers
- bloqueios reais antes de produção:
  - aplicar migration `0004_checkoutrecoveryevent`
  - configurar `CHECKOUT_OBSERVABILITY_TOKEN`
  - publicar scrape/rules/dashboard de checkout no Prometheus/Grafana real
  - decidir agenda operacional para `prune_checkout_recovery_events`

### Não bloqueia produção
- criar novos result codes
- criar alertas por recovery event
- expor analytics em UI admin
- arquivar eventos em tabela separada

## Wave ABO — Checkout Recovery Go/No-Go Decision
- decisão desta abordagem:
  - **Go técnico com pré-requisitos operacionais**
- justificativa:
  - o fluxo segue tenant-scoped
  - não há mutação transacional nova além de analytics de recovery
  - métricas derivam de dados reais
  - pruning evita crescimento indefinido

## Wave ABP — Checkout Recovery Approach Close
- esta abordagem fica encerrada como produtiva após:
  - migration aplicada
  - token de observabilidade configurado
  - dashboard importado
  - rotina de pruning validada em `--dry-run`

### Próxima abordagem sugerida
- **Payments Customer Experience Readiness Review**
- foco:
  - revisar se a experiência de pagamento pendente/falho já tem a mesma clareza operacional do checkout
  - não reabrir checkout enquanto não houver novo blocker objetivo

## Cart Foundation Wave 18 — Coupon Checkout Handoff Snapshot Review
- o handoff `cart → checkout` já transporta `discount_total` e o usa no `grand_total`.
- a próxima evolução deve transportar também snapshot promocional explícito:
  - `coupon_code`
  - `promotion_snapshot`
- checkout deve persistir o snapshot recebido, não recalcular cupom nesta etapa.
- `coupons` continua dono da validação promocional.

## Cart Foundation Wave 19 — Coupon Checkout Handoff Snapshot Execution
- `CheckoutSession` passa a armazenar:
  - `coupon_code`
  - `promotion_snapshot`
- `activate_from_cart(...)` persiste snapshot promocional vindo do carrinho.
- cupom inválido ou sem desconto não é marcado como aplicado no checkout.
- checkout continua sem recalcular promoção.

## Cart Foundation Wave 20 — Coupon Order Snapshot Review
- `checkout_completion_commands` já copia `discount_total` da sessão para o pedido.
- a próxima execução deve copiar também:
  - `coupon_code`
  - `promotion_snapshot`
- checkout completion não deve revalidar nem recalcular cupom ao criar pedido.
- o pedido deve guardar o snapshot promocional visto pelo cliente no checkout.

## Cart Foundation Wave 21 — Coupon Order Snapshot Execution
- `checkout_completion_commands` agora copia `coupon_code` e `promotion_snapshot` para `Order`.
- a cópia acontece apenas quando a sessão tem desconto aplicado e snapshot promocional.
- checkout completion continua sem chamar `coupons`.

## Checkout Delivery Method Hardening Wave 1 — Delivery Method Contract Review

### Diagnóstico

O checkout já seleciona modalidades de entrega e recalcula totais a partir do método salvo na sessão.

Lacuna encontrada:

- quando um POST enviava um `shipping_method` não presente em `shipping_methods`, o comando ignorava silenciosamente a seleção;
- a sessão podia manter o frete anterior sem feedback explícito;
- isso deixava ambíguo se a entrega foi realmente escolhida naquela submissão.

### Decisão

**Go para rejeição explícita de método de entrega inválido.**

**No-Go para cotação real por CEP, frete dinâmico ou nova integração logística.**

## Checkout Delivery Method Hardening Wave 2 — Invalid Method Guard Execution

### Execução

`checkout_session_commands.update_session(...)` agora retorna `checkout-shipping-method-invalid` quando a sessão possui métodos de entrega e o método enviado não existe na lista disponível.

Nessa situação:

- a sessão não é salva;
- endereço/contato não são atualizados;
- frete e total permanecem inalterados;
- o usuário permanece na etapa de entrega;
- a UI exibe feedback claro para escolher uma entrega válida.

### Boundary preservada

- `checkout` continua dono da seleção final de entrega;
- `shipping` não é chamado para quote real;
- `cart` não ganha cálculo de frete;
- `orders` não é afetado.

## Checkout Delivery Method Hardening Wave 3 — Test Coverage

### Cobertura adicionada

Teste cobre:

- POST com método de entrega inexistente;
- retorno `checkout-shipping-method-invalid`;
- permanência em `stage=delivery`;
- ausência de mutação nos dados da sessão;
- feedback customer-facing na página.

## Checkout Delivery Method Hardening Wave 4 — Approach Closure Review

### Resultado

A abordagem endureceu o contrato de entrega no ponto correto: dentro do checkout, antes de pagamento/revisão.

### Decisão de encerramento

**Go para encerrar Checkout Delivery Method Hardening neste ponto.**

O sistema agora rejeita seleção inválida sem inventar frete, sem recalcular de modo silencioso e sem avançar a etapa.

### Fora de escopo preservado

- quote por CEP;
- cálculo dinâmico por provider;
- frete grátis;
- SLA por região;
- split shipment;
- reserva logística;
- alteração em pedido/pagamento.

### Próxima abordagem recomendada

**Checkout Payment Method Hardening Review**

Aplicar o mesmo endurecimento ao método de pagamento para evitar seleção inválida ou drift silencioso antes da revisão final.

## Checkout Payment Method Hardening Wave 1 — Payment Method Contract Review

### Diagnóstico

O checkout já salva o método de pagamento e usa esse estado para liberar a revisão final.

Lacuna encontrada:

- quando um POST enviava um `payment_method` não presente em `payment_methods`, o comando ignorava silenciosamente a seleção;
- a sessão podia manter o pagamento anterior sem feedback explícito;
- aceite de termos e parcelas poderiam ser processados junto de uma submissão conceitualmente inválida.

### Decisão

**Go para rejeição explícita de método de pagamento inválido.**

**No-Go para criar processamento real de pagamento, provider selection ou regras financeiras novas.**

## Checkout Payment Method Hardening Wave 2 — Invalid Payment Guard Execution

### Execução

`checkout_session_commands.update_session(...)` agora retorna `checkout-payment-method-invalid` quando a sessão possui métodos de pagamento e o método enviado não existe na lista disponível.

Nessa situação:

- a sessão não é salva;
- contato/endereço não são sobrescritos;
- método de pagamento anterior permanece;
- termos e parcelas não são atualizados;
- o usuário permanece na etapa de pagamento;
- a UI exibe feedback claro para escolher pagamento válido.

### Boundary preservada

- `checkout` continua dono da seleção de pagamento no funil;
- `payments` continua responsável por execução/tentativa real;
- `orders` não é afetado;
- nenhuma cobrança é criada.

## Checkout Payment Method Hardening Wave 3 — Test Coverage

### Cobertura adicionada

Teste cobre:

- POST com método de pagamento inexistente;
- retorno `checkout-payment-method-invalid`;
- permanência em `stage=payment`;
- ausência de mutação em dados da sessão;
- feedback customer-facing na página.

## Checkout Payment Method Hardening Wave 4 — Approach Closure Review

### Resultado

A abordagem igualou o hardening de pagamento ao de entrega.

### Decisão de encerramento

**Go para encerrar Checkout Payment Method Hardening neste ponto.**

O checkout agora rejeita seleção inválida de entrega e pagamento antes da revisão final, evitando drift silencioso.

### Fora de escopo preservado

- execução real de pagamento;
- retry de provider;
- split payment;
- antifraude;
- validação de cartão;
- regras financeiras avançadas;
- criação de pedido antecipada.

### Próxima abordagem recomendada

**Checkout Stage Guardrail Closure Review**

Revisar se entrega + pagamento + revisão já estão consistentes o suficiente para encerrar a frente de hardening do checkout, sem abrir provider/payment execution novamente.

## Checkout Stage Guardrail Closure Wave 1 — Stage Contract Review

### Revisão

O checkout possui guardrails coerentes por etapa:

- sessão sem itens fica em `cart`;
- tentativa de abrir `payment` sem entrega completa volta para `delivery`;
- tentativa de abrir `review` sem pagamento/termos volta para `payment` ou `delivery`;
- entrega inválida retorna `checkout-shipping-method-invalid`;
- pagamento inválido retorna `checkout-payment-method-invalid`;
- conclusão em `review` ainda passa por readiness, estoque e snapshot.

### Decisão

**Go para closure, sem nova feature de checkout.**

Não há blocker objetivo que justifique abrir nova implementação funcional nesta abordagem.

## Checkout Stage Guardrail Closure Wave 2 — Closure Test Coverage

### Cobertura adicionada

Foi adicionado teste explícito para pedido de `review` cedo demais:

- quando entrega está completa;
- pagamento ainda não está salvo;
- `requested_stage=review`;
- o serviço força `current_stage=payment`;
- exibe feedback de etapa ajustada;
- mantém hints coerentes.

### Propósito

Esse teste fecha a matriz de navegação:

- `payment` cedo demais → `delivery`;
- `review` cedo demais → `payment` quando entrega já existe;
- POST inválido de entrega → permanece em `delivery`;
- POST inválido de pagamento → permanece em `payment`.

## Checkout Stage Guardrail Closure Wave 3 — Approach Closure Review

### Resultado

A frente de hardening do checkout está suficiente para este ciclo.

### Decisão de encerramento

**Go para encerrar Checkout Stage Guardrail Closure.**

O checkout agora tem:

- progressão explícita `cart → delivery → payment → review`;
- rollback seguro de etapa solicitada cedo demais;
- validação explícita de entrega inválida;
- validação explícita de pagamento inválido;
- feedback customer-facing;
- testes de não-mutação para seleções inválidas;
- bloqueios de conclusão por readiness, estoque e snapshot.

### No-Go deliberado

Não avançar agora para:

- provider de pagamento real;
- cotação de frete por CEP;
- novo wizard;
- edição assíncrona por HTMX;
- validação de cartão;
- antifraude;
- reserva de estoque;
- criação antecipada de pedido.

### Próxima abordagem recomendada

**Storefront Checkout Copy & Trust Closure Review**

Revisar apenas se a copy customer-facing do checkout já transmite confiança suficiente antes de voltar para trilhas maiores como provider real, fulfillment ou analytics.

## Storefront Checkout Copy & Trust Closure Wave 1 — Copy Surface Review

### Revisão

O checkout já possuía boa copy contextual:

- alertas por etapa;
- hints de conclusão;
- explicação de pedido inicial;
- explicação de pagamento real pendente;
- readiness da revisão;
- mensagens para sessão inválida/expirada.

Lacuna leve encontrada:

- as garantias estavam espalhadas em alertas e descrições;
- faltava um bloco estável no sidebar reforçando por que é seguro seguir.

### Decisão

**Go para um bloco pequeno de confiança no checkout.**

**No-Go para redesign, nova etapa, novo provider ou alteração de regra transacional.**

## Storefront Checkout Copy & Trust Closure Wave 2 — Trust Sidebar Execution

### Execução

Foi adicionado o bloco `Compra com revisão segura` no sidebar do checkout.

O bloco reforça:

- pedido só nasce na revisão;
- pagamento real fica pendente;
- estoque é revalidado antes de criar pedido.

### Boundary preservada

- apenas contexto de apresentação em `checkout_page_queries`;
- template apenas renderiza copy;
- nenhum evento novo;
- nenhuma mutation nova;
- nenhuma alteração em pedido, pagamento, frete ou estoque.

## Storefront Checkout Copy & Trust Closure Wave 3 — Test Coverage

### Cobertura adicionada

O teste de revisão do checkout agora garante que a página exibe:

- `Compra com revisão segura`;
- `Pedido só nasce na revisão`;
- `Pagamento real fica pendente`;
- `Estoque é revalidado`.

## Storefront Checkout Copy & Trust Closure Wave 4 — Approach Closure Review

### Resultado

A experiência customer-facing do checkout está suficientemente clara para esta fase.

### Decisão de encerramento

**Go para encerrar Storefront Checkout Copy & Trust Closure.**

O checkout agora comunica:

- progressão por etapas;
- bloqueios seguros;
- diferença entre pedido inicial e pagamento real;
- revisão antes de criação do pedido;
- revalidação de estoque;
- estados inválidos de entrega/pagamento.

### No-Go deliberado

Não avançar agora para:

- redesenho completo de checkout;
- provider real de pagamento;
- validação de cartão;
- cotação real por CEP;
- reserva de estoque;
- analytics de funil;
- edição assíncrona por HTMX.

### Próxima abordagem recomendada

**System ROI Re-Selection Review**

Revisar o próximo eixo de maior retorno fora de micro-hardening de checkout, porque checkout/cart/storefront já atingiram boa suficiência incremental neste ciclo.
