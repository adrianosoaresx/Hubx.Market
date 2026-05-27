# API Keys

## Responsabilidade
Gerenciar chaves para API pública futura.

## Entidades principais
- ApiKey

## Casos de uso
- criar chave
- revogar chave

## Regras de negócio
- chave pertence ao tenant
- segredo persistido apenas como hash
- valor claro só deve ser exibido no retorno da criação
- revogação não deleta histórico
- escopos são declarativos

## API Key Governance Foundation Review

- governança de API keys agora possui contrato mínimo antes de criar modelo real.
- query service:
  - `api_keys.application.api_key_governance_foundation_queries`
- comando:
  - `python manage.py api_key_governance_foundation --public-api-surface-confirmed --tenant-scoped-model-required --hashed-secret-storage-required --scoped-permissions-required --revocation-required --audit-events-required --last-used-tracking-required --rate-limit-required`
- requisitos mínimos:
  - `ApiKey` tenant-scoped;
  - segredo armazenado apenas como hash;
  - valor claro exibido somente na criação;
  - escopos declarativos;
  - revogação sem deletar histórico;
  - eventos auditáveis;
  - last-used tracking;
  - rate limit por chave/tenant.

### Escopo deliberado

- sem criar API pública nesta review.
- sem criar modelo/migration nesta review.
- sem gerar segredo real.
- sem autenticação DRF.
- sem UI admin.

## API Key Model Minimal Contract Execution

- o módulo `api_keys` agora possui modelo mínimo tenant-scoped e command service de criação/revogação.
- modelo:
  - `api_keys.models.ApiKey`
- command service:
  - `api_keys.application.api_key_commands`
- migration:
  - `api_keys.0001_initial`
- campos principais:
  - `tenant`;
  - `owner` opcional;
  - `name`;
  - `prefix`;
  - `key_hash`;
  - `scopes`;
  - `status`;
  - `created_at`, `updated_at`, `last_used_at`, `revoked_at`.
- eventos auditáveis:
  - `api_key.created`;
  - `api_key.revoked`.

### Regras

- criação exige `tenant_id` e nome.
- criação retorna o valor claro uma única vez no resultado do command service.
- persistência guarda apenas `key_hash`.
- revogação usa `tenant_id + key_id`.
- revogação muda status para `revoked` e preserva histórico.
- runtime authentication continua fora deste recorte.

### Escopo deliberado

- sem autenticação runtime.
- sem API pública.
- sem UI admin operacional.
- sem rate limiter real.
- sem registrar `last_used_at` em request real.

## API Key Runtime Authentication Contract Review

- o módulo `api_keys` agora possui contrato executável para autenticação runtime futura.
- query service:
  - `api_keys.application.api_key_runtime_authentication_contract_queries`
- comando:
  - `python manage.py api_key_runtime_authentication_contract --api-key-model-available --bearer-header-required --tenant-context-required --prefix-lookup-required --hash-verification-required --active-status-required --scope-enforcement-required --last-used-tracking-required --auth-failure-audit-required --rate-limit-boundary-required`
- próximos tracks:
  - `API Key Runtime Authentication Skeleton Execution`;
  - `API Key Public API Surface Contract Review`.

### Regras

- request deve enviar credencial somente via `Authorization: Bearer`.
- tenant vem do contexto resolvido no request, não da chave.
- lookup deve usar `tenant_id + prefix`.
- autenticação só passa se o segredo completo validar contra `key_hash`.
- chave precisa estar `active`.
- endpoint ou caso de uso precisa declarar escopo mínimo.
- sucesso deve atualizar `last_used_at`.
- falha relevante deve gerar `api_key.auth_failed` sem segredo, hash ou valor sensível.
- rate limit deve ser definido por tenant e prefixo antes de abrir API pública.

### Escopo deliberado

- sem implementar autenticação DRF nesta review.
- sem criar endpoint público.
- sem alterar modelo `ApiKey`.
- sem criar rate limiter real.
- sem expor segredo, hash ou material sensível em logs.

## API Key Runtime Authentication Skeleton Execution

- o módulo `api_keys` agora possui service runtime mínimo para autenticar uma credencial contra o modelo `ApiKey`.
- service:
  - `api_keys.application.api_key_runtime_authentication`
- contrato implementado:
  - parser de `Authorization: Bearer`;
  - extração de prefixo;
  - lookup por `tenant_id + prefix`;
  - validação de status `active`;
  - validação do segredo completo contra `key_hash`;
  - checagem de escopo mínimo opcional;
  - atualização de `last_used_at` em sucesso;
  - emissão de `api_key.auth_failed` em falhas relevantes;
  - retorno de `rate_limit_key` declarativo para boundary futura.

### Resultados

- `api-key-authenticated`;
- `api-key-auth-unavailable`;
- `api-key-auth-tenant-required`;
- `api-key-auth-invalid`;
- `api-key-auth-revoked`;
- `api-key-auth-scope-denied`.

### Regras

- tenant ausente bloqueia autenticação antes do lookup.
- chave de outro tenant não autentica e não atualiza `last_used_at`.
- prefixo sozinho nunca autentica sem hash válido do segredo completo.
- chave revogada não autentica.
- escopo insuficiente não autentica.
- logs e audit metadata não recebem segredo claro, `key_hash` ou header completo.

### Escopo deliberado

- sem plugar em `DEFAULT_AUTHENTICATION_CLASSES`.
- sem criar endpoint público.
- sem permission class DRF.
- sem rate limiter real.
- sem UI/admin de chaves.

## API Key DRF Authentication Adapter Review

- o módulo `api_keys` agora possui review executável para decidir o adapter DRF antes da implementação.
- query service:
  - `api_keys.application.api_key_drf_authentication_adapter_review_queries`
- comando:
  - `python manage.py api_key_drf_authentication_adapter_review --runtime-service-available --tenant-middleware-required --per-view-opt-in-required --global-drf-auth-forbidden --required-scope-mapping-required --safe-principal-required --permission-class-required --rate-limit-hook-required --failure-response-contract-required --no-public-endpoint-in-adapter`
- próximos tracks:
  - `API Key DRF Authentication Adapter Execution`;
  - `API Key Public Endpoint Pilot Review`.

### Decisões

- adapter DRF deve ficar em `api_keys.interfaces`.
- adapter deve delegar para `api_key_runtime_authentication`.
- ativação deve ser por view/surface explícita, não global.
- `DEFAULT_AUTHENTICATION_CLASSES` não deve receber API key neste estágio.
- cada view precisa declarar escopo mínimo ou permission dedicada.
- principal autenticado deve ser seguro: `tenant_id`, `api_key_id`, `prefix`, `scopes`; nunca segredo/hash/header.
- `rate_limit_key` deve ser preservada para throttle futuro.

### Escopo deliberado

- sem implementar authentication class nesta review.
- sem alterar settings DRF.
- sem criar endpoint público.
- sem criar permission class.
- sem criar throttle/rate limiter real.

## API Key DRF Authentication Adapter Execution

- o módulo `api_keys` agora possui adapter DRF mínimo, opt-in por view.
- adapter:
  - `api_keys.interfaces.authentication.ApiKeyAuthentication`
- permission:
  - `api_keys.interfaces.authentication.HasApiKeyScope`
- principal:
  - `api_keys.interfaces.authentication.ApiKeyPrincipal`

### Contrato implementado

