# Design System Architecture

O Design System do Hubx Market organiza a UI em camadas conectadas:

1. `tokens/`
   - primitives, semantic e component tokens exportáveis
2. `themes/`
   - regras fonte de tema por contexto
3. `static/css/`
   - CSS runtime com variables e classes base
4. `templates/shared/components/`
   - componentes reutilizáveis
5. `templates/shared/patterns/`
   - patterns com estrutura e interações HTMX
6. `templates/layouts/`
   - shells de contexto
7. `templates/pages/templates/`
   - esqueletos de página

## Fluxo

Figma -> tokens JSON -> CSS variables -> Tailwind/classes semânticas -> components -> patterns -> pages

## Token Build

O primeiro passo real de build de tokens gera CSS variables a partir de:

- `ui/tokens/primitives.json`
- `ui/tokens/semantic.json`
- `ui/tokens/components.json`

Saídas geradas:

- `ui/tokens/build/css-vars.css`
- `ui/static/css/generated-tokens.css`

Regeneração:

```bash
python ui/tokens/build/build_css_vars.py
```

Nesta fase, o build cobre principalmente:

- `color`
- `surface`
- `text`
- `border`
- `action`
- `spacing`
- `radius`
- `shadow`

Responsabilidades nesta fase:

- `ui/static/css/generated-tokens.css` e `ui/tokens/build/css-vars.css`: base gerada de tokens
- `ui/static/css/themes.css`: camada manual de tenants e imports de contexto
- `ui/themes/context-*.css`: overrides manuais por contexto de interface
- `ui/themes/tenants/*.css`: packs manuais de aliases por tenant

## Tenant Packs

Os tenant packs agora ficam organizados em:

- `ui/themes/tenants/_template.css`
- `ui/themes/tenants/default.css`
- `ui/themes/tenants/demo.css`
- `ui/themes/tenants/storefront.css`
- `ui/themes/tenants/nike.css`

### Convenção de naming

- usar arquivo em `kebab-case`
- usar o slug do tenant como nome do arquivo
- exemplos:
  - `default.css`
  - `nike.css`
  - `acme-store.css`

`_template.css` é apenas referência copiável e não deve ser importado no runtime.

### O que pertence a um tenant pack

Tenant packs devem sobrescrever apenas aliases de branding e ajustes visuais controlados por tenant, como:

- `--tenant-brand-primary`
- `--tenant-brand-primary-hover`
- `--tenant-brand-secondary`
- `--tenant-radius-base`

Tenant packs não devem definir:

- layout estrutural por contexto
- espaçamento global do shell
- overrides de comportamento de admin/storefront/checkout
- tokens gerados da base do Design System

### O que permanece em context files

Os arquivos `ui/themes/context-*.css` continuam responsáveis por:

- largura máxima do shell
- sidebar width
- gaps estruturais
- diferenças de layout por `admin`, `storefront`, `checkout` e `account`

### O que permanece gerado a partir de tokens

Continuam gerados automaticamente a partir de `ui/tokens/*.json`:

- cores base e semânticas
- spacing scale
- radius scale
- shadow scale
- aliases de component tokens

Para adicionar um novo tenant pack:

1. copiar `ui/themes/tenants/_template.css`
2. renomear para `ui/themes/tenants/<tenant-slug>.css`
3. substituir o seletor por `data-tenant="<tenant-slug>"`
4. sobrescrever apenas aliases de tenant, como:
   - `--tenant-brand-primary`
   - `--tenant-brand-primary-hover`
   - `--tenant-brand-secondary`
   - `--tenant-radius-base`
5. importar o pack em `ui/static/css/themes.css`

Resumo da separação:

1. tokens gerados = base visual do sistema
2. context files = diferenças estruturais por contexto
3. tenant packs = branding e aliases visuais por tenant

## Contextos

- `admin`
- `storefront`
- `checkout`
- `account`

## Multi-tenant

O tenant atua por `data-tenant` e troca aliases visuais controlados, principalmente:

- brand primária
- brand secundária
- raio base

Sem alterar estrutura, spacing scale ou feedback crítico fora do contrato.

## Design System Governance

As regras de governança e adoção do Design System ficam em:

- `ui/docs/design-system-governance.md`
- `ui/docs/ui-pr-checklist.md`

Esses documentos devem ser consultados antes de criar novos components, composites, patterns ou markup de página que possa virar parte da camada compartilhada.
