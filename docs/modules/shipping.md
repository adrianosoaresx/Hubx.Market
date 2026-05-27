# Shipping

## Responsabilidade
Gerenciar frete e rastreio.

## Entidades principais
- Shipment

## Casos de uso
- cotar frete
- registrar envio
- registrar rastreio

## Regras de negócio
- shipment tem tracking code no MVP

## Wave AX — Shipping Product Experience Review
- a revisão do eixo de frete/entrega mostra que `shipping` ainda é mais contrato futuro do que módulo operacional implementado
- hoje a experiência real de entrega está distribuída em:
  - `checkout`
  - `accounts`
  - `orders`
- isso é aceitável para a fase atual, desde que a fronteira fique explícita

### Módulo responsável
- **`shipping`**
  - deve ser o módulo responsável por cotação, shipment e rastreio quando a integração logística amadurecer
- **`checkout`**
  - hoje apresenta métodos de entrega e captura endereço/frete da sessão
- **`orders`**
  - hoje controla o estado operacional do pedido:
    - preparo
    - envio
    - entrega concluída
- **`accounts`**
  - hoje traduz status de entrega para a experiência do cliente no detalhe do pedido

### O que já está forte
- **checkout**
  - a etapa de entrega já tem posição clara no fluxo
  - o resumo lateral já mostra frete e total
  - o cliente entende que entrega precisa estar pronta antes de pagamento/revisão
- **customer area**
  - o detalhe do pedido já comunica:
    - preparando envio
    - em trânsito
    - entregue
    - próximo passo esperado
  - a área do cliente já funciona como superfície de acompanhamento pós-compra
- **admin orders**
  - existe fluxo operacional para:
    - iniciar preparo
    - iniciar envio
    - confirmar entrega
  - há guards para não iniciar envio antes de pagamento/preparo
- **multi-tenant**
  - os fluxos de pedido/admin continuam usando `tenant_id`
  - não há indício nesta revisão de leitura cross-tenant no eixo de entrega

### Gaps de produto
- **cotação real**
  - `shipping` ainda não tem service de cotação implementado
  - os métodos de entrega aparecem como opções estruturais/fallback no checkout
- **prazo e promessa**
  - a experiência comunica prazo simples, mas ainda não separa bem:
    - prazo estimado
    - prazo após pagamento
    - prazo após postagem
    - risco de alteração
- **rastreio**
  - a documentação menciona tracking code no MVP
  - mas a superfície customer-facing ainda não parece ter contrato rico de rastreio
- **fronteira**
  - checkout/orders/accounts carregam bastante semântica de entrega
  - isso é prático agora, mas no futuro `shipping` deve assumir cotação/rastreio para evitar acoplamento crescente

### Leitura objetiva
- não há um bug pequeno e óbvio para corrigir nesta wave
- o próximo ganho de produto deve ser uma revisão focada em **clareza de entrega no checkout**
- não é hora de implementar integração logística real sem antes definir contrato de produto:
  - que promessa de prazo exibimos?
  - quando o frete vira definitivo?
  - como comunicamos alteração de prazo?
  - onde rastreio entra na experiência?

### Decisão prática
- manter `shipping` como módulo dono futuro de cotação/shipment/tracking
- no curto prazo, tratar a próxima evolução como copy/contrato de experiência em checkout e customer area
- preservar sem mudança por enquanto:
  - modelos
  - migrations
  - fluxo admin de orders
  - integração externa de frete
  - templates

### Próxima wave
- **Wave AY — Checkout Delivery Promise Review**
- foco:
  - revisar a promessa de entrega no checkout
  - separar preço/prazo/condição da entrega antes de qualquer execução

## Wave AY — Checkout Delivery Promise Review
- a revisão da promessa de entrega no checkout mostra que a superfície já comunica preço e prazo básico
- porém a copy atual ainda tende a parecer uma promessa absoluta de entrega
- como não há integração real de frete/rastreio nesta fase, a linguagem precisa deixar mais claro que o prazo é estimado e depende da sequência do pedido

### Superfícies revisadas
- **métodos de entrega**
  - `_fallback_shipping_methods`
  - hoje exibe:
    - “Entrega padrão”
    - “Receba em até 5 dias úteis.”
    - “Entrega expressa”
    - “Receba em até 2 dias úteis.”
- **etapa de entrega**
  - `_build_stage_context`
  - comunica endereço/frete como requisito para liberar pagamento e revisão
- **hints de conclusão**
  - `_build_completion_hints`
  - comunica “Contato, endereço e frete já estão salvos nesta sessão.”
- **resumo lateral**
  - `_build_summary_confidence_copy`
  - mostra frete e total, mas ainda não diferencia muito bem frete estimado vs. compromisso final
- **template**
  - `checkout_page.html`
  - apenas renderiza os dados recebidos; não precisa mudar neste recorte

### O que está correto
- entrega aparece antes de pagamento
- frete entra no total antes da revisão
- o checkout impede revisão/pagamento completo sem entrega selecionada
- o resumo lateral já mostra o impacto do frete no total
- a fronteira transacional permanece segura

### Gaps de experiência
- **prazo estimado**
  - “Receba em até X dias úteis” pode soar definitivo demais
  - melhor indicar que é uma estimativa da modalidade
- **condição da promessa**
  - o prazo real depende de:
    - endereço
    - pagamento confirmado
    - preparo/envio
  - isso ainda não aparece com clareza suficiente
- **frete definitivo**
  - o total considera o frete selecionado, mas a copy pode explicar melhor que ele é salvo na sessão/pedido inicial
- **sem integração real**
  - enquanto `shipping` não tiver cotação real, a linguagem deve evitar prometer mais do que o sistema consegue garantir

### Menor recorte seguro
- ajustar primeiro somente copy em `checkout_page_queries.py`:
  - `_fallback_shipping_methods`
  - `shipping_descriptions`
  - `delivery_hint`
  - copy de resumo para etapa `delivery` e `payment`, se necessário
- preservar sem mudança:
  - template
  - cálculo de frete
  - `CheckoutSession`
  - criação de pedido
  - `shipping` models
  - integração externa
  - admin orders

### Decisão prática
- a próxima execução deve ser uma passada curta de copy
- o objetivo não é implementar cotação real
- o objetivo é deixar a promessa de entrega mais honesta:
  - modalidade estimada
  - frete salvo na sessão
  - prazo condicionado ao pagamento/preparo/envio