- `ApiKeyAuthentication` lê apenas `Authorization: Bearer`.
- autenticação delega para `api_key_runtime_authentication`.
- tenant é lido de `request.tenant`.
- sucesso retorna `ApiKeyPrincipal` e `request.auth` seguro.
- `request.auth` contém `api_key_id`, `tenant_id`, `prefix`, `scopes` e `rate_limit_key`.
- `HasApiKeyScope` exige `required_api_key_scope` explícito na view.
- views sem escopo explícito são negadas.
- credencial ausente ou inválida não abre fallback programático.

### Regras

- adapter não foi adicionado a `DEFAULT_AUTHENTICATION_CLASSES`.
- uso deve ser declarado por view com `authentication_classes = (ApiKeyAuthentication,)`.
- permissão deve ser declarada por view com `permission_classes = (HasApiKeyScope,)`.
- view deve declarar `required_api_key_scope`.
- principal não expõe segredo, `key_hash` ou header completo.

### Escopo deliberado

- sem criar endpoint público.
- sem alterar settings DRF.
- sem throttle/rate limiter real.
- sem catálogo de escopos avançado.
- sem UI/admin operacional de API keys.

## API Key Public Endpoint Pilot Review

- o módulo `api_keys` agora possui review executável para escolher o primeiro endpoint público piloto.
- query service:
  - `api_keys.application.api_key_public_endpoint_pilot_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_pilot_review --drf-adapter-available --pilot-endpoint-read-only --tenant-context-required --explicit-scope-required --rate-limit-plan-required --safe-payload-required --no-pii-required --no-admin-ops-reuse-required --versioned-url-required --rollout-flag-required`

### Piloto recomendado

- módulo: `catalog`;
- endpoint: `GET /api/v1/catalog/products/`;
- escopo: `read:catalog`;
- payload: lista paginada de produtos ativos/publicados com campos seguros.

### Decisões

- primeiro piloto deve ser read-only.
- catálogo é melhor candidato que pedidos/clientes/pagamentos por reduzir risco de PII e efeitos colaterais.
- rota pública deve ser versionada e separada de `/ops/`.
- endpoint não deve aceitar `tenant_id` via query/body; tenant vem do request.
- view futura deve usar `ApiKeyAuthentication`, `HasApiKeyScope` e `required_api_key_scope = "read:catalog"`.
- piloto deve nascer atrás de flag/config antes de produção real.
- `rate_limit_key` deve ser preservada e o plano de rate-limit deve existir antes de rollout amplo.

### Escopo deliberado

- sem implementar endpoint nesta review.
- sem expor pedidos, clientes, pagamentos ou dados pessoais.
- sem reutilizar rotas `/ops/`.
- sem aceitar escrita programática.
- sem aceitar tenant arbitrário por query/body.

## API Key Public Catalog Products Endpoint Execution

- o primeiro endpoint público por API key foi implementado como piloto controlado.
- endpoint:
  - `GET /api/v1/catalog/products/`
- módulo funcional:
  - `catalog`
- query service:
  - `catalog.application.public_catalog_api_queries`
- view:
  - `catalog.interfaces.public_api_views.PublicCatalogProductsApiView`
- URL:
  - `catalog.interfaces.public_api_urls`

### Contrato implementado

- endpoint exige `ApiKeyAuthentication`.
- endpoint exige `HasApiKeyScope`.
- escopo obrigatório: `read:catalog`.
- tenant é resolvido por `request.tenant`.
- endpoint não aceita `tenant_id` por query/body.
- payload lista apenas produtos persistidos, ativos e publicados do tenant atual.
- não há fallback para fixtures de storefront/admin.
- rota nasce atrás de `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED`.
- `page_size` é limitado a 50.

### Payload seguro

- inclui `id`, `slug`, `name`, `brand`, `category`, `is_featured`, `status`, `price`, `compare_price`, `availability`, `primary_image` e `updated_at`.
- não inclui dados de clientes, pedidos, pagamentos, estoque bruto, `tenant_id`, segredo, hash ou header.

### Escopo deliberado

- sem endpoint de detalhe.
- sem escrita programática.
- sem API de pedidos/clientes/pagamentos.
- sem throttle/rate limiter real.
- sem catálogo avançado de scopes.

## API Key Public Endpoint Rate Limit Review

- o módulo `api_keys` agora possui review executável para rate limit de endpoints públicos.
- query service:
  - `api_keys.application.api_key_public_endpoint_rate_limit_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_rate_limit_review --public-endpoint-active --rate-limit-key-available --per-tenant-and-key-required --cache-backend-required --fixed-window-acceptable --default-limit-config-required --endpoint-override-config-required --retry-after-required --audit-event-required --fail-closed-required`

### Política recomendada

- algoritmo: `fixed-window`;
- escopo: `tenant + api_key + endpoint`;
- limite inicial: 120 requests;
- janela inicial: 60 segundos;
- evento de auditoria: `api_key.rate_limited`.

### Decisões

- rate limit deve usar a `rate_limit_key` emitida pelo adapter.
- cache Django é aceitável para primeira versão.
- 429 deve incluir `Retry-After`.
- estouro de limite deve registrar `api_key.rate_limited`.
- payload/log/audit não podem conter segredo, hash ou header.
- integração deve ser opt-in por endpoint/permission/throttle, não global.

### Escopo deliberado

- sem implementar throttle nesta review.
- sem alterar `DEFAULT_THROTTLE_CLASSES`.
- sem rate limit por IP como substituto de tenant+key.
- sem aplicar em HTML/storefront.
- sem plano pago/quotas comerciais.

## API Key Public Endpoint Rate Limit Execution

- o módulo `api_keys` agora possui rate limit real para endpoints públicos opt-in.
- service:
  - `api_keys.application.api_key_rate_limit`
- throttle:
  - `api_keys.interfaces.throttling.ApiKeyRateLimitThrottle`
- primeiro uso:
  - `GET /api/v1/catalog/products/`

### Contrato implementado

- algoritmo: `fixed-window`;
- identidade: `rate_limit_key + endpoint`;
- endpoint atual: `catalog.products.list`;
- resposta excedida: `429`;
- header: `Retry-After`;
- evento: `api_key.rate_limited`;
- integração: opt-in por `throttle_classes`, sem alterar `DEFAULT_THROTTLE_CLASSES`.

### Configuração

- `API_KEYS_RATE_LIMIT_DEFAULT_LIMIT`;
- `API_KEYS_RATE_LIMIT_DEFAULT_WINDOW_SECONDS`;
- `API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT`;
- `API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT_WINDOW_SECONDS`.

### Regras

- limite é isolado por tenant/API key/endpoint.
- estouro registra tenant, key_id, prefix, endpoint, count, limit, janela e retry-after.
- audit/log não recebem segredo, hash ou header.
- falha de identidade/cache fecha o acesso em vez de liberar tráfego.

### Escopo deliberado

- sem alterar throttle global do DRF.
- sem rate limit por IP como política primária.
- sem quotas comerciais ou planos pagos.
- sem aplicar em storefront HTML.

## API Key Public Endpoint Observability Review

- o módulo `api_keys` agora possui review executável para observabilidade do endpoint público.
- query service:
  - `api_keys.application.api_key_public_endpoint_observability_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_observability_review --public-endpoint-active --auth-events-available --rate-limit-events-available --prometheus-metrics-required --endpoint-labels-required --tenant-labels-required --key-prefix-labels-allowed --no-secret-material-required --alert-rules-required --dashboard-required`

