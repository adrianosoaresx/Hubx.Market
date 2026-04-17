# Design System Governance

## Objetivo

Este documento define como o Design System do `Hubx.market` deve evoluir sem fragmentar a UI entre `admin`, `storefront`, `checkout` e `account`.

O foco aqui é governança leve:

- reduzir duplicação de HTML
- preservar consistência visual
- evitar explosão de componentes parecidos
- manter previsibilidade para implementação em Django templates
- facilitar manutenção por times diferentes

## Papel do Design System no Hubx.market

O Design System é a base compartilhada da interface do produto.

Ele conecta:

- tokens e temas
- componentes base
- composite components
- patterns
- layouts
- page templates

O Design System **não substitui** a composição de tela por módulo. Ele define os blocos oficiais que os módulos devem reutilizar sempre que possível.

## Camadas do sistema

### Tokens

Tokens são a camada de valores e intenção visual.

Exemplos:

- cor
- spacing
- radius
- sombra
- aliases semânticos

No Hubx, tokens devem alimentar:

- `ui/tokens/*.json`
- `ui/themes/*.css`
- `ui/static/css/design-system.css`
- `ui/static/css/themes.css`

Tokens não carregam estrutura de markup.

### Components

Components são blocos base, pequenos e reutilizáveis.

Exemplos:

- `button`
- `input`
- `select`
- `badge`
- `modal`

Um component deve:

- ter responsabilidade visual clara
- aceitar props previsíveis
- servir vários contextos
- evitar acoplamento com domínio específico

### Composite Components

Composite components combinam vários components oficiais para resolver um bloco recorrente de produto.

Exemplos:

- `product_card`
- `order_summary`
- `data_table_toolbar`
- `filter_bar`

Um composite deve existir quando já há recorrência real de estrutura e comportamento leve.

### Patterns

Patterns combinam components e composites em fluxos repetíveis, muitas vezes com integração HTMX.

Exemplos:

- `filter_table`
- `crud_modal`

Patterns podem carregar composição estrutural maior do que um composite, mas ainda não devem virar template de página.

### Page Templates

Page templates são esqueletos de composição completa.

Exemplos:

- `catalog_page`
- `product_detail_page`
- `checkout_page`
- `admin_dashboard_page`

Uma page template organiza regiões da página, mas não deve carregar lógica de negócio específica de um módulo.

## Regra principal de decisão

Antes de criar qualquer coisa nova, validar nesta ordem:

1. Existe token oficial para isso?
2. Existe component oficial que resolve isso?
3. Existe composite oficial próximo o suficiente?
4. Isso é só uma composição de página e não precisa virar component?

Se a resposta for “sim” em qualquer etapa anterior, **reutilizar** antes de criar algo novo.

## Quando criar um novo component

Criar um novo component somente quando:

- a necessidade aparece em mais de um fluxo
- o bloco tem responsabilidade visual clara
- a API pode ser curta e previsível
- a solução não cabe de forma limpa em um component existente
- o bloco não depende demais de contexto de negócio específico

Perguntas de validação:

- ele é reutilizável fora da tela atual?
- ele pode ser documentado com `variants`, `states`, `props` e `example usage`?
- ele reduz duplicação real?

Se a resposta for “não” para a maioria dessas perguntas, provavelmente não deve virar component.

## Quando reutilizar um component existente

Reutilizar quando:

- a diferença é só conteúdo
- a diferença é só variante visual
- a diferença é só tamanho, estado ou prop opcional
- o markup novo seria quase igual ao já existente

Regra prática:

- se a mudança cabe em `variant`, `size`, `state`, `props` ou `slots`, preferir evolução do component existente
- não criar `button_2`, `card_alt`, `custom_table`, `modal_v2`

## Quando algo deve ser composite e não base component

Um bloco deve virar composite quando:

- combina dois ou mais components oficiais
- já aparece em mais de um contexto
- tem estrutura recorrente de produto
- ainda faz sentido como bloco reutilizável isolado

Sinais de composite:

- card de produto
- resumo de pedido
- toolbar de listagem
- barra de filtros

Sinais de que **não** é component base:

- depende de várias regiões internas
- agrupa preço + badge + CTA + metadata
- resolve um caso de uso mais específico

## Quando algo deve permanecer só como composição de página

Não criar component ou composite quando:

- o bloco só existe em uma página
- a estrutura depende fortemente daquele layout
- a abstração deixaria a API confusa
- a recorrência ainda não foi comprovada

Nesses casos, manter a solução:

- no page template
- ou dentro do módulo consumidor

com reuso dos components oficiais já existentes.

## Regras para evolução do sistema

### 1. Preferir extensão pequena antes de criação nova

Antes de criar novo component:

- revisar `variant`
- revisar `size`
- revisar `state`
- revisar props opcionais

Se uma extensão pequena resolver, ela é preferível.

### 2. Evitar caminhos paralelos

Não introduzir markup novo em caminhos legados se já existe caminho oficial em:

- `ui/templates/shared/components/...`

Se houver legado em uso:

- criar wrapper compatível
- apontar para o caminho oficial

### 3. UI deve continuar multi-tenant-safe

Toda evolução visual deve respeitar:

- `data-tenant`
- `data-ui-context`
- tokens e themes existentes

Não hardcodar branding em componentes compartilhados.

### 4. States importam

Ao evoluir componentes, revisar se o componente precisa suportar:

- `loading`
- `empty`
- `error`
- `disabled`
- `selected`

Especialmente em:

- forms
- listagens
- overlays
- ecommerce

### 5. HTMX deve ficar onde faz sentido

HTMX é aceito para:

- filtros
- paginação
- modais
- atualizações parciais

Mas a lógica estrutural deve continuar previsível e não espalhada por componentes base sem necessidade.

## Fluxo recomendado para mudanças de UI

1. localizar component/composite existente
2. confirmar documentação em `ui/docs/component-api.md`
3. evoluir o component oficial, se necessário
4. atualizar showcase interno quando a mudança for relevante
5. atualizar documentação mínima quando a API mudar

## Fonte de verdade

Hoje a fonte de verdade da UI compartilhada é composta por:

- `ui/tokens/`
- `ui/themes/`
- `ui/static/css/`
- `ui/templates/shared/components/`
- `ui/templates/shared/patterns/`
- `ui/templates/layouts/`
- `ui/templates/pages/templates/`
- `ui/docs/component-api.md`
- `ui/templates/pages/design_system/`

## Anti-patterns a evitar

- duplicar HTML de component oficial dentro de página ou módulo
- criar “quase iguais” por pressa
- usar tokens visuais diretamente no template quando já existe classe semântica
- introduzir novos caminhos legados
- misturar responsabilidade de component base com composição de página

## Checklist rápido de decisão

Antes de subir uma mudança de UI, responder:

1. isso reutiliza um component oficial?
2. se não reutiliza, por quê?
3. isso é base component, composite, pattern ou page composition?
4. a API nova ficou curta e previsível?
5. isso respeita tema/tenant?
6. o showcase ou a documentação precisam ser atualizados?

