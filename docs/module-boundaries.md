# Module Boundaries — Hubx Market

Este documento define as **fronteiras entre módulos** do Hubx Market.

O objetivo é evitar acoplamento indevido, preservar a arquitetura modular e garantir que o sistema não evolua para um monólito desorganizado.

---

# Objetivos

Este documento serve para:

- definir responsabilidades por módulo
- definir o que cada módulo pode acessar
- definir o que cada módulo não deve acessar
- orientar contribuidores e agentes de IA
- reduzir acoplamento entre domínios

---

# Regra geral

Cada módulo deve ter uma **responsabilidade clara**.

A comunicação entre módulos deve acontecer preferencialmente por:

- `application/`
- serviços explícitos
- contratos claros
- eventos internos quando necessário

Evitar:

- importar detalhes internos arbitrários de outros módulos
- espalhar lógica de negócio entre módulos
- acessar diretamente `models.py` de outro módulo sem necessidade real e sem contrato

## Contrato de contexto de tenant

Para módulos tenant-owned (`catalog`, `customers`, `checkout`, `orders`, `payments` e superfícies logadas correlatas):

- query services e command services devem aceitar `tenant_id` explícito sempre que operarem sobre dados da loja
- a camada `interfaces/` deve repassar `request.tenant.id` quando o tenant já estiver resolvido
- services não devem depender de “primeiro registro”, “perfil ativo global” ou leitura implícita cross-tenant quando o contexto já estiver disponível
- fallback sem `tenant_id` só é aceitável em superfícies legadas ou operacionais onde essa compatibilidade já seja contrato explícito

Objetivo:

- reduzir ambiguidade entre módulos
- evitar leitura ou escrita na loja errada
- tornar o fluxo multi-tenant mais previsível para evolução futura

### Compatibilidade legada aceitável neste estágio

Ainda é aceitável tolerar ausência de `tenant_id` apenas quando **todas** as condições abaixo forem verdadeiras:

- a surface é primariamente de leitura
- a ausência de tenant já é parte do contrato legado atual
- não existe risco relevante de escrita cross-tenant
- o resultado pode ser tratado como fallback operacional ou demo, não como verdade forte do domínio

Exemplos aceitáveis por enquanto:

- superfícies de `accounts` que ainda servem login, overview ou customer area em modo legado/global
- listas e detalhes administrativos em modo global, quando a request ainda não estiver tenant-scoped
- fallbacks controlados de apresentação documentados explicitamente como compatibilidade temporária

### Compatibilidade legada que já não deve continuar

Não é mais aceitável tolerar ausência de `tenant_id` em:

- commands de `checkout`
- commands de `orders`
- commands de `payments`
- fluxos de retomada de compra (`reorder`, `payment retry`, hosted payment)
- qualquer write path que resolva entidades tenant-owned por identificadores como `order_number`, `attempt_key`, `slug` ou equivalentes

Nesses casos, o comportamento esperado passa a ser:

- falhar fechado
- responder indisponibilidade segura
- registrar breadcrumb/log suficiente para troubleshooting

### Candidatas de aposentadoria prioritária

Depois do hardening atual, as tolerâncias globais que mais parecem maduras para aposentadoria são:

1. `accounts.application.account_page_queries`
   - `FallbackAccountProfileRepository`
   - overview/login/register/forgot ainda conseguem responder com perfil demo/global
   - melhor candidato inicial para virar estado explícito de ausência ou onboarding controlado por tenant
   - risco menor por ser majoritariamente leitura e não carregar CRUD sensível da conta

2. `accounts.application.account_customer_area_queries`
   - fallback global de perfil/área do cliente ainda existe quando não há tenant resolvido
   - como a customer area já é semanticamente tenant-owned, esse modo legado continua candidato forte
   - mas a retirada completa ainda não é a próxima mais segura porque junta muitas superfícies de leitura e empty states numa única mudança
   - a decomposição segura agora fica:
     1. retirar fallback global de perfil
     2. retirar fallback global de endereços
     3. retirar fallback global de pedidos
     4. só então revisar a aposentadoria residual do modo global da customer area inteira
   - a etapa 1 já foi aplicada; o fallback global de perfil saiu da customer area, enquanto pedidos e endereços continuam preservados por compatibilidade
   - a revisão seguinte indica que a etapa 2 já parece madura:
     - `get_addresses_page_data()` é isolado
     - o template já possui empty state explícito
     - a continuidade da conta não depende de endereço fixture para permanecer compreensível
   - a etapa 2 já foi aplicada; a customer area deixa de usar fallback global de endereços e passa a expor vazio explícito quando não houver persistência real
   - a revisão do eixo de pedidos indica que a etapa 3 ainda não deve sair inteira de uma vez:
     - `orders list` e `order detail` já carregam continuidade, recovery e ações reais demais
     - a próxima decomposição segura deve separar primeiro a lista do detalhe
   - a revisão específica da lista mostrou que `get_orders_page_data()` já parece madura para ser o próximo corte seguro:
     - é primariamente leitura
     - o template já aceita empty state explícito
     - o maior risco operacional continua concentrado no detalhe
   - com isso, a ordem segura neste ponto fica:
     1. aposentar primeiro o fallback global da **lista de pedidos**
     2. manter o **detalhe do pedido** como último corte desse eixo
   - essa primeira retirada de `orders` já foi aplicada na lista:
     - `get_orders_page_data()` e `AccountOrdersView` deixam de reaproveitar fixture global
     - ausência de histórico na lista agora vira `missing` + empty state honesto
     - o detalhe continua preservando compatibilidade legada por concentrar recovery e ações reais
   - a revisão específica do detalhe reforçou essa classificação:
     - `get_order_detail_page_data()` ainda funciona como boundary de continuidade e recovery, não só como leitura simples
     - hosted payment, retry, reorder, confirmação inicial e trilha operacional ainda passam por essa mesma superfície
     - por isso, a aposentadoria do fallback global no detalhe ainda não é o próximo corte seguro
   - a decomposição segura do detalhe agora deve seguir camadas:
     1. leitura base do detalhe
     2. handoff/`confirmation_mode` do checkout
     3. capability de `reorder lite`
     4. bloco de recovery e pagamento
     5. só então a retirada residual do fallback global
   - a revisão da primeira camada mostrou que “leitura base” precisa ser tratada como **payload estrutural do pedido**, não como toda a copy do detalhe
   - entram primeiro:
     - resumo principal
     - status atual
     - itens e totais
     - timeline básica do pedido
   - ficam fora desse primeiro subcorte:
     - `page_description`, `page_meta`, `summary_subtitle`, `summary_note`
     - `confirmation_mode`
     - CTAs e sinais de `payments`
     - alerts de pending/drift/recovery
   - o plano seguro para implementar essa primeira camada é:
     1. extrair primeiro o payload estrutural para um bloco isolado
     2. manter o contrato atual do template
     3. deixar copy enriquecida, CTAs e sinais operacionais na camada residual
     4. só depois revisar se a leitura estrutural já consegue viver sem fallback global
   - essa primeira extração estrutural já foi aplicada:
     - o payload estrutural do detalhe agora nasce em um bloco próprio
     - o template continua consumindo o mesmo contrato
     - narrativa enriquecida e recovery permanecem explicitamente fora desse recorte
   - a revisão seguinte mostrou que o próximo subcorte seguro parece ser o handoff de confirmação do checkout:
     - `confirmation_mode` entra por um gate simples e explícito
     - ele altera apenas uma fatia localizada da narrativa do detalhe
     - ele não carrega sozinho a mesma complexidade de recovery transacional do bloco de `payments`
   - o plano seguro desse subcorte agora fica:
     1. extrair o confirmation payload para um bloco isolado
     2. manter o gate explícito na view
     3. deixar `payments`/recovery completamente fora
     4. só depois reavaliar se o handoff já consegue viver sem fallback legado
   - essa extração do handoff já foi aplicada:
     - o confirmation payload agora nasce em um bloco próprio
     - o gate de entrada continua explícito na view
     - `payments`/recovery seguem fora desse recorte
   - a revisão seguinte mostrou que `reorder lite` já parece o próximo subcorte seguro:
     - o CTA nasce localmente no `order detail`
     - a ação entra por `POST` explícito
     - o write real é delegado ao boundary de `checkout`
     - ele não depende diretamente do bloco transacional de `payments`
   - o plano seguro desse subcorte agora fica:
     1. extrair o payload de `reorder lite` para um bloco próprio
     2. manter a action boundary explícita na view
     3. preservar a delegação do write para `checkout_reorder_commands`
     4. deixar retry, hosted payment e recovery fora desta etapa
   - essa extração do `reorder lite` já foi aplicada:
     - o payload agora nasce em um bloco próprio
     - a action boundary segue explícita na view
     - o write real continua delegado ao boundary de `checkout`
   - por isso, o próximo passo seguro parece ser isolar melhor a capability de recompra leve antes de tocar em retry, hosted payment e recovery
   - isso evita misturar numa única mudança:
     - leitura de apresentação
     - feedback de handoff
     - ações comerciais
     - recovery transacional e observabilidade operacional
   - a revisão seguinte do `payment retry` mostrou que ele ainda **não** deve ser o próximo subcorte:
     - a action continua local, mas já depende de falha real de pagamento
     - o write segue para um bootstrap específico de retry
     - o bloco conversa com recovery e continuidade transacional demais para esta etapa
   - por isso, `payment retry` continua depois do bloco mais explícito de hosted payment / recovery, e não como próximo corte isolado
   - a revisão seguinte de `hosted payment` mostrou que ele também ainda **não** deve ser tratado como próximo subcorte isolado:
     - o CTA nasce no detalhe, mas aponta diretamente para a boundary de `payments`
     - o bloco depende de `PaymentAttempt` pendente, `attempt_key` e redirect hospedado
     - o comportamento já está acoplado ao guidance de recovery e continuidade segura do pagamento
   - por isso, `hosted payment` deve continuar junto do bloco de recovery/payment continuity, e não como uma capability isolada anterior
   - a revisão consolidada seguinte mostrou que o restante do detalhe já se organiza melhor como **recovery block**:
     - `payment_progression_*`
     - `payment_retry_*`
     - `hosted_payment_*`
     - `payment_attempt_*`
     - `pending_recovery_*`
     - `order_pending_recovery_*`
   - esse restante compartilha semântica de continuidade e recovery transacional demais para continuar sendo fatiado por CTA
   - por isso, a próxima revisão segura deve tratar esse eixo como um único boundary residual do `order detail`
   - o plano seguro dessa decomposição agora fica:
     1. isolar a leitura operacional passiva de `PaymentAttempt`
     2. isolar o guidance de recovery
     3. só então revisar actions/capabilities de pagamento
     4. deixar a narrativa residual por último
   - isso evita misturar numa única mudança:
     - telemetria passiva
     - guidance operacional
     - actions de continuidade de pagamento
     - costura narrativa final do detalhe
   - a revisão seguinte mostrou que essa primeira camada já parece segura:
     - `payment_attempt_*` hoje nasce como leitura/timeline passiva
     - o template apenas exibe contexto operacional
     - não há ação transacional disparada por esse sub-bloco
   - por isso, o próximo subcorte seguro do recovery block parece ser justamente a leitura operacional passiva de `PaymentAttempt`
   - a revisão seguinte mostrou que a segunda camada também já parece segura:
     - `pending_recovery_*` e `order_pending_recovery_*` hoje entram como alerts passivos
     - o template apenas comunica guidance contextual
     - o sub-bloco não executa retry, redirect ou bootstrap por si só
   - por isso, o próximo subcorte seguro depois de `payment_attempt_*` parece ser justamente o guidance de recovery
   - a revisão seguinte mostrou que o restante das actions já deve ser tratado como um único actions block:
     - `payment_progression_*`
     - `payment_retry_*`
     - `hosted_payment_*`
   - esse restante compartilha a mesma surface de jornada, mas delega efeitos reais para `orders`, `checkout` e `payments`
   - por isso, a próxima revisão segura não deve voltar a separar CTA por CTA
   - o que sobra agora é um único boundary residual de continuidade de pagamento
   - o plano seguro dessa decomposição agora fica:
     1. isolar o payload declarativo das actions
     2. preservar a renderização unificada das actions no detalhe
     3. manter o dispatch transacional agrupado enquanto o bloco continuar sensível
     4. só depois reavaliar se vale separar por tipo de boundary externo
   - isso evita misturar numa única mudança:
     - payload de UI
     - renderização da surface de jornada
     - dispatch transacional
     - delegação para `orders`, `checkout` e `payments`
   - essa extração do guidance de recovery já foi aplicada:
     - o payload de `pending_recovery_*` e `order_pending_recovery_*` agora nasce em um bloco próprio
     - o template continua só exibindo feedback contextual
     - as actions reais seguem fora desse recorte
   - essa extração da leitura passiva já foi aplicada:
     - o payload `payment_attempt_*` agora nasce em um bloco próprio
     - o template continua apenas exibindo contexto operacional e timeline
     - guidance e actions seguem fora desse recorte

