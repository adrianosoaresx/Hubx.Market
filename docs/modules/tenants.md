# Tenants

## Responsabilidade
Gerenciar tenant, branding, contato, manutenção e onboarding.

## Entidades principais
- Tenant
- StoreTheme
- StoreContact

## Casos de uso
- criar tenant
- ativar manutenção
- configurar identidade visual

## Regras de negócio
- tenant resolvido por subdomínio
- identidade institucional de storefront pertence ao tenant e pode usar campos `storefront_hero_*`
- `logo_url` representa a imagem pública opcional da marca do tenant
- `conversion_primary_color` representa a cor primária opcional de CTAs de conversão do tenant e deve manter contraste AA com texto branco
- o hero institucional é configuração leve de home: título, descrição, imagem remota, CTA e flag de exibição
- lojistas configuram logo, cor de conversão e hero em `/ops/branding/`, que grava apenas `Tenant.logo_url`, `Tenant.conversion_primary_color` e campos `Tenant.storefront_hero_*`
- fallback visual do hero deve usar somente dados já resolvidos do próprio tenant, nunca conteúdo global de outra loja
- superfícies de commerce devem falhar fechado quando `request.tenant` não estiver resolvido
- subdomínio inexistente sob `HUBX_MARKET_ROOT_DOMAIN` deve responder `404`
- domínios reservados (`www`, `app`, `api`, `docs`, `cdn`) continuam fora da resolução de loja
- `custom_domain` segue como contrato de modelo, mas ainda não participa da resolução HTTP neste estágio
- o tenant demo oficial configurado em `HUBX_MARKET_DEMO_TENANT_SUBDOMAIN` é marcado como somente leitura em runtime por `DemoTenantReadOnlyMiddleware`
- o modo somente leitura bloqueia métodos unsafe em superfícies tenant-owned, exceto endpoints de sessão/login/logout necessários para entrar e sair da demo

## Clarificação do contrato atual
- a resolução HTTP oficial de tenant continua sendo apenas `subdomain + HUBX_MARKET_ROOT_DOMAIN`
- hosts fora desse domínio principal não devem ser tratados como loja por inferência
- enquanto `custom_domain` não entrar no resolver HTTP, o comportamento esperado para esses hosts é:
  - `request.tenant = None`
  - nenhuma superfície de commerce deve se comportar como se uma loja válida tivesse sido resolvida
- isso mantém o sistema honesto: `custom_domain` hoje é readiness de modelo, não capability ativa
- em desenvolvimento local, subdomínios `*.localhost` podem resolver tenant para suportar a demo `hubx-demo.localhost`

## Public Self-Service Signup

Status: **implementado atrás de feature flag**.

Rota:

```text
/plans/signup/
```

Escopo entregue:

- habilitado somente com `HUBX_PUBLIC_SIGNUP_ENABLED=1`;
- exige `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN` quando `HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN=1`;
- `subscriptions` expõe a view pública e `tenants.application.public_tenant_signup_commands` orquestra o provisionamento;
- cria `Tenant` ativo em `maintenance_mode`, `TenantOnboarding` concluído, `TenantSubscription(status=active)` para os planos públicos atuais e `OwnerUser` inicial;
- `TenantSubscription` registra Asaas como provider-alvo padrão de billing SaaS, sem criar cobrança externa;
- owner inicial recebe senha utilizável pela fronteira de `accounts`;
- `Customer`, catálogo, pedido, pagamento, invoice, domínio customizado e recurso externo de billing provider não são criados.

Guardrails preservados:

- subdomínio continua sendo o identificador público do tenant;
- slugs reservados e duplicidade de tenant são bloqueados antes da criação;
- corrida concorrente de slug/subdomínio deve retornar erro de formulário, não 500;
- e-mail já vinculado a usuário/owner existente deve seguir aquisição assistida;
- criação é transacional e auditada tenant-scoped;
- tenant em `maintenance_mode` bloqueia storefront/checkout com 503 e mantém `/accounts/` e `/ops/` disponíveis para configuração.

## Contrato futuro mínimo para `custom_domain`
- quando essa capacidade entrar, ela deve definir explicitamente:
  - normalização do host (`lowercase`, sem porta, sem protocolo)
  - unicidade de domínio customizado entre tenants
  - precedência entre `custom_domain`, subdomínio e hosts reservados
  - comportamento explícito para domínio configurado porém tenant inativo

## Storefront Branding Settings

Status: **implementado**.

A configuração tenant-scoped de logo, cor primária de conversão e hero institucional foi adicionada em:

```text
/ops/branding/
```

Escopo entregue:

- formulário admin para `logo_url`, `conversion_primary_color`, `storefront_hero_enabled`, título, descrição, URL de imagem, texto e destino do CTA;
- preview reaproveitando `shared/partials/storefront_institutional_hero.html`;
- `POST` fino delegando para `tenants.application.storefront_branding_commands.update_storefront_hero(...)`;
- permissão `storefront.branding.manage` no RBAC de `accounts`;
- `AuditLog` tenant-scoped com `tenant.storefront_branding_updated`;
- validação de logo/imagem como URL pública, CTA como caminho interno iniciado por `/` e cor de conversão como hexadecimal `#rrggbb` com contraste mínimo AA contra texto branco.

Guardrails preservados:

- grava somente o `Tenant` resolvido pelo host da loja;
- não altera catálogo, produtos, páginas, pedidos, pagamentos, clientes ou dados platform-only;
- a cor de conversão é exposta para a UI por variáveis CSS sanitizadas no layout base, sem permitir CSS arbitrário;
- não faz upload/storage de imagem nesta fase; recebe apenas URL pública;
- não cria page builder nem lógica visual fora do partial compartilhado.