### Próxima wave
- **Wave AZ — Checkout Delivery Promise Copy Execution**
- foco:
  - ajustar a linguagem de prazo/frete no checkout sem mudar regra ou template

## Wave AZ — Checkout Delivery Promise Copy Execution
- a primeira passada de copy da promessa de entrega foi executada no checkout
- a mudança ficou restrita a `checkout.application.checkout_page_queries`
- não houve alteração em cálculo, sessão, models, templates ou integração externa

### Escopo executado
- **métodos de entrega**
  - “Receba em até X dias úteis” virou estimativa da modalidade
  - a copy agora condiciona o prazo a:
    - pagamento confirmado
    - preparo do pedido
- **etapa de entrega**
  - endereço/frete agora são tratados como modalidade estimada da sessão
  - isso reduz a chance de o cliente ler o prazo como promessa definitiva
- **hints de conclusão**
  - entrega salva agora comunica “frete estimado”
  - entrega incompleta orienta selecionar modalidade estimada
- **resumo lateral**
  - etapa de entrega agora fala em frete estimado
  - etapa de pagamento reforça que prazo/envio ainda dependem de pagamento confirmado e preparo

### O que não mudou
- cálculo de frete
- persistência de `CheckoutSession`
- template do checkout
- criação de pedido
- `shipping` models
- integração externa de cotação/rastreio
- fluxo admin de envio/entrega

### Leitura prática
- a promessa de entrega ficou mais honesta para a fase atual
- o cliente ainda vê preço e prazo
- mas agora entende melhor que o prazo é uma estimativa até o pedido avançar para pagamento/preparo/envio

### Próxima wave
- **Wave BA — Customer Delivery Tracking Experience Review**
- foco:
  - revisar como a área do cliente comunica preparo, envio, trânsito e entrega
  - decidir se falta uma camada leve de tracking sem implementar integração logística real

## Wave BA — Customer Delivery Tracking Experience Review
- a revisão da área do cliente mostra que já existe uma boa base de acompanhamento de entrega
- a experiência atual ainda é mais “linha do tempo do pedido” do que tracking de entrega
- isso é aceitável sem integração logística real, mas existe espaço para deixar a camada de entrega mais explícita

### Superfícies revisadas
- **`accounts.application.account_customer_area_queries`**
  - `_customer_order_next_step`
  - `_customer_order_milestone_title`
  - `_current_state_helper`
  - `_timeline_items`
  - payload persistido do detalhe do pedido
- **`order_detail_page`**
  - renderiza status atual
  - renderiza resumo do pedido
  - renderiza activity feed
  - não possui bloco dedicado de tracking
- **testes de customer area**
  - já cobrem:
    - pedido em preparação
    - pedido em trânsito
    - pedido entregue
    - próximos passos

### O que já está forte
- **preparo**
  - o cliente entende que o próximo passo é confirmação de envio
  - a página se posiciona como lugar de acompanhamento
- **envio/trânsito**
  - o estado “em trânsito” já aparece como pedido enviado
  - a área do cliente comunica que a entrega está avançando
- **entrega concluída**
  - o pedido entregue vira histórico
  - a experiência já preserva retorno ao catálogo sem perder contexto
- **timeline**
  - já há marcos de pedido, pagamento/entrega e próximo passo esperado

### Gaps de experiência
- **tracking leve**
  - não existe um bloco explícito de “Acompanhamento da entrega”
  - a informação fica misturada à timeline geral do pedido
- **sem tracking code**
  - o módulo `shipping` documenta tracking code no MVP
  - mas a área do cliente ainda não tem contrato customer-facing para código/link de rastreio
- **estado de preparo vs. envio**
  - “preparando envio”, “separando itens” e “em trânsito” estão corretos
  - mas a copy pode explicar melhor o que muda entre esses marcos
- **expectativa do próximo evento**
  - o cliente lê o próximo passo, mas não há uma descrição dedicada de “o que esperar da entrega”

### Menor recorte seguro
- antes de implementar tracking real, revisar uma camada de copy/payload leve em `accounts.application.account_customer_area_queries`
- possível recorte:
  - `delivery_tracking_title`
  - `delivery_tracking_description`
  - `delivery_tracking_state`
  - `delivery_tracking_visible`
- renderização pode usar componente existente de alert/card se necessário
- preservar sem mudança por enquanto:
  - `shipping` models
  - tracking code real
  - integração logística
  - admin orders
  - estados de `Order`

### Decisão prática
- não implementar rastreio real agora
- o próximo passo deve definir e executar uma camada leve de acompanhamento de entrega na área do cliente
- essa camada deve traduzir estados existentes, não criar novos estados operacionais

### Próxima wave
- **Wave BB — Customer Delivery Tracking Copy Plan**
- foco:
  - planejar a menor camada customer-facing para acompanhamento de entrega
  - decidir se basta copy/payload ou se precisa pequeno ajuste de template

## Wave BB — Customer Delivery Tracking Copy Plan
- o plano para tracking leve deve ficar centrado na área do cliente
- a execução não deve criar rastreio real, tracking code, provider logístico ou novos estados operacionais
- o objetivo é traduzir os estados já existentes em uma camada mais explícita de acompanhamento de entrega

### Contrato proposto
- adicionar payload derivado em `accounts.application.account_customer_area_queries`
- campos sugeridos:
  - `delivery_tracking_visible`
  - `delivery_tracking_variant`
  - `delivery_tracking_icon`
  - `delivery_tracking_title`
  - `delivery_tracking_description`
- origem dos dados:
  - `order_status_label`
  - `payment_status`
  - `shipping_status`
  - `fulfillment_status_label`

### Estados de copy
- **aguardando pagamento**
  - ocultar tracking dedicado ou manter foco em pagamento
  - entrega ainda não deve parecer iniciada
- **pagamento confirmado / aguardando preparo**
  - título sugerido: “Entrega ainda em preparação”
  - descrição: pedido salvo, pagamento confirmado, próximo marco é preparo/envio
- **separando / preparando envio**
  - título sugerido: “Preparando seu pedido”
  - descrição: itens estão em preparação; próximo marco é saída para envio
