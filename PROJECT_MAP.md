# PROJECT_MAP.md

## Visão rápida
Hubx Market é organizado como um monorepo com separação clara entre backend, UI, infraestrutura e documentação.

## Estrutura
- `backend/`
  - projeto Django bootstrapado
  - config central (`config/`) com settings separados por ambiente
  - apps por domínio em `app/modules/`
  - namespace de registro `modules.*` via aliases em `backend/modules/`
- `ui/`
  - assets
  - templates
  - componentes compartilhados
  - padrões de página
- `infra/`
  - docker
  - compose
  - scripts de operação
- `docs/`
  - produto
  - arquitetura
  - dados
  - módulos
  - API
  - runbooks
  - prompts
  - UI

## Convenção arquitetural do backend
Cada módulo segue a linha Django tradicional aprimorado:
- `models.py` para ORM
- `admin.py` para registro administrativo
- `tests/` como pacote de testes do módulo
- `domain/` para regras puras
- `application/` para casos de uso
- `infrastructure/` para integrações
- `interfaces/` para web/API/admin

## Convenção de UI
- layouts em `ui/templates/layouts/`
- componentes globais em `ui/templates/shared/components/`
- componentes de formulário em `ui/templates/shared/forms/`
- partials globais em `ui/templates/shared/partials/`
- padrões de página em `ui/templates/patterns/`
- templates por domínio em `ui/templates/<modulo>/`

## Documentos prioritários
- `ARCHITECTURE.md`
- `PRODUCT_RULES.md`
- `docs/data/erd.md`
- `docs/ui/design-system.md`
- `docs/ui/component-library.md`
