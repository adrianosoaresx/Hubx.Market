# Component Library

## Objetivo
Definir os componentes reutilizáveis oficiais do Hubx Market.

## Botão
### Variantes
- primary
- secondary
- ghost
- danger
- success
- link

### Tamanhos
- sm
- md
- lg

### Estados
- default
- hover
- focus
- disabled
- loading

### Ícones
- botões podem receber ícone Lucide à esquerda por `icon_name`
- botões também podem receber ícone Lucide à direita por `icon_right_name`
- usar ícone apenas quando ele ajuda reconhecimento de ação ou estado
- não substituir label textual por ícone sem `aria-label`

### Regras de uso
- `primary`: ação principal da tela ou fluxo; usa a cor primária de conversão do design system e, em tenant-owned surfaces, pode vir de `Tenant.conversion_primary_color` apenas quando validada para contraste AA com texto branco
- `secondary`: alternativa segura ou navegação de apoio
- `ghost`: ação de baixa ênfase em barras, listas e menus
- `danger`: ação destrutiva ou irreversível, sempre com contexto
- `success`: confirmação explícita ou conclusão operacional
- `link`: navegação textual quando a ação não deve parecer botão
- `loading` preserva o tamanho visual e usa `aria-busy`
- links desabilitados usam `aria-disabled` e saem da navegação por teclado

## Icon
Partial oficial:

`ui/templates/shared/partials/icon.html`

Uso:
- navegação
- filtros
- CTAs
- estados críticos
- confiança no checkout
- escopo admin/platform

Tamanhos:
- `sm`
- `md`
- `lg`
- `xl`

## Brand Identity
Partial oficial:

`ui/templates/shared/partials/brand_identity.html`

Responsabilidades:
- renderizar `Tenant.logo_url` quando disponível
- renderizar monograma fallback
- exibir nome da loja ou Hubx Market conforme escopo
- exibir subtítulo curto de contexto quando útil

## Storefront Institutional Hero
Partial oficial:

`ui/templates/shared/partials/storefront_institutional_hero.html`

Responsabilidades:
- renderizar o hero institucional da home tenant-owned
- consumir `storefront_hero` preparado por application/query service, sem lógica de fallback no template
- pode ser reutilizado em preview administrativo, desde que a view entregue o mesmo contrato de contexto usado pelo storefront
- manter imagem raster real quando disponível e esconder a coluna de mídia quando não houver imagem
- preservar CTAs por `button.html` e badges curtos de confiança
- manter altura contida para que filtros/produtos apareçam logo abaixo no primeiro viewport

## Card
### Variantes
- default
- interactive
- stat
- chart
- link-card
- plan-card
- warning
- danger

### Regras de uso
- `card.html` renderiza a base `ds-card ds-surface` para conteúdo editorial/operacional simples
- `stat_card.html` e `chart_card.html` são os componentes oficiais para dashboards; não recriar métricas com cards locais
- links em painel devem usar `ds-link-card` quando precisarem de área clicável completa
- cards públicos de plano usam `ds-plan-card ds-surface`, com `is-recommended` apenas para o plano destacado
- sub-blocos dentro de carrinho, checkout, aquisição e onboarding devem preferir `ds-subpanel` em vez de novas combinações de borda/background

## Badge
Usado para status:
- active
- inactive
- pending
- paid
- canceled
- shipped
- delivered

Regras:
- sempre usar `badge.html` ou helpers de interface que emitam `ds-badge`
- variantes semânticas são `neutral`, `success`, `warning`, `danger` e `info`
- helpers em views podem gerar HTML de badge, mas não devem usar classes Tailwind de cor diretamente

## Alert
Tipos:
- success
- info
- warning
- error
- usar ícone Lucide por padrão quando `icon`/`icon_name` não for informado
- `danger`/`error` usam `role="alert"`; demais variantes usam `role="status"`

## Empty State
- usar `empty_state.html` para ausência de dados, erro recuperável ou primeiro uso
- deve conter título curto, descrição orientada ao próximo passo e ação quando fizer sentido
- ícones são decorativos e não substituem o texto

## Input
Tipos:
- text
- email
- password
- number
- search

Estados:
- default
- focus
- disabled
- invalid
- success

## Select
Mesmo padrão visual e altura do input.

## Textarea
Mesmo padrão estrutural do input.

## Checkbox / Radio / Switch
Devem seguir alinhamento consistente com label e texto auxiliar.

