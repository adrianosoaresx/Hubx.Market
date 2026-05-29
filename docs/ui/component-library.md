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
- usar ícone apenas quando ele ajuda reconhecimento de ação ou estado
- não substituir label textual por ícone sem `aria-label`

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
- renderizar logo futuro quando disponível
- renderizar monograma fallback
- exibir nome da loja ou Hubx Market conforme escopo
- exibir subtítulo curto de contexto quando útil

## Card
### Variantes
- default
- interactive
- stat
- warning
- danger

## Badge
Usado para status:
- active
- inactive
- pending
- paid
- canceled
- shipped
- delivered

## Alert
Tipos:
- success
- info
- warning
- error

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

## Modal
Partes:
- header
- body
- footer
- ação primária
- ação secundária

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