3. `accounts.application.account_address_commands`
   - ainda tolera `tenant_id=None` por compatibilidade
   - hoje o risco está mais controlado, mas o contrato futuro ideal é exigir tenant também nesse boundary

### Tolerâncias que ainda valem manter

Por enquanto, ainda faz sentido manter:

- fallbacks globais de `Admin Customers`, `Admin Orders` e `Admin Products`
- leituras administrativas globais que ainda sustentam operação/plataforma fora de uma loja específica

Motivo:

- essas superfícies ainda funcionam como compatibilidade operacional legítima
- a aposentadoria delas exigiria antes um contrato mais claro de admin global vs admin por tenant

---

# Princípio central

## Permitido
- um módulo consultar outro por interfaces claras
- um módulo usar casos de uso expostos por outro módulo
- um módulo depender de entidades compartilhadas apenas quando isso for inevitável

## Não permitido
- um módulo “invadir” a regra interna do outro
- um módulo reimplementar regra do outro
- um módulo assumir comportamento não documentado de outro

---

# Fronteiras por módulo

## 1. accounts

### Responsabilidade
Gerenciar autenticação e contexto de usuários administrativos da loja e da plataforma.

### Pode acessar
- tenants, para vínculo do owner ao tenant
- audit, para registrar ações relevantes

### Não deve acessar diretamente
- lógica de catálogo
- lógica de checkout
- lógica de pagamento
- lógica de frete

### Observação
`accounts` não representa `Customer`.  
Customer é outro contexto do domínio.

### Contrato de permissões administrativas

