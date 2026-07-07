# Local Development

## Objetivo
Subir o Hubx Market localmente.

## Componentes
- backend
- redis
- postgres
- celery worker

## Observação
Em desenvolvimento, exemplos de host podem usar:
- `lojax.localhost`
- `demo.localhost`

## Hubx demo local

Para subir a loja `hubx-demo` com resolução multi-tenant por subdomínio local, use `localhost` para o portal central e `{loja}.localhost` para lojas tenant-owned.

```powershell
.\scripts\start-hubx-demo.ps1
```

Por padrão, o script aplica migrations, garante os tenants/usuários locais da demo e executa `seed_demo_catalog` para resetar o catálogo do tenant `hubx-demo`, aplicar o nome `Hubx Market Demo`, limpar eventos de descoberta e copiar fixtures JPG realistas para `MEDIA_ROOT`. Use `-SkipUsers` apenas quando quiser preservar manualmente identidades/tenants locais e `-SkipSeed` apenas quando quiser preservar manualmente a base demo local.

O script define:

- `HUBX_MARKET_ROOT_DOMAIN=localhost`
- `HUBX_MARKET_PUBLIC_PORT=8002`
- `HUBX_MARKET_DEMO_TENANT_SUBDOMAIN=hubx-demo`
- `HUBX_PLATFORM_TENANT_SLUG=platform-system`
- `ALLOWED_HOSTS=.localhost,localhost,127.0.0.1,testserver`
- `HUBX_OPS_AUTH_GATE_ENFORCED=1`

Links principais:

- portal central: `http://localhost:8002/`
- login central: `http://localhost:8002/accounts/login/`
- planos SaaS: `http://localhost:8002/plans/`
- demo público: `http://localhost:8002/demo/`
- loja/home: `http://hubx-demo.localhost:8002/`
- loja/catálogo: `http://hubx-demo.localhost:8002/catalog/`
- cockpit/admin da loja: `http://hubx-demo.localhost:8002/ops/`
- admin de lojas/platform tenants: `http://localhost:8002/ops/platform/tenants/`
- wizard de onboarding de lojas: `http://localhost:8002/ops/platform/onboarding/`
- Django admin técnico: `http://hubx-demo.localhost:8002/admin/`

Usuários locais de teste:

- platform admin: `platform.owner@hubx.market`
- admin da loja `hubx-demo`: `admin@hubx-demo.market`
- cliente da loja `hubx-demo`: `cliente@hubx-demo.market`
- senha padrão: `secret`

Contrato de escopo:

- `platform.owner@hubx.market` deve estar ativo apenas no tenant reservado `platform-system`.
- `admin@hubx-demo.market` deve existir como `OwnerUser` ativo apenas na loja `hubx-demo`.
- `cliente@hubx-demo.market` deve existir como `Customer` + `AccountProfile` ativos apenas na loja `hubx-demo`.
- `store.owner@hubx.market`, `admin@hubx.market` e `cliente@hubx.market` são legados locais e não representam o contrato multi-tenant esperado.
- rotas `/ops/platform/...` devem ser acessadas pelo host central `localhost`.
- rotas tenant-owned `/ops/...` devem ser acessadas pelo host da loja `hubx-demo.localhost`.
- `/demo/` deve ser acessado pelo host central e renderiza a escolha entre admin e cliente da loja demo, com links diretos para `hubx-demo.localhost/accounts/demo-session/?profile=...`, sem criar tenant, owner, assinatura ou dados de commerce durante a request. Em ambiente local recém-criado, use `.\scripts\start-hubx-demo.ps1` ou `.\scripts\ensure-platform-owner.ps1 -PublicPort 8002` antes de acessar a página.
- a loja `hubx-demo` é somente leitura: ações de compra, carrinho, checkout, newsletter, reviews, endereços e admin da loja são bloqueadas por middleware para métodos unsafe.
- o catálogo demo deve usar imagens JPG realistas; SVGs de fallback indicam seed antigo e devem ser corrigidos com `seed_demo_catalog --reset-seed --reset-tenant-catalog`.

Para garantir os usuários locais:

```powershell
.\scripts\ensure-platform-owner.ps1
```

Para abrir o acesso platform owner no navegador:

```powershell
.\scripts\access-platform-owner.ps1
```

Alvos disponíveis:

- onboarding: `.\scripts\access-platform-owner.ps1 -Target onboarding`
- admin de lojas: `.\scripts\access-platform-owner.ps1 -Target tenants`

Para abrir o admin tenant-owned da loja demo:

```powershell
.\scripts\access-store-owner.ps1
```

Para reseedar manualmente a demo com imagens realistas:

```powershell
python backend/manage.py seed_demo_catalog --tenant-subdomain hubx-demo --store-name "Hubx Market Demo" --count 50 --images-per-product 4 --reset-seed --reset-tenant-catalog --clear-discovery-events --image-host http://hubx-demo.localhost:8002
```

Para executar a validação E2E local de menus, links, acessos, templates e imagens:

```powershell
python backend/manage.py local_e2e_smoke --fail-on-blockers
```

Observação: portal central, loja, admin da loja, admin de lojas/platform e wizard rodam no mesmo servidor Django. Em desenvolvimento, o portal central usa `localhost`, enquanto storefront/admin tenant-owned usam `{loja}.localhost`. Em produção, o contrato equivalente é `hubx.market` e `{loja}.hubx.market`.
