
# Request Lifecycle — Hubx Market

Este documento descreve o **ciclo completo de uma requisição** dentro do Hubx Market.

O objetivo é padronizar como requests HTTP percorrem o sistema, desde a entrada
até a resposta final, garantindo consistência arquitetural.

---

# Visão geral

Fluxo padrão:

HTTP Request
→ Middleware
→ Tenant Resolution
→ Owner Context Resolution
→ View / Controller
→ Application Service
→ Domain Logic
→ Persistence
→ Domain Events
→ Response

---

# 1. HTTP Request

Uma requisição chega ao sistema através de:

- navegador (UI)
- API externa
- webhook de integração

Exemplos:

GET /products
POST /checkout
POST /api/orders

---

# 2. Middleware

Antes de chegar à view, middlewares executam tarefas transversais.

Exemplos:

- logging
- autenticação
- rate limit
- tenant resolution preliminar
- owner context em superfícies administrativas

---

# 3. Tenant Resolution

O tenant é identificado principalmente pelo **subdomínio**.

Exemplo:

store.hubx.market

O sistema resolve:

tenant_id

Esse tenant passa a acompanhar todo o fluxo da requisição.

Regras:

- nenhum dado pode ser acessado sem tenant
- isolamento entre tenants é obrigatório
- hosts fora de `*.hubx.market` não resolvem tenant por padrão
- `custom_domain` só participa da resolução HTTP quando `HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True`
- resolução por `custom_domain` deve usar match exato de tenant ativo e não deve criar fallback global
- tenant resolvido com `maintenance_mode=True` deve bloquear storefront/checkout com 503, preservando `/accounts/`, `/ops/` e rotas técnicas para configuração
- DNS, TLS e redirects de domínio customizado continuam fora do código da aplicação

---

# 3A. Owner Context Resolution

Em superfícies `/ops/`, depois de `Tenant Resolution` e autenticação Django, o sistema pode resolver:

request.owner_user

Contrato atual:

- só roda para caminhos `/ops` e `/ops/...`
- exige `request.tenant` resolvido
- exige `request.user` autenticado com e-mail
- busca `OwnerUser` ativo no mesmo tenant por e-mail case-insensitive
- quando não encontra owner, mantém `request.owner_user = None`
- não bloqueia a request por si só; autorização continua nos application services via `actor_role`

Objetivo:

- centralizar o contexto do owner atual
- reduzir lookups locais por view
- preservar compatibilidade enquanto autenticação/admin IAM completo ainda evolui

Quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`, um gate posterior para `/ops/` aplica:

- anônimo → redirect para `/accounts/login/?next=...`
- autenticado sem `request.owner_user` ativo → `403`
- autenticado com `request.owner_user` ativo, mas sem permissão do prefixo `/ops/` → `403` e `owner.ops_permission_denied`
- autenticado com `request.owner_user` ativo e permissão suficiente → segue para view

Para writes administrativos de loja, o gate HTTP não é a última defesa:

- `customers` exige `tenant_id` e `customers.manage` no command service para flags manuais;
- `orders` exige `tenant_id` e `orders.manage` no command service para status, fulfillment, cancelamento e exceções de estoque;
- `shipping` exige `tenant_id` e `shipping.manage` no command service para envio, entrega e provider de tracking.

---

# 4. View / Controller

Responsável por:

- validar entrada
- chamar serviço de aplicação
- preparar resposta

Views devem ser **finas**.

Evitar lógica de negócio em views.

---

# 5. Application Service

Camada responsável por orquestrar casos de uso.

Exemplo:

checkout/create_order.py

Responsabilidades:

- coordenar módulos
- aplicar regras de fluxo
- iniciar eventos

Regra adicional para superfícies tenant-owned:

- quando o middleware já resolveu a loja, `tenant_id` deve seguir explicitamente da `view` para os services de `application/`
- query/command services não devem voltar a inferir tenant por contexto global se ele já estiver disponível na requisição
- quando um fluxo ainda operar sem tenant explícito por compatibilidade, isso deve ser tratado como exceção documentada, não como padrão implícito

---

# 6. Domain Logic

Contém regras puras de negócio.

Exemplo:

- cálculo de preço
- validação de cupom
- mudança de status de pedido

Essa camada deve ser isolada de infraestrutura.

---

# 7. Persistence

Camada responsável por persistência via ORM.

Local típico:

models.py

Regras:

- sempre incluir tenant_id
- evitar queries pesadas sem índice

---

# 8. Domain Events

Após ações importantes, eventos podem ser emitidos.

Exemplo:

order.created
payment.paid
shipment.sent

Eventos permitem:

- desacoplamento
- tarefas assíncronas
- integrações externas

---

# 9. Response

Por fim, a resposta retorna ao cliente.

Tipos comuns:

- HTML (UI)
- JSON (API)
- redirect

---

# Fluxo exemplo: criação de pedido

Request:

POST /checkout

Fluxo:

Request
→ Middleware
→ Tenant resolution
→ Owner context, quando `/ops/`
→ Checkout view
→ Checkout application service
→ Domain validation
→ Order persistence
→ order.created event
→ Response

---

# Fluxo exemplo: webhook de pagamento

Request:

POST /payments/webhook

Fluxo:

Webhook request
→ Middleware
→ Signature validation
→ Payment service
→ Update payment status
→ Emit payment.paid event
→ Order update
→ Response 200

---

# Fluxo operacional: readiness produtiva de payments

Operação:

```bash
python manage.py payments_production_readiness --review closure --provider-gate-ready --provider-activation-evidence-ready --webhook-smoke-ready --refund-gate-ready --refund-smoke-evidence-ready-or-no-go-recorded --financial-reconciliation-ready --rollback-runbook-ready --monitoring-window-defined --incident-owner-defined --no-unbounded-rollout --no-sensitive-material-recorded --decision-recorded
```

Fluxo:

Management command
→ Payments production readiness query
→ validação de provider gate/evidence
→ validação de webhook smoke
→ validação de refund gate/evidence
→ validação de financial reconciliation
→ closure com rollback/runbook/monitoring
→ próximos tracks

Observações:

- este fluxo não chama provider real.
- este fluxo não executa refund, pagamento, webhook ou correção financeira.
- este fluxo classifica evidências operacionais já capturadas e mantém rollout amplo fora do escopo.

---

# Fluxo operacional: shipping quote no checkout

Operação:

Checkout delivery step
→ tenant resolvido
→ `checkout_shipping_quote_commands.refresh_quote(...)`
→ `shipping_quote_queries.get_quote(...)`
→ opções checkout-ready
→ atualização de `CheckoutSession.shipping_methods`
→ seleção/total de frete
→ payment/review liberados apenas com entrega válida

Observações:

- falha de CEP/tenant retorna estado explícito e limpa seleção de frete.
- quote skeleton não chama transportadora real nem usa segredo.
- pedido ainda só nasce após escolha de frete, escolha de pagamento e clique em pagar.

---

# Fluxo operacional: leitura de assinatura SaaS

Request:

GET /ops/subscriptions/

Fluxo:

Request
→ Tenant resolution
→ Owner/admin permission `subscriptions.view`
→ Subscriptions admin view
→ `subscription_queries.list_tenant_subscriptions`
→ renderização read-only

Observações:

- a tela pode exibir provider-alvo de billing SaaS já registrado na assinatura.
- a tela não chama API de provider de cobrança.
- a tela não altera plano, status ou pagamentos de pedidos.
- setup/mutação fica em application command e não em view.

---

# Fluxo público: aquisição de plano SaaS

Requests:

```text
GET  /plans/
POST /plans/
```

Fluxo:

Request
→ Tenant resolution pode existir, mas é ignorado para contexto de loja
→ Subscriptions public view
→ `subscription_queries.list_public_plans`
→ `subscription_commands.create_public_acquisition_lead`
→ `SubscriptionAcquisitionLead`
→ `AuditLog` platform-scope
→ Response

Observações:

- o fluxo público não cria `Tenant`, `OwnerUser`, `TenantSubscription`, invoice, pagamento ou catálogo.
- somente planos `active` podem ser solicitados.
- host tenant-owned não deve transformar a página de planos em storefront da loja resolvida.

---

# Fluxo público: signup self-service SaaS

Requests:

```text
GET  /plans/signup/
POST /plans/signup/
```

Fluxo:

Request
→ Tenant resolution pode existir, mas signup opera como contexto central
→ Subscriptions public signup view
→ feature flag `HUBX_PUBLIC_SIGNUP_ENABLED`
→ controle opcional por `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN`
→ `tenants.application.public_tenant_signup_commands`
→ `Tenant` em `maintenance_mode`
→ `TenantOnboarding` concluído
→ `TenantSubscription(status=trialing, trial_ends_at=started_at + plan.trial_days, billing_provider_code=asaas por default)`
→ `accounts.application.initial_owner_provisioning_commands`
→ `OwnerUser` inicial com senha utilizável
→ `AuditLog` tenant-scoped
→ Response

Observações:

- não cria `Customer`, catálogo, pedido, pagamento, invoice ou recurso/cobrança externa no billing provider.
- não coleta dados de cartão; cartão obrigatório é requisito comercial do plano e deve ser resolvido em fluxo seguro hospedado, inicialmente Asaas.
- subdomínio reservado/duplicado e e-mail já usado bloqueiam o signup.
- `/plans/` continua sendo aquisição assistida por lead.

---

# Fluxo platform: fila de aquisições SaaS

Requests:

```text
GET  /ops/platform/acquisitions/
GET  /ops/platform/acquisitions/<lead_id>/
POST /ops/platform/acquisitions/<lead_id>/convert/
POST /ops/platform/acquisitions/<lead_id>/discard/
```

Fluxo:

Request
→ Platform owner context
→ RBAC platform
→ Subscriptions acquisition view
→ `subscription_queries` ou `subscription_commands`
→ `SubscriptionAcquisitionLead`
→ opcional: `tenant_onboarding_commands.create_onboarding`
→ `AuditLog` platform-scope
→ Redirect/render

Observações:

- leitura exige `platform.tenants.view`.
- conversão/descarte exigem `platform.tenants.manage`.
- conversão cria/preenche onboarding, mas não chama complete e não provisiona tenant/owner/assinatura.
- descarte altera apenas o lead.

---

# Fluxo exemplo: login owner/admin

Request:

POST /accounts/login/

Fluxo:

Request
→ Middleware
→ Tenant resolution por subdomínio
→ Login view
→ Accounts owner login command
→ Rate limit por tenant + login + IP
→ Django authentication
→ Validação de `OwnerUser` ativo no tenant
→ Sessão Django
→ AuditLog `owner.login`
→ Redirect seguro para `next` ou `/ops/`

Observações:

- `/accounts/login/` não depende de `OwnerContextMiddleware`, pois o owner ainda não está autenticado.
- `/ops/` continua usando `OwnerContextMiddleware` depois da autenticação para preencher `request.owner_user`.
- quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`, a ausência de `request.owner_user` em `/ops/` bloqueia a request.
- antes de ativar o gate em um ambiente, `ops_auth_gate_readiness --fail-on-blockers` deve validar owners/users por tenant.
- antes de ativar RBAC granular em produção, `ops_rbac_production_readiness --tenant-id <tenant_id> --fail-on-blockers` deve validar matriz, full admin e estado do gate.
- falhas repetidas de login owner/admin retornam `429` e registram `owner.login_rate_limited`.
- MFA/SSO ainda não altera este fluxo; o contrato futuro prevê desafio MFA depois da senha e antes da sessão efetiva.

