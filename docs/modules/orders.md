# Orders

## Responsabilidade
Gerenciar pedidos e histórico de status.

## Entidades principais
- Order
- OrderItem
- OrderStatusHistory

## Casos de uso
- listar pedidos
- detalhar pedido
- alterar status

## Regras de negócio
- pedido guarda snapshot dos valores

## Integração UI
- views HTTP devem permanecer finas em `interfaces/`
- templates oficiais do Design System podem ser usados como contrato de apresentação
- adapters de contexto podem preparar dados para list/detail sem mover regra de negócio para a view
- queries de leitura para Admin Orders devem viver fora das views; enquanto o módulo ainda não expõe modelos/serviços reais, a camada `application/` pode centralizar fallback temporário sem quebrar o contrato dos templates

## Readiness de persistência
- o módulo agora possui `Order` com snapshot operacional mínimo para leitura administrativa
- `OrderItem` guarda a linha básica do pedido com `price_snapshot`, quantidade e meta visível
- `Order` agora também pode manter vínculo explícito opcional com `Customer`, preservando os snapshots de customer para compatibilidade e auditoria
- essa estrutura é propositalmente mínima e existe para desbloquear futuras leituras persistidas honestas na query layer de admin

## O que a query layer poderá consumir depois
- número do pedido, status e atualização
- resumo do cliente via snapshot (`customer_name`, `customer_email`, `customer_phone`)
- estados operacionais de pagamento e envio
- totais (`subtotal`, `shipping_total`, `discount_total`, `total`, `installments_summary`)
- itens via `OrderItem`

## O que ainda falta
- seed mínima ou fonte persistida real de pedidos
- integração formal com payment/shipping reais
- trilha de histórico/status mais rica, se quisermos substituir blocos de atividade e notas por dados persistidos
- backfill opcional dos pedidos antigos para preencher `Order.customer` quando fizer sentido

## Seed / readiness atual
- as fixtures mínimas de pedidos já podem nascer com `Order.customer` preenchido quando o `Customer` correspondente estiver explícito e inequívoco

## Auto-população em writes futuros
- `Order` agora tenta preencher `customer` automaticamente no `save()`
- isso só acontece quando:
  - o pedido ainda não possui `customer`
  - existe `tenant`
  - `customer_email` encontra exatamente um `Customer` no mesmo tenant
- snapshots como `customer_name`, `customer_email` e `customer_phone` continuam preservados

## Visibilidade operacional
- a listagem e o detalhe de `Admin Orders` agora exibem indicação operacional do modo de resolução do cliente:
  - vínculo explícito via `Order.customer`
  - ou snapshot/fallback via `customer_email`
- isso ajuda a identificar rapidamente o estágio real da integração sem alterar fluxos de usuário final

## Escopo administrativo por tenant
- a query layer de `Admin Orders` agora também aceita `tenant_id` explícito para listagem, detalhe e visibilidade operacional
- quando a superfície administrativa já estiver dentro de um tenant resolvido, esse contexto passa a limitar as leituras internas do módulo
- quando não houver tenant resolvido, a leitura global atual continua existindo como compatibilidade operacional temporária
- quando houver tenant resolvido e nenhum pedido persistido correspondente, a surface administrativa passa a expor ausência real em vez de reutilizar fixtures de demonstração
- na listagem administrativa tenant-scoped, esse caso também aparece com empty state explícito de loja sem base persistida, em vez de parecer apenas uma visão vazia por filtro
- a command layer de `Admin Orders` agora segue o mesmo contrato quando houver tenant resolvido na request
- nesse caso, ações administrativas passam a resolver o pedido por `tenant_id + order_number`, reduzindo o risco de atuar sobre outro tenant em cenários com números repetidos

## Ações operacionais iniciais
- `Admin Orders` agora já aceita ações reais de baixa complexidade no detalhe do pedido:
  - atualização de `order.status`
  - atualização de `fulfillment_status_label` + `fulfillment_status_variant`
  - cancelamento simples do pedido
- a escrita fica em `application/admin_order_commands.py`
- a view permanece fina e apenas encaminha `POST` para o command service
- ainda não há integração com:
  - pagamentos externos
  - logística externa
  - estornos, refunds ou automações de expedição

## Cancelamento simples
- o cancelamento administrativo atual é propositalmente leve:
  - muda `order.status` para `canceled`
  - registra evento em `OrderStatusHistory`
  - mantém a atribuição como ação administrativa interna