- **em trânsito / enviado**
  - título sugerido: “Pedido a caminho”
  - descrição: entrega avançou para transporte; atualizações aparecerão nesta página
- **entregue / concluído**
  - título sugerido: “Entrega concluída”
  - descrição: pedido encerrado e preservado no histórico
- **cancelado**
  - título sugerido: “Entrega sem novas movimentações”
  - descrição: pedido cancelado não terá avanço de entrega

### Superfície de UI
- usar componente existente:
  - `shared/components/feedback/alert.html`
- posição sugerida:
  - coluna lateral do `order_detail_page`
  - antes da timeline geral
- motivo:
  - dá destaque suficiente
  - não exige novo componente
  - mantém a timeline geral como histórico amplo

### Menor execução segura
- criar helper puro em `account_customer_area_queries.py`, por exemplo:
  - `_delivery_tracking_guidance(...)`
- incluir payload no retorno do detalhe do pedido
- renderizar o alert somente quando `delivery_tracking_visible` for verdadeiro
- adicionar testes em `test_customer_area_views.py` para:
  - preparação
  - trânsito
  - entregue
  - cancelado ou pendente sem tracking dedicado

### Fora de escopo
- tracking code real
- link de rastreio
- provider logístico
- `shipping` models
- novas migrations
- admin orders
- alteração de estados de pedido

### Próxima wave
- **Wave BC — Customer Delivery Tracking Copy Execution**
- foco:
  - implementar helper + payload + alert simples no detalhe do pedido
  - cobrir os estados principais com testes

## Wave BC — Customer Delivery Tracking Copy Execution
- a camada leve de acompanhamento de entrega foi implementada na área do cliente
- a execução traduziu estados existentes de pedido/entrega em um alerta customer-facing
- não foram criados novos estados operacionais nem integração logística real

### Escopo executado
- **helper**
  - criado helper derivado em `accounts.application.account_customer_area_queries`
  - ele avalia:
    - status do pedido
    - status do pagamento
    - status de entrega
    - status operacional/fulfillment
- **payload**
  - o detalhe do pedido agora expõe:
    - `delivery_tracking_visible`
    - `delivery_tracking_variant`
    - `delivery_tracking_icon`
    - `delivery_tracking_title`
    - `delivery_tracking_description`
- **UI**
  - `order_detail_page` renderiza um `alert.html` antes da timeline geral quando o tracking leve está visível
- **testes**
  - cobertura adicionada para:
    - preparação
    - pedido em trânsito
    - pedido entregue
    - pagamento pendente sem tracking dedicado

### Estados implementados
- pagamento pendente/falhou:
  - tracking dedicado fica oculto
  - foco permanece em pagamento
- preparação:
  - “Preparando seu pedido”
- trânsito/envio:
  - “Pedido a caminho”
- entregue/concluído:
  - “Entrega concluída”
- cancelado:
  - “Entrega sem novas movimentações”

### O que não mudou
- `shipping` models
- tracking code real
- link de rastreio
- provider logístico
- admin orders
- estados de pedido
- migrations

### Leitura prática
- a área do cliente agora diferencia melhor acompanhamento de entrega da timeline geral
- a timeline continua existindo como histórico amplo
- o alerta de entrega dá orientação imediata sem prometer rastreio real

### Próxima wave
- **Wave BD — Shipping Product Experience Wrap-Up Review**
- foco:
  - revisar se o eixo de frete/entrega pode ser encerrado nesta fase
  - separar roadmap futuro de cotação real, tracking code e integração logística

## Wave BD — Shipping Product Experience Wrap-Up Review
- o eixo de frete/entrega pode ser considerado encerrado nesta fase
- a trilha melhorou a experiência sem antecipar uma integração logística que ainda não existe
- a fronteira futura de `shipping` ficou mais clara

### O que ficou pronto nesta fase
- **contrato de módulo**
  - `shipping` segue como dono futuro de cotação, shipment e rastreio
  - `checkout`, `orders` e `accounts` continuam responsáveis pelas superfícies atuais
- **checkout**
  - prazo/frete agora são comunicados como estimativa da modalidade
  - a promessa de entrega ficou condicionada a pagamento confirmado e preparo do pedido
- **customer area**
  - detalhe do pedido ganhou tracking leve customer-facing
  - preparo, trânsito, entrega concluída e cancelamento agora têm leitura mais explícita
- **fronteiras**
  - não foram criados models, migrations, tracking code fake ou integração externa
  - `orders` continua dono dos estados operacionais
  - `accounts` traduz estado para cliente

### Roadmap futuro
- cotação real por CEP/endereço
- contrato de método de entrega vindo de `shipping`
- tracking code e link de rastreio
- integração com provider logístico
- eventos de shipment:
  - `shipment.created`
  - `shipment.in_transit`
  - `shipment.delivered`
- painel admin/logístico dedicado
- suporte a alteração de prazo e exceções de entrega

### Leitura objetiva
- o produto agora é mais honesto sobre promessa de entrega
- a área do cliente acompanha melhor o estado de envio sem prometer rastreio real
- o que falta já é roadmap logístico maior, não microcopy ou boundary pequeno

### Decisão prática
- encerrar o eixo de **Shipping Product Experience** nesta fase
- seguir para outro módulo funcional ainda pouco explorado no roadmap de produto

### Próxima wave
- **Wave BE — Notifications Product Experience Review**
- foco:
  - revisar notificações como experiência de produto
  - mapear onde eventos de pedido/pagamento/entrega ainda não viram comunicação útil para owner/customer

## Wave DY — Shipping Event Publisher Review
- `shipping` ainda não possui `Shipment` persistido nem comandos reais de rastreio/envio.
- por isso, não é seguro integrar eventos logísticos a partir de estados derivados em `orders` ou `accounts`.
- o menor passo seguro é criar uma boundary de publisher no próprio módulo `shipping`.

### Decisão prática
- criar publisher para `shipment.sent` e `shipment.delivered`
- não ligar o publisher a fluxo operacional inexistente
- não criar tracking code fake
- manter notifications como subscriber

## Wave DZ — Shipping Event Publisher Execution
- foi criado publisher mínimo de eventos logísticos.
- ele publica eventos por `tenant_id + order_number`, mas ainda não é chamado automaticamente por nenhum fluxo real.