## Battery J — System Production Closure

Status: **concluída**.

`tenants` coordena a closure sistêmica porque tenant resolution é o primeiro boundary de produção.

Escopo entregue:

- matriz de readiness cross-module por `system_production_readiness_matrix_queries`;
- revisão de gaps de runbook por `system_production_runbook_gap_queries`;
- checklist de smoke produtivo por `system_production_smoke_checklist_queries`;
- closure de observabilidade por `system_production_observability_closure_queries`;
- drill de rollback/incidente por `system_production_rollback_drill_queries`;
- decisão Go/No-Go por `system_production_go_nogo_queries`;
- comando operacional `system_production_closure`.

Comando Go/No-Go:

```bash
python manage.py system_production_closure --review=go-nogo --readiness-matrix-ready --runbooks-ready --smoke-checklist-ready --observability-ready --rollback-drill-ready --residual-risks-accepted --decision-owner-confirmed --docs-updated --decision-recorded
```

Regras:

- a closure não altera settings, flags, tenants, providers ou dados de domínio.
- sinais produtivos são declarativos e devem vir de evidência operacional externa.
- `GO` significa ativação controlada por tenant/provider, não rollout irrestrito.
- `NO-GO` deve abrir bateria corretiva pelo maior blocker.

## Platform Store Management — Tenant Admin Surface Review

Status: **contrato inicial definido**.

A gerência de lojas/tenants deve nascer como surface **platform-only**, separada do admin tenant-scoped da loja.

Rota recomendada:

```text
/ops/platform/tenants/
```

Escopo permitido na primeira execução:

- listar tenants com status operacional;
- abrir detalhe de tenant;
- criar nova loja com `slug` e `subdomain` únicos;
- ativar/desativar tenant sem deletar dados;
- ligar/desligar `maintenance_mode`;
- editar `custom_domain` como contrato de cadastro, ainda sem ativar resolução HTTP.

Fora do recorte inicial:

- deletar tenant;
- editar catálogo, pedidos, pagamentos ou clientes da loja;
- impersonar owner/customer;
- resolver `custom_domain` no middleware HTTP;
- controlar plano/billing SaaS fora de `subscriptions`.

Guardrails:

- exigir contexto de platform owner/admin antes da rota;
- mapear permissão RBAC própria antes de expor ações;
- registrar writes sensíveis em `AuditLog`;
- manter `custom_domain` como contract-only até wave própria de resolver HTTP;
- nunca permitir que a surface use `request.tenant` da loja visitada como autorização de plataforma.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --platform-owner-gate-confirmed --rbac-scope-confirmed --audit-events-confirmed --custom-domain-contract-confirmed --destructive-actions-deferred --tenant-isolation-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Tenant Admin Read-Only Surface Execution`.

## Platform Store Management — Tenant Admin Read-Only Surface Execution

Status: **concluída**.

A primeira surface HTTP read-only foi adicionada em:

```text
/ops/platform/tenants/
```

Escopo entregue:

- query service `platform_tenant_admin_queries` lista tenants ordenados por `slug`;
- a tela exibe nome, slug, subdomínio, domínio customizado, status e atualização;
- KPIs resumem total, ativas, em manutenção e inativas;
- navegação `/ops/` ganha item “Lojas” apenas para roles com permissão `platform.tenants.view`;
- `OpsAuthenticationGateMiddleware` passa a mapear `/ops/platform/tenants/` para permissão própria;
- surface permanece sem forms e sem writes.

Guardrails preservados:

- nenhuma criação/edição/remoção de tenant foi exposta;
- `custom_domain` continua somente cadastro contract-only;
- dados comerciais da loja não são lidos por esta surface;
- a ausência de permissão mostra empty state em modo compatível e vira `403` quando o ops gate está ativo.

Próxima execução recomendada:

- `Platform Store Management — Tenant Detail Read-Only Surface Execution`.

## Platform Store Management — Tenant Detail Read-Only Surface Execution

Status: **concluída**.

A surface read-only de detalhe foi adicionada em:

```text
/ops/platform/tenants/<tenant_slug>/
```

Escopo entregue:

- query service `platform_tenant_admin_queries.get_tenant(slug=...)`;
- link da listagem para o detalhe do tenant;
- detalhe com identidade, roteamento, domínio customizado e estado operacional;
- `404` para slug inexistente;
- empty state compatível quando a role não possui `platform.tenants.view`;
- `403` via ops gate quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`.

Guardrails preservados:

- nenhum write de tenant foi exposto;
- `custom_domain` segue contract-only;
- o detalhe não lê catálogo, pedidos, clientes, pagamentos ou qualquer dado interno de commerce;
- o tenant alvo é parâmetro operacional explícito e não autorização derivada de `request.tenant`.

Próxima execução recomendada:

- `Platform Store Management — Tenant Create Contract Review`.

## Platform Store Management — Tenant Create Contract Review

Status: **contrato definido**.

A criação de tenant deve nascer como write **platform-only** em:

```text
/ops/platform/tenants/new/
```

Campos mínimos:

- `name`: nome público/operacional da loja;
- `slug`: identificador interno único do tenant;
- `subdomain`: subdomínio único sob o domínio raiz.

Campos opcionais iniciais:

- `custom_domain`: cadastro contract-only, sem ativar resolução HTTP;
- `is_active`: estado inicial explícito, default ativo;
- `maintenance_mode`: modo manutenção inicial, default desligado.