### Métricas recomendadas

- `hubx_api_key_public_request_total`;
- `hubx_api_key_auth_failure_total`;
- `hubx_api_key_rate_limited_total`;
- `hubx_api_key_public_endpoint_enabled`.

### Decisões

- métricas devem usar labels `tenant_id`, `endpoint`, `result` e opcionalmente `prefix`.
- observabilidade não pode exportar segredo, hash, header ou valor claro.
- endpoint de métricas deve ser protegido por token de observabilidade, não por API key pública.
- alertas mínimos devem cobrir picos de `auth_failed`, picos de `rate_limited` e endpoint público desabilitado inesperadamente.
- dashboard mínimo deve cobrir requests, 401/403/429, rate limit e uso por tenant/endpoint.

### Escopo deliberado

- sem implementar métricas nesta review.
- sem criar endpoint Prometheus.
- sem criar dashboard Grafana.
- sem exportar segredo, hash, header ou valor claro de API key.
- sem billing/quotas comerciais.

## API Key Public Endpoint Metrics Execution

- o módulo `api_keys` agora exporta métricas Prometheus mínimas para endpoints públicos por API key.
- service:
  - `api_keys.application.api_key_public_endpoint_metrics`
- endpoint:
  - `GET /api-keys/metrics/public-endpoints/`
- token:
  - `API_KEYS_OBSERVABILITY_TOKEN`

### Métricas implementadas

- `hubx_api_key_public_request_total`;
- `hubx_api_key_auth_failure_total`;
- `hubx_api_key_rate_limited_total`;
- `hubx_api_key_public_endpoint_enabled`.

### Regras

- endpoint de métricas aceita `X-Hubx-Observability-Token` ou `Authorization: Bearer <observability-token>`.
- API key pública não autentica o endpoint de métricas.
- sucesso do endpoint de catálogo registra `result="success"`.
- falhas de autenticação registram `auth_failed`.
- rate limit registra `rate_limited`.
- métricas não exportam segredo, hash, header ou valor claro da chave.

### Escopo deliberado

- sem dashboard Grafana.
- sem alert rules Prometheus.
- sem billing/quotas comerciais.
- sem métricas por endpoint HTML/storefront.

## API Key Public Endpoint Dashboard Review

- o módulo `api_keys` agora possui review executável para dashboard Grafana dos endpoints públicos.
- query service:
  - `api_keys.application.api_key_public_endpoint_dashboard_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_dashboard_review --metrics-endpoint-available --observability-token-required --requests-panel-required --auth-failure-panel-required --rate-limit-panel-required --endpoint-enabled-panel-required --tenant-endpoint-filters-required --low-cardinality-required --no-sensitive-labels-required --alert-rules-plan-required`

### Dashboard recomendado

- título: `Hubx API Key Public Endpoints`;
- slug: `api-key-public-endpoints`;
- datasource: `DS_PROMETHEUS`;
- owner: `api_keys`.

### Painéis mínimos

- taxa de requests por `tenant_id`, `endpoint` e `result`;
- taxa de falhas de autenticação por `tenant_id`, `endpoint` e `reason`;
- taxa de rate limit por `tenant_id`, `endpoint` e `prefix`;
- estado operacional por endpoint via `hubx_api_key_public_endpoint_enabled`;
- top tenants por volume de requests públicos.

### Decisões

- dashboard deve consumir somente métricas Prometheus já exportadas por `api_keys`.
- scrape e datasource continuam protegidos por token de observabilidade; API key pública não autentica dashboard/scrape.
- labels permitidas são operacionais e de baixa cardinalidade: `tenant_id`, `endpoint`, `result`, `reason` e `prefix`.
- segredo, hash, header ou valor claro da API key continuam proibidos.
- dashboard não substitui alert rules para `auth_failed`, `rate_limited` e endpoint desabilitado.

### Escopo deliberado

- sem criar dashboard JSON nesta review.
- sem provisionar Grafana real nesta review.
- sem criar alert rules Prometheus nesta review.
- sem criar métricas novas nesta review.
- sem billing/quotas comerciais.

## API Key Public Endpoint Dashboard Execution

- o dashboard inicial de Grafana para endpoints públicos por API key foi versionado em:
  - `infra/observability/grafana/api-key-public-endpoints-dashboard.json`

### Painéis implementados

- `Public request rate by tenant / endpoint / result`;
- `Authentication failures by tenant / endpoint / reason`;
- `Rate limited requests by tenant / endpoint / prefix`;
- `Public endpoint enabled`;
- `Top tenants by public request volume (1h)`.

### Variáveis

- `DS_PROMETHEUS`;
- `tenant_id`;
- `endpoint`.

### Regras

- dashboard consome apenas métricas já expostas por `/api-keys/metrics/public-endpoints/`.
- labels seguem o contrato de baixa cardinalidade: tenant, endpoint, result, reason e prefix.
- artefato não contém segredo, hash, header ou valor claro de API key.
- dashboard não substitui alert rules; alertas continuam como próxima trilha própria.

### Escopo deliberado

- sem provisionar Grafana real.
- sem criar alert rules Prometheus.
- sem criar métricas novas.
- sem billing/quotas comerciais.

## API Key Public Endpoint Alert Rules Review

- o módulo `api_keys` agora possui review executável para alert rules Prometheus dos endpoints públicos.
- query service:
  - `api_keys.application.api_key_public_endpoint_alert_rules_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_alert_rules_review --metrics-endpoint-available --dashboard-available --auth-failure-alert-required --rate-limit-alert-required --endpoint-disabled-alert-required --tenant-endpoint-labels-required --low-cardinality-required --runbook-annotations-required --no-sensitive-labels-required --warning-first-required`

### Alertas recomendados

- `HubxApiKeyPublicAuthFailuresHigh`;
- `HubxApiKeyPublicRateLimitedHigh`;
- `HubxApiKeyPublicEndpointDisabled`.

### Decisões

- alert rules devem vir depois de métricas e dashboard mínimos já versionados.
- cobertura mínima inclui auth failure, rate limit e endpoint público desabilitado.
- primeiro pacote deve começar com `severity: warning` para reduzir ruído de rollout.
- labels devem apontar tenant/endpoint sem segredo, hash, header ou valor claro de API key.
- annotations devem orientar triagem por dashboard, scrape e audit events.

### Escopo deliberado

- sem criar YAML de alert rules nesta review.
- sem configurar Alertmanager.
- sem provisionar Prometheus real.
- sem criar métricas novas.
- sem alertas por API key completa ou hash.
- sem billing/quotas comerciais.

## API Key Public Endpoint Alert Rules Execution

- as alert rules iniciais de Prometheus para endpoints públicos por API key foram versionadas em:
  - `infra/observability/prometheus/api-keys-alert-rules.yml`

### Alertas implementados

- `HubxApiKeyPublicAuthFailuresHigh`;
- `HubxApiKeyPublicRateLimitedHigh`;
- `HubxApiKeyPublicEndpointDisabled`.

### Regras

- todos os alertas usam `severity: warning` neste primeiro pacote.
- `HubxApiKeyPublicAuthFailuresHigh` avalia aumento de `hubx_api_key_auth_failure_total`.
- `HubxApiKeyPublicRateLimitedHigh` avalia aumento de `hubx_api_key_rate_limited_total`.
- `HubxApiKeyPublicEndpointDisabled` avalia `hubx_api_key_public_endpoint_enabled == 0`.
- annotations apontam triagem via dashboard, scrape, flags e audit events, sem solicitar segredo/hash/header.