### Escopo executado
- `shipping.application.shipping_event_publisher`
- `publish_shipment_sent`
- `publish_shipment_delivered`
- testes unitários do publisher

### Próxima wave
- **Wave EA — Shipping Event Publisher Closure**
- foco:
  - validar boundary
  - decidir próximo passo logístico real

## Wave EA — Shipping Event Publisher Closure
- a abordagem Shipping Event Publisher está fechada.
- a boundary para eventos logísticos existe, mas nenhum fluxo real a aciona ainda.

### Pronto
- publisher de `shipment.sent`
- publisher de `shipment.delivered`
- subscriber de notifications preparado
- testes unitários

### Bloqueio real
- ainda não existe entidade `Shipment`
- ainda não existe tracking code persistido
- ainda não existe comando administrativo/logístico para marcar envio/entrega no módulo `shipping`

### Próxima macro-abordagem recomendada
- **Shipment Minimal Model & Commands**
- motivo:
  - para acionar eventos reais de shipping, precisamos primeiro persistir shipment e comandos tenant-scoped

## Wave EB — Shipment Minimal Model Execution
- `Shipment` foi implementado como entidade mínima persistida.
- ele pertence a um tenant e a um pedido.
- ainda não há provider logístico externo.

### Escopo executado
- `shipping.models.Shipment`
- migration inicial de `shipping`
- status:
  - `created`
  - `sent`
  - `delivered`
  - `canceled`
- campos de rastreio:
  - `tracking_code`
  - `tracking_url`
  - `carrier_name`
- teste de persistência básica

### Próxima wave
- **Wave EC — Shipment Command Execution**
- foco:
  - criar comandos tenant-scoped para marcar enviado/entregue
  - publicar eventos logísticos reais

## Wave EC — Shipment Command Execution
- comandos tenant-scoped de shipment foram implementados.
- `shipment.sent` e `shipment.delivered` agora podem ser publicados a partir de transições reais de `Shipment`.

### Escopo executado
- `shipment_commands.mark_shipment_sent`
- `shipment_commands.mark_shipment_delivered`
- criação automática de shipment ao marcar envio
- publicação de:
  - `shipment.sent`
  - `shipment.delivered`
- testes de:
  - envio
  - entrega
  - idempotência de envio
  - idempotência de entrega
  - bloqueio de entrega antes do envio
  - isolamento entre tenants

### Próxima wave
- **Wave ED — Shipment Minimal Model & Commands Closure**
- foco:
  - validar integração com notifications
  - registrar limites restantes

## Wave ED — Shipment Minimal Model & Commands Closure
- a abordagem mínima de shipment está fechada.
- eventos logísticos agora nascem de transições persistidas e tenant-scoped.

### Pronto
- `Shipment` mínimo persistido
- comando de envio cria/atualiza shipment e publica `shipment.sent`
- comando de entrega exige shipment enviado e publica `shipment.delivered`
- idempotência evita republicação em reexecuções
- cross-tenant access retorna indisponível sem criar shipment

### Limites restantes
- ainda não há UI/admin operacional de logística
- ainda não há provider externo de tracking
- ainda não há histórico detalhado de status logístico

### Próxima macro-abordagem recomendada
- **Shipping Admin Operations UI**
- motivo:
  - comandos existem, mas operadores ainda não têm superfície interna para marcar envio/entrega com segurança

## Wave EE — Shipping Admin Operations UI Execution
- foi criada uma superfície interna em `/ops/shipping/`.
- a UI reutiliza o template operacional de listagem existente e chama comandos tenant-scoped.

### Escopo executado
- listagem de pedidos por tenant para operação logística
- ação de marcar shipment como enviado
- ação de confirmar entrega
- feedback operacional via query param `result`
- isolamento por subdomínio/tenant

### Eventos acionados pela UI
- `shipment.sent`
- `shipment.delivered`

### Próxima wave
- **Wave EF — Shipping Admin Operations UI Closure**
- foco:
  - validar com testes de view
  - registrar limites restantes da operação logística

## Wave EF — Shipping Admin Operations UI Closure
- a UI operacional de shipping está pronta e validada.
- operadores internos já podem acionar `shipment.sent` e `shipment.delivered` sem shell.

### Limite residual
- os atalhos antigos de `/ops/orders/` ainda precisam chamar os mesmos comandos para evitar divergência entre estado de pedido e shipment.

### Próxima macro-abordagem recomendada
- **Orders Shipping Command Integration**
- motivo:
  - `start_shipping` e `complete_delivery` já existem em orders e devem reutilizar o boundary de shipping.

## Wave EG — Orders Shipping Command Integration
- ações logísticas de `/ops/orders/` agora reutilizam `shipping.application.shipment_commands`.

### Escopo executado
- `start_shipping` marca shipment como enviado
- `complete_delivery` marca shipment como entregue
- pedidos legados em trânsito sem shipment recebem backfill mínimo antes da entrega
- testes de orders passam a verificar `Shipment` persistido

## Wave EH — Shipment Audit Trail Execution
- shipment agora possui histórico próprio de status.
- comandos de shipping registram trilha operacional apenas quando há transição real.

### Escopo executado
- `ShipmentStatusHistory`
- migration incremental de shipping
- histórico para:
  - `shipment_sent`
  - `shipment_delivered`
- source/actor explícitos:
  - `Shipping Commands`
  - `Operação interna`
- idempotência sem duplicar histórico

### Limites restantes
- a UI ainda não exibe timeline própria de shipment.
- histórico ainda é operacional interno, não event store distribuído.

### Próxima macro-abordagem recomendada
- **Shipping Admin Timeline Visibility**
- motivo:
  - a trilha já existe, mas operadores ainda não conseguem visualizá-la em `/ops/shipping/`.

## Wave EI — Shipping Admin Timeline Visibility
- `/ops/shipping/` agora expõe resumo de histórico logístico por pedido.
- a listagem mostra as últimas transições registradas em `ShipmentStatusHistory`.

### Escopo executado
- contrato de query com `history_summary`
- coluna `Histórico` na UI operacional de shipping
- teste de renderização da timeline

### Fechamento da abordagem
- a operação logística mínima agora cobre:
  - persistência de shipment
  - comandos tenant-scoped
  - eventos de notifications
  - UI operacional
  - trilha de auditoria visível