Fora do recorte da criação inicial:

- criar owner inicial automaticamente;
- criar catálogo demo automaticamente;
- ativar `custom_domain` no resolver HTTP;
- criar assinatura/billing SaaS;
- impersonar usuário da loja criada;
- deletar ou sobrescrever tenant existente.

Guardrails para a próxima execution:

- exigir permissão específica `platform.tenants.manage` antes do write;
- validar unicidade de `slug` e `subdomain`;
- bloquear subdomínios reservados;
- registrar `AuditLog` platform-scope explícito;
- falhar sem side effects quando qualquer validação falhar;
- rollback inicial é manual: desativar tenant criado incorretamente, não deletar.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=create-contract --platform-permission-confirmed --unique-slug-subdomain-confirmed --reserved-subdomains-confirmed --audit-platform-scope-confirmed --no-bootstrap-side-effects-confirmed --custom-domain-contract-only-confirmed --rollback-manual-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Tenant Create Command Execution`.

## Platform Store Management — Tenant Create Command Execution

Status: **concluída**.

A criação real de tenant agora existe como command service platform-only:

```text
tenants.application.platform_tenant_admin_commands.create_tenant(...)
```

CLI operacional:

```bash
python manage.py platform_tenant_create --name="Nova Loja" --slug=nova-loja --subdomain=nova-loja --actor-label=platform@hubx.market --actor-role=owner
```

Escopo entregue:

- cria `Tenant` com `name`, `slug`, `subdomain`, `custom_domain`, `is_active` e `maintenance_mode`;
- normaliza `slug` e `subdomain` com `slugify`;
- bloqueia `slug` duplicado;
- bloqueia `subdomain` duplicado;
- bloqueia subdomínios reservados;
- bloqueia `custom_domain` duplicado;
- exige role com permissão `platform.tenants.manage`;
- registra `AuditLog` platform-scope com `action=platform.tenant.created`;
- se o audit não registrar, a transação é revertida.

Guardrails preservados:

- não cria owner inicial;
- não cria catálogo demo;
- não cria assinatura/billing;
- não ativa resolver HTTP de `custom_domain`;
- não cria sessão nem impersonação;
- não deleta nem sobrescreve tenant existente.

Próxima execução recomendada:

- `Platform Store Management — Tenant Create Admin Surface Execution`.

## Platform Store Management — Tenant Create Admin Surface Execution

Status: **concluída**.

A surface HTTP de criação foi adicionada em:

```text
/ops/platform/tenants/new/
```

Escopo entregue:

- link “Criar loja” na listagem para roles com `platform.tenants.manage`;
- formulário admin com `name`, `slug`, `subdomain`, `custom_domain`, `is_active` e `maintenance_mode`;
- `POST` delega para `tenants.application.platform_tenant_admin_commands.create_tenant(...)`;
- sucesso redireciona para `/ops/platform/tenants/<tenant_slug>/`;
- erros de validação retornam `400` com mensagens inline;
- role sem permissão vê empty state e não recebe formulário;
- criação mantém `AuditLog` platform-scope obrigatório pelo command service.

Guardrails preservados:

- nenhum owner é criado automaticamente;
- nenhum catálogo demo é criado;
- nenhuma assinatura/billing é criada;
- `custom_domain` continua contract-only;
- a view não escreve diretamente no ORM; ela delega ao command service;
- writes continuam exigindo `platform.tenants.manage`.

Próxima execução recomendada:

- `Platform Store Management — Tenant State Management Contract Review`.

## Platform Store Management — Tenant State Management Contract Review

Status: **contrato definido**.

A mudança de estado de tenant deve nascer como write **platform-only** em:

```text
/ops/platform/tenants/<tenant_slug>/state/
```

Ações permitidas na próxima execução:

- `activate`: marcar tenant como ativo para resolução por subdomínio;
- `deactivate`: marcar tenant como inativo sem deletar dados;
- `maintenance-on`: ligar modo manutenção operacional;
- `maintenance-off`: desligar modo manutenção operacional.

Fora do recorte:

- deletar tenant;
- alterar `slug` ou `subdomain`;
- alterar `custom_domain`;
- encerrar pedidos, pagamentos ou carrinhos;
- criar redirects ou resolver HTTP novo;
- notificar clientes automaticamente.

Guardrails para a próxima execution:

- exigir `platform.tenants.manage`;
- registrar `AuditLog` platform-scope para toda mudança;
- documentar que `is_active=False` afeta resolução por subdomínio;
- `maintenance_mode` é flag operacional de publicação e bloqueia storefront/checkout no resolver HTTP, sem alterar dados de commerce;
- rollback manual é executar a ação inversa.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=state-contract --platform-manage-permission-confirmed --audit-platform-scope-confirmed --resolver-impact-confirmed --no-commerce-side-effects-confirmed --manual-rollback-confirmed --maintenance-semantics-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Tenant State Command Execution`.

## Platform Store Management — Tenant State Command Execution

Status: **concluída**.

Mudanças de estado agora existem como command service platform-only:

```text
tenants.application.platform_tenant_admin_commands.update_tenant_state(...)
```

CLI operacional:

```bash
python manage.py platform_tenant_state --tenant-slug=nova-loja --action=maintenance-on --actor-label=platform@hubx.market --actor-role=owner
```

Ações suportadas:

- `activate`;
- `deactivate`;
- `maintenance-on`;
- `maintenance-off`.

Escopo entregue:

- altera apenas `is_active` ou `maintenance_mode`;
- exige `platform.tenants.manage`;
- retorna erro para action inválida;
- retorna erro para slug inexistente;
- registra `AuditLog` platform-scope com `action=platform.tenant.<action>`;
- guarda estado anterior e novo no metadata auditável;
- se audit falhar, a transação é revertida.

Guardrails preservados:

- não altera `slug`;
- não altera `subdomain`;
- não altera `custom_domain`;
- não toca commerce, owners, billing, redirects, resolver HTTP ou notificações;
- rollback operacional é executar a ação inversa.

Próxima execução recomendada:

- `Platform Store Management — Tenant State Admin Surface Execution`.

## Platform Store Management — Tenant State Admin Surface Execution

Status: **concluída**.

A surface HTTP de state management foi adicionada em:

```text
/ops/platform/tenants/<tenant_slug>/state/
```

Escopo entregue:

- detalhe do tenant renderiza ações de estado para roles com `platform.tenants.manage`;
- ações disponíveis são condicionadas ao estado atual:
  - ativo → `deactivate`;
  - inativo → `activate`;
  - manutenção ligada → `maintenance-off`;
  - manutenção desligada → `maintenance-on`;
- `POST` delega para `tenants.application.platform_tenant_admin_commands.update_tenant_state(...)`;
- sucesso redireciona para o detalhe do tenant;
- slug inexistente retorna `404`;
- role sem permissão não altera estado e volta ao detalhe com resultado de permissão negada.

Guardrails preservados:

- view não altera ORM diretamente;
- cada alteração continua exigindo AuditLog platform-scope pelo command service;
- não há edição de `slug`, `subdomain` ou `custom_domain`;
- não há side effects em commerce, owners, billing, resolver HTTP ou notificações.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Update Contract Review`.

## Platform Store Management — Custom Domain Update Contract Review

Status: **contrato definido**.

A edição de domínio customizado deve nascer como write **platform-only** em:

```text
/ops/platform/tenants/<tenant_slug>/custom-domain/
```

Campo permitido:

- `custom_domain`: domínio normalizado em lowercase, sem protocolo, path ou porta.

Fora do recorte:

- alterar middleware/resolver HTTP;
- validar DNS automaticamente;
- provisionar certificado TLS;
- criar redirects;
- trocar subdomain principal;
- publicar domínio customizado como ativo.

Guardrails para a próxima execution:

- exigir `platform.tenants.manage`;
- normalizar domínio antes de persistir;
- garantir unicidade de `custom_domain` entre tenants;
- permitir limpar `custom_domain`;
- registrar `AuditLog` platform-scope;
- manter `custom_domain` como contract-only, sem resolver HTTP.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-contract --platform-manage-permission-confirmed --normalization-confirmed --uniqueness-confirmed --audit-platform-scope-confirmed --resolver-unchanged-confirmed --dns-tls-out-of-scope-confirmed --rollback-manual-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Command Execution`.

## Platform Store Management — Custom Domain Command Execution

Status: **implementado**.

A execução de domínio customizado foi adicionada em `platform_tenant_admin_commands.update_custom_domain(...)`.

Escopo implementado:

- exige `platform.tenants.manage`;
- localiza o tenant por `tenant_slug`;
- normaliza `custom_domain` para lowercase e remove protocolo, path, query, fragmento, porta e ponto final;
- permite limpar `custom_domain` enviando valor vazio;
- valida formato mínimo de domínio;
- bloqueia duplicidade case-insensitive entre tenants;
- persiste apenas `Tenant.custom_domain`;
- registra `AuditLog` platform-scope com `platform.tenant.custom_domain_updated`;
- reverte a transação se a auditoria obrigatória não for gravada.

CLI operacional:

```bash
python manage.py platform_tenant_custom_domain --tenant-slug demo --custom-domain loja.example.com
python manage.py platform_tenant_custom_domain --tenant-slug demo --clear
```

Fora do recorte:

- resolver `custom_domain` no middleware HTTP;
- validar DNS;
- provisionar TLS;
- criar redirects;
- trocar `subdomain`;
- marcar domínio como verificado/ativo.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Admin Surface Execution`.

## Platform Store Management — Custom Domain Admin Surface Execution

Status: **implementado**.

A edição operacional de domínio customizado foi ligada ao detalhe platform-only do tenant:

```text
/ops/platform/tenants/<tenant_slug>/custom-domain/
```

Escopo entregue:

- detalhe `/ops/platform/tenants/<tenant_slug>/` mostra formulário para roles com `platform.tenants.manage`;
- `POST` delega para `platform_tenant_admin_commands.update_custom_domain(...)`;
- sucesso redireciona para o detalhe do tenant;
- slug inexistente retorna `404`;
- role sem permissão não altera o domínio e redireciona com resultado de permissão negada;
- domínio duplicado/ inválido não persiste alteração;
- limpeza do domínio é suportada enviando campo vazio.

Guardrails preservados:

- a view não escreve diretamente no ORM;
- cada alteração continua exigindo `AuditLog` platform-scope pelo command service;
- a edição permanece contract-only;
- não há DNS, TLS, redirect, verificação externa ou ativação no resolver HTTP.

Próxima execução recomendada:

- `Platform Store Management — Tenant Ops Closure Review`.

## Platform Store Management — Tenant Ops Closure Review

Status: **fechado para o recorte inicial**.

A trilha inicial de operação platform-only de lojas está encerrada com decisão **GO para uso operacional interno controlado**.

Entregas confirmadas:

- inventário `/ops/platform/tenants/`;
- detalhe `/ops/platform/tenants/<tenant_slug>/`;
- criação mínima `/ops/platform/tenants/new/`;
- ações de estado `/ops/platform/tenants/<tenant_slug>/state/`;
- edição/limpeza de `custom_domain` em `/ops/platform/tenants/<tenant_slug>/custom-domain/`;
- command services em `tenants.application`;
- RBAC com `platform.tenants.view` e `platform.tenants.manage`;
- writes auditáveis com `AuditLog` platform-scope;
- testes de contrato, comando e surface HTTP.

Decisão objetiva:

- a surface já serve para administrar cadastro operacional de lojas;
- a surface ainda não é bootstrap completo de loja;
- `custom_domain` permanece cadastro contract-only;
- não há ativação de DNS/TLS/resolver HTTP;
- não há owner inicial automático;
- não há billing SaaS automático;
- não há deleção/impersonação.

Comando de closure:

```bash
python manage.py platform_tenant_admin_surface_review --review=ops-closure --read-surface-confirmed --create-surface-confirmed --state-surface-confirmed --custom-domain-surface-confirmed --rbac-enforced-confirmed --audit-platform-scope-confirmed --contract-only-boundaries-confirmed --docs-tests-confirmed
```

Próximas trilhas candidatas:

- `Platform Store Management — Owner Bootstrap Review`;
- `Platform Store Management — Custom Domain Runtime Resolver Review`.

## Platform Store Management — Owner Bootstrap Review

Status: **contrato definido**.

O bootstrap inicial de owner deve nascer como ação platform-only separada da criação mínima de tenant:

```text
/ops/platform/tenants/<tenant_slug>/owner-bootstrap/
```

Campos mínimos:

- `owner_email`: e-mail do primeiro `OwnerUser` da loja;
- `owner_name`: nome operacional opcional;
- `owner_role`: role inicial fixa como owner/admin completo.

Decisão de fronteira:

- `tenants` orquestra a ação porque o alvo é um tenant da plataforma;
- `accounts` deve continuar dono da persistência de `OwnerUser` e do fluxo de convite/recuperação;
- `OwnerUser` não é `Customer`;
- a criação não deve definir senha manual;
- o caminho seguro é invitation/recovery, não login automático.

Fora do recorte:

- definir senha manualmente na criação;
- logar ou impersonar o owner automaticamente;
- criar catálogo demo;
- ativar billing SaaS;
- criar segundo owner inicial quando já existir owner ativo;
- misturar `Customer` com `OwnerUser`.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=owner-bootstrap --tenant-manage-permission-confirmed --owner-identity-boundary-confirmed --invitation-flow-confirmed --no-password-manual-confirmed --audit-platform-scope-confirmed --duplicate-owner-guard-confirmed --no-commerce-side-effects-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Owner Bootstrap Command Execution`.

## Platform Store Management — Owner Bootstrap Command Execution

Status: **implementado**.

O bootstrap inicial de owner agora existe como command service platform-only em:

```text
platform_tenant_admin_commands.bootstrap_owner(...)
```

CLI operacional:

```bash
python manage.py platform_tenant_owner_bootstrap --tenant-slug demo --owner-email owner@example.com --owner-name "Owner Demo"
```

Escopo entregue:

- exige `platform.tenants.manage`;
- localiza tenant ativo por `tenant_slug`;
- valida `owner_email` e `owner_role`;
- bloqueia bootstrap quando o tenant já possui owner ativo;
- delega criação de `OwnerUser` e `User` ao service de `accounts`;
- cria usuário Django com senha inutilizável;
- registra audit tenant-scoped de `accounts`;
- registra `AuditLog` platform-scope com `platform.tenant.owner_bootstrapped`;
- não cria `Customer`, catálogo, billing, sessão ou impersonação.

Próxima execução recomendada:

- `Platform Store Management — Owner Bootstrap Admin Surface Review`.

## Platform Store Management — Owner Bootstrap Admin Surface Review

Status: **contrato definido**.

A surface admin de bootstrap deve nascer como ação no detalhe platform-only do tenant:

```text
/ops/platform/tenants/<tenant_slug>/owner-bootstrap/
```

Elementos mínimos:

- entrada no detalhe da loja;
- campo `owner_email`;
- campo opcional `owner_name`;
- role restrita a `owner` ou `admin`;
- estado explícito quando o tenant já possui owner ativo.

Guardrails:

- exigir `platform.tenants.manage`;
- não renderizar campo de senha;
- delegar `POST` para `platform_tenant_admin_commands.bootstrap_owner(...)`;
- retornar feedback claro para owner já existente, permissão negada e validação;
- não criar catálogo, billing, sessão ou impersonação.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=owner-bootstrap-admin-surface --command-service-confirmed --detail-entry-confirmed --manage-permission-confirmed --no-password-field-confirmed --existing-owner-state-confirmed --audit-feedback-confirmed --no-commerce-side-effects-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Owner Bootstrap Admin Surface Execution`.

## Platform Store Management — Owner Bootstrap Admin Surface Execution

Status: **implementado**.

A surface HTTP de bootstrap do owner inicial foi adicionada ao detalhe platform-only do tenant.

Rota:

```text
/ops/platform/tenants/<tenant_slug>/owner-bootstrap/
```

Escopo entregue:

- detalhe da loja mostra bloco “Owner inicial” para roles com `platform.tenants.manage`;
- quando já existe owner ativo, a UI mostra estado bloqueado;
- quando não existe owner ativo, a UI renderiza form com `owner_email`, `owner_name` e `owner_role`;
- não há campo de senha;
- `POST` delega para `platform_tenant_admin_commands.bootstrap_owner(...)`;
- sucesso redireciona para o detalhe;
- erro de permissão/owner existente redireciona com resultado explícito;
- slug inexistente retorna `404`.

Guardrails preservados:

- a view não escreve diretamente no ORM;
- `accounts` continua dono de `OwnerUser`/`User`;
- não cria `Customer`, catálogo, billing, sessão ou impersonação;
- audit platform-scope continua obrigatório no command service.

Próxima execução recomendada:

- `Platform Store Management — Owner Bootstrap Admin Surface Closure Review`.

## Platform Store Management — Owner Bootstrap Admin Surface Closure Review

Status: **fechado para o recorte inicial**.

A surface de bootstrap de owner inicial está encerrada com decisão **GO para uso operacional interno controlado**.

Entregas confirmadas:

- form no detalhe platform-only quando não há owner ativo;
- estado bloqueado quando já existe owner ativo;
- POST fino para `platform_tenant_admin_commands.bootstrap_owner(...)`;
- permissão `platform.tenants.manage`;
- `AuditLog` platform-scope preservado;
- nenhum campo de senha na UI;
- sem criação de `Customer`, catálogo, billing, sessão ou impersonação.

Comando de closure:

```bash
python manage.py platform_tenant_admin_surface_review --review=owner-bootstrap-admin-closure --form-render-confirmed --post-action-confirmed --permission-denied-confirmed --existing-owner-block-confirmed --audit-platform-scope-confirmed --no-password-field-confirmed --tests-docs-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Owner Bootstrap Production Evidence`.

## Platform Store Management — Owner Bootstrap Production Evidence

Status: **evidência declarativa definida**.

A evidência produtiva do bootstrap de owner inicial foi adicionada ao comando de review.

Comando:

```bash
python manage.py platform_tenant_admin_surface_review --review=owner-bootstrap-production-evidence --environment=production --tenant-slug demo --owner-email owner@example.com --owner-created-confirmed --unusable-password-confirmed --platform-audit-confirmed --tenant-audit-confirmed --no-auto-login-confirmed --rollback-contact-confirmed
```

Evidências exigidas:

- tenant produtivo alvo identificado;
- `OwnerUser` inicial criado/confirmado;
- `User` Django sem senha manual utilizável;
- `AuditLog` platform-scope gravado;
- `AuditLog` tenant-scoped de `accounts` gravado;
- sem sessão automática ou impersonação;
- contato de rollback definido.

Próxima execução recomendada:

- `Platform Store Management — Owner Bootstrap Production Closure`.

## Platform Store Management — Owner Bootstrap Production Closure

Status: **fechado**.

O bootstrap produtivo do owner inicial fica encerrado quando a evidência produtiva está capturada e o handoff operacional está confirmado.

Comando de closure:

```bash
python manage.py platform_tenant_admin_surface_review --review=owner-bootstrap-production-closure --environment=production --tenant-slug demo --owner-email owner@example.com --production-evidence-confirmed --owner-access-ready-confirmed --audit-trail-confirmed --no-impersonation-confirmed --operational-handoff-confirmed
```

Critérios de fechamento:

- evidência produtiva completa;
- owner inicial pronto para fluxo de acesso sem senha manual;
- auditoria platform e tenant-scoped preservada;
- sem login automático ou impersonação;
- handoff operacional registrado.

Próxima execução recomendada:

- `Platform Store Management — Store Management Track Closure`.

## Platform Store Management — Store Management Track Closure

Status: **fechado**.

A trilha Platform Store Management fica encerrada quando tenant ops, owner bootstrap e custom domain runtime estão fechados com evidência produtiva e riscos remanescentes aceitos.

Comando de closure:

```bash
python manage.py platform_tenant_admin_surface_review --review=store-management-track-closure --tenant-ops-closed-confirmed --owner-bootstrap-closed-confirmed --custom-domain-runtime-closed-confirmed --production-evidence-confirmed --docs-tests-confirmed --remaining-risks-accepted
```

Entregas consolidadas:

- operação platform-only de tenants;
- criação, estado, domínio customizado e owner bootstrap;
- `custom_domain` runtime atrás de flag;
- evidências produtivas declarativas;
- documentação e testes atualizados.

Próxima execução recomendada:

- `System ROI Re-Selection Review`.

## System ROI Re-Selection Review

Status: **executável**.

A re-seleção sistêmica de ROI usa a closure de Platform Store Management como pré-condição e classifica a próxima trilha por menor risco e maior impacto operacional/customer-facing.

Comando de review:

```bash
python manage.py system_roi_reselection --tenant-ops-closed-confirmed --owner-bootstrap-closed-confirmed --custom-domain-runtime-closed-confirmed --production-evidence-confirmed --docs-tests-confirmed --remaining-risks-accepted --production-validation-preferred --storefront-regression-pressure-confirmed
```

Critérios de seleção:

- Platform Store Management deve estar fechado;
- regressões visíveis em home/loja/PDP/login/admin elevam ROI de validação funcional;
- payments continua candidato forte quando provider/webhook/refund/conciliação ainda bloqueiam produção real;
- shipping, platform ops e runbooks só vencem quando houver pressão operacional confirmada;
- a review não altera runtime, providers, tenants ou dados de commerce.

Recomendação atual:

- `System Validation Pass 2 — Storefront/Admin Smoke & Template Regression`.

## System Validation Pass 2 — Storefront/Admin Smoke & Template Regression

Status: **executável**.

A validação adiciona um smoke de templates/links para as superfícies que mais impactam teste manual imediato: Home, Loja, Login, Meus pedidos, cockpit `/ops/` e gerenciamento platform de lojas.

Comando:

```bash
python manage.py system_template_regression_smoke --host=hubx-demo.hubx.market
```

Cobertura:

- Home `/` deve renderizar navegação com `Início`, `Loja`, `Pedidos` e `Entrar`;
- o link de pedidos deve apontar para `/accounts/account/orders/`, nunca para o legado `/orders/`;
- Loja `/catalog/` deve renderizar grid e filtro de produtos;
- Login `/accounts/login/` deve expor botão submit `Acessar conta`;
- área de pedidos do cliente `/accounts/account/orders/` deve abrir template, não 404;
- cockpit `/ops/` e `/ops/platform/tenants/` devem renderizar templates admin mínimos.

Guardrails:

- não cria tenant, produto, pedido ou sessão de produção;
- não altera middleware, providers, flags ou dados de commerce;
- usa apenas GETs de leitura via `django.test.Client`;
- autenticação owner é opcional por `--owner-email` e só reutiliza usuário existente.

Próxima execução recomendada:

- `System Validation Pass 2 — Browser Smoke Evidence`.

## Platform Self-Service — Tenant Onboarding MVP

Status: **implementado como portal operacional controlado**.

O primeiro portal self-service de lojas nasce em `/ops/platform/onboarding/`, dentro do boundary de `tenants`, para guiar platform owners/admins na criação de uma loja com plano interno, owner inicial, branding mínimo e domínio contract-only.

Rotas:

```text
GET  /ops/platform/onboarding/
GET  /ops/platform/onboarding/new/
POST /ops/platform/onboarding/new/
GET  /ops/platform/onboarding/<onboarding_id>/
POST /ops/platform/onboarding/<onboarding_id>/step/<step_key>/
POST /ops/platform/onboarding/<onboarding_id>/complete/
```

Escopo entregue:

- modelo `TenantOnboarding` com estados `draft`, `in_progress`, `ready_for_review`, `completed` e `blocked`;
- wizard com passos de loja, plano, owner inicial, branding mínimo, domínio e revisão final;
- conclusão orquestrada por application service, reutilizando boundaries de tenants, subscriptions, accounts e audit;
- `TenantSubscription` criada como contrato comercial interno; nos planos públicos atuais o status inicial é `active`, enquanto `trialing` fica restrito a planos legados/compatibilidade com `trial_days`;
- owner inicial provisionado sem senha manual, login automático ou impersonação;
- branding mínimo persistido como `store_display_name` e `primary_color`, com `primary_color` validado pela mesma regra de contraste e aplicado como `Tenant.conversion_primary_color` na conclusão, sem upload/storage;
- smoke sistêmico inclui `/ops/platform/onboarding/`.

Guardrails:

- acesso mutável exige `platform.tenants.manage`;
- leitura usa `platform.tenants.view`;
- DNS/TLS, billing real, upload de logo, catálogo demo, frete e pagamentos ficam fora do MVP;
- conclusão não edita dados tenant-owned de commerce;
- eventos sensíveis registram `AuditLog` platform-scope.

Integração com aquisição SaaS pública:

- `subscriptions` é dono de `/plans/` e de `SubscriptionAcquisitionLead`;
- `/ops/platform/acquisitions/<lead_id>/convert/` pode criar/preencher uma jornada `TenantOnboarding`;
- essa conversão não chama `complete_onboarding`;
- tenant, owner inicial e `TenantSubscription` só nascem depois da conclusão explícita do wizard por platform admin.

Próxima execução recomendada:

- `Platform Self-Service — Lojista Owner Portal Review`.

## Platform Store Management — Custom Domain Runtime Resolver Review

Status: **contrato definido**.

A ativação runtime de `custom_domain` deve ser tratada como mudança explícita no resolver de tenant, não como efeito colateral da edição cadastral.

Alvo:

```text
TenantResolutionMiddleware
```

Regras de resolução:

- match exato do host com `Tenant.custom_domain` normalizado;
- resolver apenas tenants ativos;
- preservar subdomínio como caminho canônico/compatível;
- não validar DNS nem provisionar TLS dentro do middleware;
- host sem match deve continuar sem tenant, sem fallback global.

Fora do recorte:

- provisionar DNS automaticamente;
- emitir certificado TLS automaticamente;
- criar redirects entre subdomínio e domínio customizado;
- resolver domínio customizado de tenant inativo;
- permitir wildcard em `custom_domain`;
- usar fallback para primeiro tenant.

Guardrails para execução:

- manter rollback por setting/flag;
- adicionar observabilidade para origem da resolução;
- preservar testes existentes que provam que `custom_domain` ainda é ignorado até a flag/code path explícito;
- tratar DNS/TLS como evidência operacional externa.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-runtime --custom-domain-unique-confirmed --resolver-precedence-confirmed --active-tenant-guard-confirmed --safe-miss-confirmed --dns-tls-out-of-scope-confirmed --observability-confirmed --rollback-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Resolver Execution`.