---

# Fluxo operacional: readiness MFA/SSO owner/admin

Command:

python manage.py owner_mfa_sso_readiness --fail-on-blockers

Fluxo:

Management command
→ Accounts owner MFA/SSO readiness query
→ leitura de settings de contrato
→ validação de provider/config mínima
→ saída Go/No-Go

Observações:

- o comando não ativa MFA/SSO.
- o comando não altera login, sessão, owner ou tenant.
- SSO real futuro deve resolver identidade externa para `User` + `OwnerUser` tenant-scoped.

---

# Fluxo operacional: readiness de enrollment MFA owner/admin

Command:

python manage.py owner_mfa_enrollment_readiness --tenant-id=<tenant_id> --fail-on-blockers

Fluxo:

Management command
→ Accounts owner MFA enrollment query
→ leitura de OwnerUser ativo por tenant
→ leitura de OwnerMfaFactor por tenant
→ contagem de fatores ativos/verificados
→ saída Go/No-Go

Observações:

- o comando não gera segredo MFA.
- o comando não ativa challenge no login.
- owner só conta como enrolled quando possui fator ativo e verificado.

Command:

python manage.py owner_mfa_factor register --tenant-id=<tenant_id> --owner-id=<owner_id>

Fluxo:

Management command
→ Accounts owner MFA enrollment command
→ validação `owners.manage`
→ validação tenant + OwnerUser
→ criação/reativação de OwnerMfaFactor pendente
→ AuditLog `owner.mfa_factor_registered`
→ saída operacional

Observações:

- registro não verifica challenge.
- desativação usa `owner_mfa_factor deactivate` e registra `owner.mfa_factor_deactivated`.

---

# Fluxo exemplo: convite e reset owner/admin

Convite:

POST /ops/owners/{id}/actions/invite/
→ Middleware
→ Tenant resolution
→ Owner context
→ Ops auth gate, quando ativo
→ Owner invite view
→ Accounts owner recovery command
→ validação `owners.manage`
→ criação/reuso de `User` Django ativo
→ token Django de reset
→ EmailLog planejado em notifications
→ AuditLog `owner.invited`
→ Redirect para `/ops/owners/`

Reset:

POST /accounts/reset-password/{uidb64}/{token}/
→ Middleware
→ Tenant resolution
→ Reset password view
→ validação do token Django
→ validação de `OwnerUser` ativo no tenant atual
→ validação de senha
→ atualização do `User`
→ AuditLog `owner.password_reset_completed`
→ Redirect para login

Solicitação de reset:

POST /accounts/forgot-password/
→ Tenant resolution
→ Accounts owner recovery command
→ resposta genérica
→ se owner/user ativo existir no tenant: EmailLog planejado em notifications
→ AuditLog `owner.password_reset_requested`

---

# Fluxo operacional: produção de notifications

Provider gate:

```bash
python manage.py notification_production_delivery --review=provider-gate --provider-credentials-confirmed --sender-domain-confirmed --rollback-confirmed
```

Smoke transacional:

```bash
python manage.py notification_production_delivery --review=smoke --tenant-id=<tenant_id> --recipient-email=<smoke@email>
```

Fluxo:

Management command
→ Notifications production delivery command
→ Provider readiness
→ criação/reuso de `EmailLog` system smoke tenant-scoped
→ `notification_delivery_commands.process_email_log`
→ email backend/provider
→ `EmailLog.sent` ou `EmailLog.failed`
→ evidência com recipient mascarado

Observações:

- dry-run habilitado bloqueia smoke real.
- falha/bounce é classificada para decisão operacional, mas não altera pedidos, clientes ou preferências.
- evidence/monitoring/closure usam snapshot tenant-scoped de `EmailLog`.
- nenhum output operacional deve imprimir e-mail de customer em claro.

---

# Fluxo operacional: lifecycle pós-compra consentido

Command:

```bash
python manage.py customer_retention_lifecycle --review=plan-post-purchase --tenant-id=<tenant_id> --order-id=<order_id>
```

Fluxo:

Management command
→ Customer retention lifecycle command
→ busca `Order` por `tenant_id` + `order_id`
→ valida status pós-compra elegível
→ consulta `NewsletterSubscriber` no mesmo tenant por e-mail
→ se inscrito: cria/reusa `EmailLog` `customer.post_purchase.follow_up`
→ se descadastrado: retorna opt-out sem criar log

Observações:

- o fluxo não envia e-mail diretamente; apenas planeja `EmailLog`.
- opt-out bloqueia a comunicação.
- não há cadência automática, scoring ou campanha recorrente.
- cross-tenant falha antes de consultar/criar log.

---

# Fluxo storefront: conversão data-driven

Listagem pública:

HTTP Request
→ Tenant resolution
→ `CatalogListView`
→ `storefront_catalog_queries.list_products(tenant_id)`
→ enrichment de produto/variante
→ `storefront_conversion_insights.apply_product_card_priority_experiment`
→ ordenação de cards
→ template storefront
→ `storefront_discovery_analytics.record_listing_view`

Observações:

- o experimento usa apenas eventos tenant-scoped de discovery/PDP/CTA.
- o score altera prioridade visual dos cards, não preço, estoque, disponibilidade ou checkout.
- payloads de analytics não carregam PII.
- search/facet drop-off é leitura operacional, não bloqueia request.

---

# Fluxo operacional: System Production Closure

Command:

```bash
python manage.py system_production_closure --review=go-nogo --readiness-matrix-ready --runbooks-ready --smoke-checklist-ready --observability-ready --rollback-drill-ready --residual-risks-accepted --decision-owner-confirmed --docs-updated --decision-recorded
```

Fluxo:

Management command
→ `tenants.application.system_production_closure_queries`
→ valida sinais declarativos de matrix/runbooks/smoke/observability/rollback
→ emite decisão `GO` ou `NO-GO`
→ não altera runtime

Observações:

- `GO` exige evidência operacional externa já capturada.
- `NO-GO` aponta para bateria corretiva.
- o comando não executa smoke real, não chama provider e não altera flags/env.

