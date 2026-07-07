# Design System

## Objetivo
Garantir consistência visual, reutilização de componentes e previsibilidade de comportamento em toda a interface do Hubx Market.

## Princípios
- consistência antes de criatividade
- reutilização antes de duplicação
- clareza visual
- acessibilidade
- feedback de estado
- responsividade
- baixo acoplamento entre visual e regra de negócio
- densidade operacional em dashboards, evitando composição promocional em telas de trabalho
- tipografia estável, sem escala dependente de `vw`
- decoração contida: sem orbs/bokeh; fundos devem priorizar superfície, borda, hierarquia e imagem real quando houver hero

## Stack
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

## Tokens visuais iniciais

### Cores
- Brand Highlight: `#FFE797`
- Brand Gold: `#D6A937`
- Primary: `#9A6410`
- Primary Hover: `#794A0C`
- Accent: `#D6A937`
- Surface: `#FFFFFF`
- Background: `#F8FAFC`
- Text: `#0F172A`
- Muted Text: `#475569`
- Border: `#E2E8F0`
- Danger: `#DC2626`
- Warning: `#D97706`
- Success: `#16A34A`

Observação: a paleta de marca segue o logo ouro do Hubx Market. Cores funcionais continuam separadas para preservar leitura de estados.

### Modos claro e escuro
- O tema claro é o padrão inicial e usa os tokens semânticos definidos em `:root`.
- O tema escuro é aplicado por `html[data-color-theme="dark"]`, sobrescrevendo apenas tokens semânticos e aliases de compatibilidade.
- A preferência do usuário fica no navegador em `localStorage` pela chave `hubx-color-theme`.
- Valores aceitos: `light`, `dark` e `system`; `system` segue `prefers-color-scheme`.
- O menu oficial de seleção fica em `ui/templates/shared/partials/navbar.html` e deve ser herdado pelos shells compartilhados.

### Tipografia
Escala base sugerida:
- `text-xs`
- `text-sm`
- `text-base`
- `text-lg`
- `text-xl`
- `text-2xl`

### Raios
- controles: `rounded-lg`
- cards: `rounded-2xl`
- modais: `rounded-2xl`

### Sombra
- `shadow-sm`
- `shadow`
- `shadow-md`

### Aliases runtime de compatibilidade
O build de tokens também exporta aliases antigos ainda usados por alguns templates:

- `--color-surface`
- `--color-surface-default`
- `--color-surface-muted`
- `--color-surface-raised`
- `--color-border`
- `--color-border-muted`
- `--color-border-subtle`
- `--color-border-primary`
- `--color-text`

Esses aliases devem ser tratados como ponte de migração. Novos templates devem preferir os tokens semânticos atuais, como `--color-surface-panel`, `--color-border-default` e `--color-text-primary`.

## Padrão v1 aplicado

O modelo padrão da loja demo agora cobre storefront, área do cliente, checkout, auth,
admin da loja, project/platform owner e portal central.

### Demo oficial
- o tenant `hubx-demo` usa o logo raster oficial Hubx e a paleta ouro definida em `docs/brand.md`
- shells tenant-owned devem aplicar `data-tenant` com o slug real do tenant para ativar a paleta correta
- a demo oficial exibe aviso de "Demo somente leitura" em storefront, admin, conta, auth e checkout
- ações de compra, cadastro e edição devem parecer indisponíveis ou retornar bloqueio seguro quando acionadas
- imagens do catálogo demo devem ser raster realistas, nunca placeholder SVG

### Iconografia
- usar Lucide linear em ações, navegação, estados, confiança e escopo operacional
- stroke padrão: `2px`
- ícones decorativos com texto devem usar `aria-hidden`
- botões só com ícone devem ter `aria-label`
- tokens oficiais:
  - `icon/sm`, `icon/md`, `icon/lg`, `icon/xl`, `icon/stroke`
  - `icon/default`, `icon/muted`, `icon/brand`, `icon/success`, `icon/warning`, `icon/danger`

### Identidade da loja
- header usa logo/nome da loja quando existir
- enquanto não houver `logo_url`, usar fallback por monograma
- storefront não deve fixar "Hubx Market" como marca da loja tenant-owned
- fallback textual em storefront/auth/conta/admin da loja deve usar nome do tenant antes de qualquer rótulo genérico
- Hubx Market aparece como plataforma operadora no footer e em superfícies platform
- tokens oficiais:
  - `brand/logo-size/header`
  - `brand/logo-size/banner`
  - `brand/banner-bg`
  - `brand/banner-text`
  - `brand/banner-accent`

### Banner compacto
- home deve abrir com hero institucional curto, formal e orientado a conversão
- produtos precisam continuar visíveis logo abaixo no primeiro viewport
- o hero pode usar imagem institucional real configurada no tenant ou fallback de produto do próprio tenant
- o hero deve reforçar confiança, frete/disponibilidade e suporte sem virar landing page
- fundos de hero usam superfície/borda/tokens da marca e imagem raster real, não orbs ou gradientes decorativos

### Admin e platform owner
- admin da loja usa identidade do tenant como contexto operacional
- project/platform owner usa Hubx Market como marca principal
- escopo tenant e escopo platform devem ser visualmente explícitos
- tokens oficiais:
  - `admin/sidebar-width`
  - `admin/topbar-height`
  - `admin/content-max`
  - `admin/nav-active-bg`
  - `admin/nav-active-text`
  - `admin/nav-muted`
  - `admin/surface-raised`
  - `admin/risk-accent`
  - `admin/platform-accent`

### Storefront Footer
- footer padrão deve incluir identidade da loja, links úteis e menção discreta a Hubx Market
- links permanentes: Catálogo, Minha conta e Meus pedidos
- links institucionais permitidos: Trocas e devoluções, Política de privacidade, Termos e Contato
- links institucionais devem ser exibidos somente quando a loja tiver páginas/URLs configuradas, para evitar links mortos por tenant
- checkout e portal podem usar footer compacto

## Diretrizes
- usar escala visual limitada
- evitar cores arbitrárias por template
- respeitar tipografia e espaçamento oficiais
- criar componentes reutilizáveis antes de repetir HTML
- aplicar shells e partials compartilhados antes de alterar páginas individualmente