### Escopo deliberado

- sem configurar Alertmanager.
- sem provisionar Prometheus real.
- sem criar métricas novas.
- sem alertas por API key completa ou hash.
- sem billing/quotas comerciais.

## API Key Public Endpoint Observability Closure Review

- o módulo `api_keys` agora possui closure executável para a trilha de observabilidade pública.
- query service:
  - `api_keys.application.api_key_public_endpoint_observability_closure_queries`
- comando:
  - `python manage.py api_key_public_endpoint_observability_closure --rollout-ready`

### Artefatos verificados

- metrics service;
- endpoint Prometheus protegido;
- dashboard Grafana versionado;
- alert rules Prometheus versionadas;
- runbook de observabilidade.

### Decisões

- métricas, dashboard e alert rules estão versionados para endpoints públicos por API key.
- segredo, hash, header e valor claro de API key permanecem proibidos em observabilidade.
- ativação real de Prometheus/Grafana/Alertmanager continua decisão de ambiente.
- closure só é `ready` quando `--rollout-ready` confirma aceite operacional para carregar scrape/dashboard/alertas.

### Riscos residuais

- thresholds ainda precisam ser calibrados com tráfego real.
- datasource `DS_PROMETHEUS` precisa existir no Grafana real.
- scrape Prometheus real ainda precisa ser ativado por ambiente.
- roteamento Alertmanager real ainda precisa ser configurado por ambiente.
- novos endpoints públicos precisam aderir explicitamente às mesmas métricas e labels.

## API Key Public Endpoint Production Rollout Review

- o módulo `api_keys` agora possui review executável para rollout produtivo da observabilidade pública.
- query service:
  - `api_keys.application.api_key_public_endpoint_production_rollout_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_production_rollout_review --observability-closure-ready --production-token-configured --prometheus-scrape-planned --dashboard-import-planned --alert-rules-load-planned --smoke-metrics-planned --rollback-plan-available --evidence-capture-required --owner-approval-required --no-secret-exposure-required`

### Checklist mínimo

- closure de observabilidade pronta;
- `API_KEYS_OBSERVABILITY_TOKEN` configurado no ambiente;
- scrape Prometheus planejado;
- dashboard Grafana planejado;
- alert rules planejadas;
- smoke de métricas planejado;
- rollback disponível;
- captura de evidência obrigatória;
- aceite operacional explícito;
- sem exposição de segredo/hash/header/API key em claro.

### Runbook resumido

- configurar `API_KEYS_OBSERVABILITY_TOKEN`;
- validar endpoint de métricas sem token retornando bloqueio;
- validar scrape com token retornando Prometheus text format;
- carregar scrape no Prometheus;
- importar dashboard Grafana com `DS_PROMETHEUS`;
- carregar alert rules como `warning`;
- capturar evidências sanitizadas.

### Rollback resumido

- remover scrape job de API keys públicas;
- desabilitar alert rules `HubxApiKeyPublic*`;
- pausar/remover dashboard importado;
- rotacionar `API_KEYS_OBSERVABILITY_TOKEN` em caso de suspeita de exposição;
- desabilitar flag pública se o incidente estiver no tráfego externo.

### Escopo deliberado

- sem ativar produção nesta review.
- sem executar curl contra ambiente real.
- sem criar token ou segredo real.
- sem alterar Prometheus/Grafana/Alertmanager reais.
- sem billing/quotas comerciais.

## API Key Public Endpoint Production Activation Evidence

- o módulo `api_keys` agora possui command para registrar evidência sanitizada de ativação produtiva.
- query service:
  - `api_keys.application.api_key_public_endpoint_production_activation_evidence_queries`
- comando:
  - `python manage.py api_key_public_endpoint_production_activation_evidence --environment=production --evidence-reference=<ref-sanitizada> --rollout-review-ready --token-redacted --metrics-endpoint-reachable --metrics-payload-valid --prometheus-scrape-active --dashboard-imported --alert-rules-loaded --endpoint-enabled-metric-present --request-metric-present --auth-failure-metric-present --rate-limit-metric-present --rollback-rehearsed`

### Evidência mínima

- ambiente `production`;
- review de rollout pronta;
- token redigido;
- endpoint de métricas alcançável;
- payload Prometheus válido;
- scrape Prometheus ativo;
- dashboard importado;
- alert rules carregadas;
- quatro métricas públicas presentes;
- rollback ensaiado ou confirmado;
- referência externa sanitizada.

### Regras

- command não executa chamada real.
- `evidence-reference` é descartada se parecer conter token, segredo, hash, header ou API key em claro.
- saída imprime apenas sinais booleanos, decisões, requisitos, blockers e próximos tracks.
- evidência produtiva pronta aponta para monitoramento pós-ativação.

### Escopo deliberado

- sem armazenar token ou header de observabilidade.
- sem armazenar API key pública, hash ou segredo.
- sem alterar Prometheus/Grafana/Alertmanager.
- sem calibrar thresholds produtivos.

## API Key Public Endpoint Post-Activation Monitoring Review

- o módulo `api_keys` agora possui review executável para monitoramento pós-ativação.
- query service:
  - `api_keys.application.api_key_public_endpoint_post_activation_monitoring_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_post_activation_monitoring_review --activation-evidence-ready --monitoring-window-observed --dashboard-reviewed --auth-failure-rate-acceptable --rate-limit-rate-acceptable --endpoint-enabled-stable --alert-noise-acceptable --threshold-tuning-needed-logged --rollback-not-required --expansion-decision-deferred --no-sensitive-data-observed`

### Checks mínimos

- evidência produtiva pronta;
- janela inicial observada;
- dashboard revisado;
- auth failures aceitáveis;
- rate limit aceitável;
- endpoint enabled estável;
- ruído de alertas aceitável;
- necessidade de tuning registrada;
- rollback não exigido;
- expansão adiada para decisão própria;
- nenhuma exposição sensível observada.

### Decisões

- pós-ativação só é `ready` quando tráfego, alertas e dashboard estão estáveis.
- alertas `warning` podem exigir tuning, mas tuning real fica fora desta review.
- rollback deve permanecer disponível, mas não exigido.
- expansão de novos endpoints públicos deve ser trilha separada após estabilização.

### Escopo deliberado

- sem alterar thresholds.
- sem expandir endpoints públicos.
- sem alterar token ou scrape real.
- sem billing/quotas comerciais.
- sem armazenar evidência com segredo, hash, header ou API key em claro.

## API Key Public Endpoint Expansion Review

- o módulo `api_keys` agora possui review executável para decidir o próximo endpoint público.
- query service:
  - `api_keys.application.api_key_public_endpoint_expansion_review_queries`
- comando:
  - `python manage.py api_key_public_endpoint_expansion_review --post-activation-monitoring-ready --candidate-endpoint-identified --read-only-required --tenant-context-required --explicit-scope-required --rate-limit-required --observability-required --payload-contract-required --no-pii-required --no-cross-module-leak-required --rollout-flag-required --expansion-deferred-until-contract`

### Candidato recomendado