- guardrails atuais:
  - não recancela pedido já cancelado
  - não cancela pedido já enviado por esse atalho simples

## Clareza operacional no detalhe
- o detalhe de `Admin Orders` agora comunica melhor quando uma ação foi ignorada
- exemplos:
  - tentativa de salvar o mesmo status do pedido
  - tentativa de salvar o mesmo status operacional
  - tentativa de cancelar pedido já cancelado
  - tentativa de cancelar pedido já enviado
- essas respostas continuam leves e usam o mesmo fluxo de feedback já existente na página

## Guidance de próximo passo
- o detalhe do pedido agora deriva uma orientação leve de próximo passo usando:
  - `order.status`
  - `fulfillment status`
  - `payment_status`
  - `shipping_status`
- essa guidance ajuda a operação a entender rapidamente se o foco atual é:
  - confirmar pagamento
  - separar e preparar envio
  - acompanhar transporte
  - encerrar acompanhamento
- a implementação continua na query layer e reaproveita campos já existentes da página

## Progressão após pagamento
- `Admin Orders` agora também pode iniciar o preparo/envio de um pedido já pago
- essa ação é intencionalmente pequena e explícita:
  - exige pedido em estado `paid`
  - exige `payment_status` já confirmado
  - não roda para pedido cancelado ou enviado
- quando a ação é aplicada:
  - `fulfillment_status_label` vira `Separando itens`
  - `fulfillment_status_variant` vira `info`
  - `shipping_status` vira `Preparando envio`
  - `OrderStatusHistory` registra `fulfillment_started`
- isso conecta o pagamento confirmado ao começo operacional real da expedição sem abrir integrações logísticas mais profundas

## Shipping progression readiness
- depois de `Separando itens`, `Admin Orders` agora também pode iniciar o envio/trânsito de forma explícita
- essa ação mantém o fluxo honesto:
  - não depende de transportadora externa
  - não cria rastreio fake
  - apenas move o pedido para o primeiro estado real de trânsito
- guardrails atuais:
  - exige pedido pago
  - exige pagamento confirmado
  - exige preparo já iniciado (`Separando itens` + `Preparando envio`)
- quando aplicada:
  - `Order.status` vira `shipped`
  - `fulfillment_status_label` vira `Em trânsito`
  - `fulfillment_status_variant` vira `shipped`
  - `shipping_status` vira `Em trânsito`
  - `OrderStatusHistory` registra `shipping_started`

## Delivery / completion readiness
- depois de `Em trânsito`, `Admin Orders` agora também pode confirmar a entrega e encerrar a operação
- esse encerramento continua leve e honesto:
  - não depende de transportadora externa
  - não cria evento logístico fake
  - apenas fecha o ciclo operacional quando a entrega já puder ser confirmada com segurança
- guardrails atuais:
  - exige pedido em `shipped`
  - exige `fulfillment_status_label = Em trânsito`
  - exige `shipping_status = Em trânsito`
- quando aplicada:
  - `fulfillment_status_label` vira `Concluído`
  - `fulfillment_status_variant` vira `success`
  - `shipping_status` vira `Entregue`
  - `OrderStatusHistory` registra `delivery_completed`

## Enriquecimento de timeline
- `OrderStatusHistory` agora registra mudanças operacionais leves feitas no admin
- por enquanto ele cobre:
  - alteração de `order.status`
  - alteração de `fulfillment status`
- a query layer do detalhe do pedido prioriza esses eventos recentes em `activity_items`
- quando não houver histórico persistido, a timeline continua segura com eventos derivados do snapshot atual

## Atribuição leve de origem/contexto
- `OrderStatusHistory` agora pode guardar:
  - `source_type`
  - `source_label`
  - `actor_label`
- isso permite indicar, de forma leve, se um evento veio de ação administrativa ou de outro fluxo interno
- mudanças feitas por `Admin Orders` já persistem essa atribuição
- linhas antigas sem esses campos continuam válidas e a timeline segue segura

## Inventory / post-payment reservation readiness
- `Order` agora também pode guardar `inventory_reserved_at` para indicar quando a baixa operacional de estoque já foi aplicada após o pagamento
- `OrderItem` preserva `variant_sku` como snapshot explícito da variante comprada
- quando a confirmação interna de pagamento encontra uma `ProductVariant` inequívoca no mesmo tenant:
  - `stock` é reduzido
  - `reserved_stock` é incrementado
  - `OrderStatusHistory` registra `inventory_reserved_after_payment`
