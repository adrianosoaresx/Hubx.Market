# Visual Regression

## Objetivo

Esta é a primeira baseline de regressão visual do Design System do `Hubx.market`.

Ela cobre as páginas internas do showcase em nível de página, com foco em detectar mudanças visuais amplas antes de expandir para cenários mais granulares.

## Abordagem escolhida

Ferramenta: `Playwright`

Motivo:

- funciona bem com páginas Django renderizadas no navegador real
- suporta snapshots de página completos com pouco setup
- encaixa bem nas rotas internas do showcase já existentes
- permite exercitar o preview por tenant via querystring sem lógica extra

## Cobertura atual

Páginas cobertas:

- `/__internal__/design-system/components/?tenant=default`
- `/__internal__/design-system/forms/?tenant=default`
- `/__internal__/design-system/ecommerce/?tenant=default`
- `/__internal__/design-system/ecommerce/?tenant=storefront`
- `/__internal__/design-system/pages/?tenant=default`
- `/__internal__/design-system/pages/?tenant=default` (auth/account section preview)
- `/__internal__/design-system/pages/?tenant=default` (customer area section preview)
- `/__internal__/design-system/pages/?tenant=storefront`
- `/__internal__/design-system/pages/?tenant=demo` (admin dashboard + product + order + customer flow baseline)
- `/__internal__/design-system/pages/?tenant=nike`

Viewports:

- desktop (`chromium`)
- tablet (`iPad Pro 11 landscape`) para cenários selecionados

Arquivo de teste:

- `tests/visual/showcase.spec.js`

## Como rodar

Instalar dependências:

```bash
npm install
npx playwright install chromium
```

Executar a suíte:

```bash
npm run test:visual
```

Atualizar snapshots:

```bash
npm run test:visual:update
```

## Governança de snapshots

Use a suíte visual para cobrir diferenças visuais com impacto real no produto, não para registrar toda pequena variação possível.

### Quando adicionar um novo snapshot

Adicione um novo snapshot quando pelo menos um destes critérios for verdadeiro:

- existe um novo fluxo crítico de produto ainda não coberto
- existe um tenant ou tema com diferença visual realmente relevante
- existe um novo risco de viewport que muda layout, hierarquia ou densidade da página
- houve um refactor importante de layout, tema ou estrutura visual global
- uma nova page template oficial entrou no showcase e representa um fluxo importante

### Quando normalmente não adicionar

Em geral, não adicione um novo snapshot quando o caso for apenas:

- uma combinação redundante de tenant já bem representada por outro preview
- uma pequena variação textual ou de conteúdo sem impacto estrutural
- um caso por componente isolado que ainda não justifica expansão da baseline em nível de página
- um estado muito específico que já aparece dentro de uma página coberta
- um breakpoint extra que não muda materialmente o comportamento visual

### Regra prática de decisão

Antes de expandir a matriz, confirme:

1. este snapshot cobre um risco novo?
2. ele ajuda a detectar regressões que os snapshots atuais provavelmente não pegariam?
3. ele continuará fácil de manter daqui a alguns meses?

Se a resposta para uma dessas perguntas for “não”, prefira não adicionar.

### Como atualizar a baseline com responsabilidade

Ao atualizar snapshots:

- revise o diff visual com o mesmo cuidado de um diff de código
- confirme que a mudança foi intencional e não efeito colateral
- evite atualizar toda a baseline sem necessidade
- se a mudança visual vier de refactor estrutural, atualize esta documentação para refletir a nova cobertura
- se a mudança ampliar a matriz, explique brevemente no PR por que a nova cobertura foi adicionada

## O que esta baseline cobre

- regressão visual de páginas inteiras do showcase
- camada visual principal do Design System
- preview padrão e tenants alternativos com maior impacto visual
- uma viewport secundária de tablet para páginas-chave
- um fluxo público completo sob tenant alternativo (`storefront`) via preview de páginas
- uma baseline admin/operações em tenant alternativo (`demo`) via preview de páginas, incluindo dashboard e fluxos de products/orders/customers
- uma baseline focada na customer area no tenant padrão via preview de páginas
- uma baseline focada em auth/account no tenant padrão via preview de páginas

## O que ainda não cobre

- snapshots por componente isolado
- múltiplos breakpoints para toda a matriz
- múltiplos tenants para todas as páginas
- interações mais profundas de HTMX ou overlays

Esses pontos podem entrar em ondas futuras, mas a baseline atual já oferece uma proteção prática e de baixo risco.

## Próximas adições que ainda fazem sentido

Se a suíte crescer nas próximas ondas, os próximos candidatos mais razoáveis são:

- um único fluxo adicional de customer area sob tenant alternativo
- um único cenário tablet adicional para `pages?tenant=storefront`
- um cenário focado em refactor global de tema, quando houver mudança ampla em tokens ou tenant packs

## Matriz desta onda

Desktop (`chromium`)

- `components` com `tenant=default`
- `forms` com `tenant=default`
- `ecommerce` com `tenant=default`
- `ecommerce` com `tenant=storefront`
- `pages` com `tenant=default`
- `pages` com `tenant=default` (auth/account section preview)
- `pages` com `tenant=default` (customer area section preview)
- `pages` com `tenant=storefront`
- `pages` com `tenant=demo` (admin dashboard + product + order + customer flow)
- `pages` com `tenant=nike`

Tablet (`tablet`)

- `ecommerce` com `tenant=storefront`
- `pages` com `tenant=default`

## Cobertura adicional da wave 5

Fluxo de auth/account no tenant padrão:

- `login page template`
- `register page template`
- `forgot password page template`
- `reset password page template`
- `account overview page template`

Esse cenário é coberto de forma enxuta por:

- `/__internal__/design-system/pages/?tenant=default`

Além do snapshot full-page já existente, a suíte agora inclui um snapshot focado na seção `Auth / Account Page Templates`, o que aumenta a sensibilidade para regressões nessa área sem abrir uma nova matriz de tenants.

## Cobertura adicional da wave 6

Fluxo de customer area no tenant padrão:

- `orders page template`
- `order detail page template`
- `addresses page template`
- `profile page template`

Esse cenário é coberto de forma enxuta por:

- `/__internal__/design-system/pages/?tenant=default`

Além do snapshot full-page já existente, a suíte agora inclui um snapshot focado na seção `Customer Area Page Templates`, o que aumenta a sensibilidade para regressões nessa área sem abrir uma nova matriz de tenants.

## Cobertura adicional desta onda

Fluxo público completo sob tenant alternativo:

- `catalog page`
- `product detail page`
- `checkout page`

Esses previews são cobertos de forma enxuta por:

- `/__internal__/design-system/pages/?tenant=storefront`

Essa rota já reúne os page templates oficiais do fluxo público, então ela oferece confiança end-to-end sem multiplicar snapshots por template isolado.

## Cobertura adicional da wave 4

Fluxo admin/operações sob tenant alternativo:

- `admin dashboard page template`
- `admin products list page template`
- `admin product detail page template`
- `admin product form page template`
- `admin orders list page template`
- `admin order detail page template`
- `admin customers list page template`
- `admin customer detail page template`

Esse cenário é coberto de forma enxuta por:

- `/__internal__/design-system/pages/?tenant=demo`

Dentro do preview de páginas, a área administrativa aparece no topo da página e os fluxos de produtos, pedidos e clientes vêm logo em seguida, então esse snapshot funciona como baseline prática do fluxo interno sob um tenant não-default sem ampliar a matriz além do necessário.