- endpoint: `GET /api/v1/catalog/products/<slug>/`;
- módulo dono: `catalog`;
- escopo: `read:catalog`;
- motivo: detalhe público de produto reaproveita o domínio já exposto no piloto sem abrir pedidos, clientes ou pagamentos.

### Regras

- expansão só começa após monitoramento pós-ativação estável.
- novo endpoint deve ser read-only, tenant-scoped e protegido por escopo explícito.
- rate limit, métricas e flag de rollout devem nascer junto com qualquer endpoint público novo.
- payload não deve expor PII, estoque bruto, custo, margem, tenant_id ou dados de pedidos/clientes/pagamentos.
- execução fica para wave própria de contrato do endpoint de detalhe.

### Escopo deliberado

- sem implementar endpoint nesta review.
- sem abrir pedidos, clientes, pagamentos ou operações admin.
- sem criar escopo amplo como `read:*`.
- sem billing/quotas comerciais.

## API Key Public Product Detail Endpoint Contract Review

- o módulo `api_keys` agora possui review executável para o contrato do endpoint público de detalhe de produto.
- query service:
  - `api_keys.application.api_key_public_product_detail_endpoint_contract_review_queries`
- comando:
  - `python manage.py api_key_public_product_detail_endpoint_contract_review --expansion-review-ready --catalog-owner-confirmed --slug-lookup-required --tenant-scope-required --active-product-only-required --read-catalog-scope-required --safe-payload-required --public-variant-summary-required --rate-limit-endpoint-required --metrics-endpoint-label-required --rollout-flag-required --no-pii-or-stock-raw-required`

### Contrato recomendado

- método: `GET`;
- path: `/api/v1/catalog/products/<slug>/`;
- módulo dono: `catalog`;
- escopo: `read:catalog`;
- rate limit endpoint: `catalog.products.detail`;
- flag: `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`.

### Regras

- lookup deve ser por slug público dentro do tenant atual.
- query deve filtrar tenant, `status=ACTIVE` e `is_active=True`.
- endpoint deve usar `ApiKeyAuthentication`, `HasApiKeyScope` e `ApiKeyRateLimitThrottle`.
- payload pode retornar dados públicos de PDP, imagens públicas e resumo seguro de variantes.
- payload não deve expor estoque bruto, custo, margem, tenant_id, PII, pedidos, clientes ou pagamentos.
- sucesso deve registrar métrica com endpoint label `catalog.products.detail`.

### Escopo deliberado

- sem implementar endpoint nesta review.
- sem abrir carrinho, checkout, pedidos, clientes ou pagamentos.
- sem criar escrita pública ou admin API.
- sem criar escopo diferente de `read:catalog`.

## API Key Public Product Detail Endpoint Execution

- o endpoint público de detalhe de produto por API key foi implementado no módulo `catalog`.
- rota:
  - `GET /api/v1/catalog/products/<slug>/`
- query:
  - `catalog.application.public_catalog_api_queries.get_product_detail`
- view:
  - `catalog.interfaces.public_api_views.PublicCatalogProductDetailApiView`

### Contrato implementado

- autenticação por `ApiKeyAuthentication`;
- permissão por `HasApiKeyScope`;
- escopo obrigatório `read:catalog`;
- throttle `ApiKeyRateLimitThrottle`;
- endpoint label `catalog.products.detail`;
- flag `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`;
- settings de rate limit:
  - `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT`;
  - `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_RATE_LIMIT_WINDOW_SECONDS`.

### Payload

- retorna somente produto ativo do tenant atual.
- inclui campos públicos de PDP, imagens e resumo seguro de variantes.
- variantes expõem `sku`, preço, compare price, disponibilidade e default.
- não expõe estoque bruto, reserved stock, tenant_id, PII, custo ou margem.

### Observabilidade

- sucesso registra `hubx_api_key_public_request_total` com endpoint `catalog.products.detail`.
- `hubx_api_key_public_endpoint_enabled` agora expõe `catalog.products.detail`.
- rate limit e auth failures reutilizam o pipeline existente de `api_keys`.

### Escopo deliberado

- sem carrinho, checkout, pedidos, clientes ou pagamentos.
- sem escrita pública.
- sem admin API.
- sem billing/quotas comerciais.

## API Key Public Product Detail Endpoint Observability Review

- o módulo `api_keys` agora possui review executável para observabilidade do detalhe público de produto.
- query service:
  - `api_keys.application.api_key_public_product_detail_observability_review_queries`
- comando:
  - `python manage.py api_key_public_product_detail_observability_review --detail-endpoint-executed --metrics-endpoint-label-present --enabled-gauge-present --dashboard-endpoint-filter-covers-detail --alert-rules-endpoint-label-covers-detail --rate-limit-metrics-reused --auth-failure-metrics-reused --no-new-dashboard-required --no-new-alert-rules-required --no-sensitive-labels-required`

### Decisão

- a observabilidade existente cobre `catalog.products.detail`.
- dashboard atual usa filtro por `endpoint`, então cobre listagem e detalhe sem JSON novo.
- alert rules atuais agregam por `endpoint`, então cobrem detalhe sem YAML novo.
- `hubx_api_key_public_endpoint_enabled` já expõe `catalog.products.detail`.
- sucesso, auth failure e rate limit reutilizam as métricas públicas existentes.

### Regras

- não adicionar labels por slug ou SKU.
- não expor token, hash, header ou API key em claro.
- não criar dashboard dedicado antes de volume ou necessidade operacional real.
- não alterar thresholds nesta review.

### Escopo deliberado

- sem dashboard Grafana novo.
- sem alert rules Prometheus novas.
- sem expansão para novos endpoints.

## API Key Public Endpoint Expansion Closure Review

- o módulo `api_keys` agora possui closure executável para a expansão inicial de endpoints públicos.
- query service:
  - `api_keys.application.api_key_public_endpoint_expansion_closure_queries`
- comando:
  - `python manage.py api_key_public_endpoint_expansion_closure --list-endpoint-ready --detail-endpoint-ready --observability-ready --no-additional-endpoint-selected`

### Escopo fechado

- `GET /api/v1/catalog/products/`;
- `GET /api/v1/catalog/products/<slug>/`;
- escopo `read:catalog`;
- endpoint labels `catalog.products.list` e `catalog.products.detail`.

### Decisões

- listagem permanece o piloto público read-only tenant-scoped.
- detalhe por slug está implementado em `catalog` com `read:catalog`.
- dashboard e alert rules cobrem list/detail por label `endpoint`.
- nenhum novo endpoint público deve ser aberto antes de nova seleção ROI.

### Riscos residuais

- thresholds de alertas ainda dependem de tráfego real.
- novos endpoints devem repetir explicitamente tenant-scope, escopo, rate limit e métricas.
- mudanças futuras em `Product`/`ProductVariant` precisam preservar payload público seguro.
- billing/quotas comerciais continuam fora da trilha atual.

## API Key Governance Closure Review

- o módulo `api_keys` agora possui closure executável para a trilha de governança/API pública.
- query service:
  - `api_keys.application.api_key_governance_closure_queries`
- comando:
  - `python manage.py api_key_governance_closure --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed`

### Escopo fechado

- modelo `ApiKey`;
- command service de criação/revogação/hash/prefix/escopos;
- runtime authentication;
- DRF authentication/permission/throttle;
- `GET /api/v1/catalog/products/`;
- `GET /api/v1/catalog/products/<slug>/`;
- endpoint Prometheus;
- dashboard Grafana;
- alert rules Prometheus.