- `accounts.application.admin_permissions` é dono da matriz inicial de papéis administrativos.
- módulos tenant-owned podem consultar esse contrato por permission keys explícitas.
- commands sensíveis devem aceitar `actor_role` quando a surface admin conseguir resolver o owner atual.
- views não devem implementar regra de autorização local; elas apenas coletam contexto da request e delegam.
- ausência de `actor_role` ainda é compatibilidade legada temporária até existir autenticação/admin middleware definitivo.
- `accounts.application.admin_owner_commands` é dono de criar/editar `OwnerUser`.
- gestão de roles/status/notificações de owners deve passar por `/ops/owners/` e não por mutações espalhadas em outros módulos.
- `accounts.interfaces.middleware.OwnerContextMiddleware` pode preencher `request.owner_user` em `/ops/` a partir de `tenant + request.user.email`.
- o middleware não decide autorização; ele apenas fornece contexto para views delegarem `actor_role` aos commands.
- ausência de `request.owner_user` ainda deve ser tratada como compatibilidade temporária, não como permissão forte.
- `accounts.interfaces.middleware.OpsAuthenticationGateMiddleware` pode transformar ausência de autenticação/owner em redirect ou `403` quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`.
- ativação default do gate depende de login owner/admin real, não apenas das páginas visuais de autenticação.

---

## 2. tenants

### Responsabilidade
Gerenciar lojas, subdomínios, branding, modo manutenção, configurações do tenant.

### Pode acessar
- subscriptions, para plano/estado da loja
- accounts, durante onboarding
- notifications, para comunicações administrativas

### Não deve acessar diretamente
- detalhes internos de pedidos
- detalhes internos de pagamentos de pedidos
- lógica detalhada de catálogo

### Observação
`tenants` é o núcleo do contexto SaaS.
- identidade institucional da storefront pertence a `tenants`; páginas de commerce devem consumir contratos de application/query como `storefront_branding_queries`, sem reimplementar fallback de branding por conta própria.
- campos `Tenant.storefront_hero_*` representam configuração leve da home tenant-owned; eles não devem carregar regra de catálogo, estoque, pedido, pagamento ou page builder.
- `Tenant.conversion_primary_color` pertence a `tenants` e só pode influenciar CTAs primários por tokens/variáveis do design system; cores sem contraste AA ou CSS arbitrário não atravessam a fronteira.
- quando uma storefront precisar de imagem fallback para o hero, ela pode passar uma URL já tenant-scoped do próprio catálogo para o query service; esse fallback não autoriza leitura cross-tenant nem transforma `catalog` em dono do branding.
- a configuração administrativa desses campos, de `Tenant.logo_url` e de `Tenant.conversion_primary_color` nasce em `/ops/branding/`, com view fina em `tenants.interfaces`, command service em `tenants.application`, permissão `storefront.branding.manage` definida em `accounts` e `AuditLog` tenant-scoped.

### Platform Store Management

- a gerência de lojas/tenants pertence a `tenants`, não a módulos tenant-owned de commerce.
- a primeira surface recomendada é `/ops/platform/tenants/`, com escopo platform-only.
- essa surface não deve reutilizar `request.tenant` como autorização; ela deve exigir contexto de platform owner/admin.
- ações iniciais permitidas: listar, detalhar, criar tenant, ativar/desativar, alternar manutenção e editar `custom_domain` como cadastro.
- ações fora do recorte inicial: deletar tenant, impersonar owner/customer, editar dados internos de catálogo/pedidos/pagamentos/clientes e ativar resolução HTTP por `custom_domain`.
- writes sensíveis devem passar por application services de `tenants` e registrar `AuditLog` platform-scope ou tenant-targeted com opt-in explícito.
- `custom_domain` continua contract-only até uma wave própria alterar o resolver HTTP.
- a execução read-only inicial de `/ops/platform/tenants/` lista apenas metadados operacionais de `Tenant` e não lê dados internos de commerce.
- a permissão inicial da surface é `platform.tenants.view`, restrita a roles administrativas completas na matriz atual.
- o detalhe read-only `/ops/platform/tenants/<tenant_slug>/` pode ler apenas cadastro operacional de `Tenant` e deve retornar `404` para slug inexistente.
- a criação futura `/ops/platform/tenants/new/` deve ficar em `tenants.application`, validar `name`, `slug`, `subdomain`, bloquear subdomínios reservados e registrar `AuditLog` platform-scope explícito.
- criar tenant não deve criar owner, catálogo demo, billing, custom-domain resolver ou sessão/impersonação na mesma operação.
- a execução do command de criação exige `platform.tenants.manage`; `platform.tenants.view` permanece apenas para leitura.
- se `AuditLog` platform-scope não registrar, a criação de tenant deve ser revertida.
- a surface HTTP `/ops/platform/tenants/new/` deve permanecer fina: renderiza formulário, repassa payload/ator/role e delega o write para `platform_tenant_admin_commands`.
- mudanças de estado futuras devem ficar em `/ops/platform/tenants/<tenant_slug>/state/`, aceitar apenas `activate`, `deactivate`, `maintenance-on` e `maintenance-off`.
- `is_active` afeta o resolver por subdomínio; `maintenance_mode` é flag operacional de publicação e o middleware de `tenants` deve bloquear storefront/checkout com 503 sem alterar dados de commerce.
- a execução de state command altera apenas `is_active` ou `maintenance_mode`, registra `AuditLog` platform-scope e não toca slug/subdomain/custom_domain ou módulos de commerce.
- a surface HTTP de state management deve permanecer como action view fina: recebe `action`, delega a `platform_tenant_admin_commands.update_tenant_state(...)` e redireciona para o detalhe.
- a execução do command de `custom_domain` exige `platform.tenants.manage`, normaliza/persiste apenas `Tenant.custom_domain`, bloqueia duplicidade entre tenants, registra `AuditLog` platform-scope e não altera middleware, resolver HTTP, DNS, TLS, redirects ou subdomain principal.
- a surface HTTP de `custom_domain` deve permanecer como action view fina: recebe o campo, delega a `platform_tenant_admin_commands.update_custom_domain(...)`, redireciona para o detalhe e não adiciona side effects fora de `tenants`.
- o closure do recorte inicial considera a surface pronta apenas para operação interna controlada de cadastro/estado; bootstrap de owner, resolver runtime de custom domain, DNS/TLS, billing, impersonação e deleção seguem fora de `tenants` ops inicial.
- Owner Bootstrap futuro deve ser orquestrado por `tenants`, mas persistência/convite de `OwnerUser` pertence a `accounts`; a ação não pode criar `Customer`, senha manual, sessão automática, catálogo, billing ou impersonação.
- Custom Domain Runtime Resolver futuro pertence a `tenants`/middleware de resolução; deve usar match exato de `custom_domain`, preservar subdomínio como caminho compatível, bloquear fallback global e manter DNS/TLS fora do código.
- Owner Bootstrap Command executado em `tenants` apenas orquestra RBAC/tenant/audit platform-scope; criação de `OwnerUser`/`User` continua em `accounts.application.initial_owner_provisioning_commands`.
- Custom Domain Runtime Resolver executado no middleware de `tenants` fica atrás de `HUBX_MARKET_CUSTOM_DOMAIN_RESOLVER_ENABLED`, resolve apenas tenant ativo por match exato e não adiciona DNS/TLS/redirects.
- Owner Bootstrap Admin Surface futura deve permanecer como action view fina no detalhe platform-only, sem campo de senha e sem side effects em commerce.
- Custom Domain Runtime Evidence futura deve validar flag on/off, tenant inativo, safe miss e rollback antes de qualquer rollout de ambiente.
- Owner Bootstrap Admin Surface executada mantém view fina: renderiza formulário/estado no detalhe e delega o write para `platform_tenant_admin_commands.bootstrap_owner(...)`.
- Custom Domain Runtime Activation Runbook é evidência operacional declarativa; não altera settings, DNS, TLS ou tenants por si só.
- Owner Bootstrap Admin Surface Closure fecha apenas uso interno controlado; evidência produtiva e convite real continuam trilhas próprias.
- Custom Domain Runtime Staging Evidence é pacote declarativo de smoke/rollback; production gate ainda deve decidir rollout por ambiente.
- Owner Bootstrap Production Evidence é declarativa e não cria owner por si só; apenas confirma artefatos de produção já capturados.
- Custom Domain Runtime Production Gate decide GO/NO-GO sem alterar flag, DNS, TLS ou middleware.
- Owner Bootstrap Production Closure fecha a trilha sem novo runtime, exigindo evidência produtiva e handoff operacional.
- Custom Domain Runtime Production Activation Evidence registra ativação pós-GO, mas não executa mudança de ambiente automaticamente.
- Custom Domain Runtime Production Closure fecha o runtime sem mover DNS/TLS para o app; rollback segue por flag.
- Store Management Track Closure consolida tenants/accounts/middleware sem alterar fronteiras de commerce.
- System ROI Re-Selection pertence a `tenants.application.system_roi_reselection_queries` porque consolida a closure platform/multi-tenant e apenas recomenda a próxima trilha.
- System ROI Re-Selection não deve implementar validação funcional, acionar providers, alterar runtime, criar tenants, tocar dados de commerce ou substituir as closures específicas de payments/shipping/ops.
- System Validation Pass 2 pertence a `tenants.application.system_template_regression_smoke` como smoke sistêmico de rotas, mas só pode fazer leituras GET e checar marcadores de template/link.
- System Validation Pass 2 não deve corrigir templates, criar massa, forçar login produtivo, acionar providers, alterar permissões, mudar tenant resolution ou atravessar regras internas de commerce.
- Platform Self-Service Tenant Onboarding pertence a `tenants` como orquestrador platform-scope, mas deve chamar `subscriptions`, `accounts` e `audit` por application services explícitos.
- O onboarding self-service não deve criar billing real, invoice, catálogo demo, frete, pagamento, impersonação, DNS/TLS automático, upload de logo ou dados tenant-owned de commerce.

---

## 3. catalog

### Responsabilidade
Gerenciar produtos, variantes, categorias, marcas, tags, imagens e flags de exibição.

### Pode acessar
- tenants, para contexto de loja
- reviews, para resumo de avaliação
- coupons, se houver regra explícita de elegibilidade futura

### Não deve acessar diretamente
- checkout
- payments
- shipping
- subscriptions

### Observação
`catalog` não deve conhecer o fluxo de pedido.  
Ele fornece dados de produto; não decide compra.

---

## 3A. audit

### Responsabilidade
Registrar eventos auditáveis administrativos e operacionais.

### Pode acessar
- tenants
- eventos/payloads públicos enviados por application services

### Não deve acessar diretamente
- models internos de outros módulos
- regras de negócio internas
- executar correções operacionais

### Contrato
- escrita ocorre por `audit.application.audit_log_commands.record_event(...)`
- leitura admin ocorre por `audit.application.admin_audit_log_queries`
- eventos tenant-owned devem carregar `tenant_id`
- eventos platform-scope exigem `allow_platform_scope=True`
- metadados devem ser simples e sanitizados
- instrumentação inicial permitida:
  - criação de cupom em `coupons.application.admin_coupon_commands`
  - criação/edição de página em `pages.application.admin_page_commands`
  - aprovação/rejeição de avaliação em `reviews.application.admin_review_commands`
  - aprovação e execução registrada de refund em `payments.application`
  - criação/revogação/quota/excesso de API key em `api_keys.application`
  - atualização administrativa de visibilidade de produto em `catalog.application.admin_product_commands`
- `audit` não deve importar models internos desses módulos nem decidir se a ação é permitida
- ações bloqueadas por `accounts.application.admin_permissions` não devem registrar evento de domínio executado
- `metadata` de auditoria não deve carregar segredo, hash, payload de provider ou referência externa sensível quando um identificador operacional menor for suficiente

---

## 4. customers

### Responsabilidade
Gerenciar compradores, perfis e endereços.

### Pode acessar
- tenants
- orders, para histórico de compras
- newsletter, se houver opt-in

### Não deve acessar diretamente
- payments
- shipping internamente
- subscriptions
- accounts

### Observação
`customers` não deve ser misturado com `accounts`.

---

## 5. cart

### Responsabilidade
Gerenciar carrinho persistente e itens do carrinho.

### Pode acessar
- customers
- catalog
- tenants
- coupons, somente via application service de validação

### Não deve acessar diretamente
- payments
- shipping (cálculo formal de frete pertence ao checkout)
- orders (exceto conversão coordenada pelo checkout)

### Observação
Carrinho não é pedido.
`cart` prepara a compra, mas não a materializa sozinho.

### Contrato atual de evolução

- `cart` deve representar intenção de compra persistente antes do checkout.
- `checkout` continua dono de entrega, pagamento, revisão final e criação de pedido.
- `cart` pode guardar snapshots visuais e subtotal, mas não deve decidir frete final nem pagamento.
- `cart` pode guardar `coupon_code`, mas elegibilidade e cálculo promocional pertencem a `coupons`.
- o handoff esperado é `Cart active` → `CheckoutSession` → `Order`.
- add-to-cart permanece acumulativo por padrão; proteção contra double-submit deve usar idempotency key explícita no boundary de `cart.application`.
- `CartMutation` registra replay protection de mutações de cart por tenant/cart/chave, sem substituir a intenção acumulativa normal.
- `cart` pode aplicar guarda leve de quantidade contra disponibilidade de `ProductVariant`, mas apenas para rejeitar intenção obviamente impossível; reserva, decremento e validação final de estoque continuam fora do carrinho.
- `checkout` permanece a autoridade final para bloquear inconsistência de inventário no momento de conclusão da compra.
- conflitos finais de estoque devem ser comunicados por `checkout` como resultado de conclusão e, quando evoluídos, carregar payload por item afetado; reconciliação não deve criar pedido parcial nem ajustar quantidade sem confirmação.
- o payload de conflito de estoque pode ser recalculado por `checkout` no GET de recuperação usando `CheckoutSessionItem` e `ProductVariant`, desde que a leitura seja tenant-scoped e não escreva estoque.
- ações de reconciliação de conflito final devem alterar somente a `CheckoutSession` via `checkout.application`, nunca `Cart` convertido, estoque de `catalog` ou pedido parcial.
- `set_quantity` em `checkout.application` é aceitável como mutação explícita da sessão de checkout; ele não representa reserva de estoque nem confirmação de compra.
- reconciliação de estoque não deve concluir pedido automaticamente; depois de ajustar a sessão, o cliente precisa confirmar novamente para acionar a revalidação final.
- result codes de reconciliação de estoque pertencem a `checkout`; eles descrevem recuperação da sessão, não evento de pedido nem movimentação de inventário.
- a trilha Cart Reliability está tecnicamente encerrada para esta fase; reservation engine, baixa pós-pagamento e allocation devem ser tratados em trilhas próprias de inventory/payment, não como responsabilidade adicional do carrinho.

---

## 6. checkout

### Responsabilidade
Orquestrar o fluxo de finalização da compra.

### Pode acessar
- cart
- customers
- shipping
- coupons
- orders
- payments

### Não deve acessar diretamente
- detalhes internos de subscriptions
- lógica de admin da plataforma
- lógica de branding do tenant além do necessário

### Observação
`checkout` é o orquestrador da compra.  
Ele pode coordenar módulos, mas não deve concentrar persistência caótica nem regra espalhada.

---

## 7. orders

### Responsabilidade
Gerenciar pedidos, itens, histórico de status e consistência do lifecycle do pedido.

### Pode acessar
- customers
- tenants
- catalog, para snapshots e referências
- payments, via contrato claro
- shipping, via contrato claro
- audit

### Não deve acessar diretamente
- lógica interna do gateway de pagamento
- lógica interna de cotação de frete
- subscriptions

### Observação
`orders` é dono do lifecycle do pedido.  
Outros módulos podem influenciar o pedido, mas não devem “possuir” o fluxo do pedido.

---

## 8. payments

### Responsabilidade
Gerenciar Payment, PaymentTransaction, integração com gateway e webhooks.

### Pode acessar
- orders, por contratos claros
- checkout, quando orquestrado
- notifications, para eventos pós-pagamento
- audit

### Não deve acessar diretamente
- catalog para regra comercial arbitrária
- customers para lógica de perfil
- shipping
- subscriptions (pagamentos de assinatura podem ser outro subcontexto interno)

### Observação
`payments` não deve assumir o papel de `orders`.  
Ele confirma e informa; `orders` decide sua evolução por contrato.

---

## 9. shipping

### Responsabilidade
Gerenciar cotação de frete, remessa, rastreamento e Shipment.

### Pode acessar
- checkout
- orders
- customers, para endereço
- catalog, para peso e dimensões da variante

### Não deve acessar diretamente
- payments
- subscriptions
- accounts

### Observação
`shipping` calcula frete e cuida da remessa, mas não cria pedido sozinho.

---

## 10. coupons

### Responsabilidade
Gerenciar cupons de desconto e sua validação.

### Pode acessar
- tenants
- checkout
- orders, quando cupom já foi aplicado
- audit

### Não deve acessar diretamente
- payments
- shipping
- subscriptions
- reviews

### Observação
Regras promocionais não devem ser espalhadas por checkout, cart e orders sem centralização.
`coupons` deve validar por `tenant_id` e devolver resultado normalizado para cart/checkout consumirem.
O contrato mínimo esperado é `validate_cart_coupon(tenant_id, coupon_code, cart_snapshot)`, sempre retornando result code explícito e `discount_total` serializado.
A surface administrativa mínima de cupons deve viver em `coupons.interfaces` e escrever somente por `coupons.application.admin_coupon_commands`.
Contabilidade de uso pertence a `coupons` e lê `Order` apenas como fonte do snapshot aplicado, sem recalcular promoção.
O contrato inicial é `record_order_coupon_redemption(tenant_id, order_number)`, chamado por `checkout` após criação do pedido.
Reversão de redemption também pertence a `coupons`; `orders` pode acionar command explícito durante cancelamento, mas não deve alterar ledger de cupons diretamente.

---

## 11. reviews

### Responsabilidade
Gerenciar avaliações de produto.

### Pode acessar
- customers
- catalog
- tenants
- audit

### Não deve acessar diretamente
- checkout
- payments
- shipping
- subscriptions

### Observação
`reviews` não deve decidir regra de catálogo, apenas enriquecê-lo.
`catalog` deve consumir avaliações por application query de `reviews`, como agregados approved-only, sem ler diretamente detalhes internos do ORM.
Reviews públicas devem ser tenant-scoped e moderadas antes de aparecer no storefront/PDP.
Na PDP, `catalog.interfaces.views.ProductDetailView` pode compor `review_summary` e `approved_reviews` chamando `reviews.application.review_summary_queries`; `storefront_catalog_queries` não deve incorporar regras internas de moderação.

---

## 12. subscriptions

### Responsabilidade
Gerenciar planos, assinatura SaaS, invoices e cobrança da plataforma.

### Pode acessar
- tenants
- accounts
- notifications
- audit

### Não deve acessar diretamente
- cart
- checkout
- orders de loja
- shipping
- catálogo do tenant

### Observação
Pagamentos de assinatura SaaS são um contexto diferente dos pagamentos de pedido.
Aquisição pública de plano pertence a `subscriptions` como `SubscriptionAcquisitionLead`.
Esse lead pode chamar `tenants.application.tenant_onboarding_commands` somente na conversão platform controlada, para criar/preencher uma jornada.
O fluxo assistido de `/plans/` não deve importar commands de `tenants` nem criar tenant, owner, assinatura, catálogo, pedido ou pagamento.
O signup self-service de `/plans/signup/` é exceção explícita: a view pública em `subscriptions` delega para `tenants.application.public_tenant_signup_commands`, que orquestra tenant, assinatura trial e owner inicial sem criar dados de commerce.
Cupons comerciais de planos SaaS pertencem a `subscriptions.models.SubscriptionCoupon` e não devem reutilizar `coupons.Coupon`.
`subscriptions.application.subscription_coupon_queries.validate_plan_coupon(...)` é a boundary pública para validar `coupon_code` em `/plans/` e `/plans/signup/`.

### Public acquisition guardrails

- `/plans/` pode ler `SubscriptionPlan` ativo e criar `SubscriptionAcquisitionLead`.
- `/plans/signup/` pode ler `SubscriptionPlan` ativo e chamar o command público de `tenants` somente com `HUBX_PUBLIC_SIGNUP_ENABLED=1` e controle de acesso satisfeito.
- `/plans/` e `/plans/signup/` podem validar `SubscriptionCoupon`; cupom inválido deve bloquear side effects.
- snapshots promocionais devem ser copiados de lead para `TenantOnboarding` e de onboarding/signup para `TenantSubscription`.
- `SubscriptionPlan.monthly_price` não deve ser alterado por cupom; somente snapshots podem guardar preço efetivo.
- `/ops/platform/subscription-coupons/` gerencia cupons SaaS com `subscriptions.manage`.
- `/ops/platform/acquisitions/` pode listar/revisar leads com permissão platform.
- converter lead cria apenas `TenantOnboarding`; conclusão continua responsabilidade do wizard de onboarding em `tenants`.
- descartar lead altera apenas status/audit.
- signup self-service cria `Tenant` em `maintenance_mode`, `TenantSubscription(status=trialing)` com fim de trial calculado pelo plano e `OwnerUser`; não cria `Customer`, catálogo, pedido, pagamento ou invoice.
- `subscriptions` registra provider-alvo de billing SaaS, por padrão Asaas, mas não chama API externa nem cria cobrança recorrente.
- `subscriptions` pode expor `requires_payment_method` como requisito comercial do plano, mas `/plans/` e `/plans/signup/` não podem coletar dados de cartão.
- `payments` é o único módulo que conhece adapters de provider de checkout de pedidos; Asaas e Pagar.me não devem vazar para `checkout` ou `orders` além de contratos normalizados.
- corrida concorrente de slug/subdomínio deve ser tratada pelo command público como erro de formulário.
- `coupons.Coupon` permanece tenant-scoped para cart/checkout/order e não deve validar plano SaaS.
- provider de billing real, invoices e checkout de assinatura exigem boundary futura.

---

## 13. notifications

### Responsabilidade
Gerenciar envio de e-mails e notificações transacionais.

### Pode acessar
- orders
- payments
- subscriptions
- tenants
- customers

### Não deve acessar diretamente
- lógica de decisão de negócio
- regras de catálogo
- regras de checkout

### Observação
`notifications` deve reagir a eventos, não tomar decisões centrais do domínio.

Para cupons aplicados, `notifications` não deve consultar `coupons` nem recalcular desconto.
Qualquer copy futura sobre cupom deve ser derivada do snapshot já persistido em `Order`, com CTA para o detalhe do pedido como fonte auditável.

### Produção transacional

- provider gate, smoke, evidência, failure handling e monitoring pertencem a `notifications.application`.
- smoke produtivo cria/processa `EmailLog` tenant-scoped e não deve consultar dados de `Customer`.
- outputs operacionais devem mascarar recipient e usar contadores/status, não PII em claro.
- classificação de bounce/falha é operacional; não altera pedido, pagamento, entrega ou preferências do cliente.
- lifecycle/campanhas devem entrar em trilha própria e não reaproveitar o smoke como engine de marketing.

### Lifecycle consentido

- `newsletter` é dono do opt-in/opt-out e do segmento consentido.
- `notifications` é dono do intent e do `EmailLog` pós-compra.
- `orders` é apenas entidade de elegibilidade; `notifications` não altera status, pagamento ou fulfillment.
- opt-out (`NewsletterSubscriber.Status.UNSUBSCRIBED`) bloqueia criação de `EmailLog`.
- o recorte atual não cria campanha recorrente, scoring, frequência, worker novo ou automação de marketing.

## Storefront conversion data-driven

- `catalog` é dono dos eventos brutos de descoberta storefront e do experimento `product_card_priority_v1`.
- eventos usados para ranking devem permanecer tenant-scoped e sem PII.
- o experimento pode ajustar prioridade de cards, mas não deve alterar preço, estoque, disponibilidade, checkout ou pedidos.
- sinais negativos de indisponibilidade devem reduzir prioridade; não devem esconder conflitos ou permitir compra indisponível.
- analytics avançado, atribuição multi-touch e BI dedicado continuam fora do módulo `catalog` nesta fase.

## System production closure

- `tenants` coordena a closure sistêmica por ser o boundary inicial de resolução multi-tenant.
- a closure pode agregar sinais declarativos de módulos, runbooks, observabilidade, smoke e rollback.
- a closure não deve importar detalhes internos arbitrários, executar providers, alterar settings, criar tenants ou mutar dados de commerce.
- `GO` significa ativação controlada e reversível, não rollout irrestrito.
- `NO-GO` deve resultar em bateria corretiva mínima pelo maior blocker.

---

## 14. pages

### Responsabilidade
Gerenciar páginas institucionais editáveis tenant-owned da loja.

### Pode acessar
- tenants

### Não deve acessar diretamente
- checkout
- payments
- orders
- subscriptions

### Contrato
- admin escreve por `pages.application.admin_page_commands`
- admin lê por `pages.application.admin_page_queries`
- storefront lê por `pages.application.storefront_page_queries`
- leitura pública deve exigir tenant resolvido e `status=published`
- não há fallback global de conteúdo entre tenants

---

## 15. newsletter

### Responsabilidade
Gerenciar inscrição de newsletter e base de contatos tenant-scoped.

### Pode acessar
- tenants
- customers, quando houver vínculo explícito
- notifications, para campanhas futuras

### Não deve acessar diretamente
- checkout
- payments
- orders

### Contrato
- opt-in público escreve por `newsletter.application.newsletter_subscription_commands`
- admin lê por `newsletter.application.admin_newsletter_queries`
- inscrição exige tenant resolvido e e-mail normalizado
- descadastro deve alterar status, não deletar histórico
- campanhas e envio real devem passar por `notifications` em trilha futura
- payments
- shipping

---

## 16. audit

### Responsabilidade
Registrar ações administrativas e eventos auditáveis.

### Pode acessar
- todos os módulos, apenas como registrador

### Não deve fazer
- lógica de negócio
- orquestração
- decisão de fluxo

### Observação
`audit` é transversal, mas não deve virar dependência acopladora.

---

## 17. api-keys

### Responsabilidade
Gerenciar credenciais de integração da API pública.

### Pode acessar
- tenants
- audit

### Não deve acessar diretamente
- lógica interna de checkout
- pagamentos
- pedidos

---

# Regras de comunicação entre módulos

## Preferência 1
Chamar `application/` do módulo dono da regra.

## Preferência 2
Usar serviços explícitos ou contratos internos documentados.

## Preferência 3
Usar eventos assíncronos para efeitos colaterais ou reações secundárias.

## Evitar
- importar helpers internos arbitrários
- acessar models de outro módulo para contornar fluxo de negócio
- duplicar regra para “resolver rápido”

---

# Dono de cada regra importante

## Tenant resolution
Dono: `tenants`

## Owner authentication
Dono: `accounts`

## Customer profile
Dono: `customers`

## Product pricing
Dono: `catalog` / `ProductVariant`

- CRUD administrativo de produto pertence a `catalog.interfaces` como view fina e a `catalog.application.admin_product_commands` como boundary de escrita.
- criação/edição administrativa deve persistir `Product` e a variante padrão, mantendo preço e estoque em `ProductVariant`.
- writes administrativos de produto devem receber `tenant_id` explícito, validar unicidade de slug no tenant e SKU de variante, e registrar `AuditLog`.
- permissão de escrita usa `catalog.manage` quando `request.owner_user`/role estiver disponível; `catalog.view` permanece para navegação/leitura da área.
- a ação equivalente a delete deve desativar produto (`status=inactive`, `is_active=False`) e não remover o registro.

## Cart state
Dono: `cart`

## Checkout orchestration
Dono: `checkout`

## Order lifecycle
Dono: `orders`

## Payment gateway integration
Dono: `payments`

## Shipping quote and shipment tracking
Dono: `shipping`

- quote produtizável pertence a `shipping.application.shipping_quote_queries`.
- aplicação da quote em sessão pertence a `checkout.application.checkout_shipping_quote_commands`, consumindo contrato público de `shipping`.
- `shipping` não deve criar pedido nem alterar `Order`; `checkout` apenas atualiza a sessão aberta.
- transportadora real/token externo seguem fora do adapter skeleton desta bateria.

## Coupon validation
Dono: `coupons`

## Product reviews
Dono: `reviews`

## SaaS plan and subscription lifecycle
Dono: `subscriptions`

- fundação de plano/assinatura pertence a `subscriptions.models.SubscriptionPlan` e `subscriptions.models.TenantSubscription`.
- cupom comercial de plano pertence a `subscriptions.models.SubscriptionCoupon`.
- comandos de setup pertencem a `subscriptions.application.subscription_commands`.
- validação e administração de cupom SaaS pertencem a `subscriptions.application.subscription_coupon_queries` e `subscriptions.application.subscription_coupon_commands`.
- leitura admin pertence a `subscriptions.application.subscription_queries` e `subscriptions.interfaces`.
- `subscriptions` não deve chamar pagamentos de pedido, checkout, cart ou shipping para decidir plano SaaS.
- provider de billing real e enforcement de plano exigem trilhas próprias.

## Email sending
Dono: `notifications`

## Audit trail
Dono: `audit`

---

# Regras de implementação para agentes de IA

Antes de implementar qualquer tarefa, agentes devem responder mentalmente:

1. Qual módulo é dono dessa regra?
2. Estou colocando lógica no módulo certo?
3. Estou chamando outro módulo por caminho claro?
4. Estou acoplando demais?
5. Existe documentação do módulo em `docs/modules/`?
6. Esta mudança viola alguma fronteira deste documento?

---

# Sinais de que a fronteira foi quebrada

Exemplos de problemas:

- `payments` alterando pedido arbitrariamente sem contrato
- `cart` criando pedido diretamente
- `catalog` decidindo fluxo de shipping
- `subscriptions` lendo detalhes internos de checkout
- `notifications` contendo regra de negócio
- `accounts` tratando customer como owner

Se isso ocorrer, a implementação deve ser revista.

---

# Objetivo final

Este documento existe para manter o Hubx Market:

- modular
- previsível
- escalável
- seguro para evolução
- fácil para contribuidores e agentes de IA

---

## Nota de boundary: order detail actions block

- no `order detail` da `customer area`, o bloco residual de continuidade de pagamento agora já separa explicitamente:
  - payload declarativo das actions em `accounts.application.account_customer_area_queries`
  - renderização unificada em `accounts.interfaces.views._build_order_detail_actions(...)`
  - dispatch transacional agrupado em `accounts.interfaces.views.AccountOrderDetailView.post(...)`
- isso preserva as fronteiras com:
  - `orders` para confirmação interna
  - `checkout` para `payment retry`
  - `payments` para continuidade hospedada
- leitura prática:
  - configuração de UI fica em `accounts`
  - execução real continua delegada ao módulo dono de cada efeito
- a revisão mais recente reforça que essa renderização unificada é uma boundary segura:
  - ela monta a surface visual do detalhe
  - mas não executa o efeito de domínio em si
- isso permite tratá-la como próximo subcorte interno antes de mexer no dispatch agrupado
- o plano seguro dessa boundary agora fica:
  1. tornar a renderização mais declarativa internamente
  2. manter `_build_order_detail_actions(...)` como surface única da view
  3. preservar o dispatch agrupado até uma revisão posterior
- leitura prática:
  - `accounts.interfaces.views` continua dono da montagem visual do detalhe
  - os módulos externos continuam donos do efeito real de cada action
- essa extração já foi aplicada:
  - `accounts.interfaces.views` agora monta primeiro itens declarativos de action
  - a renderização HTML final continua centralizada na mesma surface pública
- isso reforça a boundary:
  - UI em `accounts`
  - efeito real nos módulos donos de `orders`, `checkout` e `payments`
- a revisão do dispatch reforça que a execução ainda deve permanecer agrupada:
  - `accounts` continua apenas roteando a action
  - o efeito real continua delegado para o módulo dono
- leitura prática:
  - separar o `POST` cedo demais aumentaria o acoplamento da journey sem ganho estrutural claro agora
- a auditoria residual do `order detail` mostra que a maior parte do que restou em `accounts` já não é boundary funcional forte
- o residual agora está mais concentrado em:
  - copy enriquecida
  - composição final de `page_meta`
  - composição final de `summary_note`
- leitura prática:
  - a fronteira com `orders`, `checkout` e `payments` já está mais honesta
  - o que sobra agora é principalmente narrativa local de apresentação dentro de `accounts`
- a revisão seguinte reforça que esse residual pode ser tratado como um bloco local de narrativa:
  - não muda ownership de domínio
  - não exige nova fronteira entre módulos
- leitura prática:
  - o próximo refinamento seguro, se desejado, é um `narrative block` interno de `accounts`
- o plano seguro desse bloco agora fica:
  1. base narrativa local
  2. enriquecimento de pagamento
  3. enriquecimento de tentativa
  4. confirmação continua separada
- leitura prática:
  - a evolução segue local a `accounts`
  - sem reabrir fronteiras com `orders`, `checkout` ou `payments`
- a extração da base narrativa já foi aplicada:
  - a copy-base do detalhe agora nasce em um bloco local próprio
- isso reforça que o restante desse eixo continua sendo refinamento interno de `accounts`, não uma mudança de ownership entre módulos
- a extração seguinte também já isolou o enriquecimento de pagamento:
  - origem e referência atuais
  - `page_meta` complementar de pagamento
- leitura prática:
  - a narrativa incremental continua local a `accounts`
  - sem alterar ownership de `orders` ou `payments`
- a extração seguinte também já isolou o enriquecimento de tentativa:
  - status e status label
  - provider e referência externa
  - sessão de origem e último evento
- leitura prática:
  - a narrativa residual segue sendo refinamento local de `accounts`
  - a ownership dos módulos externos continua intacta
- a revisão da confirmação reforça que esse bloco já é uma boundary local estável:
  - gate explícito
  - payload próprio
  - sem necessidade de novo corte imediato
- o hardening final em `accounts` também fecha os writes de endereço como tenant-owned de verdade:
  - `account_address_commands` não deve mais operar sem tenant resolvido
  - `accounts.interfaces.views` continua responsável só por coletar o contexto da request e delegar o write
- leitura prática:
  - isso reduz a última tolerância global relevante de escrita que ainda restava nesse módulo

## Fechamento da abordagem multi-tenant em `accounts`

- a auditoria final mostra que o residual remanescente em `accounts` está concentrado em **leituras globais controladas**
- esse residual não altera ownership entre módulos e não cria novo write path cross-tenant
- leitura prática:
  - a abordagem multi-tenant deste módulo pode ser considerada concluída nesta fase
  - o que sobra agora é compatibilidade deliberada de leitura, não gap estrutural de boundary

## Boundary de execução checkout/payment

- a revisão pós-`Cart Reliability` confirma que a execução de pagamento já passa por três boundaries distintos:
  - `payments` cria/acompanha `PaymentAttempt`, provider intent, redirect/return e webhook
  - `orders` confirma ou falha o pagamento no pedido e aplica a baixa operacional pós-pagamento
  - `catalog` fornece a variante e o estoque atual usado pela validação final
- regra prática:
  - `payments` não deve alterar pedido diretamente fora do command service público de `orders`
  - `orders` não deve interpretar payload bruto de provider
  - `catalog` não deve decidir estado financeiro do pedido
- a ausência de reserva pré-pagamento continua deliberada nesta fase:
  - carrinho e checkout bloqueiam impossibilidades óbvias
  - checkout revalida antes de criar pedido
  - webhook pago ainda revalida estoque antes de marcar pedido como pago
- próxima fronteira a endurecer:
  - cobertura explícita do caso `payment.paid` recebido quando estoque já não permite confirmação segura

## Boundary de refund financeiro

- `payments` é dono de `PaymentRefund`, idempotência, referência externa e chamada futura ao provider.
- `orders` não deve chamar provider de refund nem interpretar payload bruto financeiro.
- `orders`, `coupons`, `catalog` e `notifications` só devem reagir a uma confirmação explícita de refund concluído, preferencialmente por evento/command público.
- regra prática:
  - registrar intenção/bloqueio de refund não altera pedido, estoque, cupom ou comunicação.
  - aprovação/admin deve preceder qualquer chamada real ao provider.
  - `payment.refunded` só representa refund confirmado, não intenção `requested` nem `processing`.
- a primeira surface admin de refunds deve ficar em `payments.interfaces` e listar apenas dados do ledger do tenant.
- qualquer ação mutável futura deve continuar em `payments.application`, nunca dentro da view.
- o command de aprovação de refund pertence a `payments.application` e deve apenas preparar execução futura.
- provider execution, efeitos em pedido e eventos continuam fora do command de aprovação inicial.
- a action admin de aprovação deve ficar em `payments.interfaces`, mas apenas como adaptador HTTP fino para `payments.application.approve_refund(...)`.
- a view não deve decidir blockers nem transições; ela só coleta `tenant_id`, `refund_key`, ator/nota e delega.
- o provider adapter de refund pertence a `payments.infrastructure` e deve apenas traduzir contrato externo/resposta.
- transição de ledger após provider pertence a `payments.application`; efeitos em outros módulos continuam posteriores a refund confirmado.
- o command de execução de refund pertence a `payments.application` e só pode consumir ledger `processing`.
- mesmo quando a resposta externa for `succeeded`, emissão de evento e efeitos cross-module devem ser tratados como etapa posterior explícita.
- detalhes do endpoint Pagar.me (`DELETE /charges/{charge_id}`, amount em centavos, bank account de boleto) pertencem exclusivamente a `payments.infrastructure`.
- readiness produtiva de payments pertence a `payments.application.production_readiness_queries`.
- os gates de produção podem classificar provider, webhook, refund, reconciliação, runbook e rollback, mas não devem chamar provider real nem movimentar dinheiro.
- closure produtiva de payments não deve habilitar rollout amplo, self-service de refund, execução em lote ou correção financeira automática.

## Boundary de login owner/admin

- `accounts` é dono da autenticação owner/admin inicial para superfícies `/ops/`.
- o contrato exige:
  - tenant resolvido por subdomínio;
  - `User` Django autenticável;
  - `OwnerUser` ativo no mesmo tenant e com e-mail correspondente.
- outros módulos não devem autenticar owner diretamente nem inferir permissão por e-mail.
- módulos operacionais devem consumir `request.owner_user`, role/permissions ou application services de `accounts`.
- customer login e `AccountProfile` permanecem fora desta boundary owner/admin.
- convite e reset owner/admin também pertencem a `accounts`, mas delivery de e-mail real deve ser delegado futuramente a `notifications`.
- nenhum módulo externo deve criar token de reset owner diretamente.
- o registro de `EmailLog` para convite/reset pertence a `notifications.application`.
- o processamento de entrega deve seguir o pipeline de notifications, nunca SMTP direto em `accounts`.
- provisionamento inicial de owner pertence a `accounts` e só deve existir como operação explícita/management command.
- nenhum módulo de storefront/customer deve criar `OwnerUser` ou `User` administrativo.
- preflight de ativação do gate pertence a `accounts`, mas pode consultar readiness de provider em `notifications`.
- o preflight não deve alterar settings/env nem executar deploy; ele apenas decide Go/No-Go.
- evidência de rollout de produção também pertence a `accounts` como orquestração operacional.
- health de `EmailLog` continua sendo dado de `notifications`; `accounts` apenas consome o snapshot para Go/No-Go.
- métricas de owner access pertencem a `accounts`, mas podem agregar contagens de `EmailLog` owner access de `notifications`.
- o endpoint de métricas não deve ficar sob `/ops/`, para não depender do gate que monitora.
- rate limiting de login owner/admin pertence a `accounts.application`.
- a proteção deve permanecer no fluxo owner/admin e não ser reaproveitada implicitamente para customer login.
- política de sessão owner/admin pertence a `accounts.application`.
- views não devem decidir duração de sessão; apenas repassam a intenção `remember_me`.
- outros módulos não devem interpretar diretamente os marcadores internos `hubx_owner_session_*`.
- matriz de roles/permissões administrativas pertence a `accounts.application.admin_permissions`.
- helpers de interface para extrair role/permissão de `request.owner_user` pertencem a `accounts.interfaces.admin_rbac`.
- módulos operacionais podem consultar esse helper para renderizar actions, mas writes sensíveis devem continuar validando permissão no command service dono.
- writes administrativos de `customers`, `orders` e `shipping` devem exigir `tenant_id` resolvido e role explícita com `customers.manage`, `orders.manage` ou `shipping.manage`; compatibilidade de leitura sem role não autoriza mudança de estado.
- o cockpit `/ops/` pode personalizar navegação usando permissões de `accounts`, mas não deve criar regras próprias de autorização fora dessa matriz.
- enforcement HTTP granular de `/ops/` pertence a `accounts.interfaces.middleware`.
- módulos operacionais não devem implementar middleware próprio de RBAC para `/ops/`; devem manter validação de writes nos command services.
- permissões de navegação/leitura agora também podem proteger URL direta quando o gate `/ops/` está ativo.
- readiness de produção do RBAC granular pertence a `accounts.application.ops_rbac_production_readiness_queries`.
- o comando de readiness não deve alterar env, roles, usuários ou tenants; ele apenas emite evidência Go/No-Go.
- evidência de ativação staging do RBAC granular pertence a `accounts.application.ops_rbac_staging_evidence_queries`.
- o comando de evidência de staging apenas compõe preflight/readiness, checklist manual e rollback; ele não altera ambiente nem substitui validação real de staging.
- evidência de ativação production do RBAC granular pertence a `accounts.application.ops_rbac_production_activation_evidence_queries`.
- o comando de evidência production pode consumir health de notifications via rollout, mas não deve alterar `EmailLog`, provider, env ou roles.
- monitoramento pós-produção do RBAC pertence a `accounts.application.ops_rbac_post_production_monitoring_queries`.
- o snapshot pós-produção pode ler `AuditLog` e `EmailLog`, mas não deve executar rollback, alterar estado ou reprocessar notificações.
- closure de produção do RBAC pertence a `accounts.application.ops_rbac_production_closure_queries`.
- o closure apenas agrega evidências já existentes; ele não deve virar executor de rollout, rollback, IAM ou exportação formal de auditoria.
- contrato/readiness de MFA/SSO owner/admin pertence a `accounts.application.owner_mfa_sso_readiness_queries`.
- MFA futuro deve ser aplicado dentro do boundary de login owner/admin antes da sessão efetiva.
- SSO futuro deve resolver identidade externa para `User` Django e `OwnerUser` ativo no mesmo tenant; nenhum módulo externo deve criar sessão owner diretamente.
- audit continua dono dos registros persistidos, mas accounts decide quando registrar eventos owner access.
- enrollment de MFA owner/admin pertence a `accounts.models.OwnerMfaFactor` e `accounts.application.owner_mfa_enrollment_queries`.
- fatores MFA devem sempre pertencer ao mesmo tenant do `OwnerUser`; nenhum provider externo deve gravar fator diretamente fora de application service de `accounts`.
- mutações de enrollment MFA pertencem a `accounts.application.owner_mfa_enrollment_commands`.
- challenge de MFA owner/admin pertence a `accounts.application.owner_mfa_challenge_commands`.
- commands de MFA devem registrar `AuditLog`, mas não devem autenticar owner nem criar sessão.
- verificação de challenge pode marcar fator como verificado, mas enforcement no login continua boundary separada do fluxo owner/admin.
- surface admin de MFA pertence a `accounts.interfaces.owner_views`, mas deve permanecer fina e delegar leituras/mutações para `accounts.application`.
- readiness de break-glass e enforcement MFA pertence a `accounts.application`; nenhum módulo externo deve decidir bypass ou obrigatoriedade de MFA.
- enforcement MFA de login owner/admin pertence a `accounts.application.owner_login_commands` e `accounts.interfaces.views`.
- customer login não herda enforcement MFA owner/admin implicitamente.
- rollback de enforcement MFA deve ser controlado por setting, não por alteração de dados ou remoção de fatores.
- recovery codes MFA pertencem a `accounts.models.OwnerMfaRecoveryCode` e `accounts.application.owner_mfa_recovery_code_commands`.
- recovery codes nunca devem ser persistidos ou auditados em texto claro; apenas a saída operacional de geração pode exibir o valor uma única vez.
- resolução de `secret_reference` TOTP pertence a `accounts.application.owner_mfa_secret_storage`.
- login/challenge não devem ler segredo TOTP diretamente sem passar pelo resolver de storage.
- referências externas `ref:<path>` não devem ser consideradas resolvidas sem adapter/provider explícito.
- adapters de provider de segredo MFA pertencem a `accounts.infrastructure.owner_mfa_secret_providers`.
- readiness pode informar provider/referência/status, mas nunca deve imprimir o valor do segredo.
- plano de migração de segredo TOTP pertence a `accounts.application.owner_mfa_totp_secret_migration_plan_queries`.
- plano de migração não deve mover segredo nem atualizar `secret_reference`; execução deve ser trilha separada e controlada.
- execução de migração de segredo TOTP pertence a `accounts.application.owner_mfa_totp_secret_migration_commands`.
- execução só pode atualizar `OwnerMfaFactor.secret_reference` depois que o provider externo resolver o `target_ref` e o valor conferido for equivalente ao segredo local atual.
- comandos de migração não devem copiar segredo para provider externo, imprimir segredo, nem alterar settings como `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`.
- readiness de aposentadoria do fallback local/plain pertence a `accounts.application.owner_mfa_local_secret_retirement_queries`.
- readiness de retirement pode recomendar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`, mas não deve alterar env/settings nem migrar fatores.
- evidência de execução da aposentadoria local/plain pertence a `accounts.application.owner_mfa_local_secret_retirement_execution_queries`.
- evidência before/after pode validar setting atual e storage, mas não deve fazer deploy, reiniciar processo, alterar env/settings ou escrever em `OwnerMfaFactor`.
- health monitoring do provider MFA pertence a `accounts.application.owner_mfa_provider_health_queries`.
- monitoring pode reportar status/sinais/contagens por tenant, mas não deve imprimir segredo, fazer retry automático, alterar provider/env ou autenticar owner.
- métricas Prometheus de health do provider MFA pertencem a `accounts.application.owner_mfa_provider_health_metrics_queries` e `accounts.interfaces.views`.
- métricas devem usar labels de baixa cardinalidade e não devem incluir owner, factor, segredo ou reference path completo.
- closure da trilha de provider health MFA pertence a `accounts.application.owner_mfa_provider_health_closure_queries`.
- closure apenas agrega health e presença de artefatos de observabilidade; não deve ativar Prometheus/Grafana, alterar env/settings ou executar rollback.
- readiness para aposentadoria do código local/plain pertence a `accounts.application.owner_mfa_local_secret_code_retirement_queries`.
- essa readiness pode listar superfícies de código e recomendar execução futura, mas não deve remover suporte `plain:`, alterar dados ou desligar rollback operacional.
- execução de aposentadoria do default local/plain pertence a `accounts.application.owner_mfa_local_secret_code_retirement_execution_queries`.
- execução pode endurecer defaults de settings e emitir evidência, mas rollback deve continuar por env explícito e parsing local só deve ser removido após sweep global.
- sweep global de dados legados MFA pertence a `accounts.application.owner_mfa_legacy_data_global_sweep_queries`.
- sweep global deve ser read-only, agregar por tenant e não expor owner, factor, segredo ou reference path completo.
- review de remoção do parser local/plain pertence a `accounts.application.owner_mfa_local_secret_parser_removal_queries`.
- essa review pode montar plano e rollback de deploy, mas não deve remover parser, alterar dados ou tratar env rollback como suficiente após a remoção.
- execução de remoção do parser local/plain pertence a `accounts.application.owner_mfa_local_secret_parser_removal_execution_queries` e `accounts.application.owner_mfa_secret_storage`.
- após a execution, `plain:` e valores legados sem `ref:` devem ser tratados como `unsupported-local` sem retornar segredo; comandos/readiness podem reportar blocker, mas não devem expor secret material.
- review de provider Vault/KMS para MFA pertence a `accounts.application.owner_mfa_vault_kms_provider_review_queries`.
- essa review pode escolher contrato/target e compor health/parser removal, mas não deve chamar Vault/KMS real, alterar env/settings, migrar refs ou imprimir segredo.
- contrato técnico de adapter Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_adapter_contract_queries`.
- esse contrato pode definir settings, erros e testes esperados, mas a implementação de chamadas externas deve permanecer em `accounts.infrastructure.owner_mfa_secret_providers`.
- skeleton de adapter Vault/KMS pertence a `accounts.infrastructure.owner_mfa_secret_providers`.
- evidência de execution do skeleton pertence a `accounts.application.owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries` e não deve escrever fatores, chamar SDK real, cachear segredo ou fazer fallback automático para `env`.
- readiness evidence do provider Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_readiness_evidence_queries`.
- essa evidence pode compor skeleton e health closure por tenant, mas não deve ativar staging, mudar env/settings, exportar auditoria formal ou imprimir segredo.
- review de canário staging Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_staging_canary_queries`.
- essa review pode emitir checklist manual, preflight e rollback, mas não deve autenticar owner, criar sessão, alterar env/settings, chamar SDK real ou coletar código TOTP.
- evidência declarativa do canário staging Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_staging_canary_evidence_queries`.
- essa evidence pode registrar resultados manuais informados por flags, mas não deve automatizar browser/login, criar sessão, alterar fatores, escrever AuditLog ou coletar segredo/código TOTP.
- contrato do adapter real Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_real_adapter_contract_queries`.
- esse contrato pode exigir evidência de canário e confirmações operacionais, mas não deve instalar SDK, chamar provider real, alterar settings/env, migrar segredo ou trocar o skeleton.
- skeleton real/mocável do adapter Vault/KMS pertence a `accounts.infrastructure.owner_mfa_secret_providers`.
- evidência de execution do skeleton real pertence a `accounts.application.owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries` e não deve instalar SDK, usar credenciais reais, escrever segredo, cachear segredo ou fazer fallback automático para `env`.
- review de dependência SDK Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_sdk_dependency_review_queries`.
- essa review pode definir pacotes, imports opcionais, contratos de falha, testes e rollback, mas não deve instalar dependências, importar SDK em module load, chamar provider real, alterar env/settings ou expor segredo.
- execução do branch SDK Vault/KMS pertence a `accounts.infrastructure.owner_mfa_secret_providers` e a evidência pertence a `accounts.application.owner_mfa_vault_kms_provider_sdk_adapter_execution_queries`.
- essa execução pode validar import lazy e resposta mocável do adapter SDK, mas não deve exigir SDK no startup, chamar endpoint externo real, carregar credencial real, escrever fatores ou fazer fallback automático para `env`.
- review de endpoint real Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_real_endpoint_review_queries`.
- essa review pode escolher Hashicorp Vault como primeiro endpoint, definir settings/auth/path/timeout e blockers, mas não deve chamar `hvac`, carregar token/AppRole, criar secrets, escrever fatores ou imprimir path completo.
- execução do endpoint real Hashicorp Vault pertence a `accounts.infrastructure.owner_mfa_secret_providers` e a evidência pertence a `accounts.application.owner_mfa_hashicorp_vault_real_endpoint_execution_queries`.
- essa execução pode chamar `hvac` de forma lazy quando explicitamente habilitada, mas não deve instalar dependência, criar/migrar secrets, imprimir token/role secret/path completo ou reativar fallback local/plain.
- evidência de smoke staging Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_staging_smoke_evidence_queries`.
- essa evidência pode agregar resultado manual de smoke/rollback/redaction/health, mas não deve automatizar login, criar sessão, alterar fatores, criar secrets no Vault, chamar rollback ou exportar evidência formal.
- readiness de produção do provider Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_production_readiness_queries`.
- essa readiness pode consolidar smoke, health, runbook, monitoring e rollback em Go/No-Go, mas não deve alterar flags/env, executar deploy, chamar rollback, criar secrets ou exportar evidência formal.
- gate de produção Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_production_gate_queries`.
- esse gate pode definir ativação por tenant, ordem de rollout, flags esperadas, plantão e rollback window, mas não deve alterar flags/env, executar deploy/restart, criar secrets, ativar produção ou chamar rollback.
- evidência de ativação production Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_provider_production_activation_evidence_queries`.
- essa evidência pode consolidar resultados declarados pós-deploy, probe, login/challenge, health e redaction, mas não deve executar deploy/restart, alterar flags/env, chamar rollback, criar secrets ou exportar evidência formal.
- monitoramento pós-ativação Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_post_activation_monitoring_queries`.
- esse monitoring pode classificar HEALTHY/WATCH/ROLLBACK a partir de sinais declarados, mas não deve executar rollback, expandir tenants, alterar flags/env, criar incidentes ou exportar evidência formal.
- closure production Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_production_closure_queries`.
- esse closure pode compor monitoring, registrar riscos residuais e recomendar expansão, mas não deve executar rollback, expandir tenants, alterar flags/env, acessar secrets ou tratar evidence do tenant canário como autorização global.
- review de expansão Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_queries`.
- essa review pode validar tenants-alvo e guardrails de expansão, mas não deve ativar provider, alterar flags/env, criar secrets, executar rollback ou reutilizar evidence do canário como evidência dos targets.
- evidência de expansão Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries`.
- essa evidência pode registrar confirmations declarativas por target tenant, mas não deve ativar flags/env, executar rollback, chamar expansão global, criar secrets ou expor path/token/segredo.
- monitoramento pós-expansão Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries`.
- esse monitoring pode classificar sinais do target e recomendar próximo ciclo, mas não deve liberar próximo tenant automaticamente, alterar flags/env, executar rollback ou criar incidentes.
- review do próximo tenant Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_next_tenant_expansion_queries`.
- essa review pode decidir READY/PAUSED/BLOCKED para cadência, mas não deve ativar o próximo tenant, alterar flags/env, executar rollback, criar secrets ou pular review/evidence/monitoring do próximo ciclo.
- closure de cadência Hashicorp Vault pertence a `accounts.application.owner_mfa_hashicorp_vault_expansion_cadence_closure_queries`.
- esse closure pode consolidar decisão, riscos, arquivo de evidências e próximos tracks, mas não deve ativar tenants, alterar flags/env, executar rollback, exportar evidência formal ou acessar secrets.
- review de runbook de rotação Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_rotation_runbook_queries`.
- essa review pode listar passos de rotação/rollback e validar readiness operacional, mas não deve gerar token/AppRole, atualizar secret/configuração, alterar flags/env, executar rotação/rollback ou expor material sensível.
- evidência de rotação Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_rotation_evidence_queries`.
- essa evidência pode registrar confirmations pós-execução e evidence pack redigido, mas não deve gerar/revogar credencial, atualizar secret/configuração, executar rollback ou expor token/secret/path.
- monitoramento pós-rotação Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_post_rotation_monitoring_queries`.
- esse monitoring pode classificar sinais pós-rotação e orientar rollback/closure, mas não deve restaurar credencial, retomar expansão automaticamente, alterar flags/env ou executar rollback.
- closure de rotação Vault/KMS pertence a `accounts.application.owner_mfa_vault_kms_rotation_closure_queries`.
- esse closure pode encerrar a rotação e recomendar export/retomada, mas não deve exportar evidência formal, restaurar credencial, retomar expansão automaticamente, alterar flags/env ou executar rollback.
- closure final da trilha MFA owner/admin pertence a `accounts.application.owner_mfa_track_closure_queries`.
- esse closure pode consumir a closure de evidência MFA de `audit` e consolidar decisão operacional, mas não deve reimprimir/exportar evidência, alterar `AuditLog`, ativar enforcement/provider/tenant, alterar flags/env ou executar rollback.
- re-seleção de ROI de segurança pertence a `accounts.application.security_roi_reselection_queries`.
- essa review pode compor a closure MFA e recomendar próxima trilha, mas não deve implementar API keys, alterar autenticação, ativar provider/tenant/enforcement, escrever `AuditLog` ou reimprimir evidência auditável.
- governança inicial de API keys pertence a `api_keys.application.api_key_governance_foundation_queries`.
- essa review pode definir contrato de modelo, hash, escopos, revogação, auditoria, last-used e rate limit, mas não deve criar modelo/migration, gerar segredo real, autenticar requests, criar API pública ou UI admin.
- modelo e commands mínimos de API keys pertencem a `api_keys.models.ApiKey` e `api_keys.application.api_key_commands`.
- criação/revogação podem registrar `AuditLog`, mas não devem autenticar requests, criar API pública, expor hash, persistir segredo claro ou permitir revogação cross-tenant.
- contrato runtime de autenticação por API key pertence a `api_keys.application.api_key_runtime_authentication_contract_queries`.
- skeleton runtime de autenticação por API key pertence a `api_keys.application.api_key_runtime_authentication`.
- review do adapter DRF de API keys pertence a `api_keys.application.api_key_drf_authentication_adapter_review_queries`.
- adapter DRF mínimo de API keys pertence a `api_keys.interfaces.authentication`.
- review do primeiro endpoint público por API key pertence a `api_keys.application.api_key_public_endpoint_pilot_review_queries`.
- autenticação runtime futura deve validar `tenant_id + prefix`, hash do segredo completo, status ativo e escopo mínimo antes de entregar acesso a qualquer endpoint público.
- API key não define tenant por conta própria; tenant continua sendo resolvido pelo ciclo de request/subdomínio.
- falhas runtime podem emitir `api_key.auth_failed`, mas sem header completo, segredo claro, hash ou material sensível em payload/log.
- o skeleton runtime pode retornar uma `rate_limit_key` declarativa, mas não deve implementar rate limiter real nem liberar endpoint público por conta própria.
- adapter DRF futuro deve ser opt-in por view/surface e não deve ser adicionado globalmente em `DEFAULT_AUTHENTICATION_CLASSES` neste estágio.
- principal DRF futuro não pode expor segredo, hash ou header completo; deve carregar apenas dados mínimos de autorização.
- `HasApiKeyScope` deve negar views sem `required_api_key_scope`, para impedir endpoints programáticos sem escopo explícito.
- primeiro endpoint público recomendado é leitura versionada de catálogo (`GET /api/v1/catalog/products/`) com escopo `read:catalog`; pedidos, clientes, pagamentos e `/ops/` ficam fora do piloto.
- endpoint público futuro não pode aceitar `tenant_id` via query/body; tenant continua vindo do request.
- execução do endpoint público de catálogo pertence a `catalog.application.public_catalog_api_queries` e `catalog.interfaces.public_api_views`, usando autenticação/permission do módulo `api_keys`.
- `GET /api/v1/catalog/products/` deve permanecer read-only, versionado, protegido por `read:catalog` e flag `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED`.
- payload público de catálogo não deve expor estoque bruto, dados de clientes, pedidos, pagamentos, segredo, hash, header ou `tenant_id`.
- review de rate limit para endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_rate_limit_review_queries`.
- rate limit futuro deve usar `tenant + api_key + endpoint`, não IP como substituto de tenant/key.
- evento `api_key.rate_limited` pode ser emitido por throttle futuro, sem segredo, hash ou header completo.
- execução de rate limit por API key pertence a `api_keys.application.api_key_rate_limit` e `api_keys.interfaces.throttling`.
- endpoints públicos devem ativar `ApiKeyRateLimitThrottle` explicitamente; `DEFAULT_THROTTLE_CLASSES` permanece fora do corte.
- review de observabilidade de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_observability_review_queries`.
- métricas futuras de API key pública podem usar `tenant_id`, `endpoint`, `result` e prefixo, mas nunca segredo, hash, header ou valor claro.
- endpoint futuro de métricas deve ser protegido por token de observabilidade, não por API key pública.
- métricas Prometheus de API keys públicas pertencem a `api_keys.application.api_key_public_endpoint_metrics` e `api_keys.interfaces.views.ApiKeyPublicEndpointMetricsView`.
- `/api-keys/metrics/public-endpoints/` deve aceitar somente token de observabilidade; API keys públicas não autenticam esse scrape.
- contrato de dashboard Grafana para endpoints públicos pertence a `api_keys.application.api_key_public_endpoint_dashboard_review_queries`.
- dashboard de API keys públicas deve consumir somente métricas já expostas por `api_keys`, sem importar detalhes internos de `catalog`, `accounts` ou billing.
- labels de dashboard devem permanecer operacionais e de baixa cardinalidade; segredo, hash, header ou valor claro da API key são proibidos.
- artefato Grafana versionado para API keys públicas pertence a `infra/observability/grafana/api-key-public-endpoints-dashboard.json` e não deve introduzir consulta direta a banco, API pública ou módulo de catálogo.
- review de alert rules para endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_alert_rules_review_queries`.
- alertas de API keys públicas devem consumir apenas métricas Prometheus de `api_keys`; não devem consultar banco, audit log diretamente ou identificar API key completa/hash.
- artefato de alert rules para API keys públicas pertence a `infra/observability/prometheus/api-keys-alert-rules.yml` e deve permanecer separado de billing/quotas e Alertmanager real.
- closure de observabilidade de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_observability_closure_queries`.
- closure de observabilidade apenas verifica artefatos e riscos residuais; não deve ativar Prometheus/Grafana/Alertmanager nem alterar settings de ambiente.
- review de rollout produtivo de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_production_rollout_review_queries`.
- rollout review apenas define checklist, evidência e rollback; não deve criar token real, executar chamadas contra produção ou alterar Prometheus/Grafana/Alertmanager.
- evidência de ativação produtiva de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_production_activation_evidence_queries`.
- activation evidence apenas registra sinais sanitizados e referência externa; não deve executar chamadas reais, armazenar token/header/API key ou alterar observabilidade do ambiente.
- review de monitoramento pós-ativação de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_post_activation_monitoring_review_queries`.
- post-activation monitoring review apenas classifica estabilidade e ruído; não deve alterar thresholds, expandir endpoints ou executar rollback diretamente.
- review de expansão de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_expansion_review_queries`.
- expansão recomendada para detalhe público de produto deve ser implementada em `catalog` na query/view pública, reutilizando autenticação, permission, rate limit e observabilidade de `api_keys`.
- endpoints públicos novos não devem abrir pedidos, clientes, pagamentos, operações admin, escopo `read:*`, PII, tenant_id ou estoque bruto.
- review de contrato do endpoint público de detalhe de produto pertence a `api_keys.application.api_key_public_product_detail_endpoint_contract_review_queries`.
- execução do detalhe público de produto deve pertencer a `catalog.application.public_catalog_api_queries` e `catalog.interfaces.public_api_views`, com `api_keys` fornecendo autenticação, escopo, throttle e métricas.
- detalhe público de produto deve filtrar por tenant atual, slug, `status=ACTIVE` e `is_active=True`; não pode fazer fallback global ou expor dados privados de variante.
- execução do endpoint público de detalhe de produto pertence a `catalog.application.public_catalog_api_queries.get_product_detail` e `catalog.interfaces.public_api_views.PublicCatalogProductDetailApiView`.
- detalhe público de produto deve registrar métricas de sucesso com endpoint `catalog.products.detail` e usar flag `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`.
- review de observabilidade do detalhe público de produto pertence a `api_keys.application.api_key_public_product_detail_observability_review_queries`.
- observabilidade do detalhe deve reutilizar métricas, dashboard e alert rules por label `endpoint`; não deve adicionar labels por slug/SKU nem criar artefatos dedicados sem necessidade operacional.
- closure de expansão de endpoints públicos por API key pertence a `api_keys.application.api_key_public_endpoint_expansion_closure_queries`.
- closure de expansão apenas confirma listagem, detalhe e observabilidade; não deve selecionar ou implementar novo endpoint público.
- closure de governança de API keys pertence a `api_keys.application.api_key_governance_closure_queries`.
- governance closure apenas agrega artefatos, decisões e riscos residuais; não deve criar novo endpoint, alterar billing/quotas, ativar ambiente real ou exportar segredo/hash/header/API key.
- re-seleção ROI sistêmica pós-governança de API keys pertence a `api_keys.application.api_key_system_roi_reselection_queries`.
- system ROI re-selection apenas classifica candidatos e recomenda próxima abordagem; não deve criar endpoints, quotas, cobrança, UX admin, runbook produtivo ou exemplos com material sensível.
- review de documentação/onboarding de parceiros pertence a `api_keys.application.api_key_partner_onboarding_documentation_review_queries`.
- onboarding de parceiros pode documentar endpoints públicos já existentes, escopo, erros, rate limit e observabilidade; não deve alterar `catalog`, runtime auth, billing, quotas, admin UX, endpoints ou credenciais reais.
- execution review de documentação de parceiros pertence a `api_keys.application.api_key_partner_documentation_execution_review_queries`.
- documentation execution review pode validar canal, owner, suporte, template de smoke e change control; não deve publicar documento, enviar credencial, executar smoke real, alterar runtime ou definir termos comerciais.
- evidência de publicação da documentação de parceiros pertence a `api_keys.application.api_key_partner_documentation_publication_evidence_queries`.
- publication evidence pode registrar versão, canal, audiência, tenant reference e referência de evidência sanitizada; não deve armazenar credencial, header, token, screenshot sensível, executar smoke real ou ativar runtime.
- closure de onboarding de parceiros pertence a `api_keys.application.api_key_partner_onboarding_closure_queries`.
- partner onboarding closure apenas consolida documentação, pacote, evidência, riscos residuais e deferrals; não deve ativar parceiro, criar quota/billing, abrir endpoint ou executar smoke real.
- re-seleção ROI pós-onboarding pertence a `api_keys.application.api_key_post_onboarding_roi_reselection_queries`.
- post-onboarding ROI re-selection apenas classifica candidatos após closure; não deve executar smoke, criar credencial, ativar parceiro, abrir endpoint, alterar quota/billing ou mudar autenticação.
- contrato de smoke de ativação de parceiro pertence a `api_keys.application.api_key_partner_activation_smoke_contract_queries`.
- smoke contract pode registrar referências sanitizadas de parceiro/tenant/ambiente/slug/evidência e escopo do smoke; não deve executar request, armazenar credencial, alterar runtime, abrir endpoint, criar billing/quotas ou publicar material sensível.
- contrato de quotas comerciais pertence a `api_keys.application.api_key_commercial_quotas_contract_queries`.
- commercial quotas contract pode definir dimensões, janela, limite padrão, comportamento de excesso, visibilidade admin e observabilidade; não deve criar modelo, enforcement runtime, cobrança, plano, endpoint novo ou material sensível nesta wave.
- modelo e commands mínimos de quotas comerciais pertencem a `api_keys.models.ApiKeyQuota`, `api_keys.models.ApiKeyQuotaUsage` e `api_keys.application.api_key_quota_commands`.
- enforcement runtime de quota pertence a `api_keys.application.api_key_quota_enforcement` e deve ser chamado por `api_keys.interfaces.throttling` depois do rate limit técnico.
- quotas comerciais não devem importar `subscriptions`, criar cobrança, validar plano ou abrir endpoint público novo.
- visibilidade admin de quotas pertence a `api_keys.application.api_key_quota_queries` e `api_keys.interfaces.ops_views`; deve expor apenas prefixo, quota e uso agregado, nunca segredo/hash/header.
- closure de quotas comerciais pertence a `api_keys.application.api_key_commercial_quotas_closure_queries`.