---

# Fluxo operacional: provisionamento inicial de owner

Command:

python manage.py provision_initial_owner --tenant-id=<tenant_id> --email=<owner@email>

Fluxo:

Management command
→ Accounts initial owner provisioning command
→ validação de tenant ativo
→ validação de e-mail e role inicial
→ criação/normalização de `OwnerUser`
→ criação/reuso de `User` Django
→ senha inutilizável quando user é criado
→ AuditLog `owner.initial_provisioned`
→ readiness via `ops_auth_gate_readiness`

Observações:

- este fluxo é operacional e explícito; não há endpoint público.
- o owner ainda deve usar convite/reset para definir senha.
- o gate `/ops/` só deve ser ativado depois do readiness passar.

---

# Fluxo operacional: preflight de ativação do gate `/ops/`

Command:

python manage.py ops_gate_activation_preflight --tenant-id=<tenant_id> --expect-gate=disabled --fail-on-blockers

Fluxo:

Management command
→ Accounts activation preflight query
→ Ops gate readiness por tenant
→ leitura de `HUBX_OPS_AUTH_GATE_ENFORCED`
→ readiness opcional do provider de e-mail
→ resultado Go/No-Go

Uso:

- antes do switch: `--expect-gate=disabled`;
- depois do switch/redeploy: `--expect-gate=enabled`;
- quando convite/reset precisa sair de fato: `--require-email-delivery`.

---

# Fluxo operacional: evidência de rollout produção

Command:

python manage.py ops_gate_production_rollout --tenant-id=<tenant_id> --fail-on-blockers

Fluxo:

Management command
→ Accounts production rollout query
→ activation preflight
→ notification readiness por tenant
→ consolidação de blockers
→ saída de evidência Go/No-Go

Observações:

- o comando não altera `HUBX_OPS_AUTH_GATE_ENFORCED`.
- o comando não executa deploy/restart.
- falhas de `EmailLog` bloqueiam por padrão.
- rollout deve ser registrado por tenant e janela operacional.

---

# Fluxo operacional: evidência de ativação staging RBAC

Command:

python manage.py ops_rbac_staging_activation_evidence --tenant-id=<tenant_id> --fail-on-blockers

Fluxo:

Management command
→ Accounts RBAC staging evidence query
→ Accounts ops gate activation preflight
→ Accounts RBAC production readiness
→ checklist manual mínimo
→ rollback explícito
→ saída anexável de evidência Go/No-Go

Observações:

- o comando não altera `HUBX_OPS_AUTH_GATE_ENFORCED`.
- o comando não cria/edita owners, roles, users ou tenants.
- execução local só valida o pacote; evidência real exige rodar contra staging.

---

# Fluxo operacional: evidência de ativação production RBAC

Command:

python manage.py ops_rbac_production_activation_evidence --tenant-id=<tenant_id> --fail-on-blockers

Fluxo:

Management command
→ Accounts RBAC production activation evidence query
→ Accounts production rollout evidence
→ Accounts RBAC production readiness
→ notification owner access health
→ checklist manual de produção
→ rollback explícito
→ saída anexável de evidência Go/No-Go

Observações:

- o comando não altera `HUBX_OPS_AUTH_GATE_ENFORCED`.
- o comando não executa deploy/restart.
- provider real de e-mail é exigido por padrão.
- execução local só valida o pacote; evidência real exige rodar contra production.

---

# Fluxo operacional: monitoramento pós-produção RBAC

Command:

python manage.py ops_rbac_post_production_monitoring --tenant-id=<tenant_id> --fail-on-rollback

Fluxo:

Management command
→ Accounts RBAC post-production monitoring query
→ leitura recente de AuditLog owner access
→ leitura recente de EmailLog owner access
→ classificação HEALTHY/WATCH/ROLLBACK
→ saída operacional para change log/plantão

Observações:

- o comando não executa rollback.
- `WATCH` exige triagem humana.
- `ROLLBACK` indica sinal forte, mas a decisão operacional continua externa ao comando.

---

# Fluxo operacional: closure production RBAC

Command:

python manage.py ops_rbac_production_closure --tenant-id=<tenant_id> --fail-on-blockers

Fluxo:

Management command
→ Accounts RBAC production closure query
→ evidência de ativação production
→ snapshot de monitoramento pós-produção
→ decisões finais
→ riscos residuais
→ próximas trilhas recomendadas

Observações:

- o comando não executa ativação, rollback ou deploy.
- `WATCH` não bloqueia por blocker, mas também não é `READY`.
- `BLOCKED` exige corrigir ativação ou rollback signal antes de encerrar.

---

# Fluxo operacional: exportação de evidência auditável

Command:

python manage.py export_audit_evidence --tenant-id=<tenant_id> --format=jsonl

Fluxo:

Management command
→ Audit evidence export query
→ validação de tenant ou platform-scope explícito
→ filtro por módulo/ação/período
→ serialização JSONL/CSV
→ saída textual anexável

Observações:

- o comando não escreve `AuditLog`.
- export platform-scope exige `--platform-scope`.
- export de metadata exige `--include-metadata`.

HTTP:

GET /ops/audit/export/

Fluxo:

Request
→ Tenant resolution
→ Ops auth/RBAC gate
→ Audit evidence export view
→ Audit evidence export query
→ resposta JSONL tenant-scoped

Observações:

- a rota HTTP não exporta platform-scope.
- a rota HTTP herda permissão `audit.view` pelo prefixo `/ops/audit/`.

Closure:

python manage.py audit_evidence_closure --tenant-id=<tenant_id> --fail-on-blockers

Fluxo:

Management command
→ Audit evidence closure query
→ sample de exportação
→ decisões finais
→ riscos residuais
→ próximas trilhas

Observações:

- closure não exporta artefato completo.
- closure não altera logs nem permissões.

Review de export MFA owner/admin:

```bash
python manage.py owner_mfa_audit_evidence_export_review --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved
```

Fluxo:

Management command
→ Owner MFA audit evidence export review query
→ Audit evidence export query tenant-scoped
→ filtro `module=accounts`
→ detecção de ações MFA em `AuditLog`
→ Go/No-Go sem gerar artefato final

Observações:

- a review não consulta tabelas internas de `accounts`.
- metadata não entra no sample por padrão.
- platform-scope permanece fora do recorte MFA.

Execution de export MFA owner/admin:

```bash
python manage.py export_owner_mfa_audit_evidence --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved --format=jsonl
```

Fluxo:

Management command
→ Owner MFA audit evidence export execution query
→ Owner MFA audit evidence export review
→ Audit evidence export query tenant-scoped
→ filtro `module=accounts`
→ filtro de ações MFA
→ saída JSONL/CSV sem metadata

Observações:

- execution não registra novo `AuditLog`.
- execution não habilita platform-scope.
- execution não assina, criptografa ou armazena artefato.

Closure de export MFA owner/admin:

```bash
python manage.py owner_mfa_audit_evidence_export_closure --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved --artifact-delivered --retention-owner-confirmed --storage-decision-recorded --residual-risks-accepted
```

Fluxo:

Management command
→ Owner MFA audit evidence export closure query
→ Owner MFA audit evidence export execution
→ validação de artifact delivery/retenção/storage/riscos
→ classificação READY/BLOCKED
→ próximos tracks sem reimprimir export

Observações:

- closure não reimprime conteúdo JSONL/CSV.
- closure não assina nem armazena artefato.
- closure não altera logs nem permissões.

---

# Fluxo de observabilidade: owner access

Request:

GET /accounts/metrics/owner-access/

Fluxo:

Request
→ token de observabilidade
→ Accounts owner access metrics query
→ contagem de `AuditLog` owner access
→ contagem de `EmailLog` owner access
→ payload Prometheus

Observações:

- o endpoint fica fora de `/ops/` para continuar acessível mesmo se o gate estiver bloqueando operadores.
- o endpoint não expõe payload bruto de logs; apenas contadores por tenant/action/status.

---

# Fluxo de segurança: login owner/admin

Request:

POST /accounts/login/

Fluxo:

Request
→ Tenant resolution
→ Accounts owner login rate limit
→ autenticação Django
→ vínculo `OwnerUser` ativo no tenant
→ política de sessão owner/admin
→ em falha: AuditLog `owner.login_failed` e incremento do contador
→ em lockout: AuditLog `owner.login_rate_limited`, resposta `429` e header `Retry-After`
→ em sucesso: limpeza do contador, expiração explícita e sessão owner/admin ativa

Quando `OWNER_MFA_REQUIRED=1`:

POST /accounts/login/
→ senha válida e `OwnerUser` ativo
→ verificação de fator MFA ativo/verificado
→ sessão pendente curta `hubx_owner_mfa_pending`
→ redirect para `/accounts/login/mfa/`
→ resolução de `secret_reference` via storage resolver
→ se `ref:<path>`, resolução via provider configurado
→ challenge TOTP válido
→ `django_login`
→ política de sessão owner/admin
→ AuditLog `owner.login` e `owner.login_mfa_completed`

