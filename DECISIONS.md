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