- quando o vínculo com a variante não existir ou não puder ser resolvido com segurança, o pagamento continua evoluindo sem forçar baixa insegura

## Inventory visibility / stock impact clarity
- `Admin Orders` agora também comunica de forma mais explícita quando um pedido já aplicou impacto operacional no estoque
- essa visibilidade usa:
  - `inventory_reserved_at`
  - `OrderItem.variant_sku`
  - quantidade total ligada às variantes do pedido
- a intenção é ajudar a operação a entender rapidamente se:
  - a baixa já foi aplicada
  - o pedido ainda está apenas pronto para impacto futuro

## Inventory recovery / restock readiness
- `Order` agora também pode guardar `inventory_recovered_at` para registrar quando a devolução operacional de estoque já aconteceu
- o cancelamento administrativo passa a tentar devolver estoque apenas quando:
  - a reserva pós-pagamento já existiu (`inventory_reserved_at`)
  - ainda não houve devolução anterior (`inventory_recovered_at`)
  - o pedido ainda não foi enviado
- quando a devolução acontece:
  - `stock` volta a subir
  - `reserved_stock` diminui
  - `OrderStatusHistory` registra `inventory_recovered_after_cancel`
- esse fluxo continua propositalmente conservador:
  - sem restock automático para entrega/devolução
  - sem reversões logísticas mais profundas

## Inventory finalization guardrails
- `Order` agora também pode guardar `inventory_finalized_at` para indicar quando a reserva operacional já foi consumida de forma final após a entrega
- na confirmação de entrega, o fluxo administrativo tenta:
  - encerrar a reserva operacional ligada às variantes do pedido
  - reduzir `reserved_stock` sem mexer novamente em `stock`
  - registrar `inventory_finalized_after_delivery` em `OrderStatusHistory`
- isso ajuda a distinguir melhor três estados operacionais:
  - reserva ativa após pagamento
  - devolução após cancelamento
  - consumo final após entrega
- guardrails adicionais evitam reversões genéricas inseguras:
  - pedidos com estoque finalizado não devem mudar de status por atalho genérico
  - pedidos cancelados não devem ser reabertos por `update_order_status`
  - pedidos enviados continuam exigindo fluxo específico para qualquer reversão

## Inventory consistency before reservation
- a confirmação interna de pagamento agora também valida se a variante ainda está coerente com o estoque vivo antes de aplicar a reserva operacional
- os bloqueios atuais cobrem:
  - item sem vínculo seguro com variante
  - variante inexistente ou indisponível no mesmo tenant
  - saldo livre insuficiente para reservar a quantidade do pedido
- isso protege o intervalo entre:
  - pedido pendente já criado
  - confirmação de pagamento
  - baixa/reserva operacional efetiva

## External payment flow readiness
- `Order` agora também pode guardar `payment_confirmed_at`
- `Order` agora também pode guardar `payment_failed_at`
- isso ajuda a separar com mais clareza:
  - pedido criado no checkout
  - pagamento ainda pendente
  - pagamento confirmado por fluxo interno
  - pagamento confirmado por evento externo
  - pagamento falho por evento externo
- o módulo `orders` agora expõe um command path leve para confirmação externa por contrato claro:
  - resolve o pedido por `tenant_id + order_number`
  - atualiza:
    - `status`
    - `payment_status`
    - `payment_source_type`
    - `payment_source_label`
    - `payment_reference`
    - `payment_confirmed_at`
  - reaproveita os mesmos guardrails de estoque e reserva pós-pagamento
- os commands de confirmação agora também exigem `tenant_id` explícito:
  - não confirmam pagamento por lookup global de `order_number`
  - sem tenant resolvido, falham fechado como indisponíveis
- isso prepara o caminho para um futuro `payment.paid` sem acoplar `orders` diretamente ao gateway
- com a readiness atual de `payments`, esse fluxo agora também pode ser reconciliado com uma `PaymentAttempt` persistida sem mover a posse do lifecycle para fora de `orders`

## Negative payment event readiness
- o módulo `orders` agora também expõe um command path leve para falha externa de pagamento
- esse fluxo é propositalmente conservador:
  - não cancela o pedido
  - não toca estoque
  - não abre refund/chargeback