## Platform Store Management — Custom Domain Runtime Resolver Execution

Status: **implementado atrás de flag**.

O middleware de tenant agora pode resolver `custom_domain` quando a flag abaixo estiver ativa:

```python
HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED = True
```

Comportamento:

- default permanece desligado;
- resolução por subdomínio segue preservada e marcada como `tenant_resolution_source=subdomain`;
- quando habilitado, host fora do root domain pode fazer match exato com `Tenant.custom_domain`;
- apenas tenants ativos são resolvidos;
- match por custom domain marca `tenant_resolution_source=custom_domain`;
- host sem match continua sem tenant, sem fallback global;
- DNS, TLS, redirects e verificação externa seguem fora do middleware.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Resolver Admin Evidence Review`.

## Platform Store Management — Custom Domain Runtime Resolver Admin Evidence Review

Status: **contrato definido**.

A ativação do resolver runtime exige pacote mínimo de evidência antes de qualquer rollout por ambiente.

Itens de evidência:

- smoke com flag desligada provando comportamento contract-only;
- smoke com flag ligada provando resolução por `custom_domain`;
- smoke de tenant inativo provando que não resolve;
- smoke de safe miss provando ausência de fallback global;
- evidência de rollback desligando a flag;
- confirmação de que DNS/TLS seguem externos ao app.

Comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-runtime-evidence --resolver-flag-confirmed --flag-off-evidence-confirmed --flag-on-evidence-confirmed --inactive-tenant-evidence-confirmed --safe-miss-evidence-confirmed --rollback-evidence-confirmed --dns-tls-external-confirmed
```

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Resolver Activation Runbook`.

## Platform Store Management — Custom Domain Runtime Resolver Activation Runbook

Status: **implementado**.

O runbook operacional de ativação do resolver runtime foi adicionado ao comando de review:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-runtime-runbook --environment=staging --tenant-slug demo --custom-domain loja.example.com --rollback-owner ops@hubx.market
```

