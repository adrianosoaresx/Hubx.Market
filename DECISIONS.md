# DECISIONS.md

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