Alternativa de recuperação:

POST /accounts/login/mfa/
→ recovery code informado
→ comparação contra hash de `OwnerMfaRecoveryCode`
→ marcação `used_at`
→ `django_login`
→ AuditLog `owner.mfa_recovery_code_used` e `owner.login_mfa_completed`

Observações:

- o rate limit é calculado por tenant + identificador + IP.
- o lockout usa cache Django e não altera `OwnerUser` ou `User`.
- mensagens de falha continuam genéricas para evitar enumeração.
- a duração da sessão usa `OWNER_SESSION_IDLE_SECONDS` ou `OWNER_SESSION_REMEMBER_SECONDS`.
- customer login não herda esse hardening implicitamente.
- rollback do enforcement MFA é `OWNER_MFA_REQUIRED=0` seguido de redeploy/restart.
- recovery codes são uso único e nunca devem aparecer em logs.
- `secret_reference` TOTP deve passar por `owner_mfa_secret_storage` antes de qualquer validação.
- providers externos não devem expor segredo em response, readiness ou AuditLog.

---

# Fluxo operacional: verificação de MFA owner/admin

Operação:

```bash
python manage.py owner_mfa_factor verify --tenant-id=<tenant_id> --factor-id=<factor_id> --challenge=<code>
```

Fluxo:

Management command
→ Accounts owner MFA challenge command
→ permission check `owners.manage`
→ busca `OwnerMfaFactor` ativo por `tenant_id`
→ validação TOTP interna
→ atualização de `is_verified`, `verified_at` e `last_challenged_at`
→ AuditLog `owner.mfa_factor_verified` ou `owner.mfa_factor_verification_failed`

Observações:

- a operação não autentica owner e não cria sessão.
- falha de challenge não persiste o código informado.
- enforcement de MFA no login owner/admin permanece uma etapa futura separada.

---

# Fluxo operacional: surface admin MFA owner/admin

Request:

```http
GET /ops/owners/mfa/
POST /ops/owners/mfa/<factor_id>/verify/
POST /ops/owners/mfa/<factor_id>/deactivate/
```

Fluxo:

HTTP Request
→ Tenant resolution
→ Owner context / ops gate quando habilitado
→ Accounts owner MFA admin view
→ query service ou command service de MFA
→ AuditLog para ações sensíveis
→ Redirect com resultado operacional

Observações:

- a view não decide verificação TOTP nem desativação; ela apenas adapta request/response.
- a lista é tenant-scoped.
- a surface não aplica MFA no login.

---

# Fluxo operacional: readiness de enforcement MFA

Operações:

```bash
python manage.py owner_mfa_break_glass_readiness --tenant-id=<tenant_id>
python manage.py owner_mfa_login_enforcement_readiness --tenant-id=<tenant_id>
python manage.py owner_mfa_operational_closure --tenant-id=<tenant_id>
python manage.py owner_mfa_totp_secret_migration_plan --tenant-id=<tenant_id>
python manage.py owner_mfa_totp_secret_migration_execute --tenant-id=<tenant_id> --factor-id=<factor_id>
python manage.py owner_mfa_local_secret_retirement_readiness --tenant-id=<tenant_id>
python manage.py owner_mfa_local_secret_retirement_execution --tenant-id=<tenant_id> --phase=before
python manage.py owner_mfa_local_secret_retirement_execution --tenant-id=<tenant_id> --phase=after
python manage.py owner_mfa_provider_health --tenant-id=<tenant_id>
GET /accounts/metrics/owner-mfa-provider-health/
python manage.py owner_mfa_provider_health_closure --tenant-id=<tenant_id>
python manage.py owner_mfa_local_secret_code_retirement_readiness --tenant-id=<tenant_id>
python manage.py owner_mfa_local_secret_code_retirement_execute --tenant-id=<tenant_id>
python manage.py owner_mfa_legacy_data_global_sweep
python manage.py owner_mfa_local_secret_parser_removal_review
```

Fluxo:

Management command
→ Accounts readiness query
→ enrollment MFA por tenant
→ contrato de break-glass
→ Go/No-Go para enforcement futuro

Fluxo de execução de migração TOTP:

Management command
→ Accounts migration command service
→ Tenant-scoped OwnerMfaFactor lookup
→ Owner MFA secret storage resolver
→ External secret provider readiness/equivalence check
→ Update `secret_reference` para `ref:<target_ref>` somente com `--execute`
→ AuditLog

Fluxo de readiness para aposentadoria local:

Management command
→ Accounts local secret retirement query
→ Owner MFA secret storage readiness
→ Inventário tenant-scoped de fatores TOTP
→ Go/No-Go para `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`

Fluxo de evidência de execução da aposentadoria local:

Management command
→ Accounts local secret retirement execution query
→ Retirement readiness
→ Validação do setting atual por fase
→ Evidência before/after e rollback

Fluxo de monitoring do provider MFA:

Management command
→ Accounts MFA provider health query
→ Owner MFA secret storage readiness
→ Resolver de `ref:<path>` via provider configurado
→ Status `HEALTHY` / `WATCH` / `CRITICAL`

Fluxo de métricas do provider MFA:

Prometheus scrape
→ Accounts observability token gate
→ Owner MFA provider health metrics query
→ Provider health por tenant com fatores TOTP ativos
→ Payload Prometheus sem segredo

Fluxo de closure do provider MFA:

Management command
→ Accounts MFA provider health closure query
→ Provider health snapshot
→ Verificação de artefatos Prometheus/Grafana
→ Decisões, blockers e riscos residuais

Fluxo de readiness para retirement de código local MFA:

Management command
→ Accounts local secret code retirement query
→ Retirement after evidence
→ Provider health closure
→ Inventário de superfícies `plain:`/legado
→ Go/No-Go para execution posterior

Fluxo de execution para retirement do default local MFA:

Management command
→ Accounts local secret code retirement execution query
→ Code retirement readiness
→ Verificação de `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`
→ Evidência de default desligado e rollback por env

Fluxo de sweep global de dados legados MFA:

Management command
→ Accounts legacy data global sweep query
→ Tenant ids com fatores TOTP ativos
→ Secret storage readiness por tenant
→ Totais globais e blockers por tenant

Fluxo de review para remoção do parser local MFA:

Management command
→ Accounts local secret parser removal query
→ Legacy data global sweep
→ Verificação de `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`
→ Plano de remoção e rollback por deploy

Fluxo de execution para remoção do parser local MFA:

Management command
→ Accounts local secret parser removal execution query
→ Parser removal review
→ Probes `plain:` e legado sem `ref:`
→ Resolver retorna `unsupported-local` sem segredo
→ Decisões, blockers e rollback por deploy

Fluxo de review para provider Vault/KMS MFA:

Management command
→ Accounts Vault/KMS provider review query
→ Provider health closure por tenant
→ Parser removal execution global
→ Contrato de adapter e plano de rollout
→ Decisões, blockers e rollback sem secret material

Fluxo de contrato para adapter Vault/KMS MFA:

Management command
→ Accounts Vault/KMS adapter contract query
→ Vault/KMS provider review
→ Settings/interface/errors/security/test contract
→ Go/No-Go para skeleton sem chamada externa real

Fluxo de execution do skeleton Vault/KMS MFA:

Management command
→ Accounts Vault/KMS skeleton execution query
→ Adapter contract review
→ Secret provider registry resolve probe
→ Resultado ready/missing/unavailable/timeout/permission/invalid-reference
→ Evidência sem valor de segredo

Fluxo de readiness evidence Vault/KMS MFA:

Management command
→ Accounts Vault/KMS readiness evidence query
→ Skeleton execution evidence
→ Provider health closure por tenant
→ Evidence pack com contagens/status
→ Go/No-Go canário sem segredo

Fluxo de review de canário staging Vault/KMS MFA:

Management command
→ Accounts Vault/KMS staging canary query
→ Readiness evidence
→ Owner canário explícito
→ Preflight/checklist/success signals/rollback
→ Go/No-Go manual sem autenticação real

Fluxo de evidence execution do canário staging Vault/KMS MFA:

Management command
→ Accounts Vault/KMS staging canary evidence query
→ Staging canary review
→ Flags manuais de resultado
→ Evidence pack sem segredo
→ Go/No-Go para adapter real

Fluxo de contrato do adapter real Vault/KMS MFA:

Management command
→ Accounts Vault/KMS real adapter contract query
→ Staging canary evidence
→ Confirmações SDK/credenciais/timeouts/rollout
→ Contratos de settings/errors/tests/rollback
→ Go/No-Go para skeleton real/mocável