- quando recebe uma falha externa elegível:
  - mantém o pedido em `pending`
  - atualiza `payment_status` para `Pagamento falhou`
  - grava `payment_source_type = external_payment_failed`
  - grava `payment_source_label`
  - grava `payment_reference`
  - grava `payment_failed_at`
  - registra `payment_failed_external` em `OrderStatusHistory`
- esse path de falha também exige `tenant_id` explícito:
  - não marca falha por lookup global de `order_number`
  - sem tenant resolvido, responde como indisponível
- a intenção é deixar o pedido pronto para nova tentativa futura sem abrir um workflow complexo cedo demais

## Inventory exception visibility
- `Admin Orders` agora também expõe sinais leves de exceção de estoque quando o pedido ainda não conseguiu chegar à reserva operacional
- esses sinais cobrem, por exemplo:
  - variante ausente no tenant atual
  - produto/variante indisponível
  - saldo livre insuficiente para reservar o pedido
- a visibilidade aparece:
  - na nota operacional da listagem
  - no meta/notas do detalhe
  - em `activity_items` com destaque para exceção operacional
- a intenção é facilitar acompanhamento e triagem sem criar dashboard novo

## Inventory exception recovery guidance
- além da visibilidade da exceção, `Admin Orders` agora também deriva orientação simples de próximo passo operacional
- essa guidance ajuda a diferenciar casos como:
  - revisar vínculo da variante
  - revisar disponibilidade do produto
  - tratar conflito de saldo livre
- a orientação aparece reaproveitando o próprio detalhe do pedido:
  - `summary_subtitle`
  - `summary_note`
  - `page_meta`
  - `activity_items`
- a intenção continua leve: apoiar triagem humana, sem criar workflow novo

## Inventory exception resolution markers
- `Order` agora também pode guardar:
  - `inventory_exception_under_review_at`
  - `inventory_exception_resolved_at`
- esses markers registram uma trilha operacional mínima para exceções de estoque já visíveis no admin
- o fluxo atual continua simples:
  - marcar `em revisão` quando a exceção ainda está ativa
  - marcar `resolvida` apenas depois que o sinal ativo já saiu do pedido
- a intenção é apoiar acompanhamento humano sem abrir workflow, fila ou dashboard novos

## Inventory exception list visibility
- a lista de `Admin Orders` agora também reflete esses markers de forma compacta e escaneável
- a tabela passa a destacar, sem mudar contrato de layout:
  - `Exceção ativa`
  - `Em revisão`
  - `Resolvida`
- a intenção é permitir triagem rápida direto na fila operacional, sem depender do detalhe do pedido para cada conferência

## Inventory exception quick filters
- a lista de `Admin Orders` agora também aceita filtro rápido por querystring:
  - `?quick_filter=active`
  - `?quick_filter=review`
  - `?quick_filter=resolved`
- a filtragem acontece na query layer antes da paginação
- filtros desconhecidos continuam seguros e são ignorados

## Inventory exception filter clarity polish
- quando um quick filter de exceção está ativo, a página agora explicita:
  - qual filtro rápido está em uso
  - quantos pedidos estão naquela visão
  - como voltar para a lista completa com `Limpar`
- isso reaproveita `page_meta`, `filter_description` e `page_note`, sem redesign

## Inventory exception empty-state messaging
- os quick filters de exceção agora também ajustam o empty state da lista quando não há resultados
- a página comunica melhor cenários como:
  - nenhuma exceção ativa
  - nenhuma exceção em revisão
  - nenhuma exceção resolvida no recorte atual
- quando houver busca junto do filtro, o empty state também incorpora o termo pesquisado

## Inventory exception quick actions lite
- a lista de `Admin Orders` agora também oferece ações rápidas por linha para exceções:
  - marcar em revisão
  - marcar resolvida
- essas ações reutilizam o mesmo endpoint já existente do detalhe
- o retorno preserva a visão atual da lista com `result=...`, evitando tirar a operação da fila atual

## Inventory exception bulk actions lite
- a lista de `Admin Orders` agora também pode aplicar ações em lote na visão filtrada atual
- por enquanto o escopo continua leve:
  - marcar em revisão na visão
  - marcar resolvida na visão