### Próxima macro-abordagem recomendada
- **Shipping Provider Boundary Review**
- motivo:
  - o sistema já tem operação manual segura; o próximo gargalo é formalizar boundary para provider externo/rastreio real.

## Wave EJ — Shipping Provider Boundary Execution
- foi criado o primeiro contrato de provider de shipping.
- o adapter inicial lê o `Shipment` persistido e expõe um snapshot de tracking sem chamar fornecedor externo.

### Escopo executado
- `TrackingSnapshot`
- `ShippingProviderGateway`
- `ManualShipmentProviderGateway`
- admin shipping passa a consumir rastreio pelo gateway manual
- testes de tracking snapshot e isolamento por tenant

### Limites explícitos
- ainda não há API externa de rastreio.
- ainda não há polling assíncrono.
- ainda não há normalização entre status de múltiplas transportadoras.

### Próxima macro-abordagem recomendada
- **Shipping Tracking Normalization Review**
- motivo:
  - antes de provider real, precisamos definir o vocabulário interno de status externos para não vazar semântica de transportadora para produto.

## Wave EK — Shipping Tracking Normalization Execution
- foi criado vocabulário interno normalizado para tracking.
- provider/manual adapter mantém `provider_status` cru, mas expõe `normalized_status` para produto/UI.

### Vocabulário interno inicial
- `missing`
- `created`
- `in_transit`
- `delivered`
- `canceled`
- `unknown`

### Escopo executado
- `tracking_status_normalizer`
- `TrackingSnapshot.normalized_status`
- `TrackingSnapshot.terminal`
- admin shipping passa a renderizar status normalizado
- testes de mapeamento e fallback desconhecido

### Próxima macro-abordagem recomendada
- **Customer Tracking Surface Review**
- motivo:
  - status e tracking já estão normalizados; o próximo passo de produto é decidir onde isso aparece para o cliente sem vazar ruído operacional.

## Wave EL — Customer Tracking Surface Execution
- o detalhe do pedido do cliente passa a consumir snapshot normalizado de tracking.
- a superfície mantém fallback textual quando não há shipment/rastreio e mostra transportadora/código quando existem.

### Escopo executado
- `account_customer_area_queries` consulta `ManualShipmentProviderGateway`
- contrato customer-facing inclui:
  - `delivery_tracking_status`
  - `delivery_tracking_code`
  - `delivery_tracking_url`
  - `delivery_tracking_carrier`
- copy de acompanhamento usa status normalizado e dados de rastreio disponíveis
- teste garante renderização de transportadora e código no detalhe do pedido

### Próxima macro-abordagem recomendada
- **Customer Tracking Link UX Review**
- motivo:
  - o contrato já carrega `tracking_url`, mas a UI ainda não oferece CTA/link dedicado para acompanhar no provider.

## Wave EM — Customer Tracking Link UX Execution
- o detalhe do pedido do cliente agora exibe CTA externo quando `tracking_url` existe.

### Escopo executado
- `delivery_tracking_action_label`
- link externo com `target="_blank"` e `rel="noopener noreferrer"`
- teste de renderização do CTA e URL de rastreio

### Fechamento da abordagem
- cliente agora tem:
  - status normalizado
  - transportadora
  - código de rastreio
  - CTA para provider quando disponível

### Próxima macro-abordagem recomendada
- **Shipping Provider Polling Plan**
- motivo:
  - a experiência customer-facing já consome tracking; o próximo gargalo é atualizar snapshots automaticamente sem ação manual.

## Wave EN — Shipping Provider Polling Execution
- foi criado serviço de sincronização de tracking por snapshot de provider.
- a implementação ainda usa o gateway manual como default, mas aceita gateway injetado para provider real futuro.

### Escopo executado
- `shipment_tracking_sync`
- aplicação tenant-scoped de snapshot por `tenant_id + order_number`
- transições suportadas:
  - `in_transit` → shipment enviado
  - `delivered` → shipment enviado/entregue
  - `canceled` → shipment cancelado
- atualização de código/link/transportadora sem transição
- idempotência para shipments já entregues
- publicação de eventos `shipment.sent` e `shipment.delivered` apenas em transições reais

## Wave EO — Shipping Tracking Sync Command Execution
- foi criado comando operacional/agendável `sync_shipments_tracking`.

### Escopo executado
- filtro opcional por `--tenant-id`
- limite por `--limit`
- processa shipments não terminais (`created`, `sent`)
- sumariza resultados por código de retorno

### Limites explícitos
- ainda não há Celery beat configurado para polling automático.
- ainda não há provider HTTP real.
- ainda não há política de backoff/rate limit por transportadora.

### Próxima macro-abordagem recomendada
- **Shipping Provider HTTP Adapter Contract**
- motivo:
  - polling interno existe; falta definir adapter HTTP real com timeout, parsing e falha segura.

## Wave EP — Shipping Provider HTTP Adapter Contract Execution
- foi criado adapter HTTP inicial para provider de tracking.
- ele é fail-safe: em timeout/erro/payload inválido, retorna o snapshot manual/local.

### Escopo executado
- `HttpTrackingProviderGateway`
- `parse_tracking_provider_payload`
- transporte injetável para testes
- timeout configurável
- header `Authorization: Bearer ...` opcional
- endpoint padrão:
  - `/tracking/{tracking_code}`

### Segurança operacional
- não chama provider quando não há `tracking_code`.
- não deixa exceção de provider vazar para UI/comandos.
- status externo continua passando pelo normalizador interno.

### Próxima macro-abordagem recomendada
- **Shipping Provider Settings Contract**
- motivo:
  - adapter existe, mas ainda não há configuração por tenant/provider para base URL, token e ativação controlada.

## Wave EQ — Shipping Provider Settings Contract Execution
- foi criado contrato persistido de configuração de provider por tenant.

### Escopo executado
- `ShippingProviderSettings`
- `shipping_provider_settings.get_gateway_for_tenant`
- fallback automático para provider manual quando:
  - não há settings
  - settings está inativo
  - provider não é `http`
  - `base_url` está ausente
- comando `sync_shipments_tracking` passa a resolver gateway por tenant

### Campos iniciais
- `provider_name`
- `base_url`
- `api_token`
- `timeout_seconds`
- `is_active`