## Table
Padronizar:
- cabeçalho
- linhas
- coluna de ações
- badges de status
- empty state
- `table.html` deve usar as classes `ds-table-*`, `scope="col"` nos cabeçalhos e `caption`/`table_label` quando o contexto não estiver claro visualmente
- `data_table.html` é o bloco preferido para listagens administrativas, combinando toolbar, tabela, paginação e empty state
- linhas devem preservar altura estável, hover sem deslocamento e cores por tokens semânticos

## Filter Bar / Table Toolbar
- `filter_bar.html` é o componente oficial para busca, status, filtros extras e ações de aplicar/limpar
- filtros com HTMX devem declarar `hx-target`, `hx-swap` e loading indicator
- `data_table_toolbar.html` deve concentrar título, descrição, contagem, busca simples, filtros inline e ações de listagem
- filtros e toolbars usam controles compactos (`size="sm"`) em superfícies operacionais para manter densidade de dashboard

## Progress / Callout
- barras de progresso usam `ds-progress` e `ds-progress-bar`
- listas em alertas/callouts usam `ds-callout-list` para manter espaçamento, cor e marcador consistentes
- ações destrutivas em texto usam `ds-link-danger`; ações maiores continuam usando `button.html` com `variant="danger"`

## Navigation
- `breadcrumb.html` deve marcar o item atual com `aria-current="page"`
- `tabs.html` deve usar `aria-current="page"` para a aba ativa quando a aba navegar para outra URL
- links desabilitados devem usar `aria-disabled` e sair da navegação por teclado

## Modal
Partes:
- header
- body
- footer
- ação primária
- ação secundária
- `modal.html` e `drawer.html` devem renderizar `role="dialog"` e `aria-modal="true"` quando abertos
- sempre associar título via `aria-labelledby`; descrição deve usar `aria-describedby` quando existir
- ações de fechar precisam ter label acessível

## Dropdown
- `dropdown.html` usa `<details>/<summary>` nativos para teclado
- itens desabilitados usam `aria-disabled`/`disabled`
- ações destrutivas dentro de menu devem continuar usando copy explícita ou confirmação fora do menu

## Commerce / Checkout
- `product_card.html` deve usar `ds-product-card` e manter imagens reais quando disponíveis; placeholders só comunicam ausência de asset
- `product_gallery.html` usa `ds-product-gallery-*`, imagem principal quadrada e thumbs estáveis em 4 colunas mobile / 5 colunas desktop
- `price_display.html`, `stock_indicator.html` e `quantity_selector.html` são primitives oficiais para preço, disponibilidade e quantidade em catálogo, PDP, carrinho e checkout
- `variant_selector.html` preserva o contrato de `options` vindo do backend e expõe estados `is-selected`, `is-disabled` e `is-invalid`
- `shipping_method_selector.html` e `payment_method_selector.html` usam `ds-choice-*` para cards selecionáveis; não duplicar radios customizados por template
- `cart_item.html`, `order_summary.html` e `checkout_steps.html` formam o kit oficial de carrinho/checkout e devem ser usados por carrinho, review, área do cliente e admin quando exibirem itens/totais
- etapas de checkout devem marcar a etapa atual com `aria-current="step"`
- controles de quantidade precisam manter `aria-label` nos botões de incremento/decremento

## Storefront Footer
Partial oficial:

`ui/templates/shared/partials/footer.html`

Variantes:
- `standard`: storefront, auth e área do cliente
- `compact`: checkout e portal central

Conteúdo:
- identidade da loja
- links úteis
- links institucionais opcionais via contexto `storefront_footer_links`
- menção "Operado com Hubx Market"

## Shells
Templates oficiais:
- `layouts/storefront_shell.html`
- `layouts/admin_shell.html`
- `layouts/account_shell.html`
- `layouts/checkout_shell.html`
- `layouts/auth.html`

Regras:
- não duplicar header/footer por página
- não fixar marca da loja em templates tenant-owned
- separar visualmente admin da loja e platform owner

## Public SaaS Surfaces
- `shared/partials/public_hero.html` é o hero oficial das páginas centrais públicas e mantém o texto sobre asset raster real
- `/plans/` usa `ds-plan-card`, `badge.html`, `alert.html`, `field_error.html` e `ds-card` para a aquisição pública
- `/demo/` usa `ds-card` e `ds-public-option-icon` para os perfis de acesso
- não introduzir estilos inline de hero/card quando o padrão já existir em `design-system.css`