- o lote opera sobre o conjunto filtrado atual antes da paginação e ignora silenciosamente itens não elegíveis

## Inventory exception ownership lite
- `Order` agora também pode guardar `inventory_exception_owner_label`
- esse owner leve é preenchido a partir do contexto da ação administrativa que marcou a exceção:
  - em revisão
  - resolvida
- a intenção é registrar responsabilidade operacional mínima sem abrir workflow, fila ou permissões complexas

## Inventory exception priority lite
- `Admin Orders` agora também deriva uma prioridade leve para exceções de estoque sem criar scoring engine
- a prioridade usa apenas sinais já existentes da própria trilha:
  - conflito de saldo livre ou indisponibilidade → `Alta prioridade`
  - vínculo ausente ou exceção em revisão → `Média prioridade`
  - exceção já normalizada → `Baixa prioridade`
- essa leitura aparece na lista e no detalhe para ajudar a operação a decidir o que tratar primeiro
- a implementação continua intencionalmente simples, humana e explicável, sem SLA engine nem workflow novo

## Inventory exception priority quick filters
- a lista de `Admin Orders` agora também aceita recortes rápidos por prioridade:
  - `?quick_filter=high_priority`
  - `?quick_filter=medium_priority`
  - `?quick_filter=low_priority`
- esses filtros reaproveitam o mesmo seletor e o mesmo fluxo já usado para:
  - `active`
  - `review`
  - `resolved`
- a filtragem continua:
  - determinística
  - aplicada antes da paginação
  - segura para valores desconhecidos

## Inventory exception backlog summary lite
- a própria lista de `Admin Orders` agora resume o backlog atual de exceções sem criar dashboard novo
- o summary usa apenas sinais já existentes:
  - estado da exceção (`ativa`, `em revisão`, `resolvida`)
  - prioridade (`alta`, `média`, `baixa`)
  - ownership já registrada
- a intenção é dar leitura rápida de volume e urgência dentro da própria página operacional

## Inventory exception aging lite
- `Admin Orders` agora também deriva um hint leve de aging/staleness para exceções de estoque
- a leitura usa timestamps já persistidos no próprio pedido:
  - `updated_at` para exceção ativa
  - `inventory_exception_under_review_at` para casos em revisão
  - `inventory_exception_resolved_at` para casos resolvidos
- exemplos de saída:
  - `Exceção envelhecida`
  - `Revisão parada`
  - `Resolvida recentemente`
- esse aging aparece:
  - na lista
  - no detalhe
  - e também no resumo leve do backlog

## Inventory exception smart ordering
- a lista de `Admin Orders` agora também ordena automaticamente a fila para trazer primeiro os casos com maior urgência operacional
- a regra continua simples, determinística e implementada na query layer
- a ordem combina:
  - estado operacional da exceção (`ativa` antes de `em revisão`, que vem antes de `resolvida`)
  - prioridade (`alta`, `média`, `baixa`)
  - aging/staleness (`envelhecida` e `revisão parada` antes dos casos recentes)
  - ausência de owner em casos ainda abertos
- sem score, sem ML e sem workflow novo: a intenção é só deixar a fila naturalmente mais útil para triagem diária

## Inventory exception owner workload visibility
- a própria fila de `Admin Orders` agora também comunica melhor a carga atual por responsável sem criar workflow pesado
- o resumo leve do backlog passa a mostrar:
  - responsáveis já visíveis nos casos abertos
  - quantos casos cada responsável conduz na fila atual
  - quantos pedidos ainda seguem sem responsável
- cada linha também pode reforçar essa leitura com um hint curto de workload, por exemplo:
  - `Operação interna conduz 2 caso(s) aberto(s) nesta fila`
- a lógica continua toda derivada da própria lista atual, sem assignee engine, sem SLA e sem dashboard novo

## Inventory exception owner quick filters
- a lista de `Admin Orders` agora também aceita quick filters simples por ownership operacional:
  - `?quick_filter=unassigned`
  - `?quick_filter=assigned`
- esses recortes focam apenas exceções ainda abertas (`ativa` ou `em revisão`)
- a intenção é ajudar a operação a responder rapidamente:
  - o que ainda está sem responsável
  - o que já está assumido por alguém
- o comportamento continua:
  - determinístico
  - aplicado antes da paginação
  - seguro para valores desconhecidos