### Limites explícitos
- `api_token` ainda é campo simples; secret manager/criptação ficam para hardening posterior.
- ainda não há UI admin para ativar/desativar provider.

### Próxima macro-abordagem recomendada
- **Shipping Provider Admin Settings UI**
- motivo:
  - settings existem, mas ainda dependem de seed/shell/admin técnico para configuração.

## Wave ER — Shipping Provider Admin Settings UI Execution
- foi criada UI interna para configurar provider de tracking por tenant.

### Escopo executado
- `/ops/shipping/provider/`
- update tenant-scoped de:
  - provider
  - base URL
  - token
  - timeout
  - ativação
- validação de base URL obrigatória quando HTTP ativo
- fallback manual/local visível
- testes de renderização, update e isolamento entre tenants

### Limites explícitos
- token ainda é exibido como campo de entrada simples no update; próxima etapa deve endurecer armazenamento/rotação.
- ainda não há auditoria própria de alteração de settings.

### Próxima macro-abordagem recomendada
- **Shipping Provider Secret Hardening**
- motivo:
  - o token do provider já existe no contrato e UI, mas ainda precisa de tratamento mais seguro para produção real.

## Wave ES — Shipping Provider Secret Hardening Execution
- a UI de provider não ecoa token salvo.
- update com token vazio preserva o segredo existente.

### Escopo executado
- estado `token_configured`
- placeholder seguro quando token já existe
- coluna de token mostra apenas `Configurado` / `Não configurado`
- token só é substituído quando novo valor é enviado
- testes de masking e preservação

### Limites restantes
- o token ainda fica persistido em campo simples.
- próxima evolução de produção deve usar secret manager, criptografia em repouso ou referência externa.

### Próxima macro-abordagem recomendada
- **Shipping Provider Audit Trail**
- motivo:
  - alterações de provider agora são possíveis via UI; falta trilha de auditoria dessas mudanças.

## Wave ET — Shipping Provider Audit Trail Execution
- alterações de settings do provider agora geram histórico tenant-scoped.

### Escopo executado
- `ShippingProviderSettingsHistory`
- registro automático em update via UI/service
- resumo de histórico em `/ops/shipping/provider/`
- testes de criação e renderização da trilha

### Fechamento da abordagem de provider
- provider HTTP tem:
  - contrato
  - parser
  - fallback seguro
  - settings por tenant
  - UI interna
  - token mascarado/preservado
  - auditoria de mudanças

### Próxima macro-abordagem recomendada
- **Shipping Celery Polling Activation**
- motivo:
  - sync e settings já existem; falta ativar recorrência assíncrona real em Celery/beat.

## Wave EU — Shipping Celery Polling Task Execution
- foram criadas tasks Celery para sincronização de tracking.

### Escopo executado
- `shipping.sync_shipment_tracking`
- `shipping.sync_pending_shipments_tracking`
- limite seguro por lote:
  - padrão `100`
  - máximo `250`
- cache de gateway por tenant durante o lote
- ignora shipments terminais
- testes com `.run()` seguindo padrão de notifications

### Ativação recomendada
- usar Celery beat/cron para chamar `shipping.sync_pending_shipments_tracking`
- parâmetros iniciais sugeridos:
  - `tenant_id=""`
  - `limit=100`
- frequência inicial sugerida:
  - a cada 10–15 minutos em produção

### Limites explícitos
- beat ainda não foi configurado no settings.
- não há rate limit por provider.
- não há métrica dedicada de resultado do polling.

### Próxima macro-abordagem recomendada
- **Shipping Polling Observability**
- motivo:
  - polling já pode rodar; falta visibilidade operacional dos resultados por status/tenant.

## Wave EV — Shipping Polling Observability Execution
- foi criado endpoint protegido de métricas Prometheus para o módulo de shipping.
- a primeira superfície cobre volume de shipments e histórico operacional por tenant.

### Escopo executado
- `/ops/shipping/metrics/`
- token obrigatório via:
  - `SHIPPING_OBSERVABILITY_TOKEN`
  - fallback compatível para `NOTIFICATIONS_OBSERVABILITY_TOKEN`
- formatos aceitos:
  - header `X-Hubx-Observability-Token`
  - header `Authorization: Bearer ...`
- métricas exportadas:
  - `hubx_shipping_shipment_total{tenant_id,status}`
  - `hubx_shipping_history_event_total{tenant_id,event_type}`
- testes de:
  - export Prometheus
  - token válido
  - token inválido
  - endpoint oculto quando nenhum token está configurado

### Leitura operacional
- o polling de tracking agora tem sinais básicos para Prometheus/Grafana.
- a granularidade por `tenant_id` permite investigar concentração de problemas por loja.
- `status` e `event_type` dão visibilidade inicial sobre:
  - shipments criados/parados
  - shipments enviados/entregues/cancelados
  - atividade de sync/provider/admin no histórico

### Limites explícitos
- ainda não há regra de alerta dedicada para shipping.
- ainda não há dashboard Grafana dedicado.
- ainda não há métrica de duração, erro de provider ou timestamp do último sync.

### Próxima macro-abordagem recomendada
- **Shipping Prometheus Alert Rules**
- motivo:
  - o endpoint já exporta métricas; falta transformar esses sinais em alertas operacionais mínimos.

## Wave EW — Shipping Prometheus Alert Rules Execution
- foram criadas regras iniciais de Prometheus para o polling/rastreio de shipping.
- o objetivo é detectar backlog, cancelamentos e ausência de atividade de sync sem depender de dashboard manual.

### Escopo executado
- `infra/observability/prometheus/shipping-alert-rules.yml`
- `infra/observability/prometheus/shipping-scrape.example.yml`
- atualização do runbook de observabilidade em `infra/observability/README.md`

### Alertas iniciais
- `HubxShippingCreatedBacklogHigh`
  - dispara quando há mais de 100 shipments em `created` por 30 minutos
- `HubxShippingCanceledShipmentsPresent`
  - dispara quando existem shipments em `canceled`
- `HubxShippingNoTrackingSyncActivity`
  - dispara quando há shipments não terminais, mas nenhum evento `shipment_tracking_synced` recente

### Leitura operacional
- as regras são conservadoras e usam apenas métricas já exportadas.
- a ativação real depende de:
  - scrape do endpoint `/ops/shipping/metrics/`
  - token `SHIPPING_OBSERVABILITY_TOKEN`
  - scheduler chamando `shipping.sync_pending_shipments_tracking`

