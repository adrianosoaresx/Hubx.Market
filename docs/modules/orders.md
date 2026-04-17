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