Fluxo de execution do skeleton real Vault/KMS MFA:

Management command
→ Accounts Vault/KMS real adapter skeleton query
→ Real adapter contract
→ Secret provider registry resolve probe em modo real-adapter
→ Resultado ready/missing/unavailable/timeout/permission/invalid-reference
→ Evidência sem valor de segredo

Fluxo de review de dependência SDK Vault/KMS MFA:

Management command
→ Accounts Vault/KMS SDK dependency review query
→ Real adapter skeleton evidence
→ Matriz provider/pacote/import opcional
→ Confirmações de pinning/licença/rollback
→ Go/No-Go para adapter SDK real

Fluxo de execution do branch SDK Vault/KMS MFA:

Management command
→ Accounts Vault/KMS SDK adapter execution query
→ SDK dependency review
→ Secret provider registry em modo SDK adapter
→ Import lazy do SDK ou unavailable seguro
→ Probe read-only sem valor de segredo

Fluxo de review do endpoint real Vault/KMS MFA:

Management command
→ Accounts Vault/KMS real endpoint review query
→ SDK adapter execution evidence
→ Contrato Hashicorp Vault URL/auth/path/field/timeout
→ Confirmações operacionais
→ Go/No-Go para execução `hvac` real

Fluxo de execution do endpoint Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault endpoint execution query
→ Real endpoint review
→ Secret provider registry em modo Hashicorp Vault endpoint
→ Import lazy de `hvac`
→ Auth token/AppRole e leitura KV v2
→ Probe read-only sem segredo, token ou path completo

Fluxo de smoke staging Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault staging smoke evidence query
→ Hashicorp Vault real endpoint execution
→ Flags manuais de smoke/negative path/redaction/rollback/health
→ Evidence pack redigido
→ Go/No-Go para production readiness

Fluxo de production readiness Vault/KMS MFA:

Management command
→ Accounts Vault/KMS production readiness query
→ Hashicorp Vault staging smoke evidence
→ Owner MFA provider health closure
→ Confirmações de runbook/monitoring/rollback/janela/credencial
→ Decisão GO/NO-GO sem alterar ambiente

Fluxo de production gate Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault production gate query
→ Vault/KMS production readiness
→ Confirmações de tenant/rollout/flags/plantão/rollback/monitoring
→ Activation plan redigido
→ GO/NO-GO operacional sem alterar ambiente

Fluxo de production activation evidence Vault/KMS MFA:

Management command
→ Accounts Vault/KMS production activation evidence query
→ Hashicorp Vault production gate
→ Flags manuais de deploy/flags/probe/login/health/rollback/redaction
→ Evidence pack redigido
→ Próxima janela de monitoramento pós-ativação

Fluxo de post-activation monitoring Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault post-activation monitoring query
→ Production activation evidence
→ Sinais de janela/health/login/suporte/rollback/redaction
→ Classificação HEALTHY/WATCH/ROLLBACK/BLOCKED
→ Próxima ação operacional sem executar rollback

Fluxo de production closure Vault/KMS MFA:

Management command
→ Accounts Vault/KMS production closure query
→ Hashicorp Vault post-activation monitoring
→ Sinais de rollback runbook/riscos residuais/plano de expansão
→ Classificação READY/BLOCKED/ROLLBACK
→ Próxima trilha sem expandir tenant automaticamente

Fluxo de tenant expansion review Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault tenant expansion review query
→ Vault/KMS production closure do tenant canário
→ Validação de tenants-alvo e guardrails de expansão
→ Classificação READY/BLOCKED
→ Próxima evidência por tenant sem ativação global

Fluxo de tenant expansion evidence Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault tenant expansion evidence query
→ Tenant expansion review
→ Confirmations de flags/evidence/monitoring/login/health/rollback/redaction do target
→ Evidence pack redigido
→ Próximo monitoring do target sem expandir novo tenant

Fluxo de target post-expansion monitoring Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault target post-expansion monitoring query
→ Tenant expansion evidence
→ Sinais de janela/health/login/suporte/rollback/redaction do target
→ Classificação HEALTHY/WATCH/ROLLBACK/BLOCKED
→ Próxima review sem liberar novo tenant automaticamente

Fluxo de next tenant expansion review Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault next tenant expansion review query
→ Target post-expansion monitoring
→ Validação de próximos tenants e sinais de cadência
→ Classificação READY/PAUSED/BLOCKED
→ Próximo ciclo sem ativar tenant automaticamente

Fluxo de expansion cadence closure Hashicorp Vault MFA:

Management command
→ Accounts Hashicorp Vault expansion cadence closure query
→ Next tenant expansion review
→ Sinais de decision/archive/risk/rotation/audit evidence
→ Classificação READY/BLOCKED
→ Próxima trilha sem ativar tenant nem exportar evidência formal

Fluxo de rotation runbook Vault/KMS MFA:

Management command
→ Accounts Vault/KMS rotation runbook query
→ Hashicorp Vault expansion cadence closure
→ Sinais de escopo/owner/acesso/janela/rollback/probe/redaction
→ Runbook de rotação e rollback redigido
→ Próxima evidence execution sem executar rotação

Fluxo de rotation evidence Vault/KMS MFA:

Management command
→ Accounts Vault/KMS rotation evidence query
→ Rotation runbook
→ Confirmations de execução/credencial/probe/login/health/rollback/redaction
→ Evidence pack redigido
→ Próximo monitoring pós-rotação sem executar rollback

Fluxo de post-rotation monitoring Vault/KMS MFA:

Management command
→ Accounts Vault/KMS post-rotation monitoring query
→ Rotation evidence
→ Sinais de janela/health/login/suporte/rollback/redaction
→ Classificação HEALTHY/WATCH/ROLLBACK/BLOCKED
→ Próxima closure sem restaurar credencial automaticamente

Fluxo de rotation closure Vault/KMS MFA:

Management command
→ Accounts Vault/KMS rotation closure query
→ Post-rotation monitoring
→ Sinais de decisão/evidência/riscos/retomada/rollback/audit evidence
→ Classificação READY/WATCH/ROLLBACK/BLOCKED
→ Próxima export review sem exportar evidência nem retomar expansão automaticamente

Fluxo de owner MFA track closure:

Management command
→ Accounts owner MFA track closure query
→ Audit owner MFA evidence export closure
→ Sinais de decisão final/rollout/suporte/próximo ROI/riscos
→ Classificação READY/BLOCKED
→ Próxima ROI review sem ativar tenant, provider ou enforcement

Fluxo de security ROI re-selection:

Management command
→ Accounts security ROI re-selection query
→ Owner MFA track closure
→ Matriz de candidatos de segurança
→ Score e recomendação
→ Próxima abordagem sem executar implementação

Fluxo de API key governance foundation:

Management command
→ API keys governance foundation query
→ sinais de superfície/modelo/hash/scopes/revogação/auditoria/last-used/rate-limit
→ contrato mínimo de governança
→ próxima model execution sem gerar segredo real

Fluxo de API key model commands:

Application service
→ API key command service
→ validação de tenant
→ geração de segredo apenas na criação
→ persistência de hash/prefix/scopes/status
→ AuditLog `api_key.created` ou `api_key.revoked`
→ retorno sem expor hash

Fluxo futuro de API key runtime authentication:

HTTP Request
→ Tenant Resolution por subdomínio/contexto
→ leitura de `Authorization: Bearer`
→ extração de prefixo
→ lookup `ApiKey` por `tenant_id + prefix`
→ validação de status ativo
→ validação do segredo completo contra `key_hash`
→ validação do escopo mínimo do endpoint/caso de uso
→ atualização segura de `last_used_at`
→ view/API pública

Skeleton atual:

- `api_keys.application.api_key_runtime_authentication` implementa parser Bearer, lookup tenant-scoped, hash/status/scope check, `last_used_at`, `api_key.auth_failed` e `rate_limit_key` declarativa.
- o skeleton ainda não está plugado em DRF, middleware ou endpoint público.

Adapter DRF futuro:

- deve morar em `api_keys.interfaces`;
- deve ser ativado por view/surface explícita;
- deve delegar ao skeleton runtime;
- deve ler escopo mínimo declarado pela view ou permission dedicada;
- deve retornar principal seguro sem segredo, hash ou header completo;
- não deve entrar em `DEFAULT_AUTHENTICATION_CLASSES` até existir rollout explícito.

Adapter DRF atual:

- `ApiKeyAuthentication` autentica apenas quando a view opt-in recebe `Authorization: Bearer`.
- `ApiKeyAuthentication` usa `request.tenant`, delega para `api_key_runtime_authentication` e retorna `ApiKeyPrincipal`.
- `HasApiKeyScope` exige `required_api_key_scope` explícito na view.
- `request.auth` preserva `rate_limit_key` para throttle futuro, mas nenhum rate limiter real roda neste corte.

