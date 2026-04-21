# Customers

## Responsabilidade
Gerenciar compradores, perfis, contato, endereços e visão operacional da conta.

## Entidades principais
- Customer
- CustomerAddress
- CustomerPreference

## Casos de uso
- listar clientes
- detalhar cliente
- manter dados de perfil e contato
- manter endereços usados na experiência logada do cliente

## Regras de negócio
- customer pertence a um tenant específico
- customer não deve ser misturado com accounts

## Integração UI
- views HTTP devem permanecer finas em `interfaces/`
- templates oficiais do Design System podem ser usados como contrato de apresentação
- adapters de contexto podem preparar dados para list/detail sem mover regra de negócio para a view
- queries de leitura para Admin Customers devem viver fora das views; enquanto o módulo ainda não expõe modelos/serviços reais, a camada `application/` pode centralizar fallback temporário sem quebrar o contrato dos templates

## Persistência mínima disponível
- `Customer` existe como base persistida mínima para leituras reais do Admin Customers
- `CustomerAddress` agora existe como base persistida mínima para futuras leituras reais da área logada do cliente
- `Customer` também passa a ser o elo explícito preferencial para:
  - `AccountProfile.customer`
  - `Order.customer`
- a estrutura cobre o mínimo necessário para:
  - listagem administrativa
  - detalhe administrativo básico
  - endereços da experiência logada
  - identificação e isolamento por tenant

## O que a query layer poderá consumir depois
- de `Customer`:
  - `slug`
  - `reference`
  - `full_name`
  - `email`
  - `phone`
  - `status`
  - `account_type`
  - `last_seen_at`
  - `created_at`
  - `updated_at`
- de `CustomerAddress`:
  - `label`
  - `recipient_name`
  - `line_1`
  - `line_2`
  - `district`
  - `city`
  - `state`
  - `postal_code`
  - `is_default`
- de fontes já existentes reaproveitáveis:
  - `orders.Order` e `orders.OrderItem` para list/detail de pedidos do cliente
  - `accounts.AccountProfile` para identidade e preferências

## O que ainda permanece faltando
- backfill progressivo dos vínculos explícitos em registros legados
- agregados reais de pedidos por cliente autenticado
- histórico operacional mais rico
- preferências além do escopo atual de `AccountProfile`

## Estado atual da leitura administrativa
- `Admin Customers` já pode ler `Customer` persistido quando registros existem
- a integração real cobre:
  - identidade básica
  - contato
  - status
  - tipo de conta
  - timestamps administrativos
  - agregados simples de valor do cliente com base em `Order`:
    - total de pedidos
    - total gasto
    - ticket médio
    - data do último pedido
- ainda permanece em fallback controlado:
  - resumo real de pedidos
  - histórico operacional mais rico

## Enriquecimento operacional atual
- `orders_summary_content` agora usa agregados reais de pedidos quando houver histórico persistido
- `summary_content` também passa a refletir valor do cliente quando existirem pedidos
- a leitura também já deriva mix simples de status:
  - pedidos pagos
  - pedidos enviados
  - pedidos cancelados
  - status e total do último pedido
- e agora também deriva indicadores simples de recência/retenção:
  - dias desde o último pedido
  - bucket de recência
  - cliente recorrente
  - cliente em risco
- a leitura prefere:
  - `Order.customer`
  - fallback por `tenant + customer_email` quando o vínculo explícito ainda não existir

## Business intelligence lite
- `Admin Customers` agora também deriva sinais simples e explicáveis para leitura operacional:
  - tier de valor
  - engajamento atual
  - highlights de lista como `alto valor`, `recorrente` e `em risco`
- esses sinais continuam baseados apenas em agregados já existentes de `Order`
- o objetivo é melhorar priorização operacional sem criar um motor analítico separado

## Guidance operacional leve
- a query layer agora também deriva um próximo passo simples por cliente:
  - `Revisar e reengajar`
  - `Priorizar e monitorar`
  - `Acompanhar próxima recompra`
  - `Observar próxima interação`
  - `Estimular primeiro retorno`
- essa guidance continua totalmente determinística e usa apenas:
  - tier de valor
  - engajamento
  - recência
  - repetição
  - risco

## Revenue awareness
- `Admin Customers` agora deixa a contribuição de receita mais visível com sinais simples:
  - receita acumulada
  - leitura textual de contribuição (`receita relevante`, `em desenvolvimento`, `inicial`)
  - reforço do ticket médio no contexto de valor