### Limites explícitos
- ainda não há dashboard Grafana dedicado para shipping.
- ainda não há roteamento Alertmanager dedicado para shipping.
- alertas de latência/provider error exigem novas métricas específicas.

### Próxima macro-abordagem recomendada
- **Shipping Grafana Dashboard**
- motivo:
  - alertas existem; falta uma visão operacional inicial para status por tenant e eventos de histórico.

## Wave EX — Shipping Grafana Dashboard Execution
- foi criado dashboard inicial de Grafana para polling/rastreio de shipping.
- o painel acompanha os mesmos sinais usados pelos alertas, com foco em operação rápida.

### Escopo executado
- `infra/observability/grafana/shipping-polling-dashboard.json`
- atualização do runbook de observabilidade para importação do dashboard

### Painéis iniciais
- shipments criados
- shipments cancelados
- distribuição de shipments por status
- eventos de histórico de shipping na última hora

### Leitura operacional
- o dashboard serve para triagem:
  - backlog de shipments ainda não enviados
  - cancelamentos
  - atividade recente do sync
  - evolução dos status principais

### Limites explícitos
- ainda não há variável de filtro por tenant no dashboard.
- ainda não há painel de erro/latência por provider.
- granularidade de última execução exige métrica dedicada futura.

### Próxima macro-abordagem recomendada
- **Shipping Alertmanager Routing**
- motivo:
  - scrape, regras e dashboard existem; falta exemplo de roteamento inicial para o domínio de shipping.

## Wave EY — Shipping Alertmanager Routing Execution
- foi criado exemplo inicial de roteamento Alertmanager para alertas de shipping.
- o padrão segue os domínios já existentes de payments e notifications.

### Escopo executado
- `infra/observability/alertmanager/shipping-routing.example.yml`
- atualização do runbook de observabilidade para incluir o roteamento

### Contrato de labels
- `domain="shipping"`
- `severity="warning"`
- `severity="critical"`

### Leitura operacional
- todos os alertas atuais de shipping são `warning`.
- o receiver `shipping-critical` fica preparado para regras futuras mais severas:
  - provider indisponível
  - falha massiva de sync
  - erro de credencial/token

### Fechamento da abordagem de observabilidade shipping
- shipping agora tem:
  - endpoint Prometheus protegido
  - scrape example
  - alert rules
  - dashboard Grafana inicial
  - routing Alertmanager example

### Próxima macro-abordagem recomendada
- **Shipping Provider Error Metrics**
- motivo:
  - a observabilidade básica está completa; a próxima evolução útil é medir falhas/latência do provider em vez de inferir apenas por ausência de sync.

## Wave EZ — Shipping Provider Error Metrics Execution
- falhas do provider HTTP de tracking agora deixam sinal explícito no contrato de sync.
- em vez de falhar silenciosamente apenas com fallback manual, o snapshot passa a carregar metadados de erro e o sync registra histórico tenant-scoped.

### Escopo executado
- `TrackingSnapshot.provider_error_code`
- `TrackingSnapshot.provider_error_message`
- `TrackingSnapshot.has_provider_error`
- erro `transport_error` para exceções no transporte HTTP
- erro `invalid_payload` para payload não-objeto
- evento `shipment_tracking_provider_failed`
- alerta `HubxShippingProviderFailuresPresent`
- stat “Falhas provider (1h)” no dashboard Grafana

### Leitura operacional
- o customer/admin continuam protegidos por fallback local/manual.
- a operação deixa de depender apenas de ausência de sync para suspeitar de provider com problema.
- o evento entra na métrica já existente:
  - `hubx_shipping_history_event_total{event_type="shipment_tracking_provider_failed"}`

### Limites explícitos
- ainda não há métrica de latência do provider.
- ainda não há classificação por HTTP status code.
- erros repetidos podem gerar múltiplos eventos de histórico enquanto o polling continuar falhando.

### Próxima macro-abordagem recomendada
- **Shipping Provider Latency/Status Contract**
- motivo:
  - erros agora aparecem; a próxima camada seria capturar tempo de resposta e status externo sem misturar isso com regra de domínio.

## Wave FA — Shipping Provider Latency/Status Contract Execution
- o contrato de snapshot de tracking passou a carregar telemetria mínima do provider HTTP.
- a mudança fica no boundary de infraestrutura/aplicação e não cria persistência nova.

### Escopo executado
- `TrackingSnapshot.provider_http_status`
- `TrackingSnapshot.provider_latency_ms`
- `TrackingTransportResult`
- `HttpTrackingProviderGateway` mede duração da chamada
- `urllib_tracking_transport` retorna payload e status HTTP quando disponível
- histórico de erro do provider inclui status HTTP e latência quando presentes

### Leitura operacional
- falhas de provider agora podem ser investigadas com:
  - código de erro interno
  - classe da exceção
  - status HTTP, quando o transporte informa
  - duração da chamada em milissegundos
- o customer-facing continua usando fallback local/manual.
- a telemetria não altera transições de shipment.

### Limites explícitos
- status/latência ainda não são métricas Prometheus dedicadas.
- não há histograma de latência.
- não há agregação por status HTTP.

### Próxima macro-abordagem recomendada
- **Shipping Provider Metrics Enrichment**
- motivo:
  - o contrato já carrega status/latência; a próxima etapa é decidir como exportar isso sem inflar o modelo de domínio.

## Wave FB — Shipping Provider Metrics Enrichment Execution
- a telemetria do provider passou a ser persistida de forma opcional em `ShipmentStatusHistory`.
- o exporter Prometheus agora expõe status HTTP e latência média do provider.

### Escopo executado
- `ShipmentStatusHistory.provider_http_status`
- `ShipmentStatusHistory.provider_latency_ms`
- índice por `tenant + provider_http_status`
- propagação da telemetria do snapshot para eventos de sync
- novas métricas:
  - `hubx_shipping_provider_http_status_total{tenant_id,http_status}`
  - `hubx_shipping_provider_latency_ms_avg{tenant_id,event_type}`
- alertas adicionais:
  - `HubxShippingProviderHttp5xxPresent`
  - `HubxShippingProviderLatencyHigh`
