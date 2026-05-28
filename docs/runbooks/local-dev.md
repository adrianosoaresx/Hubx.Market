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

O script define:

- `HUBX_MARKET_ROOT_DOMAIN=localhost`
- `HUBX_MARKET_PUBLIC_PORT=8002`
- `ALLOWED_HOSTS=.localhost,localhost,127.0.0.1,testserver`
- `HUBX_OPS_AUTH_GATE_ENFORCED=1`

Links principais:

- portal central: `http://localhost:8002/`
- login central: `http://localhost:8002/accounts/login/`
- loja/home: `http://hubx-demo.localhost:8002/`
- loja/catálogo: `http://hubx-demo.localhost:8002/catalog/`
- cockpit/admin da loja: `http://hubx-demo.localhost:8002/ops/`
- admin de lojas/platform tenants: `http://localhost:8002/ops/platform/tenants/`
- wizard de onboarding de lojas: `http://localhost:8002/ops/platform/onboarding/`
- Django admin técnico: `http://hubx-demo.localhost:8002/admin/`

Usuários locais de teste:

- platform admin: `platform.owner@hubx.market`
- store admin da `hubx-demo`: `store.owner@hubx.market`
- senha padrão: `secret`

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

Observação: portal central, loja, admin da loja, admin de lojas/platform e wizard rodam no mesmo servidor Django. Em desenvolvimento, o portal central usa `localhost`, enquanto storefront/admin tenant-owned usam `{loja}.localhost`. Em produção, o contrato equivalente é `hubx.market` e `{loja}.hubx.market`.