- esses sinais continuam apenas na query layer e usam exclusivamente agregados já persistidos de `Order`

## Lifecycle simples
- a query layer agora organiza os sinais existentes em um lifecycle determinístico:
  - `Novo`
  - `Ativo`
  - `Recorrente`
  - `Em risco`
  - `Perdido`
- a derivação usa apenas:
  - total de pedidos
  - dias desde o último pedido
  - repetição
  - risco
- isso ajuda a consolidar leitura operacional sem criar um engine separado

## Growth signals leves
- `Admin Customers` agora também deriva uma direção simples de crescimento:
  - `Incentivar primeira recompra`
  - `Manter engajamento`
  - `Expandir frequência de compra`
  - `Recuperar cliente`
  - `Recuperação seletiva`
- essa leitura continua determinística e usa somente:
  - lifecycle
  - tier de valor
  - engajamento
  - repetição
  - risco

## Prioritização simples
- a query layer agora também deriva `priority_label`:
  - `Alta prioridade`
  - `Média prioridade`
  - `Baixa prioridade`
- a priorização usa apenas sinais já existentes:
  - tier de valor
  - lifecycle
  - risco
  - direção de crescimento

## Execução mínima
- `Admin Customers` agora permite ações operacionais simples no detalhe do cliente:
  - marcar `follow-up`
  - marcar `reengajamento`
  - marcar `prioridade manual`
- essas ações usam apenas flags leves no próprio `Customer`
- o objetivo é permitir execução mínima dentro do sistema sem abrir um CRM completo
- a list view passa a priorizar highlights compactos e escaneáveis com:
  - prioridade
  - estágio de lifecycle / base ativa
  - direção de crescimento
  - flags manuais de execução quando existirem
- a ordenação da lista também segue leitura operacional determinística:
  - `Alta prioridade` primeiro, depois `Média`, depois `Baixa`
  - dentro de cada grupo: risco, dias desde o último pedido e receita acumulada
  - flags manuais de execução ajudam a puxar casos já sinalizados para o topo do grupo
- a listagem também aceita filtros rápidos por querystring:
  - `high_priority`
  - `at_risk`
  - `followup`
  - `repeat`
  - `new`
- filtros rápidos são aplicados antes da ordenação e filtros desconhecidos são ignorados com fallback seguro
- quando um filtro rápido está ativo, a list view explicita:
  - nome do filtro ativo
  - quantidade de clientes naquela visão
  - orientação para limpar o filtro e voltar à lista completa
- quando a visão filtrada retorna `0` resultados, a list view também usa mensagens específicas por segmento:
  - alta prioridade
  - em risco
  - follow-up
  - recorrentes
  - novos
- buscas sem resultado adicionam contexto curto com o termo pesquisado, mantendo a orientação de limpar o filtro
- a listagem também oferece ações rápidas mínimas por linha para:
  - marcar `follow-up`
  - marcar `prioridade manual`
- essas ações reutilizam o mesmo endpoint de detalhe e preservam o retorno para a visão atual da lista via querystring
- follow-up e prioridade manual também são reversíveis:
  - `clear_followup`
  - `clear_priority`
- detail e list continuam compartilhando o mesmo endpoint de atualização, com feedback seguro para marcar, remover ou ignorar estados já aplicados
- a list view agora suporta `bulk actions lite` sobre a visão segmentada atual:
  - marcar `follow-up` na visão
  - marcar `prioridade manual` na visão
- a wave seguinte fecha a reversibilidade em lote para a mesma visão:
  - remover `follow-up` na visão
  - remover `prioridade manual` na visão
- a simetria operacional também passa a cobrir `reengajamento`:
  - marcar / remover no detail
  - marcar / remover na list
  - marcar / remover em lote na visão segmentada
- essas ações em lote:
  - só aparecem quando existe busca ou filtro ativo
  - operam sobre o conjunto filtrado atual antes da paginação
  - retornam para a mesma visão com feedback simples

## Estado atual da readiness para customer area
- a próxima wave de persisted read da área logada já pode reaproveitar:
  - `AccountProfile` para perfil
  - `Order`/`OrderItem` para pedidos
  - `CustomerAddress` para endereços
- o próximo passo deixa de ser modelagem e passa a ser integração de leitura tenant-aware

## Readiness de vínculo explícito
- seeds e utilitários de backfill agora podem preencher com segurança:
  - `AccountProfile.customer`
  - `Order.customer`
- o vínculo só é aplicado quando o match por `tenant + email` é inequívoco