Piloto público recomendado:

HTTP Request `GET /api/v1/catalog/products/`
→ Tenant Resolution por subdomínio/contexto
→ `ApiKeyAuthentication`
→ `HasApiKeyScope` com `required_api_key_scope = "read:catalog"`
→ query service de catálogo tenant-scoped
→ payload paginado de produtos ativos/publicados

Restrições do piloto:

- não aceitar `tenant_id` via query/body.
- não reutilizar `/ops/`.
- não expor pedidos, clientes, pagamentos ou PII.
- não abrir escrita programática.

Execução atual:

- `GET /api/v1/catalog/products/` está registrado em `config.urls` via `catalog.interfaces.public_api_urls`.
- `PublicCatalogProductsApiView` exige `ApiKeyAuthentication`, `HasApiKeyScope` e `required_api_key_scope = "read:catalog"`.
- `public_catalog_api_queries` lista apenas produtos persistidos `active` e `is_active=True`.
- o endpoint fica oculto quando `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED` está desligado.

Rate limit planejado para API keys:

HTTP Request público autenticado
→ `ApiKeyAuthentication`
→ `request.auth["rate_limit_key"]`
→ cálculo `tenant + api_key + endpoint`
→ cache fixed-window
→ se permitido: permission/view
→ se excedido: resposta `429`, header `Retry-After` e AuditLog `api_key.rate_limited`

Execução de rate limit atual:

- `ApiKeyRateLimitThrottle` está plugado apenas no endpoint público de catálogo.
- `api_key_rate_limit` usa cache Django com fixed-window.
- a chave de limite combina `rate_limit_key` e endpoint lógico.
- `GET /api/v1/catalog/products/` usa endpoint lógico `catalog.products.list`.
- limites são configuráveis por `API_KEYS_*_RATE_LIMIT`.

Observabilidade planejada para API keys públicas:

- `hubx_api_key_public_request_total` para requests por tenant/endpoint/result.
- `hubx_api_key_auth_failure_total` para falhas de autenticação por tenant/endpoint/motivo seguro.
- `hubx_api_key_rate_limited_total` para 429 por tenant/endpoint/prefixo seguro.
- `hubx_api_key_public_endpoint_enabled` para flag operacional do endpoint público.
- endpoint de métricas deve usar token de observabilidade, não API key pública.

Execução de métricas atual:

HTTP Request `/api-keys/metrics/public-endpoints/`
→ token `API_KEYS_OBSERVABILITY_TOKEN`
→ `api_key_public_endpoint_metrics.export_prometheus_metrics()`
→ Prometheus text format

- sucesso em `GET /api/v1/catalog/products/` incrementa `hubx_api_key_public_request_total{result="success"}`.
- falha de autenticação incrementa `hubx_api_key_auth_failure_total` e `hubx_api_key_public_request_total{result="auth_failed"}`.
- rate limit incrementa `hubx_api_key_rate_limited_total` e `hubx_api_key_public_request_total{result="rate_limited"}`.

Falhas relevantes:

- tenant ausente, prefixo inválido, hash inválido, chave revogada ou escopo insuficiente devem encerrar o fluxo antes da view.
- falhas podem gerar `api_key.auth_failed`, sem segredo claro, hash ou header completo.
- API key nunca redefine tenant do request.

Observações:

- estes comandos não alteram login, sessão, fatores ou settings.
- readiness bloqueado é evidência operacional, não rollback automático.
- plano de migração TOTP não move segredo nem atualiza `secret_reference`.
- execução de migração TOTP roda em dry-run por padrão e nunca imprime segredo.
- readiness de retirement recomenda corte de setting, mas não altera settings/env.
- execução de retirement captura evidência operacional, mas também não altera settings/env.
- provider health é read-only e não imprime segredo.
- métricas de provider MFA não expõem owner, factor, segredo ou reference path completo.
- closure de provider MFA não ativa observabilidade real nem altera ambiente.
- readiness de code retirement não remove código nem altera dados/settings.
- execution de code retirement muda o default seguro, mas não remove parsing local do resolver.
- sweep global não expõe owner/factor/segredo/reference path completo.
- parser removal review não remove código; apenas decide se a execution pode seguir.
- parser removal execution não altera dados, mas muda o comportamento do resolver para nunca devolver segredo local/plain.
- Vault/KMS provider review não chama cofre real; apenas prepara contrato e Go/No-Go para adapter.
- Vault/KMS adapter contract não implementa SDK nem muda settings; ele fixa a fronteira para a próxima execution.
- Vault/KMS skeleton execution usa provider configurável e read-only; não escreve segredo nem faz fallback automático para `env`.
- Vault/KMS readiness evidence apenas agrega sinais tenant-scoped e não ativa staging real.
- Vault/KMS staging canary review não executa login nem cria sessão; apenas prepara checklist operacional.
- Vault/KMS staging canary evidence não automatiza browser/login; apenas valida resultados declarados pelo operador.
- Vault/KMS real adapter contract não instala SDK nem chama provider real; apenas define a fronteira da próxima implementação.
- Vault/KMS real adapter skeleton usa branch mocável separado; ainda não instala SDK nem usa credenciais reais.
- Vault/KMS SDK dependency review não instala nem importa SDK real; apenas fixa o contrato para execução futura.
- Vault/KMS SDK adapter execution valida import lazy e branch SDK, mas ainda não chama endpoint externo real.
- Vault/KMS real endpoint review escolhe Hashicorp Vault como primeiro provider real, mas ainda não chama `hvac`.
- Hashicorp Vault real endpoint execution chama `hvac` apenas quando flag explícita está ativa e mantém output redigido.
- Hashicorp Vault staging smoke evidence agrega resultados manuais de staging e não cria sessão, fator ou secret.
- Vault/KMS production readiness consolida Go/No-Go, mas não ativa produção nem altera flags/env.
- Hashicorp Vault production gate define ativação operacional por tenant, mas não executa deploy/restart nem muda flags.
- Vault/KMS production activation evidence registra resultado pós-ativação declarado, mas não executa deploy/restart nem rollback.
- Hashicorp Vault post-activation monitoring classifica a janela, mas não executa rollback nem expansão de tenants.
- Vault/KMS production closure encerra a trilha do tenant canário, mas não executa rollback, não altera flags/env e não autoriza expansão global implícita.
- Hashicorp Vault tenant expansion review valida o plano de expansão, mas não ativa provider, não altera flags/env e exige evidence própria por target tenant.
- Hashicorp Vault tenant expansion evidence registra uma execução declarativa por target tenant, mas não altera flags/env nem libera próximo tenant sem monitoring próprio.
- Hashicorp Vault target post-expansion monitoring classifica o target, mas não executa rollback nem libera próxima expansão automaticamente.
- Hashicorp Vault next tenant expansion review decide cadência, mas não ativa próximo tenant nem pula review/evidence/monitoring do próximo ciclo.
- Hashicorp Vault expansion cadence closure consolida a cadência, mas não ativa tenant, não altera flags/env e não exporta evidência formal.
- Vault/KMS rotation runbook prepara a operação de rotação, mas não gera credencial, não atualiza secret/configuração e não executa rollback.
- Vault/KMS rotation evidence registra execução declarada, mas não gera/revoga credencial, não atualiza secret/configuração e não executa rollback.
- Vault/KMS post-rotation monitoring classifica estabilidade, mas não restaura credencial, não retoma expansão automaticamente e não executa rollback.
- Vault/KMS rotation closure encerra a rotação, mas não exporta evidência formal, não restaura credencial, não retoma expansão automaticamente e não executa rollback.
- owner MFA track closure consolida a trilha MFA, mas não ativa enforcement/provider/tenant, não altera flags/env e não reimprime evidência auditável.
- security ROI re-selection apenas recomenda próxima trilha; não implementa API keys, não altera autenticação e não grava novos eventos.
- API key governance foundation não cria API pública, não cria modelo/migration, não gera segredo e não autentica requests.
- API key model commands não autenticam requests e não persistem segredo claro.
- API key runtime authentication contract não implementa autenticação DRF, não cria endpoint público e não cria rate limiter real.
- API key runtime authentication skeleton não altera settings DRF, não cria permission class e não abre API pública.
- API key DRF authentication adapter review não implementa authentication class, não altera settings DRF e não cria endpoint público.
- API key DRF authentication adapter execution não altera settings globais, não cria endpoint público e não implementa throttle real.
- API key public endpoint pilot review não implementa endpoint, não cria URL pública e não altera catálogo.
- API key public catalog products endpoint execution cria apenas leitura de catálogo; não cria escrita, detalhe, pedidos, clientes, pagamentos ou throttle real.
- API key public endpoint rate limit review não implementa throttle, não altera settings globais e não aplica rate limit em HTML/storefront.
- API key public endpoint rate limit execution não altera settings globais de throttle e não cria quotas comerciais.
- API key public endpoint observability review não implementa métricas, endpoint Prometheus ou dashboard.
- API key public endpoint metrics execution não cria dashboard, alert rules ou quotas comerciais.
- API key public endpoint dashboard review não provisiona Grafana real, não cria JSON e não cria novas métricas; apenas fixa painéis mínimos, labels seguras e o handoff para execução.
- API key public endpoint dashboard execution cria apenas artefato Grafana versionado; o ciclo real continua Prometheus scrape do endpoint protegido → Grafana datasource `DS_PROMETHEUS` → painéis de leitura.
- API key public endpoint alert rules review não carrega YAML no Prometheus; apenas fixa regras mínimas para avaliar métricas já exportadas e orientar a próxima execution.
- API key public endpoint alert rules execution versiona YAML Prometheus; ativação real ainda depende de carregar o arquivo no Prometheus/Alertmanager do ambiente.
- API key public endpoint observability closure review verifica artefatos versionados e riscos residuais; não executa scrape real, não importa dashboard e não configura Alertmanager.
- API key public endpoint production rollout review não toca produção; ele fixa o ciclo operacional esperado: configurar token → validar endpoint → carregar scrape/dashboard/alertas → capturar evidência → manter rollback.
- API key public endpoint production activation evidence registra sinais sanitizados de ativação; não executa curl, não armazena token/header/API key e não altera Prometheus/Grafana/Alertmanager.
- API key public endpoint post-activation monitoring review avalia estabilidade após evidência produtiva; não altera thresholds, não expande endpoints e não executa rollback.
- API key public endpoint expansion review apenas seleciona o próximo contrato público; execução do endpoint deve acontecer em wave própria no módulo dono, mantendo tenant resolution → API key auth → permission/scope → rate limit → application query → métricas.
- API key public product detail endpoint contract review fixa o contrato para `GET /api/v1/catalog/products/<slug>/`; execução futura deve seguir tenant resolution → API key auth → `read:catalog` → rate limit `catalog.products.detail` → query catalog por slug ativo → métrica success.
- API key public product detail endpoint execution implementa esse ciclo em `catalog`: request por slug → tenant resolvido → API key `read:catalog` → throttle `catalog.products.detail` → query de produto ativo por tenant/slug → payload público → métrica success.
- API key public product detail endpoint observability review confirma que métricas/dashboard/alert rules existentes cobrem `catalog.products.detail` por label `endpoint`; não adiciona slug/SKU a métricas.
- API key public endpoint expansion closure fecha o escopo list/detail; não seleciona endpoint novo e mantém o próximo ciclo dependente de nova seleção ROI.
- API key governance closure fecha a trilha de modelo/runtime/DRF/endpoints/observabilidade; não altera request runtime e não abre novos endpoints.
- API key system ROI re-selection acontece fora do runtime HTTP; apenas recomenda a próxima frente e mantém qualquer futuro endpoint obrigado a passar por tenant resolution → API key auth → permission/scope → rate limit → application query → métricas.
- API key partner onboarding documentation review também acontece fora do runtime HTTP; documenta o ciclo existente de list/detail e exige exemplos seguros, mas não muda middleware, autenticação, query ou métricas.
- API key partner documentation execution review continua fora do runtime HTTP; valida pacote de entrega, suporte e evidência de smoke sem executar requests ou alterar feature flags.
- API key partner documentation publication evidence continua fora do runtime HTTP; registra entrega documental sanitizada e não executa smoke, autenticação, query, feature flag ou ativação de endpoint.
- API key partner onboarding closure continua fora do runtime HTTP; consolida a trilha documental e devolve a decisão para ROI sem alterar request lifecycle.
- API key post-onboarding ROI re-selection continua fora do runtime HTTP; apenas seleciona próxima trilha e mantém qualquer smoke futuro obrigado a usar tenant resolution → API key auth → scope → rate limit → query → métricas.
- API key partner activation smoke contract continua fora do runtime HTTP; apenas define que a execução futura deve usar tenant resolution → API key auth → `read:catalog` → rate limit → list/detail query → métricas.
- API key commercial quotas contract continua fora do runtime HTTP; define quota futura por tenant/key/endpoint/window, mas ainda não altera throttle, autenticação, query, resposta ou métricas em runtime.
- API key commercial quotas execution altera o runtime HTTP apenas no throttle opt-in de endpoints públicos: tenant resolution → API key auth → permission/scope → rate limit técnico → quota comercial ativa por tenant/key/endpoint/window → application query → métricas.
- se não existir quota ativa, o fluxo preserva o comportamento anterior.
- se quota ativa for excedida, a request é bloqueada com `429`, `Retry-After`, audit `api_key.quota_exceeded` e métrica `hubx_api_key_quota_exceeded_total`.
- a visibilidade admin de quotas roda em `/ops/api-keys/quotas/` como leitura tenant-scoped e não participa do fluxo público de catálogo.
- audit instrumentation expansion altera apenas commands explícitos já tenant-scoped:
  - aprovação de refund: tenant resolution/admin context → view ops → `payments.application.refund_approval_commands` → persistência → `audit_log_commands.record_event`
  - execução de refund: command/service interno → `payments.application.refund_execution_commands` → provider adapter → persistência → `audit_log_commands.record_event`
  - visibilidade de produto: admin context → `catalog.application.admin_product_commands` → persistência → `audit_log_commands.record_event`