## Inventory exception owner backlog summary
- o resumo leve do backlog agora também traz uma leitura mais executiva da distribuição por responsável
- além do volume aberto, a fila passa a resumir:
  - principais owners por quantidade de casos abertos
  - owners que concentram casos envelhecidos ou revisão parada
- exemplos de leitura:
  - `Carga atual por responsável: Operação interna (2), Logística (1).`
  - `Casos envelhecidos por responsável: Logística (1 envelhecido(s)), Operação interna (1 envelhecido(s)).`
- isso continua no mesmo `page_note`, sem dashboard novo, sem analytics engine e sem workflow pesado

## Inventory exception owner review + priority ordering
- a fila agora também prioriza melhor os casos **dentro de cada owner** sem abrir score ou workflow novo
- para exceções abertas com responsável já visível, a ordenação passa a:
  - agrupar casos por owner de forma determinística
  - e, dentro de cada owner, priorizar:
    - maior prioridade
    - maior aging/staleness
- a ordem geral continua respeitando primeiro:
  - estado operacional
  - casos sem responsável antes dos já assumidos
- depois disso, os casos assumidos ficam mais fáceis de tratar em sequência por responsável

## Inventory exception reassignment lite
- `Admin Orders` agora também permite reatribuir de forma leve o responsável atual da exceção para o ator da ação
- a operação reaproveita:
  - o mesmo endpoint de ações
  - a mesma trilha de history
  - a mesma visibilidade já existente na fila e no detalhe
- o reassignment continua intencionalmente simples:
- sem workflow de aprovação
- sem permissões complexas
- sem fila nova
- a ideia é só permitir handoff operacional explícito quando outro responsável assume o caso

## Reorder lite continuity
- `OrderItem` agora também serve como ponto de reentrada leve para uma nova compra na área do cliente
- o fluxo de reorder usa o snapshot anterior apenas para localizar:
  - `variant_sku`
  - título/subtítulo visíveis
  - quantidade
- a nova sessão não reaproveita o `price_snapshot` como verdade comercial:
  - o checkout volta com o preço atual da variante elegível
  - itens sem variante elegível ficam de fora com feedback explícito

## Real payment readiness signals
- `Order` agora também guarda sinais mínimos para distinguir melhor o estado de pagamento atual:
  - `payment_source_type`
  - `payment_source_label`
  - `payment_reference`
- isso não integra gateway ainda, mas prepara o contrato para separar com clareza:
  - pedido criado no checkout e ainda pendente
  - confirmação interna usada nas waves atuais
  - futura confirmação externa por provider/gateway

## Wave FK — Inventory/Stock Operational Readiness Review
- a revisão confirmou que estoque ainda vive corretamente em `catalog.ProductVariant`.
- a operação de exceções de estoque, porém, já acontece dentro da fila de `orders`.

### Módulos responsáveis
- `catalog`
  - dono de `ProductVariant.stock`
  - dono de `ProductVariant.reserved_stock`
  - dono dos flags `track_inventory` e `allow_backorder`
- `orders`
  - dono da visibilidade operacional das exceções ligadas ao pedido
  - dono dos marcadores de revisão, resolução e responsável

### Decisão prática
- não criar módulo `inventory` separado nesta fase.
- reforçar a operação no boundary atual:
  - CLI tenant-scoped
  - métricas Prometheus
  - runbook operacional

## Wave FL — Inventory Exception CLI Execution
- foi criado comando operacional para listar exceções de estoque por tenant.

### Escopo executado
- `list_inventory_exceptions`
- filtros:
  - `--tenant-id`
  - `--quick-filter`
  - `--limit`
- quick filters suportados:
  - `active`
  - `review`
  - `resolved`
  - `high_priority`
  - `medium_priority`
  - `low_priority`
  - `unassigned`
  - `assigned`
- testes de exceção ativa e exceção atribuída

## Wave FM — Inventory Exception Metrics Execution
- foi criado exporter protegido para métricas de exceções de estoque.

### Escopo executado
- endpoint:
  - `/ops/orders/metrics/inventory-exceptions/`
- tokens aceitos:
  - `INVENTORY_OBSERVABILITY_TOKEN`
  - fallback `ORDERS_OBSERVABILITY_TOKEN`
- métricas:
  - `hubx_inventory_exception_total{tenant_id,state}`
  - `hubx_inventory_exception_priority_total{tenant_id,priority}`
  - `hubx_inventory_exception_owner_total{tenant_id,owner_state}`
  - `hubx_inventory_exception_aging_total{tenant_id,aging}`