### Decisões

- governança mínima de API keys está pronta para endpoints públicos read-only de catálogo.
- endpoints públicos fechados neste ciclo são listagem e detalhe de produto.
- observabilidade cobre endpoints por label `endpoint`.
- billing/quotas comerciais permanecem diferidos.
- novos endpoints públicos exigem nova seleção ROI e contrato próprio.

### Riscos residuais

- billing/quotas comerciais ainda não existem.
- thresholds de alertas precisam de calibração com tráfego real.
- rotação operacional de API keys pode ganhar surface admin mais rica.
- documentação de parceiros externos ainda pode exigir exemplos versionados de payload.

## System ROI Re-Selection Review

- o módulo `api_keys` agora possui review executável para re-selecionar ROI sistêmico após a closure de governança.
- query service:
  - `api_keys.application.api_key_system_roi_reselection_queries`
- comando:
  - `python manage.py api_key_system_roi_reselection --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-missing --partner-onboarding-requested`

### Decisão recomendada

- próxima abordagem: **API Key Partner Onboarding Documentation Review**.
- motivo: endpoints públicos list/detail já existem, mas o maior gap de ROI é tornar o contrato consumível por parceiros sem abrir novo endpoint, billing ou quota comercial.

### Candidatos reavaliados

- partner onboarding docs: recomendado quando documentação/versionamento de payload está ausente e há demanda de integração.
- quotas comerciais: diferido até existir pressão explícita de billing/plano/abuso comercial.
- expansão de endpoint público: diferida até demanda concreta de integração.
- admin management UX: útil, mas não bloqueia o consumo inicial do contrato.
- production incident hardening: deve furar fila apenas com pressão real de incidente/ativação.

### Fora de escopo

- criar novo endpoint público.
- criar cobrança, quota comercial ou plano.
- alterar autenticação runtime.
- expor segredo, hash ou material sensível em comando/documentação.

## API Key Partner Onboarding Documentation Review

- o módulo `api_keys` agora possui review executável para validar a documentação mínima de onboarding de parceiros.
- query service:
  - `api_keys.application.api_key_partner_onboarding_documentation_review_queries`
- comando:
  - `python manage.py api_key_partner_onboarding_documentation_review --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required`
- artefato:
  - `docs/api/public-catalog-partner-onboarding.md`

### Escopo fechado

- documentação versionada para parceiros.
- endpoints `GET /api/v1/catalog/products/` e `GET /api/v1/catalog/products/<slug>/`.
- escopo `read:catalog`.
- placeholder seguro de autenticação.
- checklist de ativação.
- contrato de erros.
- notas de rate limit e observabilidade.

### Decisões

- onboarding deve productizar a API pública existente antes de abrir novos endpoints.
- exemplos usam apenas payload público e placeholder.
- documentação não cria billing, quotas comerciais, surface admin ou novo escopo.
- qualquer próxima execução de docs deve manter o contrato sem material sensível.

### Próxima trilha recomendada

**API Key Partner Documentation Execution Review**

Objetivo:

- transformar o contrato de onboarding em pacote operacional/publicável, incluindo revisão final de exemplos, versão, canal de entrega e checklist de ativação por parceiro.

## API Key Partner Documentation Execution Review

- o módulo `api_keys` agora possui review executável para validar o pacote operacional/publicável da documentação de parceiros.
- query service:
  - `api_keys.application.api_key_partner_documentation_execution_review_queries`
- comando:
  - `python manage.py api_key_partner_documentation_execution_review --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required --delivery-channel-documented --support-handoff-documented --smoke-evidence-template-ready --change-control-documented --owner-approved --no-runtime-change-required --no-commercial-terms-included --no-sensitive-material-included`

### Escopo fechado

- guia versionado de onboarding de catálogo público.
- decisão de canal de entrega.
- owner de documentação.
- handoff de suporte.
- template de evidência de smoke.
- controle de mudança.
- confirmação de que não há runtime change, termos comerciais ou material sensível.

### Decisões

- execution review prepara o pacote publicável, mas não publica, envia credencial ou executa smoke real.
- pacote deve circular apenas por canal restrito/aprovado.
- suporte pode validar status/flags, mas não deve solicitar nem armazenar API key em claro.
- qualquer alteração de shape, erro ou checklist exige nova versão e registro de decisão.

### Próxima trilha recomendada

**API Key Partner Documentation Publication Evidence Review**

Objetivo:

- capturar evidência sanitizada de que a documentação foi publicada/entregue pelo canal aprovado e está pronta para onboarding real de parceiro.

## API Key Partner Documentation Publication Evidence Review

- o módulo `api_keys` agora possui review executável para capturar evidência sanitizada de publicação/entrega da documentação de parceiros.
- query service:
  - `api_keys.application.api_key_partner_documentation_publication_evidence_queries`
- comando:
  - `python manage.py api_key_partner_documentation_publication_evidence --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required --delivery-channel-documented --support-handoff-documented --smoke-evidence-template-ready --change-control-documented --owner-approved --no-runtime-change-required --no-commercial-terms-included --no-sensitive-material-included --published-version 2026-05-26 --approved-channel restricted-support-ticket --target-audience approved-partner --tenant-reference tenant-ref-001 --published-at 2026-05-26T12:00:00-03:00 --evidence-reference DOC-EVIDENCE-001 --publication-confirmed --support-notified --activation-status-recorded --smoke-template-attached --redaction-confirmed --no-credential-shared --no-runtime-activation-performed`

### Escopo da evidência

- versão publicada;
- canal aprovado;
- audiência alvo;
- referência de tenant;
- timestamp de publicação;
- referência sanitizada de evidência;
- suporte notificado;
- status de ativação registrado;
- template de smoke anexado.

### Decisões

- evidência de publicação não executa smoke real.
- evidência de publicação não ativa runtime, feature flag ou endpoint.
- evidência de publicação não inclui API key, segredo, hash, token, header ou screenshot de credencial.
- entrega documentada é suficiente para avançar a closure de onboarding de parceiros.

### Próxima trilha recomendada

**API Key Partner Onboarding Closure Review**

Objetivo:

- fechar a trilha de onboarding/documentação de parceiros e decidir se o próximo ROI volta para quotas comerciais, novos endpoints ou ativação real por parceiro.

## API Key Partner Onboarding Closure Review

- o módulo `api_keys` agora possui closure executável para fechar a trilha de onboarding/documentação de parceiros.
- query service:
  - `api_keys.application.api_key_partner_onboarding_closure_queries`
- comando:
  - `python manage.py api_key_partner_onboarding_closure --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required --delivery-channel-documented --support-handoff-documented --smoke-evidence-template-ready --change-control-documented --owner-approved --no-runtime-change-required --no-commercial-terms-included --no-sensitive-material-included --published-version 2026-05-26 --approved-channel restricted-support-ticket --target-audience approved-partner --tenant-reference tenant-ref-001 --published-at 2026-05-26T12:00:00-03:00 --evidence-reference DOC-EVIDENCE-001 --publication-confirmed --support-notified --activation-status-recorded --smoke-template-attached --redaction-confirmed --no-credential-shared --no-runtime-activation-performed --onboarding-scope-closed --residual-risks-accepted --next-roi-decision-recorded --partner-activation-deferred --commercial-quotas-deferred --new-endpoint-expansion-deferred`

### Escopo fechado