- CRUD administrativo de produto segue: request `/ops/catalog/products/...` → tenant resolution → owner/admin context → view fina de `catalog.interfaces` → `catalog.application.admin_product_commands` → persistência em `Product` + `ProductVariant` padrão → `AuditLog` `product.created`, `product.updated` ou `product.deactivated` → redirect/render com erro.
- A desativação administrativa de produto substitui delete físico: `POST /ops/catalog/products/<slug>/actions/deactivate/` atualiza status/visibilidade e preserva histórico.
- API keys continuam registrando eventos em creation/revocation/quota/quota exceeded sem expor segredo/hash.
- a expansão não cria middleware de auditoria, não loga leituras e não altera responses públicas.
- platform tenant admin surface futura deve seguir: request `/ops/platform/tenants/` → autenticação owner/platform → RBAC platform permission → application service de `tenants` → persistência/audit quando houver write → response.
- essa surface não deve derivar autorização de `request.tenant`; o tenant alvo é dado operacional explícito e não contexto da loja atual.
- edição de `custom_domain` nessa surface continua cadastro contract-only e não altera o middleware de resolução HTTP.
- a execução read-only atual segue: request `/ops/platform/tenants/` → ops gate/RBAC quando habilitado → `tenants.application.platform_tenant_admin_queries` → template admin read-only.
- como não há write, a tela não registra `AuditLog` e não emite evento.
- o detalhe read-only segue o mesmo fluxo e resolve o tenant alvo por `tenant_slug` explícito, sem consultar dados tenant-owned de commerce.
- o create futuro deve seguir: request `/ops/platform/tenants/new/` → ops gate/RBAC platform → command service de `tenants` → validação de slug/subdomain/reservados → persistência de `Tenant` → `AuditLog` platform-scope explícito → redirect para detalhe.
- falhas de validação no create não devem criar owner, catálogo, billing, sessão, custom-domain resolver ou qualquer side effect em outros módulos.
- o command service atual de criação usa permissão `platform.tenants.manage` e reverte a transação se `AuditLog` platform-scope não for persistido.
- a surface HTTP de criação já implementa esse ciclo: GET renderiza formulário para roles com manage, POST delega ao command service, sucesso redireciona para detalhe e falhas retornam 400.
- state management futuro deve seguir: request `/ops/platform/tenants/<tenant_slug>/state/` → ops gate/RBAC platform → command service de `tenants` → atualização de `is_active` ou `maintenance_mode` → `AuditLog` platform-scope → redirect para detalhe.
- state management não deve alterar slug, subdomain, custom_domain, commerce, owners, billing, redirects, resolver HTTP ou notificações.
- o command service atual de state management já executa essa atualização transacionalmente e reverte se `AuditLog` platform-scope não persistir.
- a surface HTTP atual de state management implementa o POST fino, renderizando botões condicionais no detalhe e delegando todo write ao command service.
- custom domain update futuro deve seguir: request `/ops/platform/tenants/<tenant_slug>/custom-domain/` → ops gate/RBAC platform → command service de `tenants` → normalização/unicidade → persistência de `custom_domain` → `AuditLog` platform-scope → redirect para detalhe.
- custom domain update não deve ativar resolver HTTP, validar DNS, provisionar TLS, criar redirect ou publicar domínio como ativo.
- o command service atual de custom domain já normaliza, valida formato mínimo, bloqueia duplicidade, permite limpar o campo e reverte a transação se `AuditLog` platform-scope não for persistido.
- a surface HTTP atual de custom domain implementa esse POST fino no detalhe do tenant e delega todo write ao command service.
- o closure da trilha mantém o lifecycle restrito a ops internos: request `/ops/platform/tenants/...` → ops gate/RBAC → query/command service de `tenants` → ORM/AuditLog quando houver write → redirect/render, sem bootstrap automático, DNS/TLS, resolver custom-domain ou side effects em commerce.
- Owner Bootstrap futuro deve seguir: request `/ops/platform/tenants/<tenant_slug>/owner-bootstrap/` → ops gate/RBAC platform → command service orquestrador de `tenants` → service de `accounts` para OwnerUser/convite → `AuditLog` platform-scope → redirect para detalhe.
- Custom Domain Runtime Resolver futuro deve seguir: HTTP request → middleware → resolução por subdomínio preservada → quando habilitado, match exato por `custom_domain` de tenant ativo → sem fallback global → view; DNS/TLS seguem validações externas.
- Owner Bootstrap Command atual executa esse fluxo por service/CLI, ainda sem surface HTTP dedicada.
- Custom Domain Runtime Resolver atual executa esse fluxo no middleware somente quando `HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED=True`; com a flag desligada, `custom_domain` continua cadastro contract-only.
- Owner Bootstrap Admin Surface futura deve seguir: detalhe platform-only → action POST sem senha → command service de `tenants` → service de `accounts` → AuditLog → redirect para detalhe.
- Custom Domain Runtime Evidence futura deve capturar smoke flag off/on, tenant inativo, safe miss e rollback antes de ativação em staging/produção.
- Owner Bootstrap Admin Surface atual executa esse lifecycle via POST `/ops/platform/tenants/<tenant_slug>/owner-bootstrap/` e retorna ao detalhe.
- Custom Domain Runtime Activation Runbook atual apenas emite checklist/comandos; ativação real continua controlada por setting de ambiente e evidência externa.
- Owner Bootstrap Admin Surface Closure não adiciona novo runtime; apenas confirma form, POST, permissão, blocked state, audit e ausência de senha.
- Custom Domain Runtime Staging Evidence não altera middleware; apenas confirma smoke flag off/on, tenant inativo, safe miss e rollback antes de production gate.
- Owner Bootstrap Production Evidence não altera runtime; confirma tenant alvo, owner/user, senha inutilizável, auditorias e ausência de sessão automática.
- Custom Domain Runtime Production Gate não ativa produção; retorna GO/NO-GO para etapa posterior de activation evidence.
- Owner Bootstrap Production Closure não altera runtime; fecha a trilha após evidência produtiva e handoff.
- Custom Domain Runtime Production Activation Evidence confirma pós-ativação, smokes e rollback pronto; a mudança real de flag continua externa ao comando.
- Custom Domain Runtime Production Closure não altera runtime; confirma activation evidence, resolver source, rollback, monitoramento e handoff.
- Store Management Track Closure não adiciona request flow; consolida a trilha e retorna para re-seleção de ROI.
- System ROI Re-Selection continua fora do runtime HTTP; compõe a closure de Platform Store Management e recomenda a próxima trilha sem alterar tenant resolution, providers, flags, sessões ou dados de commerce.
- A recomendação atual favorece validação funcional de storefront/admin quando há regressão visual confirmada; a execução dessa validação deve ocorrer em trilha própria de smoke/browser/templates.
- System Validation Pass 2 executa GETs de leitura via `django.test.Client`: host tenant-scoped → middleware de tenant → views/templates públicas/admin → verificação de status e marcadores HTML.
- O smoke não cria sessão salvo quando `--owner-email` for explicitamente fornecido para reutilizar usuário existente; não executa POST, não altera dados e não chama providers.
- Platform Self-Service Tenant Onboarding segue: request `/ops/platform/onboarding/...` → tenant/owner context → RBAC platform → `tenants.application.tenant_onboarding_commands` → `TenantOnboarding` draft/step → audit platform-scope.
- A conclusão segue: onboarding ready → `platform_tenant_admin_commands.create_tenant(...)` → `subscription_commands.set_tenant_subscription(...)` → `platform_tenant_admin_commands.bootstrap_owner(...)` → audit completion → redirect para a jornada/loja criada.
- O fluxo não chama provider de billing, DNS/TLS, pagamentos de pedido, frete ou catálogo.
- Platform Owner Context permite que `/ops/platform/...` use o portal central `hubx.market`, resolvendo `request.owner_user` por e-mail autenticado e permissão `platform.tenants.view`.
- Home central segue: request `/` em host sem tenant → middleware não resolve `request.tenant` → `StorefrontHomeView` renderiza `portal_home_page.html` → navegação pública para login, planos e demo. Esse fluxo não lê catálogo, pedidos, clientes ou admin tenant-owned.
- Home tenant-owned segue: request `/` em host de loja → tenant resolution → `StorefrontHomeView` → leitura tenant-scoped de produtos em destaque → `tenants.application.storefront_branding_queries` compõe o hero institucional com campos `storefront_hero_*` e fallback visual do próprio tenant → template `home_page.html`. Esse fluxo não emite evento nem altera catálogo, pedidos, clientes ou pagamentos.
- Configuração de branding segue: request `/ops/branding/` em host de loja → tenant resolution → owner context/RBAC `/ops/` → `StorefrontBrandingSettingsView` → `tenants.application.storefront_branding_commands.update_storefront_hero(...)` → persistência de `Tenant.logo_url`, `Tenant.conversion_primary_color` e `Tenant.storefront_hero_*` → `AuditLog` tenant-scoped → redirect/render. O layout base expõe a cor validada como variáveis CSS sanitizadas para tokens de conversão. Esse fluxo não altera catálogo, pedidos, clientes, pagamentos nem dados platform-only.
- Demo público segue: request `/demo/` em host central → middleware sem tenant → `PublicDemoAccessView` consulta apenas `Tenant` ativo pelo subdomínio configurado em `HUBX_MARKET_DEMO_TENANT_SUBDOMAIN` → renderiza uma tela pública com dois caminhos de sessão direta para a loja demo: admin da loja e cliente da loja. Em requisição local por `localhost`, o host/porta da própria request prevalece para montar links `hubx-demo.localhost:<porta>/accounts/demo-session/?profile=...`. Ao clicar, a request já chega no host tenant-owned, o middleware resolve o tenant demo, `accounts.application.demo_session_login_commands` valida tenant/perfil/e-mail fixo e cria a sessão Django correspondente antes de redirecionar para `/ops/` ou `/`. Se o tenant ou perfil não for válido, retorna 404 seguro.
- Demo tenant-owned read-only segue: request em `hubx-demo.<root>` → `TenantSubdomainMiddleware` resolve o tenant → `DemoTenantReadOnlyMiddleware` marca `request.is_demo_read_only=True` e bloqueia `POST`, `PUT`, `PATCH` e `DELETE` fora de endpoints de sessão/login/logout → views GET renderizam a demo com logo/paleta Hubx, imagens raster realistas e aviso de somente leitura. O mesmo contrato impede mutações de carrinho, checkout, newsletter, reviews, endereços e admin da loja.
- Analytics de descoberta storefront também respeita o modo read-only: `StorefrontDiscoveryAnalyticsService` descarta eventos para o tenant demo oficial e não cria `StorefrontDiscoveryEventLog` durante navegação da demo.
- Login central em `hubx.market` direciona platform owner/admin para `/ops/platform/tenants/`, owner de loja única para `https?://{loja}.hubx.market/ops/` e owners multi-loja para `/accounts/select-store/`.
- Login central usa navegação pública de portal, planos e demo; login tenant-owned preserva navegação de loja, catálogo e pedidos.
- Login tenant-owned em `{loja}.hubx.market` continua respeitando `request.tenant` para storefront, customers e admin da loja.
- Platform owner/admin em runtime central exige `OwnerUser` ativo no tenant reservado `platform-system` (`HUBX_PLATFORM_TENANT_SLUG`); role `owner` em uma loja comum não concede contexto platform no portal central.
- Requests `/ops/platform/...` feitas em host tenant-owned são bloqueadas pelo gate; platform surfaces só rodam no host central.
- O smoke local `local_e2e_smoke` valida home central, planos, login central, redirect demo, login/redirect por perfil, menus contextuais, links GET locais, bloqueio de platform em host de loja, bloqueio read-only da demo e imagens raster do storefront.

---

# Boas práticas

- manter views simples
- mover lógica para application/domain
- emitir eventos para efeitos colaterais
- respeitar isolamento multi-tenant
- evitar acesso cruzado entre módulos

---

# Objetivo

Padronizar o fluxo interno do sistema para:

- previsibilidade arquitetural
- facilidade de manutenção
- integração com agentes de IA