- testes de:
  - export Prometheus
  - token válido
  - token inválido
  - endpoint oculto sem token configurado

## Wave FN — Inventory Observability Pack Execution
- foram criados artefatos de observability para exceções de estoque.

### Escopo executado
- `infra/observability/prometheus/inventory-scrape.example.yml`
- `infra/observability/prometheus/inventory-alert-rules.yml`
- `infra/observability/grafana/inventory-exceptions-dashboard.json`
- `infra/observability/alertmanager/inventory-routing.example.yml`
- `docs/modules/inventory-operational-runbook.md`
- atualização do índice operacional

### Alertas iniciais
- `HubxInventoryActiveExceptionsPresent`
- `HubxInventoryHighPriorityExceptionsPresent`
- `HubxInventoryUnassignedExceptionsPresent`

### Próxima macro-abordagem recomendada
- **Inventory Operational Wrap-Up Review**
- motivo:
  - triagem, métricas, alertas, dashboard e runbook já cobrem o pacote operacional mínimo desta fase.

## Wave FO — Inventory Operational Wrap-Up Review
- o pacote operacional de estoque/inventory pode ser considerado completo para esta fase.
- a abordagem reforçou operação e observability sem mover a fronteira de domínio.

### O que ficou pronto
- CLI tenant-scoped:
  - `list_inventory_exceptions`
- endpoint Prometheus:
  - `/ops/orders/metrics/inventory-exceptions/`
- métricas:
  - `hubx_inventory_exception_total`
  - `hubx_inventory_exception_priority_total`
  - `hubx_inventory_exception_owner_total`
  - `hubx_inventory_exception_aging_total`
- observability:
  - scrape example
  - alert rules
  - dashboard Grafana
  - routing Alertmanager
- runbook:
  - `docs/modules/inventory-operational-runbook.md`

### O que fica fora de escopo
- módulo `inventory` dedicado
- ledger de movimentos de estoque
- reconciliação contábil de estoque
- SLA engine para aging
- workflow complexo de assignee

### Próxima macro-abordagem recomendada
- **Catalog Operational Readiness Review**
- motivo:
  - estoque em variante está mais observável; o próximo domínio natural é revisar operação de catálogo/produtos, especialmente produtos inativos, variantes e qualidade de publicação.

## Cart Foundation Wave 20 — Coupon Order Snapshot Review
- `Order` já guarda `discount_total`.
- a próxima execução deve adicionar snapshot promocional auditável:
  - `coupon_code`
  - `promotion_snapshot`
- o snapshot deve ser copiado de `CheckoutSession` durante `checkout_completion_commands`.
- `orders` não deve recalcular promoção nem consultar `coupons`.
- mudanças futuras no cupom não devem alterar pedidos já criados.

## Cart Foundation Wave 21 — Coupon Order Snapshot Execution
- `Order` passa a armazenar:
  - `coupon_code`
  - `promotion_snapshot`
- `checkout_completion_commands` copia o snapshot promocional da sessão.
- pedidos sem cupom aplicado mantêm snapshot vazio.
- `orders` segue sem recalcular cupom.

## Cart Foundation Wave 22 — Coupon Admin Visibility Review
- admin orders deve exibir cupom aplicado como snapshot de pedido.
- origem: `Order.coupon_code`, `Order.discount_total`, `Order.promotion_snapshot`.
- exibir apenas quando houver cupom e desconto real.
- `orders` não deve consultar `coupons` para explicar pedidos já criados.
- notificações ficam fora desta wave.

## Cart Foundation Wave 23 — Coupon Admin Visibility Execution
- Admin Orders agora expõe o cupom aplicado no detalhe do pedido como snapshot operacional.
- origem dos dados: `Order.coupon_code`, `Order.discount_total`, `Order.promotion_snapshot`.
- visibilidade: somente quando existe cupom, desconto real e snapshot promocional não vazio.
- copy operacional: “Cupom aplicado: CODE” e “-R$ X,XX · origem: cart · validação: coupon-valid”.
- fronteira preservada: `orders` não chama `coupons` e não recalcula desconto.
- essa superfície ajuda atendimento/auditoria a entender por que o total final do pedido contém desconto, mantendo o pedido como fonte histórica.