## Boundary de exportação de evidência auditável

- exportação formal de `AuditLog` pertence a `audit.application.audit_evidence_export_queries`.
- módulos como `accounts`, `orders`, `coupons`, `pages` e `reviews` devem registrar eventos por `audit.application.audit_log_commands`, não exportar suas próprias evidências diretamente.
- export tenant-owned exige `tenant_id`; export platform-scope exige opt-in explícito.
- export não deve alterar logs, reprocessar eventos, executar rollback ou consultar dados internos dos módulos de origem.
- metadata em export é opt-in para reduzir exposição acidental.
- surface HTTP de exportação pertence a `audit.interfaces` e deve apenas adaptar a request para `audit.application.audit_evidence_export_queries`.
- export HTTP sob `/ops/audit/` não deve habilitar platform-scope nem bypassar o gate `audit.view`.
- closure da trilha de evidência auditável pertence a `audit.application.audit_evidence_closure_queries`.
- closure de audit não deve virar storage, assinatura, redaction avançado ou IAM.
- review de export de evidência MFA owner/admin pertence a `audit.application.owner_mfa_audit_evidence_export_review_queries`.
- essa review pode amostrar `AuditLog` tenant-scoped com `module=accounts` e decidir Go/No-Go para export, mas não deve consultar tabelas internas de `accounts`, exportar artefato final, incluir metadata sensível por padrão ou habilitar platform-scope.
- execution de export de evidência MFA owner/admin pertence a `audit.application.owner_mfa_audit_evidence_export_execution_queries`.
- essa execution pode gerar JSONL/CSV tenant-scoped a partir de `AuditLog`, mas não deve incluir metadata, habilitar platform-scope, assinar/armazenar artefato, registrar novo `AuditLog` ou consultar tabelas internas de `accounts`.
- closure de export de evidência MFA owner/admin pertence a `audit.application.owner_mfa_audit_evidence_export_closure_queries`.
- esse closure pode validar entrega, retenção, storage decision e riscos residuais, mas não deve reimprimir o export, assinar/armazenar artefato, alterar `AuditLog`, habilitar platform-scope ou consultar tabelas internas de `accounts`.
