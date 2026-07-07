# DECISIONS.md

## 2026-07

### Decisão: MVP segue como release candidate funcional, produção real permanece NO-GO
Decisão:
- em 2026-07-06, o MVP está apto para validação controlada como release candidate local/staging.
- produção real permanece `NO-GO` até fechar evidências reais de pagamentos, notificações, shipping, observabilidade, rollback drill e aceite explícito de risco residual.
- `npm run test:visual`, suíte Django, smokes locais e gates de accounts/RBAC são critérios obrigatórios antes de nova decisão.
- flags produtivas devem ser ativadas de forma controlada por tenant: `HUBX_OPS_AUTH_GATE_ENFORCED=1`, signup público apenas com token operacional e tenants novos em `maintenance_mode`.

Motivo:
- evitar liberar tráfego real sem provider de pagamento/e-mail/frete comprovado, runbook testado e dono de incidente confirmado.
- permitir avanço seguro do pacote técnico sem mascarar lacunas externas de produção.

Guardrail:
- não marcar Go sem `payments_production_readiness`, `notification_production_delivery`, `shipping_quote_productionization` e `system_production_closure` verdes com evidência real.
- não registrar secrets, tokens, payload sensível ou dados financeiros em audit/evidence.
- rollback inicial deve poder desligar signup público, manter tenants em manutenção e desativar rollout de provider.

### Decisão: aquisição pública de plano SaaS cria lead seguro
Decisão:
- `/plans/` é uma superfície pública de aquisição de plano SaaS.
- o POST público cria `SubscriptionAcquisitionLead` em `subscriptions`.
- o lead pode ser revisado em `/ops/platform/acquisitions/`.
- conversão por platform admin cria apenas uma jornada `TenantOnboarding`.
- tenant, owner inicial e `TenantSubscription` só nascem na conclusão explícita do wizard de onboarding.

Motivo:
- evitar provisionamento público automático antes de antifraude, billing provider, verificação de contato e política comercial.
- manter `subscriptions` como dono da intenção comercial e `tenants` como dono da criação de loja.
- preservar isolamento multi-tenant: fluxo público não toca dados tenant-owned de commerce.

Guardrail:
- o fluxo público não cria tenant, owner, assinatura, invoice, pagamento, catálogo, pedido ou sessão de checkout.

### Decisão: signup self-service público fica atrás de feature flag
Decisão:
- `/plans/signup/` é a superfície pública de self-service SaaS.
- a rota só fica disponível com `HUBX_PUBLIC_SIGNUP_ENABLED=1`.
- quando `HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN=1`, o POST exige `HUBX_PUBLIC_SIGNUP_ACCESS_TOKEN` antes de criar qualquer tenant.
- o POST cria `Tenant` ativo em `maintenance_mode`, `TenantSubscription(status=trialing)`, `TenantOnboarding(status=completed)` e `OwnerUser` inicial com senha utilizável.
- tenant em `maintenance_mode` resolve por subdomínio/custom domain, mas storefront/checkout respondem 503; `/accounts/`, `/ops/` e caminhos técnicos continuam disponíveis para configuração.
- `/plans/` permanece como aquisição assistida via `SubscriptionAcquisitionLead`.

Motivo:
- permitir MVP self-service controlado sem ativar billing SaaS recorrente.
- manter a loja recém-criada fechada para configuração antes de publicação.
- preservar a separação entre `OwnerUser` e `Customer` e não criar dados de commerce no signup.

Guardrail:
- o signup self-service não cria customer, catálogo, pedido, pagamento de loja, invoice, domínio customizado ou recurso/cobrança externa no billing provider.
- a assinatura trial pode registrar o provider-alvo de billing SaaS para onboarding operacional, mas nenhuma API externa deve ser chamada nessa etapa.
- e-mails já vinculados a usuário/owner existente devem usar aquisição assistida.
- corrida de slug/subdomínio deve retornar erro de formulário, não 500.
- toda criação deve ser auditada tenant-scoped e manter isolamento por subdomínio.

### Decisão: planos públicos exibem trial de 30 dias com cartão obrigatório
Decisão:
- `SubscriptionPlan` passa a declarar `trial_days`, `requires_payment_method` e `feature_list`.
- os planos comerciais seedados iniciam com `trial_days=30` e `requires_payment_method=True`.
- `/plans/` e `/plans/signup/` exibem 30 dias grátis, cartão obrigatório e preço mensal após o trial.
- `TenantSubscription(status=trialing)` recebe `trial_ends_at` calculado a partir de `started_at + plan.trial_days`.

Motivo:
- responder ao contrato comercial de MVP: loja pode validar por 30 dias antes da cobrança.
- deixar claro para o usuário que cartão é requisito de ativação comercial sem ativar billing SaaS recorrente no MVP.
- manter a fundação de assinatura tenant-scoped pronta para provider futuro sem armazenar dados sensíveis.

Guardrail:
- formulário público não coleta número de cartão, CVV, validade, token de cartão ou dado bancário sensível.
- captura real de payment method deve ocorrer somente em provider seguro de billing SaaS.
- `requires_payment_method` não cria invoice, cobrança recorrente, checkout de assinatura ou enforcement automático.

### Decisão: Asaas é o provider inicial de checkout hospedado e billing SaaS-alvo
Decisão:
- `PAYMENTS_PROVIDER_DEFAULT` passa a apontar para `asaas` em ambientes novos.
- `payments` possui adapter Asaas para criar cliente e cobrança hospedada em `/customers` e `/payments`, usando `ASAAS_API_KEY`, `ASAAS_BASE_URL`, `ASAAS_SANDBOX` e `ASAAS_WEBHOOK_TOKEN`.
- `subscriptions` registra `billing_provider_code`, `billing_provider_label`, `billing_external_reference` e `billing_checkout_url` em `TenantSubscription`.
- `SUBSCRIPTIONS_BILLING_PROVIDER_DEFAULT=asaas` define o provider-alvo da assinatura SaaS.
- Pagar.me permanece como provider alternativo e caminho de refund sandbox-first existente.

Motivo:
- alinhar onboarding ao fluxo comercial atual: lojas recebem pedidos via Asaas primeiro e o billing SaaS também começa preparado para Asaas.
- manter uma interface extensível para incluir outros providers de recebimento/billing depois.
- não armazenar dados de cartão no Hubx Market; coleta e validação ficam no checkout/interface hospedada do provider.

Guardrail:
- nenhuma chave Asaas deve ser versionada; usar apenas variáveis de ambiente e reaproveitar nomes já usados em sandbox quando disponíveis.
- signup público não chama Asaas nem cria cobrança SaaS; ele só registra assinatura trial e provider-alvo.
- pagamento real controlado vale para checkout de pedidos da loja; cobrança recorrente SaaS continua fora do MVP até nova decisão.
- webhooks Asaas devem ser autenticados por token configurado e normalizados em `payment.paid`/`payment.failed` antes de chegar em `orders`.

## 2026-04
### Decisão: nome oficial do produto
- Produto: Hubx Market
- Domínio principal: hubx.market

### Decisão: multi-tenant por subdomínio
Motivo:
- simplicidade
- clareza operacional
- bom encaixe com SaaS de e-commerce

### Decisão: `custom_domain` permanece fora da resolução HTTP por enquanto
Decisão:
- o campo `custom_domain` continua existindo no modelo de `tenants` como readiness de domínio
- a resolução HTTP oficial segue restrita a `subdomain + HUBX_MARKET_ROOT_DOMAIN`
- hosts fora do domínio raiz não devem resolver tenant implicitamente neste estágio

Motivo:
- evitar capacidade “meio ativa” sem regras completas de precedência, unicidade e operação
- manter o contrato multi-tenant explícito e previsível enquanto o sistema endurece suas fronteiras

### Decisão: services tenant-owned devem aceitar `tenant_id` explícito
Decisão:
- query services e command services que operam sobre dados da loja devem aceitar `tenant_id` explícito no boundary
- a camada `interfaces/` deve repassar `request.tenant.id` quando o tenant já estiver resolvido
- inferência por contexto global, “primeiro ativo” ou leitura cross-tenant implícita deve ser tratada como compatibilidade legada, não como contrato principal

Motivo:
- reduzir risco de leitura ou escrita na loja errada
- deixar o comportamento multi-tenant mais previsível entre módulos
- facilitar futuras waves de hardening sem depender de convenções implícitas

### Decisão: compatibilidade global sem tenant vira exceção documentada, não padrão silencioso
Decisão:
- tolerância a `tenant_id=None` só continua aceitável em superfícies legadas de leitura ou fallback operacional explicitamente documentadas
- flows tenant-owned de escrita, checkout, pagamento, retry, reorder e confirmação de pedido devem falhar fechado sem tenant resolvido
- qualquer nova tolerância global precisa ser tratada como exceção consciente, não como default implícito

Motivo:
- separar com clareza legado controlado de risco estrutural real
- evitar que compatibilidade temporária volte a contaminar boundaries já endurecidas
- facilitar aposentadoria gradual do modo global à medida que o sistema amadurece

### Decisão: próximas aposentadorias devem começar por `accounts`, não pelo admin global
Decisão:
- os próximos candidatos naturais de aposentadoria do modo global ficam em `accounts`
- especialmente:
  - `account_page_queries`
  - `account_customer_area_queries`
  - `account_address_commands`
- os fallbacks globais de `Admin Customers`, `Admin Orders` e `Admin Products` permanecem por enquanto

Motivo:
- a área de conta já é mais semanticamente tenant-owned e tende a se beneficiar antes de estados explícitos de ausência
- o admin global ainda mantém valor operacional real e não deve perder compatibilidade antes de um contrato mais claro de plataforma/admin por tenant

### Decisão: primeira aposentadoria em `accounts` deve começar por `account_page_queries`
Decisão:
- a primeira retirada planejada do fallback global em `accounts` deve começar por `account_page_queries`
- ordem sugerida:
  1. `account_page_queries`
  2. `account_customer_area_queries`
  3. `account_address_commands`

Motivo:
- `account_page_queries` é majoritariamente leitura
- concentra auth/overview com menor risco operacional
- não carrega write path nem CRUD sensível
- customer area e address commands ainda têm impacto maior em continuidade e operação da conta

Plano seguro inicial:
- remover primeiro apenas o perfil demo/global de `account_page_queries`
- manter o contrato visual das páginas
- substituir conteúdo demo por estado explícito de ausência, readiness ou onboarding leve
- deixar `account_customer_area_queries` e `account_address_commands` fora da mesma wave

Status:
- a primeira retirada já foi executada em `account_page_queries`
- as páginas continuam renderizando com o mesmo contrato visual, mas sem identidade demo/global pré-preenchida

### Decisão: `account_customer_area_queries` ainda não é a próxima retirada mais segura
Decisão:
- a próxima retirada completa não deve começar ainda por `account_customer_area_queries`
- a customer area continua candidata importante, mas precisa de decomposição adicional antes da aposentadoria do fallback global

Motivo:
- a mudança afetaria ao mesmo tempo:
  - lista de pedidos
  - detalhe do pedido
  - endereços
  - perfil
- isso mistura continuidade de conta, empty states e ausência de tenant em uma única remoção
- o risco operacional é maior do que o da retirada que acabamos de fazer em `account_page_queries`

### Decisão: aposentadoria da customer area deve seguir uma decomposição por superfícies
Decisão:
- a retirada do legado em `account_customer_area_queries` deve acontecer em etapas menores
- ordem recomendada:
  1. fallback global de perfil
  2. fallback global de endereços
  3. fallback global de pedidos
  4. revisão final do modo global residual da customer area

Motivo:
- `profile` é a superfície mais isolada e de menor risco dentro da customer area
- `addresses` tem impacto intermediário e não altera jornada crítica de pedido
- `orders` concentra o maior risco porque mistura histórico, detalhe, retry, hosted payment e guidance operacional
- essa ordem transforma uma aposentadoria “grande demais” em cortes pequenos, verificáveis e reversíveis

Status:
- a primeira etapa já foi executada
- `get_active_profile_context()` e `get_profile_page_data()` não usam mais perfil demo/global
- a customer area agora mostra `missing` para identidade quando não houver `AccountProfile` persistido
- fallbacks globais de pedidos e endereços continuam por enquanto

### Decisão: fallback global de endereços já é o próximo corte seguro na customer area
Decisão:
- a próxima retirada segura em `account_customer_area_queries` deve começar por `get_addresses_page_data()`
- o fallback global de endereços já pode sair antes da trilha de pedidos

Motivo:
- a superfície de endereços é mais isolada
- o template já possui empty state honesto para ausência real
- create/edit/delete possuem fluxo próprio e não dependem de fixture de leitura para continuar operando
- a continuidade da conta ainda pode continuar apoiada no histórico de pedidos enquanto a trilha de `orders` permanece legada

Status:
- essa etapa já foi executada
- `get_addresses_page_data()` não usa mais fallback global
- quando não houver endereços persistidos, a customer area agora responde com vazio explícito e empty state honesto
- a trilha de pedidos continua preservando compatibilidade legada por enquanto

### Decisão: fallback global de pedidos ainda não deve sair inteiro de uma vez
Decisão:
- `get_orders_page_data()` e `get_order_detail_page_data()` ainda não devem perder o modo global na mesma wave
- a aposentadoria de `orders` precisa de decomposição adicional

Motivo:
- a trilha de pedidos na customer area já carrega:
  - retenção e continuidade
  - checkout completion feedback
  - reorder lite
  - payment retry
  - hosted payment continuation
  - recovery guidance e trilha operacional
- remover o fallback global agora apagaria ao mesmo tempo histórico, detalhe e ações de retomada

Próxima decomposição recomendada:
1. revisar `orders list` separadamente
2. só depois revisar `order detail`
3. deixar o detalhe como último corte, por concentrar o maior risco operacional

### Decisão: `orders list` já é o próximo corte seguro dentro da customer area
Decisão:
- a próxima retirada segura no eixo de pedidos deve começar por `get_orders_page_data()`
- `get_order_detail_page_data()` continua ficando para depois

Motivo:
- a lista é majoritariamente leitura
- o template já possui empty state honesto para ausência real
- o maior acoplamento com recovery, hosted payment, retry e guidance operacional continua concentrado no detalhe

Leitura prática:
- o próximo passo seguro na aposentadoria do legado de pedidos deixa de ser uma revisão ampla
- passa a ser a execução da retirada do fallback global da **lista de pedidos**

Status:
- essa etapa já foi executada
- `get_orders_page_data()` e a view `account-orders` deixam de reutilizar fallback global de pedidos
- quando não houver histórico persistido, a lista agora responde com `missing` e empty state honesto
- `get_order_detail_page_data()` continua ficando para depois, preservando compatibilidade legada no detalhe

### Decisão: `order detail` ainda não é o próximo corte seguro
Decisão:
- `get_order_detail_page_data()` ainda não deve perder o fallback global nesta etapa

Motivo:
- o detalhe continua concentrando:
  - confirmação inicial de checkout
  - reorder lite
  - payment retry
  - hosted payment continuation
  - trilha operacional de pagamento
  - guidance de stale pending, drift e recovery
- isso faz do detalhe uma boundary operacional, não apenas uma leitura de apresentação

Leitura prática:
- depois da retirada da lista, o legado remanescente em `orders` ficou bem concentrado
- mas ele ainda está carregando regras e sinais sensíveis demais para um corte simples

### Decisão: `order detail` deve ser decomposto por camadas antes de qualquer retirada
Decisão:
- a aposentadoria do legado em `get_order_detail_page_data()` deve acontecer em subcortes menores
- ordem recomendada:
  1. leitura base do detalhe
  2. `confirmation_mode` / handoff do checkout
  3. `reorder lite`
  4. recovery e pagamento
  5. retirada residual do fallback global

Motivo:
- o detalhe hoje mistura leitura, feedback de jornada, ações comerciais e recovery operacional na mesma boundary
- essa decomposição permite isolar primeiro o que é mais passivo e previsível
- o bloco de pagamento continua por último por concentrar hosted payment, retry, confirmação e trilha operacional

Leitura prática:
- o próximo passo seguro deixa de ser “aposentar o detalhe”
- passa a ser escolher o **primeiro subcorte do detalhe** com menor risco

### Decisão: o primeiro subcorte seguro do `order detail` é o payload estrutural do pedido
Decisão:
- a primeira camada segura do detalhe deve ser tratada como **payload estrutural do pedido**
- esse subcorte inclui:
  - resumo principal
  - status atual
  - itens
  - totais
  - timeline básica do pedido
- esse subcorte não inclui ainda:
  - copy enriquecida (`page_description`, `page_meta`, `summary_subtitle`, `summary_note`)
  - `confirmation_mode`
  - CTAs de reorder/retry/hosted payment
  - trilha operacional de `PaymentAttempt`
  - alerts de pending/drift/recovery

Motivo:
- a narrativa do detalhe já está bastante contaminada por jornada, retomada e operação
- o payload estrutural continua sendo a parte mais previsível e menos acoplada para um primeiro corte

Leitura prática:
- o próximo passo seguro não é remover toda a leitura do detalhe
- é revisar/recortar primeiro a parte estrutural, deixando a narrativa enriquecida e o recovery para depois

### Decisão: o primeiro corte executável do `order detail` deve começar por extração estrutural interna
Decisão:
- a próxima execução segura no detalhe deve começar por uma **extração estrutural interna**
- passos recomendados:
  1. isolar o payload estrutural do pedido
  2. preservar o contrato atual do template
  3. manter copy enriquecida e capability flags fora desse primeiro corte
  4. manter recovery e trilha operacional totalmente fora desta etapa

Motivo:
- isso permite separar estrutura persistida de narrativa e operação sem mexer cedo demais na jornada
- reduz o risco de regressão em hosted payment, retry, reorder e feedback de checkout

Leitura prática:
- a próxima wave de execução do detalhe deve ser mais um refactor orientado a boundary do que uma remoção direta de comportamento

Status:
- essa primeira extração estrutural já foi executada
- o payload estrutural do detalhe agora nasce em um bloco próprio dentro de `account_customer_area_queries`
- o contrato visual e os nomes já consumidos no template foram preservados
- narrativa enriquecida, handoff e recovery continuam fora deste primeiro corte

### Decisão: o próximo subcorte seguro do `order detail` parece ser o handoff de confirmação do checkout
Decisão:
- depois da extração estrutural, o próximo subcorte seguro do detalhe deve revisar o `confirmation_mode`

Motivo:
- ele entra por um gate explícito (`result=checkout-completed`)
- altera uma fatia localizada da narrativa do detalhe
- não depende da mesma carga de hosted payment, retry, `PaymentAttempt` e recovery operacional que permanece no bloco mais sensível

Leitura prática:
- o próximo passo seguro no detalhe já não parece ser payment recovery
- parece ser isolar melhor o handoff de confirmação inicial do checkout

### Decisão: o handoff de confirmação do checkout deve ser isolado antes de qualquer retirada
Decisão:
- a próxima execução segura nesse eixo deve começar por uma extração dedicada do confirmation payload
- o gate `result=checkout-completed` deve permanecer explícito na view

Motivo:
- isso separa o feedback inicial de checkout da narrativa residual do detalhe
- evita misturar handoff de jornada com recovery de pagamento ou sinais operacionais

Leitura prática:
- o próximo passo seguro agora não é remover o handoff
- é isolá-lo melhor como boundary própria dentro do detalhe

Status:
- essa extração do handoff já foi executada
- o confirmation payload agora nasce em um bloco próprio dentro de `account_customer_area_queries`
- o gate explícito `result=checkout-completed` foi preservado
- recovery e sinais de `payments` continuam fora desse corte

### Decisão: `reorder lite` parece ser o próximo subcorte seguro do `order detail`
Decisão:
- depois do payload estrutural e do handoff de confirmação, o próximo subcorte seguro do detalhe deve revisar/isolar o boundary de `reorder lite`

Motivo:
- o CTA nasce de sinais locais e explícitos do payload
- a ação entra por `POST` explícito no `order detail`
- o write real é delegado a `checkout_reorder_commands.bootstrap_from_order(...)`
- ele não depende do mesmo bloco sensível de `payments`, `PaymentAttempt` e recovery operacional

Leitura prática:
- o próximo passo seguro nesse eixo não parece ser retry nem hosted payment
- parece ser separar melhor a capability de recompra leve antes de tocar no restante do legado residual

### Decisão: o `reorder lite` deve ser isolado antes de qualquer retirada residual do `order detail`
Decisão:
- a próxima execução segura nesse eixo deve começar por uma extração dedicada do payload de `reorder lite`
- a action boundary `action_type=reorder_lite` deve permanecer explícita na view

Motivo:
- isso separa a capability comercial de recompra leve da narrativa residual do detalhe
- preserva `accounts` como superfície de jornada e `checkout` como dono do bootstrap da nova sessão
- evita misturar esse subcorte com retry, hosted payment ou recovery operacional

Leitura prática:
- o próximo passo seguro agora não é remover `reorder lite`
- é isolá-lo melhor como boundary própria antes de tocar no bloco mais sensível restante

Status:
- essa extração do `reorder lite` já foi executada
- o payload agora nasce em um bloco próprio dentro de `account_customer_area_queries`
- a action boundary explícita na view foi preservada
- o write real continua delegado a `checkout_reorder_commands.bootstrap_from_order(...)`

### Decisão: `payment retry` ainda não é o próximo subcorte seguro do `order detail`
Decisão:
- depois de `reorder lite`, o eixo de `payment retry` ainda não deve ser o próximo corte isolado do detalhe

Motivo:
- apesar do CTA local e do `POST` explícito, ele já depende de semântica real de falha de pagamento
- o write segue para `checkout_payment_retry_commands.bootstrap_from_failed_order(...)`
- o bloco conversa diretamente com continuidade de pagamento, retry e guidance de recovery

Leitura prática:
- `payment retry` já está perto demais do boundary de recovery transacional para ser o próximo subcorte seguro
- ele deve continuar depois do bloco de hosted payment / recovery explícito, não antes

### Decisão: `hosted payment` também ainda não é o próximo subcorte seguro do `order detail`
Decisão:
- o eixo de `hosted payment` ainda não deve ser tratado como próximo corte isolado do detalhe

Motivo:
- apesar do CTA local, ele aponta diretamente para a boundary de `payments`
- o bloco depende de `PaymentAttempt` pendente, `attempt_key`, redirect hospedado e feedback de retorno do provider
- isso o coloca dentro do mesmo eixo de continuidade/recovery transacional, e não como simples capability de apresentação

Leitura prática:
- `hosted payment` deve continuar junto do bloco de recovery/payment continuity
- ele não parece um corte seguro anterior ao eixo explícito de recovery

### Decisão: o restante do `order detail` deve ser tratado como recovery block
Decisão:
- depois dos subcortes já isolados, o restante do legado sensível do detalhe deve ser tratado como um único **recovery block**

Motivo:
- o que sobra compartilha a mesma semântica de continuidade e recovery transacional:
  - `payment_progression_*`
  - `payment_retry_*`
  - `hosted_payment_*`
  - `payment_attempt_*`
  - `pending_recovery_*`
  - `order_pending_recovery_*`
- esse bloco já mistura CTA, tentativa de pagamento, drift, stale state e guidance operacional demais para continuar sendo decomposto com segurança por ação individual

Leitura prática:
- a próxima revisão segura não deve buscar “o próximo botão”
- deve revisar esse restante como um boundary único de recovery/payment continuity antes de qualquer retirada residual

### Decisão: o recovery block deve ser decomposto por camadas, não por CTA
Decisão:
- a decomposição segura do recovery block deve seguir esta ordem:
  1. `payment_attempt_*`
  2. `pending_recovery_*` e `order_pending_recovery_*`
  3. `payment_progression_*`, `payment_retry_*` e `hosted_payment_*`
  4. narrativa residual do detalhe

Motivo:
- isso separa leitura passiva, guidance operacional e actions reais de continuidade
- reduz o risco de misturar observabilidade, retry e redirect hospedado numa única extração

Leitura prática:
- o próximo passo seguro nesse eixo deve começar pela leitura operacional passiva do bloco
- actions de pagamento continuam vindo depois

### Decisão: a leitura passiva de `PaymentAttempt` parece ser o próximo subcorte seguro do recovery block
Decisão:
- a próxima revisão/execução segura do recovery block deve começar pelo sub-bloco `payment_attempt_*`

Motivo:
- esse trecho hoje funciona como leitura operacional passiva:
  - título/descrição operacional
  - timeline
  - metadados de tentativa
- ele não dispara retry, redirect hospedado nem bootstrap de nova sessão

Leitura prática:
- o próximo passo seguro do recovery block parece ser isolar primeiro a telemetria passiva da tentativa
- guidance de recovery e actions de pagamento continuam vindo depois

Status:
- essa extração da leitura passiva de `PaymentAttempt` já foi executada
- o payload `payment_attempt_*` agora nasce em um bloco próprio dentro de `account_customer_area_queries`
- a `Trilha do pagamento` preserva o mesmo contrato visual
- guidance e actions do recovery block continuam fora deste corte

### Decisão: o guidance de recovery parece ser o próximo subcorte seguro do recovery block
Decisão:
- depois de `payment_attempt_*`, o próximo subcorte seguro do recovery block deve revisar/isolar:
  - `pending_recovery_*`
  - `order_pending_recovery_*`

Motivo:
- esse trecho hoje funciona como guidance passivo:
  - alertas contextuais
  - recomendação de retomada hospedada
  - sinalização de revisão operacional
- ele não dispara retry, redirect ou bootstrap de nova sessão por si só

Leitura prática:
- o próximo passo seguro do recovery block parece ser isolar o guidance de recovery
- as actions reais de pagamento continuam vindo depois

Status:
- essa extração do guidance de recovery já foi executada
- o payload de `pending_recovery_*` e `order_pending_recovery_*` agora nasce em um bloco próprio dentro de `account_customer_area_queries`
- os alerts da lateral preservam o mesmo contrato visual
- as actions reais de pagamento continuam fora deste corte

### Decisão: o restante das actions deve ser tratado como um único actions block
Decisão:
- depois de `payment_attempt_*` e do guidance de recovery, o restante do detalhe deve ser tratado como um único **actions block** de continuidade de pagamento

Motivo:
- `payment_progression_*`, `payment_retry_*` e `hosted_payment_*` compartilham a mesma surface no `order detail`
- mas cada uma já delega efeitos reais para um boundary diferente:
  - `orders`
  - `checkout`
  - `payments`
- isso deixa esse restante sensível demais para voltar a ser decomposto CTA por CTA com o mesmo ganho de segurança

Leitura prática:
- o que sobra agora não é mais “o próximo botão”
- é um único bloco residual de continuidade de pagamento antes de qualquer retirada final do detalhe

### Decisão: o actions block deve ser decomposto por camadas de boundary
Decisão:
- a decomposição segura do actions block deve seguir esta ordem:
  1. payload declarativo das actions
  2. renderização unificada no detalhe
  3. dispatch transacional agrupado
  4. só depois reavaliação por tipo de boundary externo

Motivo:
- isso separa configuração de UI da execução real
- mantém a surface de jornada estável enquanto o bloco ainda delega efeitos para múltiplos módulos
- evita um refactor precoce dos fluxos mais sensíveis de continuidade de pagamento

Leitura prática:
- o próximo passo seguro nesse eixo parece ser extrair primeiro o payload declarativo das actions
- a separação das actions transacionais continua para depois

Status:
- essa extração do payload declarativo das actions já foi executada
- `payment_progression_*`, `payment_retry_*` e `hosted_payment_*` agora nascem em um bloco próprio dentro de `account_customer_area_queries`
- a renderização continua unificada em `_build_order_detail_actions(...)`
- o dispatch transacional continua agrupado em `AccountOrderDetailView.post(...)`

Decisão:
- depois da extração do payload declarativo, a renderização unificada já parece o próximo subcorte seguro deste bloco

Motivo:
- `_build_order_detail_actions(...)` já atua como surface única de UI
- ela transforma contexto em HTML, links e forms
- mas os efeitos reais continuam delegados para:
  - `AccountOrderDetailView.post(...)`
  - `payments:hosted-redirect`

Leitura prática:
- o próximo passo seguro parece ser isolar melhor a renderização
- o dispatch transacional agrupado continua para depois

Plano:
1. isolar primeiro a renderização declarativa interna do bloco
2. manter `_build_order_detail_actions(...)` como surface única nesta etapa
3. preservar `AccountOrderDetailView.post(...)` e `payments:hosted-redirect` sem mudança
4. só depois reavaliar separação mais fina por tipo de action

Motivo:
- isso separa visualização de execução sem espalhar a journey do detalhe
- mantém a boundary estável enquanto as actions ainda compartilham uma mesma surface

Status:
- essa extração da renderização declarativa já foi executada
- as actions agora passam por itens declarativos internos antes da montagem HTML final
- `_build_order_detail_actions(...)` continua como surface única da view
- o dispatch agrupado permanece inalterado

Decisão:
- o dispatch agrupado ainda não é o próximo subcorte seguro deste bloco

Motivo:
- `reorder_lite` já dispara continuidade real em `checkout`
- `payment_retry` já abre nova sessão de recuperação em `checkout`
- `confirm_payment` já altera lifecycle real em `orders`
- esses fluxos ainda compartilham a mesma jornada de retorno no detalhe

Leitura prática:
- o dispatch deve continuar agrupado por enquanto
- a decomposição atual já é suficiente antes de tentar separar execução real por action

Decisão:
- o legado residual do `order detail` já não parece mais um problema grande de boundary funcional

Motivo:
- payload estrutural, confirmação, `reorder lite`, leitura passiva, guidance e actions já foram melhor isolados
- o que ainda sobra está concentrado principalmente na costura narrativa final do payload:
  - `page_meta`
  - `summary_note`
  - copy combinada de pagamento, tentativa e continuidade

Leitura prática:
- o próximo eixo seguro, se quisermos continuar, deve revisar a narrativa residual
- e não tentar forçar mais uma decomposição artificial de boundary funcional onde ela já não traz tanto retorno

Decisão:
- a narrativa residual do `order detail` deve ser tratada, se necessário, como um pequeno `narrative block`

Motivo:
- `summary_note` e `page_meta` ainda acumulam informação incremental de múltiplas fontes
- isso afeta clareza e previsibilidade do payload final
- mas já não representa um problema forte de ownership entre módulos

Leitura prática:
- o próximo refinamento seguro, se quisermos seguir, é separar melhor a costura narrativa final
- sem reabrir decomposições artificiais do boundary funcional

Plano:
1. isolar primeiro a base narrativa (`summary_note` e `page_meta`)
2. separar depois o enriquecimento de pagamento
3. separar depois o enriquecimento de tentativa
4. manter o handoff de confirmação fora desta etapa

Motivo:
- isso separa copy-base de copy incremental
- mantém o comportamento atual estável
- evita misturar narrativa residual com o bloco de confirmação já isolado

Status:
- a extração da base narrativa já foi executada
- `page_description`, `page_meta`, `summary_subtitle`, `summary_note`, `activity_description` e `return_to_buy_*` agora nascem em um bloco próprio
- enriquecimentos de pagamento, tentativa e confirmação continuam fora desta etapa

Status:
- a extração do enriquecimento narrativo de pagamento já foi executada
- a copy incremental de origem/referência atual do pagamento e o complemento de `page_meta` agora nascem em um helper próprio
- enriquecimento de tentativa e confirmação continuam fora desta etapa

Status:
- a extração do enriquecimento narrativo de tentativa já foi executada
- a copy incremental de status da tentativa, provider, referência externa, sessão de origem e último evento agora nasce em um helper próprio
- o handoff de confirmação continua fora desta etapa

Decisão:
- o bloco de confirmação já está suficientemente separado e não parece exigir novo corte imediato

Motivo:
- `_build_order_detail_confirmation_payload(...)` já nasce em boundary própria
- ele entra por gate explícito de confirmação inicial
- não compete mais com a narrativa principal do detalhe

Leitura prática:
- depois de base, pagamento e tentativa, o eixo narrativo do `order detail` fica estruturalmente bem organizado

Decisão:
- `account_address_commands` deve exigir tenant resolvido para writes e leituras auxiliares sensíveis

Motivo:
- gestão de endereços é fluxo tenant-owned da customer area
- a tolerância global restante nessa boundary já não trazia benefício suficiente para continuar
- a UI deve refletir indisponibilidade real em vez de sinalizar sucesso falso sem contexto válido

Leitura prática:
- com isso, `accounts` fecha sua principal tolerância global de escrita remanescente
- o que sobra agora é legado controlado de leitura global onde isso ainda é deliberado

Decisão:
- a abordagem multi-tenant desta fase pode ser considerada encerrada em `accounts`

Motivo:
- os writes tenant-owned sensíveis já exigem tenant resolvido
- a customer area e o account overview já respeitam tenant quando ele existe
- o residual remanescente está concentrado em compatibilidade deliberada de leitura global, e não em cross-tenant writes ou boundaries quebradas

Leitura prática:
- o próximo trabalho em `accounts` já não precisa ser “mais hardening multi-tenant”
- o que sobra aqui é legado útil e controlado, com valor de compatibilidade maior do que o ganho estrutural de removê-lo agora

Decisão:
- no pós-compra, o próximo investimento de maior retorno deve ser UX de `order detail`, não novo hardening estrutural

Motivo:
- a base funcional já existe e está correta
- o maior gap agora é valor percebido:
  - clareza de status
  - linguagem mais orientada ao cliente
  - próximo passo mais explícito
  - retenção leve no pós-compra

Leitura prática:
- o detalhe do pedido passa a ser a principal superfície de evolução funcional do pós-compra
- a próxima fase deve priorizar confiança, continuidade e leitura rápida para o cliente

Decisão:
- o próximo refinamento funcional do `order detail` deve priorizar **customer milestone language**

Motivo:
- a página já tem:
  - status
  - timeline
  - trilha de pagamento
  - guidance de recovery
- o maior gap agora não é falta de capability
- é a falta de uma sequência mais uniforme e evidente de marcos da jornada do cliente

Leitura prática:
- os marcos já existem de forma parcial:
  - pedido iniciado
  - pagamento confirmado
  - preparação/envio
  - histórico salvo
- o próximo passo de produto deve consolidar esses sinais em uma linguagem mais consistente e mais fácil de escanear
- a trilha operacional continua importante, mas como apoio à jornada principal do cliente, não como protagonista

Decisão:
- a jornada principal do `order detail` passa a ser organizada por uma sequência canônica curta de milestones do cliente

Sequência recomendada:
1. pedido recebido
2. pagamento aprovado
3. pedido em preparação
4. pedido enviado
5. pedido entregue

Motivo:
- reduzir a mistura entre:
  - status operacional
  - guidance transacional
  - leitura da jornada
- deixar a página mais fácil de escanear no pós-compra
- manter a trilha operacional e o recovery como apoio, não como narrativa principal

Leitura prática:
- summary e status card devem reforçar o milestone atual
- timeline deve mostrar progressão e próximo passo
- trilha do pagamento continua separada para suporte, recovery e transparência operacional

Decisão:
- a primeira execução de milestone language no `order detail` deve ficar restrita a **copy e hierarquia visual leve**

Motivo:
- já existe um recorte seguro para mexer em:
  - summary
  - status card
  - labels da timeline
  - handoff de confirmação inicial
- sem tocar em:
  - trilha do pagamento
  - alerts de recovery
  - actions transacionais

Leitura prática:
- o próximo passo funcional pode ser uma wave pequena e de baixo risco
- a trilha operacional continua separada
- a jornada do cliente ganha prioridade visual sem perder suporte e recovery

Decisão:
- a primeira passada de milestone language no `order detail` já pode ser considerada executada com baixo risco

Motivo:
- a mudança ficou restrita a:
  - summary
  - status card
  - labels principais da timeline
  - handoff de confirmação inicial
- sem tocar em:
  - recovery
  - trilha do pagamento
  - dispatch transacional

Leitura prática:
- o `order detail` agora comunica melhor a etapa atual da jornada
- a linguagem do cliente ganhou prioridade
- a camada operacional continua separada e íntegra

Decisão:
- depois do `order detail`, o próximo refinamento funcional do pós-compra deve olhar para a **lista de pedidos como superfície de continuidade**

Motivo:
- a lista já está correta e útil
- mas ainda comunica melhor:
  - histórico salvo
  - retorno ao catálogo
- do que:
  - qual pedido merece atenção agora
  - qual milestone principal cada pedido vive no momento

Leitura prática:
- o próximo ganho de produto na lista não parece ser estrutural
- parece ser priorização de continuidade:
  - melhor row hint
  - melhor resumo por linha
  - hierarquia mais clara do pedido mais relevante do momento

Decisão:
- a próxima evolução da lista de pedidos deve priorizar **continuity prioritization**, não redesign estrutural

Motivo:
- a lista já resolve:
  - histórico
  - busca básica
  - retorno ao detalhe
- o gap atual está em:
  - deixar mais evidente qual pedido merece atenção agora
  - reforçar milestone principal por linha
  - usar `row_hint` como sinal de prioridade, não só de contexto

Leitura prática:
- o próximo passo seguro na lista deve mexer primeiro em copy e taxonomia de hints
- filtros, paginação e estrutura da tabela podem continuar intactos nesta fase

Decisão:
- a primeira passada real na lista de pedidos deve começar por **copy e taxonomia de hints**

Motivo:
- já existe um recorte seguro para mexer em:
  - `page_description`
  - `table_description`
  - `row_hint`
  - resumo factual por linha
- sem tocar em:
  - ordenação
  - filtros
  - paginação
  - estrutura da tabela

Leitura prática:
- a lista pode ganhar continuidade percebida mais forte sem abrir risco estrutural
- o próximo passo de execução deve ser pequeno, reversível e bem focado em linguagem

Decisão:
- a primeira passada real de continuidade na lista de pedidos já pode ser considerada executada com baixo risco

Motivo:
- a mudança ficou restrita a:
  - `page_description`
  - `table_description`
  - `row_hint`
  - resumo curto por linha
- sem tocar em:
  - ordenação
  - filtros
  - paginação
  - estrutura da tabela

Leitura prática:
- a lista agora comunica melhor a etapa principal do pedido
- o cliente consegue perceber com mais rapidez qual pedido merece atenção
- a superfície continua estável e reversível

Decisão:
- depois da lista de pedidos, o próximo refinamento funcional deve olhar para o **account overview como superfície de retenção**

Motivo:
- o overview já reúne bem:
  - resumo da conta
  - pedidos recentes
  - quick links
  - atividade recente
- mas ainda fala mais de readiness e menos de:
  - retorno valioso
  - próximo ponto de atenção
  - motivo claro para voltar

Leitura prática:
- o próximo ganho no overview não parece estrutural
- parece ser enquadramento de retenção:
  - melhor framing do resumo
  - quick links mais intencionais
  - atividade recente mais orientada a retorno

Decisão:
- a próxima evolução do `account overview` deve acontecer como **refinamento de retenção por copy e framing**, não como redesign estrutural

Motivo:
- a página já está:
  - estável
  - útil
  - coerente com a área da conta
- o maior gap agora é de:
  - intenção percebida
  - clareza do retorno
  - motivo para voltar

Escopo recomendado:
- revisar primeiro:
  - `summary framing`
  - `recent orders framing`
  - `quick links intention`
  - `activity card role`
- sem alterar:
  - layout
  - navegação
  - fluxos transacionais

Leitura prática:
- o `account overview` já está pronto para uma wave de **retention copy**
- isso preserva estabilidade e entrega ganho funcional perceptível sem abrir risco estrutural

Decisão:
- a primeira execução de retenção no `account overview` deve começar por **copy de framing**, não por ajustes de estrutura ou profundidade de dados

Motivo:
- já existe um recorte pequeno e seguro para entregar valor percebido
- os melhores candidatos são:
  - `page_description`
  - `summary_subtitle`
  - `quick_links_subtitle`
  - `activity_subtitle`
- esses pontos conseguem melhorar:
  - clareza de retorno
  - intenção da página
  - valor percebido da conta
  sem tocar em:
  - layout
  - tabela de pedidos recentes
  - navegação
  - lógica transacional

Leitura prática:
- o overview deve seguir o mesmo padrão usado antes em:
  - `order detail`
  - `orders list`
- primeiro copy e framing
- depois, se necessário, refinamentos mais profundos

Decisão:
- a primeira execução de retenção no `account overview` deve ficar restrita ao **framing textual do overview**

Escopo executado:
- atualização de:
  - `page_description`
  - `summary_subtitle`
  - `quick_links_subtitle`
  - `activity_subtitle`
- ajuste leve de `summary_content` e `quick_links_content` para o mesmo enquadramento

Motivo:
- esse recorte entrega ganho funcional perceptível sem mexer em:
  - layout
  - tabela de pedidos recentes
  - quick links
  - continuidade transacional

Leitura prática:
- o `account overview` agora comunica melhor:
  - retorno útil
  - próximo ponto de atenção
  - retomada com contexto
- sem abrir risco estrutural na área da conta

Decisão:
- o próximo refinamento do `account overview` deve olhar para **`recent_orders` como bloco de continuidade**, não como mudança estrutural da tabela

Motivo:
- a tabela recente já está funcional e estável
- o maior gap agora é de:
  - framing do bloco
  - hierarquia na célula de status
  - clareza sobre qual pedido merece atenção agora

Escopo recomendado:
- revisar primeiro:
  - framing do bloco `Pedidos recentes`
  - composição textual da coluna `Status`
  - prioridade entre milestone, atualização recente e hint de continuidade
- sem alterar:
  - estrutura da tabela
  - navegação
  - filtros
  - paginação

Leitura prática:
- esse é um próximo passo pequeno e seguro
- e mantém a evolução do overview alinhada ao mesmo padrão:
  - primeiro framing
  - depois, se necessário, refinamentos mais profundos

Decisão:
- o bloco `recent_orders` do `account overview` deve evoluir primeiro por **framing do bloco e taxonomia da célula de status**

Motivo:
- a tabela já está estável
- o principal ganho agora não exige mudança estrutural
- exige melhorar a ordem da leitura entre:
  - milestone principal
  - atualização recente
  - hint de continuidade

Escopo recomendado:
- revisar primeiro:
  - título/contexto do bloco
  - composição textual da coluna `Status`
  - prioridade da leitura da linha
- sem alterar:
  - colunas
  - navegação
  - filtros
  - paginação

Leitura prática:
- isso mantém `recent_orders` no mesmo padrão de evolução usado no restante da área da conta:
  - primeiro copy e framing
  - depois, se necessário, refinamentos mais profundos

Decisão:
- a primeira execução em `recent_orders` deve começar por **copy do bloco e da célula `Status`**

Motivo:
- esse é o menor recorte com melhor custo-benefício
- ele melhora:
  - percepção de continuidade
  - clareza sobre o pedido que merece atenção
  - hierarquia da leitura
- sem tocar em:
  - estrutura da tabela
  - colunas
  - navegação
  - ordenação

Escopo recomendado:
- revisar primeiro:
  - `recent_orders_title`
  - composição textual da célula `Status`
- manter factual, por enquanto:
  - coluna de data
  - total
  - número do pedido

Leitura prática:
- `recent_orders` já está pronto para uma wave pequena de **copy execution**
- isso preserva estabilidade e mantém a evolução do overview incremental

Decisão:
- a primeira execução em `recent_orders` fica restrita a:
  - `recent_orders_title`
  - composição textual da célula `Status`

Escopo executado:
- o bloco passa a comunicar continuidade já no título:
  - `Pedidos para acompanhar`
- a célula `Status` passa a priorizar:
  - milestone/hint principal
  - atualização recente
  - estado factual

Motivo:
- esse recorte entrega uma leitura melhor de continuidade sem mexer em:
  - colunas
  - estrutura da tabela
  - navegação
  - ordenação

Leitura prática:
- o overview recente fica mais útil para localizar rápido o pedido certo
- e continua estável do ponto de vista estrutural

Decisão:
- o próximo refinamento do `account overview` deve olhar para o **`activity card` como superfície de retenção leve**

Motivo:
- o card já entrega:
  - resumo recente
  - próximo passo
  - contexto de continuidade
- o principal gap agora é de framing:
  - menos resumo operacional puro
  - mais motivo claro para voltar

Escopo recomendado:
- revisar primeiro:
  - `activity_title`
  - `activity_subtitle`
  - framing textual de `activity_content`
- sem alterar:
  - estrutura do card
  - ordem da página
  - lógica de continuidade

Leitura prática:
- isso mantém o overview evoluindo por cortes pequenos de copy e retenção
- sem abrir complexidade estrutural nova

Decisão:
- o `activity card` do `account overview` deve evoluir primeiro por **framing do card e ordenação da leitura do conteúdo**

Motivo:
- o card já é útil e estável
- o principal ganho agora é melhorar a leitura entre:
  - estado mais relevante
  - próximo passo
  - contexto de continuidade
- sem alterar:
  - estrutura do card
  - ordem da página
  - lógica da conta

Escopo recomendado:
- revisar primeiro:
  - `activity_title`
  - `activity_subtitle`
  - framing de `activity_content`

Leitura prática:
- isso mantém o `activity card` alinhado ao padrão de evolução usado no overview:
  - primeiro copy e framing
  - depois, se necessário, refinamentos mais profundos

Decisão:
- a primeira execução no `activity card` deve começar por **copy do card e framing do conteúdo**

Motivo:
- esse é o menor recorte com melhor custo-benefício
- ele melhora:
  - percepção de retorno
  - clareza do próximo acompanhamento
  - utilidade do overview no próximo acesso
- sem tocar em:
  - estrutura do card
  - ordem da página
  - origem dos dados
  - lógica da conta

Escopo recomendado:
- revisar primeiro:
  - `activity_title`
  - `activity_subtitle`
  - framing de `activity_content`

Leitura prática:
- o `activity card` já está pronto para uma wave pequena de **copy execution**
- isso preserva estabilidade e mantém a evolução do overview incremental

Decisão:
- a primeira execução no `activity card` fica restrita a:
  - `activity_title`
  - `activity_subtitle`
  - framing de `activity_content`

Escopo executado:
- o card passa a comunicar continuidade já no título:
  - `O que acompanhar agora`
- o subtítulo reforça:
  - melhor próximo retorno
  - utilidade do próximo acesso
- o conteúdo passa a abrir com foco em:
  - melhor acompanhamento atual
  - próximo contexto útil

Motivo:
- esse recorte entrega uma leitura melhor de retenção sem mexer em:
  - estrutura do card
  - ordem da página
  - origem dos dados
  - lógica da conta

Leitura prática:
- o overview agora termina com uma superfície mais claramente orientada a retorno
- e continua estável do ponto de vista estrutural

Decisão:
- o eixo de retenção do `account overview` pode ser considerado **encerrado com sucesso nesta fase**

Motivo:
- os principais ganhos planejados já foram entregues em:
  - framing do overview
  - bloco `recent_orders`
  - `activity card`
- o que resta agora parece:
  - refinamento futuro
  - e não gap funcional urgente

Leitura prática:
- o `account overview` ficou mais coerente como superfície de retenção
- o próximo investimento mais honesto deve voltar para a **customer area como produto**, não insistir no mesmo bloco do overview

Decisão:
- o eixo de **pós-compra + retenção leve da `customer area`** pode ser considerado **encerrado com sucesso nesta fase**

Motivo:
- os principais ganhos planejados já foram consolidados em:
  - `order detail`
  - `orders list`
  - `account overview`
- a área agora comunica melhor:
  - acompanhamento
  - continuidade
  - motivo de retorno

Leitura prática:
- o próximo investimento mais honesto agora deve sair da `customer area`
- e voltar ao roadmap funcional mais amplo do produto, com foco em conversão e valor percebido antes da compra

Decisão:
- o próximo eixo do roadmap funcional deve olhar para **`catalog` / `PDP` como superfície de conversão**

Motivo:
- o pós-compra e a retenção leve da `customer area` já avançaram bem nesta fase
- no momento, o maior ganho funcional parece estar antes da compra, em:
  - descoberta
  - clareza comercial
  - merchandising leve
  - apoio à decisão no detalhe do produto

Leitura prática:
- o próximo investimento mais honesto não parece ser checkout ou payment
- parece ser aprofundar a confiança e o valor percebido no `catalog` / `PDP`

Decisão:
- o próximo refinamento do roadmap funcional deve olhar para o **PDP como principal superfície de confiança de conversão**

Motivo:
- o detalhe do produto já está sólido em:
  - variante efetiva
  - preço
  - disponibilidade
  - continuidade até checkout/cart
- o principal ganho agora parece estar em:
  - copy comercial leve
  - reforço de desejo
  - confiança de decisão

Leitura prática:
- o próximo investimento mais honesto não parece ser novo fluxo
- parece ser aprofundar o valor percebido do PDP sem mexer no handoff já consolidado

Decisão:
- o PDP deve evoluir primeiro por **narrativa comercial leve**, não por novo fluxo

Motivo:
- o detalhe já está sólido em:
  - variante efetiva
  - preço
  - disponibilidade
  - continuidade até cart/checkout
- o principal ganho agora é elevar:
  - desejo
  - contexto de uso
  - confiança de decisão

Escopo recomendado:
- revisar primeiro:
  - `product_subtitle`
  - `short_description`
  - `purchase_note`
  - framing do `cta_helper`
- sem alterar:
  - seleção de variante
  - cart
  - checkout
  - estrutura do template

Leitura prática:
- isso mantém o PDP no mesmo padrão de evolução seguro:
  - primeiro framing
  - depois copy
  - sem reabrir o fluxo que já está estabilizado

Decisão:
- a primeira execução comercial do PDP deve começar por **copy narrativa do detalhe**

Motivo:
- esse é o menor recorte com melhor custo-benefício
- ele melhora:
  - valor percebido
  - desejo leve
  - confiança de decisão
- sem tocar em:
  - seleção de variante
  - preço
  - estoque
  - cart/checkout
  - estrutura do template

Escopo recomendado:
- revisar primeiro:
  - `product_subtitle`
  - `short_description`
  - `purchase_note`
  - `cta_helper`

Leitura prática:
- o PDP já está pronto para uma wave pequena de **copy execution**
- isso preserva estabilidade e mantém o handoff seguro já conquistado

Decisão:
- a primeira execução comercial do PDP fica restrita a:
  - `product_subtitle`
  - `short_description`
  - `purchase_note`
  - `cta_helper`

Escopo executado:
- o detalhe passa a reforçar melhor:
  - valor percebido da combinação atual
  - contexto de decisão
  - prontidão para avançar

Motivo:
- esse recorte entrega mais confiança comercial sem mexer em:
  - seleção de variante
  - preço
  - estoque
  - cart/checkout
  - estrutura do template

Leitura prática:
- o PDP agora fica menos “apenas seguro”
- e mais convincente como superfície de decisão antes da compra

Decisão:
- o eixo de **confiança de conversão do PDP** pode ser considerado **encerrado com sucesso nesta fase**

Motivo:
- os principais ganhos planejados já foram consolidados em:
  - clareza da variante efetiva
  - helper e CTA mais seguros
  - narrativa comercial leve do detalhe
- o que sobra agora parece:
  - refinamento futuro
  - e não gap funcional urgente

Leitura prática:
- o próximo investimento mais honesto agora deve sair do detalhe do produto
- e voltar ao roadmap funcional mais amplo do storefront, com foco em descoberta e merchandising

Decisão:
- a vitrine de catálogo já pode ser tratada, nesta fase, como superfície funcionalmente madura e pronta para um eixo de **merchandising leve**

Motivo:
- os cards já comunicam bem:
  - combinação em destaque
  - disponibilidade
  - helper de clique
  - contexto comercial básico
- o principal gap restante não é mais fluxo
- o principal gap agora é:
  - framing editorial
  - descoberta mais desejável
  - motivo mais forte para abrir um produto agora

Leitura prática:
- o próximo passo mais honesto no roadmap do catálogo não é reabrir filtros, paginação ou handoff para PDP
- o próximo passo deve revisar a vitrine como produto de descoberta e merchandising, começando por copy e framing da página/listagem

Decisão:
- o eixo seguinte do catálogo deve evoluir por **merchandising leve de vitrine**, não por refactor estrutural

Motivo:
- a superfície já está sólida em:
  - descoberta segura
  - continuidade até o PDP
  - decisão inicial por card
- os gaps mais relevantes agora são:
  - framing editorial do topo
  - motivo comercial para abrir um produto agora
  - curadoria mais perceptível dentro dos cards

Leitura prática:
- o próximo corte seguro deve começar por copy e framing de:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - sinais editoriais dos cards
- sem reabrir:
  - filtros
  - paginação
  - estrutura da grade
  - handoff para o detalhe

Decisão:
- a evolução seguinte da vitrine deve começar por um **plano de copy editorial**, não por mudança estrutural

Motivo:
- o menor recorte com melhor custo-benefício agora é:
  - topo da página
  - framing editorial leve dos cards
- isso melhora descoberta e merchandising sem tocar em:
  - filtros
  - paginação
  - layout
  - lógica de preço/estoque
  - handoff para o PDP

Leitura prática:
- o primeiro corte recomendado fica em:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - `curation_note`
  - `click_helper`
- helpers mais próximos da decisão (`price_helper`, `availability_note`) ficam para depois, se ainda fizer sentido

Decisão:
- a primeira execução de merchandising da vitrine deve começar por **copy editorial do topo e sinais leves de curadoria**

Motivo:
- esse é o menor recorte com melhor custo-benefício para melhorar:
  - percepção de vitrine
  - desejo leve de exploração
  - motivo para abrir um produto agora
- sem tocar em:
  - helpers transacionais/comerciais mais sensíveis
  - filtros
  - paginação
  - layout

Leitura prática:
- a primeira passada de execução fica restrita a:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - `curation_note`
  - `click_helper`

Decisão:
- a primeira execução de merchandising da vitrine deve ficar restrita à **copy editorial do topo e à curadoria leve dos cards**

Escopo executado:
- o topo da página passa a reforçar melhor:
  - combinações em destaque
  - curadoria leve
  - motivo para abrir um produto agora
- os cards passam a usar linguagem mais editorial em:
  - `curation_note`
  - `click_helper`

Motivo:
- esse recorte melhora valor percebido e descoberta sem tocar em:
  - filtros
  - paginação
  - grade
  - helpers mais próximos da decisão final
  - handoff para o detalhe

Leitura prática:
- a vitrine agora fica mais convidativa e memorável
- sem perder o caráter honesto e seguro que já tínhamos consolidado

Decisão:
- o eixo de **merchandising leve da vitrine** pode ser considerado encerrado com sucesso nesta fase

Motivo:
- os principais ganhos planejados já foram entregues em:
  - framing editorial do topo
  - curadoria leve dos cards
  - motivo comercial mais claro para abrir um produto agora
- o que sobra agora parece:
  - refinamento futuro
  - e não gap funcional pequeno ou urgente

Leitura prática:
- o próximo passo mais honesto agora não é insistir na mesma vitrine
- o próximo passo deve revisar o storefront antes da compra como um todo, consolidando:
  - catálogo
  - PDP

Decisão:
- o eixo de **storefront discovery / confiança pré-compra** pode ser considerado encerrado com sucesso nesta fase

Motivo:
- os principais ganhos planejados já foram consolidados em:
  - vitrine mais editorial
  - PDP mais convincente
  - continuidade mais clara entre catálogo e detalhe
- o que sobra agora parece:
  - refinamento futuro
  - e não gap funcional pequeno ou urgente antes da compra

Leitura prática:
- o próximo passo mais honesto agora é sair de descoberta/PDP
- e revisar o checkout como a próxima superfície funcional de produto

Decisão:
- o checkout deve ser o próximo eixo funcional de produto depois de storefront discovery e pós-compra

Motivo:
- a superfície já está forte em:
  - progressão por etapa
  - cart surface lite
  - checklist de revisão
  - recovery guidance
  - handoff para pedido inicial e pagamento pendente
- o principal gap restante não parece ser fluxo
- o principal gap agora é:
  - clareza de jornada
  - redução de atrito percebido
  - melhor orientação do próximo passo

Leitura prática:
- o próximo corte seguro deve revisar copy e framing de etapa
- sem reabrir:
  - criação de pedido
  - `PaymentAttempt`
  - estoque
  - retry/recovery transacional
  - layout estrutural

Decisão:
- a primeira execução de clareza do checkout deve começar por **copy de etapa e orientação final**

Motivo:
- a superfície já está funcionalmente segura
- o menor ganho de produto agora está em reduzir dúvida sobre:
  - etapa atual
  - próximo clique
  - consequência da ação
- isso pode ser feito sem tocar em:
  - template
  - regras transacionais
  - `PaymentAttempt`
  - recovery

Leitura prática:
- o primeiro recorte fica em:
  - `stage_title`
  - `stage_description`
  - `submit_label`
  - `final_action_description`
  - `final_action_helper`

Decisão:
- a primeira execução de clareza do checkout fica restrita à copy de etapa, CTA e orientação final

Escopo executado:
- as etapas passam a comunicar melhor:
  - onde a pessoa está
  - qual é o próximo passo
  - o que acontece depois do clique

Motivo:
- esse recorte reduz atrito percebido sem alterar:
  - template
  - criação de pedido
  - `PaymentAttempt`
  - estoque
  - recovery transacional

Leitura prática:
- o checkout mantém o mesmo comportamento seguro
- mas agora a progressão fica mais compreensível para o cliente

Decisão:
- o próximo ajuste de checkout deve revisar o resumo lateral como superfície de confiança, sem mudar sua estrutura

Motivo:
- o resumo já está correto em itens e totais
- o ganho restante é de copy:
  - o que o total representa
  - quando vira pedido inicial
  - por que o pagamento real ainda não é confirmado ali

Leitura prática:
- o primeiro recorte do resumo deve ficar em:
  - `summary_description`
  - `summary_note`
- sem mexer em:
  - template
  - cálculo de totais
  - parcelamento
  - criação de pedido
  - `PaymentAttempt`

Decisão:
- a primeira execução de confiança do resumo lateral deve ficar restrita a `summary_description` e `summary_note`

Escopo executado:
- o resumo passa a explicar melhor:
  - o que o total representa por etapa
  - quando a sessão ainda está em preparação
  - quando o total será levado para pedido inicial
  - que a confirmação real de pagamento acontece depois

Motivo:
- esse recorte aumenta confiança no momento da decisão sem alterar:
  - template
  - cálculo de totais
  - parcelamento
  - criação de pedido
  - `PaymentAttempt`

Leitura prática:
- o resumo lateral fica mais tranquilizador
- o comportamento transacional permanece igual

Decisão:
- o eixo de **checkout product experience** pode ser considerado encerrado com sucesso nesta fase

Motivo:
- os principais ganhos planejados já foram entregues em:
  - copy de etapa
  - CTA e orientação final
  - resumo lateral mais tranquilizador
- o que sobra agora parece:
  - refinamento visual futuro
  - UX específica de métodos reais de pagamento
  - e não gap funcional pequeno ou urgente do checkout

Leitura prática:
- o próximo passo mais honesto agora é sair do checkout geral
- e revisar pagamentos como experiência de produto, sem reabrir a base transacional já endurecida

Decisão:
- a próxima evolução de `payments` deve tratar pagamento como experiência de produto, não como novo trabalho de gateway

Motivo:
- a base atual já cobre tentativa, checkout hospedado, retorno, webhook, rollout por tenant, observabilidade e runbook
- o gap mais visível agora está em como o cliente entende:
  - pagamento pendente
  - retorno do provider
  - falha
  - retomada
  - pendência longa

Leitura prática:
- não devemos reabrir provider, webhook, rollout ou alertas nesta etapa
- o próximo recorte deve revisar mensagens customer-facing no detalhe do pedido e nos fluxos de retorno/retomada

Decisão:
- a primeira evolução customer-facing de pagamentos deve ficar em `accounts.application.account_customer_area_queries`

Motivo:
- `payments` já produz sinais técnicos suficientes sobre tentativa, retorno, falha, stale state e hosted payment
- o cliente lê esses sinais principalmente no detalhe do pedido
- portanto a melhor fronteira é manter `payments` como origem técnica e `accounts` como tradução de produto

Leitura prática:
- o menor recorte seguro é ajustar copy de:
  - estado atual
  - recovery pendente
  - pedido pendente antigo
  - CTA/helper de retomada hospedada ou retry
  - enriquecimento narrativo da tentativa
- sem alterar templates, webhook, provider, tenant scope ou criação de sessão

Decisão:
- executar a primeira melhoria de linguagem de pagamentos somente no detalhe do pedido

Escopo executado:
- mensagens de pagamento pendente, falha, retry, hosted payment e pendência longa ficaram mais orientadas ao cliente
- a copy agora reforça melhor:
  - pedido salvo
  - verificação externa possível
  - retomada segura
  - nova tentativa com sessão limpa
  - suporte quando não há ação automática segura

Motivo:
- isso melhora confiança e compreensão sem mover regras para fora das fronteiras atuais
- `payments` permanece responsável por sinais técnicos e `accounts` pela tradução customer-facing

Leitura prática:
- a próxima revisão deve olhar especificamente os resultados de retorno hospedado/indisponibilidade após redirect

Decisão:
- o fluxo de retorno hospedado já está estruturalmente correto e não precisa mudar nesta etapa

Motivo:
- `payments` registra o retorno por tenant e devolve um `result`
- `accounts` renderiza o feedback customer-facing no detalhe do pedido
- o retorno positivo não confirma pagamento sozinho, preservando a reconciliação via evento/webhook

Leitura prática:
- a próxima execução deve ajustar apenas a copy do mapping de `page_feedback` para resultados `hosted-payment-*`
- também vale adicionar testes em `accounts` para garantir que esses results continuam visíveis e compreensíveis
- não mexer em redirect/return, webhook, `PaymentAttempt`, template ou tenant scope

Decisão:
- ajustar a linguagem dos resultados `hosted-payment-*` sem alterar o fluxo técnico

Escopo executado:
- `hosted-payment-unavailable`
- `hosted-payment-returned`
- `hosted-payment-return-pending-verification`
- `hosted-payment-return-failed`

Motivo:
- o cliente precisa entender continuidade, verificação e retry sem ler termos técnicos como provider/hospedado
- a camada correta para isso é `accounts.interfaces.views`, onde o `result` vira `page_feedback`

Leitura prática:
- o fluxo segue preservando reconciliação segura via evento/webhook
- a próxima wave deve revisar se o eixo de experiência de pagamentos já pode ser encerrado nesta fase

Decisão:
- encerrar o eixo de **Payment Product Experience** nesta fase

Motivo:
- já foram revisados e ajustados:
  - estado customer-facing de pagamento
  - retry e hosted payment
  - pendência longa
  - retorno do ambiente seguro
  - feedback de indisponibilidade/falha/verificação
- a base operacional de `payments` já tinha provider, tentativa, webhook, rollout, observabilidade e runbook
- não resta um próximo recorte pequeno e urgente sem abrir temas maiores

Fora de escopo futuro:
- métodos reais adicionais
- parcelamento avançado por provider
- conciliação financeira/backoffice
- refund/chargeback/cancelamento
- automações de suporte para pagamento preso

Leitura prática:
- o próximo passo deve sair de pagamentos e avançar para outro eixo funcional do produto
- candidato natural: frete/entrega como experiência de produto

Decisão:
- iniciar o eixo de **Shipping Product Experience** como revisão de contrato de produto, não integração logística

Motivo:
- o módulo `shipping` ainda é esquelético e representa o dono futuro de cotação, shipment e rastreio
- a experiência atual de entrega está distribuída entre:
  - `checkout`
  - `orders`
  - `accounts`
- essa distribuição é aceitável nesta fase, mas precisa de fronteira explícita antes de crescer

Leitura prática:
- `checkout` apresenta entrega/frete na sessão
- `orders` controla preparo/envio/entrega concluída
- `accounts` traduz o estado de entrega para o cliente
- `shipping` deve absorver cotação/rastreio quando o contrato funcional amadurecer

Próximo recorte:
- revisar promessa de entrega no checkout antes de implementar integração real de frete

Decisão:
- a primeira evolução de entrega deve ajustar a promessa de frete no checkout, não implementar cotação real

Motivo:
- os métodos atuais comunicam preço e prazo básico, mas “Receba em até X dias úteis” pode soar definitivo demais
- sem integração real de `shipping`, o produto deve tratar prazo como estimativa condicionada a endereço, pagamento, preparo e envio

Leitura prática:
- o menor recorte seguro fica em `checkout.application.checkout_page_queries`
- ajustar copy de métodos, seção de entrega, hints e eventualmente resumo lateral
- não mexer em templates, cálculo de frete, models, criação de pedido ou integração externa

Decisão:
- executar a primeira melhoria de promessa de entrega apenas como copy no checkout

Escopo executado:
- métodos de entrega passam a comunicar estimativa da modalidade
- entrega salva/incompleta passa a falar em frete estimado
- resumo lateral reforça que prazo/envio dependem de pagamento confirmado e preparo do pedido

Motivo:
- sem cotação real em `shipping`, o produto não deve prometer prazo definitivo
- a copy pode aumentar confiança sem alterar cálculo, sessão, pedido ou integração

Leitura prática:
- o próximo eixo natural é revisar tracking/estado de entrega na área do cliente

Decisão:
- tratar tracking de entrega inicialmente como camada customer-facing leve, não integração logística

Motivo:
- a área do cliente já comunica preparo, envio, trânsito e entrega via status e timeline
- ainda falta separar melhor “acompanhamento da entrega” da timeline geral do pedido
- `shipping` ainda não tem contrato real de tracking code/link no código

Leitura prática:
- o próximo recorte deve traduzir estados existentes de pedido/fulfillment em uma camada de acompanhamento
- não criar novos estados, models ou integração externa nesta etapa
- possível implementação futura: payload dedicado em `accounts.application.account_customer_area_queries` e renderização com componente existente

Decisão:
- implementar tracking leve de entrega como payload derivado em `accounts`, usando componente existente de alert

Motivo:
- a área do cliente já tem status e timeline, mas falta um destaque específico para acompanhamento de entrega
- `alert.html` cobre bem o caso sem criar componente novo
- os estados necessários já existem em `Order`/fulfillment/shipping status

Contrato planejado:
- `delivery_tracking_visible`
- `delivery_tracking_variant`
- `delivery_tracking_icon`
- `delivery_tracking_title`
- `delivery_tracking_description`

Leitura prática:
- a execução deve criar helper em `account_customer_area_queries.py`, renderizar no `order_detail_page` e adicionar testes
- não mexer em `shipping` models, tracking code, integração logística ou estados operacionais

Decisão:
- executar tracking leve de entrega como alerta customer-facing derivado dos estados existentes

Escopo executado:
- helper derivado em `accounts.application.account_customer_area_queries`
- payload `delivery_tracking_*`
- renderização com `shared/components/feedback/alert.html`
- testes para preparação, trânsito, entrega concluída e pagamento pendente sem tracking

Motivo:
- melhora a leitura de entrega sem fingir integração logística real
- mantém `shipping` como dono futuro de tracking code/provider
- preserva `orders` como dono dos estados operacionais

Leitura prática:
- a próxima wave deve decidir se o eixo de frete/entrega já está completo para esta fase

Decisão:
- encerrar o eixo de **Shipping Product Experience** nesta fase

Motivo:
- a promessa de entrega no checkout ficou mais honesta e condicionada
- a área do cliente ganhou tracking leve derivado de estados existentes
- a fronteira futura de `shipping` ficou clara sem criar integração falsa

Futuro:
- cotação real por endereço/CEP
- tracking code/link
- provider logístico
- eventos de shipment
- painel ou fluxo logístico dedicado

Leitura prática:
- o próximo eixo funcional deve sair de frete/entrega e revisar notificações como camada de comunicação do produto

Decisão:
- iniciar o eixo de **Notifications Product Experience** como revisão de contrato, não envio real

Motivo:
- `notifications` ainda é módulo esquelético
- `docs/events-map.md` já indica eventos consumidores de notificações
- o produto já possui estados suficientes para mensagens transacionais futuras

Leitura prática:
- não implementar `EmailLog`, Celery ou adapter de e-mail sem antes definir intents
- o próximo recorte deve catalogar notificações mínimas por evento, público, canal e idempotência
- toda futura notificação deve carregar `tenant_id` e distinguir `Customer` de `OwnerUser`

Decisão:
- o primeiro artefato executável de notifications deve ser um catálogo puro de intents

Motivo:
- evita implementar envio antes de decidir o que será comunicado, para quem e por qual evento
- permite testar contrato de idempotência e fronteiras sem depender de Celery/e-mail

Leitura prática:
- implementar em `notifications.application`
- incluir intents customer e owner para pedido, pagamento e entrega
- não criar `EmailLog`, migrations, worker ou adapter SMTP nesta etapa

Decisão:
- implementar catálogo puro de intents de notificações antes de qualquer dispatch real

Escopo executado:
- `notifications.application.notification_intent_catalog`
- testes de contrato em `notifications.tests.test_notification_intent_catalog`

Motivo:
- cria base testável para mensagens transacionais
- permite validar idempotência por tenant/intenção/entidade/canal
- evita acoplar envio real antes de amadurecer fronteira de eventos

Leitura prática:
- o próximo passo deve revisar boundary de dispatch, não partir direto para worker/SMTP

Decisão:
- a fronteira inicial de dispatch de notificações será um preview puro, não um worker real

Motivo:
- permite validar evento, público, canal, copy e idempotência sem provider externo
- mantém os módulos de origem desacoplados de SMTP/Celery/templates
- preserva `tenant_id` como parte obrigatória da resolução

Leitura prática:
- implementar resolver em `notifications.application`
- retornar candidatos de dispatch com idempotency key, sem persistir nem enviar

Decisão:
- implementar `NotificationDispatchPreview` como contrato intermediário antes de recipients reais

Escopo executado:
- `notifications.application.notification_dispatch_resolver`
- testes de resolução por evento, audience e idempotência tenant-scoped

Motivo:
- cria uma ponte segura entre catálogo de intents e futuro envio assíncrono
- evita misturar `Customer` e `OwnerUser` antes de formalizar resolução de destinatários

Leitura prática:
- o próximo passo deve revisar a boundary de recipients antes de qualquer `EmailLog`/worker

Decisão:
- destinatários de notificações devem ser representados por referência explícita antes de qualquer envio real

Motivo:
- evita confundir `Customer` com `OwnerUser`
- mantém `tenant_id` obrigatório no caminho de notificação
- impede que `notifications` vire dono de queries internas de identidade cedo demais

Leitura prática:
- criar contrato puro de recipient target
- separar `customer` e `owner_user`
- não resolver usuários automaticamente dentro do módulo ainda

Decisão:
- implementar `NotificationRecipientTarget` como value object de boundary

Escopo executado:
- `notifications.application.notification_recipient_targets`
- helpers explícitos para customer e owner
- testes de identidade, tenant e entregabilidade

Motivo:
- prepara o futuro envelope de dispatch sem misturar identidade administrativa e comprador
- preserva a fronteira entre `accounts`, `customers` e `notifications`

Leitura prática:
- o próximo passo seguro é combinar intent preview + recipient target em um envelope puro

Decisão:
- o primeiro envelope de dispatch deve ser puro e validado por tenant, audience e entregabilidade

Motivo:
- combina intent e destinatário sem ainda acionar infraestrutura
- impede envio cruzado entre tenants
- impede que customer-facing seja entregue para owner/admin por acidente

Leitura prática:
- envelope rejeita mismatch de `tenant_id`
- envelope rejeita mismatch de `audience`
- recipient sem e-mail não gera unidade de envio

Decisão:
- adicionar chave de delivery por recipient além da chave de idempotência do evento

Motivo:
- a idempotência do evento continua útil para deduplicar intent
- a chave por recipient evita colisões quando um evento precisar avisar mais de um owner ou contato

Escopo executado:
- `notifications.application.notification_dispatch_envelopes`
- testes de envelope válido, cross-tenant, audience e entregabilidade

Leitura prática:
- o próximo passo deve revisar persistência (`EmailLog`) antes de qualquer worker real

Decisão:
- `EmailLog` deve nascer como unidade persistida planejável, não como confirmação de entrega

Motivo:
- permite idempotência e auditoria antes de acionar infraestrutura assíncrona
- separa evento/intenção de tentativa real de envio
- preserva snapshot de recipient e copy para retry futuro

Leitura prática:
- criar status mínimo `planned/requested/sent/failed/skipped`
- manter `tenant_id`, intent, evento e delivery key explícitos
- não criar worker/provider nesta etapa

Decisão:
- implementar persistência mínima de `EmailLog` em `notifications`

Escopo executado:
- modelo `EmailLog`
- migration inicial do módulo
- testes de default e unicidade de `recipient_delivery_key`

Motivo:
- cria base auditável para futuro dispatch sem acoplar envio real
- mantém idempotência por destinatário/canal

Leitura prática:
- o próximo passo seguro é um writer idempotente que persiste envelopes

Decisão:
- persistir envelopes de notificação por writer idempotente antes de qualquer envio

Motivo:
- separa criação de unidade planejada de dispatch real
- permite deduplicar por `recipient_delivery_key`
- evita que retries ou eventos repetidos dupliquem logs planejados

Leitura prática:
- writer recebe envelope já validado
- `EmailLog` nasce como `planned`
- log existente não deve ser sobrescrito automaticamente

Escopo executado:
- `notifications.application.notification_log_writer`
- testes de criação e reuso idempotente

Leitura prática:
- o próximo passo deve revisar boundary de worker/provider, ainda sem envio real

Decisão:
- preparar lifecycle de `EmailLog` antes de implementar worker/provider

Motivo:
- um worker futuro precisa de comandos explícitos para marcar solicitação, sucesso, falha ou skip
- transições precisam continuar tenant-scoped
- envio real ainda seria prematuro sem provider/template/preferências

Leitura prática:
- comandos de status recebem `tenant_id` e `log_id`
- não há busca global de logs
- `sent` não volta para `failed`

Escopo executado:
- `notifications.application.notification_log_status_commands`
- testes de transições e proteção cross-tenant

Leitura prática:
- o eixo de notifications já tem base suficiente para wrap-up desta fase

Decisão:
- encerrar a fase atual de Notifications Product Experience como contrato operacional mínimo pronto

Motivo:
- a cadeia de intent → preview → recipient → envelope → EmailLog → lifecycle já está testável
- ainda não há dependência de provider externo, worker ou template HTML
- os bloqueios restantes pertencem à integração operacional, não à revisão de produto/contrato

Bloqueios para produção real de envio:
- resolver destinatários reais a partir dos eventos
- provider/adapters de e-mail
- templates
- Celery/queue
- retry/backoff
- preferências por tenant
- integração com eventos reais

Leitura prática:
- a próxima trilha natural é readiness de integração por evento piloto, não mais UX/copy

Decisão:
- usar `payment.failed` como primeiro evento piloto de integração de notifications

Motivo:
- baixo risco operacional, pois não confirma pedido nem baixa estoque
- já existe webhook seguro e tenant-scoped em `payments`
- já existe intent customer-facing e recovery UX para esse estado

Leitura prática:
- criar handler em `notifications.application`
- conectar apenas depois de `payment-failed` persistido
- gravar `EmailLog` planejado e idempotente, sem envio real

Escopo executado:
- `notifications.application.notification_event_handlers`
- integração em `payments.application.webhook_commands`
- testes de handler e webhook com `EmailLog`

Leitura prática:
- o piloto valida a ponte evento → log; próximos eventos devem ser adicionados um por vez

Decisão:
- encerrar o piloto de `payment.failed` como integração mínima bem-sucedida

Motivo:
- cria log planejado customer-facing de forma tenant-scoped e idempotente
- não envia e-mail real nem aciona worker
- replay do webhook não duplica unidade de entrega

Leitura prática:
- próximos eventos devem entrar incrementalmente
- melhor próximo candidato é `payment.paid`, mas com atenção ao impacto operacional de confirmação/estoque
- owner-facing continua bloqueado por resolver explícito de owners/admins

Decisão:
- conectar `payment.paid` como segundo evento customer-facing de notifications

Motivo:
- já passa pelo mesmo webhook seguro e tenant-scoped de payments
- comunica confirmação real após efeito operacional aplicado
- mantém envio real fora do escopo e só persiste `EmailLog` planejado

Leitura prática:
- criar log apenas em `payment-confirmed`
- não criar nova unidade em `payment-already-confirmed`
- preservar idempotência por delivery key

Decisão:
- não conectar `order.created` diretamente nesta abordagem

Motivo:
- o ponto real de criação ainda está na orquestração de checkout
- não há publisher interno formal pelo módulo `orders`
- acoplar checkout a notifications agora anteciparia uma fronteira que ainda precisa ser desenhada

Leitura prática:
- fechar integração atual com `payment.failed` e `payment.paid`
- retomar `order.created` depois de definir event bus/publisher interno

Decisão:
- encerrar a abordagem de integração de notifications com dois eventos reais de pagamento

Motivo:
- o fluxo já prova evento real → log idempotente sem envio real
- os próximos passos exigem infraestrutura nova: provider, template, worker, preferências e publisher

Bloqueios restantes:
- event bus/publisher interno
- resolver de owners/admins
- shipping/tracking real
- SMTP/provider
- templates
- Celery/worker
- retry/backoff
- preferências por tenant

Leitura prática:
- próxima abordagem natural é Delivery Infrastructure Readiness, começando por dry-run

Decisão:
- delivery de notifications deve começar em dry-run por padrão

Motivo:
- evita envio real acidental durante rollout
- permite validar worker/adapter/lifecycle em produção controlada
- mantém provider real atrás de configuração explícita

Leitura prática:
- `NOTIFICATIONS_EMAIL_DRY_RUN` começa ligado
- envio real exige `DEFAULT_FROM_EMAIL` e backend de e-mail configurado
- adapter vive em `notifications.infrastructure`

Escopo executado:
- `notifications.infrastructure.email_delivery`
- settings de dry-run, batch e remetente
- testes de dry-run e backend Django

Decisão:
- delivery de um `EmailLog` deve passar por comando application tenant-scoped

Motivo:
- mantém worker futuro fino
- centraliza lifecycle e tratamento de adapter
- evita mutação cross-tenant por `log_id` global

Leitura prática:
- dry-run marca log como `skipped`
- envio aceito marca `sent`
- falha marca `failed`
- worker/Celery devem chamar esse comando em vez de acessar infraestrutura diretamente

Escopo executado:
- `notifications.application.notification_delivery_commands`
- testes de dry-run, sent, failed e cross-tenant

Decisão:
- antes de Celery real, notifications terá management command tenant-scoped para processar batch de `EmailLog`

Motivo:
- permite validar dry-run em ambiente real
- mantém operação reversível e limitada por tenant
- evita acionar worker/provider antes de observabilidade e configuração final

Leitura prática:
- comando `process_email_logs --tenant-id ...`
- processa apenas logs `planned`
- respeita batch limit
- Celery futuro deve reaproveitar a mesma boundary

Escopo executado:
- management command `process_email_logs`
- teste de batch tenant-scoped em dry-run

Decisão:
- encerrar Delivery Infrastructure Readiness em dry-run

Motivo:
- já existe caminho planejado → processado sem envio acidental
- a boundary está pronta para Celery futuro
- envio real ainda depende de templates, CTAs reais, provider, observabilidade e preferências

Leitura prática:
- não desligar `NOTIFICATIONS_EMAIL_DRY_RUN` até haver template/CTA/provider/rollout por tenant
- próxima abordagem natural é Template & CTA Readiness

Decisão:
- CTAs de notifications devem ser resolvidos por tenant antes de envio real

Motivo:
- `cta_target` lógico não é suficiente para e-mail real
- tenants podem usar subdomínio ou custom domain
- links de pedido precisam respeitar isolamento por tenant e entidade

Leitura prática:
- resolver `customer_order_detail` e `admin_order_detail`
- não resolver pedido cross-tenant
- adapter plain-text deve usar URL resolvida quando existir

Escopo executado:
- `notifications.application.notification_cta_resolver`
- integração no adapter de delivery
- testes de subdomínio, custom domain e cross-tenant

Decisão:
- o primeiro contrato de template de notifications será plain-text

Motivo:
- reduz risco antes de provider real
- já permite dry-run e envio controlado sem depender de design HTML
- mantém o adapter de infraestrutura fino

Leitura prática:
- renderer fica em `notifications.application`
- adapter consome mensagem renderizada
- HTML template fica para abordagem posterior

Escopo executado:
- `notifications.application.notification_message_renderer`
- testes de subject, corpo e CTA resolvido

Decisão:
- encerrar Template & CTA Readiness com plain-text e CTA tenant-aware

Motivo:
- já remove o principal bloqueio funcional de link real
- HTML pode ser evoluído depois sem alterar pipeline de delivery
- o próximo risco é operacional: observabilidade e rollout por tenant

Leitura prática:
- próxima abordagem natural é Rollout & Observability Readiness

Decisão:
- rollout de notifications precisa de snapshot tenant-scoped antes de desligar dry-run

Motivo:
- operação precisa enxergar backlog, falhas e skips por tenant
- evita habilitar envio real às cegas
- cria base para métricas Prometheus futuras

Leitura prática:
- criar query de readiness por status
- expor management command operacional
- dashboard/métricas ficam para evolução posterior

Escopo executado:
- `notifications.application.notification_readiness_queries`
- management command `notification_readiness`
- testes de snapshot e saída do comando

Decisão:
- encerrar Rollout & Observability Readiness com relatório tenant-scoped mínimo

Motivo:
- já existe visibilidade de backlog/falha suficiente para piloto dry-run
- métricas e dashboard podem ser adicionados sem mudar o pipeline principal
- envio amplo segue bloqueado até provider, preferências, retry e Celery real

Leitura prática:
- próximo ciclo sistêmico deve ser Event Bus / Publisher Boundary
- isso desbloqueia `order.created` e `shipment.*` sem acoplar módulos diretamente

Decisão:
- criar publisher mínimo in-process antes de conectar novos eventos

Motivo:
- evita acoplamento direto entre módulos de origem e notifications
- oferece contrato inicial para futuros publishers/Celery
- mantém `order.created` e `shipment.*` fora até o boundary amadurecer

Leitura prática:
- publisher atual não é fila real
- não persiste eventos
- serve para estabilizar interface antes de Celery

Escopo executado:
- `notifications.application.notification_event_bus`
- testes de publish/subscribe

Decisão:
- encerrar Event Publisher Boundary sem conectar novos eventos

Motivo:
- o contrato mínimo existe, mas ainda falta ponto oficial de publicação em `orders` e `shipping`
- conectar cedo demais reintroduziria acoplamento direto

Leitura prática:
- próximo ciclo natural é Owner Recipient Resolver Readiness
- isso prepara owner-facing sem depender de novos eventos

Decisão:
- não implementar resolver owner-facing usando `AccountProfile`

Motivo:
- `OwnerUser` ainda não existe como modelo persistido explícito
- `AccountProfile` também pode estar ligado a `Customer`
- usar essa entidade como owner recipient misturaria identidades e criaria risco multi-tenant

Leitura prática:
- owner-facing intents permanecem como contrato futuro
- envio owner-facing exige `OwnerUser`/admin boundary explícita

Decisão:
- notifications está Go para dry-run operacional, Go condicionado para piloto real isolado e No-Go para produção ampla

Motivo:
- pipeline customer-facing de pagamento já existe e é idempotente
- delivery permanece seguro por dry-run default
- bloqueios de produção ampla ainda envolvem identidade owner, provider, Celery, retry, preferências e observabilidade

Leitura prática:
- permitido: dry-run tenant-scoped
- permitido com controle: tenant piloto real pequeno
- não permitido: envio amplo multi-tenant

Próxima abordagem natural:
- Owner/Admin Identity Implementation

Decisão:
- implementar `OwnerUser` como entidade administrativa explícita por tenant

Motivo:
- desbloqueia owner-facing notifications sem misturar `Customer` e `AccountProfile`
- preserva isolamento multi-tenant
- cria ponto futuro para roles e preferências administrativas

Escopo executado:
- modelo `accounts.OwnerUser`
- migration
- teste de persistência

Decisão:
- resolver owner-facing recipients a partir de `OwnerUser` ativo por tenant

Motivo:
- mantém identidade administrativa separada de customer/account profile
- respeita opt-in operacional `receives_notifications`
- permite múltiplos owners por tenant no futuro

Escopo executado:
- `notifications.application.notification_owner_recipient_resolver`
- testes de isolamento e elegibilidade

Decisão:
- integrar owner-facing logs ao evento `payment.failed`

Motivo:
- já existe intent owner-facing para falha de pagamento
- falha de pagamento pode exigir acompanhamento operacional
- confirmação de pagamento ainda não tem intent owner-facing definida

Escopo executado:
- handler owner-facing em notifications
- webhook `payment.failed` criando log para owner elegível
- testes de handler e webhook

Decisão:
- encerrar Owner/Admin Identity Implementation como pronto para owner-facing básico

Motivo:
- `OwnerUser` existe como entidade separada
- resolver owner-facing está tenant-scoped
- `payment.failed` já gera log operacional para owner elegível

Leitura prática:
- próxima abordagem natural é Notification Admin Operations Review

Decisão:
- criar operação mínima de listagem de `EmailLog` antes de UI administrativa completa

Motivo:
- facilita troubleshooting tenant-scoped
- evita depender de envio real para validar pipeline
- mantém operação simples via management command

Escopo executado:
- `notifications.application.notification_admin_queries`
- comando `list_email_logs`
- testes de query e comando

Decisão:
- encerrar Notification Admin Operations Review sem UI

Motivo:
- management commands já cobrem operação mínima desta fase
- UI admin adicionaria escopo visual sem desbloquear envio real

Leitura prática:
- próxima abordagem natural é Notification Provider Rollout Plan

Decisão:
- envio real de notifications exige readiness explícita de provider/configuração

Motivo:
- evita desligar dry-run sem backend/remetente configurado
- mantém credenciais fora do repositório
- cria checklist operacional automatizável

Escopo executado:
- `notifications.application.notification_provider_readiness`
- comando `notification_provider_readiness`
- testes de blockers/configuração mínima

Decisão:
- encerrar Notification Provider Rollout Plan sem credenciais reais no repositório

Motivo:
- o sistema consegue verificar prontidão, mas provider real depende de ambiente externo
- hardcode de credenciais seria risco de segurança
- envio amplo segue condicionado a piloto isolado

Leitura prática:
- próxima etapa é wrap-up final da trilha de notifications

Decisão:
- encerrar a trilha técnica de notifications nesta fase

Motivo:
- pipeline operacional dry-run está completo e validado
- envio real depende de ambiente externo/provider e decisão de rollout
- novas integrações de evento dependem de publisher oficial em módulos de origem

Resultado:
- pronto para dry-run por tenant
- pronto para piloto real isolado sob configuração externa
- não pronto para envio amplo multi-tenant

Próxima macro-abordagem recomendada:
- Owner/Admin Management UI

Decisão:
- iniciar Owner/Admin Management UI por services tenant-scoped antes das views

Motivo:
- mantém views finas
- evita lógica de owner em templates
- prepara operação mínima para owner-facing notifications

Escopo executado:
- `accounts.application.admin_owner_queries`
- `accounts.application.admin_owner_commands`
- `accounts.interfaces.owner_views`
- rota `/ops/owners/`
- testes tenant-scoped

Decisão:
- encerrar Owner/Admin Management UI como operação mínima pronta

Motivo:
- já permite gerenciar elegibilidade de owner-facing notifications
- criação/edição completa pode esperar autenticação/autorização administrativa mais formal

Leitura prática:
- próxima abordagem natural é Celery Email Worker Boundary

Decisão:
- criar tasks Celery finas para notifications sem mover regra de delivery para worker

Motivo:
- Celery deve orquestrar execução, não conter regra de negócio
- management command continua fallback operacional
- commands application permanecem a boundary única de lifecycle/delivery

Escopo executado:
- `notifications.tasks`
- testes de task sem worker real

Decisão:
- encerrar Celery Email Worker Boundary com tasks prontas e worker real opcional

Motivo:
- a boundary application já centraliza delivery
- tasks e management command podem coexistir
- provider real ainda depende de runbook/ambiente

Leitura prática:
- próxima abordagem natural é Notification Production Pilot Runbook

Decisão:
- documentar runbook de piloto real antes de recomendar qualquer envio

Motivo:
- provider real depende de ambiente externo
- dry-run precisa ser validado por tenant antes do envio
- rollback deve ser simples e conhecido

Leitura prática:
- piloto real só com `notification_provider_readiness` sem blockers
- lote pequeno
- rollback por `NOTIFICATIONS_EMAIL_DRY_RUN=1`

Próxima abordagem natural:
- Notification Metrics/Prometheus Integration

Decisão:
- expor métricas Prometheus de `EmailLog` por tenant/status

Motivo:
- operação precisa enxergar backlog e falhas antes de envio amplo
- segue o padrão já adotado em payments
- protege endpoint por token operacional

Escopo executado:
- `notifications.application.notification_metrics_queries`
- `notifications.interfaces.NotificationMetricsView`
- rota `/notifications/metrics/email-logs/`
- testes de exporter e endpoint

Decisão:
- encerrar Notification Metrics/Prometheus Integration com endpoint de scrape protegido

Motivo:
- já há métrica operacional mínima de backlog/falha por tenant
- dashboard pode ser especificado sem alterar o pipeline

Leitura prática:
- próxima abordagem natural é Notification Grafana Dashboard Spec

Decisão:
- especificar dashboard inicial de notifications em cima de `hubx_notifications_email_log_total`

Motivo:
- rollout precisa visualizar backlog e falhas por tenant
- métrica atual já é suficiente para painel operacional básico
- dashboard real pode ser materializado depois conforme stack de infra

Leitura prática:
- próxima abordagem natural é materializar alert rules versionadas

Decisão:
- materializar alert rules e scrape example de notifications em `infra/observability`

Motivo:
- aproxima a métrica de uma operação real de Prometheus
- mantém ativação documentada e reproduzível
- segue estrutura já usada por payments

Escopo executado:
- `prometheus/notifications-alert-rules.yml`
- `prometheus/notifications-scrape.example.yml`
- atualização de `infra/observability/README.md`

Decisão:
- versionar dashboard inicial de Grafana para notifications

Motivo:
- facilita ativação operacional junto do scrape/alert rules
- cobre os sinais mínimos de rollout: backlog, falhas, status e tenant

Escopo executado:
- `grafana/notifications-email-logs-dashboard.json`
- atualização de runbook de observability

Decisão:
- encerrar Notification Observability com exporter, scrape, alert rules e dashboard inicial

Motivo:
- há visibilidade operacional suficiente para rollout controlado
- os próximos incrementos são roteamento Alertmanager e métricas avançadas de provider/latência

Leitura prática:
- próxima macro-abordagem natural é Notification Alertmanager Routing

Decisão:
- versionar exemplo de roteamento Alertmanager para notifications

Motivo:
- completa o trio operacional scrape + alert rules + routing
- mantém URLs reais como placeholders de ambiente

Escopo executado:
- `alertmanager/notifications-routing.example.yml`
- atualização de runbook de observability

Decisão:
- encerrar observability de notifications com scrape, alertas, dashboard e routing versionados

Motivo:
- operação já consegue monitorar backlog/falhas e rotear alertas iniciais
- próximos gaps de notifications dependem mais de eventos de domínio do que de monitoramento

Leitura prática:
- próxima macro-abordagem recomendada é Order Created Event Publisher

Decisão:
- publicar `order.created` por boundary em `orders.application`

Motivo:
- evita acoplar checkout diretamente a detalhes de notifications
- mantém `orders` como dono da semântica do evento de pedido
- permite customer e owner notifications com writer idempotente

Escopo executado:
- `orders.application.order_event_publisher`
- integração em checkout completion
- testes de publisher e checkout criando logs de `order.created`

Decisão:
- encerrar Order Created Event Publisher como boundary funcional pronta

Motivo:
- o evento já gera logs customer/owner sem acoplar checkout aos detalhes de notifications
- replay de sessão não duplica pedido/logs

Leitura prática:
- próxima macro-abordagem recomendada é Shipping Event Publisher

Decisão:
- criar publisher mínimo de eventos logísticos em `shipping.application`

Motivo:
- prepara `shipment.sent` e `shipment.delivered` para notifications
- evita acoplar eventos a estados derivados sem `Shipment` real
- não cria tracking code fake

Escopo executado:
- `shipping.application.shipping_event_publisher`
- testes unitários do publisher

Decisão:
- encerrar Shipping Event Publisher sem integração automática

Motivo:
- sem `Shipment` real, disparar eventos a partir de estados derivados seria frágil
- a próxima evolução precisa persistir shipment/tracking antes de publicar eventos reais

Leitura prática:
- próxima macro-abordagem recomendada é Shipment Minimal Model & Commands

Decisão:
- implementar `Shipment` mínimo antes de ligar eventos logísticos reais

Motivo:
- eventos `shipment.sent` e `shipment.delivered` precisam de entidade persistida
- evita derivar eventos de copy/status soltos em orders/accounts
- cria base para tracking code/link futuro

Escopo executado:
- `shipping.models.Shipment`
- migration inicial
- teste de persistência básica

Decisão:
- comandos de shipment serão o ponto de publicação de eventos logísticos reais

Motivo:
- eventos passam a nascer de transição persistida de `Shipment`
- preserva tenant scope
- permite notifications customer/owner sem rastreio fake

Escopo executado:
- `shipping.application.shipment_commands`
- testes de envio, entrega e idempotência

Decisão:
- entrega logística só pode ser registrada por comando após shipment enviado

Motivo:
- evita publicar `shipment.delivered` sem transição logística mínima
- preserva semântica de pós-compra e notifications
- mantém enforcement tenant-scoped no boundary de shipping

Escopo executado:
- bloqueio de entrega antes do envio
- idempotência de entrega
- teste de isolamento cross-tenant

Leitura prática:
- próxima macro-abordagem recomendada é Shipping Admin Operations UI

Decisão:
- criar `/ops/shipping/` como superfície operacional inicial para comandos de shipment

Motivo:
- evita uso de shell para transições logísticas reais
- mantém ações passando por application commands tenant-scoped
- permite disparar notifications reais sem acoplar UI diretamente ao módulo de notifications

Escopo executado:
- listagem operacional de pedidos por tenant
- ação de marcar envio
- ação de confirmar entrega
- testes de isolamento por tenant

Decisão:
- ações logísticas de `/ops/orders/` devem chamar `shipping.application.shipment_commands`

Motivo:
- evita dois caminhos divergentes para envio/entrega
- mantém events de shipping nascendo do módulo dono da regra logística
- preserva compatibilidade com atalhos operacionais já existentes em Orders

Escopo executado:
- `start_shipping` cria/marca shipment enviado
- `complete_delivery` marca shipment entregue
- entrega de pedido legado em trânsito cria backfill mínimo de shipment antes de finalizar

Decisão:
- registrar transições de shipment em `ShipmentStatusHistory`

Motivo:
- shipments passam a ter trilha operacional própria, separada da timeline de orders
- auditoria fica tenant-scoped e consultável sem depender de logs externos
- idempotência dos comandos evita duplicar histórico em reexecuções

Escopo executado:
- modelo e migration de `ShipmentStatusHistory`
- histórico para envio e entrega
- source/actor explícitos para ações internas

Decisão:
- exibir resumo de `ShipmentStatusHistory` em `/ops/shipping/`

Motivo:
- operadores precisam enxergar a trilha sem acessar banco ou shell
- mantém a UI de shipping como superfície operacional principal da logística
- evita misturar timeline logística própria com timeline de orders antes de um detail dedicado

Escopo executado:
- `history_summary` no contrato admin de shipping
- coluna de histórico na listagem
- teste de renderização

Decisão:
- criar boundary de provider logístico antes de integrar transportadora real

Motivo:
- evita acoplar UI/comandos diretamente a APIs externas
- mantém tenant scope no ponto de consulta de tracking
- permite adapter manual atual e provider real futuro compartilharem contrato

Escopo executado:
- `TrackingSnapshot`
- `ShippingProviderGateway`
- `ManualShipmentProviderGateway`
- admin shipping consumindo snapshot via gateway

Decisão:
- separar status cru de provider (`provider_status`) de status interno normalizado (`normalized_status`)

Motivo:
- evita vazar semântica específica de transportadora para UI/produto
- permite fallback seguro para estados externos desconhecidos
- prepara integração futura com múltiplos providers sem mudar contrato de produto

Escopo executado:
- `tracking_status_normalizer`
- vocabulário interno inicial de tracking
- admin shipping renderizando status normalizado

Decisão:
- expor tracking normalizado no detalhe de pedido do cliente via contrato de shipping

Motivo:
- cliente precisa ver rastreio sem receber semântica crua de provider
- mantém accounts como consumidor do boundary de shipping, não dono da regra logística
- preserva fallback quando shipment ainda não existe

Escopo executado:
- `account_customer_area_queries` usando `ManualShipmentProviderGateway`
- contrato customer-facing para status/código/transportadora/link
- teste de renderização de rastreio no detalhe do pedido

Decisão:
- exibir CTA externo de tracking apenas quando `tracking_url` existir

Motivo:
- evita CTA morto em shipments sem provider/link real
- mantém a experiência do cliente clara e acionável
- preserva segurança básica de navegação externa com `noopener noreferrer`

Escopo executado:
- `delivery_tracking_action_label`
- link externo no detalhe do pedido
- teste de renderização do CTA

Decisão:
- criar serviço de sync de tracking antes de configurar polling automático

Motivo:
- separa regra de aplicação de snapshot da infraestrutura de agendamento
- permite testar transições de shipment sem provider HTTP real
- mantém tenant scope e publicação de eventos dentro do boundary de shipping

Escopo executado:
- `shipment_tracking_sync`
- sync por `tenant_id + order_number`
- transições de envio, entrega e cancelamento
- atualização de dados de rastreio sem transição

Decisão:
- expor `sync_shipments_tracking` como primeiro ponto operacional/agendável

Motivo:
- permite rodar polling manual ou via scheduler futuro
- mantém escopo restrito a shipments não terminais
- oferece filtro por tenant e limite de lote

Escopo executado:
- management command `sync_shipments_tracking`
- teste de tenant scope do comando

Decisão:
- adapter HTTP de tracking deve falhar fechado para snapshot local/manual

Motivo:
- provider externo não pode quebrar detalhe do pedido, admin ou polling
- status cru precisa passar pelo normalizador antes de chegar ao produto
- transporte injetável permite testar sem rede real

Escopo executado:
- `HttpTrackingProviderGateway`
- parser de payload HTTP
- timeout/header/token configuráveis no adapter
- fallback para `ManualShipmentProviderGateway`

Decisão:
- configurar provider de tracking por tenant via `ShippingProviderSettings`

Motivo:
- evita hardcode de URL/token no adapter HTTP
- permite ativação controlada por tenant
- preserva fallback manual quando provider não estiver configurado

Escopo executado:
- modelo `ShippingProviderSettings`
- resolver `shipping_provider_settings.get_gateway_for_tenant`
- comando de sync usando gateway resolvido por tenant

Decisão:
- expor configuração de provider em `/ops/shipping/provider/`

Motivo:
- reduz dependência de shell/seed para ativar provider por tenant
- deixa fallback manual/local explícito para operação
- mantém update passando por service tenant-scoped

Escopo executado:
- UI interna de settings do provider
- update de provider/base URL/token/timeout/ativo
- validação de base URL para HTTP ativo
- testes de isolamento por tenant

Decisão:
- não ecoar token de provider salvo na UI e preservar segredo quando update envia token vazio

Motivo:
- reduz exposição acidental de segredo em HTML
- permite alterar base URL/timeout/ativação sem rotacionar token
- mantém compatibilidade com secret hardening futuro

Escopo executado:
- `token_configured` no contrato admin
- placeholder seguro no campo de token
- preservação do token existente quando `api_token` vem vazio
- testes de masking/preservação

Decisão:
- registrar alterações de provider em `ShippingProviderSettingsHistory`

Motivo:
- configuração de provider afeta polling e experiência do cliente
- mudanças operacionais precisam de trilha tenant-scoped
- UI deve mostrar histórico mínimo sem acesso ao banco

Escopo executado:
- modelo `ShippingProviderSettingsHistory`
- registro automático em update de settings
- resumo de histórico na UI `/ops/shipping/provider/`

Decisão:
- ativar polling de tracking primeiro como task Celery explícita, sem beat automático no código

Motivo:
- task fica testável e reutilizável por scheduler futuro
- evita ativar recorrência em ambientes sem política operacional definida
- mantém limite de lote e escopo por tenant

Escopo executado:
- `shipping.sync_shipment_tracking`
- `shipping.sync_pending_shipments_tracking`
- testes diretos de task via `.run()`

Decisão:
- expor métricas Prometheus protegidas para polling/status de shipping

Motivo:
- polling de tracking precisa de visibilidade operacional por tenant
- status de shipment e histórico de eventos são os primeiros sinais úteis antes de alertas/dashboards
- token dedicado permite ativação controlada sem expor endpoint interno publicamente

Escopo executado:
- `/ops/shipping/metrics/`
- `hubx_shipping_shipment_total`
- `hubx_shipping_history_event_total`
- suporte a `SHIPPING_OBSERVABILITY_TOKEN` com fallback compatível para `NOTIFICATIONS_OBSERVABILITY_TOKEN`

Decisão:
- criar alertas Prometheus iniciais para backlog, cancelamento e ausência de sync de shipping

Motivo:
- polling sem alerta pode falhar silenciosamente
- os sinais atuais já permitem detectar gargalos operacionais simples
- regras em infra deixam ativação reprodutível por ambiente

Escopo executado:
- `shipping-alert-rules.yml`
- `shipping-scrape.example.yml`
- runbook curto de ativação em observability

Decisão:
- criar dashboard Grafana inicial para polling de shipping

Motivo:
- alertas indicam problemas, mas operação precisa de visão rápida para triagem
- status de shipments e eventos de histórico já são suficientes para um painel inicial
- manter dashboard versionado em infra facilita replicação entre ambientes

Escopo executado:
- `shipping-polling-dashboard.json`
- painéis de backlog, cancelamentos, distribuição por status e eventos recentes

Decisão:
- versionar exemplo de roteamento Alertmanager para alertas de shipping

Motivo:
- alertas de shipping precisam de canal operacional separado por domínio
- manter labels `domain` e `severity` consistentes facilita roteamento futuro
- o exemplo completa o pacote mínimo de ativação observability para shipping

Escopo executado:
- `shipping-routing.example.yml`
- receivers default, warning e critical para shipping

Decisão:
- registrar falhas de provider de tracking como evento de histórico de shipping

Motivo:
- fallback silencioso protege a experiência, mas pode esconder falha operacional
- usar `ShipmentStatusHistory` reaproveita a métrica Prometheus já exposta por `event_type`
- manter erro no `TrackingSnapshot` preserva a fronteira entre adapter HTTP e service de sync

Escopo executado:
- `provider_error_code` e `provider_error_message` no snapshot
- evento `shipment_tracking_provider_failed`
- alerta e dashboard atualizados para falhas recentes do provider

Decisão:
- carregar status HTTP e latência do provider no contrato de snapshot

Motivo:
- investigação de falhas precisa distinguir timeout, payload inválido e resposta HTTP do provider
- manter telemetria no snapshot evita acoplar models de shipping ao adapter HTTP
- histórico de erro pode expor contexto operacional sem alterar a experiência do cliente

Escopo executado:
- `provider_http_status`
- `provider_latency_ms`
- `TrackingTransportResult`
- descrição de erro enriquecida em `ShipmentStatusHistory`

Decisão:
- persistir telemetria opcional do provider em `ShipmentStatusHistory`

Motivo:
- o histórico de shipping já é tenant-scoped e exportado para Prometheus
- campos opcionais evitam criar tabela nova para o primeiro recorte de observabilidade
- métricas de status HTTP e latência podem ser derivadas sem acoplar Prometheus ao adapter

Escopo executado:
- `provider_http_status`
- `provider_latency_ms`
- métricas `hubx_shipping_provider_http_status_total` e `hubx_shipping_provider_latency_ms_avg`
- alertas de HTTP 5xx e latência alta

Decisão:
- disponibilizar pruning manual de histórico antigo de shipping

Motivo:
- polling pode gerar crescimento contínuo em `ShipmentStatusHistory`
- retenção por idade é suficiente para o primeiro controle operacional
- exigir janela mínima reduz risco de apagar histórico recente útil para suporte

Escopo executado:
- comando `prune_shipment_history`
- `--tenant-id`
- `--days >= 30`
- `--dry-run`

Decisão:
- consolidar operação de shipping em runbook dedicado

Motivo:
- a sequência de provider, polling, métricas, alertas e retenção ficou grande demais para depender apenas de waves
- produção precisa de um caminho objetivo de ativação e diagnóstico
- runbook reduz risco operacional ao ativar shipping por tenant

Escopo executado:
- `docs/modules/shipping-operational-runbook.md`
- passos de provider, polling, observabilidade, alertas e retenção
- diagnóstico inicial para backlog, ausência de sync, HTTP 5xx e latência alta

Decisão:
- consolidar operação de payments em runbook dedicado

Motivo:
- payments já tinha artefatos de observabilidade e comandos sandbox, mas faltava uma trilha única de ativação
- pagamentos são domínio crítico e precisam de diagnóstico objetivo para rollout real
- runbook reduz risco de operar webhook/redirect/provider apenas por conhecimento disperso

Escopo executado:
- `docs/modules/payments-operational-runbook.md`
- readiness sandbox
- validação de webhook
- métricas, alertas, dashboard e routing de payments

Decisão:
- não fazer pruning de `PaymentAttempt` nesta fase e criar triagem CLI

Motivo:
- tentativas de pagamento são relevantes para suporte, reconciliação e rastreabilidade financeira
- remoção exige política de retenção/legal/financeiro mais explícita
- listar pendências por tenant/status/idade entrega valor operacional com menor risco

Escopo executado:
- comando `list_payment_attempts`
- filtros por tenant, status, pendência antiga e limite
- runbook de payments atualizado

Decisão:
- expor volume de `PaymentAttempt` por tenant/status no exporter de payments

Motivo:
- alert signals mostram incidentes, mas não mostram backlog operacional de tentativas
- tentativas pendentes são sinal útil para checkout, redirect hospedado e webhook
- manter labels `tenant_id` e `status` ajuda suporte sem expor dados financeiros sensíveis

Escopo executado:
- `hubx_payments_attempt_total`
- alerta `HubxPaymentsPendingAttemptsHigh`
- painel “PaymentAttempts por status”

Decisão:
- consolidar operação de notifications em runbook dedicado

Motivo:
- notifications já tinha comandos e observabilidade, mas faltava uma trilha única de operação
- entrega de comunicação é crítica para pedido, pagamento e envio
- runbook reduz risco ao alternar dry-run/provider real e ao tratar backlog/falhas

Escopo executado:
- `docs/modules/notifications-operational-runbook.md`
- readiness, provider readiness, listagem, processamento, observabilidade e diagnóstico

Decisão:
- não fazer pruning de `EmailLog` nesta fase e melhorar triagem de logs antigos

Motivo:
- logs de notificação são trilha de entrega, suporte e auditoria de comunicação
- remoção exige política clara de retenção e possível arquivamento
- filtro por idade resolve investigação de itens travados com menor risco

Escopo executado:
- `list_email_logs --stale-hours`
- runbook de notifications atualizado com triagem de logs travados

Decisão:
- criar índice operacional central para runbooks críticos

Motivo:
- shipping, payments e notifications passaram a ter runbooks dedicados
- operação precisa de uma porta de entrada única para ativação, monitoramento e suporte
- índice reduz risco de documentos críticos ficarem escondidos em módulos isolados

Escopo executado:
- `docs/operational-runbooks.md`
- referência em `docs/modules-index.md`
- referência em `infra/observability/README.md`

Decisão:
- manter estoque em `catalog.ProductVariant` e operar exceções via `orders`

Motivo:
- preço/estoque pertencem à variante, não ao produto
- exceções atuais são observadas no contexto de pedidos e fulfillment
- criar módulo `inventory` separado agora adicionaria fronteira antes de existir ledger dedicado

Escopo executado:
- comando `list_inventory_exceptions`
- métricas `hubx_inventory_exception_*`
- observability pack de inventory
- runbook `docs/modules/inventory-operational-runbook.md`

Decisão:
- tratar problemas de publicação de catálogo como triagem operacional, não como bloqueio automático

Motivo:
- catálogo ainda não tem workflow formal de aprovação editorial
- comando e métricas entregam visibilidade sem impedir operação existente
- problemas como variante ausente, preço vazio e status inconsistente precisam aparecer antes de campanhas/publicação

Escopo executado:
- comando `list_catalog_publication_issues`
- service `catalog_publication_issues`
- métrica `hubx_catalog_publication_issue_total`
- observability pack e runbook de catalog

### Decisão: problemas de dados de clientes viram sinais operacionais tenant-scoped
Decisão:
- manter inconsistências legadas de `Customer`/`CustomerAddress` como triagem operacional explícita, não como correção automática
- expor `order_email_fallback` para orientar backfill seguro de `Order.customer`
- exigir `tenant_id` no comando e token dedicado no endpoint de métricas

Motivo:
- customer area e pós-compra dependem de dados mínimos confiáveis
- pedidos legados ainda podem depender de `tenant + customer_email`
- corrigir cadastro/endereço/pedido automaticamente sem workflow de backfill aumenta risco de alteração incorreta

Escopo executado:
- comando `list_customer_data_issues`
- service `customer_data_issues`
- métrica `hubx_customer_data_issue_total`
- observability pack e runbook de customers

### Decisão: customer area consome qualidade de dados como visibility, não como bloqueio visual
Decisão:
- `accounts` passa a expor `customer_data_mode` e `customer_data_issue_codes` na visibility operacional da customer area
- o sinal é derivado de `customers.application.customer_data_issues`
- a experiência do cliente não é bloqueada automaticamente por esse sinal nesta fase

Motivo:
- pós-compra precisa saber se vínculo, endereço e dados mínimos estão confiáveis
- bloquear ou esconder telas por dados legados poderia piorar suporte e retenção
- visibility interna prepara ativações futuras com menor risco

### Decisão: backfill de vínculos explícitos deve ser tenant-scoped na operação
Decisão:
- `backfill_customer_links` passa a aceitar `--tenant-id`
- o comando também aceita `--only profiles|orders|all`
- o resumo passa a informar `order_email_fallback_remaining`
- compatibilidade global sem `tenant_id` permanece apenas como legado operacional
- skips passam a ser separados por motivo:
  - missing email
  - no match
  - ambiguous

Motivo:
- `order_email_fallback` agora é um sinal observável por tenant
- rodar backfill global aumenta ruído e risco operacional
- recortes por tenant e por tipo permitem aplicar correções menores e validar o efeito no mesmo ciclo
- motivos de skip reduzem ambiguidade operacional antes de qualquer correção manual

### Decisão: vitrine de catálogo ganha sinal determinístico de decisão comercial
Decisão:
- `storefront_catalog_queries` passa a derivar `catalog_card_decision_signal`
- o sinal não altera layout nem fluxo de compra nesta fase
- o sinal classifica a intenção principal do card: oferta, decisão rápida, reserva, reposição, destaque ou compra pronta
- o exporter de catálogo também passa a expor `hubx_catalog_card_decision_signal_total`

Motivo:
- a vitrine já tinha copy e ranking, mas faltava um contrato compacto para testes e futuras métricas
- usar sinal determinístico evita depender de parsing de textos longos
- o recorte respeita a fronteira do catálogo e usa apenas dados do próprio produto/variante
- observar a composição da vitrine por tenant ajuda merchandising sem criar workflow editorial novo

### Decisão: inconsistências de sessão de checkout viram triagem operacional
Decisão:
- sessões de checkout com dados incompletos, stale, total divergente ou vínculo de pedido ausente passam a ser sinais operacionais tenant-scoped
- o comando `list_checkout_session_issues` exige `tenant_id`
- o exporter expõe `hubx_checkout_session_issue_total{tenant_id,issue}`
- nenhuma sessão é corrigida, expirada ou removida automaticamente nesta fase

Motivo:
- checkout é ponto transacional sensível entre vitrine, pedidos e pagamentos
- corrigir sessão automaticamente pode criar pedido indevido, alterar intenção do cliente ou mascarar drift
- alertar por tenant permite triagem segura antes de introduzir política formal de expiração/retention

### Decisão: sessões abertas antigas de checkout são expiradas, não removidas
Decisão:
- adicionar `expire_checkout_sessions` como ação operacional tenant-scoped
- exigir `--tenant-id`
- exigir janela mínima de 6 horas para evitar expiração agressiva
- preservar sessões `completed`
- marcar sessões candidatas como `expired` em vez de deletar registros

Motivo:
- sessões de checkout representam intenção transacional e podem ser úteis para suporte/auditoria
- deleção reduziria rastreabilidade e poderia mascarar problemas de sessão
- expiração explícita reduz reutilização insegura de sessões antigas sem alterar pedidos, pagamentos ou estoque

### Decisão: session_key explícito de checkout não usa fallback demonstrativo
Decisão:
- sessão `expired` passa a ser serializada como estado read-only
- `session_key` inexistente retorna indisponibilidade explícita
- fallback demonstrativo de checkout não é usado quando o request carrega `session_key`

Motivo:
- links antigos não podem parecer uma compra ativa
- fallback com itens de showcase mascara estados inválidos e dificulta suporte
- a recuperação segura deve orientar retorno ao produto para criar/reutilizar uma sessão aberta válida

### Decisão: ativação pelo produto não reutiliza sessão open stale
Decisão:
- `_get_reusable_open_session` passa a reutilizar apenas sessões abertas recentes
- sessões `open` com `expires_at` vencido ou `updated_at` acima da janela de 24 horas são marcadas como `expired`
- a ativação cria nova sessão quando a candidata existente não é mais segura

Motivo:
- a retomada pelo produto é a porta segura depois de sessão expirada
- reaproveitar uma sessão antiga quebraria a semântica de expiração e poderia carregar itens/totais desatualizados
- manter reuso apenas para sessões recentes preserva carrinho multi-item sem mascarar abandono antigo

### Decisão: checkout expõe lifecycle de sessão separado dos issues operacionais
Decisão:
- adicionar `hubx_checkout_session_status_total{tenant_id,status}`
- manter `hubx_checkout_session_issue_total{tenant_id,issue}` para problemas acionáveis
- usar `status=expired` como estoque observável de sessões retiradas do fluxo ativo

Motivo:
- `open_stale` representa backlog que ainda precisa de ação
- `expired` representa sessão já bloqueada/retenção operacional
- separar as duas leituras evita tratar sessão já expirada como incidente ativo

### Decisão: pruning de sessões expiradas exige janela longa e tenant_id
Decisão:
- adicionar `prune_expired_checkout_sessions`
- remover apenas sessões `expired`
- exigir `--tenant-id`
- exigir `--older-than-days >= 180`
- manter `--dry-run` para estimativa prévia

Motivo:
- sessões expiradas ainda representam intenção transacional recente e podem apoiar suporte/auditoria
- pruning global ou com janela curta pode apagar contexto útil
- sem tabela de archive, a remoção deve ser explícita, conservadora e operada por tenant

### Decisão: recovery copy de checkout diferencia recriação e revisão
Decisão:
- usar `Voltar ao produto` quando a sessão atual não é confiável para seguir
- reservar `Reabrir checkout` para casos em que a própria sessão ainda pode ser revisada com segurança
- remover `Revisar produto` como rótulo concorrente nessa superfície de recovery

Motivo:
- reabrir uma sessão com drift, estoque inconsistente ou completion indisponível pode parecer que o fluxo ainda é seguro
- voltar ao produto recria a sessão pela fonte comercial atualizada
- vocabulário consistente reduz ambiguidade para cliente, suporte e futuros analytics de recovery

### Decisão: result codes de checkout ganham taxonomia de recovery
Decisão:
- classificar result codes em `family`, `severity` e `recovery_action`
- expor a classificação no contexto da página como `checkout_result_taxonomy`
- não persistir eventos novos nesta etapa

Motivo:
- analytics futuros precisam distinguir session drift, inventory conflict, snapshot conflict e readiness sem parsear copy
- a classificação reduz divergência entre texto exibido e ação recomendada
- manter derivado no contexto evita acoplar a UI a um novo modelo operacional antes da necessidade real

### Decisão: analytics de recovery começa com métrica info, não contador
Decisão:
- expor `hubx_checkout_recovery_result_info{code,family,severity,recovery_action}`
- centralizar a taxonomia em `checkout.application.checkout_result_taxonomy`
- não criar contador de ocorrências sem evento persistido

Motivo:
- o endpoint Prometheus não observa cada redirect/result code real
- contar ocorrências sem persistência criaria métrica enganosa
- a métrica info prepara dashboards e consultas para uma futura trilha de eventos reais

### Decisão: eventos de recovery do checkout são persistidos por tenant
Decisão:
- adicionar `CheckoutRecoveryEvent`
- gravar apenas result codes conhecidos pela taxonomia
- exigir `tenant_id` explícito no command service
- vincular `CheckoutSession` somente quando a sessão pertence ao mesmo tenant

Motivo:
- analytics de produto precisa de ocorrência real, não só catálogo de result codes
- recovery pode envolver sessão expirada, ausente ou insegura, então o vínculo com sessão precisa ser opcional
- impedir associação cross-tenant mantém a trilha segura para futuras métricas e consultas

### Decisão: métricas de recovery contam eventos persistidos
Decisão:
- expor `hubx_checkout_recovery_event_total{tenant_id,code,family,severity,recovery_action}`
- derivar a contagem de `CheckoutRecoveryEvent`
- manter labels de baixa cardinalidade e sem identificadores de sessão, pedido ou cliente

Motivo:
- a métrica info descreve a taxonomia, mas não mede ocorrência real
- eventos persistidos permitem analytics de produto por tenant sem inventar volume
- labels sensíveis ou de alta cardinalidade prejudicariam Prometheus e poderiam expor contexto de cliente

### Decisão: eventos de recovery têm pruning conservador
Decisão:
- adicionar `prune_checkout_recovery_events`
- exigir `--tenant-id`
- exigir `--older-than-days >= 180`
- manter `--dry-run` para estimativa prévia

Motivo:
- eventos de recovery podem crescer com page views e refreshes
- analytics recente ainda é útil para produto e suporte por tenant
- pruning explícito evita crescimento indefinido sem apagar sinais recentes prematuramente

### Decisão: recovery do checkout está em Go técnico com pré-requisitos operacionais
Decisão:
- considerar a abordagem de checkout recovery tecnicamente pronta
- bloquear produção real apenas por pré-requisitos operacionais:
  - migration aplicada
  - token de observabilidade configurado
  - scrape/dashboard ativados
  - pruning testado em `--dry-run`

Motivo:
- tenant scope está explícito nos comandos, eventos e métricas
- analytics de recovery não cria pedido, pagamento ou alteração de estoque
- eventos reais já sustentam métricas sem inventar ocorrência
- os riscos restantes são de ativação operacional, não de contrato funcional

### Decisão: não reabrir payments customer experience agora
Decisão:
- não iniciar nova implementação pequena em `Payments customer experience` neste momento
- manter payments como eixo já suficiente para esta fase em:
  - comunicação customer-facing
  - hosted redirect/return
  - retry/retomada
  - triagem e métricas operacionais

Motivo:
- a documentação e o código já cobrem pedido salvo, pendência, falha, retorno hospedado e tentativa segura
- continuar agora tenderia a gerar microcopy, painéis ou estados adicionais com baixo retorno
- os próximos ganhos relevantes em payments são maiores e devem entrar como roadmap específico: métodos reais, conciliação, refund/estorno ou backoffice financeiro

### Decisão: merchant operations começa por cockpit de leitura
Decisão:
- criar `/ops/` como cockpit operacional inicial para o lojista
- manter `accounts` como módulo responsável pelo shell admin/owner-facing
- consumir sinais de `orders`, `catalog`, `customers`, `shipping` e `owners` por application services
- não criar novas escritas, eventos ou regras de domínio nesta primeira wave

Motivo:
- o maior ganho funcional agora é orientar o lojista sobre onde agir, não adicionar mais detalhes em checkout/payments
- o cockpit reduz navegação cega entre módulos e expõe bloqueios operacionais já existentes
- o risco multi-tenant permanece baixo porque os sinais respeitam `tenant_id` resolvido pela request

### Decisão: PDP conversion começa por decision checks
Decisão:
- adicionar uma faixa curta de decisão na PDP antes do formulário/CTA
- derivar os sinais em `catalog.application.storefront_catalog_queries`
- cobrir preço, disponibilidade e próximo passo seguro sem criar evento ou escrita nova

Motivo:
- a PDP já tinha muitos sinais corretos, mas espalhados em textos longos
- conversão tende a melhorar quando o cliente confirma rapidamente preço, variante e disponibilidade antes do CTA
- o recorte preserva multi-tenant e não altera checkout, estoque ou pedidos

### Decisão: pausar waves locais e auditar status por módulo
Decisão:
- registrar uma matriz de readiness por módulo em `docs/system-module-status-audit.md`
- classificar módulos como maduro, bom o suficiente, parcial, skeleton ou bloqueador
- usar a matriz para escolher próximas trilhas por ROI em vez de continuar refinando módulos já bons

Motivo:
- várias trilhas críticas já atingiram suficiência para esta fase
- seguir onda por onda sem mapa global aumenta o risco de polir áreas de baixo retorno
- a auditoria expõe módulos skeleton que podem virar os próximos verdadeiros gargalos de produto ou produção

### Decisão: próxima trilha principal é Cart & Promotion Conversion Foundation
Decisão:
- priorizar `cart` como próximo domínio funcional
- incluir `coupons` apenas como contrato mínimo posterior, sem motor promocional completo
- adiar `reviews`, `pages`, `newsletter`, `api_keys`, `audit` e `subscriptions` até o próximo corte estratégico

Motivo:
- a PDP já inicia checkout, mas não existe carrinho persistente real entre descoberta e finalização
- isso limita multi-item, revisão antes do checkout, aplicação de cupom e campanhas básicas
- a lacuna está diretamente no funil de receita e tem maior ROI imediato que novas melhorias em módulos já bons

Corte de risco:
- `cart` não deve criar pedido
- `cart` não deve decidir pagamento
- `cart` não deve calcular frete final
- `checkout` continua sendo o orquestrador da finalização

### Decisão: cart nasce como intenção pré-checkout
Decisão:
- definir `cart` como domínio de intenção persistente antes da finalização
- manter `CheckoutSession` como dono do carrinho leve dentro do checkout
- implementar handoff futuro de `Cart` para `CheckoutSession`, sem substituir o fluxo atual de PDP direto para checkout nesta primeira etapa

Motivo:
- o checkout atual já suporta itens, quantidades e revisão dentro da sessão
- criar `cart` como duplicação de `CheckoutSessionItem` aumentaria acoplamento e risco
- o valor real de `cart` está antes do checkout: persistência de intenção, multi-item, cupom e campanhas

### Decisão: cart model skeleton sem integração PDP/checkout
Decisão:
- criar modelos e command service mínimos do módulo `cart`
- manter a integração com PDP e checkout fora desta wave
- preservar o fluxo atual PDP → `CheckoutSession` até o handoff cart → checkout ser desenhado

Motivo:
- o primeiro risco era estrutural: tirar `cart` do estado skeleton sem quebrar o fluxo de compra existente
- ligar UI, PDP e checkout junto com a modelagem aumentaria o raio da mudança
- agora existe base persistida tenant-scoped para avançar com superfície storefront em uma wave separada

### Decisão: primeira superfície de cart será leitura em /cart/
Decisão:
- implementar primeiro uma página storefront `/cart/` de leitura
- não ligar PDP nem checkout nesta etapa
- não criar mutações HTTP ou aplicação de cupom ainda

Motivo:
- a surface de leitura valida o domínio `cart` no storefront com baixo risco
- PDP e checkout já funcionam hoje por `CheckoutSession`; alterar esse comportamento cedo demais pode quebrar o funil
- a página `/cart/` cria base visual e contratual para adicionar item, editar quantidade e handoff em waves separadas

### Decisão: /cart/ entra como surface read-only
Decisão:
- publicar `/cart/` como página storefront de leitura do carrinho ativo
- resolver carrinho por `tenant + session_key`
- não criar carrinho durante leitura
- manter PDP e checkout sem alteração funcional nesta etapa

Motivo:
- a surface valida o novo domínio persistido com risco baixo
- empty state seguro evita fallback enganoso
- isolamento por tenant/session foi coberto antes de adicionar mutações públicas

### Decisão: PDP adiciona ao carrinho por intent explícito
Decisão:
- implementar a primeira ponte PDP → cart como ramificação do POST existente por `intent=add_to_cart`
- preservar o caminho atual PDP → `CheckoutSession` para `intent=buy_now` ou ausência de intent
- redirecionar add-to-cart bem-sucedido para `/cart/`
- manter `cart.application.cart_commands` como dono da mutação de carrinho

Motivo:
- a PDP já resolve tenant, produto e variante com o contrato de storefront
- duplicar essa resolução em outro endpoint aumentaria risco de divergência
- preservar o buy-now atual reduz risco no funil enquanto o domínio `cart` amadurece
- o handoff `Cart → CheckoutSession` ainda deve ser uma wave separada

### Decisão: cart storefront ganha mutações mínimas antes de promoções
Decisão:
- permitir incrementar, decrementar e remover itens em `/cart/`
- manter as mutações via POST simples na própria página
- delegar escrita exclusivamente a `cart.application.cart_commands`

Motivo:
- a surface de carrinho só fica funcional se o cliente puder corrigir quantidade antes do checkout
- mutações pequenas têm menor risco que cupom, frete ou handoff
- o command service já aplica tenant scope por `cart_id + tenant_id`

### Decisão: handoff cart checkout cruza módulos por application services
Decisão:
- `cart.application.cart_checkout_queries` expõe payload de intenção para checkout
- `checkout.application.checkout_activation_commands.activate_from_cart(...)` cria a sessão finalizável
- `cart_commands.mark_converted(...)` marca o carrinho após sucesso

Motivo:
- cart não deve criar `CheckoutSession` diretamente
- checkout não deve consultar detalhes internos de cart sem contrato de aplicação
- carrinho convertido deixa uma trilha auditável sem criar pedido ou pagamento

### Decisão: cupom começa como intenção, não motor promocional
Decisão:
- `cart` pode capturar e armazenar `coupon_code`
- `cart` não deve validar elegibilidade promocional complexa
- `coupons` será o dono futuro de validação e cálculo de desconto
- a próxima execução deve expor apply/remove de cupom sem inventar desconto enquanto `coupons` ainda é skeleton

Motivo:
- aplicar desconto real sem regras de cupom criaria comportamento fictício e risco financeiro
- centralizar elegibilidade em `coupons` evita espalhar regra promocional por cart, checkout e orders
- uma surface de intenção prepara UX e contrato com baixo risco

### Decisão: coupon intent no cart mantém desconto zerado
Decisão:
- adicionar apply/remove de cupom no carrinho como intenção promocional
- persistir `coupon_code` normalizado no `Cart`
- manter `discount_total=0.00` até existir validação real em `coupons`
- exibir mensagem explícita de validação promocional indisponível

Motivo:
- a UI passa a suportar a jornada esperada de cupom
- o sistema não inventa economia nem altera total sem regra promocional auditável
- o próximo passo pode focar no service skeleton de `coupons` com contrato claro

### Decisão: coupons começa por validation service conservador
Decisão:
- definir `coupons.application.coupon_validation_queries.validate_cart_coupon(...)` como contrato mínimo futuro
- exigir `tenant_id`, `coupon_code` e `cart_snapshot`
- retornar result codes explícitos, incluindo `coupon-unavailable`
- permitir que `cart` aplique desconto somente quando receber `coupon-valid`

Motivo:
- o módulo `coupons` ainda não possui modelo nem regra persistida
- um service conservador permite plugar cart sem criar desconto fictício
- `coupon-unavailable` mantém o fallback seguro e auditável até existir motor promocional real

### Decisão: cart consome coupon validation skeleton sem aplicar desconto
Decisão:
- criar `coupons.application.coupon_validation_queries`
- retornar `coupon-unavailable` enquanto não houver modelo real de cupom
- fazer `cart_commands.apply_coupon_intent(...)` chamar o service
- manter `discount_total=0.00` para qualquer resultado diferente de `coupon-valid`

Motivo:
- o boundary real entre cart e coupons passa a existir em código
- o sistema continua conservador financeiramente
- a próxima evolução pode focar no modelo mínimo de `Coupon`, não em refazer integração

### Decisão: Coupon mínimo pode ser criado com escopo percentual/fixo
Decisão:
- criar futuramente `Coupon` tenant-scoped com código único por tenant
- limitar o primeiro recorte a `percent` e `fixed`
- permitir apenas status ativo/inativo e janela temporal opcional
- manter fora limites de uso, segmentação, frete grátis, campanhas e stack promocional

Motivo:
- o contrato `coupons.application` já existe e protege `cart` de conhecer ORM interno
- percentual/fixo simples cobre o primeiro ganho funcional sem virar motor promocional
- manter o modelo pequeno reduz risco financeiro e multi-tenant

### Decisão: Coupon mínimo entra em produção de domínio
Decisão:
- criar modelo `Coupon` no módulo `coupons`
- validar cupom por tenant, código, status e janela temporal
- calcular apenas desconto percentual ou fixo simples
- manter `cart` consumindo validação por application service

Motivo:
- o service skeleton já isolou a fronteira entre cart e coupons
- o modelo mínimo desbloqueia desconto real sem campanha avançada
- constraints por tenant reduzem risco de vazamento cross-tenant

### Decisão: admin de cupons começa lite em /ops/coupons/
Decisão:
- criar futuramente uma surface `/ops/coupons/` no módulo `coupons`
- permitir primeiro apenas listagem e criação
- escrever por `coupons.application.admin_coupon_commands`
- manter edição avançada, exclusão e segmentação fora do primeiro corte

Motivo:
- cupom real já existe no domínio, mas ainda não há operação tenant-scoped para lojista
- uma surface lite desbloqueia uso real sem motor promocional complexo
- manter o admin no módulo `coupons` preserva fronteira com `accounts`, `cart` e `checkout`

### Decisão: /ops/coupons/ publica admin lite tenant-scoped
Decisão:
- publicar `/ops/coupons/` e `/ops/coupons/new/`
- listar e criar cupons via services de `coupons.application`
- adicionar navegação no cockpit `/ops/`
- manter a surface sem edição/exclusão por enquanto

Motivo:
- o lojista passa a operar cupons reais sem depender do Django admin técnico
- a criação segue validações tenant-scoped e evita duplicidade por loja
- o recorte ainda não introduz regra promocional avançada

### Decisão: cupom aplicado viaja para checkout como snapshot
Decisão:
- transportar `coupon_code` e `discount_total` do carrinho para checkout apenas quando houver desconto aplicado
- adicionar futuramente `promotion_snapshot` em `CheckoutSession`
- checkout deve persistir o snapshot recebido sem recalcular promoção
- `coupons` continua sendo o único dono da validação promocional

Motivo:
- o cliente vê o desconto no carrinho e o checkout deve preservar esse contexto
- recalcular no checkout pode divergir se a regra de cupom mudar no meio do funil
- snapshot mantém auditabilidade sem espalhar regra promocional

### Decisão: CheckoutSession persiste snapshot promocional do cart
Decisão:
- adicionar `coupon_code` e `promotion_snapshot` em `CheckoutSession`
- transportar snapshot somente quando o carrinho tem cupom aplicado com desconto
- manter cupom inválido/salvo sem desconto fora do checkout aplicado

Motivo:
- checkout precisa preservar o contexto comercial visto pelo cliente
- não recalcular no checkout evita divergência de regra promocional
- o próximo passo pode propagar snapshot para pedido sem depender do carrinho original

### Decisão: pedido deve guardar snapshot promocional sem recalcular cupom
Decisão:
- copiar `coupon_code` e `promotion_snapshot` de `CheckoutSession` para `Order`
- preservar `discount_total` já usado no checkout
- não chamar `coupons` durante criação do pedido
- manter pedidos imutáveis em relação a mudanças futuras no cupom

Motivo:
- pedido precisa ser auditável mesmo se o cupom for alterado depois
- checkout já representa a decisão comercial apresentada ao cliente
- recalcular no pedido espalharia regra promocional para `orders`

### Decisão: Order persiste snapshot promocional do checkout
Decisão:
- adicionar `coupon_code` e `promotion_snapshot` em `Order`
- copiar snapshot apenas quando a sessão tem cupom aplicado com desconto
- manter pedidos sem cupom com snapshot vazio

Motivo:
- fecha a trilha de auditoria cart → checkout → order
- evita depender do estado futuro do cupom para explicar um pedido antigo
- preserva `orders` como armazenamento transacional, não motor promocional

### Decisão: cupom aplicado aparece primeiro em detalhes de pedido
Decisão:
- expor cupom aplicado primeiro no detalhe do pedido da área do cliente
- expor também no detalhe/admin orders para suporte e lojista
- adiar notificações/e-mails até revisão específica de copy e payload de evento

Motivo:
- detalhes de pedido já mostram totais e desconto, então são o lugar natural para explicar o cupom
- admin orders precisa auditabilidade operacional do snapshot
- notificações são superfície transacional sensível e não devem ser alteradas sem revisão de mensagem

### Decisão: notificações não exibem cupom aplicado nesta fase
Decisão:
- manter e-mails/notificações sem menção direta a cupom aplicado nesta etapa
- usar CTA para detalhe do pedido como superfície canônica de explicação do desconto
- não expandir `order.created` com payload promocional agora
- permitir copy futura somente a partir do snapshot em `Order`

Motivo:
- notifications opera por intents estáticos e não deve virar motor de interpretação promocional
- o detalhe do pedido já é tenant-scoped, auditável e exibe o snapshot do cupom
- incluir cupom em e-mail exige revisão específica de copy, público e enriquecimento de envelope

### Decisão: uso de cupom deve virar ledger, não contador simples
Decisão:
- não adicionar `usage_count` em `Coupon` nesta fase
- manter `Order.promotion_snapshot` como fonte suficiente para explicação/auditoria leve
- quando necessário, criar um ledger tenant-scoped de resgate de cupom ligado a pedido
- registrar uso após criação do pedido, sem recalcular promoção

Motivo:
- contador mutável em `Coupon` não lida bem com concorrência, idempotência, cancelamento e auditoria
- ledger preserva histórico mesmo se o cupom mudar depois
- limites de uso podem ser construídos depois sobre uma base auditável

### Decisão: CouponRedemption nasce como command idempotente de coupons
Decisão:
- `CouponRedemption` pertence ao módulo `coupons`
- `checkout` deve chamar um application command de `coupons` após criar `Order`
- o command deve resolver `Order` por `tenant_id + order_number` e criar ledger a partir do snapshot do pedido
- não expandir `order.created` para carregar dados promocionais nesta etapa

Motivo:
- mantém `checkout` como orquestrador sem escrever detalhes internos de coupons
- mantém `orders` como fonte histórica do snapshot aplicado
- evita acoplar notifications/event payload ao ledger promocional cedo demais

### Decisão: checkout registra redemption após criar pedido
Decisão:
- `checkout_completion_commands` chama `record_order_coupon_redemption(...)` depois de materializar `Order`
- o ledger é criado apenas para pedido com cupom, desconto real e `promotion_snapshot`
- o command é idempotente por tenant/pedido/código
- o ledger preserva snapshot de código, desconto e payload promocional

Motivo:
- fecha a trilha cart → checkout → order → redemption sem recalcular promoção
- mantém a contabilidade em `coupons`
- evita duplicidade em retry de checkout concluído

### Decisão: admin de cupons mostra agregados mínimos de redemption
Decisão:
- expor uso de cupom primeiro como coluna agregada na listagem `/ops/coupons/`
- usar apenas `CouponRedemption` para contar usos e somar descontos
- não criar detalhe de cupom, analytics, filtros por data ou últimos pedidos nesta fase

Motivo:
- lojista ganha visibilidade operacional básica sem virar dashboard de campanha cedo demais
- o ledger já pertence a `coupons`, então a leitura respeita boundary
- agregados simples evitam consultar `orders` para recomputar histórico promocional

### Decisão: agregados de redemption vivem na listagem de cupons
Decisão:
- `/ops/coupons/` mostra coluna `Resgates`
- a coluna usa contagem de `CouponRedemption.applied` e soma de `discount_total_snapshot`
- cupons sem uso mostram estado explícito de ausência

Motivo:
- entrega visibilidade útil ao lojista com superfície mínima
- mantém analytics avançado fora do MVP de cupom
- usa o ledger como fonte canônica de uso promocional

### Decisão: reversão de coupon redemption começa por cancelamento admin
Decisão:
- não tratar `payment.refunded` nesta fase
- implementar reversão primeiro a partir de `admin_order_commands.cancel_order(...)`
- `orders` deve acionar command explícito de `coupons`, sem editar ledger diretamente
- reversão deve ser idempotente e marcar `CouponRedemption` como `reversed`

Motivo:
- refund financeiro ainda não existe como fluxo suportado
- cancelamento admin já é tenant-scoped e possui semântica operacional explícita
- manter a reversão em `coupons` preserva ownership do ledger promocional

### Decisão: cancelamento admin reverte redemption via coupons command
Decisão:
- `reverse_order_coupon_redemption(...)` marca redemptions `applied` como `reversed`
- `admin_order_commands.cancel_order(...)` chama esse command durante o cancelamento
- requests legadas sem tenant explícito usam `order.tenant_id` para manter scope seguro

Motivo:
- fecha o lifecycle mínimo applied → reversed sem criar refund financeiro
- mantém `orders` fora da escrita direta no ledger promocional
- preserva idempotência para cancelamentos repetidos

### Decisão: agregados principais de cupom representam uso ativo
Decisão:
- coluna `Resgates` continua contando apenas `CouponRedemption.applied`
- redemptions `reversed` não entram no número principal
- reversões devem aparecer como informação complementar, não como uso vigente

Motivo:
- cancelamentos não devem inflar consumo operacional ativo do cupom
- limites futuros de uso precisam começar de uma semântica de uso vigente
- auditoria de reversão é útil, mas não deve confundir o número principal da lista

### Decisão: reversões aparecem como complemento em Resgates
Decisão:
- manter uma única coluna `Resgates` na listagem de cupons
- mostrar uso ativo como número principal
- mostrar contagem de reversões no mesmo label quando existir
- manter `redemption_count` como alias de uso ativo por compatibilidade

Motivo:
- deixa cancelamentos visíveis sem criar dashboard de campanha
- evita multiplicar superfícies administrativas cedo demais
- preserva a leitura principal como uso vigente

### Decisão: não criar detalhe de cupom nesta fase
Decisão:
- encerrar o recorte promocional mínimo com listagem agregada de cupons
- adiar detalhe de cupom, últimos redemptions, filtros por período e analytics
- seguir para hardening de confiabilidade de cart/checkout

Motivo:
- admin de cupons já cobre criação, status, validade, uso ativo e reversões
- detalhe de cupom puxaria escopo de campanha/analytics antes de haver limites ou segmentação
- carrinho e checkout são agora o caminho crítico para robustez do produto

### Decisão: add-to-cart continua acumulativo, idempotência será explícita
Decisão:
- manter `cart_commands.add_item(...)` acumulativo quando não houver chave de idempotência
- tratar double-submit/retry com `idempotency_key` opcional em wave própria
- registrar mutações idempotentes de forma tenant-scoped no domínio `cart`

Motivo:
- cliques repetidos podem ser intenção real de aumentar quantidade
- retries técnicos precisam de proteção sem quebrar a semântica existente
- separar add acumulativo de replay protection evita comportamento surpreendente no PDP

### Decisão: CartMutation protege replay de add-to-cart
Decisão:
- criar `CartMutation` com unique por tenant/cart/mutation_key
- `add_item(...)` aceita `idempotency_key` opcional
- replay da mesma chave retorna snapshot original sem incrementar novamente
- PDP passa a enviar `cart_idempotency_key` hidden

Motivo:
- protege double-submit sem impedir cliques intencionais com novas chaves
- mantém a idempotência dentro do domínio `cart`
- evita acoplar proteção de replay ao checkout ou à sessão global

### Decisão: cart terá guarda leve de quantidade por estoque
Decisão:
- adicionar validação leve de estoque em `cart.application` para `add_item(...)` e `update_quantity(...)`
- resolver disponibilidade por `tenant_id + variant_sku`
- respeitar inventário não rastreado e backorder permitido
- bloquear quantidade acima de `stock - reserved_stock` com result code explícito
- manter `checkout.application` como autoridade final contra corrida de estoque

Motivo:
- melhora a experiência ao impedir erro óbvio antes do checkout
- evita transformar carrinho em motor de reserva de inventário
- preserva a regra de que pedido e baixa/reserva real não pertencem ao carrinho

### Decisão: guarda de estoque do cart preserva quantidade anterior
Decisão:
- `add_item(...)` rejeita incremento que excede estoque livre sem alterar o item existente
- `update_quantity(...)` rejeita quantidade final acima do estoque livre sem salvar alteração
- PDP e `/cart/` comunicam o bloqueio via flash message
- não aplicar clamp automático nesta fase

Motivo:
- preservar quantidade anterior evita surpresa silenciosa no carrinho
- flash message deixa a restrição explícita sem inventar reserva de estoque
- clamp automático exigiria copy e semântica adicional para explicar ajuste parcial

### Decisão: conflito final de estoque precisa virar payload por item
Decisão:
- manter `checkout.application` como revalidação final antes de criar pedido
- não tentar resolver corrida de estoque apenas no carrinho
- evoluir `checkout-completion-stock-conflict` para carregar detalhes por item afetado
- não ajustar quantidade automaticamente sem confirmação do cliente

Motivo:
- estoque pode mudar depois do handoff cart → checkout
- bloquear criação do pedido continua correto
- UX atual já é segura, mas genérica demais para cliente decidir o próximo passo
- payload por item permite recuperar a sessão sem criar pedido parcial nem inventar reserva

### Decisão: payload de conflito de estoque é leitura pós-redirect
Decisão:
- calcular `inventory_conflicts` no GET do checkout quando `result=checkout-completion-stock-conflict`
- usar `CheckoutSessionItem` e `ProductVariant` atual para montar SKU, título, quantidade solicitada e estoque livre
- mudar a recovery action para `review_current_session`
- não persistir snapshot de conflito nesta fase

Motivo:
- o conflito é uma condição transitória de disponibilidade, não um novo estado de checkout
- recalcular no GET evita migration e mantém a tela alinhada ao estoque atual
- a sessão pode ser revisada sem criar pedido parcial nem alterar quantidade automaticamente

### Decisão: reconciliação de estoque deve ser ação explícita na sessão
Decisão:
- reutilizar `checkout_session_commands.mutate_item(...)` para reconciliar conflitos finais de estoque
- adicionar futuramente operação `set_quantity` para reduzir item até o estoque livre atual
- remover item explicitamente quando `available_quantity == 0`
- manter criação de pedido bloqueada até o cliente confirmar nova tentativa

Motivo:
- a sessão de checkout já é o boundary correto para revisão final
- ação explícita evita ajuste silencioso e preserva confiança do cliente
- reaproveitar mutações existentes reduz escopo e mantém totais recalculados no mesmo command service

### Decisão: set_quantity é mutação normal da CheckoutSession
Decisão:
- adicionar `set_quantity` em `checkout_session_commands.mutate_item(...)`
- expor CTAs no bloco de conflito final de estoque
- reduzir para estoque livre apenas após POST explícito do cliente
- usar `remove` quando a disponibilidade atual for zero

Motivo:
- mantém a reconciliação no mesmo boundary de edição de itens do checkout
- evita novo subfluxo transacional antes de haver reserva de estoque
- preserva a revalidação final: depois de corrigir, o cliente ainda precisa concluir novamente

### Decisão: reconciliação não conclui pedido automaticamente
Decisão:
- manter o cliente na revisão após corrigir conflito de estoque
- exigir novo clique em “Criar pedido inicial”
- usar feedback específico de reconciliação em vez de copy genérica de item atualizado/removido
- preservar a revalidação final no novo POST de conclusão

Motivo:
- reconciliação altera itens e totais que o cliente precisa revisar
- estoque pode mudar novamente entre a correção e a conclusão
- conclusão automática após ajuste de quantidade seria surpreendente e arriscada

### Decisão: feedback de reconciliação usa result codes próprios
Decisão:
- usar `checkout-inventory-reconciled` para redução até estoque disponível
- usar `checkout-inventory-item-removed` para remoção de item indisponível
- classificar ambos como `inventory/success/review_current_session`
- manter `checkout-item-updated` e `checkout-item-removed` para mutações comuns

Motivo:
- a mecânica de sessão é a mesma, mas a intenção do cliente é recuperação de estoque
- copy específica deixa claro que os totais mudaram e o pedido ainda não nasceu
- separar result codes melhora analytics e evita ambiguidade operacional

### Decisão: encerrar Cart Reliability com Go técnico
Decisão:
- considerar a trilha Cart Reliability suficiente para esta fase
- não continuar refinando carrinho/checkout em micro-waves agora
- aceitar como riscos futuros reservation engine, allocation, baixa pós-pagamento e analytics avançado
- recomendar próxima abordagem em checkout/payment execution ou inventory fulfillment

Motivo:
- add-to-cart já possui idempotência explícita
- carrinho bloqueia quantidade obviamente impossível
- checkout revalida estoque antes de criar pedido
- conflitos finais são explicáveis e reconciliáveis sem pedido parcial
- continuar aqui agora puxaria temas maiores que merecem trilha própria

### Decisão: reabrir payments por readiness transacional, não por UX
Decisão:
- tratar a próxima abordagem como `Checkout/Payment Execution Foundation`
- não criar novo esqueleto de pagamentos antes de auditar o fluxo real já existente
- manter `payments` como dono de tentativas, provider intent, redirect/return e webhook
- manter `orders` como dono da confirmação do pedido e baixa operacional de estoque pós-pagamento
- priorizar hardening do webhook pago quando a confirmação encontra conflito de estoque

Motivo:
- `PaymentAttempt`, hosted redirect/return, provider intent e webhook já existem
- webhook pago já delega confirmação ao command service de `orders`
- a baixa pós-pagamento já é aplicada no boundary de `orders`
- o maior risco residual não é ausência de fluxo, mas garantir que falhas finais de inventário não marquem tentativa/pedido como pagos indevidamente

### Decisão: webhook pago com conflito de estoque não reconcilia pagamento
Decisão:
- manter `payment-confirmation-stock-conflict` como resposta `409` do webhook
- não marcar `Order` como `paid`
- não marcar `PaymentAttempt` como `paid`
- não registrar email/histórico de pagamento confirmado
- registrar `payment_confirmation.stock_conflict` para operação investigar

Motivo:
- o provider pode informar pagamento antes de o sistema conseguir cumprir o pedido com estoque atual
- o boundary seguro é bloquear a confirmação local até intervenção/reconciliação operacional
- reconciliar a tentativa como paga sem pedido confirmado criaria divergência financeira/operacional silenciosa

### Decisão: retorno hospedado é hint, não confirmação financeira
Decisão:
- manter `hosted-payment-return-pending-verification` como estado informativo
- não marcar pedido como pago a partir do browser return
- não reconciliar `PaymentAttempt` como pago a partir do browser return
- manter webhook assinado como fonte de verdade para `payment.paid`
- manter a área do cliente comunicando que nenhuma ação extra é necessária enquanto a confirmação segura chega

Motivo:
- retorno hospedado pertence à navegação do cliente, não ao livro financeiro
- o browser pode voltar com status otimista antes da confirmação assíncrona
- transformar return em confirmação abriria risco de pedido pago sem evento confiável de provider
- o fluxo atual já é honesto: informa progresso, preserva o pedido e espera webhook

### Decisão: não criar status intermediário para pagamento em verificação
Decisão:
- manter `PaymentAttempt.status=pending` para tentativas ainda não reconciliadas
- representar “em verificação” por timeline, return hint, idade da pendência e drift operacional
- não adicionar `verifying`, `awaiting_webhook` ou status semelhante nesta fase
- não mudar `Order.payment_status` apenas por retorno hospedado

Motivo:
- o estado financeiro continua binário no ponto de reconciliação: pendente, pago ou falhou
- status intermediário persistido aumentaria complexidade de transição sem nova fonte de verdade
- a granularidade necessária para suporte já cabe em `PaymentAttempt.metadata`
- métricas e triagem operacional já conseguem enxergar backlog pendente por tenant/status

### Decisão: alerta de tentativa pendente antiga deve ser métrica derivada
Decisão:
- manter `HubxPaymentsPendingAttemptsHigh` para backlog agregado
- adicionar depois métrica `hubx_payments_pending_attempt_oldest_age_seconds{tenant_id}`
- usar threshold inicial de 6 horas (`21600` segundos)
- não criar job assíncrono nem novo estado persistido para stale attempt nesta fase

Motivo:
- backlog agregado não identifica tenant com tentativa antiga isolada
- idade máxima por tenant é diretamente acionável pelo suporte
- o threshold de 6 horas já é consistente com a UX operacional do detalhe do pedido e com `list_payment_attempts --stale-hours=6`
- scrape Prometheus basta para detectar o problema sem aumentar complexidade transacional

### Decisão: stale payment attempts merecem painel no dashboard atual
Decisão:
- adicionar painel no dashboard existente de payments, não criar dashboard novo
- usar `hubx_payments_pending_attempt_oldest_age_seconds`
- preferir tabela por `tenant_id`, ordenada pela maior idade
- manter Alertmanager como canal de ação e Grafana como triagem visual

Motivo:
- tentativa antiga é melhor investigada por tenant do que por série agregada
- o painel reduz tempo de diagnóstico após o alerta
- dashboard separado seria excesso para a fase atual
- a operação permanece alinhada ao runbook e ao comando `list_payment_attempts`

### Decisão: encerrar Checkout/Payment Execution com Go técnico
Decisão:
- considerar a trilha `Checkout/Payment Execution` suficiente para esta fase
- não continuar em micro-waves de execução de pagamento sem escolher um tema maior
- tratar refund/estorno, conciliação financeira, SLA automático e rollout real de provider como trilhas próprias
- recomendar `Provider Production Rollout Review` como próxima abordagem natural

Motivo:
- o fluxo de tentativa, provider intent, hosted redirect/return, webhook e confirmação do pedido já existe
- o webhook assinado permanece fonte de verdade para pagamento confirmado/falho
- conflito de estoque em pagamento confirmado está protegido por teste e alerta
- stale attempt possui CLI, métrica, alerta e painel
- continuar aqui agora misturaria temas maiores de produto/operação financeira em pequenas waves pouco objetivas

### Decisão: live global de provider exige flag explícita
Decisão:
- `PAYMENTS_REAL_PROVIDER_ROLLOUT_MODE=live` não deve liberar provider real globalmente por si só
- exigir `PAYMENTS_REAL_PROVIDER_LIVE_GLOBAL_ENABLED=true` para live global
- manter rollout de produção recomendado em `controlled`
- exigir `PAYMENTS_REAL_PROVIDER_FALLBACK_MODE=block` no readiness de produção

Motivo:
- ativação global acidental de gateway real é risco financeiro/operacional alto
- rollout controlado por tenant é suficiente para piloto de produção
- fallback lite em produção pode mascarar falha real de provider
- a flag explícita cria uma segunda trava simples antes de expandir para todos os tenants

### Decisão: Provider Production Rollout fecha com Go controlado
Decisão:
- permitir avanço para piloto real controlado por tenant
- bloquear live global imediato como decisão padrão
- exigir readiness production antes de ativar tenant em allowlist
- tratar conciliação financeira como próxima trilha maior

Motivo:
- a ativação controlada tem trava por tenant, fallback `block`, readiness e rollback simples
- a operação já possui alertas para provider intent, webhook, stale attempts e conflitos de estoque
- live global ainda depende de confiança operacional adquirida em piloto
- o próximo risco relevante é financeiro/backoffice, não mais o contrato técnico mínimo de rollout

### Decisão: conciliação financeira começa read-only
Decisão:
- criar auditoria operacional entre `PaymentAttempt` e `Order`
- não criar ledger persistido nesta fase
- não criar correção automática de divergências financeiras
- manter ajustes financeiros manuais fora do produto até haver política clara

Motivo:
- divergências financeiras são sensíveis e exigem conferência de provider, webhook e histórico do pedido
- `PaymentAttempt` já contém dados suficientes para uma primeira auditoria
- ledger/backoffice completo é uma trilha maior que envolve estorno, conciliação contábil e política operacional
- auditoria read-only reduz risco imediatamente sem introduzir mutações financeiras perigosas

### Decisão: Payments Financial Reconciliation fecha no recorte mínimo
Decisão:
- considerar suficiente nesta fase a auditoria read-only tenant-scoped
- adiar ledger financeiro persistido
- adiar tela financeira administrativa completa
- recomendar revisão de surface admin financeira mínima como próximo passo

Motivo:
- a lacuna crítica imediata era detectar divergências, não corrigi-las automaticamente
- correções financeiras exigem política, permissão e rastreabilidade mais fortes
- CLI operacional é suficiente para piloto/controlado e suporte interno inicial
- UI/admin deve ser uma decisão de produto separada, não consequência automática do auditor

### Decisão: surface admin financeira mínima é read-only
Decisão:
- expor divergências financeiras em `/ops/payments/finance/`
- reutilizar o auditor entre `PaymentAttempt` e `Order`
- não permitir correção manual nesta tela
- não criar ledger persistido nesta abordagem

Motivo:
- suporte/admin ganha visibilidade sem risco de mutação financeira prematura
- tenant scope fica explícito pela rota ops e pela query de auditoria
- resolução financeira exige política e rastreabilidade próprias
- a tela prepara o terreno para um backoffice futuro sem antecipar sua complexidade

### Decisão: refund/reversal começa por readiness read-only
Decisão:
- criar auditoria de candidatos a refund/reversal
- não executar estorno real no provider nesta abordagem
- não alterar pedido, estoque, cupom ou tentativa por esse auditor
- exigir ledger persistido antes de qualquer refund transacional

Motivo:
- refund é mutação financeira sensível e precisa de idempotência, auditoria e política operacional
- cancelamento de pedido já recupera estoque/cupom em alguns casos, mas isso não equivale a estorno financeiro
- candidatos read-only ajudam suporte a preparar análise sem risco de movimentar dinheiro
- chamar provider sem ledger aumentaria risco de divergência financeira irreconciliável

### Decisão: refund ledger mínimo antes de provider
Decisão:
- criar `PaymentRefund` como ledger tenant-scoped de intenção/bloqueio de refund
- exigir idempotência por `(tenant, idempotency_key)`
- registrar blockers quando a intenção não está apta para execução
- não chamar provider nem mutar pedido, tentativa, estoque ou cupom nesta etapa

Motivo:
- refund real é mutação financeira e precisa de trilha persistida antes da chamada externa
- idempotência reduz risco de estorno duplicado em operação/admin
- blockers preservados no ledger ajudam auditoria e suporte
- separar intenção de execução mantém o rollout seguro para a próxima fase

### Decisão: refund provider exige aprovação admin antes de execução
Decisão:
- não chamar provider real de refund diretamente a partir de CLI/API nesta fase
- criar antes uma surface admin de aprovação/triagem sobre `PaymentRefund`
- manter `payment.refunded` reservado para refund confirmado pelo provider
- exigir transição auditável `requested → processing → succeeded|failed` antes de efeitos em outros módulos

Motivo:
- estorno real movimenta dinheiro e não deve ser consequência invisível de um comando técnico
- o adapter atual de provider só cobre criação de intent/link de pagamento, não refund
- operador precisa ver blockers, valor, pedido, tentativa e referência externa antes de aprovar
- efeitos em `orders`, estoque, cupom e notifications precisam ser explícitos e posteriores à confirmação externa

### Decisão: primeira surface admin de refund é read-only
Decisão:
- criar primeiro `/ops/payments/refunds/` como triagem tenant-scoped do ledger
- não incluir approve/execute provider nessa primeira surface
- exibir `requested`, `blocked`, blockers, valor, pedido, tentativa e idempotency key
- separar aprovação mutável em wave posterior com command service próprio

Motivo:
- visibilidade operacional do ledger é pré-requisito para aprovação segura
- botão de aprovação antes de detalhe/auditoria aumentaria risco de estorno acidental
- a tela read-only aproveita o padrão já usado por `/ops/payments/finance/`
- manter mutações fora da view preserva a arquitetura modular do projeto

### Decisão: surface read-only de refunds fecha a triagem inicial
Decisão:
- considerar `/ops/payments/refunds/` suficiente para visibilidade inicial do ledger
- manter aprovação/execução fora da tela nesta abordagem
- tratar filtro por status como recurso operacional suficiente para a primeira triagem
- recomendar contrato de command de aprovação como próxima trilha

Motivo:
- a lacuna imediata era enxergar `PaymentRefund`, não movimentar dinheiro
- tela tenant-scoped reduz risco de suporte operar às cegas
- separar leitura de aprovação mantém o próximo passo pequeno e auditável

### Decisão: aprovação de refund prepara execução, mas não chama provider
Decisão:
- criar um command futuro `approve_refund(...)` em `payments.application`
- permitir somente `requested → processing`
- exigir tenant, `refund_key`, ator, ausência de blockers, tentativa paga e referência externa
- registrar aprovação em metadata sem emitir `payment.refunded`
- manter provider call fora desse command inicial

Motivo:
- aprovação é uma transição operacional diferente da execução financeira
- separar aprovação de provider reduz risco de estorno acidental
- `processing` prepara a próxima wave para adapter real sem fingir sucesso financeiro
- efeitos em `orders`, estoque, cupom e notifications só devem ocorrer após confirmação externa

### Decisão: command de aprovação de refund fecha transição interna
Decisão:
- implementar `approve_refund(...)` como transição interna do ledger
- registrar aprovação em metadata com `provider_call=not-executed`
- preservar status e registrar `approval_blockers` quando a aprovação não é permitida
- manter execução financeira real fora desta etapa

Motivo:
- a operação ganha uma fronteira explícita entre triagem e execução futura
- bloqueios ficam auditáveis no próprio `PaymentRefund`
- separar command de aprovação da action admin mantém o próximo passo pequeno e testável

### Decisão: action admin de aprovação é adaptador fino
Decisão:
- criar futuramente `POST /ops/payments/refunds/<refund_key>/approve/`
- usar a action apenas para chamar `payments.application.approve_refund(...)`
- exibir ação somente para refunds `requested`
- redirecionar para a lista de refunds após sucesso/bloqueio/indisponibilidade
- não chamar provider nem produzir efeitos em outros módulos

Motivo:
- a view deve permanecer fina e não duplicar regras de aprovação
- POST tenant-scoped reduz risco de mutação acidental/cross-tenant
- o operador precisa de uma ação clara, mas com copy honesta de que ainda não é estorno real
- provider execution deve continuar como trilha separada

### Decisão: action admin de aprovação interna está pronta
Decisão:
- conectar `/ops/payments/refunds/` ao POST de aprovação interna
- exibir `Aprovar internamente` somente para `requested`
- usar copy explícita `Não executa estorno`
- manter a view como adaptador fino para `approve_refund(...)`

Motivo:
- a operação agora consegue sair de triagem para `processing` sem chamar provider
- a copy evita confundir aprovação interna com estorno real
- cross-tenant continua protegido pelo command tenant-scoped
- provider adapter de refund pode ser tratado como próxima trilha isolada

### Decisão: refund provider adapter começa por contrato
Decisão:
- definir `RefundProviderContract` e `RefundProviderResponse` antes de chamar provider real
- manter adapter em `payments.infrastructure`
- manter transições de `PaymentRefund` em `payments.application`
- aceitar `accepted`, `succeeded` e `failed` como semântica inicial de resposta externa
- reservar `payment.refunded` apenas para ledger `succeeded`

Motivo:
- refund real precisa separar tradução externa de transição interna do ledger
- provider pode aceitar uma solicitação sem confirmar conclusão imediata
- skeleton/testes de contrato reduzem risco antes de integrar endpoint real do gateway
- outros módulos só devem reagir depois de confirmação financeira efetiva

### Decisão: skeleton de refund adapter não executa provider real
Decisão:
- criar `RefundProviderContract` e `RefundProviderResponse`
- implementar `ProviderAdapterLite.create_refund(...)` retornando `accepted`
- manter `PagarmeProviderAdapter.create_refund(...)` como erro explícito de não implementado
- não conectar o skeleton a `PaymentRefund` ainda

Motivo:
- o sistema ganha contrato testável sem risco de movimentar dinheiro
- retorno `accepted` permite modelar execução assíncrona futura
- falha explícita no adapter real evita falsa sensação de suporte a estorno em produção

### Decisão: execution command registra resposta, não efeitos externos
Decisão:
- criar futuramente `execute_refund(...)` para consumir apenas `PaymentRefund.processing`
- construir `RefundProviderContract` dentro de `payments.application`
- registrar `accepted`, `succeeded` ou `failed` no ledger
- manter `accepted` como `processing`
- adiar `payment.refunded` e efeitos em outros módulos para etapa posterior

Motivo:
- execução financeira e propagação de efeitos são responsabilidades diferentes
- `accepted` não garante conclusão financeira
- registrar resposta no ledger primeiro preserva auditabilidade e permite retry/consulta futura com mais segurança
- efeitos em `orders`, estoque, cupom e notifications precisam de contrato próprio após confirmação

### Decisão: execution command skeleton fecha pipeline interno
Decisão:
- implementar `execute_refund(...)` consumindo somente `processing`
- registrar resposta do adapter em `metadata.provider_refund`
- manter `accepted` em `processing`
- transicionar `succeeded` e `failed` apenas no ledger
- não emitir evento nem tocar outros módulos

Motivo:
- fecha o caminho interno approval → execution sem provider real obrigatório
- mantém a fonte de verdade financeira em `PaymentRefund`
- evita propagar efeitos antes de revisar endpoint real e confirmação do gateway

### Decisão: endpoint real Pagar.me de refund começa conservador
Decisão:
- mapear refund real para `DELETE /core/v5/charges/{charge_id}` conforme API Reference V5
- tratar `PaymentRefund.external_reference` como `charge_id`
- enviar `amount` em centavos para refund parcial
- não suportar boleto com `bank_account` nesta primeira execução
- tratar resposta 2xx inicialmente como `accepted` até validação sandbox da semântica

Motivo:
- a documentação oficial chama a operação de cancelamento de cobrança e permite amount opcional
- boleto exige dados adicionais que o ledger atual não possui
- classificar 2xx como `accepted` evita fingir conclusão financeira sem validar comportamento real do provider
- produção deve depender de sandbox contract test/manual validation

### Decisão: adapter Pagar.me de refund fica sandbox-first
Decisão:
- implementar `PagarmeProviderAdapter.create_refund(...)` com `DELETE /charges/{charge_id}`
- enviar `amount` em centavos e `Idempotency-Key`
- classificar resposta 2xx como `accepted`
- manter boleto com `bank_account` fora do escopo
- manter produção bloqueada até validação sandbox real

Motivo:
- o adapter agora tem caminho técnico testável sem depender de rede nos testes
- `accepted` preserva cautela sobre a confirmação final do provider
- idempotência explícita reduz risco de duplicidade ao validar sandbox
- dados bancários de boleto exigem expansão própria do ledger

### Decisão: validação sandbox de refund será comando controlado
Decisão:
- criar `payment_sandbox_validate_refund`
- exigir `tenant-id` e `refund-key`
- exigir ledger `processing`
- oferecer `--dry-run`
- delegar execução real controlada para `execute_refund(...)`
- não emitir evento nem propagar efeitos

Motivo:
- refund real precisa de validação operacional antes de qualquer rollout
- o comando permite testar um caso específico sem criar feature genérica de estorno
- `--dry-run` reduz risco durante setup de credenciais e conferência do ledger
- tenant/refund explícitos evitam execução acidental em massa

### Decisão: command sandbox de refund executa somente caso explícito
Decisão:
- implementar `payment_sandbox_validate_refund`
- bloquear lookup cross-tenant
- bloquear status diferente de `processing`
- usar `--dry-run` como caminho recomendado antes da execução
- delegar execução a `execute_refund(...)`

Motivo:
- validação sandbox precisa ser reproduzível e auditável
- execução por `refund_key` evita operações em lote acidentais
- reusar `execute_refund(...)` evita duplicar regra de ledger/provider

### Decisão: runbook sandbox de refund exige dry-run e No-Go explícito
Decisão:
- documentar o fluxo sandbox ponta a ponta antes de qualquer rollout real
- exigir tenant controlado, credenciais sandbox e refund em `processing`
- exigir `payment_sandbox_validate_refund --dry-run` antes da execução sem `--dry-run`
- manter `accepted` como estado operacional pendente, não como refund concluído
- bloquear produção se faltar referência externa, idempotência rastreável, payload auditável ou conciliação pós-execução

Motivo:
- refund movimenta dinheiro e precisa de evidência operacional antes de produção
- dry-run reduz risco de chamada acidental ao provider
- No-Go explícito evita transformar um teste sandbox em rollout financeiro real
- manter `payment.refunded` bloqueado preserva a semântica de evento concluído

### Decisão: refund provider permanece em No-Go para produção até evidência sandbox
Decisão:
- manter refund provider bloqueado para produção real neste momento
- permitir apenas gate documental para produção manual limitada futura
- exigir evidência sandbox antes de qualquer habilitação:
  - dry-run pronto
  - execução sandbox observada
  - referência do provider preservada
  - payload em `metadata.provider_refund`
  - conciliação financeira revisada
- limitar futura produção inicial a execução manual por refund já aprovado internamente
- manter fora execução em lote, boleto com dados bancários não modelados, eventos automáticos e efeitos cross-module

Motivo:
- adapter e command existem, mas ainda não há evidência operacional real suficiente para movimentar dinheiro em produção
- `accepted` ainda pode representar solicitação recebida, não refund concluído
- produção financeira precisa de rastreabilidade e conciliação antes de automação
- bloquear eventos e efeitos externos evita que um refund parcial/inconclusivo contamine pedidos, estoque, cupons ou notificações

### Decisão: evidência sandbox de refund usa envelope em metadata
Decisão:
- padronizar evidência sandbox em `PaymentRefund.metadata.sandbox_evidence`
- manter `metadata.provider_refund` como resposta técnica do adapter/provider
- não criar modelo novo nesta etapa
- não alterar status do ledger ao anexar evidência
- proibir secrets, tokens, Authorization headers, dados de cartão e dados bancários sensíveis no envelope
- exigir tenant/refund explícitos quando a captura virar command ou action

Motivo:
- `PaymentRefund` já é o ledger financeiro tenant-scoped da operação
- criar uma tabela antes do primeiro fluxo de captura aumentaria superfície sem ganho imediato
- separar `sandbox_evidence` de `provider_refund` evita misturar observação humana com payload técnico
- evidência sem efeito de status reduz risco de transformar documentação operacional em automação financeira

### Decisão: captura de evidência sandbox usa command separado
Decisão:
- criar futuramente `capture_payment_refund_sandbox_evidence`
- manter o command separado de `payment_sandbox_validate_refund`
- exigir `tenant-id`, `refund-key`, `captured-by` e `decision`
- escrever apenas em `PaymentRefund.metadata.sandbox_evidence`
- bloquear conteúdo sensível e decisões fora da lista permitida
- exigir evidência técnica e conciliação para `go-production-limited`

Motivo:
- validação sandbox pode chamar provider; captura de evidência não deve chamar nada externo
- command separado reduz risco de execução financeira acidental
- preservar `metadata.provider_refund` evita sobrescrever payload técnico do adapter
- exigir operador e decisão explícita melhora auditabilidade operacional

### Decisão: command de evidência sandbox escreve apenas metadata
Decisão:
- implementar `capture_payment_refund_sandbox_evidence`
- escrever somente em `PaymentRefund.metadata.sandbox_evidence`
- preservar status, referência de provider, timestamps finais e `metadata.provider_refund`
- bloquear conteúdo sensível antes da escrita
- exigir referências adicionais para `go-production-limited`
- manter provider, eventos e efeitos cross-module fora do command

Motivo:
- evidência operacional deve ser auditável sem movimentar dinheiro
- preservar o ledger evita que captura de evidência seja confundida com execução financeira
- bloquear conteúdo sensível reduz risco de vazar tokens ou dados financeiros em JSON auditável
- `go-production-limited` precisa ser uma decisão qualificada, não um texto solto

### Decisão: refund provider não habilita produção sem evidência externa
Decisão:
- manter No-Go para produção ampla de refund provider
- manter No-Go para automação, self-service e execução em lote
- permitir apenas preparação para produção manual limitada futura
- condicionar qualquer produção manual limitada a:
  - `metadata.sandbox_evidence.decision=go-production-limited`
  - evidência real de sandbox externo
  - `metadata.provider_refund` revisado
  - referência de dashboard do provider
  - referência de conciliação financeira
  - operador financeiro identificado
- não implementar feature flag ampla nem botão admin de execução real nesta etapa

Motivo:
- testes mockados validam contrato de código, mas não provam comportamento financeiro externo
- refund real movimenta dinheiro e precisa de evidência operacional fora do repositório
- manter produção limitada como caminho futuro reduz risco sem descartar a preparação já feita
- bloquear automação evita que `accepted` seja tratado como dinheiro efetivamente devolvido

### Decisão: refund/reversal encerra como fundação técnica, não produto financeiro
Decisão:
- encerrar a trilha de refund/reversal como fundação técnica interna
- manter produção real bloqueada
- permitir uso interno para auditoria, triagem, ledger, aprovação interna, sandbox e captura de evidência
- não liberar automação, self-service, execução em lote, boleto/dados bancários, `payment.refunded` ou efeitos cross-module
- reabrir a trilha apenas com evidência sandbox externa real ou demanda operacional concreta de produção manual limitada

Motivo:
- a trilha já entregou os contratos técnicos necessários para controlar o risco
- a ausência de evidência externa impede tratar refund como produto financeiro lançado
- encerrar agora evita overengineering em uma área ainda dependente de validação operacional fora do código
- manter bloqueios explícitos protege pedidos, estoque, cupons e notificações de estados financeiros inconclusivos

### Decisão: payments financial operations encerra como suficiente para este ciclo
Decisão:
- encerrar operações financeiras de payments como abordagem ativa neste ciclo
- considerar payments pronto para operação controlada, suporte, triagem, observabilidade e rollout controlado
- manter No-Go para backoffice financeiro completo, settlement/extrato, ledger geral, correções automáticas, pruning financeiro formal e refund production-ready
- não tratar payments como bloqueador principal do próximo roadmap funcional
- reabrir payments financeiro apenas com evidência externa real ou demanda operacional concreta

Motivo:
- o módulo já cobre o risco imediato de tentativa, webhook, retorno, divergência read-only, admin finance e refund foundation
- os bloqueios restantes dependem mais de operação/provider/financeiro externo do que de micro-refactors locais
- continuar refinando payments agora tende a gerar baixo ROI frente a outras áreas de produto
- encerrar com No-Go explícito preserva segurança sem congelar evolução futura

### Decisão: próximo ROI funcional é Trust & Social Proof
Decisão:
- selecionar `reviews` como próxima trilha funcional recomendada
- iniciar por `ProductReview` tenant-scoped, moderação e agregados approved-only para PDP
- manter `cart`, `coupons`, `checkout`, `payments` e `shipping` fora da fila ativa neste ciclo
- adiar governança SaaS (`audit`, `subscriptions`, owner permissions) se o objetivo imediato continuar sendo produto/conversão

Motivo:
- `cart` e `coupons` já deixaram o estado skeleton e cobrem o gargalo transacional inicial
- `payments` foi fechado como operação controlada, com produção financeira real bloqueada por evidência externa
- `reviews` ainda é skeleton e atua diretamente na confiança da PDP antes do clique
- o primeiro recorte de prova social tem risco menor que reabrir payments/refund ou criar promoções avançadas

### Decisão: ProductReview nasce tenant-scoped e approved-only
Decisão:
- criar `ProductReview` como modelo inicial de reviews
- exigir `tenant`, `product`, `rating` e status moderável
- fazer toda review nascer como `pending`
- expor query de agregados e listagem apenas para reviews `approved`
- manter PDP/catalog como consumidores por application query
- adiar surface admin/ops de moderação para a próxima wave

Motivo:
- prova social precisa de moderação antes de aparecer no storefront
- tenant scope evita vazamento de reputação entre lojas
- approved-only permite integrar PDP depois sem expor conteúdo pendente/rejeitado
- começar por query e modelo evita acoplar reviews a checkout, payments ou orders

### Decisão: reviews exige moderação admin antes de PDP pública
Decisão:
- criar uma surface `/ops/reviews/` antes de integrar reviews à PDP
- implementar listagem tenant-scoped e ações POST de approve/reject por application command
- manter views finas e sem regra de negócio
- preservar conteúdo, produto, customer e rating durante moderação
- não emitir eventos/notificações nesta wave
- bloquear qualquer exibição pública de reviews pendentes ou rejeitadas

Motivo:
- prova social sem moderação pode expor spam, conteúdo incorreto ou dado sensível
- o lojista precisa de controle operacional antes de reviews impactarem conversão
- aprovar/rejeitar é uma mutação simples e auditável sem tocar checkout, orders ou payments
- manter PDP fora desta wave reduz risco e confirma o fluxo interno primeiro

### Decisão: /ops/reviews/ publica moderação mínima
Decisão:
- publicar `/ops/reviews/` como surface admin/ops de moderação
- usar `admin_review_queries` para listagem tenant-scoped
- usar `admin_review_commands.moderate_review(...)` para approve/reject
- preservar conteúdo, rating, product e customer durante moderação
- incluir link `Avaliações` no cockpit `/ops/`
- manter integração PDP fora desta wave

Motivo:
- a moderação precisa existir antes de qualquer prova social pública
- commands isolam a mutação e mantêm views finas
- tenant scope em listagem e POST evita vazamento/alteração cross-tenant
- separar PDP permite validar operação interna antes de impacto em conversão

### Decisão: PDP consome reviews approved-only por application query
Decisão:
- integrar reviews à PDP como enrichment de `ProductDetailView`
- chamar `reviews.application.review_summary_queries` a partir da view
- injetar `review_summary` e `approved_reviews` no contexto do template
- manter `catalog.application.storefront_catalog_queries` sem regra interna de moderação
- exibir somente reviews `approved`
- adiar formulário público de criação de reviews

Motivo:
- `reviews` é dono de moderação e visibilidade approved-only
- `catalog` deve continuar dono do produto/PDP, não do ORM interno de reviews
- compor no boundary da view reduz acoplamento e mantém o fluxo de compra intacto
- prova social pode aumentar confiança sem tocar cart, checkout, payments ou orders

### Decisão: PDP exibe prova social apenas quando há review aprovada
Decisão:
- renderizar bloco “Avaliações de clientes” somente com `approved_reviews`
- omitir bloco quando não houver reviews aprovadas
- expor `Product.id` no payload persistido para lookup de agregados
- manter `storefront_catalog_queries` livre de dependência direta de reviews
- adiar submissão pública de reviews

Motivo:
- não mostrar fallback fake preserva confiança
- approved-only protege a PDP de conteúdo pendente/rejeitado
- lookup por application query mantém o boundary entre `catalog` e `reviews`
- formulário público exige regras adicionais de identidade, spam e vínculo com pedido

### Decisão: submissão pública de review fica fora do primeiro corte
Decisão:
- não abrir formulário storefront público de review agora
- criar primeiro um command/application service interno para registrar reviews `pending`
- exigir tenant e produto do mesmo tenant
- validar rating entre 1 e 5
- manter moderação obrigatória antes de qualquer visibilidade pública
- adiar verified purchase, vínculo obrigatório com pedido, anti-spam público e notificações

Motivo:
- submissão pública exige decisões de identidade, spam, consentimento e vínculo com compra
- o sistema ainda não precisa expor entrada pública para provar o fluxo de moderação/PDP
- command interno permite operar seeds/suporte com menor risco
- manter `pending` por padrão preserva a garantia approved-only da PDP

### Decisão: submissão interna de review sempre cria pending
Decisão:
- implementar `reviews.application.review_submission_commands`
- criar command `submit_product_review`
- validar tenant, produto e rating antes de criar review
- associar customer apenas quando pertence ao mesmo tenant
- criar toda review com `status=pending`
- manter publicação dependente de `/ops/reviews/`

Motivo:
- command interno permite popular e testar prova social sem abrir superfície pública
- pending por padrão preserva moderação obrigatória
- produto/customer tenant-scoped evita vazamento cross-tenant
- separar submissão de publicação mantém a PDP protegida por approved-only

### Decisão: entrada admin de review usa submissão interna pending
Decisão:
- criar futuramente `/ops/reviews/new/` como entrada operacional mínima para suporte/merchant ops
- reutilizar `reviews.application.review_submission_commands.submit_product_review(...)`
- resolver `tenant_id` pela request e validar produto no tenant atual
- criar toda review admin como `pending`
- manter aprovação dependente da moderação em `/ops/reviews/`
- manter submissão pública/customer-facing fora do escopo

Motivo:
- CLI é suficiente tecnicamente, mas ruim para operação cotidiana
- formulário admin reduz atrito sem abrir superfície pública de spam/identidade
- reaproveitar o command existente evita duplicar regra de criação
- pending por padrão preserva a garantia approved-only da PDP
- separar criação admin de publicação mantém o controle editorial do lojista

Status:
- executado com `/ops/reviews/new/`
- a criação admin reutiliza `submit_product_review(...)`
- reviews criadas por essa surface continuam nascendo como `pending`
- PDP permanece approved-only

### Decisão: submissão pública de review exige eligibility gate antes do formulário
Decisão:
- não abrir formulário público/customer-facing de review neste momento
- criar antes um eligibility service read-only para tenant/customer/product
- exigir, para fluxo público futuro, customer e produto do mesmo tenant
- exigir compra entregue/concluída ou equivalente operacional antes de permitir review pública
- bloquear duplicidade de review do mesmo customer para o mesmo produto até haver política explícita de edição
- manter toda submissão futura como `pending` e dependente de moderação

Motivo:
- reviews públicas sem elegibilidade viram vetor de spam e ruído de confiança
- compra entregue é a menor proxy segura de experiência real do cliente
- separar eligibility de submission evita contaminar o command admin, que continua útil para suporte/seeding
- manter pending por padrão preserva a garantia approved-only da PDP
- o boundary evita que PDP, accounts ou orders acessem ORM interno de reviews de forma cruzada

Status:
- executado como `reviews.application.review_eligibility_queries`
- eligibility é read-only e falha fechado sem tenant/customer/product explícitos
- compra do produto é inferida por `OrderItem.variant_sku` ligado a `ProductVariant`
- pedido precisa estar entregue/concluído no recorte operacional atual
- submissão pública permanece bloqueada

### Decisão: eligibility pública de review não deve depender só de SKU
Decisão:
- endurecer `OrderItem` com snapshot explícito de produto antes de abrir formulário público de review
- adicionar futuramente `product_id_snapshot` e `product_slug_snapshot`
- preencher esses campos no checkout completion para novos pedidos
- atualizar eligibility para preferir `product_id_snapshot`
- manter fallback por `variant_sku` apenas como compatibilidade legada
- não exigir backfill histórico no primeiro corte

Motivo:
- SKU é uma ponte operacional útil, mas frágil como contrato de experiência pública
- pedido precisa preservar o produto comprado mesmo se catálogo mudar depois
- reviews públicas devem se apoiar no snapshot transacional do pedido, não no estado atual do catálogo
- campos opcionais reduzem risco de migration e preservam pedidos legados
- fallback legado mantém compatibilidade enquanto novos pedidos passam a carregar snapshot

Status:
- executado com `OrderItem.product_id_snapshot` e `OrderItem.product_slug_snapshot`
- checkout completion preenche snapshot para novos pedidos
- eligibility prefere snapshot e usa SKU apenas para itens legados sem snapshot
- submissão pública de review segue bloqueada até revisão de surface customer-facing

### Decisão: primeira submissão customer-facing de review nasce no detalhe do pedido
Decisão:
- não abrir formulário de review diretamente na PDP nesta etapa
- iniciar a surface customer-facing pelo detalhe do pedido da área do cliente
- exibir CTA apenas para item elegível por tenant/customer/order/product
- criar um command customer-facing separado do command admin
- manter toda submissão pública como `pending`
- redirecionar pós-submit para o detalhe do pedido com feedback

Motivo:
- PDP não carrega contexto seguro de customer e pedido no contrato atual
- detalhe do pedido já concentra tenant, customer, order e itens comprados
- eligibility pode ser aplicada item a item sem contaminar `catalog`
- separar command público do admin evita bypass acidental de eligibility
- moderação obrigatória preserva a garantia approved-only do storefront

### Decisão: command customer-facing de review é separado do admin
Decisão:
- implementar `reviews.application.customer_review_submission_commands`
- exigir `tenant_id`, `customer_id`, `order_number` e `product_id`
- exigir pedido entregue/concluído do mesmo tenant/customer
- exigir produto presente no snapshot do pedido informado
- bloquear duplicidade customer/produto
- criar review sempre como `pending`
- respeitar consentimento explícito para exibir nome do autor

Motivo:
- o command admin precisa continuar útil para operação controlada sem exigir pedido entregue
- o command público precisa impedir bypass de eligibility
- validar o pedido explícito reduz risco de uma compra antiga de outro item liberar review indevida
- pending por padrão preserva moderação obrigatória
- consentimento de nome evita expor identidade na PDP sem confirmação do cliente

### Decisão: rota customer-facing de review fica sob account order detail
Decisão:
- criar futuramente `accounts:account-order-review-create`
- usar rota `/account/orders/<order_number>/reviews/<product_id>/new/`
- hospedar a view em `accounts.interfaces` porque a jornada nasce no detalhe do pedido
- delegar submissão para `reviews.application.customer_review_submission_commands`
- redirecionar pós-submit para o detalhe do pedido com result code
- deixar CTA automático por item para uma wave separada se necessário

Motivo:
- o detalhe do pedido já possui tenant, customer e order context
- manter a rota em `accounts` evita contaminar PDP/catalog com auth e pedido
- o command de `reviews` continua dono da regra de criação e eligibility
- separar CTA automático reduz risco de mexer demais no payload já sensível do detalhe
- formulário dedicado é mais simples de validar e testar que formulário inline

Status:
- executado com `AccountOrderReviewCreateView`
- rota `accounts:account-order-review-create` publicada
- template `customer_review_form_page.html` criado
- feedback de result codes de review adicionado ao detalhe do pedido
- CTA automático por item permanece fora desta wave

### Decisão: CTA de review usa actions do resumo do pedido
Decisão:
- renderizar o primeiro CTA customer-facing de avaliação no detalhe do pedido
- usar o slot `actions` do componente `order_summary`
- filtrar links por `reviews.application.review_eligibility_queries`
- linkar para `accounts:account-order-review-create`
- omitir CTA para item sem `product_id_snapshot`, pedido não entregue ou review duplicada
- manter formulário dedicado, sem inline form no detalhe ou na PDP

Motivo:
- o detalhe do pedido já concentra o contexto de tenant, customer e pedido
- `order_summary.actions` permite um incremento pequeno sem redesenhar a lista de itens
- manter eligibility em `reviews` evita duplicar regra de negócio em `accounts`
- CTA como navegação preserva POST explícito e feedback já existente
- PDP ainda não possui contexto seguro de compra/customer para submissão

Status:
- decidido para execução em wave seguinte
- requer expor snapshot mínimo de produto no payload de itens do pedido

### Decisão: CTA de avaliação aparece somente para itens elegíveis
Decisão:
- expor `product_id_snapshot` e `product_slug_snapshot` no payload de itens da área do cliente
- montar CTAs no detalhe do pedido usando `reviews.application.review_eligibility_queries`
- renderizar os CTAs no slot `actions` de `order_summary`
- ocultar CTA para pedido não entregue, review duplicada, item sem snapshot ou contexto sem tenant/customer
- manter submissão em rota/formulário dedicado

Motivo:
- evita duplicar regra de elegibilidade em template ou query de accounts
- preserva o contrato multi-tenant via tenant/customer explícitos
- reduz mudança visual usando slot de componente existente
- mantém a PDP sem contexto customer/order e sem formulário público precoce

Status:
- executado na área do cliente
- coberto por testes de elegibilidade no detalhe do pedido

### Decisão: primeiro estado explícito de review é duplicidade
Decisão:
- manter CTA visível apenas para itens elegíveis
- adicionar futuramente estado explícito para `review-ineligible-duplicate`
- não mostrar “aguardando entrega” nesta etapa
- não expor estados técnicos como produto ausente, customer ausente, item sem snapshot ou eligibility unavailable
- manter estados visuais separados da submissão e da moderação

Motivo:
- “já avaliado” reduz dúvida do cliente depois do envio
- pedidos recentes ainda não entregues não precisam de ruído adicional
- estados técnicos refletem qualidade de dados/legado e não uma ação útil para o cliente
- preservar o contrato de reviews como dono da eligibility evita duplicação de regra em accounts

Status:
- aprovado para execução em wave seguinte

### Decisão: duplicidade de review vira estado informativo
Decisão:
- renderizar estado informativo para `review-ineligible-duplicate` no detalhe do pedido
- manter CTA oculto para produtos já avaliados
- manter pedidos não entregues sem mensagem explícita
- preservar estados técnicos de eligibility fora da UI customer-facing

Motivo:
- confirma ao cliente que a avaliação já foi recebida
- reduz tentativa repetida de envio
- evita abrir detalhes moderacionais antes de uma decisão específica de produto
- mantém a superfície simples e focada em ações úteis

Status:
- executado no detalhe do pedido
- coberto por testes customer-facing

### Decisão: feedback moderacional de review será status simples
Decisão:
- criar query customer-facing para status da review do customer por tenant/customer/product
- substituir mensagem genérica de duplicidade por status simples
- mapear `pending`, `approved` e `rejected` para mensagens customer-facing
- não exibir título, body ou rating da review nesta etapa
- não adicionar edição, contestação ou nova submissão

Motivo:
- status simples dá transparência sem criar uma surface completa de “minhas avaliações”
- evitar conteúdo completo reduz risco de expor dado moderado/rejeitado fora de contexto
- query dedicada preserva boundary: `accounts` renderiza, `reviews` consulta
- tenant/customer/product explícitos mantêm isolamento multi-tenant

Status:
- aprovado para execução em wave seguinte

### Decisão: status moderacional aparece no detalhe do pedido
Decisão:
- criar query customer-facing `customer_review_status_queries`
- exibir status simples no detalhe do pedido para reviews já existentes
- mapear `pending`, `approved` e `rejected` para mensagens customer-facing
- ocultar CTA de nova avaliação quando já existir review do customer para o produto
- não expor conteúdo da review ainda

Motivo:
- melhora transparência sem criar uma surface completa de histórico
- mantém boundary de dados em `reviews.application`
- reduz dúvida operacional após moderação
- evita edição/reenvio antes de contrato de produto específico

Status:
- executado com testes de query e UI

### Decisão: não criar Minhas avaliações agora
Decisão:
- não criar uma página customer-facing dedicada para histórico de reviews nesta fase
- manter submissão, CTA e status moderacional no detalhe do pedido
- não adicionar item de sidebar da conta para reviews ainda
- retomar a surface dedicada apenas se houver edição/reenvio, notificações, volume alto ou necessidade de suporte/self-service

Motivo:
- o ciclo básico já está fechado no contexto do pedido
- uma listagem exigiria decisões adicionais sobre conteúdo completo, paginação, filtros e links
- a navegação da account area ainda é genérica e não deve crescer com placeholder de baixo ROI
- o próximo ganho maior está na conversão pública das reviews aprovadas no storefront/PDP

Status:
- decidido como No-Go nesta fase

### Decisão: próxima prova social pública é resumo compacto no PDP
Decisão:
- adicionar resumo compacto de reviews aprovadas próximo ao topo do PDP
- usar `review_summary` já disponível
- linkar para a seção completa de avaliações via âncora
- não criar formulário de review na PDP
- não adicionar distribuição por estrelas ou reviews na listagem ainda

Motivo:
- melhora conversão antes do CTA de compra
- reaproveita dados já tenant-scoped e approved-only
- evita query/aggregate novo nesta etapa
- mantém o fluxo de submissão preso ao detalhe do pedido

Status:
- aprovado para execução em wave seguinte

### Decisão: badge compacto de reviews no PDP executado
Decisão:
- exibir média e contagem de reviews aprovadas perto do título do PDP
- linkar o badge para a seção completa por `#product-reviews`
- ocultar badge quando não houver reviews aprovadas
- manter PDP sem formulário de review

Motivo:
- aumenta prova social antes da decisão de compra
- usa contrato approved-only já existente
- evita custo de nova agregação ou mudança de backend
- mantém submissão vinculada ao pedido entregue

Status:
- executado com testes de storefront approved-only

### Decisão: PDP pode destacar uma review aprovada curta
Decisão:
- destacar no PDP a primeira review aprovada já carregada
- não criar nova query ou agregação
- manter badge compacto e seção completa
- ocultar destaque quando não houver review aprovada
- não levar submissão para PDP

Motivo:
- transforma nota média em prova social textual
- reaproveita dados approved-only já disponíveis
- reduz custo técnico e risco de N+1
- evita curadoria editorial antes de haver volume suficiente

Status:
- aprovado para execução em wave seguinte

### Decisão: featured review do PDP executada sem nova query
Decisão:
- renderizar micro-destaque com a primeira review aprovada já carregada
- manter fallback para title/body ausentes
- manter link para a seção completa de reviews
- ocultar destaque sem reviews aprovadas
- não criar query, agregação ou curadoria manual nesta etapa

Motivo:
- aumenta confiança com prova social textual
- preserva contrato approved-only
- evita N+1 e complexidade prematura
- mantém a submissão fora da PDP

Status:
- executado com testes de PDP

### Decisão: reviews em cards exigem summary bulk antes
Decisão:
- não renderizar reviews nos cards/listagem antes de existir query bulk
- criar primeiro contrato `get_product_review_summaries(tenant_id, product_ids)` em `reviews.application`
- usar apenas summaries approved-only nos cards
- não expor body/title/autor na listagem

Motivo:
- evita N+1 na vitrine
- preserva boundary entre catalog e reviews
- mantém listagem leve e orientada à conversão
- evita prova social fake ou fallback enganoso

Status:
- aprovado para execução em wave seguinte

### Decisão: summary bulk de reviews aprovado
Decisão:
- implementar `get_product_review_summaries(tenant_id, product_ids)`
- retornar mapa por product_id com count, average e status
- incluir produtos solicitados sem reviews como `empty`
- ignorar IDs inválidos/duplicados
- manter somente approved e tenant-scoped

Motivo:
- prepara integração em cards sem N+1
- preserva fronteira de `reviews.application`
- mantém payload leve para listagem
- evita exposição de conteúdo textual de reviews nos cards

Status:
- executado com testes de aggregate bulk

### Decisão: summaries de reviews aparecem nos cards da vitrine
Decisão:
- integrar `get_product_review_summaries(...)` na listagem storefront
- consultar summaries uma vez por página de produtos
- renderizar média e contagem approved-only nos cards
- ocultar summary quando não há review aprovada
- não expor conteúdo textual da review na listagem

Motivo:
- adiciona prova social na descoberta sem N+1
- mantém cards leves
- preserva isolamento tenant-scoped
- evita duplicar lógica de reviews em catalog/templates

Status:
- executado com testes de storefront

### Decisão: trilha Trust & Social Proof encerrada
Decisão:
- encerrar a trilha de reviews/conversão neste ponto
- considerar o ciclo mínimo completo: coleta, moderação, customer feedback, PDP e listagem
- não avançar agora em página “Minhas avaliações”, distribuição por estrelas, merchant reply ou formulário na PDP
- recomendar próxima abordagem em Search & Discovery

Motivo:
- reviews já impactam decisão no detalhe e descoberta na listagem
- fluxo customer-facing permanece seguro e vinculado a pedido entregue
- moderação protege storefront de conteúdo não aprovado
- novos incrementos são úteis, mas têm ROI menor que melhorar descoberta/ranking/filtros

Status:
- encerrado com Go

### Decisão: Search & Discovery começa por ranking explícito
Decisão:
- iniciar a abordagem Search & Discovery pelo contrato de ranking da vitrine
- manter busca externa fora de escopo nesta fase
- usar sinais já existentes: estoque, oferta, destaque, decision signal e proof social
- preservar filtros e paginação atuais até o ranking base ficar explícito

Motivo:
- a vitrine já possui sinais suficientes para melhorar descoberta sem infraestrutura nova
- ranking explícito é menor risco que adicionar sort público ou motor externo
- contratos de score/razão ajudam testes, analytics e evolução incremental
- summaries de reviews já foram preparados sem N+1

Status:
- aprovado para próxima wave

### Decisão: ranking de descoberta vira contrato explícito
Decisão:
- transformar o ranking implícito da vitrine em `discovery_rank_score`, `discovery_rank_reason` e possível `discovery_rank_components`
- iniciar com sinais nativos de catálogo: status, disponibilidade, oferta, destaque e intenção comercial do card
- manter reviews como decoração visual até que summaries aprovadas possam ser avaliadas antes da paginação
- não expor `sort=` público nem adotar search engine externo nesta fase

Motivo:
- o ranking atual já influencia conversão, mas não explica por que um produto aparece antes de outro
- social proof pós-paginação não é suficiente para ranking global sem distorcer páginas
- score explícito cria base testável para futuras ordenações, métricas e experimentos

Consequência:
- a execução seguinte deve preservar a compatibilidade da ordem atual enquanto expõe score/razão
- qualquer ranking por reviews exigirá integração bulk do conjunto filtrado antes da paginação

Status:
- aprovado para execução

### Decisão: discovery rank nasce observável antes de ordenar
Decisão:
- expor `discovery_rank_score`, `discovery_rank_reason` e `discovery_rank_components` no payload storefront de catálogo
- manter `_catalog_initial_order_key(...)` como chave real de ordenação nesta primeira execução
- limitar o score aos sinais nativos de catálogo
- deixar reviews fora do cálculo até existir avaliação bulk antes da paginação

Motivo:
- ranking explícito ganha testes e rastreabilidade sem reembaralhar a vitrine
- preservar a ordenação atual reduz risco em paginação, filtros rápidos e screenshots de produto
- score observável permite comparar sem mudar experiência pública

Consequência:
- a próxima decisão deve comparar score versus ordem atual antes de trocar a ordenação real
- integrações futuras de reviews precisam acontecer antes da paginação e via `reviews.application`

Status:
- executado

### Decisão: gate de /ops nasce ativável por ambiente
Decisão:
- criar `OpsAuthenticationGateMiddleware` para `/ops/`.
- ativar o bloqueio somente quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`.
- redirecionar anônimos para `/accounts/login/?next=...`.
- retornar `403` para usuário autenticado sem `OwnerUser` ativo no tenant.
- permitir acesso quando `request.owner_user` estiver resolvido.

Motivo:
- o sistema já resolve `request.owner_user`, mas login owner/admin real ainda não está implementado.
- ativar bloqueio default agora travaria as surfaces operacionais antes de existir fluxo de autenticação completo.
- um gate ativável permite testar e ligar por ambiente sem quebrar compatibilidade imediatamente.

Consequência:
- `/ops/` tem contrato de proteção HTTP pronto.
- produção pode ativar o gate assim que o login owner/admin estiver operacional.
- a próxima abordagem natural é executar login real de owner/admin.

Status:
- executado

### Decisão: owner context passa a ser resolvido por middleware em /ops
Decisão:
- criar `OwnerContextMiddleware` em `accounts.interfaces`.
- registrar o middleware depois de `AuthenticationMiddleware`.
- preencher `request.owner_user` apenas para `/ops` e `/ops/...`.
- resolver owner por `request.tenant + request.user.email`, exigindo `OwnerUser.is_active=True`.
- manter ausência de owner como compatibilidade temporária, sem bloquear a request.

Motivo:
- permissões administrativas já dependem de `actor_role`.
- repetir lookup de owner por view aumenta drift e acoplamento.
- ainda é cedo para impor autenticação owner obrigatória em todo `/ops/`.
- separar contexto de autorização mantém o ciclo previsível: middleware identifica, application service decide.

Consequência:
- views `/ops/` passam a ter uma fonte central para o owner atual.
- roles reais de `OwnerUser` já afetam mutações sensíveis quando o usuário está autenticado.
- o próximo endurecimento natural é revisar o gate obrigatório de autenticação/admin para `/ops/`.

Status:
- executado

### Decisão: gestão de acesso owner começa por surface mínima
Decisão:
- evoluir `/ops/owners/` de listagem/toggle para gestão mínima de acesso.
- permitir criar owner e editar e-mail, nome, role, status ativo e notificações.
- adicionar `owners.manage` ao contrato de permissões.
- registrar `owner.created` e `owner.access_updated` no `AuditLog`.
- manter middleware central de `request.owner_user` fora deste recorte.

Motivo:
- o permission gate recém-criado depende de roles operáveis.
- criar middleware obrigatório antes de uma surface de gestão prenderia a evolução em autenticação ainda incompleta.
- gestão por command service mantém tenant-scope e evita regra de acesso espalhada nas views.
- auditoria de mudanças de owner é mais valiosa que log genérico de acesso neste ponto.

Consequência:
- roles administrativos deixam de depender apenas de seed/admin técnico.
- `accounts` se firma como dono de owner identity e access management inicial.
- o próximo endurecimento natural é resolver `request.owner_user` centralmente nas surfaces `/ops/`.

Status:
- executado

### Decisão: permissões administrativas começam por role gate mínimo
Decisão:
- usar `OwnerUser.role` como contrato inicial de permissões administrativas.
- criar `accounts.application.admin_permissions` como dono da matriz.
- aplicar o primeiro enforcement em criação de cupom, criação/edição de página e moderação de review.
- preservar compatibilidade quando a surface ainda não fornecer `actor_role`.

Motivo:
- o sistema já possui audit log para ações sensíveis, mas ainda precisava decidir quem pode executá-las.
- começar pelas mesmas ações auditadas reduz escopo e evita IAM completo prematuro.
- deixar a decisão em application services mantém views finas e evita regras duplicadas por módulo.
- bloquear antes da mutação evita gravar evento de domínio para uma ação que não aconteceu.

Consequência:
- roles `owner`, `admin`, `marketing`, `content_editor`, `support` e `viewer` passam a ter semântica inicial.
- permissões futuras devem ser adicionadas como keys explícitas, não como condicionais soltas em views.
- a próxima evolução natural é resolver `request.owner_user` de forma centralizada ou criar uma surface segura de gestão de roles.

Status:
- executado

### Decisão: discovery score pode assumir ordenação real com guardrail
Decisão:
- aprovar a troca controlada da ordenação real de catálogo para uma chave baseada em `discovery_rank_score`
- manter desempate determinístico por nome
- não incluir reviews, `sort=` público ou search engine externo na mesma troca
- exigir teste de compatibilidade da ordem fallback e teste persistido com múltiplos estados antes de considerar a troca concluída

Motivo:
- a ordem por score reproduz a ordem atual no fallback storefront
- o score já explicita os mesmos sinais comerciais da chave implícita anterior
- manter a troca isolada reduz risco em paginação, filtros rápidos e descoberta

Consequência:
- a próxima wave pode substituir `_catalog_initial_order_key(...)` por uma chave score-based em `list_products(...)`
- social proof continua como decoração visual até existir coleta bulk antes da paginação

Status:
- aprovado para execução controlada

### Decisão: storefront passa a ordenar por discovery score
Decisão:
- usar `discovery_rank_score` como base da ordenação real em `storefront_catalog_queries.list_products(...)`
- aplicar nome do produto como desempate determinístico
- manter `sort=` público, search engine externo e reviews fora desta mudança

Motivo:
- a wave anterior validou equivalência com a ordem fallback atual
- o score é mais explicável e testável que a chave implícita anterior
- a troca isola a mudança de ranking sem alterar templates, filtros ou payload visual

Consequência:
- a paginação storefront passa a seguir a ordem por score
- futuras mudanças de peso devem ser testadas como alteração explícita de ranking
- social proof só deve entrar depois de summary bulk antes da paginação

Status:
- executado

### Decisão: ranking de descoberta fica invisível no storefront
Decisão:
- não expor `discovery_rank_score` em UI pública
- não renderizar `discovery_rank_reason` diretamente nos cards nesta fase
- manter a experiência do comprador guiada por copy comercial já existente: oferta, disponibilidade, curadoria, estoque e review summary
- considerar explicabilidade primeiro em admin/ops antes de mostrar novos sinais no storefront

Motivo:
- score numérico é útil para operação e testes, mas não melhora a decisão do comprador
- os cards já têm sinais suficientes para explicar valor e próximo passo
- expor razão algorítmica agora criaria ruído e poderia repetir mensagens existentes
- reviews ainda não influenciam ranking, então a UI não deve sugerir isso

Consequência:
- o ranking real continua ativo, mas silencioso no storefront
- a próxima análise deve olhar admin/ops observability antes de novo texto público

Status:
- aprovado

### Decisão: discovery ranking aparece primeiro em admin/ops
Decisão:
- expor score, razão e componentes de discovery ranking na lista admin de produtos quando houver tenant resolvido
- manter a superfície read-only
- reutilizar `storefront_catalog_queries` como fonte do contrato de ranking
- não criar endpoint novo nem edição de pesos nesta fase

Motivo:
- merchant se beneficia da explicabilidade operacional sem poluir storefront
- score é linguagem de auditoria, não de compra
- tenant-scope evita misturar ranking storefront com catálogo global/fallback

Consequência:
- admin passa a ter observabilidade mínima sobre a ordem de descoberta
- futuras mudanças de peso podem ser auditadas antes de virar UX pública

Status:
- executado

### Decisão: Search & Discovery Foundation encerrada
Decisão:
- encerrar a trilha de fundação de Search & Discovery após ranking explícito, ordenação real e observabilidade admin
- não avançar agora para `sort=` público, busca externa, edição de pesos ou ranking por reviews
- recomendar próxima abordagem em productização de filtros e ordenação pública

Motivo:
- o ganho central da trilha foi capturado com baixo risco
- continuar adicionando features de busca agora teria ROI menor que validar filtros/sort como produto
- reviews ainda exigem mudança de coleta pré-paginação antes de entrar no ranking

Status:
- encerrado com Go

### Decisão: productizar sort público mínimo no storefront
Decisão:
- iniciar productização de filtros/sort com `sort=` público mínimo
- suportar inicialmente `recommended`, `price_asc`, `price_desc` e `name_asc`
- manter `recommended` como default baseado no ranking de descoberta atual
- preservar filtros existentes e paginação

Motivo:
- o ranking base já está explícito, testado e observável
- sort público pequeno melhora controle do cliente sem virar motor de busca
- preço e nome são critérios compreensíveis e não dependem de módulos externos
- reviews ainda não devem entrar porque summaries são pós-paginação

Consequência:
- a próxima wave deve implementar sort depois dos filtros e antes da paginação
- sort inválido deve voltar para `recommended`
- UI não deve expor score ou promessa de relevância baseada em reviews

Status:
- aprovado para execução

### Decisão: sort público mínimo executado e abordagem encerrada
Decisão:
- executar `sort=` público no storefront com `recommended`, `price_asc`, `price_desc` e `name_asc`
- expor o controle no `filter_bar` existente
- preservar paginação e fallback seguro para `recommended`
- encerrar a abordagem sem adicionar sort por reviews, novidades ou estoque bruto

Motivo:
- o cliente ganha controle básico de descoberta sem complexidade excessiva
- `recommended` continua apoiado no ranking explícito já testado
- preço e nome são critérios simples, compreensíveis e catalog-owned
- reviews ainda não estão disponíveis antes da paginação

Consequência:
- próximas evoluções devem focar busca textual/facets ou captura de analytics, não proliferar sort prematuramente

Status:
- encerrado com Go

### Decisão: busca storefront evolui por superfície textual leve
Decisão:
- expandir a busca pública da vitrine antes de adotar full-text, fuzzy search ou serviço externo
- manter a busca dentro do módulo `catalog`
- pesquisar apenas dados já tenant-scoped retornados pelo query service da vitrine
- priorizar nome, marca, SKU, categoria, descrição e textos públicos de card
- preservar o pipeline atual de busca, filtros, sort e paginação

Motivo:
- a busca atual é segura, mas limitada a nome, marca e SKU
- categoria e descrição são sinais catalog-owned e melhoram descoberta com baixo risco
- motor externo ou full-text ainda adicionaria complexidade antes de evidência de necessidade
- reviews e analytics ainda não devem influenciar o match textual

Consequência:
- a próxima wave deve implementar um helper puro/testável de matching textual
- copy de empty state deve refletir a superfície ampliada
- nenhum fallback global ou leitura cross-tenant deve ser introduzido

Status:
- aprovado para execução incremental

### Decisão: busca storefront textual leve executada
Decisão:
- implementar matching textual em helper puro de `catalog.application`
- expandir a superfície de busca para categoria, descrição e textos públicos de card/variante
- normalizar caixa, espaços e acentos
- usar semântica simples de todos os termos presentes
- encerrar a abordagem sem full-text, fuzzy, sinônimos ou serviço externo

Motivo:
- melhora descoberta pública com baixo risco e sem mudar persistência
- mantém a view fina e a regra testável
- preserva tenant-scope porque o match acontece sobre a lista já escopada
- evita misturar ranking de descoberta, reviews e busca textual antes de evidência de necessidade

Consequência:
- próximas evoluções de descoberta devem priorizar facets ou analytics antes de sofisticar busca
- se busca crescer em complexidade, o próximo passo natural é full-text PostgreSQL ou índice dedicado com contrato explícito

Status:
- encerrado com Go

### Decisão: facets públicas mínimas no storefront
Decisão:
- evoluir filtros da vitrine para um contrato explícito de facets públicas mínimas
- preservar `q`, `category`, `quick_filter` e `sort`
- considerar `availability`, `offer`, `price_min` e `price_max` como primeiros parâmetros facetados
- manter facets derivadas apenas da lista tenant-scoped do catálogo
- não criar contagens, reviews facets, atributos variantes arbitrários ou índice externo nesta etapa

Motivo:
- a vitrine já possui filtros úteis, mas eles ainda estão espalhados entre categoria e recortes rápidos
- facets explícitas melhoram descoberta sem exigir motor de busca completo
- disponibilidade, oferta e preço são sinais catalog-owned e compreensíveis para o cliente
- contagens e facets avançadas podem criar complexidade antes de estabilizar o contrato público

Consequência:
- a próxima wave deve implementar facets pequenas, compatíveis com a querystring atual
- busca deve continuar antes dos facets e sort depois dos facets
- nenhum valor facetado pode vazar dados entre tenants

Status:
- aprovado para execução incremental

### Decisão: facets públicas mínimas executadas no storefront
Decisão:
- implementar `availability`, `offer`, `price_min` e `price_max` como facets públicas explícitas
- preservar compatibilidade com `q`, `category`, `quick_filter` e `sort`
- aplicar facets depois de busca/categoria e antes de `quick_filter`/sort
- renderizar facets no `filter_bar` existente
- encerrar a abordagem sem contagens, review facets, atributos variantes arbitrários ou índice externo

Motivo:
- o cliente ganha refinamento objetivo sem complexidade excessiva
- disponibilidade, oferta e preço são sinais catalog-owned
- o pipeline continua previsível e tenant-scoped
- `quick_filter` permanece compatível para recortes editoriais/legados

Consequência:
- próximas decisões de descoberta devem ser orientadas por analytics/telemetria antes de adicionar filtros avançados
- conflitos entre facets e quick filters continuam resolvidos por aplicação sequencial e empty state

Status:
- encerrado com Go

### Decisão: analytics de descoberta storefront por contrato leve
Decisão:
- definir analytics de descoberta como contrato catalog-owned antes de criar persistência ou dashboard
- considerar `catalog.discovery_viewed`, `catalog.search_performed`, `catalog.facets_applied`, `catalog.sort_changed`, `catalog.product_card_clicked` e `catalog.product_detail_viewed`
- carregar `tenant_id`, sessão anônima, contexto de filtros/sort e contagem de resultados
- não registrar PII nem querystring bruta sensível
- não usar analytics para alterar ranking nesta etapa

Motivo:
- busca, sort e facets já existem; o próximo ganho depende de entender uso real
- contrato leve evita construir filtros/ranking às cegas
- eventos de descoberta pertencem à fronteira do catálogo na origem
- persistência, dashboards e módulo `analytics` podem esperar até o contrato estabilizar

Consequência:
- a próxima wave deve criar service/publisher no-op seguro e testável em `catalog.application`
- eventos sem tenant resolvido devem ser descartados
- falha de analytics não pode bloquear renderização storefront

Status:
- aprovado para execução incremental

### Decisão: contrato de analytics de descoberta executado com publisher no-op
Decisão:
- criar service de analytics em `catalog.application` com dataclass de evento e publisher substituível
- emitir eventos server-side para listagem e PDP
- usar publisher no-op como implementação padrão
- descartar eventos sem `tenant_id`
- engolir falhas do publisher para não bloquear storefront
- encerrar a abordagem sem persistência, dashboard ou provider externo

Motivo:
- a boundary permite observar descoberta sem acoplar a view a um pipeline definitivo
- server-side cobre busca, facets, sort e PDP view sem depender de JavaScript
- no-op reduz risco operacional até haver decisão de retenção/agregação
- tenant-scope e ausência de PII ficam explícitos no contrato inicial

Consequência:
- próxima evolução deve decidir persistência/agregação ou seguir para conversão PDP
- click real de card ainda exige instrumentação específica futura
- qualquer publisher real deve respeitar o protocolo atual e não bloquear request

Status:
- encerrado com Go

### Decisão: persistência mínima de analytics de descoberta
Decisão:
- avançar para persistência mínima de eventos brutos tenant-scoped de descoberta storefront
- manter origem dos eventos em `catalog`
- persistir atrás do protocolo de publisher já existente
- salvar sessão apenas como hash/anônimo, nunca crua
- limitar payload a chaves públicas permitidas
- adiar dashboard, agregações, personalização e click tracking real

Motivo:
- o contrato no-op já está testado e pronto para publisher real
- eventos brutos por tenant permitem descobrir termos sem resultado, uso de facets/sort e PDPs vistos
- persistência mínima gera evidência sem transformar catálogo em produto de analytics completo
- retenção e privacidade precisam ser explícitas antes de produção real

Consequência:
- a próxima wave deve criar modelo/migration de log e publisher persistente best-effort
- toda query futura sobre analytics deve exigir tenant explícito
- eventos brutos devem ter retenção curta inicial, recomendada em 30 dias

Status:
- aprovado para execução incremental

### Decisão: event log persistente de descoberta storefront executado
Decisão:
- criar `StorefrontDiscoveryEventLog` como log bruto tenant-scoped
- usar publisher Django persistente atrás do protocolo existente
- salvar `session_key` apenas como hash
- persistir somente payload allowlisted
- descartar eventos sem tenant e nomes não catalogados
- encerrar a abordagem sem dashboard, agregações, limpeza automática ou ranking analytics-driven

Motivo:
- eventos brutos permitem aprendizado inicial de busca/facets/sort/PDP sem pipeline complexo
- hash de sessão preserva análise de sessão sem armazenar identificador cru
- allowlist reduz risco de PII e querystring sensível
- manter publisher substituível preserva fronteira da view e facilita futura fila/agregação

Consequência:
- próxima evolução operacional deve tratar retenção/limpeza antes de volume real
- qualquer query/admin surface deve exigir tenant explícito
- click tracking real de card e atribuição checkout seguem fora de escopo

Status:
- encerrado com Go

### Decisão: PDP conversion evolui por feedback de ação
Decisão:
- priorizar feedback pós-add-to-cart e clareza de decisão no PDP
- manter buy-now como caminho direto para checkout
- preservar fronteira de `cart` para adicionar item e `checkout` para ativar compra imediata
- não iniciar cross-sell, wishlist, sticky add-to-cart ou recomendação personalizada nesta etapa
- considerar CTA analytics como extensão futura, sem bloquear a primeira execução

Motivo:
- o PDP já possui base forte de galeria, variante, preço, estoque e reviews
- a maior lacuna atual é o feedback da ação, não falta de conteúdo
- feedback claro reduz incerteza após clique e melhora continuidade de compra
- recomendações/cross-sell seriam prematuras antes de consolidar o fluxo principal

Consequência:
- a próxima wave deve melhorar add-to-cart success/conflict/unavailable com impacto mínimo
- qualquer mudança deve preservar idempotência do carrinho e tenant-scope
- out-of-stock não deve criar pedido nem carrinho silencioso

Status:
- aprovado para execução incremental

### Decisão: add-to-cart do PDP retorna com feedback contextual
Decisão:
- redirecionar add-to-cart bem-sucedido de volta ao PDP com `cart_feedback=added`
- exibir alerta contextual no PDP além da mensagem global
- preservar variante selecionada na URL de retorno
- mapear conflitos/indisponibilidade para feedbacks explícitos
- manter buy-now direcionando para checkout

Motivo:
- o cliente recebe confirmação clara sem perder o contexto do produto/variante
- o carrinho continua sendo mutado exclusivamente por `cart`
- a mudança melhora continuidade de compra sem criar cross-sell ou novo funil
- idempotência do carrinho permanece protegida

Consequência:
- o carrinho deixa de ser destino automático do add-to-cart no PDP
- próximas melhorias podem instrumentar intenção de CTA em analytics
- recomendações, sticky CTA e wishlist seguem fora do escopo atual

Status:
- executado

### Decisão: PDP registra intenção de CTA server-side
Decisão:
- adicionar `catalog.pdp_cta_intent` ao contrato de analytics persistente
- emitir o evento no POST do PDP para `add_to_cart`, `buy_now` e indisponibilidade
- registrar `cta_intent`, `cta_result`, `quantity` e `variant_sku`
- manter emissão server-side, sem JavaScript
- encerrar PDP Conversion sem cross-sell, sticky CTA, wishlist ou personalização

Motivo:
- depois do feedback de ação, a próxima evidência útil é saber quais CTAs são acionados e com qual resultado
- server-side captura apenas intenções reais submetidas ao backend
- o publisher persistente já sanitiza sessão/payload e preserva tenant-scope
- o evento não altera carrinho, checkout ou ranking

Consequência:
- admin/analytics futuro pode medir funil PDP sem instrumentação client-side inicial
- click tracking visual e atribuição checkout/pedido seguem fora de escopo
- próxima abordagem pode avaliar uma surface admin mínima para contagens tenant-scoped

Status:
- PDP Conversion encerrado com Go

### Decisão: admin analytics inicial será read-only e tenant-scoped
Decisão:
- criar uma primeira leitura admin mínima para eventos de descoberta/conversão
- manter a surface em `catalog` enquanto não existir módulo `analytics`
- limitar a contadores por evento e eventos recentes
- filtrar opcionalmente por `event_name`
- não criar dashboard pesado, gráficos, exportação ou edição

Motivo:
- já existe log persistente suficiente para uma leitura operacional simples
- merchants/ops precisam validar se eventos estão chegando antes de investir em agregações
- read-only reduz risco e evita transformar analytics em produto grande cedo demais
- tenant-scope explícito evita vazamento entre lojas

Consequência:
- próxima wave deve criar query service, rota e template admin simples
- toda query deve exigir tenant explícito
- payload bruto e `session_key_hash` não devem ser destacados por padrão

Status:
- aprovado para execução incremental

### Decisão: admin analytics read-only executado em catalog
Decisão:
- expor `/ops/catalog/analytics/` como leitura admin inicial de conversão
- manter consulta em `catalog.application` via `admin_conversion_analytics_queries`
- listar apenas contadores por evento e eventos recentes
- permitir filtro por `event_name`
- não exibir `session_key_hash` nem payload bruto completo

Motivo:
- operadores precisam confirmar se discovery/PDP/CTA estão chegando por tenant
- a leitura ainda é pequena demais para justificar módulo `analytics`
- o formato read-only evita criar operação ou produto de BI cedo demais
- tenant-scope explícito é mais importante que gráficos nesta fase

Consequência:
- admins ganham uma primeira visibilidade operacional sobre conversão storefront
- dashboards, exportação, retenção e agregações temporais continuam fora de escopo
- próxima decisão deve escolher entre encerrar a trilha ou evoluir para agregados de analytics

Status:
- executado

### Decisão: encerrar analytics admin inicial de conversão
Decisão:
- encerrar a abordagem Storefront Conversion Analytics Admin após a surface read-only
- não evoluir agora para dashboard, gráficos, exportação ou agregados temporais
- manter os eventos brutos como evidência operacional mínima
- priorizar próxima abordagem com impacto direto em conversão storefront

Motivo:
- a pergunta crítica da fase era confirmar chegada dos sinais por tenant
- a rota `/ops/catalog/analytics/` já cobre leitura operacional mínima
- expandir analytics agora teria retorno menor que melhorar fricções visíveis do funil
- manter analytics pequeno reduz risco de acoplamento em `catalog`

Consequência:
- analytics admin permanece como validação e suporte, não como produto completo
- pruning/agregações/atribuição ficam para uma trilha dedicada futura
- próxima frente recomendada é otimização de conversão storefront com foco customer-facing

Status:
- encerrado com Go

### Decisão: otimização de conversão começa por clareza no carrinho
Decisão:
- iniciar Storefront Conversion Optimization pelo recorte cart-to-checkout
- adicionar no carrinho um bloco read-only de “Próximo passo seguro”
- explicar que itens ainda são revisáveis, frete vem no checkout e pedido ainda não foi criado
- não alterar regra de criação de pedido, checkout, estoque ou pagamento

Motivo:
- o maior ROI imediato estava em reduzir dúvida customer-facing antes do checkout
- a infraestrutura de carrinho/checkout já existe; faltava clareza de transição
- microcopy estruturada tem baixo risco e não cruza fronteiras de domínio
- calcular frete, reservar estoque ou criar wizard novo seria escopo maior e mais arriscado

Consequência:
- o cliente entende melhor que ir para checkout ainda é seguro e reversível
- `cart` continua dono da intenção pré-checkout
- `checkout` continua dono de entrega, pagamento e criação do pedido
- próxima trilha recomendada é revisar promessa de entrega/frete sem antecipar regra final

Status:
- executado e encerrado

### Decisão: instrumentação inicial do AuditLog por ações sensíveis
Decisão:
- começar a gravar `AuditLog` apenas em criação de cupom, criação/edição de página e moderação de review.
- manter a chamada dentro dos application services donos de cada regra.
- não criar middleware global, hooks automáticos de model ou log genérico de leitura.

Motivo:
- cupons têm impacto comercial e financeiro.
- páginas publicadas afetam storefront e SEO.
- reviews aprovadas/rejeitadas afetam prova social e confiança.
- instrumentar tudo agora aumentaria ruído operacional sem melhorar governança real.

Consequência:
- `audit` passa a receber primeiros eventos de produção com baixo acoplamento.
- os módulos continuam decidindo suas regras localmente.
- novas ações auditáveis devem entrar por decisão explícita, não por logging automático.

Status:
- executado

### Decisão: próximo ROI sistêmico é Storefront Content & SEO Foundation
Decisão:
- reeleger a próxima abordagem sistêmica para **Storefront Content & SEO Foundation Review**
- priorizar o módulo `pages` como contrato tenant-owned mínimo de páginas institucionais e SEO básico
- não reabrir agora checkout, cart, coupons, reviews, discovery, payments ou refunds para refinamentos incrementais

Motivo:
- as trilhas transacionais e de conversão já entregaram fundação suficiente para esta fase
- `pages` permanece skeleton e ainda bloqueia confiança institucional, aquisição orgânica e completude pública da loja
- o recorte é baixo risco porque pode nascer `published-only`, tenant-scoped e sem impacto em checkout/pagamento/pedido/estoque
- `newsletter`, retention e governança SaaS ficam mais bem posicionados depois de existir conteúdo público mínimo

Consequência:
- a próxima evolução deve começar por contrato de domínio/query em `pages.application`
- admin lite e renderização storefront devem respeitar tenant resolvido e não usar fallback global
- page builder, SEO engine avançado, tradução, menus e automação de marketing continuam fora de escopo inicial

Status:
- aprovado como próxima abordagem recomendada

### Decisão: pages nasce como conteúdo institucional tenant-owned
Decisão:
- criar `Page` como modelo tenant-scoped com `slug`, `title`, `body`, `status`, `seo_title` e `seo_description`
- expor admin lite em `/ops/pages/` para listagem, criação e edição simples
- expor storefront em `/pages/<slug>/` apenas para páginas publicadas do tenant resolvido
- manter page builder, menus, tradução, SEO engine e automação de marketing fora do primeiro corte

Motivo:
- `pages` era skeleton e bloqueava confiança institucional e SEO básico do storefront
- o recorte published-only evita publicar rascunhos ou conteúdo de outro tenant
- views continuam finas e a regra fica em `pages.application`
- o contrato não toca checkout, cart, payments, orders, estoque ou events

Consequência:
- a loja ganha uma base pública de conteúdo institucional com baixo risco
- qualquer evolução futura de newsletter/retention pode depender de páginas já tenant-owned
- navegação dinâmica, editor avançado e analytics de conteúdo seguem como trilhas futuras

Status:
- executado como fundação inicial

### Decisão: Storefront Content & SEO Foundation encerrada no recorte pages
Decisão:
- encerrar a abordagem após `Page` tenant-scoped, admin lite, storefront published-only e link operacional
- não avançar agora para navegação dinâmica, footer gerenciado, preview, page builder ou newsletter capture
- manter próximas expansões de conteúdo dependentes de demanda real de aquisição/SEO

Motivo:
- o principal gap skeleton de `pages` foi removido com baixo risco
- a loja já consegue publicar conteúdo institucional básico sem tocar fluxo transacional
- continuar agora tenderia a transformar `pages` em CMS antes da validação do uso real

Consequência:
- `pages` passa de skeleton para bom o suficiente nesta fase
- a próxima seleção de ROI pode escolher entre retention/newsletter, platform governance ou melhorias editoriais específicas
- qualquer nova surface pública deve continuar published-only e tenant-scoped

Status:
- encerrado com Go

### Decisão: retention começa por newsletter opt-in tenant-scoped
Decisão:
- criar `NewsletterSubscriber` como modelo tenant-scoped de opt-in
- garantir unicidade por `(tenant, email)` e permitir o mesmo e-mail em lojas diferentes
- registrar status `subscribed|unsubscribed`, origem e consentimento
- expor inscrição pública em `/newsletter/` e leitura admin em `/ops/newsletter/`
- manter campanhas, segmentação, automação e envio real fora do primeiro corte

Motivo:
- depois de `pages`, o próximo gap customer-facing de baixo risco era captura explícita de interesse
- newsletter opt-in prepara retenção sem acoplar checkout, pedidos, pagamentos ou estoque
- envio real pertence a uma trilha futura com `notifications`, não ao primeiro contrato de captura
- preservar descadastro como status mantém histórico sem apagar consentimento

Consequência:
- `newsletter` passa de skeleton para bom o suficiente nesta fase
- campanhas e lifecycle messaging ainda exigem decisão própria antes de usar `notifications`
- a próxima seleção de ROI deve comparar governança SaaS, retention avançada e operações

Status:
- executado e encerrado

### Decisão: governança de produção começa por AuditLog mínimo
Decisão:
- criar `AuditLog` como ledger administrativo mínimo
- exigir tenant por padrão em eventos tenant-owned
- permitir platform-scope apenas com `allow_platform_scope=True`
- expor `/ops/audit/` como leitura admin read-only por tenant
- não instrumentar todos os módulos automaticamente nesta etapa

Motivo:
- produção SaaS multi-lojista precisa de rastreabilidade antes de avançar em permissions/subscriptions
- audit log pode nascer com baixo risco porque não corrige dados nem dispara efeito colateral
- instrumentação ampla cedo demais criaria ruído e acoplamento com módulos ainda em evolução
- metadados sanitizados reduzem risco de armazenar payload sensível

Consequência:
- `audit` passa de skeleton para bom o suficiente como fundação
- próximas waves devem escolher ações sensíveis específicas para instrumentação
- subscriptions, owner permissions, retenção de logs e exportação continuam fora do primeiro corte

Status:
- executado e encerrado

### Decisão: promessa de entrega pré-checkout é informativa
Decisão:
- criar um contrato `shipping.application.delivery_promise_queries`
- exibir no carrinho uma promessa de entrega antes do checkout
- apresentar preços como “a partir de”
- deixar explícito que valores e prazos finais dependem do endereço no checkout
- não persistir frete nem alterar total do carrinho

Motivo:
- o cliente precisa entender que há opções de entrega antes de avançar
- cart não deve virar dono de cálculo logístico final
- checkout já é o boundary correto para endereço, método de entrega, pagamento e pedido
- uma promessa honesta reduz fricção sem criar risco financeiro/logístico

Consequência:
- `shipping` passa a ter um contrato customer-facing pré-checkout
- `cart` consome apenas leitura informativa
- quote real por CEP fica para trilha futura
- próxima abordagem recomendada é hardening da escolha de entrega dentro do checkout

Status:
- executado e encerrado

### Decisão: checkout rejeita método de entrega inválido
Decisão:
- retornar `checkout-shipping-method-invalid` quando o método enviado não existe na sessão
- não salvar contato/endereço/frete nessa submissão inválida
- manter a etapa em `delivery`
- exibir feedback customer-facing explícito

Motivo:
- seleção inválida de entrega não deve ser ignorada silenciosamente
- manter frete antigo sem feedback cria ambiguidade antes de pagamento/revisão
- o checkout é o boundary correto para escolha final de frete
- quote real por CEP ainda é escopo futuro e não deve ser misturado a hardening

Consequência:
- a sessão só avança quando a modalidade de entrega é válida
- totais não mudam em submissão inválida
- a próxima frente natural é aplicar hardening equivalente ao método de pagamento

Status:
- executado e encerrado

### Decisão: checkout rejeita método de pagamento inválido
Decisão:
- retornar `checkout-payment-method-invalid` quando o método enviado não existe na sessão
- não salvar dados da sessão nessa submissão inválida
- manter a etapa em `payment`
- exibir feedback customer-facing explícito

Motivo:
- seleção inválida de pagamento não deve ser ignorada silenciosamente
- manter pagamento anterior com nova submissão inválida cria drift antes da revisão
- `checkout` escolhe método; `payments` executa tentativa real depois
- hardening deve proteger o contrato sem criar provider/payment execution novo

Consequência:
- a revisão final só recebe método de pagamento válido
- termos/parcelas não mudam em submissão inválida
- entrega e pagamento agora possuem guardrails equivalentes

Status:
- executado e encerrado

### Decisão: encerrar hardening de etapas do checkout
Decisão:
- considerar suficientes os guardrails de etapa do checkout neste ciclo
- manter progressão `cart → delivery → payment → review`
- preservar rollback seguro quando uma etapa é solicitada cedo demais
- não abrir nova feature de checkout nesta abordagem

Motivo:
- entrega e pagamento inválidos agora possuem result codes explícitos
- requests para etapas futuras já retornam para a etapa segura possível
- conclusão continua protegida por readiness, estoque e snapshot
- continuar agora tenderia a abrir provider/payment/frete real sem necessidade objetiva

Consequência:
- checkout fica pronto como funil server-rendered progressivo para esta fase
- próximos ganhos devem ser de copy/trust leve ou trilhas maiores bem separadas
- provider real, frete por CEP e fulfillment permanecem fora deste fechamento

Status:
- encerrado com Go

### Decisão: encerrar copy/trust do checkout com bloco lateral
Decisão:
- adicionar um bloco estável de confiança no sidebar do checkout
- reforçar que pedido só nasce na revisão
- reforçar que pagamento real fica pendente
- reforçar que estoque é revalidado antes de criar pedido
- não alterar fluxo, eventos, pedidos, pagamentos, frete ou estoque

Motivo:
- a copy já estava correta, mas dispersa em várias áreas
- um bloco estável reduz ansiedade antes da ação final
- a mudança tem baixo risco e não cruza fronteiras de domínio
- continuar refinando checkout agora teria retorno menor que reeleger o próximo eixo sistêmico

Consequência:
- checkout fica mais claro customer-facing sem nova feature
- a trilha de micro-hardening/copy do checkout pode ser encerrada
- próxima recomendação é uma revisão de ROI sistêmico

Status:
- executado e encerrado

### Decisão: banco único com tenant_id
Motivo:
- menor complexidade operacional
- melhor custo
- bom caminho para MVP e crescimento

### Decisão: UI server-rendered
Stack:
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

Motivo:
- alta produtividade
- menor complexidade que SPA
- excelente encaixe com Django

### Decisão: gateway inicial
- Pagar.me

### Decisão: frete inicial
- API de frete desde o MVP

### Decisão: design system documentado
Motivo:
- consistência visual
- reutilização
- melhor atuação do Codex

### ADR: namespace modules.*
Decisão:
- `INSTALLED_APPS` usa `modules.*` como namespace público de registro dos apps.
- O código-fonte real permanece em `app.modules.*`.
- O diretório `backend/modules/` funciona como camada de alias para alinhar implementação e documentação.

Motivo:
- manter compatibilidade com a estrutura já bootstrapada em `app.modules.*`
- alinhar com a convenção documental do projeto (`modules.*`)
- evitar refactor estrutural grande nesta fase inicial

### Decisão: login owner/admin tenant-scoped
Decisão:
- `/accounts/login/` autentica owner/admin por Django `User` e valida `OwnerUser` ativo no tenant atual.
- o vínculo administrativo é `tenant + User.email`.
- redirect pós-login só aceita `next` seguro para o mesmo host.
- login/logout owner geram `AuditLog`.

Motivo:
- permitir ativar o gate de `/ops/` sem depender de fallback visual ou sessão implícita.
- preservar separação entre `OwnerUser`, `Customer` e `AccountProfile`.
- evitar acesso administrativo cross-tenant por credencial válida em outro tenant.

Consequência:
- customer login completo continua fora de escopo.
- convite, reset de senha, MFA e ativação default do gate ficam para waves posteriores.

### Decisão: ativação controlada do gate `/ops/`
Decisão:
- `HUBX_OPS_AUTH_GATE_ENFORCED=1` deve ser ativado por ambiente, não por default no código.
- antes da ativação, executar `ops_auth_gate_readiness --fail-on-blockers`.
- blockers incluem tenant ativo sem owner ativo, owner sem `User` Django ativo correspondente e e-mail ambíguo em `User`.

Motivo:
- o gate já bloqueia `/ops/` quando não há `request.owner_user`.
- ativar sem preflight pode impedir acesso administrativo legítimo em tenants sem owner/user preparado.
- o comando cria um ponto objetivo de Go/No-Go operacional.

Consequência:
- rollout pode ser gradual por ambiente ou tenant.
- criação/convite/reset de owner segue como próxima evolução natural.

### Decisão: convite e reset owner/admin mínimos
Decisão:
- `accounts` passa a gerar convite e reset de senha para `OwnerUser`.
- convite cria/reusa `User` Django ativo com o mesmo e-mail do owner.
- reset usa token padrão Django e exige owner ativo no tenant atual.
- `forgot-password` responde genericamente para não enumerar owner/user.

Motivo:
- ativar o gate `/ops/` exige caminho operacional para preparar acesso de owners reais.
- manter o vínculo por `tenant + OwnerUser.email + User.email` evita misturar owner, customer e account profile.
- token Django entrega segurança suficiente para esta fase sem criar infraestrutura própria.

Consequência:
- envio real de e-mail fica fora de `accounts` e deve ser tratado por `notifications`.
- MFA, SSO e política avançada de convite continuam fora de escopo.

### Decisão: delivery de owner access via notifications
Decisão:
- convite e reset owner/admin registram `EmailLog` planejado em `notifications`.
- `accounts` não chama provider de e-mail diretamente.
- `notifications` usa o pipeline existente de processamento/dry-run para entregar esses logs.

Motivo:
- preservar boundary entre acesso administrativo e delivery transacional.
- aproveitar observabilidade, comandos e estado de `EmailLog` já existentes.
- evitar acoplamento de SMTP/provider dentro de `accounts.application`.

Consequência:
- HTML/branding de e-mail e automação de fila ficam para abordagem futura.
- operação pode processar logs owner access com `process_email_logs`.

### Decisão: owner access pronto com gate condicionado a readiness
Decisão:
- a trilha técnica de owner access é considerada pronta para rollout controlado.
- `HUBX_OPS_AUTH_GATE_ENFORCED=1` só deve ser ativado quando `ops_auth_gate_readiness --fail-on-blockers` passar no ambiente alvo.
- tenants sem owner ativo ou sem `User` Django correspondente permanecem No-Go operacional.

Motivo:
- login, gate, convite, reset, delivery e auditoria já existem.
- o risco restante é provisionamento inicial de dados administrativos, não ausência de fluxo técnico.

Consequência:
- próxima evolução deve focar provisionamento inicial de owner por tenant.
- ativar o gate antes disso pode bloquear `/ops/` para tenants reais.

### Decisão: provisionamento inicial de owner por comando operacional
Decisão:
- criar `provision_initial_owner` para provisionar owner/user inicial por tenant.
- exigir `tenant_id` e e-mail explícitos.
- criar `User` com senha inutilizável quando necessário.
- registrar `owner.initial_provisioned` em auditoria.

Motivo:
- readiness do gate depende de pelo menos um owner/user ativo por tenant.
- comando operacional é mais seguro que endpoint público de bootstrap.
- senha inutilizável força o fluxo de convite/reset já auditado.

Consequência:
- ativação do gate passa a ter um caminho claro para preparar tenants.
- batch global, convite automático e definição direta de senha continuam fora de escopo.

### Decisão: ativação do gate `/ops/` por preflight de ambiente
Decisão:
- criar `ops_gate_activation_preflight` como Go/No-Go antes/depois do switch.
- validar readiness de tenants, estado esperado do gate e readiness opcional de e-mail.
- não alterar env/deploy automaticamente pelo comando.

Motivo:
- ativação real depende de configuração de ambiente e restart/redeploy.
- separar preflight de mudança reduz risco operacional.
- staging precisa validar o mesmo contrato que produção usará depois.

Consequência:
- rollout de produção deve reaproveitar o preflight com checklist e evidências.
- ativação default no código continua fora de escopo.

### Decisão: rollout de produção do gate `/ops/` por evidência tenant-by-tenant
Decisão:
- criar `ops_gate_production_rollout` para consolidar evidência Go/No-Go por tenant.
- exigir gate enabled e provider de e-mail real por padrão.
- bloquear por falhas de `EmailLog` por padrão.
- não alterar env/deploy automaticamente.

Motivo:
- produção exige evidência registrável e rollback claro.
- readiness técnico sozinho não cobre saúde de delivery owner access.
- rollout por tenant reduz blast radius.

Consequência:
- ativação global em lote fica fora de escopo.
- próxima evolução deve observar falhas pós-ativação e fricção de login.

### Decisão: monitoramento pós-ativação do gate `/ops/`
Decisão:
- expor métricas owner access em `/accounts/metrics/owner-access/`.
- proteger o endpoint com `ACCOUNTS_OBSERVABILITY_TOKEN`.
- instrumentar falhas de login, redirects anônimos e 403 do gate via `AuditLog`.
- agregar status de `EmailLog` owner access no mesmo payload Prometheus.

Motivo:
- o gate pode bloquear operadores; o endpoint de métricas não deve depender de `/ops/`.
- `AuditLog` já é a trilha persistida das decisões sensíveis de acesso.
- e-mails de convite/reset são parte crítica do fluxo owner/admin pós-ativação.

Consequência:
- dashboard dedicado e rate limiting ficam para abordagem posterior.
- alertas Prometheus podem ser ligados junto do rollout do gate.

### Decisão: rate limit leve no login owner/admin
Decisão:
- aplicar rate limit por tenant + login + IP no POST de `/accounts/login/`.
- usar cache Django, sem persistir lockout no banco.
- retornar `429` e `Retry-After` durante lockout.
- auditar `owner.login_rate_limited`.

Motivo:
- reduz brute force básico sem criar IAM completo.
- mantém mensagens genéricas e evita enumeração.
- preserva rollback simples via configuração de limites.

Consequência:
- MFA, captcha e lockout persistido ficam fora de escopo.
- monitoramento Prometheus passa a alertar quando o rate limit aciona.

### Decisão: política explícita de sessão owner/admin
Decisão:
- aplicar duração explícita no login owner/admin.
- usar `OWNER_SESSION_IDLE_SECONDS` para sessão curta padrão.
- usar `OWNER_SESSION_REMEMBER_SECONDS` apenas quando `remember_me` for marcado.
- registrar a política aplicada no `AuditLog owner.login`.
- manter logout via `django_logout`.

Motivo:
- sessões administrativas não devem depender silenciosamente do default global Django.
- remember-me precisa ser escolha explícita do operador.
- metadados de auditoria ajudam investigação sem criar um IAM completo.

Consequência:
- customer login não herda essa política automaticamente.
- revogação centralizada, gestão de dispositivos, MFA e SSO continuam fora de escopo.
- settings globais de cookie continuam protegendo também sessões não-owner.

### Decisão: RBAC administrativo granular por matriz em accounts
Decisão:
- manter a matriz inicial de roles/permissões em `accounts.application.admin_permissions`.
- centralizar leitura de tenant, role e permissões de request em `accounts.interfaces.admin_rbac`.
- esconder actions visuais de `/ops/` quando a role não possui a permissão necessária.
- manter validação de writes sensíveis nos command services dos módulos donos.

Motivo:
- evita espalhar lookup de `OwnerUser.role` por views de módulos diferentes.
- melhora UX e reduz tentativa acidental de ação negada.
- preserva compatibilidade legada enquanto o gate `/ops/` ainda pode estar desligado.

Consequência:
- `OwnerUser.role` continua sendo a fonte simples de autorização nesta fase.
- permission matrix persistida, grupos Django e UI de RBAC ficam fora de escopo.
- módulos operacionais ainda podem renderizar leituras, mas não devem decidir a matriz de permissões.

### Decisão: navegação `/ops/` personalizada por RBAC
Decisão:
- filtrar atalhos e filas do cockpit `/ops/` pela matriz de permissões de `accounts`.
- adicionar permissões leves de navegação/leitura para pedidos, catálogo, clientes, shipping, newsletter, audit e payments.
- usar `accounts.interfaces.admin_rbac.request_admin_can(...)` como único helper de request.
- manter compatibilidade quando não há role explícita resolvida.

Motivo:
- reduz fricção operacional para roles limitadas.
- evita apresentar caminhos que resultarão em bloqueio de write ou ação indisponível.
- prepara a próxima decisão de enforcement granular por rota sem acoplar middleware prematuramente.

Consequência:
- ocultação visual não substitui validação de command services.
- URLs `/ops/` ainda não têm permission middleware granular nesta fase.
- o shell lateral global permanece fora do recorte.

### Decisão: enforcement HTTP granular para `/ops/`
Decisão:
- aplicar permissão por prefixo de URL dentro do `OpsAuthenticationGateMiddleware`.
- executar o enforcement apenas quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`.
- manter `/ops/` raiz acessível para qualquer owner/admin ativo.
- registrar negações como `owner.ops_permission_denied`.
- exportar e alertar esse action pela observabilidade de accounts.

Motivo:
- ocultação visual não é controle suficiente contra URL direta.
- o gate já é o ponto central do ciclo HTTP `/ops/`.
- manter o enforcement no middleware evita espalhar RBAC por cada módulo.

Consequência:
- roles limitadas passam a receber `403` em rotas diretas sem permissão.
- command services continuam responsáveis pelo bloqueio final de writes.
- granularidade por método, matriz persistida e UI de permissões ficam fora de escopo.

### Decisão: readiness de produção para RBAC granular
Decisão:
- criar `ops_rbac_production_readiness` como evidência Go/No-Go para ativação real.
- validar estado esperado do gate, matriz de permissões, full admin por tenant e roles desconhecidas.
- não alterar ambiente, usuários ou roles automaticamente.

Motivo:
- RBAC granular pode bloquear rotas operacionais reais se roles estiverem incompletas.
- rollout tenant-by-tenant precisa de evidência anexável ao change log.
- separar evidência de ativação reduz blast radius.

Consequência:
- tenants sem `owner/admin` ativo com `User` Django correspondente são No-Go.
- ativação/rollback continuam por env `HUBX_OPS_AUTH_GATE_ENFORCED`.
- ajustes automáticos de role/provisionamento ficam fora de escopo.
## 2026-04-28 — Platform RBAC Staging Activation Evidence Review

Decisão:

- criar um pacote de evidência de staging para RBAC granular em `/ops/` como comando read-only de `accounts`.

Motivação:

- ativação de staging precisa de saída reproduzível, checklist manual mínimo e rollback sem depender de interpretação solta do runbook.

Implementação:

- `accounts.application.ops_rbac_staging_evidence_queries` compõe preflight do gate e readiness de RBAC.
- `ops_rbac_staging_activation_evidence` imprime comandos de reprodução, resultados, testes manuais e rollback.

Consequências:

- o comando é seguro para rodar localmente, mas não afirma evidência real de staging fora do ambiente alvo.
- nenhuma variável de ambiente, role, usuário ou tenant é alterado pela captura.

## 2026-04-28 — Platform RBAC Production Activation Evidence Review

Decisão:

- criar um pacote agregado de evidência para ativação/manutenção do RBAC granular em `/ops/` em produção.

Motivação:

- produção precisa combinar rollout do gate, readiness de RBAC, health de e-mail/notificações, checklist manual e rollback em uma saída única anexável.

Implementação:

- `accounts.application.ops_rbac_production_activation_evidence_queries` compõe `ops_gate_production_rollout` e `ops_rbac_production_readiness`.
- `ops_rbac_production_activation_evidence` imprime comandos de reprodução, resultados, health por tenant, testes manuais e rollback.

Consequências:

- provider de e-mail real e ausência de falhas de notification owner access bloqueiam por padrão.
- o comando é read-only e não executa ativação, deploy, restart ou alteração de roles.
- execução local não substitui evidência real de produção.

## 2026-04-28 — Platform RBAC Post-Production Monitoring Review

Decisão:

- criar snapshot operacional pós-produção do RBAC para classificar sinais em `HEALTHY`, `WATCH` e `ROLLBACK`.

Motivação:

- após ativar RBAC em produção, a decisão crítica não é só ver métricas brutas, mas saber quando observar, corrigir roles ou considerar rollback do gate.

Implementação:

- `accounts.application.ops_rbac_post_production_monitoring_queries` lê `AuditLog` e `EmailLog` recentes.
- `ops_rbac_post_production_monitoring` imprime contagens, sinais watch e sinais rollback.
- alerta `HubxAccountsRBACPostProductionRollbackSignal` cobre rate limit owner/admin e falha de e-mail owner access.

Consequências:

- o comando não executa rollback automático.
- thresholds podem ser ajustados por execução.
- nenhuma métrica nova foi criada; o pacote reaproveita owner access metrics existentes.

## 2026-04-28 — Platform RBAC Production Closure Review

Decisão:

- encerrar a trilha RBAC production desta fase com um closure read-only que agrega ativação, monitoramento, riscos residuais e próximas trilhas.

Motivação:

- a trilha já possui readiness, evidence, monitoring e rollback manual; continuar refinando o mesmo gate teria retorno decrescente sem evidência real de produção.

Implementação:

- `accounts.application.ops_rbac_production_closure_queries` compõe production activation evidence e post-production monitoring.
- `ops_rbac_production_closure` classifica a trilha em `READY`, `WATCH` ou `BLOCKED`.

Consequências:

- RBAC `/ops/` fica tecnicamente fechado nesta fase.
- MFA/SSO, permission matrix persistida e exportação formal de evidências devem virar trilhas próprias.
- closure não executa deploy, rollback ou alteração de permissões.

## 2026-05-02 — Platform Audit Evidence Export Review

Decisão:

- criar exportação read-only de `AuditLog` por management command como primeiro mecanismo formal de evidência operacional.

Motivação:

- várias trilhas já produzem evidência em comandos, mas auditoria persistida precisava de saída controlada e anexável sem depender de consulta manual ao banco.

Implementação:

- `audit.application.audit_evidence_export_queries` exporta eventos tenant-scoped ou platform-scope explícitos.
- `export_audit_evidence` imprime `jsonl` ou `csv`, com filtros por módulo, ação e período.

Consequências:

- não há endpoint HTTP nem storage externo nesta fase.
- metadata só entra com opt-in.
- export cross-tenant agregado permanece fora de escopo para preservar isolamento multi-tenant.

## 2026-05-02 — Platform Audit Evidence Admin Surface Review

Decisão:

- expor uma ação read-only de exportação JSONL em `/ops/audit/export/`.

Motivação:

- operadores admin precisam anexar evidências do tenant sem depender exclusivamente de shell, mantendo o mesmo gate/permissão da listagem de auditoria.

Implementação:

- `AdminAuditEvidenceExportView` reutiliza `audit_evidence_export_queries`.
- a listagem `/ops/audit/` adiciona botão de exportação preservando filtros simples.

Consequências:

- export HTTP é tenant-scoped e não permite platform-scope.
- filtros avançados e storage externo continuam fora de escopo.

## 2026-05-02 — Platform Audit Evidence Closure Review

Decisão:

- encerrar a trilha de exportação de evidências auditáveis com closure read-only.

Motivação:

- export command e surface admin mínima já cobrem a necessidade inicial; continuar no mesmo eixo criaria funcionalidades de baixo ROI sem demanda operacional real.

Implementação:

- `audit.application.audit_evidence_closure_queries` valida uma amostra de exportação e lista decisões, riscos residuais e próximas trilhas.
- `audit_evidence_closure` imprime o fechamento para change log.

Consequências:

- `audit` fica dono formal do export de evidência.
- storage externo, assinatura, redaction avançado e filtros ricos ficam como escopos futuros.
- próxima trilha recomendada: Owner MFA/SSO.

## 2026-05-02 — Platform Owner MFA/SSO Review

Decisão:

- criar contrato/readiness read-only para MFA/SSO owner/admin sem alterar o fluxo atual de login.

Motivação:

- RBAC e auditoria já endureceram `/ops/`; o próximo risco de IAM é autenticação forte, mas implementar provider externo cedo demais aumentaria acoplamento.

Implementação:

- `accounts.application.owner_mfa_sso_readiness_queries` lê settings de contrato e emite blockers.
- `owner_mfa_sso_readiness` imprime modo atual, contratos, riscos residuais e próximas trilhas.

Consequências:

- password-only segue como baseline atual.
- MFA/enrollment, SSO adapter e break-glass ficam em trilhas próprias.
- nenhum comportamento de login muda nesta wave.

## 2026-05-02 — Owner MFA Enrollment Model Review

Decisão:

- criar `OwnerMfaFactor` como modelo tenant-scoped mínimo para enrollment MFA de owner/admin.

Motivação:

- antes de aplicar MFA no login, o sistema precisa representar fatores por owner com isolamento por tenant e readiness objetivo.

Implementação:

- `OwnerMfaFactor` pertence a `Tenant` e `OwnerUser`, com validação para impedir divergência de tenant.
- `owner_mfa_enrollment_readiness` lista owners ativos e bloqueia quando não há fator ativo/verificado.

Consequências:

- MFA ainda não é exigido no login.
- geração de segredo, challenge, recovery codes e provider externo ficam para trilhas futuras.
- modelo cria a base segura para enrollment auditável.

## 2026-05-02 — Owner MFA Enrollment Command Review

Decisão:

- criar command service auditável para registrar e desativar fatores MFA sem challenge real.

Motivação:

- o modelo de fator precisa ser operável e auditável antes de existir verificação/challenge.

Implementação:

- `owner_mfa_enrollment_commands.register_factor(...)` cria/reativa fator pendente.
- `owner_mfa_enrollment_commands.deactivate_factor(...)` desativa fator sem apagar histórico.
- eventos `owner.mfa_factor_registered` e `owner.mfa_factor_deactivated` são gravados em `AuditLog`.

Consequências:

- fatores registrados não contam como verified automaticamente.
- login continua sem enforcement MFA.

## 2026-05-02 — Owner MFA Enrollment Closure Review

Decisão:

- encerrar a abordagem de enrollment MFA com modelo, readiness e commands auditáveis prontos.

Motivação:

- o próximo risco já não é persistência/enrollment, mas challenge verification e UX/admin.

Consequências:

- próxima trilha recomendada: Owner MFA Challenge Verification Review.

## 2026-05-02 — Owner MFA Challenge Verification Review

Decisão:

- criar command service para verificar challenge TOTP de fator MFA owner/admin sem ainda aplicar MFA no login.

Motivação:

- fatores registrados como `pending/unverified` precisam de uma transição auditável para `verified` antes de qualquer enforcement real.

Implementação:

- `accounts.application.owner_mfa_challenge_commands.verify_factor(...)` valida TOTP interno, respeita `tenant_id` e exige `owners.manage`.
- `owner_mfa_factor verify` recebe `--challenge`, atualiza `is_verified`, `verified_at` e `last_challenged_at`.
- eventos `owner.mfa_factor_verified` e `owner.mfa_factor_verification_failed` são gravados em `AuditLog`.

Consequências:

- readiness de enrollment passa a conseguir considerar owners realmente enrolled quando há fator ativo/verificado.
- login owner/admin continua sem enforcement MFA.
- UI admin, recovery codes, vault/provider externo e break-glass seguem em trilhas próprias.

## 2026-05-02 — Owner MFA Admin Surface Review

Decisão:

- criar superfície `/ops/owners/mfa/` mínima para listar/verificar/desativar fatores MFA owner/admin.

Motivação:

- fatores MFA já tinham modelo, commands e challenge; faltava operação segura por tenant sem depender apenas de CLI.

Implementação:

- `owner_mfa_admin_queries` lista fatores por tenant.
- views em `accounts.interfaces.owner_views` adaptam requests e delegam verify/deactivate para command services auditáveis.

Consequências:

- actions sensíveis continuam auditadas.
- registro de fator via UI, QR code e enforcement no login continuam fora de escopo.

## 2026-05-02 — Owner Break-Glass Access Review

Decisão:

- criar readiness de break-glass por settings antes de qualquer enforcement MFA.

Motivação:

- enforcement de MFA sem conta de emergência operacional aumenta risco de lockout administrativo.

Implementação:

- `owner_mfa_break_glass_readiness` valida `OWNER_MFA_BREAK_GLASS_ENABLED` e `OWNER_MFA_BREAK_GLASS_OWNER_EMAILS` contra owners ativos do tenant.

Consequências:

- ainda não existe bypass real.
- readiness serve como evidência Go/No-Go para rollout futuro.

## 2026-05-02 — Owner MFA Login Enforcement Readiness Review

Decisão:

- criar readiness para enforcement MFA sem alterar o fluxo de login.

Motivação:

- antes de bloquear login, precisamos provar que owners ativos têm fator verificado e break-glass está pronto.

Implementação:

- `owner_mfa_login_enforcement_readiness` compõe `OWNER_MFA_REQUIRED`, enrollment MFA e break-glass.

Consequências:

- login permanece sem challenge MFA.
- blockers ficam explícitos antes da execução.

## 2026-05-02 — Owner MFA Operational Closure Review

Decisão:

- fechar o pacote operacional MFA owner/admin até o ponto anterior ao enforcement real.

Motivação:

- a abordagem já cobre modelo, enrollment, challenge, admin surface, break-glass e readiness; insistir sem mudar login teria ROI baixo.

Implementação:

- `owner_mfa_operational_closure` agrega decisões, blockers, riscos residuais e próximas trilhas.

Consequências:

- próxima trilha recomendada: Owner MFA Login Enforcement Execution Review.
- recovery codes e hardening de secret storage seguem independentes.

## 2026-05-03 — Owner MFA Login Enforcement Execution Review

Decisão:

- aplicar MFA no login owner/admin quando `OWNER_MFA_REQUIRED=True`, depois da senha e antes da sessão efetiva.

Motivação:

- modelo, enrollment, challenge, admin surface e readiness já existem; o próximo risco real é impedir sessão owner/admin sem segundo fator.

Implementação:

- `owner_login_commands.authenticate_owner(...)` cria `hubx_owner_mfa_pending` em vez de chamar `django_login` quando MFA está ativo.
- `/accounts/login/mfa/` chama `owner_login_commands.complete_mfa_challenge(...)`.
- challenge válido cria sessão owner/admin e registra `owner.login` + `owner.login_mfa_completed`.
- challenge inválido registra `owner.login_mfa_failed` e não cria sessão.

Rollback:

- definir `OWNER_MFA_REQUIRED=0`, redeploy/restart e validar login direto pós-senha.

Consequências:

- customer login não muda.
- owner sem fator ativo/verificado fica bloqueado quando enforcement está ativo.
- recovery codes e bypass break-glass real continuam em trilhas separadas.

## 2026-05-04 — Owner MFA Recovery Codes Review

Decisão:

- criar recovery codes reais para MFA owner/admin com persistência hash-only e uso único.

Motivação:

- enforcement MFA já bloqueia sessão owner/admin sem segundo fator; recovery codes reduzem risco de lockout sem criar bypass genérico.

Implementação:

- `OwnerMfaRecoveryCode` pertence a `Tenant` e `OwnerUser`.
- `owner_mfa_recovery_code_commands.generate_codes(...)` gera códigos, substitui não usados anteriores e persiste apenas hashes.
- `/accounts/login/mfa/` aceita recovery code válido como alternativa ao TOTP e marca `used_at`.
- readiness de enrollment só considera fator `recovery_code` quando há código não usado.

Consequências:

- códigos claros aparecem apenas na saída operacional de geração.
- recovery code usado não pode ser reutilizado.
- UI admin de regeneração e hardening de `secret_reference` ficam em trilhas futuras.

## 2026-05-04 — Owner MFA Secret Storage Hardening Review

Decisão:

- centralizar a resolução de `secret_reference` TOTP em um resolver explícito antes de introduzir vault/provider externo.

Motivação:

- o enforcement MFA já depende de segredo TOTP; ler `secret_reference` diretamente espalha contrato inseguro e dificulta migração para storage externo.

Implementação:

- `owner_mfa_secret_storage` classifica `plain:<secret>`, valor legado sem prefixo, `ref:<path>` e ausência.
- `owner_mfa_secret_storage_readiness` inventaria fatores TOTP ativos por tenant.
- `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` permite bloquear segredo local sem mudar dados.
- login MFA e command de challenge passam pelo resolver.

Consequências:

- fatores legados continuam funcionando enquanto local plain estiver permitido.
- referências externas ficam bloqueadas até existir adapter/provider.
- próxima trilha recomendada: Owner MFA External Secret Provider Adapter Review.

## 2026-05-05 — Owner MFA External Secret Provider Adapter Review

Decisão:

- criar adapter mínimo de provider externo para resolver `ref:<path>` via variáveis de ambiente.

Motivação:

- o resolver já separava local plain de referência externa, mas `ref:<path>` ainda era sempre bloqueado; um provider inicial permite validar o contrato sem introduzir vault/KMS cedo demais.

Implementação:

- `accounts.infrastructure.owner_mfa_secret_providers` resolve provider `env`.
- `OWNER_MFA_SECRET_PROVIDER=env` ativa lookup por variável.
- `OWNER_MFA_SECRET_ENV_PREFIX` define prefixo de variável.
- `owner_mfa_secret_storage` delega `ref:<path>` ao registry.
- readiness e login MFA passam a aceitar referência resolvida sem imprimir segredo.

Consequências:

- provider ausente ou env sem valor segue bloqueado.
- vault/KMS real fica como evolução posterior.
- próxima trilha recomendada: Owner MFA TOTP Secret Migration Plan.

## 2026-05-05 — Owner MFA TOTP Secret Migration Plan

Decisão:

- criar plano operacional para migrar fatores TOTP locais/legados para `ref:<path>` sem executar a alteração automaticamente.

Motivação:

- o provider externo mínimo já resolve referências; antes de trocar dados sensíveis, precisamos listar candidatos, referência alvo, blockers, runbook e rollback.

Implementação:

- `owner_mfa_totp_secret_migration_plan_queries` classifica fatores TOTP ativos.
- `owner_mfa_totp_secret_migration_plan` imprime candidatos, `target_ref`, runbook e rollback.
- fatores locais viram candidatos `migrate-local-to-ref`.
- fatores externos resolvidos ficam `already-external`.
- segredo ausente ou referência externa não resolvida bloqueia o plano.

Consequências:

- nenhuma escrita em `OwnerMfaFactor` acontece nesta trilha.
- execução da migração fica para trilha separada com evidência de provider.
- próxima trilha recomendada: Owner MFA TOTP Secret Migration Execution Review.

## 2026-05-05 — Owner MFA TOTP Secret Migration Execution Review

Decisão:

- permitir a troca controlada de `OwnerMfaFactor.secret_reference` de segredo local para `ref:<path>` somente quando o provider externo já resolver o alvo com valor equivalente.

Motivação:

- o plano já lista candidatos e `target_ref`; a execução precisa ser segura, auditável e reversível, sem transformar o app em copiador de segredo ou expor valor sensível em saída operacional.

Implementação:

- `owner_mfa_totp_secret_migration_commands` valida tenant, fator TOTP ativo, storage local/plain, provider externo e equivalência de segredo.
- `owner_mfa_totp_secret_migration_execute` roda em dry-run por padrão e exige `--execute` para gravar.
- a escrita troca apenas `secret_reference` para `ref:<target_ref>`.
- `AuditLog` registra `owner.mfa_totp_secret_migrated` com metadata não sensível.

Consequências:

- copiar/publicar o segredo no provider continua tarefa externa ao app.
- divergência entre segredo local e provider bloqueia a migração.
- próxima trilha recomendada: Owner MFA Local Secret Retirement Review.

## 2026-05-05 — Owner MFA Local Secret Retirement Review

Decisão:

- criar readiness específico para decidir quando o fallback local/plain de TOTP owner/admin pode ser desligado por ambiente.

Motivação:

- depois da migração para `ref:<path>`, desligar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` reduz superfície sensível, mas só é seguro quando não resta fator local e o provider externo resolve todos os fatores ativos.

Implementação:

- `owner_mfa_local_secret_retirement_queries` compõe o readiness de storage e adiciona blockers de retirement.
- `owner_mfa_local_secret_retirement_readiness` emite Go/No-Go, contagens, runbook e rollback.
- nenhum setting/env é alterado pelo comando.

Consequências:

- ativação real continua fora do app e deve ser feita por ambiente.
- fatores locais restantes bloqueiam a aposentadoria.
- próxima trilha recomendada: Owner MFA Local Secret Retirement Execution Review.

## 2026-05-05 — Owner MFA Local Secret Retirement Execution Review

Decisão:

- modelar a ativação de `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False` como evidência operacional before/after, não como mutação automática de ambiente pelo app.

Motivação:

- desligar o fallback local depende de deploy/env/restart fora do processo Django; o sistema deve provar readiness e pós-condição, mas não deve editar configuração operacional por conta própria.

Implementação:

- `owner_mfa_local_secret_retirement_execution_queries` compõe readiness e valida fase `before` ou `after`.
- `owner_mfa_local_secret_retirement_execution` captura contagens, setting atual, evidências esperadas e rollback.
- fase `after` bloqueia enquanto `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` ainda estiver habilitado.

Consequências:

- a troca real do setting permanece responsabilidade do operador/deploy.
- regressão para fator local/plain bloqueia o after.
- próxima trilha recomendada: Owner MFA Provider Health Monitoring Review.

## 2026-05-05 — Owner MFA Provider Health Monitoring Review

Decisão:

- criar snapshot operacional read-only para acompanhar a saúde do provider externo de segredos TOTP owner/admin por tenant.

Motivação:

- depois que o fallback local é aposentado, provider externo indisponível vira risco direto de login MFA; precisamos detectar referência quebrada antes de depender só de erro no login.

Implementação:

- `owner_mfa_provider_health_queries` compõe storage readiness e classifica status `HEALTHY`, `WATCH` ou `CRITICAL`.
- `owner_mfa_provider_health` imprime contagens, sinais, blockers e runbook sem expor segredo.
- sinais incluem provider ausente, referência externa não resolvida, segredo ausente, fallback local e ausência de fatores externos.

Consequências:

- monitoramento ainda é comando/readiness, sem endpoint Prometheus nesta etapa.
- nenhum retry/fallback automático é acionado.
- próxima trilha recomendada: Owner MFA Provider Health Metrics Review.

## 2026-05-05 — Owner MFA Provider Health Metrics Review

Decisão:

- expor health do provider externo TOTP MFA em endpoint Prometheus separado, protegido pelo token de observabilidade de accounts.

Motivação:

- o snapshot via management command é útil para triagem, mas produção precisa de scrape e alertas para detectar provider crítico antes de falhas recorrentes de login owner/admin.

Implementação:

- `owner_mfa_provider_health_metrics_queries` exporta métricas por tenant com labels de baixa cardinalidade.
- `/accounts/metrics/owner-mfa-provider-health/` reutiliza `ACCOUNTS_OBSERVABILITY_TOKEN`.
- scrape example e alert rules de accounts incluem provider crítico, referência externa não resolvida e fallback local/plain restante.

Consequências:

- métricas não incluem owner, factor, segredo nem reference path completo.
- endpoint não depende de `/ops/`.
- próxima trilha recomendada: Owner MFA Provider Health Dashboard Review.

## 2026-05-05 — Owner MFA Provider Health Dashboard Review

Decisão:

- criar dashboard Grafana mínimo para acompanhar provider/status/storage de TOTP MFA owner/admin usando as métricas Prometheus já expostas.

Motivação:

- alertas cobrem incidentes, mas operação precisa de visão rápida de tenants críticos, referências não resolvidas, fallback local restante e sinais ativos após o corte do storage local.

Implementação:

- `accounts-owner-mfa-provider-health-dashboard.json` usa datasource parametrizado `DS_PROMETHEUS`.
- painéis usam apenas métricas tenant/provider/status/state/storage/signal.
- README de observabilidade documenta importação e pré-validações.

Consequências:

- dashboard evita drill-down por owner/factor para manter cardinalidade baixa.
- provisionamento automático do Grafana fica fora desta wave.
- próxima trilha recomendada: Owner MFA Provider Health Closure Review.

## 2026-05-05 — Owner MFA Provider Health Closure Review

Decisão:

- fechar a trilha de provider health MFA com um closure read-only que agrega health atual, artefatos Prometheus/Grafana e riscos residuais.

Motivação:

- a trilha já possui storage resolver, migração, retirement, health, métricas, alertas e dashboard; antes de seguir para novas frentes, precisamos distinguir o que está pronto do que ainda depende de ativação real de ambiente.

Implementação:

- `owner_mfa_provider_health_closure_queries` compõe `owner_mfa_provider_health` e verifica presença dos artefatos de observabilidade.
- `owner_mfa_provider_health_closure` imprime decisões, artifacts, blockers, riscos residuais e próximas trilhas.
- health `CRITICAL` bloqueia o closure; health `WATCH` mantém acompanhamento sem blocker.

Consequências:

- ativar Prometheus/Grafana real permanece tarefa operacional externa.
- remoção de código/tolerância local fica para trilha dedicada.
- próxima trilha recomendada: Owner MFA Local Secret Code Retirement Review.

## 2026-05-05 — Owner MFA Local Secret Code Retirement Review

Decisão:

- criar uma readiness específica antes de remover tolerância de código para `plain:`/legado em TOTP MFA owner/admin.

Motivação:

- remover suporte local melhora postura de segurança, mas reduz rollback rápido se o provider externo falhar; a remoção só deve ser autorizada quando o setting já estiver desligado, não houver fatores locais e o provider health estiver fechado.

Implementação:

- `owner_mfa_local_secret_code_retirement_queries` compõe evidência `after` da aposentadoria local e closure de provider health.
- `owner_mfa_local_secret_code_retirement_readiness` lista decisões, blockers, superfícies de código, riscos residuais e próxima execution.
- a wave não remove `LOCAL_PREFIX`, `can_accept_local_plain` nem testes legados.

Consequências:

- a remoção real fica para execution review separada.
- rollback operacional permanece possível por enquanto.
- próxima trilha recomendada: Owner MFA Local Secret Code Retirement Execution Review.

## 2026-05-05 — Owner MFA Local Secret Code Retirement Execution Review

Decisão:

- endurecer o default de `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` para desligado, preservando rollback explícito por variável de ambiente.

Motivação:

- a readiness indicou que a postura segura deve ser não aceitar segredo local/plain por padrão; manter default ligado prolonga risco de dados sensíveis locais e torna produção dependente de opt-out.

Implementação:

- `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` agora usa default `"0"`.
- `owner_mfa_local_secret_code_retirement_execution_queries` captura evidência do default desligado e da readiness tenant-scoped.
- testes que precisam de fallback local agora usam `override_settings(OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True)`.
- rollback documentado: definir `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1` e reiniciar o ambiente.

Consequências:

- ambientes sem env explícito deixam de aceitar TOTP local/plain no challenge/login.
- parsing `plain:`/legado ainda existe para inventário, migração e rollback controlado.
- próxima trilha recomendada: Owner MFA Legacy Data Global Sweep Review.

## 2026-05-05 — Owner MFA Legacy Data Global Sweep Review

Decisão:

- criar sweep global read-only para confirmar se ainda existem fatores TOTP MFA owner/admin em storage local/plain, ausente ou com referência externa não resolvida.

Motivação:

- depois de desligar o default local, remover o parser `plain:`/legado só é seguro se o banco real não possui dependência residual por tenant.

Implementação:

- `owner_mfa_legacy_data_global_sweep_queries` lista tenants com TOTP ativo e compõe readiness de storage por tenant.
- `owner_mfa_legacy_data_global_sweep` imprime totais e blockers por tenant sem segredo ou reference path.
- status `ready`, `watch` ou `blocked` orienta parser removal vs cleanup.

Consequências:

- sweep não cobre backups/dumps/fixtures externos ao banco atual.
- parser local ainda permanece até uma review dedicada.
- próxima trilha recomendada: Owner MFA Local Secret Parser Removal Review.

## 2026-05-05 — Owner MFA Local Secret Parser Removal Review

Decisão:

- criar uma review Go/No-Go antes de remover o parser `plain:`/legado do resolver TOTP MFA owner/admin.

Motivação:

- após desligar o default local e varrer dados legados, a remoção do parser muda o rollback: env sozinho deixa de resolver; rollback passa a exigir revert de deploy.

Implementação:

- `owner_mfa_local_secret_parser_removal_queries` compõe sweep global, setting local e plano de remoção.
- `owner_mfa_local_secret_parser_removal_review` imprime decisões, superfícies, blockers, plano e rollback.
- a wave permanece review-only e não altera o resolver.

Consequências:

- execution posterior só deve seguir com sweep global ready e env local desligado.
- rollback pós-removal será por revert de código/deploy.
- próxima trilha recomendada: Owner MFA Local Secret Parser Removal Execution Review.

## 2026-05-05 — Owner MFA Local Secret Parser Removal Execution Review

Decisão:

- remover a capacidade efetiva de parsing local/plain no resolver TOTP MFA owner/admin, reclassificando `plain:` e valores legados sem `ref:` como `unsupported-local`.

Motivação:

- depois do default local desligado, sweep global e review Go/No-Go, manter o parser capaz de devolver segredo local prolongava uma superfície sensível que já não deve existir em produção real.

Implementação:

- `OwnerMfaSecretStorageResolver.resolve` só retorna segredo para `ref:<path>` resolvido por provider externo.
- valores `plain:` e legados retornam `owner-mfa-secret-local-unsupported`, `ready=False` e `secret=""`.
- readiness e migration plan agora classificam resíduos locais com blocker `local-secret-unsupported`.
- `owner_mfa_local_secret_parser_removal_execution_queries` e `owner_mfa_local_secret_parser_removal_execute` capturam evidência por probes sem expor segredo.

Consequências:

- rollback por `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1` não reativa mais o parser local; rollback passa a exigir revert/deploy.
- fatores locais residuais deixam de ser migráveis pelo app e precisam de cleanup/restauração por trilha operacional controlada.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Review.

## 2026-05-07 — Owner MFA Vault/KMS Provider Review

Decisão:

- tratar `env` como provider transitório e formalizar um contrato de provider Vault/KMS para segredos TOTP MFA owner/admin antes de implementar adapter real.

Motivação:

- depois da remoção do parser local/plain, a próxima superfície crítica é tirar secret material de variáveis de ambiente e preparar um storage operacional com health, rollback e observabilidade previsíveis.

Implementação:

- `owner_mfa_vault_kms_provider_review_queries` compõe provider health closure, parser removal execution e target provider suportado.
- `owner_mfa_vault_kms_provider_review` emite decisões, blockers, adapter contract, rollout plan e rollback sem segredo.
- targets iniciais: HashiCorp Vault, AWS Secrets Manager, AWS KMS, GCP Secret Manager e Azure Key Vault.

Consequências:

- esta wave não chama provider externo real nem muda settings.
- status `ready` significa pronto para desenhar/implementar adapter skeleton, não produção ativada.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Adapter Contract Review.

## 2026-05-11 — Owner MFA Vault/KMS Provider Adapter Contract Review

Decisão:

- formalizar o contrato técnico do adapter Vault/KMS antes de implementar qualquer SDK/vendor real para segredos TOTP MFA owner/admin.

Motivação:

- o provider `env` é transitório; a troca para cofre/KMS precisa preservar falha segura no login, evitar exposição de segredo e impedir fallback silencioso para storage fraco.

Implementação:

- `owner_mfa_vault_kms_provider_adapter_contract_queries` compõe a review Vault/KMS anterior e emite settings, interface, erros recuperáveis, controles de segurança, testes e rollback.
- `owner_mfa_vault_kms_provider_adapter_contract` imprime o contrato sem segredo e sem chamar provider externo.
- primeira versão do adapter fica limitada a read-path-only, sem escrita, migração ou cache de segredo.

Consequências:

- skeleton futuro deve viver em `accounts.infrastructure.owner_mfa_secret_providers`.
- falhas de Vault/KMS devem retornar `ready=False` com result explícito, não exception que derrube login.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Adapter Skeleton Execution.

## 2026-05-11 — Owner MFA Vault/KMS Provider Adapter Skeleton Execution

Decisão:

- implementar um skeleton read-only para providers Vault/KMS aprovados, atrás de `OWNER_MFA_SECRET_PROVIDER`, sem SDK/vendor real obrigatório nesta etapa.

Motivação:

- precisamos provar a fronteira do resolver, os modos de falha e a evidência operacional antes de acoplar um cofre real; isso reduz risco de quebrar login owner/admin por timeout, permissão ou referência inválida.

Implementação:

- `owner_mfa_secret_providers` reconhece `hashicorp-vault`, `aws-secrets-manager`, `aws-kms`, `gcp-secret-manager` e `azure-key-vault`.
- o skeleton usa settings controlados para status e refs de teste, aplica namespace opcional e valida referências inválidas.
- `owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries` e o comando correspondente capturam probe, decisões, blockers e rollback sem imprimir o segredo.

Consequências:

- não há chamada real a Vault/KMS ainda.
- não existe fallback automático para `env` quando o skeleton falha.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Readiness Evidence Review.

## 2026-05-11 — Owner MFA Vault/KMS Provider Readiness Evidence Review

Decisão:

- criar um pacote de evidência tenant-scoped para provar readiness do skeleton Vault/KMS antes de qualquer canário staging.

Motivação:

- o skeleton já prova o caminho read-only, mas a decisão de seguir para staging precisa reunir health closure, provider observado, probe e rollback num artefato operacional simples e sem segredo.

Implementação:

- `owner_mfa_vault_kms_provider_readiness_evidence_queries` compõe skeleton execution e provider health closure.
- `owner_mfa_vault_kms_provider_readiness_evidence` imprime decisions, evidence pack, blockers, rollback e next tracks sem secret material.
- readiness bloqueia mismatch entre target provider e provider observado no health.

Consequências:

- ainda não há ativação staging real nem SDK/vendor real.
- a próxima etapa pode focar em canário staging com checklist manual e rollback.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Staging Canary Review.

## 2026-05-11 — Owner MFA Vault/KMS Provider Staging Canary Review

Decisão:

- criar uma review/checklist de canário staging para validar manualmente login/challenge MFA owner/admin usando o provider Vault/KMS target.

Motivação:

- readiness evidence prova sinais técnicos, mas staging exige um roteiro seguro de teste manual com owner canário, critérios de sucesso e rollback antes de qualquer execução real.

Implementação:

- `owner_mfa_vault_kms_provider_staging_canary_queries` compõe readiness evidence, exige `canary_owner_email` e emite preflight, checklist, success signals e rollback.
- `owner_mfa_vault_kms_provider_staging_canary_review` imprime o pacote sem segredo/código TOTP.

Consequências:

- esta wave não autentica owner nem cria sessão.
- a execução real do canário fica para trilha separada de evidência.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Staging Canary Evidence Execution.

## 2026-05-11 — Owner MFA Vault/KMS Provider Staging Canary Evidence Execution

Decisão:

- capturar a execução do canário staging como evidência declarativa via flags, sem automatizar browser/login nem gravar estado operacional.

Motivação:

- a validação manual de MFA envolve senha, TOTP e sessão; automatizar isso cedo demais aumenta risco. Nesta etapa basta consolidar resultados, blockers e rollback sem coletar segredo ou código.

Implementação:

- `owner_mfa_vault_kms_provider_staging_canary_evidence_queries` compõe a review do canário e valida flags de resultado manual.
- `owner_mfa_vault_kms_provider_staging_canary_evidence` imprime decisions, evidence pack, blockers, rollback e próximos tracks.

Consequências:

- a trilha está pronta para revisar adapter real com SDK/vendor.
- evidência formal assinada/exportável continua fora desta wave.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Real Adapter Contract Review.

## 2026-05-11 — Owner MFA Vault/KMS Provider Real Adapter Contract Review

Decisão:

- formalizar o contrato do adapter real Vault/KMS pós-canário antes de introduzir SDK/vendor ou credenciais reais.

Motivação:

- o skeleton validou a fronteira e o canário validou o fluxo operacional; a próxima mudança de risco é acoplar SDK/infra real, então o contrato precisa fixar credenciais, timeouts, erros, testes e rollback antes de código externo.

Implementação:

- `owner_mfa_vault_kms_provider_real_adapter_contract_queries` compõe canary evidence e exige confirmações de SDK, credenciais, timeouts e owner de rollout.
- `owner_mfa_vault_kms_provider_real_adapter_contract` imprime contrato real, settings, erros, testes, plano e rollback sem secret material.

Consequências:

- `aws-kms` permanece fora dos targets reais por ora, por não ser secret store direto no mesmo contrato.
- ainda não há SDK/vendor instalado nem chamada real ao provider.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution.

## 2026-05-11 — Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution

Decisão:

- implementar um branch real/mocável separado para providers Vault/KMS, habilitado por setting, mantendo o skeleton configurável anterior como trilha de teste/rollback.

Motivação:

- antes de instalar SDK/vendor, precisamos provar que o registry consegue separar modo skeleton e modo real-adapter, mapear erros recuperáveis e manter saída sem segredo.

Implementação:

- `owner_mfa_secret_providers` passa a usar `OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED` para rotear ao branch real/mocável.
- `owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries` compõe contrato real e prova probe pelo branch real.
- comando de execution imprime decisões, blockers e rollback sem secret material.

Consequências:

- ainda não há SDK/vendor real nem credenciais reais.
- o próximo risco controlado é escolher/isolar a dependência SDK.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider SDK Dependency Review.

## 2026-05-11 — Owner MFA Vault/KMS Provider SDK Dependency Review

Decisão:

- formalizar a dependência SDK/vendor por provider Vault/KMS antes de instalar pacote ou chamar serviço externo real.

Motivação:

- o branch real/mocável já prova a fronteira técnica; a próxima fonte de risco é acoplar bibliotecas externas no caminho de login/challenge sem pinning, licença, import opcional e rollback definidos.

Implementação:

- `owner_mfa_vault_kms_provider_sdk_dependency_review_queries` compõe o skeleton real e emite contrato de pacotes/imports por provider.
- `owner_mfa_vault_kms_provider_sdk_dependency_review` exige confirmações de pinning, import opcional, rollback de deploy e licença.
- a saída inclui contratos de falha/teste/rollback sem imprimir segredo.

Consequências:

- nenhum SDK foi instalado nesta etapa.
- imports reais devem permanecer lazy/opcionais dentro de `accounts.infrastructure`.
- `aws-kms` continua fora do contrato como secret store direto.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider SDK Adapter Execution.

## 2026-05-11 — Owner MFA Vault/KMS Provider SDK Adapter Execution

Decisão:

- adicionar um branch SDK lazy ao registry de secrets MFA, habilitado por flag própria e seguro quando a dependência não estiver instalada.

Motivação:

- depois do contrato de dependência, o risco imediato é provar que o código suporta import opcional e rollback sem quebrar startup/login. A chamada externa real ainda deve ser isolada numa review de endpoint por provider.

Implementação:

- `owner_mfa_secret_providers` passa a rotear para SDK adapter quando `OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED` e `OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED` estão ativos.
- o branch SDK importa módulos por provider dentro do resolver e mapeia `ImportError` para `owner-mfa-secret-provider-vault-unavailable`.
- `owner_mfa_vault_kms_provider_sdk_adapter_execution_queries` compõe dependency review e captura probe/decisions/blockers sem segredo.
- `owner_mfa_vault_kms_provider_sdk_adapter_execute` emite evidência operacional do branch SDK.

Consequências:

- ainda não há chamada externa real ao Vault/KMS nem credenciais reais.
- o branch SDK pode ser desligado por `OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED=False`.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Real Endpoint Review.

## 2026-05-11 — Owner MFA Vault/KMS Provider Real Endpoint Review

Decisão:

- escolher Hashicorp Vault como primeiro endpoint real para segredos TOTP MFA owner/admin e exigir contrato explícito antes da implementação `hvac`.

Motivação:

- implementar todos os vendors ao mesmo tempo aumentaria risco e acoplamento. Hashicorp Vault é o alvo mais direto após a dependency review, então a execução real deve começar por ele com URL, auth, path, timeout e rollback definidos.

Implementação:

- `owner_mfa_vault_kms_provider_real_endpoint_review_queries` compõe SDK adapter execution e bloqueia targets diferentes de `hashicorp-vault`.
- `owner_mfa_vault_kms_provider_real_endpoint_review` exige confirmações de endpoint, auth, path/campo, timeout e rollback.
- a saída define settings `OWNER_MFA_HASHICORP_VAULT_*`, contratos de falha/teste e redaction sem segredo.

Consequências:

- ainda não há chamada real via `hvac`.
- token/AppRole e path completo continuam fora de stdout/log/evidence.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Real Endpoint Execution.

## 2026-05-11 — Owner MFA Hashicorp Vault Real Endpoint Execution

Decisão:

- implementar a primeira chamada real de segredo MFA TOTP via Hashicorp Vault usando `hvac`, mantendo import lazy, flag explícita e redaction operacional.

Motivação:

- a review de endpoint já fixou o contrato de URL, auth, mount, field, timeout e rollback. O próximo risco controlado é provar a integração real com client mockável e mapeamento de falhas sem alterar fatores ou login.

Implementação:

- `owner_mfa_secret_providers` passa a rotear para Hashicorp Vault real quando `OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED=True`.
- o adapter importa `hvac` dentro do resolver, monta client por token ou AppRole e lê KV v2 com `mount_point`, `path` e field configuráveis.
- `owner_mfa_hashicorp_vault_real_endpoint_execution_queries` compõe a endpoint review e captura probe/decisions/blockers sem segredo, token ou path completo.
- `owner_mfa_hashicorp_vault_real_endpoint_execute` emite evidência operacional do endpoint.

Consequências:

- `hvac` continua dependência opcional; ausência mapeia para unavailable.
- produção segue bloqueada até smoke/evidência de staging.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Staging Smoke Evidence.

## 2026-05-12 — Owner MFA Hashicorp Vault Staging Smoke Evidence

Decisão:

- capturar o smoke staging do endpoint Hashicorp Vault como evidência declarativa, sem automatizar login/challenge nem alterar fatores MFA.

Motivação:

- a chamada real via `hvac` já existe e precisa de uma etapa operacional segura antes de readiness de produção. O smoke staging deve provar probe, negative path, redaction, rollback e health sem coletar segredo ou token.

Implementação:

- `owner_mfa_hashicorp_vault_staging_smoke_evidence_queries` compõe a execution real e exige confirmations manuais de staging.
- `owner_mfa_hashicorp_vault_staging_smoke_evidence` imprime evidence pack, decisions, blockers e rollback sem secret material.

Consequências:

- produção continua bloqueada até uma readiness review consolidada.
- evidência formal assinada/exportável continua fora desta wave.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Production Readiness Review.

## 2026-05-12 — Owner MFA Vault/KMS Provider Production Readiness Review

Decisão:

- consolidar a cadeia Hashicorp Vault em um Go/No-Go de produção sem ativar flags, executar deploy ou alterar fatores MFA.

Motivação:

- smoke staging e health closure provam partes diferentes do risco. Antes de produção, a decisão precisa agregar evidência técnica, observabilidade, runbook, rollback owner, janela de mudança e rotação de credenciais.

Implementação:

- `owner_mfa_vault_kms_provider_production_readiness_queries` compõe staging smoke e provider health closure.
- `owner_mfa_vault_kms_provider_production_readiness` imprime decisão `GO`/`NO-GO`, confirmations, decisions, runbook, rollback e blockers sem secret material.

Consequências:

- produção só é considerada permitida quando `go_no_go.decision=GO`.
- a ativação operacional por tenant continua em gate separado.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Production Gate Review.

## 2026-05-12 — Owner MFA Hashicorp Vault Production Gate Review

Decisão:

- transformar o Go técnico do provider Hashicorp Vault em gate operacional de ativação por tenant, sem alterar flags/env nem executar deploy.

Motivação:

- readiness técnica indica que produção pode seguir, mas ativação real ainda precisa controlar escopo, ordem de rollout, flags, plantão, rollback window e monitoramento pós-ativação.

Implementação:

- `owner_mfa_hashicorp_vault_production_gate_queries` compõe production readiness e exige confirmations operacionais.
- `owner_mfa_hashicorp_vault_production_gate` imprime decisão `GO`/`NO-GO`, activation plan, rollback, blockers e próximos tracks sem secret material.

Consequências:

- o sistema possui gate operacional pronto, mas ainda não há ativação real.
- próxima trilha recomendada: Owner MFA Vault/KMS Provider Production Activation Evidence.

## 2026-05-12 — Owner MFA Vault/KMS Provider Production Activation Evidence

Decisão:

- capturar a ativação production do provider Vault/KMS como evidência declarativa pós-gate, sem executar deploy/restart, alterar flags ou chamar rollback.

Motivação:

- o gate operacional define quando a ativação pode acontecer; a etapa seguinte precisa registrar se o deploy, flags, probe, login/challenge, health e redaction realmente ficaram bons após a mudança.

Implementação:

- `owner_mfa_vault_kms_provider_production_activation_evidence_queries` compõe o production gate e exige confirmations pós-ativação.
- `owner_mfa_vault_kms_provider_production_activation_evidence` imprime evidence pack, decisions, rollback e blockers sem secret material.

Consequências:

- a ativação continua sendo uma ação externa ao comando.
- o próximo risco é monitoramento pós-ativação e classificação rollback/watch/healthy.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Post-Activation Monitoring Review.

## 2026-05-12 — Owner MFA Hashicorp Vault Post-Activation Monitoring Review

Decisão:

- classificar a janela pós-ativação Hashicorp Vault como `HEALTHY`, `WATCH`, `ROLLBACK` ou `BLOCKED`, sem executar rollback ou expansão automaticamente.

Motivação:

- activation evidence registra que a mudança foi aplicada; ainda é preciso observar sinais de estabilidade antes de encerrar a trilha ou expandir para outros tenants.

Implementação:

- `owner_mfa_hashicorp_vault_post_activation_monitoring_queries` compõe activation evidence e classifica sinais declarados.
- `owner_mfa_hashicorp_vault_post_activation_monitoring` imprime sinais, decisões, watch items, rollback guidance e próximos tracks sem secret material.

Consequências:

- `HEALTHY` libera closure/expansão futura.
- `WATCH` segura expansão e exige nova evidência.
- `ROLLBACK` orienta rollback operacional externo.
- próxima trilha recomendada: Owner MFA Vault/KMS Production Closure Review.

## 2026-05-12 — Owner MFA Vault/KMS Production Closure Review

Decisão:

- encerrar a trilha production do provider Vault/KMS MFA owner/admin somente quando o monitoring Hashicorp Vault estiver `HEALTHY` e os critérios finais de rollback, riscos residuais e expansão estiverem confirmados.

Motivação:

- post-activation monitoring prova estabilidade da janela, mas closure precisa separar encerramento do tenant canário de expansão para novos tenants.

Implementação:

- `owner_mfa_vault_kms_production_closure_queries` compõe o monitoring e adiciona sinais finais de closure.
- `owner_mfa_vault_kms_production_closure` imprime decisions, blockers, residual risks, expansion guardrails e próximos tracks sem secret material.

Consequências:

- `READY` encerra a trilha production do tenant canário.
- expansão para novos tenants permanece uma trilha separada com evidência própria.
- rollback e flags/env seguem ações operacionais externas ao command.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Tenant Expansion Review.

## 2026-05-12 — Owner MFA Hashicorp Vault Tenant Expansion Review

Decisão:

- tratar expansão Hashicorp Vault MFA owner/admin como review tenant-by-tenant, dependente de closure `READY` do canário e sem rollout automático.

Motivação:

- o tenant canário prova estabilidade inicial, mas cada tenant precisa de evidência própria para evitar autorização global implícita.

Implementação:

- `owner_mfa_hashicorp_vault_tenant_expansion_queries` compõe production closure e valida tenants-alvo, janela, evidência por tenant, suporte, rollback e limite de um tenant por janela.
- `owner_mfa_hashicorp_vault_tenant_expansion_review` imprime targets, decisões, blockers, runbook e evidence requirements sem secret material.

Consequências:

- expansão paralela fica bloqueada nesta fase.
- tenants inativos, em maintenance mode, inexistentes ou iguais ao canário bloqueiam a review.
- ativação real permanece externa ao command.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution.

## 2026-05-12 — Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution

Decisão:

- capturar a expansão Hashicorp Vault para um tenant-alvo como evidence pack declarativo, dependente de review `READY` e sem automatizar rollout.

Motivação:

- a expansão precisa produzir evidência própria por tenant antes de liberar o próximo alvo, mantendo isolamento multi-tenant e rollback claro.

Implementação:

- `owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries` compõe a review e exige confirmations do target para flags, activation evidence, monitoring, login/challenge, provider health, rollback e redaction.
- `owner_mfa_hashicorp_vault_tenant_expansion_evidence` imprime evidence pack, confirmations, decisions, rollback e blockers sem secret material.

Consequências:

- cada tenant expandido precisa de evidence pack próprio.
- falha no target recomenda rollback limitado ao tenant-alvo e interrupção da expansão.
- próximo tenant só deve ser considerado após monitoring do target atual.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review.

## 2026-05-12 — Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review

Decisão:

- classificar o tenant-alvo recém-expandido como `HEALTHY`, `WATCH`, `ROLLBACK` ou `BLOCKED` antes de considerar qualquer próximo tenant.

Motivação:

- expansion evidence confirma a execução, mas a cadência segura exige observação própria do target para evitar propagar falha em cadeia.

Implementação:

- `owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries` compõe expansion evidence e classifica sinais declarados do target.
- `owner_mfa_hashicorp_vault_target_post_expansion_monitoring` imprime sinais, decisões, watch items, rollback guidance e próximos tracks sem secret material.

Consequências:

- `HEALTHY` permite apenas considerar uma nova review para próximo tenant.
- `WATCH` bloqueia próxima expansão até nova evidência.
- `ROLLBACK` recomenda rollback limitado ao tenant-alvo.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Next Tenant Expansion Review.

## 2026-05-12 — Owner MFA Hashicorp Vault Next Tenant Expansion Review

Decisão:

- separar a decisão de cadência da execução de expansão: o sistema pode classificar `READY`, `PAUSED` ou `BLOCKED`, mas não ativa o próximo tenant automaticamente.

Motivação:

- mesmo com o target atual `HEALTHY`, a próxima expansão precisa validar janela, capacidade operacional, evidence arquivada e tenant-alvo explícito.

Implementação:

- `owner_mfa_hashicorp_vault_next_tenant_expansion_queries` compõe target monitoring e valida próximos tenants e sinais de cadência.
- `owner_mfa_hashicorp_vault_next_tenant_expansion_review` imprime targets, cadence signals, decisions, blockers, runbook e próximos tracks sem secret material.

Consequências:

- `READY` apenas retorna para `Tenant Expansion Review` do próximo ciclo.
- `PAUSED` encerra a cadência sem blocker.
- `BLOCKED` exige resolver monitoring/cadência/target antes de prosseguir.
- próxima trilha recomendada: Owner MFA Hashicorp Vault Expansion Cadence Closure Review.

## 2026-05-12 — Owner MFA Hashicorp Vault Expansion Cadence Closure Review

Decisão:

- encerrar ou consolidar a cadência Hashicorp Vault somente após next tenant review `READY` ou `PAUSED` e sinais finais de closure completos.

Motivação:

- a cadência de expansão precisa de um ponto de fechamento auditável antes de seguir para rotação, export de evidência ou novo ciclo operacional.

Implementação:

- `owner_mfa_hashicorp_vault_expansion_cadence_closure_queries` compõe next tenant review e exige decisão registrada, archive de evidências, riscos revisados, rotation runbook e audit evidence pronta.
- `owner_mfa_hashicorp_vault_expansion_cadence_closure` imprime closure signals, decisions, blockers, residual risks, runbook e próximos tracks sem secret material.

Consequências:

- closure não ativa próximo tenant nem exporta evidência formal.
- cadência `PAUSED` pode fechar sem blockers.
- cadência `READY` retorna para novo ciclo apenas via review/evidence/monitoring próprios.
- próxima trilha recomendada: Owner MFA Vault/KMS Rotation Runbook Review.

## 2026-05-12 — Owner MFA Vault/KMS Rotation Runbook Review

Decisão:

- formalizar rotação Vault/KMS como runbook verificável após closure da cadência, sem executar geração de credencial, atualização de secret/config ou rollback.

Motivação:

- a operação contínua do provider Hashicorp Vault depende de rotação segura de token/AppRole/segredos, com escopo, owner, rollback e redaction explícitos antes de qualquer execução real.

Implementação:

- `owner_mfa_vault_kms_rotation_runbook_queries` compõe expansion cadence closure e valida sinais operacionais da rotação.
- `owner_mfa_vault_kms_rotation_runbook` imprime runbook signals, decisions, blockers, rotation steps, rollback steps e próximos tracks sem secret material.

Consequências:

- rotação real permanece fora do command.
- qualquer evidence futura precisa confirmar execução sem expor token, secret ou path completo.
- expansão de tenants deve ficar congelada durante a janela de rotação.
- próxima trilha recomendada: Owner MFA Vault/KMS Rotation Evidence Execution.

## 2026-05-13 — Owner MFA Vault/KMS Rotation Evidence Execution

Decisão:

- capturar rotação Vault/KMS como evidence pack declarativo pós-execução, dependente de runbook `READY` e sem executar operações de credencial no command.

Motivação:

- a execução real de rotação precisa deixar evidência auditável de estado de credencial, probe, login/challenge, health, rollback e redaction, sem expor material sensível.

Implementação:

- `owner_mfa_vault_kms_rotation_evidence_queries` compõe rotation runbook e exige confirmations pós-execução.
- `owner_mfa_vault_kms_rotation_evidence` imprime evidence pack, confirmations, decisions, rollback e blockers sem secret material.

Consequências:

- geração/revogação de credenciais permanece externa ao command.
- falha em probe/login/health recomenda rollback operacional fora do command.
- provider deve ser monitorado antes de retomar expansão.
- próxima trilha recomendada: Owner MFA Vault/KMS Post-Rotation Monitoring Review.

## 2026-05-13 — Owner MFA Vault/KMS Post-Rotation Monitoring Review

Decisão:

- classificar a janela pós-rotação Vault/KMS como `HEALTHY`, `WATCH`, `ROLLBACK` ou `BLOCKED` antes de retomar expansão ou encerrar a rotação.

Motivação:

- evidence confirma que a rotação foi executada; ainda é preciso observar estabilidade do provider, login/challenge e suporte antes de declarar a operação segura.

Implementação:

- `owner_mfa_vault_kms_post_rotation_monitoring_queries` compõe rotation evidence e classifica sinais pós-rotação.
- `owner_mfa_vault_kms_post_rotation_monitoring` imprime signals, decisions, watch items, rollback guidance e próximos tracks sem secret material.

Consequências:

- `HEALTHY` libera closure de rotação.
- `WATCH` mantém expansão congelada.
- `ROLLBACK` orienta restauração operacional externa de credencial.
- próxima trilha recomendada: Owner MFA Vault/KMS Rotation Closure Review.

## 2026-05-13 — Owner MFA Vault/KMS Rotation Closure Review

Decisão:

- encerrar a rotação Vault/KMS somente quando o monitoramento pós-rotação estiver `HEALTHY` e os sinais de closure estiverem explicitamente confirmados.

Motivação:

- uma rotação saudável precisa de decisão registrada, evidência arquivada, riscos aceitos, rollback window resolvida e plano claro antes de retomar expansão ou exportar auditoria.

Implementação:

- `owner_mfa_vault_kms_rotation_closure_queries` compõe post-rotation monitoring e classifica closure como `READY`, `WATCH`, `ROLLBACK` ou `BLOCKED`.
- `owner_mfa_vault_kms_rotation_closure` imprime closure signals, decisions, blockers, riscos residuais, guardrails de retomada e próximos tracks sem secret material.

Consequências:

- `READY` libera review de export de evidência auditável ou próximo ciclo controlado de expansão.
- `WATCH` mantém observação pós-rotação.
- `ROLLBACK` retorna para evidência/runbook de rollback.
- closure não exporta evidência formal, não restaura credencial e não retoma expansão automaticamente.
- próxima trilha recomendada: Owner MFA Audit Evidence Export Review.

## 2026-05-13 — Owner MFA Audit Evidence Export Review

Decisão:

- revisar export de evidência MFA owner/admin dentro do módulo `audit`, usando `AuditLog` tenant-scoped e `module=accounts`, antes de gerar qualquer artefato formal.

Motivação:

- `accounts` deve registrar eventos MFA, mas export formal de evidência pertence a `audit`; isso evita exportadores paralelos e reduz risco de vazamento de metadata sensível.

Implementação:

- `owner_mfa_audit_evidence_export_review_queries` amostra o export canônico `audit_evidence_export_queries`, detecta ações MFA e exige confirmações de escopo, redaction, actions esperadas e destinatário.
- `owner_mfa_audit_evidence_export_review` imprime apenas sinais, decisions, blockers, contrato e próximos tracks; não imprime metadata nem conteúdo do export.

Consequências:

- export MFA é tenant-scoped e não platform-scope.
- ausência de eventos MFA bloqueia a execution.
- metadata continua desabilitada por padrão.
- próxima trilha recomendada: Owner MFA Audit Evidence Export Execution.

## 2026-05-13 — Owner MFA Audit Evidence Export Execution

Decisão:

- executar export MFA owner/admin por command dedicado em `audit`, tenant-scoped, usando o export canônico de `AuditLog` e removendo metadata da saída.

Motivação:

- a trilha MFA/Vault precisa de artefato anexável para auditoria sem vazar segredo, metadata sensível ou acoplar `accounts` a regras de exportação.

Implementação:

- `owner_mfa_audit_evidence_export_execution_queries` compõe a review, chama `audit_evidence_export_queries`, filtra `module=accounts` e mantém apenas ações MFA.
- `export_owner_mfa_audit_evidence` emite JSONL/CSV para stdout e falha quando a review está bloqueada.

Consequências:

- export é tenant-scoped e não aceita platform-scope.
- metadata não é incluída.
- storage, assinatura e retenção ficam fora do recorte.
- próxima trilha recomendada: Owner MFA Audit Evidence Export Closure Review.

## 2026-05-13 — Owner MFA Audit Evidence Export Closure Review

Decisão:

- fechar o export MFA owner/admin somente quando o artefato tenant-scoped tiver sido gerado, entregue, vinculado a owner de retenção e coberto por decisão de storage/assinatura futura.

Motivação:

- gerar JSONL/CSV não basta para auditoria operacional; é preciso confirmar destinatário, retenção e riscos sem transformar o command em storage, assinatura ou cofre de artefatos.

Implementação:

- `owner_mfa_audit_evidence_export_closure_queries` compõe a export execution e valida entrega, retenção, decisão de storage e riscos residuais.
- `owner_mfa_audit_evidence_export_closure` imprime summary, signals, decisions, blockers, riscos e próximos tracks sem reimprimir conteúdo do export.

Consequências:

- closure não altera `AuditLog` nem reexporta conteúdo sensível.
- assinatura/storage continuam como trilha futura opcional.
- próxima trilha recomendada: Owner MFA Track Closure Review.

## 2026-05-13 — Owner MFA Track Closure Review

Decisão:

- fechar a trilha MFA owner/admin como pacote operacional somente quando a evidência auditável MFA estiver encerrada e os sinais finais de rollout, suporte, ROI e riscos estiverem confirmados.

Motivação:

- depois de Vault/KMS, rotação e export auditável, o maior risco passa a ser continuar abrindo microtrilhas sem uma decisão de fim; o closure define que a abordagem está pronta para re-seleção de ROI.

Implementação:

- `owner_mfa_track_closure_queries` compõe `audit.application.owner_mfa_audit_evidence_export_closure_queries` e consolida sinais finais da trilha.
- `owner_mfa_track_closure` imprime summary, decisions, blockers, riscos e próximos tracks sem reimprimir evidência exportada.

Consequências:

- trilha MFA/Vault/Audit pode ser considerada fechada para este ciclo quando `READY`.
- novas expansões, storage/assinatura ou hardening adicional devem entrar por nova re-seleção de ROI.
- closure não ativa enforcement/provider/tenant, não altera flags/env e não executa rollback.
- próxima trilha recomendada: Security ROI Re-Selection Review.

## 2026-05-13 — Security ROI Re-Selection Review

Decisão:

- re-selecionar o próximo ROI de segurança após closure MFA/Vault/Audit e priorizar **API Key Governance Foundation Review** quando a superfície programática estiver ativa.

Motivação:

- seguir refinando MFA agora tem retorno marginal menor; API keys representam superfície programática com risco cross-tenant, automação indevida e necessidade clara de escopo/revogação/auditoria.

Implementação:

- `security_roi_reselection_queries` compõe `owner_mfa_track_closure_queries`, pontua candidatos e emite recomendação única.
- `security_roi_reselection` imprime candidatos, scores, decisões e próxima trilha sem implementar a abordagem escolhida.

Consequências:

- próxima abordagem recomendada é `API Key Governance Foundation Review`.
- storage/assinatura MFA e próxima expansão Vault seguem como alternativas futuras, não prioridade imediata.
- a re-seleção não altera autenticação, flags/env, tenants, providers ou AuditLog.

## 2026-05-13 — API Key Governance Foundation Review

Decisão:

- definir governança mínima de API keys antes de criar modelo ou autenticação: tenant-scope, hash de segredo, escopos, revogação, auditoria, last-used e rate limit.

Motivação:

- API keys são superfície programática sensível; criar chave sem escopo, revogação e auditoria abriria risco cross-tenant maior que o benefício inicial.

Implementação:

- `api_key_governance_foundation_queries` classifica Go/No-Go por sinais declarativos e lista requisitos do modelo mínimo.
- `api_key_governance_foundation` imprime decisões, requisitos, blockers e próximos tracks sem gerar segredo real.

Consequências:

- próxima trilha recomendada: API Key Model Minimal Contract Execution.
- autenticação runtime, API pública e UI admin ficam fora deste primeiro corte.
- segredo claro só deve existir no resultado inicial de criação futura; persistência deve ser sempre hash.

## 2026-05-13 — API Key Model Minimal Contract Execution

Decisão:

- criar `ApiKey` tenant-scoped com prefixo, hash, escopos, status e timestamps, acompanhado de command service para criação e revogação auditáveis.

Motivação:

- antes de autenticar requests, o sistema precisa garantir que chaves sejam governáveis: sem segredo claro persistido, sem revogação cross-tenant e com trilha auditável.

Implementação:

- `api_keys.models.ApiKey` guarda `key_hash`, `prefix`, `scopes`, `status`, `last_used_at` e campos de revogação.
- `api_key_commands.create_key(...)` gera segredo uma única vez, persiste hash e registra `api_key.created`.
- `api_key_commands.revoke_key(...)` revoga por `tenant_id + key_id` e registra `api_key.revoked`.

Consequências:

- `api_keys` sai do skeleton estrutural.
- runtime authentication, rate limit real, API pública e UI admin ficam para trilhas seguintes.
- próxima trilha recomendada: API Key Runtime Authentication Contract Review.

## 2026-05-13 — API Key Runtime Authentication Contract Review

Decisão:

- definir autenticação runtime de API keys como contrato antes de implementar middleware/auth class ou endpoints públicos.

Motivação:

- uma API key só é segura se respeitar o tenant resolvido no request, validar hash do segredo completo, exigir status ativo, checar escopo e registrar falhas sem vazar material sensível.

Implementação:

- `api_key_runtime_authentication_contract_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_runtime_authentication_contract` imprime sinais, decisões, requisitos, blockers e próximos tracks.
- contrato exige `Authorization: Bearer`, lookup por `tenant_id + prefix`, `check_password`, escopo mínimo, `last_used_at`, `api_key.auth_failed` e boundary de rate limit.

Consequências:

- não há autenticação DRF implementada nesta wave.
- API pública, rate limiter real e surface admin continuam fora do corte.
- próxima trilha recomendada: API Key Runtime Authentication Skeleton Execution.

## 2026-05-13 — API Key Runtime Authentication Skeleton Execution

Decisão:

- implementar um service runtime mínimo para autenticação por API key, mas ainda não conectá-lo ao DRF nem a endpoints públicos.

Motivação:

- o sistema precisa validar o comportamento crítico em application service antes de abrir superfície HTTP: tenant explícito, Bearer header, prefix lookup, hash match, status ativo, escopo e auditoria segura.

Implementação:

- `api_key_runtime_authentication.authenticate(...)` recebe `tenant_id`, `authorization_header`, `required_scope`, `request_id` e `ip_address`.
- sucesso atualiza `last_used_at` e retorna `rate_limit_key` declarativa.
- falhas relevantes registram `api_key.auth_failed` sem segredo claro, `key_hash` ou header completo.

Consequências:

- runtime de API keys agora tem núcleo testável.
- adapter DRF, permission class, endpoint público e rate limiter real continuam pendentes.
- próxima trilha recomendada: API Key DRF Authentication Adapter Review.

## 2026-05-13 — API Key DRF Authentication Adapter Review

Decisão:

- o adapter DRF de API keys deve ser opt-in por view/surface e não deve ser adicionado a `DEFAULT_AUTHENTICATION_CLASSES` neste estágio.

Motivação:

- plugar API key globalmente poderia mudar o comportamento de endpoints existentes e abrir autenticação programática em superfícies sem escopo/rate-limit explícito.

Implementação:

- `api_key_drf_authentication_adapter_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_drf_authentication_adapter_review` imprime decisões, requisitos, blockers e próximos tracks.
- contrato exige adapter fino em `api_keys.interfaces`, delegação para `api_key_runtime_authentication`, principal seguro, escopo mínimo e hook futuro de rate-limit.

Consequências:

- nenhum setting DRF foi alterado.
- nenhum endpoint público foi criado.
- próxima trilha recomendada: API Key DRF Authentication Adapter Execution.

## 2026-05-13 — API Key DRF Authentication Adapter Execution

Decisão:

- implementar `ApiKeyAuthentication` e `HasApiKeyScope` como adapter DRF opt-in por view, sem alterar autenticação global.

Motivação:

- o núcleo runtime já autentica com segurança; o próximo menor passo é permitir uso controlado em views DRF específicas, exigindo escopo explícito e mantendo endpoints existentes intocados.

Implementação:

- `api_keys.interfaces.authentication.ApiKeyAuthentication` lê `Authorization: Bearer`, usa `request.tenant` e delega para `api_key_runtime_authentication`.
- `ApiKeyPrincipal` expõe apenas `tenant_id`, `api_key_id`, `prefix` e `scopes`.
- `HasApiKeyScope` nega views sem `required_api_key_scope` ou sem escopo suficiente.

Consequências:

- API keys continuam fora de `DEFAULT_AUTHENTICATION_CLASSES`.
- nenhum endpoint público foi criado nesta wave.
- throttle/rate limiter real permanece pendente.
- próxima trilha recomendada: API Key Public Endpoint Pilot Review.

## 2026-05-13 — API Key Public Endpoint Pilot Review

Decisão:

- escolher `GET /api/v1/catalog/products/` como primeiro endpoint público piloto para API keys, com escopo `read:catalog`.

Motivação:

- catálogo read-only reduz risco frente a pedidos, clientes e pagamentos, evita PII e permite validar autenticação API key em superfície útil sem efeitos colaterais.

Implementação:

- `api_key_public_endpoint_pilot_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_pilot_review` imprime piloto recomendado, decisões, requisitos, blockers e próximos tracks.
- contrato exige URL versionada, tenant pelo request, payload seguro, sem `/ops/`, sem `tenant_id` arbitrário e rollout flag.

Consequências:

- nenhum endpoint foi implementado nesta wave.
- API pública continua fechada até a execução do piloto.
- próxima trilha recomendada: API Key Public Catalog Products Endpoint Execution.

## 2026-05-17 — API Key Public Catalog Products Endpoint Execution

Decisão:

- implementar `GET /api/v1/catalog/products/` como primeiro endpoint público protegido por API key, atrás da flag `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED`.

Motivação:

- catálogo read-only valida a pilha API key em produção controlada com baixo risco: sem PII, sem escrita, sem pedidos/clientes/pagamentos e sem fallback para fixtures.

Implementação:

- `catalog.application.public_catalog_api_queries` lista produtos persistidos `active` e `is_active=True` por tenant.
- `catalog.interfaces.public_api_views.PublicCatalogProductsApiView` usa `ApiKeyAuthentication`, `HasApiKeyScope` e `required_api_key_scope = "read:catalog"`.
- `catalog.interfaces.public_api_urls` registra `products/` sob `api/v1/catalog/`.
- `config.urls` inclui a rota versionada.

Consequências:

- API pública agora possui um piloto real, limitado a catálogo read-only.
- `DEFAULT_AUTHENTICATION_CLASSES` permanece sem API key.
- throttle/rate limiter real continua pendente.
- próxima trilha recomendada: API Key Public Endpoint Rate Limit Review.

## 2026-05-18 — API Key Public Endpoint Rate Limit Review

Decisão:

- definir rate limit de API keys por `tenant + api_key + endpoint`, usando fixed-window via cache Django na primeira implementação.

Motivação:

- já existe endpoint público real; antes de expandir API pública, é necessário limitar abuso por chave/tenant sem recorrer apenas a IP e sem alterar throttle global do DRF.

Implementação:

- `api_key_public_endpoint_rate_limit_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_rate_limit_review` imprime política recomendada, decisões, requisitos, blockers e próximos tracks.
- contrato recomenda 120 requests por 60 segundos, `Retry-After` em 429 e AuditLog `api_key.rate_limited`.

Consequências:

- nenhum throttle real foi implementado nesta wave.
- `DEFAULT_THROTTLE_CLASSES` permanece inalterado.
- próxima trilha recomendada: API Key Public Endpoint Rate Limit Execution.

## 2026-05-18 — API Key Public Endpoint Rate Limit Execution

Decisão:

- implementar rate limit fixed-window opt-in para endpoints públicos por API key, começando por `GET /api/v1/catalog/products/`.

Motivação:

- o endpoint público já existe; limitar por `rate_limit_key + endpoint` reduz abuso por tenant/chave sem ativar throttle global nem depender apenas de IP.

Implementação:

- `api_key_rate_limit` usa cache Django e falha fechado em ausência de identidade/cache.
- `ApiKeyRateLimitThrottle` integra com DRF por `throttle_classes` opt-in.
- `PublicCatalogProductsApiView` ativa o throttle com endpoint lógico `catalog.products.list`.
- settings/env `API_KEYS_RATE_LIMIT_*` e `API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT*` controlam limite e janela.

Consequências:

- excedente retorna `429` com `Retry-After`.
- `api_key.rate_limited` registra estouro sem segredo, hash ou header.
- `DEFAULT_THROTTLE_CLASSES` permanece inalterado.
- próxima trilha recomendada: API Key Public Endpoint Observability Review.

## 2026-05-18 — API Key Public Endpoint Observability Review

Decisão:

- definir observabilidade mínima para API keys públicas antes de criar métricas reais: requests, falhas de autenticação, rate limit e flag operacional do endpoint.

Motivação:

- com endpoint público, autenticação e rate limit ativos, operação precisa enxergar 401/403/429 por tenant/endpoint sem expor segredo, hash ou header.

Implementação:

- `api_key_public_endpoint_observability_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_observability_review` imprime métricas recomendadas, decisões, requisitos, blockers e próximos tracks.
- contrato recomenda `hubx_api_key_public_request_total`, `hubx_api_key_auth_failure_total`, `hubx_api_key_rate_limited_total` e `hubx_api_key_public_endpoint_enabled`.

Consequências:

- nenhuma métrica real foi implementada nesta wave.
- endpoint Prometheus e dashboard ficam para a próxima trilha.
- próxima trilha recomendada: API Key Public Endpoint Metrics Execution.

## 2026-05-18 — API Key Public Endpoint Metrics Execution

Decisão:

- implementar métricas Prometheus mínimas para endpoints públicos por API key, protegidas por token de observabilidade.

Motivação:

- o endpoint público já possui autenticação e rate limit; operação precisa enxergar sucesso, falhas e 429 sem expor material sensível e sem usar API key pública para scrape.

Implementação:

- `api_key_public_endpoint_metrics` registra contadores em cache e exporta Prometheus text format.
- `ApiKeyPublicEndpointMetricsView` expõe `/api-keys/metrics/public-endpoints/` com `API_KEYS_OBSERVABILITY_TOKEN`.
- `ApiKeyAuthentication`, `ApiKeyRateLimitThrottle` e `PublicCatalogProductsApiView` registram auth failures, rate limits e sucessos.

Consequências:

- API keys públicas não autenticam o endpoint de métricas.
- dashboard Grafana e alert rules continuam para a próxima trilha.
- próxima trilha recomendada: API Key Public Endpoint Dashboard Review.

## 2026-05-18 — API Key Public Endpoint Dashboard Review

Decisão:

- definir contrato mínimo de dashboard Grafana para endpoints públicos por API key antes de materializar JSON.

Consequências:

- `api_key_public_endpoint_dashboard_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_dashboard_review` imprime dashboard, painéis, decisões, requisitos, blockers e próximos tracks.
- dashboard recomendado é `Hubx API Key Public Endpoints`, com datasource `DS_PROMETHEUS`.
- painéis mínimos cobrem requests, auth failures, rate limit, endpoint enabled e top tenants.
- labels devem continuar seguras e de baixa cardinalidade.
- segredo, hash, header e valor claro de API key seguem proibidos.
- alert rules permanecem como trilha própria; dashboard não substitui alerta.
- próxima abordagem recomendada: API Key Public Endpoint Dashboard Execution.

## 2026-05-18 — API Key Public Endpoint Dashboard Execution

Decisão:

- versionar o dashboard inicial de Grafana para endpoints públicos por API key em `infra/observability/grafana`.

Consequências:

- `api-key-public-endpoints-dashboard.json` usa datasource parametrizado `DS_PROMETHEUS`.
- painéis consomem `hubx_api_key_public_request_total`, `hubx_api_key_auth_failure_total`, `hubx_api_key_rate_limited_total` e `hubx_api_key_public_endpoint_enabled`.
- variáveis `tenant_id` e `endpoint` permitem triagem sem alta cardinalidade nova.
- dashboard não provisiona Grafana real e não cria alert rules.
- artefato não contém segredo, hash, header ou valor claro de API key.
- próxima abordagem recomendada: API Key Public Endpoint Alert Rules Review.

## 2026-05-18 — API Key Public Endpoint Alert Rules Review

Decisão:

- definir contrato mínimo de alert rules Prometheus para endpoints públicos por API key antes de materializar YAML.

Consequências:

- `api_key_public_endpoint_alert_rules_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_alert_rules_review` imprime regras, decisões, requisitos, blockers e próximos tracks.
- regras recomendadas: `HubxApiKeyPublicAuthFailuresHigh`, `HubxApiKeyPublicRateLimitedHigh` e `HubxApiKeyPublicEndpointDisabled`.
- primeiro pacote deve usar `severity: warning` para evitar ruído antes de baseline produtivo.
- alertas devem usar tenant/endpoint e nunca API key completa, hash, header ou segredo.
- próxima abordagem recomendada: API Key Public Endpoint Alert Rules Execution.

## 2026-05-18 — API Key Public Endpoint Alert Rules Execution

Decisão:

- versionar as alert rules iniciais de Prometheus para endpoints públicos por API key.

Consequências:

- `infra/observability/prometheus/api-keys-alert-rules.yml` contém alertas para auth failures, rate limit e endpoint disabled.
- todos os alertas começam como `severity: warning`.
- regras usam métricas já exportadas por `api_keys`, sem métricas novas.
- annotations orientam triagem sem pedir segredo/hash/header ou API key em claro.
- Prometheus/Alertmanager real continuam fora de escopo desta execution.
- próxima abordagem recomendada: API Key Public Endpoint Observability Closure Review.

## 2026-05-18 — API Key Public Endpoint Observability Closure Review

Decisão:

- fechar a trilha de observabilidade de endpoints públicos por API key com verificação de artefatos e riscos residuais, sem ativar ambiente real.

Consequências:

- `api_key_public_endpoint_observability_closure_queries` verifica metrics service, endpoint, dashboard, alert rules e runbook.
- `api_key_public_endpoint_observability_closure` exige `--rollout-ready` para classificar como ready.
- Prometheus/Grafana/Alertmanager reais continuam ativação de ambiente.
- thresholds e roteamento precisam de calibração após tráfego real.
- novos endpoints públicos devem aderir explicitamente ao contrato de métricas e labels.
- próxima abordagem recomendada: API Key Public Endpoint Production Rollout Review.

## 2026-05-18 — API Key Public Endpoint Production Rollout Review

Decisão:

- criar review executável para rollout produtivo da observabilidade pública de API keys, mantendo ativação real fora do código.

Consequências:

- `api_key_public_endpoint_production_rollout_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_production_rollout_review` imprime checklist, decisões, requisitos, runbook, rollback e próximos tracks.
- rollout produtivo exige token, scrape, dashboard, alert rules, smoke, evidência, rollback e aceite operacional.
- evidência não pode conter segredo, hash, header ou API key em claro.
- próxima abordagem recomendada: API Key Public Endpoint Production Activation Evidence.

## 2026-05-18 — API Key Public Endpoint Production Activation Evidence

Decisão:

- criar command de evidência sanitizada para ativação produtiva de observabilidade pública de API keys.

Consequências:

- `api_key_public_endpoint_production_activation_evidence_queries` classifica evidência por sinais declarativos.
- `api_key_public_endpoint_production_activation_evidence` não executa chamadas reais e não altera ambiente.
- evidência exige ambiente production, scrape ativo, dashboard importado, alert rules carregadas, métricas presentes e rollback ensaiado.
- referências suspeitas de conter token, segredo, hash, header ou API key em claro são descartadas.
- próxima abordagem recomendada: API Key Public Endpoint Post-Activation Monitoring Review.

## 2026-05-18 — API Key Public Endpoint Post-Activation Monitoring Review

Decisão:

- criar review executável para classificar estabilidade pós-ativação antes de expandir endpoints públicos.

Consequências:

- `api_key_public_endpoint_post_activation_monitoring_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_post_activation_monitoring_review` exige janela observada, dashboard revisado, tráfego aceitável, ruído aceitável e rollback não exigido.
- tuning de thresholds e expansão de endpoints ficam fora desta review.
- próxima abordagem recomendada: API Key Public Endpoint Expansion Review.

## 2026-05-18 — API Key Public Endpoint Expansion Review

Decisão:

- escolher `GET /api/v1/catalog/products/<slug>/` como próximo candidato de endpoint público protegido por API key.

Consequências:

- `api_key_public_endpoint_expansion_review_queries` classifica Go/No-Go por sinais declarativos.
- `api_key_public_endpoint_expansion_review` recomenda detalhe público de produto com escopo `read:catalog`.
- execução deve ocorrer em wave própria no módulo `catalog`, reutilizando autenticação/rate limit/observabilidade de `api_keys`.
- pedidos, clientes, pagamentos, admin, PII, tenant_id e estoque bruto permanecem fora do contrato público.
- próxima abordagem recomendada: API Key Public Product Detail Endpoint Contract Review.

## 2026-05-18 — API Key Public Product Detail Endpoint Contract Review

Decisão:

- definir contrato para `GET /api/v1/catalog/products/<slug>/` como próximo endpoint público protegido por API key.

Consequências:

- `api_key_public_product_detail_endpoint_contract_review_queries` classifica Go/No-Go por sinais declarativos.
- execução futura pertence a `catalog`, reutilizando autenticação, escopo, rate limit e métricas de `api_keys`.
- rate limit endpoint será `catalog.products.detail`.
- flag será `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`.
- payload deve ser público e não expor estoque bruto, custo, margem, tenant_id, PII ou dados de pedidos/clientes/pagamentos.
- próxima abordagem recomendada: API Key Public Product Detail Endpoint Execution.

## 2026-05-18 — API Key Public Product Detail Endpoint Execution

Decisão:

- implementar `GET /api/v1/catalog/products/<slug>/` como endpoint público read-only protegido por API key.

Consequências:

- execução fica em `catalog.application.public_catalog_api_queries` e `catalog.interfaces.public_api_views`.
- endpoint usa `read:catalog`, throttle `catalog.products.detail` e flag `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`.
- payload retorna dados públicos de PDP e variantes com disponibilidade segura.
- endpoint não expõe tenant_id, estoque bruto, reserved stock, custo, margem, PII ou dados de outros módulos.
- próxima abordagem recomendada: API Key Public Product Detail Endpoint Observability Review.

## 2026-05-19 — API Key Public Product Detail Endpoint Observability Review

Decisão:

- reaproveitar dashboard e alert rules existentes para `catalog.products.detail`, porque ambos já operam por label `endpoint`.

Consequências:

- `api_key_public_product_detail_observability_review_queries` classifica a cobertura por sinais declarativos.
- nenhum dashboard Grafana novo é necessário nesta fase.
- nenhuma alert rule Prometheus nova é necessária nesta fase.
- métricas continuam sem labels por slug/SKU para preservar cardinalidade e sigilo.
- próxima abordagem recomendada: API Key Public Endpoint Expansion Closure Review.

## 2026-05-19 — API Key Public Endpoint Expansion Closure Review

Decisão:

- fechar a expansão inicial de endpoints públicos de API key com listagem e detalhe de produto.

Consequências:

- `api_key_public_endpoint_expansion_closure_queries` verifica listagem, detalhe, dashboard, alert rules e métricas.
- escopo fechado inclui `GET /api/v1/catalog/products/` e `GET /api/v1/catalog/products/<slug>/`.
- nenhum novo endpoint público deve ser aberto sem nova seleção ROI.
- próximos endpoints precisam repetir tenant-scope, `read:catalog` ou escopo específico, rate limit e observabilidade.
- próxima abordagem recomendada: API Key Governance Closure Review.

## 2026-05-19 — API Key Governance Closure Review

Decisão:

- fechar a trilha de governança de API keys no ciclo atual com endpoints públicos read-only de catálogo e observabilidade mínima.

Consequências:

- `api_key_governance_closure_queries` verifica modelo, command service, runtime auth, DRF adapter, throttle, endpoints públicos e observabilidade.
- escopo público atual fica limitado a listagem e detalhe de produto.
- billing/quotas comerciais continuam diferidos.
- novos endpoints públicos exigem nova seleção ROI e contrato próprio.
- próxima abordagem recomendada: System ROI Re-Selection Review.

## 2026-05-19 — System ROI Re-Selection Review

Decisão:

- selecionar documentação/onboarding de parceiros como próxima frente de maior ROI após a closure de governança de API keys.

Consequências:

- `api_key_system_roi_reselection_queries` classifica candidatos de ROI e bloqueia a seleção quando a closure de API keys não está pronta.
- a próxima abordagem recomendada é API Key Partner Onboarding Documentation Review.
- quotas comerciais, novos endpoints públicos, UX admin e hardening por incidente ficam diferidos até haver pressão explícita.
- a re-seleção não altera runtime, não cria endpoint, não cria quota/billing e não expõe material sensível.

## 2026-05-26 — API Key Partner Onboarding Documentation Review

Decisão:

- criar o contrato mínimo de onboarding de parceiros para a API pública de catálogo antes de expandir endpoints ou monetização.

Consequências:

- `api_key_partner_onboarding_documentation_review_queries` valida a prontidão documental do onboarding.
- `docs/api/public-catalog-partner-onboarding.md` passa a ser o artefato versionado de referência.
- o escopo documentado continua restrito a listagem/detalhe de catálogo com `read:catalog`.
- billing, quotas, admin UX e novos endpoints permanecem diferidos.
- exemplos devem usar placeholders e payload público, sem credencial real, segredo ou hash.

## 2026-05-26 — API Key Partner Documentation Execution Review

Decisão:

- preparar o pacote operacional/publicável de documentação de parceiros antes de qualquer entrega externa.

Consequências:

- `api_key_partner_documentation_execution_review_queries` valida canal, owner, suporte, smoke evidence template e change control.
- `docs/api/public-catalog-partner-onboarding.md` inclui a seção `Delivery package`.
- a execução não publica credencial, não executa smoke real, não altera runtime e não define termos comerciais.
- a próxima abordagem recomendada é API Key Partner Documentation Publication Evidence Review.

## 2026-05-26 — API Key Partner Documentation Publication Evidence Review

Decisão:

- capturar evidência sanitizada de publicação/entrega da documentação de parceiros antes da closure da trilha.

Consequências:

- `api_key_partner_documentation_publication_evidence_queries` valida versão, canal, audiência, tenant reference, timestamp e referência de evidência.
- `docs/api/public-catalog-partner-onboarding.md` inclui a seção `Publication evidence`.
- evidência não inclui credencial, segredo, hash, token, header ou screenshot sensível.
- a review não executa smoke real, não ativa runtime e não altera feature flags.
- a próxima abordagem recomendada é API Key Partner Onboarding Closure Review.

## 2026-05-26 — API Key Partner Onboarding Closure Review

Decisão:

- fechar a trilha de onboarding/documentação de parceiros de API key pública no ciclo atual.

Consequências:

- `api_key_partner_onboarding_closure_queries` consolida documentação, pacote, publication evidence, riscos residuais e deferrals.
- ativação real por parceiro fica diferida para trilha operacional própria.
- quotas comerciais/billing ficam diferidos até nova seleção ROI.
- novos endpoints públicos ficam diferidos até contrato próprio.
- a próxima abordagem recomendada é System ROI Re-Selection Review.

## 2026-05-27 — System ROI Re-Selection Review pós-onboarding

Decisão:

- recomendar API Key Partner Activation Smoke Review como próximo maior ROI após closure de onboarding/documentação.

Consequências:

- `api_key_post_onboarding_roi_reselection_queries` compara ativação smoke, quotas comerciais, expansão de endpoints, UX admin e pausa da trilha.
- ativação smoke vence quando há parceiro pronto e API key preparada.
- quotas comerciais continuam condicionadas a pressão real de plano, abuso ou billing.
- novos endpoints públicos continuam condicionados a demanda concreta depois de list/detail.
- a re-seleção não executa smoke, não cria credencial, não ativa runtime e não muda autenticação.

## 2026-05-27 — System Execution Wave Batteries Review

Decisão:

- pausar a execução linear de waves e organizar a evolução restante em baterias autocontidas com closure e seleção automática da próxima bateria.

Consequências:

- `docs/system-execution-wave-batteries.md` passa a ser o mapa operacional de execução por baterias.
- a próxima bateria recomendada é Battery A — API Key Partner Activation.
- cada bateria deve fechar com closure, atualização de docs, decisão registrada e validação antes de iniciar a próxima.
- se houver blocker, a próxima bateria automática deve ser substituída por uma bateria corretiva mínima.

## 2026-05-27 — API Key Partner Activation Smoke Contract Review

Decisão:

- definir o contrato do primeiro smoke controlado de ativação de parceiro antes de executar qualquer request real.

Consequências:

- `api_key_partner_activation_smoke_contract_queries` valida ROI, referências sanitizadas, escopo list/detail, observabilidade, rollback e redaction.
- o smoke futuro fica limitado a `GET /api/v1/catalog/products/` e `GET /api/v1/catalog/products/<slug>/`.
- esta review não executa request, não cria credencial, não altera runtime e não abre endpoint.
- a próxima abordagem recomendada é API Key Partner Activation Smoke Execution.

## 2026-05-27 — API Key Commercial Quotas Contract Review

Decisão:

- abrir a Battery B por seleção operacional explícita e definir o contrato mínimo de quotas comerciais antes do modelo/enforcement.

Consequências:

- ondas restantes da Battery A ficam diferidas, não canceladas.
- `api_key_commercial_quotas_contract_queries` define dimensões `tenant_id/api_key_id/endpoint/window`.
- o contrato inicial usa escopo `read:catalog`, janela diária, limite padrão e excesso `429`.
- billing, plano/subscription e enforcement runtime ficam fora desta wave.
- a próxima abordagem recomendada é API Key Quota Model Minimal Execution.

## 2026-05-27 — API Key Partner Activation Remaining Waves

Decisão:

- executar e fechar as ondas restantes da Battery A antes de continuar a evolução de quotas comerciais.

Consequências:

- `api_key_partner_activation_smoke_execution_queries` cobre execução sanitizada de list/detail, auth negativa, observabilidade e rollback.
- `api_key_partner_activation_evidence_capture_queries` define evidência sanitizada de resultados, métricas, audit log, handoff e rollback note.
- `api_key_partner_activation_post_smoke_monitoring_queries` valida estabilidade inicial, suporte, rollback e pressão comercial por quota.
- `api_key_partner_activation_closure_queries` fecha a Battery A e direciona o próximo ROI para quotas comerciais.
- nenhuma dessas ondas cria endpoint, quota, billing, plano, runtime change ou registro de credencial.
- a próxima abordagem recomendada é API Key Quota Model Minimal Execution.

## 2026-05-27 — API Key Commercial Quotas Execution & Closure

Decisão:

- concluir a Battery B criando quota comercial mínima para API pública sem criar cobrança real ou enforcement por plano.

Consequências:

- `ApiKeyQuota` define quota por `tenant_id`, `api_key_id`, `endpoint`, `scope`, `window_seconds`, `limit` e `status`.
- `ApiKeyQuotaUsage` registra consumo por janela de forma tenant-scoped.
- `api_key_quota_enforcement` roda após o rate limit técnico e bloqueia excesso com `429`.
- excesso de quota registra audit `api_key.quota_exceeded` e métrica `hubx_api_key_quota_exceeded_total`.
- `/ops/api-keys/quotas/` fornece visibilidade read-only usando permissão `api_keys.view`.
- billing provider, plan/subscription enforcement e endpoints novos continuam fora desta bateria.
- a próxima abordagem recomendada é System ROI Re-Selection Review.

## 2026-05-27 — System ROI Post-Quota Re-Selection Review

Decisão:

- após fechar Battery A e Battery B da trilha de API pública, recomendar Payments Production Readiness Review como próxima abordagem quando provider produtivo, refund e conciliação ainda forem blockers.

Consequências:

- `system_roi_post_quota_reselection_queries` compara pagamentos produtivos, shipping real, runbooks cross-module e experimentação de conversão.
- a review depende da closure de quotas comerciais pronta.
- a review não implementa provider, shipping, runbook produtivo, billing, quota ou endpoint novo.
- pagamentos vencem o ROI quando há blocker de provider produtivo e financeiro porque impactam receita real e risco operacional central.
- shipping real pode vencer se cotação/frete bloquear conversão e pagamentos não forem blocker.
- runbooks cross-module podem vencer se produção estiver pronta tecnicamente, mas ainda sem fechamento operacional.
- a próxima abordagem recomendada é Payments Production Readiness Review.

## 2026-05-27 — Battery C Payments Production Readiness Closure

Decisão:

- concluir a Battery C com gates executáveis de readiness para produção controlada de pagamentos.

Consequências:

- `payments.application.production_readiness_queries` cobre provider gate, activation evidence, webhook smoke, refund gate, refund evidence, reconciliation e closure.
- `payments_production_readiness` permite executar cada review por `--review`.
- a closure exige provider, webhook, refund, reconciliação, rollback/runbook, janela de monitoramento, dono de incidente e decisão registrada.
- a bateria não chama provider real, não movimenta dinheiro automaticamente, não habilita rollout amplo e não registra segredo/token/header.
- refund permanece manual, unitário e controlado; self-service e batch seguem fora.
- correção automática de divergência financeira segue fora.
- a próxima bateria recomendada é Battery D — Shipping Quote Productionization.

## 2026-05-27 — Battery D Shipping Quote Productionization Closure

Decisão:

- concluir a Battery D com quote mínimo tenant-scoped aplicável ao checkout, mantendo provider real externo fora desta etapa.

Consequências:

- `shipping_quote_queries` fornece cotação checkout-ready com carrier, service code, preço, prazo e referência de provider.
- `checkout_shipping_quote_commands.refresh_quote(...)` aplica a cotação em `CheckoutSession.shipping_methods`, seleção e total.
- falha de quote por tenant/CEP inválido limpa seleção de entrega e retorna mensagem explícita.
- `shipping_quote_productionization_queries` fecha contrato, adapter skeleton, integração checkout, UX de falha, observabilidade e closure.
- a bateria não chama transportadora real, não registra token/header/segredo e não calcula peso/dimensão real.
- a próxima bateria recomendada é Battery E — Subscriptions & Tenant Billing Foundation.

## 2026-05-27 — Battery E Subscriptions & Tenant Billing Foundation Closure

Decisão:

- concluir a Battery E criando fundação mínima de plano e assinatura SaaS tenant-scoped.

Consequências:

- `SubscriptionPlan` define código, nome, preço mensal, moeda, quota operacional e status.
- `TenantSubscription` define o estado da assinatura do tenant por plano.
- `subscription_commands` permite criar/atualizar plano e estado do tenant com audit.
- `/ops/subscriptions/` expõe leitura tenant-scoped sem provider de cobrança.
- a bateria não chama Pagar.me, não cobra cartão, não cria invoice real e não acopla pagamentos de pedidos.
- enforcement de plano fica reservado para trilha própria.
- a próxima bateria recomendada é Battery F — Audit Instrumentation Expansion.

## 2026-05-27 — Battery F Audit Instrumentation Expansion Closure

Decisão:

- concluir a Battery F ampliando audit trail apenas para ações críticas administrativas/operacionais, sem logging genérico.

Consequências:

- `payments` passa a registrar `refund.approved` quando um refund sai de `requested` para `processing`.
- `payments` passa a registrar `refund.execution_recorded` após resposta/falha do provider adapter de refund.
- `catalog` ganha `admin_product_commands.update_product_visibility(...)` para mudança auditável de status/visibilidade.
- `api_keys` permanece coberto por criação, revogação, quota atualizada e quota excedida.
- metadata sensível continua redigida: sem segredo, hash, payload provider ou referência externa de pagamento.
- a próxima bateria recomendada é Battery G — Notifications Production Delivery.

## 2026-05-27 — Battery G Notifications Production Delivery Closure

Decisão:

- concluir a Battery G com produção transacional controlada de notifications, usando `EmailLog` e smoke real sem abrir campanhas/lifecycle.

Consequências:

- `notification_production_delivery_commands.execute_transactional_smoke(...)` cria/reusa `EmailLog` system smoke por tenant e processa pelo pipeline existente.
- `notification_production_delivery` consolida provider gate, smoke, evidence, failure handling, monitoring e closure.
- falhas passam a ser classificadas como bounce, rate limit, provider unavailable, authentication ou provider error.
- evidências operacionais mascaram recipient e não imprimem e-mail de customer em claro.
- dry-run continua bloqueando smoke real.
- a próxima bateria recomendada é Battery H — Customer Retention Lifecycle.

## 2026-05-27 — Battery H Customer Retention Lifecycle Closure

Decisão:

- concluir a Battery H com lifecycle mínimo pós-compra baseado em newsletter opt-in, sem campanha recorrente ou automação complexa.

Consequências:

- `newsletter_segment_queries.list_subscribed_segment(...)` expõe segmento consentido tenant-scoped.
- `customer.post_purchase.follow_up` entra no catálogo de intents.
- `customer_retention_lifecycle_commands.plan_post_purchase_follow_up(...)` cria/reusa `EmailLog` para pedido elegível quando o e-mail está inscrito.
- `NewsletterSubscriber.Status.UNSUBSCRIBED` bloqueia criação de log.
- cross-tenant falha antes de consultar/criar comunicação.
- a próxima bateria recomendada é Battery I — Storefront Data-Driven Conversion.

## 2026-05-27 — Battery I Storefront Data-Driven Conversion Closure

Decisão:

- concluir a Battery I criando baseline/funil de conversão storefront e executando um experimento leve de prioridade de cards.

Consequências:

- `storefront_conversion_insights` calcula baseline discovery/PDP/CTA, funil PDP e drop-off de busca/facet.
- `product_card_priority_v1` ajusta `discovery_rank_score` com base em sinais recentes tenant-scoped.
- sinais positivos de PDP/CTA aumentam prioridade; sinais de indisponibilidade reduzem prioridade.
- o experimento não altera preço, estoque, checkout, pedido, pagamento ou disponibilidade.
- a próxima bateria recomendada é Battery J — System Production Closure.

## 2026-05-27 — Battery J System Production Closure

Decisão:

- concluir a Battery J com closure sistêmica declarativa e decisão Go/No-Go para produção real controlada.

Consequências:

- `system_production_closure_queries` consolida matrix, runbooks, smoke, observabilidade, rollback e Go/No-Go.
- `system_production_closure` permite executar cada review de closure por comando.
- `GO` exige evidência operacional externa, aceite de riscos residuais e owner de decisão confirmado.
- `NO-GO` abre bateria corretiva pelo maior blocker.
- a closure não altera settings, flags, providers, tenants nem dados de domínio.
- se `GO`, a próxima trilha recomendada é Growth/Commercial Activation Track.

## 2026-05-28 — Platform Self-Service Tenant Onboarding MVP

Decisão:

- criar o primeiro portal self-service de lojas como wizard operacional em `/ops/platform/onboarding/`, restrito a platform owner/admin.

Consequências:

- `TenantOnboarding` passa a guardar rascunho, progresso, blockers e conclusão da jornada.
- a conclusão orquestra criação de tenant, assinatura interna trialing e owner inicial por services existentes.
- billing real, DNS/TLS automático, upload de logo, catálogo demo, frete, pagamentos e impersonação ficam fora do MVP.
- o portal usa RBAC platform, Design System admin e AuditLog platform-scope.

## 2026-07-06 — Refund Provider Admin Execution

Decisão:

- habilitar execução manual controlada de refund no admin da loja, após aprovação interna no ledger `PaymentRefund`.

Consequências:

- `/ops/payments/refunds/<refund_key>/execute/` chama `payments.application.refund_execution_commands.execute_refund(...)`.
- writes financeiros passam a exigir role tenant-scoped resolvida e permissão `payments.manage`.
- `AsaasProviderAdapter.create_refund(...)` usa `POST /payments/{id}/refund`; Pagar.me mantém o adapter conservador já existente para charge.
- respostas de provider ficam registradas em `PaymentRefund.provider_refund_reference` e `metadata.provider_refund`.
- `payment.refunded`, alteração de pedido, estoque, cupons, shipment e notifications continuam fora da execução automática.

## 2026-07-06 — Advanced Catalog Variants MVP

Decisão:

- expandir `ProductVariant` como unidade administrável de preço, estoque, atributos e logística leve no admin do produto.

Consequências:

- `ProductVariant` passa a guardar `label`, `option_values`, `barcode`, `weight_grams`, `is_active` e `position`.
- o admin do produto permite criar variante, definir variante padrão e desativar variante por POST tenant-scoped.
- desativação é lógica; não há exclusão física de variante no fluxo administrativo.
- o service bloqueia deixar o produto sem variante ativa e impede variante inativa como padrão.
- storefront e checkout continuam consumindo a variante efetiva/padrão existente, sem alterar baixa de estoque ou criação de pedido.
