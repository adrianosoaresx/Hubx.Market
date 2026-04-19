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