O runbook emite:

- alvo de ambiente, tenant, domínio e responsável por rollback;
- feature flag `HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED`;
- steps de preflight, smoke flag-off, smoke flag-on, tenant inativo, safe miss e rollback;
- comandos mínimos de validação local.

Fora do recorte:

- ativar DNS automaticamente;
- emitir TLS automaticamente;
- alterar configuração real de ambiente;
- executar rollout produtivo sem evidência capturada.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Staging Activation Evidence`.

## Platform Store Management — Custom Domain Runtime Staging Activation Evidence

Status: **evidência declarativa definida**.

A evidência de staging do resolver runtime foi adicionada como pacote verificável no comando de review.

Comando:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-staging-evidence --environment=staging --tenant-slug demo --custom-domain loja.example.com --flag-off-confirmed --flag-on-confirmed --inactive-tenant-confirmed --safe-miss-confirmed --rollback-confirmed --dns-tls-external-confirmed
```

Evidências exigidas:

- staging target definido;
- flag desligada mantém `custom_domain` contract-only;
- flag ligada resolve `custom_domain` para tenant ativo;
- tenant inativo não resolve;
- safe miss não usa fallback global;
- rollback por flag off confirmado;
- DNS/TLS continuam externos ao app.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Production Gate Review`.

## Platform Store Management — Custom Domain Runtime Production Gate Review

Status: **gate produtivo definido**.

O gate produtivo do resolver runtime de `custom_domain` agora retorna decisão objetiva **GO/NO-GO**.

Comando:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-production-gate --environment=production --tenant-slug demo --custom-domain loja.example.com --staging-evidence-confirmed --dns-tls-confirmed --feature-flag-confirmed --rollback-owner-confirmed --monitoring-window-confirmed --support-comms-confirmed
```

Critérios de GO:

- evidência staging completa;
- tenant/domínio produtivo alvo definidos;
- DNS/TLS confirmados externamente;
- feature flag definida para ativação/rollback;
- responsável por rollback definido;
- janela de monitoramento pós-ativação definida;
- comunicação/support readiness confirmada.

Critérios de NO-GO:

- qualquer critério acima ausente;
- alvo de tenant/domínio vazio;
- ausência de rollback imediato por flag.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Production Activation Evidence`.

## Platform Store Management — Custom Domain Runtime Production Activation Evidence

Status: **evidência declarativa definida**.

A evidência de ativação produtiva do resolver `custom_domain` foi adicionada ao comando de review.

Comando:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-production-activation --environment=production --tenant-slug demo --custom-domain loja.example.com --production-gate-go-confirmed --flag-enabled-confirmed --custom-domain-smoke-confirmed --subdomain-smoke-confirmed --safe-miss-confirmed --rollback-ready-confirmed --monitoring-captured-confirmed
```

Evidências exigidas:

- gate produtivo retornou GO;
- feature flag habilitada no ambiente alvo;
- smoke de `custom_domain` resolvendo tenant ativo;
- smoke de subdomínio canônico preservado;
- smoke de safe miss sem fallback;
- rollback por flag off pronto;
- janela de monitoramento capturada.

Próxima execução recomendada:

- `Platform Store Management — Custom Domain Runtime Production Closure`.

## Platform Store Management — Custom Domain Runtime Production Closure

Status: **fechado**.

O runtime produtivo de `custom_domain` fica encerrado quando a ativação pós-GO possui evidência capturada, rollback pronto e handoff de suporte.

Comando de closure:

```bash
python manage.py platform_tenant_admin_surface_review --review=custom-domain-production-closure --environment=production --tenant-slug demo --custom-domain loja.example.com --activation-evidence-confirmed --resolver-source-confirmed --rollback-ready-confirmed --monitoring-confirmed --dns-tls-external-confirmed --support-handoff-confirmed
```

Critérios de fechamento:

- evidência de ativação produtiva capturada;
- `tenant_resolution_source=custom_domain` validado;
- rollback por flag off pronto;
- monitoramento pós-ativação capturado;
- DNS/TLS permanecem externos ao app;
- handoff de suporte confirmado.

Próxima execução recomendada:

- `Platform Store Management — Store Management Track Closure`.