- review de documentação de onboarding;
- execution review do pacote publicável;
- publication evidence sanitizada;
- guia público de catálogo;
- delivery package;
- publication evidence;
- exemplos seguros e guardrails de redaction.

### Riscos residuais

- ativação real por parceiro ainda exige smoke operacional separado.
- quotas comerciais e billing continuam fora do contrato.
- novos endpoints públicos exigem nova seleção ROI e contrato próprio.
- documentação precisa ser versionada novamente se payload ou erro mudar.
- canal de entrega deve continuar restrito para evitar exposição acidental.

### Decisões

- trilha de onboarding/documentação está fechada para o ciclo atual.
- ativação real por parceiro fica diferida.
- quotas comerciais e novos endpoints ficam diferidos.
- próxima decisão deve voltar para seleção sistêmica de ROI.

### Próxima trilha recomendada

**System ROI Re-Selection Review**

Objetivo:

- decidir se o próximo maior ROI está em quotas comerciais de API key, ativação real por parceiro, expansão de endpoints públicos ou outra frente do sistema.

## Post-Onboarding System ROI Re-Selection Review

- o módulo `api_keys` agora possui re-seleção executável de ROI após closure de onboarding/documentação de parceiros.
- query service:
  - `api_keys.application.api_key_post_onboarding_roi_reselection_queries`
- comando:
  - `python manage.py api_key_post_onboarding_roi_reselection --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required --delivery-channel-documented --support-handoff-documented --smoke-evidence-template-ready --change-control-documented --owner-approved --no-runtime-change-required --no-commercial-terms-included --no-sensitive-material-included --published-version 2026-05-26 --approved-channel restricted-support-ticket --target-audience approved-partner --tenant-reference tenant-ref-001 --published-at 2026-05-26T12:00:00-03:00 --evidence-reference DOC-EVIDENCE-001 --publication-confirmed --support-notified --activation-status-recorded --smoke-template-attached --redaction-confirmed --no-credential-shared --no-runtime-activation-performed --onboarding-scope-closed --residual-risks-accepted --next-roi-decision-recorded --partner-activation-deferred --commercial-quotas-deferred --new-endpoint-expansion-deferred --partner-activation-requested --partner-api-key-ready`

### Candidatos reavaliados

- partner activation smoke: recomendado quando há parceiro pronto e API key preparada.
- commercial quotas: recomendado quando há pressão real de plano, abuso ou cobrança.
- public endpoint expansion: recomendado apenas com demanda concreta depois de list/detail.
- admin management UX: recomendado quando suporte/admin sofre carga operacional real.
- pause API key track: recomendado quando outra frente sistêmica superar o ROI restante.

### Decisão recomendada

**API Key Partner Activation Smoke Review**

Motivo:

- onboarding/documentação já está fechado;
- uma ativação controlada valida o contrato com menor risco do que abrir endpoint novo;
- quotas comerciais ainda dependem de pressão de plano/abuso/cobrança;
- expansão pública deve esperar demanda concreta depois do consumo real de list/detail.

### Próxima trilha recomendada

**API Key Partner Activation Smoke Review**

Objetivo:

- desenhar o menor smoke operacional real por parceiro, validando list/detail com evidência sanitizada e rollback, sem mudar endpoint, escopo, billing ou quota.

## API Key Partner Activation Smoke Contract Review

- o módulo `api_keys` agora possui review executável para definir o contrato do primeiro smoke controlado de ativação de parceiro.
- query service:
  - `api_keys.application.api_key_partner_activation_smoke_contract_queries`
- comando:
  - `python manage.py api_key_partner_activation_smoke_contract --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required --delivery-channel-documented --support-handoff-documented --smoke-evidence-template-ready --change-control-documented --owner-approved --no-runtime-change-required --no-commercial-terms-included --no-sensitive-material-included --published-version 2026-05-26 --approved-channel restricted-support-ticket --target-audience approved-partner --tenant-reference tenant-ref-001 --published-at 2026-05-26T12:00:00-03:00 --evidence-reference DOC-EVIDENCE-001 --publication-confirmed --support-notified --activation-status-recorded --smoke-template-attached --redaction-confirmed --no-credential-shared --no-runtime-activation-performed --onboarding-scope-closed --residual-risks-accepted --next-roi-decision-recorded --partner-activation-deferred --commercial-quotas-deferred --new-endpoint-expansion-deferred --partner-activation-requested --partner-api-key-ready --partner-reference partner-ref-001 --target-environment staging --product-slug-reference product-slug-ref-001 --smoke-evidence-reference SMOKE-CONTRACT-001 --smoke-scope-documented --list-endpoint-in-scope --detail-endpoint-in-scope --expected-status-codes-documented --observability-check-documented --rollback-plan-documented --redaction-plan-documented --no-new-endpoint-in-smoke --no-commercial-terms-in-smoke --no-runtime-change-in-smoke --no-credential-material-in-smoke`

### Escopo do smoke

- `GET /api/v1/catalog/products/`;
- `GET /api/v1/catalog/products/<slug>/`;
- escopo `read:catalog`;
- subdomínio do tenant;
- referência sanitizada de evidência;
- verificação de observabilidade;
- plano de rollback.

### Decisões

- o contrato prepara a execução, mas não executa requests.
- smoke cobre apenas list/detail já existentes.
- não há endpoint novo, billing, quota, termo comercial ou mudança de runtime.
- evidência futura deve ser sanitizada e sem credencial/header/token.

### Próxima trilha recomendada

**API Key Partner Activation Smoke Execution**

Objetivo:

- executar o smoke controlado em ambiente alvo, capturando apenas sinais sanitizados de sucesso/falha.

## API Key Commercial Quotas Contract Review

- o módulo `api_keys` agora possui review executável para o contrato mínimo de quotas comerciais.
- esta abordagem foi aberta por seleção explícita de Battery B, deixando ondas restantes da Battery A diferidas.
- query service:
  - `api_keys.application.api_key_commercial_quotas_contract_queries`
- comando:
  - `python manage.py api_key_commercial_quotas_contract --model-ready --runtime-auth-ready --drf-adapter-ready --public-endpoints-ready --observability-ready --expansion-closed --no-billing-or-quotas-required --no-secret-exposure-confirmed --partner-docs-versioned --endpoint-examples-documented --activation-checklist-ready --error-contract-documented --safe-examples-confirmed --no-new-endpoint-required --no-quota-or-billing-required --delivery-channel-documented --support-handoff-documented --smoke-evidence-template-ready --change-control-documented --owner-approved --no-runtime-change-required --no-commercial-terms-included --no-sensitive-material-included --published-version 2026-05-26 --approved-channel restricted-support-ticket --target-audience approved-partner --tenant-reference tenant-ref-001 --published-at 2026-05-26T12:00:00-03:00 --evidence-reference DOC-EVIDENCE-001 --publication-confirmed --support-notified --activation-status-recorded --smoke-template-attached --redaction-confirmed --no-credential-shared --no-runtime-activation-performed --onboarding-scope-closed --residual-risks-accepted --next-roi-decision-recorded --partner-activation-deferred --commercial-quotas-deferred --new-endpoint-expansion-deferred --battery-b-selected-by-operator --battery-a-remaining-deferred --commercial-quota-pressure-confirmed --quota-dimensions-documented --quota-window-documented --quota-default-limits-documented --quota-overage-behavior-documented --quota-error-contract-documented --quota-observability-documented --quota-admin-visibility-documented --no-billing-charge-in-contract --no-plan-enforcement-in-contract --no-runtime-enforcement-in-contract --no-new-endpoint-in-contract --no-sensitive-material-in-contract`