- dashboard atualizado com:
  - latência média do provider
  - distribuição de HTTP status por hora

### Leitura operacional
- o histórico segue tenant-scoped.
- eventos antigos ficam com telemetria nula.
- o exporter só considera status/latência quando os campos estão preenchidos.

### Limites explícitos
- a métrica de latência ainda é média simples, não histograma.
- status HTTP depende de transporte que informe status.
- ainda não há retenção/compactação dedicada para histórico de polling.

### Próxima macro-abordagem recomendada
- **Shipping Polling Retention Review**
- motivo:
  - com mais eventos de sync e métricas derivadas do histórico, vale revisar se precisamos de política de retenção/volume para não transformar observabilidade em crescimento indefinido.

## Wave FC — Shipping Polling Retention Execution
- foi criado comando operacional para remover histórico antigo de shipping com escopo seguro.
- o objetivo é controlar crescimento de eventos de polling sem apagar dados recentes necessários para suporte e observabilidade.

### Escopo executado
- management command `prune_shipment_history`
- parâmetros:
  - `--tenant-id`
  - `--days`
  - `--dry-run`
- trava de segurança:
  - `--days` precisa ser `>= 30`
- testes de:
  - dry-run sem remoção
  - isolamento por tenant
  - rejeição de janela agressiva

### Uso recomendado
- simulação:
  - `python manage.py prune_shipment_history --days=90 --dry-run`
- execução por tenant:
  - `python manage.py prune_shipment_history --tenant-id=<id> --days=90`
- execução global:
  - `python manage.py prune_shipment_history --days=90`

### Leitura operacional
- a política inicial sugerida é retenção de 90 dias.
- ambientes com maior volume podem rodar o comando por tenant.
- eventos recentes continuam disponíveis para métricas, dashboard e suporte.

### Limites explícitos
- ainda não há agendamento automático desse pruning.
- não há arquivamento frio antes da remoção.
- a retenção é por idade, não por volume máximo.

### Próxima macro-abordagem recomendada
- **Shipping Operational Runbook Consolidation**
- motivo:
  - shipping agora tem polling, provider, métricas, alertas e retenção; vale consolidar ativação/rotina operacional em um runbook único.

## Wave FD — Shipping Operational Runbook Consolidation
- foi criado runbook operacional dedicado para shipping.
- ele consolida provider, polling, observabilidade, alertas e retenção em um único documento acionável.

### Escopo executado
- `docs/modules/shipping-operational-runbook.md`
- referência aos artefatos de Prometheus, Grafana e Alertmanager
- comandos operacionais:
  - `sync_shipments_tracking`
  - `prune_shipment_history`
- checklist de diagnóstico rápido

### Leitura operacional
- a ativação de shipping em produção agora tem trilha explícita.
- o runbook evita depender da sequência histórica de waves para operar o módulo.
- troubleshooting inicial fica agrupado por sintomas:
  - backlog
  - ausência de sync
  - HTTP 5xx
  - latência alta

### Fechamento da abordagem shipping operacional
- shipping agora tem:
  - provider HTTP configurável por tenant
  - polling manual/Celery
  - métricas Prometheus
  - alertas Prometheus
  - dashboard Grafana
  - routing Alertmanager
  - pruning de histórico
  - runbook de ativação/operação

### Próxima macro-abordagem recomendada
- **Payments Operational Parity Review**
- motivo:
  - shipping chegou a um pacote operacional completo; o próximo domínio crítico é revisar se payments tem a mesma clareza de operação, retenção e runbook.

## Shipping Quote & Delivery Promise — Pre-Checkout Contract

### Decisão

Shipping passa a expor um contrato de promessa pré-checkout por `shipping.application.delivery_promise_queries`.

Esse contrato é apenas informativo e customer-facing.

### Escopo

Permitido:

- exibir opções de entrega padrão/expressa antes do checkout;
- usar preço como “a partir de”;
- explicar que valores e prazos finais dependem do endereço;
- consumir o contrato em `cart`.

Não permitido:

- calcular frete final no carrinho;
- persistir método de envio no carrinho;
- alterar total do carrinho;
- criar pedido ou reserva logística;
- substituir a escolha de frete do checkout.

### Boundary

- `shipping` define a promessa.
- `cart` apresenta a promessa.
- `checkout` escolhe e aplica o frete final.
- `orders` persiste o snapshot transacional do pedido.

## Battery D — Shipping Quote Productionization Closure

- o módulo `shipping` agora possui quote mínimo produtizável para checkout.
- application services:
  - `shipping.application.shipping_quote_queries`;
  - `checkout.application.checkout_shipping_quote_commands`;
  - `shipping.application.shipping_quote_productionization_queries`.
- comando:
  - `python manage.py shipping_quote_productionization --provider-contract-ready --adapter-skeleton-ready --checkout-integration-review-ready --checkout-execution-ready --failure-ux-ready --observability-ready --tenant-scope-confirmed --no-order-without-delivery-confirmed --no-provider-secret-recorded --rollback-plan-ready --docs-updated --decision-recorded`

### Ondas fechadas

1. Shipping Quote Provider Contract Review.
2. Shipping Quote Adapter Skeleton Execution.
3. Shipping Quote Checkout Integration Review.
4. Shipping Quote Checkout Execution.
5. Shipping Quote Failure UX Review.
6. Shipping Quote Observability Execution.
7. Shipping Quote Closure Review.

### Semântica

- `shipping_quote_queries` retorna métodos checkout-ready com carrier, service code, preço e prazo estimado.
- `checkout_shipping_quote_commands.refresh_quote(...)` aplica a cotação em `CheckoutSession.shipping_methods`.
- falha de CEP/tenant limpa seleção de frete e preserva mensagem honesta.
- checkout continua responsável por impedir pedido sem entrega válida.

### Limites explícitos

- adapter atual é skeleton/manual, sem chamada de transportadora real.
- nenhum token/provider secret é persistido em evidência.
- não há cotação por peso/dimensões reais nesta bateria.
- não há label de alta cardinalidade em observabilidade.

### Próxima bateria recomendada

**Battery E — Subscriptions & Tenant Billing Foundation**

Objetivo:

- iniciar fundação de billing SaaS do tenant sem misturar cobrança de loja, pedidos ou frete.
