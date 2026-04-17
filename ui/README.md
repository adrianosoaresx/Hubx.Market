# UI

Camada de interface do Hubx Market.

## Stack
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

## Arquitetura do Design System

O Design System do Hubx Market vive dentro de `ui/` e conecta:

- tokens exportáveis do Figma
- temas por contexto e tenant
- CSS variables para runtime
- componentes reutilizáveis em Django templates
- patterns com HTMX
- layouts e page templates para acelerar telas

## Estrutura principal

- `tokens/`: tokens primitivos, semânticos e de componentes
- `themes/`: definição fonte dos temas por contexto
- `static/css/`: CSS runtime do Design System
- `templates/shared/components/`: biblioteca de componentes
- `templates/shared/patterns/`: composições e flows reutilizáveis
- `templates/layouts/`: shells de interface
- `templates/pages/templates/`: esqueletos de páginas
- `docs/`: documentação operacional do sistema

## Regras

- Todo componente deve depender de tokens ou classes semânticas
- Temas de tenant não podem hardcodar estrutura visual fora do contrato
- Patterns HTMX devem definir `hx-target`, `hx-swap` e estado de loading
- Módulos de produto devem reutilizar `shared/components/` antes de criar HTML novo

## Documentação de referência
- `docs/ui/design-system.md`
- `docs/ui/component-library.md`
- `docs/ui/forms-and-validation.md`
- `ui/docs/design-system-architecture.md`
- `ui/docs/component-api.md`

## Design System Governance

As regras práticas de evolução do Design System vivem em:

- `ui/docs/design-system-governance.md`
- `ui/docs/ui-pr-checklist.md`

Antes de criar novo HTML, component, composite ou pattern, desenvolvedores devem revisar esses dois documentos para confirmar reuso, encaixe na taxonomia oficial e checklist de PR de UI.

## Token Build

Os tokens fonte vivem em:

- `ui/tokens/primitives.json`
- `ui/tokens/semantic.json`
- `ui/tokens/components.json`

O CSS gerado a partir desses arquivos vive em:

- `ui/tokens/build/css-vars.css`
- `ui/static/css/generated-tokens.css`

Para regenerar a saída:

```bash
python ui/tokens/build/build_css_vars.py
```

O runtime continua consumindo `ui/static/css/design-system.css`, que agora importa o arquivo gerado.

## Visual Regression

A baseline inicial de regressão visual do Design System está documentada em:

- `ui/docs/visual-regression.md`

Ela cobre as páginas internas do showcase em nível de página usando Playwright.