### Contrato mínimo

- dimensões: `tenant_id`, `api_key_id`, `endpoint`, `window`;
- escopo inicial: `read:catalog`;
- janela padrão: diária;
- limite padrão inicial: `10000` requests por janela;
- excesso: hard-limit com `429`;
- visibilidade admin: read-only mínima;
- observabilidade: métricas e audit de bloqueio.

### Fora de escopo

- cobrança real;
- enforcement de plano;
- enforcement runtime nesta wave;
- endpoint público novo;
- billing provider;
- material sensível em logs/evidências.

### Próxima trilha recomendada

**API Key Quota Model Minimal Execution**

Objetivo:

- criar o modelo mínimo de quota tenant/key/endpoint/window sem ainda acoplar billing ou enforcement runtime.

## API Key Partner Activation Remaining Waves

- o módulo `api_keys` agora possui execução completa das ondas restantes da Battery A.
- query services:
  - `api_keys.application.api_key_partner_activation_smoke_execution_queries`
  - `api_keys.application.api_key_partner_activation_evidence_capture_queries`
  - `api_keys.application.api_key_partner_activation_post_smoke_monitoring_queries`
  - `api_keys.application.api_key_partner_activation_closure_queries`
- comandos:
  - `python manage.py api_key_partner_activation_smoke_execution --smoke-contract-ready --partner-reference partner-ref-001 --tenant-reference tenant-ref-001 --target-environment staging --list-endpoint-checked --detail-endpoint-checked --list-status-expected --detail-status-expected --auth-failure-negative-checked --observability-signal-checked --rollback-not-required --evidence-reference SMOKE-EXEC-001 --redaction-confirmed --no-secret-material-recorded --no-runtime-change-performed`
  - `python manage.py api_key_partner_activation_evidence_capture --smoke-execution-ready --evidence-reference SMOKE-EVIDENCE-001 --list-result-attached --detail-result-attached --negative-auth-result-attached --metrics-snapshot-attached --audit-log-reference-attached --partner-handoff-reference-attached --support-handoff-reference-attached --redaction-confirmed --no-secret-material-recorded --rollback-note-attached`
  - `python manage.py api_key_partner_activation_post_smoke_monitoring --evidence-capture-ready --monitoring-window-observed --partner-access-stable --auth-failure-rate-expected --rate-limit-noise-expected --endpoint-error-rate-expected --support-ticket-status-recorded --rollback-not-required --no-sensitive-data-observed --commercial-quota-pressure-recorded`
  - `python manage.py api_key_partner_activation_closure --smoke-contract-ready --smoke-execution-ready --evidence-capture-ready --post-smoke-monitoring-ready --partner-handoff-closed --support-handoff-closed --rollback-window-closed --no-sensitive-material-retained --no-runtime-change-pending --commercial-quota-track-selected --docs-updated --decision-recorded`

### Decisões

- a execução da Battery A permanece operacional e auditável, mas não cria endpoint, quota, cobrança ou runtime change.
- evidências devem ser referências sanitizadas, sem API key, header, token, hash ou segredo.
- monitoramento pós-smoke registra estabilidade, suporte, rollback e pressão comercial por quota.
- closure direciona o próximo ROI para `API Key Commercial Quotas Contract Review`/modelo mínimo.

### Próxima trilha recomendada

**API Key Quota Model Minimal Execution**

Objetivo:

- transformar o contrato de quota comercial já aprovado em modelo mínimo tenant-scoped, ainda sem billing real.

## API Key Commercial Quotas Execution & Closure

- o módulo `api_keys` agora possui quotas comerciais mínimas tenant-scoped para endpoints públicos.
- modelos:
  - `ApiKeyQuota`;
  - `ApiKeyQuotaUsage`.
- application services:
  - `api_keys.application.api_key_quota_commands`;
  - `api_keys.application.api_key_quota_enforcement`;
  - `api_keys.application.api_key_quota_queries`;
  - `api_keys.application.api_key_commercial_quotas_closure_queries`.
- comandos:
  - `python manage.py api_key_quota_upsert --tenant-id <tenant_id> --api-key-id <api_key_id> --endpoint catalog.products.list --limit 10000 --window-seconds 86400 --actor-label ops`
  - `python manage.py api_key_commercial_quotas_closure --contract-ready --model-ready --enforcement-review-ready --enforcement-ready --admin-visibility-review-ready --admin-visibility-ready --metrics-ready --audit-ready --no-billing-charge-created --no-plan-enforcement-created --no-sensitive-material-recorded --docs-updated --decision-recorded`
- surface admin:
  - `/ops/api-keys/quotas/`.

### Semântica de runtime

- se não houver quota ativa para `tenant/api_key/endpoint`, o comportamento existente permanece igual.
- se houver quota ativa, o throttle executa rate limit técnico primeiro e quota comercial depois.
- excesso de quota retorna `429`, registra `api_key.quota_exceeded` e incrementa `hubx_api_key_quota_exceeded_total`.
- contagem é por `tenant_id`, `api_key_id`, `endpoint`, `window_start` e `window_seconds`.

### Fora de escopo

- cobrança real;
- enforcement por plano/subscription;
- billing provider;
- criação de endpoint público novo;
- armazenamento de API key, header, hash, token ou segredo.

### Próxima trilha recomendada

**System ROI Re-Selection Review**

Objetivo:

- escolher o próximo maior ROI após fechar ativação de parceiro e quotas comerciais mínimas.

## System ROI Post-Quota Re-Selection Review

- o módulo `api_keys` agora possui uma re-seleção sistêmica pós-Battery B para encerrar a trilha de API pública antes de mover para outro domínio.
- query service:
  - `api_keys.application.system_roi_post_quota_reselection_queries`
- comando:
  - `python manage.py system_roi_post_quota_reselection --quota-contract-ready --quota-model-ready --quota-enforcement-review-ready --quota-enforcement-ready --quota-admin-visibility-review-ready --quota-admin-visibility-ready --quota-metrics-ready --quota-audit-ready --quota-no-billing-charge-created --quota-no-plan-enforcement-created --quota-no-sensitive-material-recorded --quota-docs-updated --quota-decision-recorded --payments-provider-production-blocker --payments-refund-reconciliation-blocker`

### Candidatos

- `Payments Production Readiness Review`: recomendado quando provider produtivo, refund ou conciliação financeira ainda bloqueiam receita real.
- `Shipping Real Quote & SLA Activation Review`: recomendado quando cotação/frete real bloqueia conversão e há contrato de transportadora pronto.
- `Cross-Module Production Runbook Closure Review`: recomendado quando a lacuna principal é operação/runbook antes de Go/No-Go produtivo.
- `Storefront Conversion Experimentation Review`: recomendado apenas com tráfego/dados reais suficientes.

### Decisão recomendada

**Payments Production Readiness Review**

Motivo:

- após Battery A e Battery B, API pública já tem uso controlado, quotas, audit, métrica e admin visibility.
- o maior risco sistêmico restante tende a estar em receita real: provider de pagamento, refund produtivo e conciliação.
- shipping real e runbooks continuam candidatos, mas ficam abaixo quando pagamentos ainda bloqueiam produção.
