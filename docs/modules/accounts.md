# Accounts

## Responsabilidade
Gerenciar autenticação e contas administrativas.

## Entidades principais
- AccountProfile
- OwnerUser
- PlatformUser

## Casos de uso
- login
- logout
- recuperação de senha

## Regras de negócio
- Owner e Customer são contextos diferentes
- permissões administrativas usam `OwnerUser.role` como contrato inicial
- ausência de contexto de role ainda preserva compatibilidade legada das surfaces admin atuais

## Permissões administrativas iniciais

O primeiro gate de governança fica em `accounts.application.admin_permissions`.

Papéis suportados:

- `owner` e `admin`: podem executar ações sensíveis iniciais;
- `marketing`: pode criar cupons, gerenciar páginas e moderar reviews;
- `content_editor`: pode gerenciar páginas e moderar reviews;
- `support`: pode moderar reviews;
- `viewer`: não pode executar ações mutáveis sensíveis.

Permissões iniciais:

- `coupons.manage`;
- `owners.manage`;
- `pages.manage`;
- `reviews.moderate`.

Contrato:

- commands sensíveis recebem `actor_role` opcional;
- quando `actor_role` existe, o gate bloqueia papéis sem permissão;
- quando `actor_role` não existe, o fluxo legado continua permitido até existir autenticação/admin middleware definitivo;
- views devem preferir `request.owner_user` e só manter fallback por e-mail enquanto a migração de surfaces `/ops/` estiver em andamento;
- views não decidem permissão localmente.

## Owner context middleware

`accounts.interfaces.middleware.OwnerContextMiddleware` injeta `request.owner_user` nas surfaces `/ops/`.

Contrato:

- roda depois de `TenantSubdomainMiddleware` e `AuthenticationMiddleware`;
- só resolve contexto em `/ops` e `/ops/...`;
- exige tenant resolvido e usuário Django autenticado;
- busca `OwnerUser` ativo por `tenant + user.email`;
- mantém `request.owner_user = None` quando não há match;
- não bloqueia a request sozinho.

Esse middleware reduz duplicação nas views, mas o enforcement continua nos commands via `actor_role`.

## Ops authentication gate

`accounts.interfaces.middleware.OpsAuthenticationGateMiddleware` fornece o primeiro gate HTTP para `/ops/`.

Contrato:

- é ativado por `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
- quando ativo, usuário anônimo em `/ops/` é redirecionado para `/accounts/login/?next=...`;
- usuário autenticado sem `request.owner_user` ativo recebe `403`;
- usuário autenticado com `OwnerUser` ativo no tenant segue para a view;
- o gate depende de `OwnerContextMiddleware`, por isso roda depois dele no pipeline.

Status de rollout:

- implementado e coberto por testes;
- desligado por padrão até existir login owner/admin real e sessão operacional pronta;
- pronto para ativação por ambiente quando `/accounts/login/` deixar de ser apenas surface visual.

## Gestão de owners

A surface mínima de gestão fica em `/ops/owners/`.

Escopo atual:

- listar owners por tenant;
- criar owner;
- editar e-mail, nome, papel, status ativo e recebimento de notificações;
- bloquear gestão de owners para papéis sem `owners.manage` quando `actor_role` estiver disponível;
- registrar `owner.created` e `owner.access_updated` em `AuditLog`.

Fora de escopo atual:

- convite por e-mail;
- troca de senha/autenticação real;
- permissões por objeto;
- remoção física de owner;
- ativação default obrigatória do gate em todos os ambientes.

## Integração UI
- views HTTP devem permanecer finas em `interfaces/`
- templates oficiais do Design System podem ser usados como contrato de apresentação para login, cadastro, recuperação e visão geral da conta
- adapters de contexto podem preparar dados de formulário e resumo sem mover regra de negócio para a view
- a mesma camada `interfaces/` também pode expor a área logada do cliente (`/accounts/account/...`) usando page templates oficiais para pedidos, endereços e perfil
- queries de leitura para auth/account devem viver em `application/`; fallback temporário de páginas de entrada e visão geral deve ficar nessa camada, não nas views
- queries de leitura para a área logada do cliente também devem viver em `application/`; paginação, querystring e hrefs podem permanecer nas views como adaptação HTTP

## Escopo por tenant nas leituras de conta
- as query layers de login, cadastro, recuperação e visão geral agora também aceitam `tenant_id` explícito
- quando o request já possui tenant resolvido, a camada `interfaces/` repassa esse contexto para preferir o `AccountProfile` correto da loja
- quando não houver tenant resolvido, o fallback atual continua existindo para preservar compatibilidade nas superfícies que ainda operam sem contexto multi-tenant explícito
- esse fallback global remanescente deve ser lido como compatibilidade legada temporária:
  - útil para superfícies de leitura/auth ainda não totalmente tenant-scoped
  - inadequado como contrato para writes ou flows sensíveis de domínio
- pela leitura atual de roadmap, os próximos candidatos naturais de aposentadoria desse modo global ficam justamente em `accounts`:
  - `account overview` e páginas de auth com perfil demo/global
  - fallback global da customer area
  - tolerância residual de `account_address_commands` sem tenant explícito
- entre esses três, o candidato de menor risco para aposentadoria primeiro é `account_page_queries`:
  - é majoritariamente read-only
  - fica concentrado em login/register/forgot/reset/overview
  - não carrega write path sensível
  - pode migrar de perfil demo/global para estado explícito de ausência ou onboarding com impacto operacional menor que customer area ou address CRUD
- o menor plano seguro para essa aposentadoria fica assim:
  1. retirar primeiro apenas o fallback de perfil demo/global (`FallbackAccountProfileRepository`)
  2. preservar o contrato visual das páginas, mas trocar conteúdo demo por estado explícito de ausência/onboarding
  3. manter, por enquanto, os fallback texts leves de overview derivados de falta de pedidos reais, para não misturar duas mudanças na mesma wave
  4. só depois revisar se login/register/forgot/reset continuam úteis sem preenchimento inicial demo
- isso reduz risco porque:
  - separa identidade demo de continuidade de pedidos
  - evita mexer junto em `account_page_queries` e `account_customer_area_queries`
  - deixa a primeira aposentadoria concentrada em leitura pura e mensagens de página
- essa primeira retirada já foi aplicada em `account_page_queries`:
  - login/register/forgot/overview não usam mais perfil demo/global
  - quando não houver `AccountProfile` persistido, a página continua renderizando normalmente
  - os campos passam a ficar vazios e a cópia vira estado explícito de ausência/readiness, em vez de simular uma pessoa demo
- a revisão seguinte mostrou que **ainda não é o momento de aposentar o fallback global inteiro de `account_customer_area_queries`**
- motivo:
  - a customer area ainda concentra várias superfícies de leitura ao mesmo tempo:
    - lista de pedidos
    - detalhe do pedido
    - endereços
    - perfil
  - o fallback global atual ainda sustenta continuidade visual e contratual dessas páginas quando não há tenant
  - retirar tudo de uma vez misturaria:
    - ausência de perfil
    - ausência de pedidos
    - ausência de endereços
    - empty states e mensagens de continuidade
- leitura atual:
  - **`account_customer_area_queries` ainda não é a próxima retirada mais segura**
  - antes disso, vale quebrar a aposentadoria em passos menores e mais explícitos
- o recorte seguro para essa decomposição agora fica assim:
  1. **retirar primeiro só o fallback global de perfil dentro da customer area**
     - `get_active_profile_context()`
     - `get_profile_page_data()`
     - sem mexer ainda em pedidos e endereços
     - objetivo: transformar identidade/global profile em `missing`, mantendo a continuidade visual do restante
  2. **retirar depois o fallback global de endereços**
     - `get_addresses_page_data()`
     - endereços já podem virar ausência explícita com risco menor do que mexer em pedidos
     - objetivo: separar “sem endereço salvo” de “modo demo/global”
  3. **retirar por último o fallback global de pedidos**
     - `get_orders_page_data()`
     - `get_order_detail_page_data()`
     - esse corte fica por último porque mexe em continuidade, retenção, recovery e leitura operacional do pedido
  4. **só depois revisar o modo global residual da customer area como um todo**
     - quando profile, addresses e orders já estiverem decompostos
     - aí sim faz sentido decidir se `account_customer_area_queries` ainda precisa aceitar modo legado sem tenant
- motivo dessa ordem:
  - `profile` é leitura mais isolada e menos acoplada à continuidade da conta
  - `addresses` tem impacto intermediário, mas não altera jornada crítica de pedido
  - `orders` concentra o maior risco porque mistura histórico, detalhe, retry, hosted payment e sinais operacionais
- leitura prática:
  - a próxima retirada segura dentro da customer area não é “remover tudo”
  - é **aposentar primeiro o fallback global de perfil**, preservando pedidos e endereços para uma wave seguinte
- essa primeira sub-retirada da customer area já foi aplicada:
  - `get_active_profile_context()` não usa mais perfil demo/global
  - `get_profile_page_data()` não usa mais perfil demo/global
  - quando não houver `AccountProfile` persistido, o perfil da customer area agora entra em `missing`
  - pedidos e endereços continuam preservando a compatibilidade atual por enquanto
- a revisão seguinte do eixo de endereços mostrou que **sim, este já parece o próximo corte seguro**
- motivo:
  - `get_addresses_page_data()` é muito mais isolado do que a trilha de pedidos
  - a página já possui empty state honesto no template
  - create/edit/delete já têm fluxo próprio e não dependem de fixture para continuar funcionando
  - a continuidade da conta pode continuar vindo de `orders`, sem exigir endereço demo/global
- o corte recomendado para a próxima wave fica assim:
  1. remover o fallback global de `get_addresses_page_data()`
  2. deixar `addresses` vazio quando não houver persistência real
  3. manter a descrição da página apoiada em pedidos persistidos ou fallback de pedidos por enquanto
  4. não mexer ainda em `get_orders_page_data()` nem `get_order_detail_page_data()`
- leitura prática:
  - a próxima retirada segura agora já não é mais revisão
  - é **executar a aposentadoria do fallback global de endereços**
- essa retirada de endereços já foi aplicada:
  - `get_addresses_page_data()` não usa mais fixture global
  - quando não houver endereço persistido, a página agora fica vazia de forma honesta
  - o empty state do template passa a ser a resposta oficial
  - pedidos continuam preservando a compatibilidade atual por enquanto
- a revisão seguinte do eixo de pedidos mostrou que **ainda não é o momento de aposentar esse fallback global inteiro**
- motivo:
  - `get_orders_page_data()` e `get_order_detail_page_data()` já concentram muito mais do que leitura simples
  - esse contrato hoje também sustenta:
    - retenção e continuidade da conta
    - checkout completion feedback
    - reorder lite
    - payment retry
    - hosted payment continuation
    - recovery guidance e trilha operacional de pagamento
  - retirar o fallback agora misturaria:
    - ausência de histórico
    - ausência de detalhe
    - ausência de CTA de retomada
    - ausência de trilha operacional do pedido
- leitura atual:
  - **orders ainda não é o próximo corte seguro**
  - antes disso, vale decompor esse legado em etapas menores
- a próxima decomposição recomendada para `orders` fica assim:
  1. separar `orders list` de `order detail`
  2. revisar primeiro a aposentadoria da **lista** (`get_orders_page_data()`)
  3. deixar o **detalhe** (`get_order_detail_page_data()`) por último
  4. só então revisar o modo global residual de pedidos como um todo
- por quê:
  - a lista aceita melhor um empty state explícito
  - o detalhe ainda é o ponto onde mais se concentram continuidade, recovery e ações reais
- a revisão seguinte da **orders list** mostrou que este já parece o próximo corte seguro dentro do eixo de pedidos
- motivo:
  - `get_orders_page_data()` é primariamente leitura
  - o template da lista já possui empty state honesto para ausência real
  - a lista não concentra, sozinha, a mesma carga operacional de recovery e retomada que existe no detalhe
  - o risco maior continua concentrado em `get_order_detail_page_data()`
- leitura prática:
  - a próxima retirada segura na trilha de pedidos agora deve começar pela **lista**
  - o **detalhe** continua ficando por último neste eixo
- essa retirada da **lista de pedidos** já foi aplicada:
  - `get_orders_page_data()` não usa mais fallback global
  - a view `account-orders` também deixa de reaproveitar pedidos fixture quando não houver persistência real
  - ausência de histórico na lista agora aparece como empty state honesto, com `orders_mode = missing`
  - `get_order_detail_page_data()` continua preservando compatibilidade legada por enquanto
- a revisão seguinte do **detalhe do pedido** confirmou que **ainda não é hora** de aposentar esse fallback global
- motivo:
  - `get_order_detail_page_data()` ainda concentra continuidade, recovery e ações reais demais em uma única superfície
  - o detalhe hoje também sustenta:
    - `checkout-completed` / confirmação inicial
    - `reorder lite`
    - `payment retry`
    - hosted payment continuation
    - trilha operacional de `PaymentAttempt`
    - guidance para pending stale, drift e revisão operacional
- leitura prática:
  - o detalhe continua sendo o ponto mais sensível do legado remanescente em `account_customer_area_queries`
  - a próxima retirada segura **não** deve começar por ele sem uma decomposição adicional
- a decomposição segura do **order detail** agora fica assim:
  1. **separar a leitura base do detalhe**
     - resumo principal
     - status atual
     - itens e totais
     - activity feed básico
     - objetivo: distinguir o que é leitura passiva do que já é capability operacional
  2. **isolar o `confirmation_mode` do checkout**
     - `checkout-completed`
     - confirmação inicial do pedido
     - objetivo: não misturar handoff do checkout com fallback global do detalhe inteiro
  3. **revisar primeiro a capability de `reorder lite`**
     - por continuar mais próxima de continuidade comercial do que de recovery transacional
  4. **deixar depois o bloco de recovery e pagamento**
     - `confirm_payment`
     - `payment_retry`
     - hosted payment continuation
     - trilha operacional de `PaymentAttempt`
     - guidance de stale pending, drift e revisão operacional
  5. **só então revisar a aposentadoria residual do fallback global no detalhe**
     - quando leitura base, confirmação e capabilities já estiverem decompostas
- motivo dessa ordem:
  - a leitura base é o recorte mais previsível e menos acoplado
  - `confirmation_mode` ainda é leitura contextual, mas não deve continuar colado ao legado inteiro
  - `reorder lite` é mais seguro do que mexer cedo em payment recovery
  - a parte de pagamento continua sendo a mais sensível porque mistura ações, retomada e observabilidade operacional
- leitura prática:
  - o próximo passo seguro agora não é “remover o detalhe”
  - é **planejar o primeiro subcorte dentro do detalhe**, começando pela leitura base ou pelo handoff de confirmação
- a revisão da **leitura base do detalhe** mostrou que **sim, este parece o primeiro subcorte seguro**, mas com um recorte mais estreito do que “todo o detalhe passivo”
- o que já parece seguro classificar como leitura base:
  - `page_title`
  - `eyebrow`
  - `summary_title`
  - `status_title`
  - `order_number`
  - `order_status_label` / `order_status_variant`
  - `payment_status`
  - `shipping_status`
  - `summary_content`
  - `order_items`
  - `subtotal`, `shipping`, `discount`, `installments`, `total`
  - `activity_items` básicos do pedido
- o que **ainda não** parece seguro colocar no mesmo subcorte:
  - `page_description`
  - `page_meta`
  - `summary_subtitle`
  - `summary_note`
  - qualquer bloco de `PaymentAttempt`
  - qualquer CTA ou disponibilidade de ação
  - `pending_recovery_*`
  - `order_pending_recovery_*`
  - `confirmation_mode`
- motivo:
  - parte importante da copy do detalhe já foi enriquecida com continuidade, checkout handoff, payment source, retry, hosted payment e sinais operacionais
  - então “leitura base” precisa significar **payload estrutural do pedido**, não toda a narrativa da página
- leitura prática:
  - o primeiro subcorte seguro dentro do detalhe agora fica melhor definido como:
    - **payload estrutural do pedido**
    - deixando copy enriquecida, handoff e recovery para waves seguintes
- o plano seguro para executar esse primeiro subcorte agora fica assim:
  1. **extrair a montagem estrutural do detalhe para um bloco próprio**
     - resumo principal
     - status atual
     - itens e totais
     - timeline básica
  2. **preservar a interface do template**
     - sem redesign
     - sem mudar nomes já consumidos em `order_detail_page.html`
  3. **manter fora desse primeiro corte toda a narrativa enriquecida**
     - `page_description`
     - `page_meta`
     - `summary_subtitle`
     - `summary_note`
  4. **não tocar ainda em capability flags**
     - `reorder_lite_*`
     - `payment_retry_*`
     - `hosted_payment_*`
     - `payment_progression_*`
  5. **não tocar ainda em guidance operacional**
     - `payment_attempt_*`
     - `pending_recovery_*`
     - `order_pending_recovery_*`
     - `confirmation_mode`
- objetivo desse plano:
  - separar o “esqueleto persistido do pedido” da parte mais sensível de jornada e operação
  - preparar um corte futuro sem apagar cedo demais recovery, hosted payment ou feedback do checkout
- leitura prática:
  - a próxima execução segura do detalhe deve começar por uma **extração estrutural interna**
  - e não por mudança direta de comportamento visível na jornada
- essa primeira extração estrutural já foi aplicada:
  - a montagem do payload estrutural do detalhe agora fica isolada em um bloco próprio dentro de `account_customer_area_queries`
  - o contrato já consumido por `order_detail_page.html` foi preservado
  - copy enriquecida, handoff de checkout, CTAs e recovery continuam fora dessa primeira extração
- a revisão seguinte do **handoff de confirmação do checkout** mostrou que **sim, este já parece o próximo subcorte seguro**
- motivo:
  - `confirmation_mode` entra por um gate explícito na view (`result=checkout-completed`)
  - ele altera um recorte relativamente localizado do payload:
    - `eyebrow`
    - `summary_title`
    - `status_title`
    - `page_description`
    - `page_meta`
    - `summary_subtitle`
    - `summary_note`
    - `activity_title`
    - `activity_description`
  - ele não é a mesma coisa que recovery de pagamento nem depende diretamente de `PaymentAttempt`
- leitura prática:
  - depois da extração estrutural, o próximo subcorte seguro do detalhe já parece ser justamente o **harness de confirmação inicial do checkout**
  - recovery, hosted payment, retry e trilha operacional continuam ficando para depois
- o plano seguro para esse handoff agora fica assim:
  1. **isolar a montagem do payload de confirmação em um bloco próprio**
     - `eyebrow`
     - `summary_title`
     - `status_title`
     - `page_description`
     - `page_meta`
     - `summary_subtitle`
     - `summary_note`
     - `activity_title`
     - `activity_description`
  2. **preservar o gate explícito na view**
     - `result=checkout-completed`
     - sem espalhar essa decisão pelo restante da journey
  3. **não tocar ainda no bloco transacional do detalhe**
     - `PaymentAttempt`
     - hosted payment
     - retry
     - pending/drift recovery
  4. **não misturar esse handoff com remoção de fallback global**
     - primeiro isolar
     - depois reavaliar se o subcorte já consegue viver sozinho
- objetivo desse plano:
  - separar feedback de handoff do checkout da narrativa residual do detalhe
  - deixar o trecho de confirmação inicial mais previsível para um corte futuro
- leitura prática:
  - a próxima execução segura agora parece ser uma **extração dedicada do confirmation payload**
  - sem mexer ainda na parte operacional de pagamento
- essa extração dedicada do handoff já foi aplicada:
  - o payload de confirmação inicial do checkout agora nasce em um bloco próprio dentro de `account_customer_area_queries`
  - o gate explícito na view (`result=checkout-completed`) foi preservado
  - o bloco transacional de `payments` continua fora desse recorte
- a customer area (`orders`, `order detail`, `addresses`, `profile`) agora segue esse mesmo contrato quando houver tenant resolvido
- a visão geral da conta (`account overview`) também passa a respeitar esse escopo nas leituras derivadas de pedidos e continuidade de compra
- isso evita que um `AccountProfile` ativo mais recente de outra loja desvie o histórico e os endereços exibidos para a conta atual
- além disso, em requests já tenant-scoped, a customer area deixa de reaproveitar fixtures de pedidos e endereços como fallback silencioso
- nesse cenário, ausência de dados persistidos passa a aparecer como contexto faltante (`missing`) em vez de simular histórico de outra superfície

## Readiness de persistência
- o módulo agora possui `AccountProfile` como estrutura mínima para dados persistidos de identidade, contato e preferências da experiência de conta
- `AccountProfile` não substitui o contexto de `Customer`; ele prepara leituras seguras para auth/account e área logada sem abrir acoplamento indevido nesta wave
- `AccountProfile` agora também pode manter um vínculo explícito opcional com `Customer`, permitindo que a área logada prefira uma relação de domínio estável sem quebrar o fallback anterior por `tenant + email`
- essa base permite futuras leituras reais para:
  - account overview
  - profile/preferences
  - identidade básica da área logada
- as query layers de `account overview` e `profile` já consomem `AccountProfile` quando houver registro persistido disponível

## O que a query layer poderá consumir depois
- `first_name`, `last_name`, `email`, `phone`
- `newsletter_opt_in`, `order_updates_opt_in`
- `last_login_at` e `last_seen_at` para resumo/atividade da conta

## O que ainda falta
- ampliação da seed mínima ou fonte persistida real de perfis em ambiente mais completo
- integração formal com autenticação real e sessão do usuário
- conexão futura com dados reais de pedidos/endereços sem puxar regra indevida para `accounts`

## Readiness de Address CRUD
- a área logada agora expõe rotas nomeadas para o próximo passo de CRUD de endereços:
  - `account-address-create`
  - `account-address-edit`
  - `account-address-delete`
- nesta wave, essas rotas ainda funcionam como readiness/navigation:
  - redirecionam de volta para `account-addresses`
  - preservam a intenção (`create`, `edit`, `delete`) via querystring
  - mantêm o contrato atual da página e evitam abrir fluxo incompleto

## Create/Edit de endereços
- `account-address-create` e `account-address-edit` agora já aceitam `POST` real
- a implementação reutiliza a própria página `account-addresses` como superfície de formulário
- o fluxo atual:
  - `GET` nas rotas de create/edit continua posicionando a experiência na página de endereços
  - `POST` persiste `CustomerAddress`
  - após salvar, o usuário volta para `account-addresses#address-management`
- `delete` continua apenas em readiness/navigation nesta etapa

## Delete de endereços
- `account-address-delete` agora aceita `POST` real
- a confirmação continua ancorada na própria página `account-addresses`
- a remoção usa o mesmo vínculo seguro da área logada:
  - `AccountProfile` ativo
  - `Customer` por `tenant + email`
- endereços de outro customer não entram no escopo de remoção do customer atual

## Escopo por tenant nos commands de endereço
- `account_address_commands` agora também aceita `tenant_id` explícito para create, edit, delete e leitura auxiliar do formulário
- quando o request já possui tenant resolvido, a camada `interfaces/` repassa esse contexto para que o customer atual seja resolvido dentro da loja correta
- isso evita que um `AccountProfile` ativo de outro tenant, mais recente, desvie operações de endereço em cenários com e-mails repetidos entre lojas

## Integração mais profunda da customer area
- a query layer da área logada agora prefere relacionamentos explícitos quando disponíveis:
  - `AccountProfile.customer`
  - `Order.customer`
- quando esses vínculos ainda não existirem em registros antigos, o sistema continua funcionando com fallback por `tenant + email`
- isso melhora a integridade dos dados e prepara futuras waves com menos dependência de matching por snapshot

## Readiness de backfill dos vínculos explícitos
- o módulo agora expõe o comando `backfill_customer_links`
- ele tenta preencher com segurança:
  - `AccountProfile.customer`
  - `Order.customer`
- o critério é estritamente determinístico:
  - mesmo `tenant`
  - `email`/`customer_email` com match case-insensitive
  - exatamente um `Customer` candidato
- quando houver zero ou múltiplos candidatos, o comando não força vínculo e apenas faz no-op seguro
- existe suporte a `--dry-run` para inspeção antes de persistir alterações

## Auto-população em writes futuros
- `AccountProfile` agora tenta preencher `customer` automaticamente no `save()`
- isso só acontece quando:
  - o perfil ainda não possui `customer`
  - existe `tenant`
  - o `email` encontra exatamente um `Customer` no mesmo tenant
- quando o match é ambíguo ou inexistente, o vínculo continua vazio e o sistema preserva o fallback atual

## Visibilidade operacional dos vínculos
- a query layer da customer area agora expõe metadados internos:
  - `operational_linkage_visibility`
  - `operational_linkage_mode`
- esses campos não alteram o contrato visual da área do cliente, mas permitem inspeção segura em testes, debug e observabilidade interna
- o comando `backfill_customer_links --dry-run` agora também informa quantos registros já estavam explicitamente vinculados

## Refinamento de experiência da customer area
- a área do cliente agora usa mensagens mais humanas e contextuais em:
  - overview da conta
  - lista de pedidos
  - detalhe do pedido
- esse refinamento continua apoiado apenas nos dados já persistidos:
  - `AccountProfile`
  - `Order`
  - `OrderItem`
  - `CustomerAddress`
- a arquitetura continua a mesma:
  - views finas
  - contexto preparado em `application/`
  - contratos de template preservados

## Sinais leves de confiança
- a customer area agora reforça confiança usando somente dados já persistidos do pedido:
  - estado atual
  - andamento operacional
  - última atualização registrada
- isso melhora a leitura de:
  - lista de pedidos
  - detalhe do pedido
  - linha do tempo
- sem simular rastreio externo, eventos logísticos falsos ou integrações inexistentes

## Retenção e reengajamento leves
- a área do cliente agora usa sinais simples de retenção baseados apenas em dados já persistidos:
  - quantidade de pedidos
  - recência da última movimentação
  - histórico já salvo na conta
- esses sinais refinam:
  - resumo da conta
  - descrição da lista de pedidos
  - contexto do detalhe do pedido
- quando não houver leitura persistida real de pedidos, a experiência continua com copy genérica e fallback seguro

## Continuidade de pedidos na customer area
- a lista e o detalhe de pedidos agora reforçam melhor a continuidade da jornada usando apenas dados já persistidos:
  - status atual
  - recência da última atualização
  - quantidade de pedidos já salvos na conta
- a query layer passou a derivar:
  - hints curtos por linha para indicar continuidade do histórico
  - um `próximo passo esperado` no detalhe do pedido
  - descrições mais úteis sobre quando voltar para acompanhar ou comprar de novo
- tudo continua sem redesign e sem depender de integrações externas de tracking ou recomendação

## Continuidade na visão geral da conta
- a `account overview` agora também consome os pedidos persistidos da customer area quando eles existirem
- isso permite mostrar:
  - descrição da página mais alinhada ao histórico real da conta
  - resumo da conta com contexto do pedido mais recente
  - tabela de pedidos recentes usando os mesmos sinais de continuidade já aplicados na área de pedidos
- quando não houver leitura persistida real de pedidos, a visão geral continua usando fallback seguro

## Continuidade entre perfil e endereços
- `profile` e `addresses` agora também reforçam a continuidade da conta usando apenas dados já persistidos:
  - quantidade de pedidos já salvos
  - quantidade de endereços disponíveis
  - existência de endereço principal
- isso melhora:
  - a descrição do perfil
  - o contexto das preferências
  - a descrição da página de endereços
- a intenção é deixar mais claro como dados pessoais, preferências e endereços sustentam o acompanhamento do pedido atual e as próximas compras

## Guidance de retorno ao catálogo
- a área do cliente agora também usa guidance leve de retorno ao catálogo em:
  - lista de pedidos
  - detalhe do pedido
- esse guidance continua totalmente honesto e baseado só no estado atual da conta:
  - quantidade de pedidos salvos
  - status atual do pedido
  - estágio de envio
- a intenção não é recomendar produtos, e sim deixar mais claro quando o catálogo continua sendo o próximo ponto natural para uma nova compra

## Confirmação inicial do pedido
- quando um pedido nasce a partir da etapa `review` do checkout, o detalhe do pedido na área do cliente agora também pode entrar em `confirmation mode`
- isso não cria uma nova página; apenas reforça no mesmo template que:
  - o pedido foi iniciado com sucesso
  - esta ainda é uma confirmação inicial
  - a evolução real de pagamento, preparo e envio passa a aparecer dali em diante
- a view continua fina e apenas repassa o contexto; a copy de confirmação fica na query layer da customer area
- esse handoff agora também deixa mais explícito que:
  - itens, entrega e forma de pagamento da revisão já foram registrados
  - o pagamento ainda continua pendente nessa chegada inicial
  - a próxima confiança vem das atualizações futuras do próprio pedido

## Fechamento de pedido na customer area
- a área do cliente agora também reflete melhor quando o pedido já chegou ao fim do ciclo operacional
- quando o pedido estiver com entrega concluída, o detalhe passa a comunicar melhor que:
  - a compra foi entregue com segurança
  - o histórico continua salvo na conta
  - o próximo passo natural já não é acompanhamento, e sim retorno opcional ao catálogo
- isso continua sem redesign e usando apenas os estados persistidos já existentes do pedido

## Return-to-buy review
- a área do cliente agora também reforça melhor quando a conta já está pronta para uma nova compra
- esse refinamento aparece especialmente em:
  - cabeçalho da lista de pedidos
  - detalhe de pedido já concluído
  - descrição lateral da linha do tempo
- a intenção continua leve e honesta:
  - sem recomendação personalizada
  - sem campanha artificial
  - apenas deixando mais claro quando o catálogo volta a ser o próximo ponto natural

## Recovery guidance para pagamento pendente
- o detalhe do pedido agora também diferencia melhor quando uma `PaymentAttempt` pendente ficou aberta por tempo demais
- quando ainda existir hosted payment reaproveitável, a área do cliente passa a recomendar explicitamente que a retomada mais segura é reabrir esse fluxo antes de criar outra tentativa
- quando não houver uma retomada clara, o pedido continua salvo, mas a experiência deixa explícito que o estado já merece revisão operacional antes do próximo passo
- o detalhe também já consegue sinalizar quando `Order` e `PaymentAttempt` ficaram operacionalmente desalinhados, para reduzir ambiguidade de suporte em casos de drift
- o próprio `Order.pending` também já pode ganhar guidance operacional leve quando fica tempo demais sem avanço:
  - se ainda houver retomada segura, o detalhe orienta esse próximo passo
  - se não houver, a experiência sinaliza que o caso já merece revisão operacional

## Reentrada pela visão geral da conta
- a `account overview` agora também reforça melhor a volta ao catálogo como próximo passo natural quando a conta já possui histórico de pedidos
- esse refinamento aparece em:
  - `page_meta` do cabeçalho
  - subtítulo de `Ações rápidas`
  - atalho direto `Voltar ao catálogo`
- a intenção continua leve e honesta:
- sem reorder real
- sem recomendação personalizada
- apenas usando o histórico já salvo para deixar a conta mais útil como ponto de reentrada no funil

## Reorder lite readiness
- o detalhe do pedido na customer area agora também pode iniciar uma nova sessão de compra a partir do histórico
- esse `reorder lite` continua leve e seguro:
  - usa o pedido anterior só como ponto de reentrada
  - recria no checkout apenas os itens ainda elegíveis
  - redireciona para o estágio `cart` da nova sessão
- quando algum item não puder voltar:
  - a UI deixa isso explícito
  - a sessão continua apenas com os itens elegíveis
- a intenção é transformar o histórico em continuidade real de compra sem prometer recompra automática completa
- a revisão mais recente do `order detail` mostrou que **sim, este já parece o próximo subcorte seguro** dentro do legado residual
- motivo:
  - o CTA nasce de sinais locais e previsíveis do payload:
    - `reorder_lite_available`
    - `reorder_lite_label`
    - `reorder_lite_helper`
  - a ação entra por `POST` explícito no detalhe
  - o write real fica delegado a `checkout_reorder_commands.bootstrap_from_order(...)`
  - ele não depende do mesmo bloco sensível de `payments`, `PaymentAttempt` e recovery operacional
- leitura prática:
  - depois da extração estrutural e do handoff de confirmação, o próximo subcorte seguro do detalhe já parece ser o **boundary de reorder lite**
  - retry, hosted payment e recovery operacional continuam ficando para depois
- cuidado:
  - `reorder lite` ainda é capability comercial de jornada
  - por isso, o próximo passo seguro continua sendo **isolar melhor esse bloco antes de qualquer retirada residual**
- o plano seguro dessa decomposição agora fica:
  1. isolar o payload de `reorder lite` em um bloco próprio do detalhe
     - `reorder_lite_available`
     - `reorder_lite_label`
     - `reorder_lite_helper`
  2. manter a action boundary explícita na view
     - `action_type=reorder_lite`
     - `POST` dedicado no `order detail`
  3. manter o write real delegado a `checkout_reorder_commands.bootstrap_from_order(...)`
  4. não misturar esse subcorte com:
     - `payment_retry_*`
     - `hosted_payment_*`
     - `payment_progression_*`
     - `payment_attempt_*`
     - alerts de pending/drift/recovery
- objetivo desse plano:
  - separar a capability de recompra leve da narrativa residual do detalhe
  - deixar explícita a boundary entre `accounts` como superfície de jornada e `checkout` como dono da nova sessão
- leitura prática:
  - a próxima execução segura nesse eixo parece ser uma **extração dedicada do reorder payload**
  - sem tocar ainda em retry, hosted payment ou recovery operacional
- essa extração dedicada do `reorder lite` já foi aplicada:
  - o payload de recompra leve agora nasce em um bloco próprio dentro de `account_customer_area_queries`
  - a action boundary `action_type=reorder_lite` continua explícita na view
  - o write real continua delegado a `checkout_reorder_commands.bootstrap_from_order(...)`
  - retry, hosted payment e recovery operacional seguem fora desse recorte

## Payment retry readiness lite
- o detalhe do pedido na customer area agora também pode abrir uma nova tentativa de pagamento quando o pedido continuar pendente e a última tentativa tiver falhado
- esse retry continua leve e seguro:
  - não cancela o pedido
  - não cria um segundo pedido
  - não abre uma página nova fora do checkout
- a ação apenas:
  - recria uma `CheckoutSession` com os itens ainda elegíveis
  - leva a pessoa para o estágio `payment`
  - mantém o detalhe do pedido como ponto de retorno
- além disso, a retomada agora também pode reabrir uma `PaymentAttempt` pendente no módulo `payments`
- isso prepara melhor a continuidade entre:
  - pedido com falha
  - nova tentativa de pagamento
  - futuro evento real do gateway
- a revisão mais recente do `order detail` mostrou que **`payment retry` ainda não é o próximo subcorte seguro**
- motivo:
  - o CTA continua local ao detalhe, mas ele já nasce acoplado a uma semântica de falha operacional real
  - o write segue para `checkout_payment_retry_commands.bootstrap_from_failed_order(...)`
  - a capability já conversa diretamente com:
    - status de pagamento falho
    - retomada de checkout
    - continuidade de pagamento
    - guidance de recovery no próprio detalhe
- leitura prática:
  - diferente de `reorder lite`, esse bloco já encosta no boundary de recovery transacional
  - por isso, ele deve continuar **depois** de `hosted payment` / recovery explícito, e não como próximo corte isolado

## Hosted payment continuation
- quando existir uma `PaymentAttempt` pendente para o pedido, o detalhe também pode mostrar:
  - `Abrir pagamento hospedado`
- esse atalho continua leve:
  - sai da customer area por um endpoint interno de `payments`
  - redireciona para o ambiente hospedado do provider
  - volta ao detalhe do pedido com feedback previsível se a tentativa já não estiver mais disponível
- quando o provider devolve a pessoa para o produto, a customer area também já consegue receber feedback leve de retorno:
  - retorno recebido
  - sucesso ainda em verificação
  - falha/cancelamento no retorno
- esse feedback não substitui webhook; ele só deixa a retomada mais clara para a pessoa enquanto o sistema ainda aguarda a confirmação segura
- a revisão mais recente do `order detail` mostrou que **`hosted payment` também ainda não é o próximo subcorte seguro**
- motivo:
  - o CTA nasce no detalhe, mas aponta diretamente para a boundary de `payments`
  - ele depende de:
    - `PaymentAttempt` pendente
    - `attempt_key`
    - `payments:hosted-redirect`
    - guidance de `pending_recovery`
  - isso faz dele mais um bloco de **recovery explícito** do que um simples trecho de apresentação
- leitura prática:
  - `hosted payment` não parece um corte isolado anterior a recovery
  - ele deve continuar junto do bloco de recovery/payment continuity, não antes

## Observabilidade operacional de pagamento
- o detalhe do pedido agora também pode mostrar uma `Trilha do pagamento` quando existir `PaymentAttempt` associada ao pedido
- essa trilha continua leve e usa apenas os marcos operacionais já persistidos em `payments`, como:
  - tentativa criada
  - tentativa preparada para o provider
  - link hospedado criado
  - retorno hospedado
  - webhook com pagamento confirmado ou falho
- a intenção é dar contexto operacional útil sem transformar a customer area em dashboard de suporte
- o restante da UI continua o mesmo:
  - `orders` e `customer area` seguem consumindo leitura limpa por query layer
  - `payments` continua dono da trilha externa e da telemetria mínima da tentativa
- a revisão mais recente do `order detail` mostrou que o restante do legado sensível agora se comporta como **um bloco único de recovery/payment continuity**
- esse bloco reúne, ao mesmo tempo:
  - `payment_progression_*`
  - `payment_retry_*`
  - `hosted_payment_*`
  - `payment_attempt_*`
  - `pending_recovery_*`
  - `order_pending_recovery_*`
- leitura prática:
  - depois de estrutural, confirmação e `reorder lite`, não sobra mais um próximo corte leve óbvio
  - o que sobra agora é um boundary explícito de continuidade e recovery transacional do pagamento
- decisão prática:
  - a próxima revisão segura não deve tentar quebrar isso em mais um CTA isolado
  - deve tratar esse restante como **recovery block** antes de qualquer retirada residual do detalhe
- o plano seguro dessa decomposição agora fica:
  1. isolar primeiro a **leitura operacional passiva**
     - `payment_attempt_*`
  2. isolar depois o **guidance de recovery**
     - `pending_recovery_*`
     - `order_pending_recovery_*`
  3. só então revisar as **capability flags/actions**
     - `payment_progression_*`
     - `payment_retry_*`
     - `hosted_payment_*`
  4. por último reavaliar a narrativa residual que ainda costura esse bloco ao detalhe
- por que essa ordem:
  - separa telemetria passiva de guidance operacional
  - separa guidance de ações que realmente mudam a jornada
  - evita misturar `PaymentAttempt`, retry, hosted redirect e confirmação manual numa única wave
- leitura prática:
  - o próximo passo seguro nesse eixo parece ser começar pela **leitura operacional passiva do recovery block**
  - e não pelas actions de pagamento
- a revisão seguinte mostrou que **sim, a leitura operacional passiva já parece o próximo subcorte seguro** desse bloco
- motivo:
  - ela já aparece como trilha passiva no detalhe:
    - `payment_attempt_operational_visible`
    - `payment_attempt_operational_description`
    - `payment_attempt_timeline_items`
  - o template só renderiza contexto operacional e timeline
  - esse trecho não dispara redirect, retry nem bootstrap de nova sessão
- leitura prática:
  - o próximo passo seguro do recovery block parece ser isolar primeiro o sub-bloco de `payment_attempt_*`
  - guidance e actions continuam vindo depois
- essa extração da leitura passiva de `PaymentAttempt` já foi aplicada:
  - o payload `payment_attempt_*` agora nasce em um bloco próprio dentro de `account_customer_area_queries`
  - a `Trilha do pagamento` continua usando o mesmo contrato no template
  - guidance de recovery e actions de pagamento seguem fora desse recorte
- a revisão seguinte mostrou que **sim, o guidance de recovery já parece o próximo subcorte seguro** desse bloco
- motivo:
  - `pending_recovery_*` e `order_pending_recovery_*` hoje renderizam apenas alerts passivos no detalhe
  - o template só exibe feedback contextual:
    - retomada hospedada recomendada
    - pedido pendente sem avanço
    - revisão operacional quando não houver caminho seguro
  - esse trecho ainda não dispara retry, redirect nem bootstrap por conta própria
- leitura prática:
  - o próximo passo seguro do recovery block parece ser isolar o guidance de recovery
  - as actions reais de pagamento continuam vindo depois
- essa extração do guidance de recovery já foi aplicada:
  - o payload de `pending_recovery_*` e `order_pending_recovery_*` agora nasce em um bloco próprio dentro de `account_customer_area_queries`
  - os alerts da lateral continuam usando o mesmo contrato no template
  - as actions reais de pagamento seguem fora desse recorte
- a revisão seguinte mostrou que o restante das actions já se comporta como **um único actions block de continuidade de pagamento**
- esse bloco reúne:
  - `payment_progression_*`
  - `payment_retry_*`
  - `hosted_payment_*`
- motivo:
  - todas as actions saem do mesmo `order detail`
  - todas compartilham a mesma surface de jornada e retorno
  - e todas disparam continuidade real para outro boundary:
    - confirmação interna em `orders`
    - retry em `checkout`
    - redirect hospedado em `payments`
- leitura prática:
  - não sobra mais um próximo CTA leve a ser revisado separadamente
  - o que sobra agora é tratar essas actions como **um único bloco residual de continuidade**
- o plano seguro dessa decomposição agora fica:
  1. isolar primeiro o **payload declarativo das actions**
     - `payment_progression_*`
     - `payment_retry_*`
     - `hosted_payment_*`
  2. preservar a **surface única de renderização**
     - `_build_order_detail_actions(...)`
  3. manter o **dispatch transacional** agrupado na view enquanto o bloco ainda estiver sensível
     - `confirm_payment`
     - `payment_retry`
     - `reorder_lite`
     - `hosted payment`
  4. só depois reavaliar se vale decompor o restante por tipo de boundary:
     - confirmação interna em `orders`
     - continuidade em `checkout`
     - redirect hospedado em `payments`
- por que essa ordem:
  - separa primeiro configuração/declaração de action da execução real
  - mantém a jornada previsível enquanto o bloco ainda mistura múltiplos módulos
  - evita refactor cedo demais em fluxos que já encostam em `orders`, `checkout` e `payments`
- leitura prática:
  - o próximo passo seguro nesse eixo parece ser uma **extração do payload declarativo das actions**
  - não uma separação prematura das actions transacionais
- essa extração do payload declarativo das actions já foi aplicada:
  - `payment_progression_*`
  - `payment_retry_*`
  - `hosted_payment_*`
  agora nascem em um bloco próprio dentro de `account_customer_area_queries`
- a renderização continua unificada em `_build_order_detail_actions(...)`
- o dispatch transacional continua agrupado na view do detalhe
- leitura prática:
  - agora o actions block já separa melhor:
    - payload declarativo
    - renderização
    - execução real
  - os próximos cortes podem continuar sem mexer cedo demais no comportamento sensível de continuidade de pagamento
- a revisão seguinte mostrou que **sim, a renderização unificada já parece o próximo subcorte seguro** desse eixo
- motivo:
  - `_build_order_detail_actions(...)` já funciona como surface única de montagem visual
  - ela só traduz o payload declarativo em HTML/links/forms
  - os efeitos reais continuam totalmente delegados para o `POST` do detalhe ou para `payments:hosted-redirect`
- leitura prática:
  - o próximo passo seguro parece ser isolar melhor essa renderização
  - o dispatch transacional continua vindo depois
- o plano seguro dessa decomposição agora fica:
  1. isolar primeiro a **renderização declarativa do bloco**
     - cada action vira um item de configuração visual previsível
  2. manter a **montagem final unificada**
     - `_build_order_detail_actions(...)` continua sendo a única surface pública desta etapa
  3. preservar o **dispatch agrupado**
     - nenhum `POST` ou redirect muda nesta wave
  4. só depois reavaliar se a renderização já pode ser quebrada por tipo de action
- por que essa ordem:
  - separa visualização de execução sem espalhar a surface do detalhe
  - mantém os testes atuais válidos
  - evita refactor cedo demais em flows que ainda compartilham a mesma jornada visual
- essa extração da renderização declarativa já foi aplicada:
  - cada action agora nasce primeiro como item declarativo interno da view
  - a montagem HTML segue centralizada em `_build_order_detail_actions(...)`
  - o dispatch transacional continua intacto
- leitura prática:
  - o actions block agora já separa melhor:
    - payload de contexto
    - itens declarativos de renderização
    - montagem final
    - execução real
- a revisão seguinte mostrou que o **dispatch agrupado ainda não é o próximo subcorte seguro**
- motivo:
  - `reorder_lite` já delega continuidade real para `checkout`
  - `payment_retry` já abre nova trilha de recuperação em `checkout`
  - `confirm_payment` já altera lifecycle real em `orders`
  - todos ainda compartilham o mesmo `POST` e a mesma jornada de retorno do detalhe
- leitura prática:
  - o dispatch deve continuar agrupado por enquanto
  - o bloco já está bem decomposto o suficiente antes de tentar separar a execução real por action
- a revisão residual do `order detail` mostrou que o que ainda sobra como legado sensível não é mais um bloco funcional grande
- o residual agora está concentrado principalmente em **costura narrativa do payload final**, como:
  - enriquecimento de `page_meta`
  - enriquecimento de `summary_note`
  - composição textual que junta:
    - pagamento atual
    - tentativa atual
    - guidance comercial
    - continuidade de jornada
- leitura prática:
  - estrutural, confirmação, `reorder lite`, leitura passiva, guidance e actions já estão bem mais honestos
  - o que sobra agora é mais **narrativa residual** do que boundary funcional mal definida
- decisão prática:
  - não parece haver outro corte estrutural urgente antes disso
  - a próxima evolução segura, se quisermos seguir, deve revisar essa costura narrativa final como eixo próprio
- a revisão da narrativa residual mostrou que esse eixo também já é **localizado e tratável**
- hoje a maior concentração está em dois pontos:
  - composição incremental de `summary_note`
  - composição incremental de `page_meta`
- esses campos ainda acumulam informação de múltiplas origens:
  - base do pedido
  - guidance comercial
  - origem atual do pagamento
  - estado da `PaymentAttempt`
  - handoff de confirmação inicial
- leitura prática:
  - isso não parece risco de boundary entre módulos
  - parece mais um ponto de **clareza e previsibilidade narrativa** dentro de `accounts`
- decisão prática:
  - se quisermos seguir, o próximo passo seguro deve ser tratar `summary_note` e `page_meta` como um pequeno **narrative block**
  - antes de qualquer tentativa de aposentadoria final do detalhe
- o plano seguro dessa decomposição agora fica:
  1. isolar primeiro a **base narrativa**
     - `summary_note` e `page_meta` como payload inicial previsível
  2. separar depois os **enriquecimentos de pagamento**
     - origem atual do pagamento
     - referência atual
  3. separar depois os **enriquecimentos de tentativa**
     - status da tentativa
     - provider
     - referência externa
     - último evento
  4. manter o **handoff de confirmação** fora dessa etapa
     - ele continua como bloco próprio
- por que essa ordem:
  - separa copy-base de copy incremental
  - preserva o comportamento atual do detalhe
  - evita misturar narrativa residual com o bloco de confirmação já extraído
- essa extração da base narrativa já foi aplicada:
  - `page_description`
  - `page_meta`
  - `summary_subtitle`
  - `summary_note`
  - `activity_description`
  - `return_to_buy_*`
  agora nascem em um bloco próprio dentro de `account_customer_area_queries`
- leitura prática:
  - a costura narrativa do detalhe começa a ficar separada entre:
    - base narrativa
    - enriquecimento de pagamento
    - enriquecimento de tentativa
    - confirmação
- essa extração do enriquecimento de pagamento já foi aplicada:
  - a narrativa de:
    - origem atual do pagamento
    - referência atual
    - `page_meta` com `pagamento via ...`
  agora nasce em um helper próprio dentro de `account_customer_area_queries`
- leitura prática:
  - a narrativa do detalhe agora separa melhor:
    - base
    - pagamento
    - tentativa
    - confirmação
- essa extração do enriquecimento de tentativa já foi aplicada:
  - a narrativa incremental de:
    - status da tentativa
    - provider
    - referência externa
    - sessão de origem
    - último evento
  agora nasce em um helper próprio dentro de `account_customer_area_queries`
- leitura prática:
  - o `narrative block` agora já separa melhor:
    - base
    - pagamento
    - tentativa
    - confirmação
- a revisão seguinte mostrou que o **bloco de confirmação já está suficientemente separado**
- motivo:
  - `_build_order_detail_confirmation_payload(...)` já nasce isolado
  - ele entra por um gate explícito:
    - `confirmation_mode=True`
    - `result=checkout-completed`
  - ele já não compete mais com o narrative block principal
- leitura prática:
  - não parece haver um próximo corte urgente dentro da confirmação
  - o eixo narrativo do detalhe agora está estruturalmente bem organizado
- o último gap estrutural relevante em `accounts` estava nos writes de endereço:
  - `account_address_commands` ainda aceitava `tenant_id=None` como compatibilidade implícita
- esse hardening já foi aplicado:
  - create/edit/delete e leituras auxiliares de endereço agora exigem tenant resolvido
  - a UI deixa de reportar sucesso falso quando não houver contexto de loja válido
  - resultados explícitos de indisponibilidade passam a ser:
    - `address-create-unavailable`
    - `address-update-unavailable`
- leitura prática:
  - o eixo multi-tenant de `accounts` agora fica coerente entre:
    - reads tenant-aware
    - writes tenant-owned
    - customer area
    - account pages
    - address management

## Auditoria final do legado útil em `accounts`
- a auditoria ampla final mostra que o que ainda resta como legado em `accounts` já não parece risco estrutural multi-tenant
- o legado residual útil agora fica concentrado principalmente em **leituras globais deliberadas**, como:
  - `account_page_queries._overview_orders_context(...)`
    - mantém uma visão geral útil mesmo quando ainda não há histórico persistido suficiente
  - `account_page_queries._overview_reengagement_copy(...)`
    - preserva copy de continuidade para auth/overview sem exigir toda a trilha tenant-owned
  - `account_customer_area_queries`
    - `FallbackCustomerAreaRepository`
    - `FallbackAccountProfileRepository`
    - `_allow_fixture_fallback(...)`
    usados apenas quando **não há tenant resolvido**
- leitura prática:
  - esse residual hoje serve mais como:
    - compatibilidade global controlada
    - suporte a superfícies read-only
    - readiness de páginas sem contexto de loja
  - e menos como “atalho perigoso” entre tenants

## Classificação final
- **Já endurecido o suficiente**
  - `customer area` tenant-scoped
  - `account overview` tenant-aware
  - `account pages` sem perfil demo/global
  - `order detail` decomposto
  - `address commands` tenant-required para writes
  - writes de `checkout`, `orders` e `payments` tenant-owned
- **Legado útil que ainda vale manter**
  - fallbacks read-only sem tenant explícito em `account_page_queries`
  - fallback global controlado da `customer area` apenas para requests sem tenant resolvido
- **Não parece valer mais hardening agora**
  - perseguir remoção completa do modo global de leitura em `accounts`
  - porque o retorno estrutural ficou baixo perto do risco de mexer em compatibilidade deliberada

## Encerramento da trilha multi-tenant
- nesta fase do produto, a abordagem multi-tenant em `accounts` pode ser considerada **encerrada com sucesso**
- o que sobra agora é:
  - legado controlado de leitura global
  - e refinamento opcional de produto/UX
- não parece mais haver um próximo investimento de alto valor no eixo multi-tenant deste módulo

## Wave A — Customer Post-Purchase Experience Review
- a leitura atual do pós-compra mostra que a base funcional já está boa:
  - histórico de pedidos
  - detalhe do pedido
  - trilha de pagamento
  - guidance de recovery
  - reorder/retry
- o próximo ganho deixa de ser estrutural e passa a ser **clareza, confiança e valor percebido**

### Gaps mais importantes no detalhe do pedido
- **status ainda muito operacional**
  - o detalhe comunica bem o estado interno
  - mas ainda pode traduzir melhor:
    - o que aconteceu
    - o que acontece agora
    - o que o cliente precisa fazer, se algo for necessário
- **timeline ainda pouco orientada a marcos do cliente**
  - já existe boa trilha operacional
  - mas ainda faltam marcos mais fáceis de ler como jornada:
    - pedido recebido
    - pagamento aprovado
    - separação iniciada
    - envio iniciado
    - entrega concluída
- **pós-compra ainda pouco acionável do ponto de vista comercial**
  - `reorder lite` já ajuda
  - mas ainda há espaço para orientar melhor:
    - retorno ao catálogo
    - próxima ação sugerida
    - recompra depois da entrega
- **excesso de densidade informacional no detalhe**
  - hoje convivem na mesma página:
    - resumo
    - status
    - trilha operacional
    - alerts de recovery
    - timeline
    - actions
  - a base está correta, mas pode ficar mais fácil de escanear

### Prioridade recomendada
1. **Order Detail clarity**
2. **Customer-facing milestone language**
3. **Post-purchase next-step guidance**
4. **Retention/reorder polish**

### Próximo passo recomendado
- a próxima wave mais valiosa agora parece ser:
  - **Wave B — Order Detail Post-Purchase UX Review**
- foco:
  - clareza de status
  - próximo passo
  - confiança
  - retenção leve
  - linguagem mais orientada ao cliente

## Wave B — Order Detail Post-Purchase UX Review
- a revisão do `order detail` confirma que a página já está funcionalmente forte:
  - resumo principal
  - status atual
  - itens e totais
  - timeline
  - trilha de pagamento
  - guidance de recovery
- o maior ganho agora já não parece estrutural
- ele parece estar em **clareza, escaneabilidade e tradução da jornada para a linguagem do cliente**

### Leitura prática
- o detalhe hoje comunica bem o estado interno do pedido
- mas ainda existe uma mistura entre:
  - estado operacional
  - guidance transacional
  - narrativa de jornada do cliente
- isso torna a página correta, porém mais densa do que precisa no pós-compra

### Próximo passo recomendado
- a próxima wave mais valiosa depois dessa revisão passa a ser:
  - **Wave C — Order Detail Customer Milestone Review**
- foco:
  - revisar os marcos que o cliente enxerga no detalhe
  - distinguir melhor o que é milestone de jornada do que é telemetria operacional

## Wave C — Order Detail Customer Milestone Review
- a auditoria dos marcos atuais mostra que o `order detail` **já tem bons sinais de jornada**, mas eles ainda aparecem misturados com linguagem operacional demais

### Marcos que já existem de forma útil
- confirmação inicial do pedido:
  - `Pedido gerado com sucesso`
  - `Pedido iniciado com sucesso`
  - `Confirmação inicial do pedido`
- pagamento confirmado:
  - `Pagamento confirmado`
  - `pedido confirmado`
- preparação e envio:
  - `confirmação do envio`
  - `entrega preparando envio`
  - `acompanhe a entrega`
- fechamento da jornada:
  - `pedido concluído`
  - `Histórico salvo na sua conta`

### Gaps principais
- **marcos ainda aparecem mais como consequência de status do sistema do que como etapas claras da jornada**
  - hoje existe a mensagem certa, mas nem sempre a estrutura “o que aconteceu agora” fica evidente de primeira
- **payment trail e timeline ainda disputam atenção**
  - a página já mostra bem a parte operacional
  - mas o milestone do cliente às vezes perde protagonismo para a trilha técnica
- **faltam labels de jornada mais uniformes**
  - a linguagem atual alterna entre:
    - `pedido confirmado`
    - `pagamento confirmado`
    - `próximo passo esperado`
    - `histórico salvo`
  - todos funcionam, mas ainda não formam uma sequência de marcos tão consistente quanto poderiam
- **o detalhe já sugere o próximo passo, mas ainda não separa com total clareza milestone vs. guidance**
  - exemplo:
    - `Próximo passo esperado` ajuda bastante
    - porém continua convivendo com mensagens mais operacionais no mesmo nível

### Leitura objetiva
- o `order detail` já está perto de uma narrativa de pós-compra mais forte
- o que falta agora não parece ser:
  - nova capability
  - nova action
  - novo fluxo
- o que falta parece ser **uma camada mais consistente de milestone language**, algo como:
  - pedido recebido
  - pagamento aprovado
  - pedido em preparação
  - pedido enviado
  - pedido entregue

### Recomendação
- o próximo investimento de maior retorno agora parece ser:
  - **Wave D — Order Detail Milestone Language Plan**
- foco:
  - consolidar uma sequência curta e consistente de marcos do cliente
  - decidir onde esses marcos vivem:
    - summary
    - status card
    - timeline
  - manter a trilha operacional como apoio, sem competir com a jornada principal

## Wave D — Order Detail Milestone Language Plan
- o plano de milestone language para o `order detail` agora fica bem definido:
  - **não** criar novos fluxos
  - **não** mexer no contrato transacional
  - **sim** reorganizar a leitura da jornada do pedido com uma sequência curta, consistente e mais orientada ao cliente

### Sequência canônica recomendada
1. **Pedido recebido**
   - quando o checkout terminou e o pedido já foi registrado com segurança
2. **Pagamento aprovado**
   - quando o pagamento foi confirmado e o pedido segue para preparação
3. **Pedido em preparação**
   - quando a separação/preparação já começou
4. **Pedido enviado**
   - quando o envio foi confirmado ou a entrega está em trânsito
5. **Pedido entregue**
   - quando a jornada operacional principal foi concluída

### Casos especiais que ficam fora da sequência principal
- **Pagamento não concluído**
  - continua como guidance de recovery
  - não deve competir visualmente com milestone saudável
- **Pedido cancelado**
  - continua como fechamento alternativo de jornada
- **Confirmação inicial do checkout**
  - continua como handoff especial
  - pode ser apresentado como versão inicial de `Pedido recebido`, mas sem se misturar com evolução real do pagamento

### Distribuição recomendada na página
- **summary**
  - deve responder primeiro:
    - em que etapa da jornada este pedido está
  - aqui o milestone atual precisa ser mais evidente do que a telemetria operacional
- **status card**
  - continua mostrando:
    - pedido
    - pagamento
    - entrega
  - mas como apoio factual ao milestone principal
- **timeline**
  - deve contar a progressão dos marcos de jornada
  - `Próximo passo esperado` continua útil, mas como ponte entre milestones
- **trilha do pagamento**
  - continua separada
  - serve como apoio operacional, não como narrativa principal da jornada

### Tradução recomendada do estado atual para milestone
- `confirmation_mode`:
  - priorizar `Pedido recebido`
- `payment_status` confirmado / `order_status` pago:
  - priorizar `Pagamento aprovado`
- `shipping_status` em preparação / fulfillment em separação:
  - priorizar `Pedido em preparação`
- `shipping_status` enviado / em trânsito:
  - priorizar `Pedido enviado`
- `shipping_status` entregue:
  - priorizar `Pedido entregue`

### Leitura prática
- hoje o detalhe já possui quase todos os ingredientes necessários
- o trabalho seguinte parece ser mais de:
  - taxonomia de milestone
  - consistência de copy
  - hierarquia visual da mensagem
- e menos de nova regra funcional

### Recomendação
- o próximo passo mais valioso agora parece ser:
  - **Wave E — Order Detail Milestone Copy Execution Review**
- foco:
  - aplicar a sequência canônica nas superfícies certas
  - sem apagar a trilha operacional que já ajuda suporte e recovery

## Wave E — Order Detail Milestone Copy Execution Review
- a revisão de execução mostra que o próximo passo seguro **já pode começar por copy e hierarquia de leitura**, sem tocar no fluxo do pedido

### O que já parece seguro mudar agora
- **summary principal**
  - hoje:
    - `Resumo do pedido`
    - `summary_content` mais factual
  - direção:
    - usar o summary para reforçar o **milestone atual**
    - exemplo:
      - `Pedido recebido`
      - `Pagamento aprovado`
      - `Pedido em preparação`
      - `Pedido enviado`
      - `Pedido entregue`
- **status card title**
  - hoje:
    - `Status atual`
  - direção:
    - título mais orientado a jornada, sem perder a factualidade do bloco
- **timeline title e itens de jornada**
  - hoje:
    - `Linha do tempo`
    - `Próximo passo esperado`
    - `Histórico salvo na sua conta`
  - direção:
    - deixar a timeline mais claramente ligada à progressão da jornada
    - preservar `Próximo passo esperado`, mas como apoio ao milestone
- **confirmation handoff copy**
  - hoje:
    - `Pedido iniciado com sucesso`
    - `Confirmação inicial`
  - direção:
    - aproximar esse estado de `Pedido recebido`, sem fingir avanço do pagamento

### O que ainda não parece bom mudar nesta primeira passada
- **trilha do pagamento**
  - `Trilha do pagamento` ainda deve continuar com linguagem operacional
- **alerts de recovery**
  - `pending_recovery_*`
  - `order_pending_recovery_*`
  - continuam pertencendo a guidance transacional, não a milestone saudável
- **dispatch de actions**
  - `payment_retry`
  - `hosted_payment`
  - `confirm_payment`
  - ficam totalmente fora desta wave
- **copy que depende de tentativa operacional**
  - tudo que nasce diretamente de `payment_attempt_*`
  - continua como apoio operacional separado

### Recorte seguro recomendado
1. ajustar **summary titles/subtitles/notes** para refletirem milestone atual
2. ajustar **status card** para apoiar milestone com leitura factual
3. ajustar **timeline labels** para progressão mais orientada ao cliente
4. manter recovery, trilha de pagamento e actions exatamente onde estão

### Leitura prática
- esta já parece uma wave de execução pequena e segura
- porque mexe em:
  - linguagem
  - taxonomia de milestones
  - hierarquia de leitura
- e não mexe em:
  - tenant boundaries
  - transações
  - retry
  - hosted payment
  - recovery operacional

### Recomendação
- o próximo passo mais valioso agora parece ser:
  - **Wave F — Order Detail Milestone Copy Execution**
- foco:
  - aplicar a primeira passada de milestone language no summary, status card e timeline
  - mantendo payment trail e recovery como camadas separadas

## Wave F — Order Detail Milestone Copy Execution
- a primeira passada de milestone language já foi aplicada no `order detail`

### O que mudou
- **summary**
  - deixa de nascer com `Resumo do pedido`
  - passa a destacar o milestone atual da jornada
- **status card**
  - deixa de usar `Status atual`
  - passa a usar `Etapa atual do pedido`
- **timeline**
  - deixa de usar `Linha do tempo`
  - passa a usar `Marcos do pedido`
  - os primeiros itens reforçam melhor a jornada:
    - milestone atual
    - andamento de pagamento e entrega
    - próximo passo esperado
- **confirmation handoff**
  - a confirmação inicial do checkout aproxima a narrativa de `Pedido recebido`
  - sem fingir avanço real do pagamento

### O que continua separado
- `Trilha do pagamento`
- alerts de recovery
- actions transacionais
- copy operacional de `PaymentAttempt`

### Leitura prática
- o detalhe do pedido agora fica mais fácil de escanear do ponto de vista do cliente
- a jornada principal ganhou prioridade visual
- a camada operacional continua preservada para suporte, recovery e transparência

### Validação
- suíte de `accounts` verde após a mudança
- checks e schema também sem impacto

## Wave G — Orders List Continuity UX Review
- a revisão da lista de pedidos mostra que ela já está:
  - honesta
  - estável
  - coerente com o pós-compra
- mas ainda privilegia mais a ideia de **histórico salvo** do que a de **continuidade orientada ao próximo passo**

### O que já funciona bem
- a página deixa claro que:
  - os pedidos ficam salvos
  - o catálogo continua disponível
  - o cliente consegue retomar o acompanhamento
- cada linha já entrega:
  - número do pedido
  - resumo curto
  - hint de continuidade
  - atualização recente

### Gaps principais
- **a lista ainda ajuda mais a “revisar o passado” do que a “escolher o pedido certo agora”**
  - a linguagem atual puxa bastante:
    - histórico salvo
    - recompra
    - retorno ao catálogo
  - mas menos:
    - qual pedido merece atenção agora
    - qual pedido está mais perto do próximo marco importante
- **o status resumido ainda é mais factual do que orientado à continuidade**
  - `Pago · pagamento confirmado · entrega preparando envio`
  - isso é correto
  - mas ainda não destaca com tanta força o milestone principal da linha
- **o row hint ainda pode evoluir**
  - hoje temos hints como:
    - `histórico salvo`
    - `cliente recorrente`
    - `pedido mais recente`
    - `acompanhe a entrega`
  - eles funcionam, mas ainda não formam uma hierarquia tão clara de prioridade
- **a página ainda não destaca explicitamente um “pedido principal do momento”**
  - especialmente quando há mais de um pedido salvo

### Leitura objetiva
- o próximo ganho de produto na lista parece ser:
  - **continuity prioritization**
- menos foco em “todos os pedidos continuam aqui”
- mais foco em:
  - “qual pedido você provavelmente quer abrir agora”
  - “qual etapa principal cada pedido está vivendo”

### Recomendação
- o próximo passo mais valioso agora parece ser:
  - **Wave H — Orders List Continuity Prioritization Plan**
- foco:
  - revisar:
    - row summary
    - row hint
    - page description
    - ordering/prioridade visual do pedido mais relevante
  - sem mexer ainda em filtros, paginação ou estrutura da tabela

## Wave H — Orders List Continuity Prioritization Plan
- o plano de priorização da lista agora fica bem definido:
  - **não** refazer a tabela
  - **não** mexer em filtros ou paginação
  - **sim** melhorar a leitura de prioridade e continuidade por linha

### Estratégia recomendada
1. **destacar a etapa principal de cada pedido**
   - cada linha deve deixar mais visível o milestone principal do pedido
   - menos ênfase em resumo factual puro
   - mais ênfase em “em que etapa este pedido está agora”
2. **melhorar o `row_hint`**
   - o hint deve comunicar prioridade de atenção
   - exemplos desejados:
     - pedido em preparação
     - acompanhe a entrega
     - pedido entregue
     - pedido mais recente
   - menos foco em hints muito genéricos quando já houver um milestone mais útil
3. **elevar o pedido mais relevante do momento**
   - sem redesign pesado
   - mas com hierarquia mais clara do pedido:
     - mais recente
     - em andamento
     - com próximo passo mais importante
4. **preservar histórico e recompra como camada secundária**
   - histórico salvo continua importante
   - retorno ao catálogo continua útil
   - mas ambos devem apoiar a continuidade, não competir com ela

### Distribuição recomendada
- **page description**
  - deve orientar a leitura da lista como acompanhamento ativo, não só arquivo de compras
- **row summary**
  - deve reforçar o milestone principal
- **row hint**
  - deve ajudar o cliente a escolher o pedido certo para abrir
- **meta/recency**
  - continua útil para localizar o pedido mais recente, mas como apoio

### Leitura prática
- o próximo corte seguro na lista parece ser pequeno e bem valioso
- ele deve mexer principalmente em:
  - taxonomia de hint
  - linguagem de summary por linha
  - ênfase do pedido mais relevante

### Recomendação
- o próximo passo mais valioso agora parece ser:
  - **Wave I — Orders List Continuity Copy Review**
- foco:
  - revisar as cópias e hints da lista antes de executar a primeira passada real

## Wave I — Orders List Continuity Copy Review
- a revisão de copy da lista mostra que a próxima passada segura **já pode acontecer sem mexer em estrutura**

### O que já parece seguro mudar agora
- **page description**
  - hoje a página ainda fala mais de:
    - histórico de compras
    - consultas futuras
    - retorno ao catálogo
  - direção:
    - puxar mais a leitura de acompanhamento ativo
    - ajudar o cliente a entender que a lista serve para localizar rapidamente o pedido mais relevante do momento
- **table description**
  - hoje a ênfase está em:
    - histórico reunido
    - recompras
    - novos acompanhamentos
  - direção:
    - aproximar a descrição de uma lógica de prioridade:
      - localizar o pedido certo
      - entender a etapa atual
      - decidir qual detalhe abrir
- **row hint**
  - é hoje o melhor candidato de alto valor e baixo risco
  - direção:
    - reduzir hints genéricos quando houver um hint de milestone mais útil
    - priorizar sinais como:
      - pedido em preparação
      - acompanhe a entrega
      - pedido entregue
      - pedido mais recente
- **row summary/status summary**
  - hoje ainda tende a ficar em forma factual:
    - `Pago · pagamento confirmado · entrega preparando envio`
  - direção:
    - aproximar o resumo da etapa principal vivida pelo pedido

### O que ainda não parece bom mudar nesta primeira passada
- **ordenação da lista**
  - ainda vale preservar a ordenação atual nesta fase
- **filtros e paginação**
  - continuam fora de escopo
- **estrutura da tabela**
  - não precisa mudar ainda
- **ligação com detail/recovery**
  - o comportamento de navegação e continuidade segue como está

### Recorte seguro recomendado
1. ajustar `page_description`
2. ajustar `table_description`
3. melhorar a taxonomia de `row_hint`
4. revisar o resumo factual por linha para aproximar milestone e continuidade

### Leitura prática
- esta já parece uma wave de execução pequena e bem segura
- porque mexe em:
  - linguagem
  - prioridade percebida
  - leitura rápida da lista
- sem mexer em:
  - query behavior
  - navegação
  - filtros
  - paginação

### Recomendação
- o próximo passo mais valioso agora parece ser:
  - **Wave J — Orders List Continuity Copy Execution**
- foco:
  - aplicar a primeira passada real de copy na lista
  - com prioridade em `page_description`, `table_description`, `row_hint` e resumo por linha

## Wave J — Orders List Continuity Copy Execution
- a primeira passada real de copy na lista já foi aplicada

### O que mudou
- **page description**
  - agora puxa mais a leitura de acompanhamento ativo
  - menos foco em arquivo de compras
  - mais foco em localizar o pedido certo rapidamente
- **table description**
  - agora reforça melhor a ideia de etapa principal da jornada
  - e não só histórico/recompra
- **row hint**
  - passa a priorizar melhor sinais de milestone, como:
    - `pedido em preparação`
    - `acompanhe a entrega`
    - `pedido entregue`
- **row summary**
  - aproxima o resumo da etapa principal vivida pelo pedido
  - sem abandonar a factualidade de pagamento e entrega

### O que continua igual
- ordenação da lista
- filtros
- paginação
- estrutura da tabela
- navegação para o detalhe

### Leitura prática
- a lista agora ajuda melhor o cliente a perceber:
  - qual pedido merece atenção agora
  - em que etapa esse pedido está
- tudo isso sem abrir risco estrutural ou mudar a interação principal

### Validação
- suíte de `accounts` verde após a mudança
- checks e schema sem impacto

## Wave K — Account Overview Retention UX Review
- a revisão do `account overview` mostra que ele já é:
  - estável
  - coerente
  - útil como visão resumida da conta
- mas ainda entrega mais **readiness estrutural** do que **retention value**

### O que já funciona bem
- o overview reúne:
  - resumo da conta
  - pedidos recentes
  - atalhos
  - atividade recente
- ele já conecta:
  - identidade
  - histórico
  - retorno ao catálogo
  - quick links

### Gaps principais
- **o resumo ainda fala mais de “conta pronta” do que de “por que voltar agora”**
  - a copy atual comunica segurança e readiness
  - mas ainda menos:
    - qual valor imediato existe em voltar
    - o que merece atenção agora
- **pedidos recentes ainda aparecem mais como contexto do que como convite de continuidade**
  - a tabela recente ajuda
  - mas não parece ainda uma superfície tão orientada a ação quanto poderia
- **quick links ainda são úteis, mas pouco intencionais**
  - hoje funcionam como atalhos corretos
  - porém ainda podem vender melhor:
    - acompanhar pedido atual
    - revisar conta
    - voltar à loja
- **activity card ainda é mais informativo do que mobilizador**
  - ele resume bem
  - mas ainda pode reforçar melhor o “próximo retorno natural”

### Leitura objetiva
- o overview já está bom como:
  - painel resumido
  - continuidade básica
- o próximo ganho de produto parece ser:
  - **retention framing**
- menos “sua conta está pronta”
- mais:
  - “aqui está o melhor próximo ponto de retorno”

### Recomendação
- o próximo passo mais valioso agora parece ser:
  - **Wave L — Account Overview Retention Plan**
- foco:
  - revisar:
    - summary framing
    - orders recent framing
    - quick links intention
    - activity card role
  - sem mexer ainda na estrutura da página

## Wave L — Account Overview Retention Plan
- o plano de retenção do `account overview` deve seguir um recorte pequeno e bem seguro
- a direção não é redesenhar a página
- é **reposicionar a utilidade do overview como superfície de retorno**

### Estratégia definida
- **summary framing**
  - o resumo deve falar menos de “conta pronta”
  - e mais de:
    - onde está o melhor retorno agora
    - o que vale acompanhar
    - qual é a utilidade imediata da conta
- **recent orders framing**
  - o bloco de pedidos recentes deve reforçar:
    - etapa principal do pedido
    - continuidade mais natural
    - abertura rápida do pedido que mais importa agora
- **quick links intention**
  - os atalhos devem continuar simples
  - mas com framing mais intencional para:
    - acompanhar pedido
    - revisar conta
    - voltar à loja
- **activity card role**
  - a atividade recente deve deixar de soar apenas como histórico curto
  - e passar a reforçar:
    - próximo retorno natural
    - motivo simples para voltar

### O que fica fora desta etapa
- sem alterar:
  - layout
  - hierarquia visual estrutural
  - navegação
  - dados transacionais
  - fluxo de pedidos
- o foco é só:
  - framing
  - intenção
  - copy

### Ordem recomendada
1. revisar `summary_title`, `summary_subtitle` e `page_description`
2. revisar framing de `recent_orders`
3. revisar `quick_links_title`, `quick_links_subtitle` e intenção dos links
4. revisar papel do `activity card`

### Leitura prática
- o overview já está estável o suficiente para esse refinamento
- o próximo ganho de produto aqui parece claramente ser:
  - **retention copy**
- não:
  - refactor estrutural
  - mudança de interação
  - mudança de domínio

### Próxima wave
- **Wave M — Account Overview Retention Copy Review**
- foco:
  - revisar o melhor primeiro corte real de copy no overview
  - sem mudar ainda a estrutura da página

## Wave M — Account Overview Retention Copy Review
- a revisão da copy do `account overview` mostra que já existe um **primeiro corte seguro de execução**
- o melhor ponto de entrada não é mudar layout, blocos ou navegação
- é ajustar a linguagem das superfícies que ainda falam mais de **readiness** do que de **retorno útil**

### Candidatos mais seguros para a primeira passada
- **`page_description`**
  - hoje já resume bem a área
  - mas ainda pode falar menos de “dados e acessos rápidos”
  - e mais de:
    - acompanhar o que importa agora
    - voltar ao pedido certo
    - retomar a conta com contexto
- **`summary_subtitle`**
  - hoje ainda recai bastante em:
    - “conta pronta”
    - “acompanhamento simples”
  - o próximo passo seguro é aproximar isso de:
    - melhor ponto de atenção atual
    - motivo para voltar
- **`quick_links_subtitle`**
  - já tem boa função
  - mas ainda pode deixar mais claro:
    - por que acompanhar pedidos
    - por que revisar a conta
    - por que voltar à loja
- **`activity_subtitle`**
  - hoje ainda soa mais como readiness estrutural
  - é um bom candidato para virar framing de:
    - retorno natural
    - continuidade recente
    - utilidade imediata

### O que fica fora desta primeira passada
- sem alterar ainda:
  - `recent_orders` payload
  - ordem dos blocos
  - quick links em si
  - activity content detalhado
  - lógica de continuidade dos pedidos
- isso preserva:
  - estabilidade visual
  - continuidade funcional
  - risco baixo de regressão

### Leitura objetiva
- o `account overview` já tem um primeiro recorte muito parecido com o que fizemos em:
  - `order detail`
  - `orders list`
- primeiro copy e framing
- depois, se fizer sentido, ajustes mais finos de profundidade

### Próxima wave
- **Wave N — Account Overview Retention Copy Execution**
- foco:
  - aplicar a primeira passada real em:
    - `page_description`
    - `summary_subtitle`
    - `quick_links_subtitle`
    - `activity_subtitle`
  - sem mexer ainda na estrutura da página nem na lógica do overview

## Wave N — Account Overview Retention Copy Execution
- aplicamos a primeira passada real de **retention copy** no `account overview`
- a execução ficou restrita ao recorte mais seguro da wave:
  - `page_description`
  - `summary_subtitle`
  - `quick_links_subtitle`
  - `activity_subtitle`

### O que mudou
- o overview agora fala menos de:
  - “conta pronta”
  - “dados e acessos rápidos”
- e mais de:
  - ponto de retorno
  - pedido que merece atenção
  - retomada com contexto
- a copy de `summary_content` e `quick_links_content` também foi aproximada desse framing, sem mudar estrutura nem interação

### O que continua igual
- layout
- hierarquia visual
- navegação
- tabela de pedidos recentes
- quick links
- lógica de continuidade dos pedidos

### Leitura prática
- o overview agora fica mais coerente com a trilha já aplicada em:
  - `order detail`
  - `orders list`
- a página continua estável, mas comunica melhor:
  - por que vale voltar
  - o que merece atenção agora
  - como retomar a conta sem fricção

### Validação
- suíte de `accounts` cobre a nova linguagem do overview
- checks e schema sem impacto

### Próxima wave
- **Wave O — Account Overview Recent Orders Framing Review**
- foco:
  - revisar se o bloco de `recent_orders` já merece a próxima passada funcional
  - sem mexer ainda em estrutura, filtros ou navegação

## Wave O — Account Overview Recent Orders Framing Review
- a revisão do bloco de `recent_orders` mostra que ele já está:
  - estável
  - útil
  - coerente com o overview
- o próximo ganho aqui não parece estrutural
- parece ser **framing do bloco e da linha recente**

### O que já funciona bem
- a tabela recente já mostra:
  - número do pedido
  - estado atual
  - total
  - atualização recente
- o row payload já combina:
  - `order_status_label`
  - `recent_update_hint`
  - `reengagement_hint`

### Gap principal
- o bloco ainda comunica melhor:
  - **estado factual do pedido**
- do que:
  - **por que este pedido merece sua atenção agora**
- isso aparece especialmente na coluna `Status`, que já é útil, mas ainda não tem uma hierarquia tão clara entre:
  - etapa principal
  - atualização recente
  - hint de continuidade

### Leitura objetiva
- a tabela não precisa de:
  - redesign
  - filtros novos
  - mudança de navegação
- o melhor próximo passo parece ser:
  - revisar a taxonomia da linha recente
  - e o framing do bloco como superfície de continuidade

### Próxima wave
- **Wave P — Account Overview Recent Orders Framing Plan**
- foco:
  - decidir o menor recorte seguro para melhorar:
    - título/subtítulo do bloco
    - composição da célula de status
    - prioridade entre milestone, atualização e hint
  - sem alterar ainda a estrutura da tabela

## Wave P — Account Overview Recent Orders Framing Plan
- o plano para `recent_orders` deve continuar pequeno, seguro e totalmente compatível com a tabela atual
- a direção não é reestruturar o bloco
- é **melhorar a leitura de continuidade da superfície recente**

### Recorte seguro definido
1. **framing do bloco**
   - revisar primeiro:
     - `recent_orders_title`
     - eventual subtítulo/contexto do bloco quando isso já existir no payload
   - objetivo:
     - deixar mais explícito que este é o lugar para localizar rápido o pedido certo
2. **composição textual da célula de status**
   - manter a célula única
   - mas decidir ordem mais clara entre:
     - milestone principal
     - atualização recente
     - hint de continuidade
3. **prioridade da leitura**
   - a linha deve ser lida primeiro como:
     - etapa principal do pedido
   - depois como:
     - atualização recente
     - próximo contexto de retorno

### O que fica fora desta etapa
- sem alterar:
  - colunas
  - estrutura da tabela
  - navegação para o detalhe
  - filtros
  - paginação
  - payload transacional do pedido

### Leitura objetiva
- isso mantém `recent_orders` alinhado com o padrão já usado no roadmap:
  - primeiro framing
  - depois execução de copy
  - só mais tarde ajustes de profundidade, se ainda fizer sentido

### Próxima wave
- **Wave Q — Account Overview Recent Orders Copy Review**
- foco:
  - revisar o melhor primeiro corte real de copy no bloco recente
  - sem mudar ainda a estrutura da tabela

## Wave Q — Account Overview Recent Orders Copy Review
- a revisão de copy do bloco `recent_orders` mostra que já existe um **primeiro corte seguro de execução**
- o melhor ponto de entrada não é mexer nas colunas nem na navegação
- é melhorar a linguagem do bloco e a ordem de leitura da célula `Status`

### Candidatos mais seguros para a primeira passada
- **`recent_orders_title`**
  - hoje é funcional
  - mas ainda pode comunicar melhor que este é o lugar para:
    - localizar rápido o pedido certo
    - reencontrar a etapa atual
    - seguir para o detalhe com contexto
- **célula `Status`**
  - o melhor primeiro corte parece ser:
    - manter a célula única
    - mas reordenar a copy para que a leitura comece por:
      - milestone principal
      - atualização recente
      - hint de continuidade
- **coluna de data**
  - ainda pode continuar factual
  - não parece precisar de evolução nesta primeira passada

### O que fica fora desta etapa
- sem alterar ainda:
  - `recent_order_columns`
  - estrutura da tabela
  - ordenação
  - navegação para o detalhe
  - payload transacional do pedido

### Leitura objetiva
- o bloco recente já está pronto para uma wave de **copy execution**
- sem mexer cedo demais em estrutura ou profundidade de dados

### Próxima wave
- **Wave R — Account Overview Recent Orders Copy Execution**
- foco:
  - aplicar a primeira passada real em:
    - `recent_orders_title`
    - composição textual da célula `Status`
  - sem mudar ainda a tabela, as colunas ou a navegação

## Wave R — Account Overview Recent Orders Copy Execution
- aplicamos a primeira passada real de copy no bloco `recent_orders` do `account overview`
- a execução ficou restrita ao recorte mais seguro:
  - `recent_orders_title`
  - composição textual da célula `Status`

### O que mudou
- o bloco agora usa um título mais orientado à continuidade:
  - `Pedidos para acompanhar`
- a célula `Status` agora prioriza melhor a ordem de leitura:
  1. milestone/hint principal
  2. atualização recente
  3. estado factual

### O que continua igual
- colunas
- estrutura da tabela
- navegação para o detalhe
- ordenação
- payload transacional do pedido

### Leitura prática
- o bloco recente agora ajuda mais o cliente a responder:
  - qual pedido merece atenção
  - em que etapa ele está
  - qual é o contexto mais útil antes de abrir o detalhe
- tudo isso sem mudar a tabela nem a interação principal

### Validação
- suíte de `accounts` cobre o novo framing
- checks e schema sem impacto

### Próxima wave
- **Wave S — Account Overview Activity Card Retention Review**
- foco:
  - revisar se o `activity card` já merece a próxima passada funcional
  - mantendo a evolução do overview incremental e segura

## Wave S — Account Overview Activity Card Retention Review
- a revisão do `activity card` mostra que ele já está cumprindo um papel útil no `account overview`
- hoje ele funciona como:
  - resumo curto do pedido mais recente
  - apoio de continuidade
  - reforço do próximo passo

### O que já funciona bem
- o card já reúne numa única superfície:
  - estado atual do pedido mais recente
  - atualização recente
  - próximo passo esperado
  - contexto de continuidade
- isso ajuda a conta a terminar com uma leitura de:
  - “o que aconteceu”
  - “o que acontece agora”

### Gap principal
- o card ainda comunica melhor:
  - **resumo operacional recente**
- do que:
  - **motivo claro para voltar depois**
- a copy já está boa, mas ainda pode ficar mais orientada a:
  - retorno natural
  - acompanhamento futuro
  - utilidade prática do próximo acesso

### Leitura objetiva
- o `activity card` não parece pedir:
  - mudança estrutural
  - novo bloco
  - nova interação
- o próximo ganho aqui parece ser:
  - **copy de retenção do próprio card**

### Próxima wave
- **Wave T — Account Overview Activity Card Copy Plan**
- foco:
  - decidir o menor recorte seguro para melhorar:
    - `activity_title`
    - `activity_subtitle`
    - framing de `activity_content`
  - sem mudar ainda a estrutura do card

## Wave T — Account Overview Activity Card Copy Plan
- o plano do `activity card` deve continuar pequeno, seguro e totalmente compatível com o overview atual
- a direção não é mudar o card
- é **reposicionar a leitura do card como motivo de retorno**

### Recorte seguro definido
1. **framing do card**
   - revisar primeiro:
     - `activity_title`
     - `activity_subtitle`
   - objetivo:
     - deixar mais explícito que o card ajuda a entender
       - o que vale acompanhar
       - quando voltar
       - por que a conta segue útil
2. **framing de `activity_content`**
   - manter a base factual
   - mas decidir ordem mais clara entre:
     - estado mais relevante
     - próximo passo
     - contexto de continuidade
3. **prioridade da leitura**
   - o card deve ser lido primeiro como:
     - próximo ponto de retorno
   - e depois como:
     - resumo recente do pedido

### O que fica fora desta etapa
- sem alterar:
  - estrutura do card
  - ordem da página
  - origem dos dados
  - lógica de continuidade
  - navegação

### Leitura objetiva
- isso mantém o `activity card` no mesmo padrão usado no restante do overview:
  - primeiro framing
  - depois execução de copy
  - só mais tarde ajustes de profundidade, se ainda fizer sentido

### Próxima wave
- **Wave U — Account Overview Activity Card Copy Review**
- foco:
  - revisar o melhor primeiro corte real de copy no `activity card`
  - sem mudar ainda a estrutura do card

## Wave U — Account Overview Activity Card Copy Review
- a revisão de copy do `activity card` mostra que já existe um **primeiro corte seguro de execução**
- o melhor ponto de entrada não é mexer na estrutura do card
- é melhorar a linguagem da superfície para reforçar:
  - motivo de retorno
  - próximo acompanhamento
  - utilidade do próximo acesso

### Candidatos mais seguros para a primeira passada
- **`activity_title`**
  - hoje é funcional
  - mas ainda pode comunicar melhor a ideia de:
    - acompanhamento
    - próximo retorno
    - continuidade recente
- **`activity_subtitle`**
  - já aponta o valor do card
  - mas ainda pode ficar mais claro em torno de:
    - o que vale acompanhar
    - por que voltar depois
- **framing de `activity_content`**
  - a melhor primeira passada parece ser:
    - manter a base factual
    - mas aproximar a abertura do texto de:
      - próximo ponto de atenção
      - retorno natural
      - acompanhamento útil

### O que fica fora desta etapa
- sem alterar ainda:
  - estrutura do card
  - ordem da página
  - origem dos dados
  - lógica de continuidade
  - demais blocos do overview

### Leitura objetiva
- o `activity card` já está pronto para uma wave pequena de **copy execution**
- sem mexer cedo demais em estrutura, dados ou fluxo

### Próxima wave
- **Wave V — Account Overview Activity Card Copy Execution**
- foco:
  - aplicar a primeira passada real em:
    - `activity_title`
    - `activity_subtitle`
    - framing de `activity_content`
  - sem mudar ainda a estrutura do card

## Wave V — Account Overview Activity Card Copy Execution
- aplicamos a primeira passada real de copy no `activity card` do `account overview`
- a execução ficou restrita ao recorte mais seguro:
  - `activity_title`
  - `activity_subtitle`
  - framing de `activity_content`

### O que mudou
- o card agora usa um título mais orientado à continuidade:
  - `O que acompanhar agora`
- o subtítulo passa a reforçar:
  - melhor próximo retorno
  - utilidade do próximo acesso
- o conteúdo abre menos como resumo operacional puro
- e mais como:
  - melhor acompanhamento atual
  - próximo contexto útil da conta

### O que continua igual
- estrutura do card
- ordem da página
- origem dos dados
- lógica de continuidade

### Leitura prática
- o `activity card` agora ajuda mais o cliente a responder:
  - por que vale voltar
  - o que acompanhar agora
  - qual é o melhor próximo retorno dentro da conta
- tudo isso sem mudar a estrutura do overview

### Validação
- suíte de `accounts` cobre o novo framing
- checks e schema sem impacto

### Próxima wave
- **Wave W — Account Overview Retention Wrap-Up Review**
- foco:
  - revisar o overview como um todo depois dessas waves
  - decidir se ainda existe algum ajuste funcional pequeno antes de sair desse eixo

## Wave W — Account Overview Retention Wrap-Up Review
- a revisão final do `account overview` mostra que a superfície já avançou bem nesse eixo de produto
- hoje o overview já comunica melhor:
  - por que vale voltar
  - qual pedido merece atenção
  - qual é o melhor próximo retorno dentro da conta

### O que ficou mais forte
- **summary**
  - agora enquadra a conta como ponto de retorno, não só como readiness
- **recent orders**
  - agora ajuda a localizar mais rápido o pedido certo e a etapa principal
- **quick links**
  - agora reforçam melhor a utilidade prática da conta
- **activity card**
  - agora fecha a página como superfície de acompanhamento, não só de histórico recente

### O que ainda pode evoluir no futuro
- pequenos refinamentos de:
  - profundidade do `activity_content`
  - subtítulo contextual do bloco de pedidos recentes
  - eventual hierarquia visual mais forte entre blocos
- mas isso já não parece urgente neste momento

### Leitura objetiva
- eu não vejo mais um gap funcional pequeno e óbvio que justifique continuar insistindo neste mesmo eixo agora
- o `account overview` parece:
  - coerente
  - mais útil
  - mais orientado a retenção
- sem ter perdido estabilidade estrutural

### Decisão prática
- este eixo do `account overview` pode ser considerado **encerrado com sucesso nesta fase**
- o próximo passo mais honesto agora é sair do overview e voltar ao roadmap funcional mais amplo

### Próxima wave
- **Wave X — Customer Area Product Value Review**
- foco:
  - revisar a área do cliente como produto de retenção como um todo
  - depois do ganho já consolidado em:
    - `order detail`
    - `orders list`
    - `account overview`

## Wave X — Customer Area Product Value Review
- a revisão ampla da `customer area` mostra que ela já deixou de ser só uma área “funcional”
- hoje ela já atua melhor como:
  - superfície de acompanhamento
  - ponto de continuidade
  - mecanismo leve de retenção

### O que ficou mais forte como produto
- **`order detail`**
  - agora funciona como a superfície mais rica de pós-compra
  - combina:
    - marco atual
    - próximos passos
    - continuidade de pagamento
    - recompra leve
- **`orders list`**
  - agora ajuda melhor a localizar:
    - pedido certo
    - etapa atual
    - continuidade mais relevante
- **`account overview`**
  - agora amarra a experiência:
    - retorno útil
    - quick access
    - pedido que merece atenção
    - melhor próximo acompanhamento

### Valor percebido atual
- a `customer area` já consegue responder melhor:
  - “onde eu acompanho meu pedido?”
  - “o que acontece agora?”
  - “por que vale voltar aqui depois?”
- isso é um salto importante de produto, não só de copy

### Gaps restantes
- eu não vejo agora um gap pequeno e óbvio no mesmo eixo de retenção imediata
- o que sobra parece mais futuro do que urgente:
  - recomendações de recompra mais fortes
  - sinais mais ricos de valor no perfil/endereços
  - integração mais forte entre histórico e descoberta

### Leitura objetiva
- a `customer area` nesta fase já está:
  - mais clara
  - mais útil
  - mais coerente como produto de retenção
- sem ter perdido previsibilidade estrutural

### Decisão prática
- este eixo de **pós-compra + retenção leve da customer area** pode ser considerado **encerrado com sucesso nesta fase**
- o próximo passo mais honesto agora é voltar ao roadmap funcional mais amplo

### Próxima wave
- **Wave Y — Catalog Conversion Review**
- foco:
  - sair do pós-compra e revisar o próximo eixo de valor percebido no produto:
    - descoberta
    - merchandising
    - clareza comercial
    - apoio à conversão no catálogo/PDP

## Wave Y — Catalog Conversion Review
- a revisão do eixo `catalog` / `PDP` mostra que a base comercial já está bem mais madura do que no início do projeto
- hoje o storefront já comunica melhor:
  - variante efetiva
  - preço real
  - disponibilidade
  - confiança para avançar ao checkout

### O que já está forte
- **vitrine**
  - os cards já carregam:
    - contexto comercial da combinação em destaque
    - disponibilidade curta
    - helper de clique
    - curadoria leve
- **PDP**
  - o detalhe já aprofunda bem:
    - variante efetiva
    - preço e compare price
    - disponibilidade
    - CTA e próximo passo
    - continuidade até checkout/cart
- **discovery**
  - quick filters, recortes e estados vazios já ajudam mais a descoberta do que antes

### Gaps mais relevantes agora
- **1. merchandising ainda é leve**
  - a vitrine já é honesta e coerente
  - mas ainda pode ficar mais forte em:
    - destaque comercial
    - storytelling curto por coleção/categoria
    - razão clara para abrir determinado produto agora
- **2. PDP ainda é mais seguro do que persuasivo**
  - ele comunica bem disponibilidade e checkout
  - mas ainda pode evoluir em:
    - desejo
    - contexto de uso
    - reforço comercial da variante escolhida
- **3. descoberta ainda parece mais funcional do que orientada a decisão**
  - quick filters ajudam
  - porém a vitrine ainda pode reforçar melhor:
    - caminhos de entrada
    - diferenciação entre recortes
    - priorização de decisão

### Leitura objetiva
- eu não vejo agora um gap crítico de arquitetura ou fluxo neste eixo
- o próximo ganho aqui parece claramente de:
  - **valor percebido**
  - **clareza comercial**
  - **apoio à conversão**

### Decisão prática
- o próximo passo mais valioso não parece ser mexer em checkout nem payment agora
- parece ser aprofundar o `catalog` / `PDP` como superfície de conversão

### Próxima wave
- **Wave Z — PDP Conversion Confidence Review**
- foco:
  - revisar o detalhe do produto como principal superfície de conversão antes da compra
  - decidir qual é o menor próximo passo funcional com maior retorno

## Wave ZA — Customer Area Post-Purchase Activation Review
- depois do pacote operacional de `customers`, a customer area passa a ter um sinal interno melhor para decidir se a experiência pós-compra está apoiada em dados reais suficientemente confiáveis
- o módulo responsável continua sendo `accounts`, mas o sinal vem de `customers.application.customer_data_issues`
- a fronteira fica preservada:
  - `customers` detecta issues de dados
  - `accounts` apenas consome a leitura como visibility operacional
  - nenhuma correção automática é feita na customer area

### Contrato multi-tenant
- a leitura usa o `tenant_id` já resolvido na request
- quando existe `AccountProfile.customer`, a visibility avalia apenas issues daquele customer no tenant atual
- quando não existe customer explícito, o modo permanece `missing`

### Sinais adicionados
- `customer_data_mode`
  - `ready`
  - `needs_attention`
  - `missing`
- `customer_data_issue_codes`
  - lista compacta dos códigos operacionais já emitidos por `customers`

### Leitura prática
- a customer area agora consegue distinguir:
  - perfil/customer explícito e saudável
  - perfil/customer explícito, mas com dados que ainda exigem atenção
  - ausência de vínculo explícito
- isso prepara ativações futuras de pós-compra sem depender só de presença visual de pedidos/endereço

### Próxima wave
- **Wave ZB — Customer Area Activation Wrap-Up Review**
- foco:
  - confirmar se o eixo de activation já tem sinais suficientes
  - decidir se o próximo ciclo deve voltar para conversão de catálogo/PDP ou seguir para backfill operacional

## Wave ZB — Customer Area Activation Wrap-Up Review
- a customer area já possui sinais suficientes para separar experiência visual de readiness operacional
- agora a área consegue distinguir:
  - profile/customer ausente
  - vínculo explícito pronto
  - dados do customer que ainda exigem atenção
  - pedidos ainda dependentes de fallback por e-mail
- decisão objetiva:
  - não bloquear a experiência pós-compra por esses sinais nesta fase
  - usar os sinais para orientar backfill e triagem por tenant
- o próximo ciclo natural deve seguir para **backfill operacional**, porque `order_email_fallback` agora é mensurável e já existe comando de correção segura

## Wave ZC — Customer Link Backfill Operational Hardening
- o comando `backfill_customer_links` foi endurecido para operar com recortes menores e mais auditáveis
- novo escopo:
  - `--tenant-id <tenant_id>`
  - mantém compatibilidade global quando omitido, mas o uso operacional recomendado passa a ser tenant-scoped
- novo recorte:
  - `--only all`
  - `--only profiles`
  - `--only orders`
- novo resumo residual:
  - `order_email_fallback_remaining`
- isso conecta o comando ao sinal operacional de `customers`, permitindo medir se o backfill reduziu o problema que aparece em `hubx_customer_data_issue_total{issue="order_email_fallback"}`

### Leitura prática
- o fluxo seguro agora fica:
  1. rodar `list_customer_data_issues --tenant-id <tenant_id> --issue order_email_fallback`
  2. rodar `backfill_customer_links --tenant-id <tenant_id> --only orders --dry-run`
  3. aplicar `backfill_customer_links --tenant-id <tenant_id> --only orders`
  4. validar `order_email_fallback_remaining=0` ou revisar os casos que permanecerem

### Próxima wave
- **Wave ZD — Customer Backfill Operational Wrap-Up Review**
- foco:
  - decidir se o backfill operacional já está seguro o suficiente para virar runbook de ativação por tenant
  - ou se ainda falta relatório mais detalhado de casos skipped

## Wave ZD — Customer Backfill Operational Wrap-Up Review
- a revisão mostrou que o backfill já estava seguro no critério de match:
  - mesmo tenant
  - e-mail case-insensitive
  - exatamente um `Customer`
- porém o resumo ainda era agregado demais para operação por tenant
- decisão objetiva:
  - antes de promover isso como rotina operacional, vale separar os motivos de skip
  - assim suporte/ops sabe se precisa criar customer, corrigir e-mail ou resolver duplicidade

## Wave ZE — Customer Backfill Skipped Reason Execution
- o comando `backfill_customer_links` agora detalha skips por motivo
- novos campos de resumo:
  - `profiles_skipped_missing_email`
  - `profiles_skipped_no_match`
  - `profiles_skipped_ambiguous`
  - `orders_skipped_missing_email`
  - `orders_skipped_no_match`
  - `orders_skipped_ambiguous`
- o contador agregado `profiles_skipped` e `orders_skipped` continua existindo para compatibilidade
- isso transforma o comando em uma ferramenta melhor de triagem, não apenas de aplicação

### Decisão prática
- o backfill operacional tenant-scoped está pronto para runbook nesta fase
- o fluxo recomendado passa a ser:
  - dry-run por tenant
  - revisar skipped reasons
  - aplicar recorte `--only` apropriado
  - validar `order_email_fallback_remaining`

### Próxima abordagem eleita
- **Catalog Merchandising Operational Review**
- motivo:
  - o eixo pós-compra/customer data/backfill ficou observável e operável
  - o próximo ganho funcional natural volta para antes da compra: catálogo, vitrine e decisão comercial
## Owner/Admin Identity Implementation
- `OwnerUser` passa a existir como identidade administrativa explícita por tenant
- a entidade é separada de `Customer` e de `AccountProfile`
- esse contrato desbloqueia notificações owner-facing sem reaproveitar perfil de conta/customer como fallback

### Regras
- e-mail único por tenant
- owner deve estar ativo para usos operacionais futuros
- `receives_notifications` controla elegibilidade inicial para notificações administrativas

## Wave DG — Owner Admin Services Execution
- foram criados services administrativos mínimos para owners.
- a leitura e a ação são tenant-scoped.

### Escopo
- `admin_owner_queries`
- `admin_owner_commands`
- listagem de owners por tenant
- toggle de `receives_notifications`

## Wave DH — Owner Admin Views Execution
- foi criada surface operacional mínima para owners administrativos.
- a rota `/ops/owners/` lista owners do tenant atual.
- cada owner pode ter notificações administrativas ativadas/desativadas.

### Escopo
- `accounts.interfaces.owner_urls`
- `accounts.interfaces.owner_views`
- rota `ops/owners`
- testes de listagem e toggle
## Wave EL — Customer Tracking Surface Execution
- o detalhe do pedido na área do cliente agora consome tracking normalizado do módulo `shipping`.
- quando há shipment com rastreio, a copy customer-facing mostra transportadora e código.
- quando não há shipment, o fallback textual existente permanece seguro.

### Boundary
- accounts não lê provider externo diretamente.
- accounts usa o gateway manual de shipping como contrato inicial de tracking.

## Wave EM — Customer Tracking Link UX Execution
- quando `tracking_url` existe, o detalhe do pedido exibe CTA `Acompanhar entrega`.
- o link externo abre em nova aba com `noopener noreferrer`.

## Wave AMO-A — Admin Merchant Operations Review
- a próxima evolução de produto não deve começar por mais uma micro-otimização de checkout/payments.
- a lacuna operacional mais transversal é o lojista não ter uma raiz clara em `/ops/` para responder: “onde devo agir agora?”.
- módulo responsável:
  - `accounts`, como shell administrativo/owner-facing.
- módulos consumidos:
  - `orders`
  - `catalog`
  - `customers`
  - `shipping`
  - `accounts/owners`
- decisão:
  - começar por um cockpit de leitura, sem criar workflow novo e sem escrever dados.
  - manter cada sinal derivado dos application services já existentes.
  - preservar o contrato multi-tenant usando `tenant_id` resolvido pela request.

## Wave AMO-B — Merchant Operations Dashboard Execution
- foi criada a rota `/ops/` como cockpit operacional inicial do lojista.
- a página consolida:
  - pedidos pendentes
  - exceções de estoque abertas/em revisão
  - produtos ativos e estoque sensível
  - clientes em atenção
  - entregas sem rastreio operacional
  - owners inativos ou com notificações pausadas
- o dashboard apenas aponta para superfícies existentes:
  - `/ops/orders/`
  - `/ops/catalog/products/`
  - `/ops/customers/`
  - `/ops/shipping/`
  - `/ops/owners/`
- nenhum evento novo foi introduzido nesta wave.
- nenhum dado customer/store-owned é lido sem `tenant_id` quando o tenant está resolvido.

## Wave AMO-C — Admin Dashboard Template Hardening
- ao ativar o template `admin_dashboard_page`, foi identificado que alguns includes estavam escritos em formato multilinha não renderizado pelo Django Template Language.

## Coupon Admin Lite Review
- a próxima surface operacional de cupons deve seguir o padrão `/ops/`.
- `accounts` continua como shell/cockpit, mas a listagem/criação pertence ao módulo `coupons`.
- a rota esperada para navegação operacional é `/ops/coupons/`.
- o dashboard pode adicionar link para cupons quando a surface existir, sem incorporar regra promocional em `accounts`.

## Coupon Admin Lite Execution
- o cockpit `/ops/` passou a apontar para `/ops/coupons/`.
- `accounts` apenas fornece navegação; listagem e criação ficam no módulo `coupons`.

## Cart Foundation Wave 22 — Coupon Customer Visibility Review
- a área do cliente deve mostrar cupom aplicado no detalhe do pedido.
- origem dos dados: snapshot em `Order`.
- regra: exibir apenas quando `coupon_code` existe, `discount_total > 0` e `promotion_snapshot` não está vazio.
- não consultar `coupons` a partir de `accounts`.
- o template e o componente de tabela foram ajustados para renderizar os includes reais.
- esse ajuste transforma a página de showcase em superfície reutilizável para dashboards operacionais reais.

## Cart Foundation Wave 23 — Coupon Customer Visibility Execution
- a área do cliente agora expõe um bloco derivado de cupom aplicado no detalhe do pedido.
- origem dos dados: `Order.coupon_code`, `Order.discount_total`, `Order.promotion_snapshot`.
- visibilidade: somente quando existe cupom, desconto real e snapshot promocional não vazio.
- copy: “Cupom aplicado: CODE” e “Desconto preservado no pedido: -R$ X,XX.”.
- fronteira preservada: `accounts` não chama `coupons` e não recalcula desconto.
- essa superfície é tenant-scoped porque reaproveita a resolução de pedido já filtrada pelo tenant/request.

## Platform Owner Login Execution Review
- `/accounts/login/` passa a autenticar owners/admins reais para superfícies `/ops/`.
- o login usa autenticação Django e exige `OwnerUser` ativo no tenant resolvido por subdomínio.
- o identificador aceito é e-mail ou username do `User`; o vínculo administrativo continua sendo `OwnerUser.email`.
- sucesso cria sessão Django e respeita `next` apenas quando o destino é seguro para o mesmo host.
- falha retorna mensagem genérica para evitar enumeração de usuário, owner ou tenant.
- `/accounts/logout/` encerra a sessão e registra saída quando há owner ativo tenant-scoped.

### Boundary
- `accounts.application.owner_login_commands` contém a regra de autenticação owner.
- `accounts.interfaces.views.LoginView` permanece adaptador HTTP fino.
- storefront/customer login continua fora desta execução.
- nenhuma regra de domínio de catálogo, pedido, pagamento ou customer é alterada.

### Auditoria
- `owner.login` registra entrada owner/admin.
- `owner.logout` registra saída quando a sessão está vinculada a owner ativo do tenant.

## Platform Ops Gate Activation Runbook Review
- a ativação de `HUBX_OPS_AUTH_GATE_ENFORCED=1` agora possui um comando de readiness.
- o comando valida tenants ativos antes do rollout do gate `/ops/`.
- a checagem considera bloqueante:
  - tenant ativo sem owner ativo;
  - owner ativo sem `User` Django correspondente;
  - `User` Django inativo;
  - e-mail de owner com múltiplos `User` Django.

### Comando
- executar `python manage.py ops_auth_gate_readiness` para relatório informativo.
- executar `python manage.py ops_auth_gate_readiness --fail-on-blockers` em CI/preflight.
- usar `--tenant-id=<id>` para validar um tenant específico antes de ativação gradual.

### Rollout
1. criar/validar pelo menos um `OwnerUser` ativo por tenant operacional;
2. garantir `User` Django ativo com o mesmo e-mail;
3. executar o comando de readiness sem blockers;
4. ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
5. testar `/accounts/login/?next=/ops/` e acesso a `/ops/`;
6. em rollback, retornar `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

## Platform Owner Invitation & Password Recovery Review
- owners administrativos agora têm um caminho mínimo de convite e recuperação de senha.
- a action `/ops/owners/<id>/actions/invite/` cria ou reaproveita `User` Django ativo para o `OwnerUser`.
- o convite gera token de reset usando o mecanismo padrão do Django.
- `/accounts/forgot-password/` solicita reset owner/admin de forma genérica para evitar enumeração.
- `/accounts/reset-password/<uidb64>/<token>/` conclui a redefinição quando o token é válido e o owner pertence ao tenant atual.

### Segurança e tenant
- convite exige permissão `owners.manage`.
- reset exige `OwnerUser` ativo no tenant resolvido por subdomínio.
- e-mail duplicado em `User` bloqueia convite.
- usuário Django inativo bloqueia convite e reset.
- resposta de forgot password não revela se owner/user existe.

### Auditoria
- `owner.invited` registra geração de convite.
- `owner.password_reset_requested` registra solicitação válida de reset.
- `owner.password_reset_completed` registra conclusão de redefinição.

### Fora de escopo
- envio de e-mail real.
- template transacional de convite.
- expiração customizada de token além do padrão Django.
- MFA/SSO.

## Platform Owner Email Delivery Review
- convite e reset owner/admin agora registram `EmailLog` planejado via módulo `notifications`.
- `accounts` continua dono do fluxo de acesso, token e auditoria de owner.
- `notifications` passa a ser dono da mensagem e do pipeline de entrega.
- o link de reset é colocado na descrição do `EmailLog`, evitando criar CTA customizado antes da decisão de URL pública/canonical.

### Integração
- `owner.invited` cria log `owner.access.invite`.
- `owner.password_reset_requested` cria log `owner.access.password_reset`.
- os logs permanecem `planned` e seguem o processamento existente:
  - `process_email_logs`;
  - Celery `notifications.process_email_log`;
  - dry-run por `NOTIFICATIONS_EMAIL_DRY_RUN`.

### Boundary
- `accounts.application.owner_access_recovery_commands` apenas chama `notifications.application.owner_access_email_commands`.
- `accounts` não usa `send_mail`, SMTP ou provider.
- `notifications` não decide permissão owner nem valida tenant de reset.

## Platform Owner Access Closure Review
- o pacote técnico de owner access está completo para ativação controlada por ambiente.
- o gate `/ops/`, login/logout, owner context, readiness, convite, reset e delivery via `EmailLog` estão integrados.
- a decisão de produção depende de dados operacionais por tenant, não de nova feature estrutural.

### Status técnico
- **Go** para staging com tenants preparados.
- **No-Go** para ambientes/tenants sem `OwnerUser` ativo e `User` Django correspondente.

### Checklist antes de ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1`
1. criar pelo menos um `OwnerUser` ativo por tenant operacional;
2. gerar convite em `/ops/owners/` ou criar `User` Django correspondente;
3. executar `python manage.py ops_auth_gate_readiness --fail-on-blockers`;
4. confirmar que `EmailLog` de convite/reset foi processado ou entregue;
5. validar login real em `/accounts/login/?next=/ops/`;
6. ativar o gate e manter rollback com `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

### Riscos restantes
- envio real depende de configuração `DEFAULT_FROM_EMAIL` e `NOTIFICATIONS_EMAIL_DRY_RUN=0`.
- não há MFA/SSO.
- não há tela específica para reenviar/processar convite individual; operação usa pipeline de notifications.
- tenants sem owner ativo continuam bloqueando readiness.

## Platform Initial Owner Provisioning Review
- existe um comando operacional para provisionar o primeiro owner/user administrativo de um tenant.
- o comando é tenant-scoped, idempotente e auditável.
- ele não cria cadastro público nem bypass permanente de autenticação.

### Comando
- dry-run:
  - `python manage.py provision_initial_owner --tenant-id=<tenant_id> --email=<owner@email> --dry-run`
- aplicação:
  - `python manage.py provision_initial_owner --tenant-id=<tenant_id> --email=<owner@email> --full-name="Nome" --role=owner`
- validação posterior:
  - `python manage.py ops_auth_gate_readiness --tenant-id=<tenant_id> --fail-on-blockers`

### Regras
- tenant deve estar ativo.
- e-mail deve ser válido.
- role inicial aceita apenas `owner` ou `admin`.
- se `OwnerUser` já existir, ele é reativado e normalizado para readiness quando seguro.
- se `User` Django não existir, é criado com senha inutilizável para exigir convite/reset.
- se houver múltiplos `User` Django com o mesmo e-mail, o comando bloqueia.
- se `User` Django existente estiver inativo, o comando bloqueia.

### Auditoria
- registra `owner.initial_provisioned` em `AuditLog`.
- metadata inclui se owner/user foram criados e o `user_id`.

### Fluxo recomendado
1. executar dry-run;
2. aplicar provisionamento;
3. gerar convite/reset;
4. processar `EmailLog` se necessário;
5. rodar readiness;
6. ativar gate apenas se readiness passar.

## Platform Ops Gate Staging Activation Review
- existe um preflight operacional para validar ativação do gate `/ops/` em staging.
- o preflight combina:
  - readiness de owner/user por tenant;
  - estado atual de `HUBX_OPS_AUTH_GATE_ENFORCED`;
  - readiness opcional do provider de e-mail.

### Comando
- antes de ativar:
  - `python manage.py ops_gate_activation_preflight --tenant-id=<tenant_id> --expect-gate=disabled --fail-on-blockers`
- se staging exigir envio real de convite/reset:
  - `python manage.py ops_gate_activation_preflight --tenant-id=<tenant_id> --expect-gate=disabled --require-email-delivery --fail-on-blockers`
- depois de ativar:
  - `python manage.py ops_gate_activation_preflight --tenant-id=<tenant_id> --expect-gate=enabled --fail-on-blockers`

### Runbook staging
1. provisionar owner inicial com `provision_initial_owner`;
2. gerar convite/reset para o owner;
3. processar logs de e-mail se o ambiente não estiver em dry-run;
4. validar `ops_gate_activation_preflight --expect-gate=disabled`;
5. configurar `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
6. reiniciar/redeployar o ambiente;
7. validar `ops_gate_activation_preflight --expect-gate=enabled`;
8. testar login em `/accounts/login/?next=/ops/`;
9. testar acesso negado para usuário autenticado sem owner;
10. rollback: retornar `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

### Critério de Go/No-Go
- Go: preflight sem blockers antes e depois da ativação.
- No-Go: readiness bloqueado, gate em estado inesperado ou provider de e-mail não pronto quando entrega real for exigida.

## Platform Ops Gate Production Rollout Review
- produção passa a ter comando de evidência Go/No-Go para rollout do gate `/ops/`.
- o comando não altera env, não executa deploy e não ativa o gate.
- ele consolida:
  - estado esperado do gate;
  - readiness owner/user;
  - provider de e-mail;
  - saúde de `EmailLog` por tenant.

### Comando
- evidência padrão pós-switch:
  - `python manage.py ops_gate_production_rollout --tenant-id=<tenant_id> --fail-on-blockers`
- evidência pré-switch:
  - `python manage.py ops_gate_production_rollout --tenant-id=<tenant_id> --expect-gate=disabled --fail-on-blockers`
- permitir dry-run de e-mail em rollout técnico:
  - `python manage.py ops_gate_production_rollout --tenant-id=<tenant_id> --allow-email-dry-run --fail-on-blockers`

### Critérios padrão
- gate deve estar enabled.
- owner readiness deve passar.
- provider de e-mail real deve estar pronto.
- `EmailLog failed` bloqueia rollout.
- `EmailLog planned/requested` é informado; pode bloquear com `--block-on-pending-delivery`.

### Runbook produção
1. escolher tenant e janela de ativação;
2. provisionar owner inicial, se necessário;
3. gerar/processar convite ou reset;
4. rodar evidência pré-switch com `--expect-gate=disabled`;
5. ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1` no ambiente;
6. redeploy/restart;
7. rodar evidência pós-switch padrão;
8. validar login owner em `/accounts/login/?next=/ops/`;
9. registrar evidência do comando no change log;
10. rollback: retornar `HUBX_OPS_AUTH_GATE_ENFORCED=0` e redeploy/restart.

### No-Go
- tenant sem owner/user ativo;
- gate em estado diferente do esperado;
- provider de e-mail não pronto quando exigido;
- falhas de notification não resolvidas;
- login owner manual falhando após switch.

## Platform Ops Gate Post-Activation Monitoring Review
- o acesso owner/admin agora expõe métricas Prometheus específicas.
- o endpoint fica fora de `/ops/` para não depender do próprio gate monitorado.
- acesso ao endpoint exige `ACCOUNTS_OBSERVABILITY_TOKEN`.

### Endpoint
- `/accounts/metrics/owner-access/`

### Métricas
- `hubx_accounts_owner_access_audit_event_total`
  - labels: `tenant_id`, `action`
  - ações monitoradas:
    - `owner.login_failed`
    - `owner.login_rate_limited`
    - `owner.ops_gate_forbidden`
    - `owner.ops_gate_redirected`
- `hubx_accounts_owner_access_email_log_total`
  - labels: `tenant_id`, `intent_key`, `status`
  - intents:
    - `owner.access.invite`
    - `owner.access.password_reset`

### Alertas
- `HubxAccountsOwnerLoginFailuresHigh`
- `HubxAccountsOwnerLoginRateLimited`
- `HubxAccountsOpsGateForbiddenHigh`
- `HubxAccountsOpsPermissionDenied`
- `HubxAccountsOpsGateAnonymousRedirectHigh`
- `HubxAccountsOwnerAccessEmailFailures`
- `HubxAccountsOwnerAccessEmailBacklog`

### Runbook curto
1. login failures: verificar owner/user, reset de senha e origem do IP;
2. 403 no gate: verificar `User.email` e `OwnerUser` ativo no tenant;
3. redirects anônimos: confirmar se é tráfego esperado pós-switch;
4. e-mail failed/backlog: usar pipeline de `notifications` e `process_email_logs`;
5. se o problema bloquear operação, rollback com `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

## Platform Owner Access Security Hardening Review
- login owner/admin agora possui rate limit leve por tenant + identificador + IP.
- o bloqueio usa cache Django e não altera `OwnerUser` ou `User`.
- falhas continuam com mensagem genérica para evitar enumeração.
- quando bloqueado, o POST de login retorna `429` e header `Retry-After`.

### Configurações
- `OWNER_LOGIN_RATE_LIMIT_MAX_ATTEMPTS`
  - padrão: `5`
- `OWNER_LOGIN_RATE_LIMIT_WINDOW_SECONDS`
  - padrão: `900`
- `OWNER_LOGIN_RATE_LIMIT_LOCKOUT_SECONDS`
  - padrão: `900`

### Auditoria e métricas
- falhas comuns continuam registrando `owner.login_failed`.
- bloqueio por rate limit registra `owner.login_rate_limited`.
- a métrica `hubx_accounts_owner_access_audit_event_total` inclui `owner.login_rate_limited`.
- alerta: `HubxAccountsOwnerLoginRateLimited`.

### Escopo deliberado
- sem lockout persistido no banco.
- sem bloqueio global por tenant.
- sem captcha.
- sem MFA/SSO.
- sem rate limit em customer login.

## Platform Owner Session Policy Review
- sessões owner/admin agora possuem política explícita aplicada no login.
- o default é sessão curta, controlada por `OWNER_SESSION_IDLE_SECONDS`.
- `remember_me` precisa ser marcado explicitamente e usa `OWNER_SESSION_REMEMBER_SECONDS`.
- o login registra metadados de sessão no `AuditLog owner.login`:
  - `session_expiry_seconds`;
  - `session_remembered`.
- a sessão recebe marcadores internos:
  - `hubx_owner_session_kind=owner`;
  - `hubx_owner_session_remembered`;
  - `hubx_owner_session_expires_at`.

### Configurações
- `OWNER_SESSION_IDLE_SECONDS`
  - padrão: `7200`.
- `OWNER_SESSION_REMEMBER_SECONDS`
  - padrão: `43200`.
- baseline global de cookie:
  - `SESSION_COOKIE_HTTPONLY=True`;
  - `SESSION_COOKIE_SAMESITE=Lax`;
  - `SESSION_COOKIE_SECURE` por env;
  - `CSRF_COOKIE_SECURE` por env.

### Escopo deliberado
- sem MFA/SSO.
- sem rotação customizada de sessão além do login Django.
- sem sessão owner separada da sessão Django.
- sem revogação centralizada multi-dispositivo.
- sem idle timeout em middleware próprio além da expiração nativa da sessão.

## Platform Admin RBAC Granularization Review
- `accounts` continua dono do contrato de roles/permissões administrativas.
- `accounts.interfaces.admin_rbac` centraliza extração de tenant, role owner/admin e decisão de permissão para surfaces `/ops/`.
- views de módulos operacionais não devem resolver role manualmente por e-mail.
- actions visuais agora respeitam permissões:
  - owners: `owners.manage`;
  - coupons: `coupons.manage`;
  - pages: `pages.manage`;
  - reviews: `reviews.moderate`.
- writes sensíveis continuam bloqueados nos command services quando a role não possui permissão.

### Roles atuais
- `owner` e `admin`: acesso total às permissões administrativas atuais.
- `marketing`: cupons, páginas e reviews.
- `content_editor`: páginas e reviews.
- `support`: reviews.
- `viewer`: leitura sem actions mutáveis.

### Escopo deliberado
- sem modelo novo de permissões no banco.
- sem grupos Django.
- sem RBAC cross-tenant.
- sem permission matrix editável por UI.
- sem enforcement em storefront/customer.

## Platform Admin Navigation Personalization Review
- o cockpit `/ops/` agora personaliza atalhos e filas operacionais pela role do owner/admin ativo.
- a navegação usa `accounts.interfaces.admin_rbac.request_admin_can(...)`.
- permissões leves de leitura/navegação foram adicionadas à matriz:
  - `orders.view`;
  - `catalog.view`;
  - `customers.view`;
  - `shipping.view`;
  - `newsletter.view`;
  - `audit.view`;
  - `payments.view`.
- filas do cockpit também são filtradas por permissão:
  - pedidos/estoque exigem `orders.view`;
  - catálogo exige `catalog.view`;
  - clientes exige `customers.view`;
  - entregas exige `shipping.view`;
  - owners exige `owners.manage`.
- compatibilidade legada sem role explícita continua preservada enquanto o gate `/ops/` puder estar desligado.

### Escopo deliberado
- sem mudar as queries de KPI de base.
- sem bloquear URL por middleware granular.
- sem menu lateral global personalizado.
- sem persistência de preferências por operador.
- sem UI para editar permissões.

## Platform Ops URL Permission Enforcement Review
- o gate `/ops/` agora aplica enforcement HTTP granular por prefixo quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`.
- a raiz `/ops/` continua acessível para qualquer owner/admin ativo.
- prefixos operacionais exigem permissão explícita da matriz de `accounts.application.admin_permissions`:
  - `/ops/orders/`: `orders.view`;
  - `/ops/catalog/`: `catalog.view`;
  - `/ops/checkout/`: `checkout.view`;
  - `/ops/customers/`: `customers.view`;
  - `/ops/shipping/`: `shipping.view`;
  - `/ops/newsletter/`: `newsletter.view`;
  - `/ops/audit/`: `audit.view`;
  - `/ops/payments/`: `payments.view`;
  - `/ops/coupons/`: `coupons.manage`;
  - `/ops/pages/`: `pages.manage`;
  - `/ops/reviews/`: `reviews.moderate`;
  - `/ops/owners/`: `owners.manage`.
- negação registra `AuditLog owner.ops_permission_denied`.
- métricas owner access exportam `owner.ops_permission_denied`.
- alerta Prometheus: `HubxAccountsOpsPermissionDenied`.

### Escopo deliberado
- enforcement só ocorre com o gate `/ops/` ativo.
- sem permission middleware fora de `/ops/`.
- sem matriz persistida em banco.
- sem granularidade por método HTTP neste primeiro corte.
- command services continuam sendo a camada final de bloqueio para writes.

## Platform RBAC Production Readiness Review
- ativação real do RBAC granular agora possui comando próprio de evidência Go/No-Go.
- comando:
  - `python manage.py ops_rbac_production_readiness --tenant-id=<tenant_id> --fail-on-blockers`
- a evidência valida:
  - estado esperado de `HUBX_OPS_AUTH_GATE_ENFORCED`;
  - matriz `owner/admin` contendo todas as permissões exigidas pelos prefixos `/ops/`;
  - tenant ativo com ao menos um `OwnerUser` `owner` ou `admin` ativo;
  - `User` Django ativo, único e correspondente ao e-mail desse full admin;
  - ausência de roles desconhecidas em owners ativos.

### Critérios Go/No-Go
- Go:
  - gate no estado esperado;
  - matriz sem permissões faltantes para `owner` e `admin`;
  - cada tenant alvo possui pelo menos um full admin operacional;
  - nenhuma role desconhecida ativa.
- No-Go:
  - `ops-gate-not-enabled`;
  - `no_active_full_admin_owner`;
  - `unknown_owner_role`;
  - `full_admin_without_django_user`;
  - `full_admin_with_inactive_django_user`;
  - `full_admin_email_ambiguous`.

### Runbook curto
1. rodar `ops_rbac_production_readiness --tenant-id=<tenant_id> --expect-gate=disabled` antes do switch, se o gate ainda estiver desligado;
2. provisionar ou corrigir owner/admin com `provision_initial_owner` e convite/reset;
3. ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1` no ambiente;
4. redeploy/restart;
5. rodar `ops_rbac_production_readiness --tenant-id=<tenant_id> --fail-on-blockers`;
6. testar `/ops/`, uma rota permitida e uma rota proibida para role limitada;
7. monitorar `owner.ops_permission_denied`;
8. rollback: retornar `HUBX_OPS_AUTH_GATE_ENFORCED=0` e redeploy/restart.

### Escopo deliberado
- sem ativação automática de env.
- sem mudança automática de roles.
- sem criar owners em lote.
- sem browser E2E obrigatório.
- sem permission matrix persistida/editável.

## Platform RBAC Staging Activation Evidence Review
- staging agora possui pacote único de evidência para ativar RBAC granular em `/ops/`.
- comando:
  - `python manage.py ops_rbac_staging_activation_evidence --tenant-id=<tenant_id> --fail-on-blockers`
- a captura compõe:
  - `ops_gate_activation_preflight`;
  - `ops_rbac_production_readiness`;
  - checklist manual mínimo;
  - passos explícitos de rollback.
- o comando não altera `HUBX_OPS_AUTH_GATE_ENFORCED`, tenants, owners, roles ou usuários.
- a saída é textual e deve ser anexada ao change log/janela de staging.

### Evidência mínima
- saída `[READY]` do pacote agregado;
- saída dos comandos sugeridos em `command.preflight` e `command.rbac`;
- teste manual de `/ops/` com owner/admin ativo;
- teste manual de rota permitida pela role;
- teste manual de rota proibida com `403` e `owner.ops_permission_denied`;
- rollback documentado com `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

### Critério Go/No-Go
- Go:
  - preflight pronto;
  - RBAC production readiness pronto para o tenant;
  - gate no estado esperado;
  - testes manuais mínimos concluídos.
- No-Go:
  - qualquer blocker de `preflight:*`;
  - qualquer blocker de `rbac:*`;
  - falha manual em `/ops/`, rota permitida ou rota proibida.

### Escopo deliberado
- sem executar deploy/restart.
- sem modificar variável de ambiente.
- sem criar evidência falsa de staging real quando rodado localmente.
- sem E2E browser obrigatório.
- sem alteração automática de roles/users.

## Platform RBAC Production Activation Evidence Review
- produção agora possui pacote agregado de evidência para manter RBAC granular ativo com segurança.
- comando:
  - `python manage.py ops_rbac_production_activation_evidence --tenant-id=<tenant_id> --fail-on-blockers`
- a captura compõe:
  - `ops_gate_production_rollout`;
  - `ops_rbac_production_readiness`;
  - health de e-mail/notificações owner access;
  - checklist manual mínimo de produção;
  - rollback explícito.
- por padrão, produção exige provider de e-mail real e bloqueia `EmailLog failed`.
- o comando não altera env, deploy, roles, usuários ou tenants.

### Evidência mínima
- saída `[READY]` do pacote agregado em `environment=production`;
- saída reproduzível de `command.rollout`;
- saída reproduzível de `command.rbac`;
- login real owner/admin no subdomínio do tenant;
- rota permitida retornando `200`;
- rota proibida retornando `403`;
- métrica/log de `owner.ops_permission_denied` visível;
- rollback documentado.

### Critério Go/No-Go
- Go:
  - rollout do gate pronto;
  - RBAC production readiness pronto;
  - provider de e-mail pronto, salvo override explícito;
  - sem falhas de notification owner access, salvo override explícito;
  - testes manuais concluídos.
- No-Go:
  - qualquer blocker de `rollout:*`;
  - qualquer blocker de `rbac:*`;
  - falha manual em dashboard, rota permitida, rota proibida ou métrica.

### Escopo deliberado
- sem ativação automática de produção.
- sem restart/deploy automático.
- sem criar evidência falsa de produção quando rodado localmente.
- sem batch global obrigatório.
- sem alteração automática de permission matrix.

## Platform RBAC Post-Production Monitoring Review
- pós-ativação production agora possui snapshot operacional para decidir `HEALTHY`, `WATCH` ou `ROLLBACK`.
- comando:
  - `python manage.py ops_rbac_post_production_monitoring --tenant-id=<tenant_id> --fail-on-rollback`
- sinais observados:
  - `owner.ops_permission_denied`;
  - `owner.ops_gate_forbidden`;
  - `owner.login_failed`;
  - `owner.login_rate_limited`;
  - `EmailLog failed` para owner access.
- `WATCH` indica ruído que exige triagem sem rollback automático.
- `ROLLBACK` indica rate limit owner/admin ou falha de e-mail owner access.

### Runbook curto
1. rodar o comando a cada janela de observação pós-ativação;
2. se `HEALTHY`, manter gate e seguir monitoramento normal;
3. se `WATCH`, revisar roles, vínculos owner/user, navegação direta e resets;
4. se `ROLLBACK`, avaliar retorno de `HUBX_OPS_AUTH_GATE_ENFORCED=0`;
5. registrar evidência e ação tomada no change log.

### Alertas
- `HubxAccountsOpsPermissionDenied`: warning para negações granulares recorrentes.
- `HubxAccountsRBACPostProductionRollbackSignal`: critical para rate limit owner/admin ou falha de e-mail owner access.

### Escopo deliberado
- sem executar rollback automaticamente.
- sem criar métrica nova além das existentes de owner access.
- sem dashboard Grafana novo nesta fase.
- sem inferir incidente a partir de redirects anônimos isolados.

## Platform RBAC Production Closure Review
- a trilha de RBAC production agora possui snapshot final de closure.
- comando:
  - `python manage.py ops_rbac_production_closure --tenant-id=<tenant_id> --fail-on-blockers`
- o closure compõe:
  - evidência de ativação production;
  - monitoramento pós-produção;
  - decisões finais;
  - riscos residuais;
  - próximas trilhas fora do recorte RBAC atual.
- status possíveis:
  - `READY`: ativação pronta e monitoramento saudável;
  - `WATCH`: ativação pronta, mas sinais recentes exigem triagem;
  - `BLOCKED`: ativação bloqueada ou sinal rollback presente.

### Decisão de encerramento
- RBAC granular de `/ops/` está tecnicamente fechado para esta fase.
- a próxima evolução não deve continuar polindo o mesmo gate, salvo evidência real de produção.
- riscos remanescentes viram trilhas próprias:
  - MFA/SSO owner/admin;
  - permission matrix persistida;
  - exportação formal de evidências de auditoria.

### Escopo deliberado
- sem executar ativação, rollback ou deploy.
- sem transformar matriz de permissões em modelo persistido.
- sem resolver MFA/SSO nesta trilha.
- sem substituir change management humano.

## Platform Owner MFA/SSO Review
- MFA/SSO owner/admin agora possui contrato/readiness read-only.
- comando:
  - `python manage.py owner_mfa_sso_readiness --fail-on-blockers`
- o login atual permanece:
  - `User` Django;
  - `OwnerUser` ativo no tenant;
  - rate limit owner/admin;
  - sessão owner/admin explícita.
- MFA futuro deve ocorrer depois da senha e antes da sessão efetiva.
- SSO futuro deve resolver identidade externa para `User` + `OwnerUser` do mesmo tenant.

### Settings de contrato
- `OWNER_MFA_REQUIRED`;
- `OWNER_MFA_PROVIDER`;
- `OWNER_SSO_ENABLED`;
- `OWNER_SSO_PROVIDER`;
- `OWNER_SSO_LOGIN_URL`;
- `OWNER_SSO_CALLBACK_PATH`.

### Escopo deliberado
- sem enrollment de fator.
- sem provider externo real.
- sem callback SSO.
- sem break-glass.
- sem alterar fluxo de login atual.

## Owner MFA Enrollment Model Review
- enrollment MFA owner/admin agora possui modelo persistido tenant-scoped.
- entidade:
  - `OwnerMfaFactor`
- comando de leitura:
  - `python manage.py owner_mfa_enrollment_readiness --tenant-id=<tenant_id> --fail-on-blockers`
- o modelo pertence ao mesmo tenant do `OwnerUser`.
- fatores são únicos por `(tenant, owner, factor_type, provider_key)`.
- o readiness considera enrolled apenas owner com fator ativo e verificado.

### Campos principais
- `factor_type`: `totp`, `recovery_code` ou `external`;
- `provider_key`;
- `label`;
- `secret_reference`;
- `is_verified`;
- `is_active`;
- `verified_at`;
- `last_challenged_at`.

### Escopo deliberado
- sem gerar segredo TOTP.
- sem verificar challenge.
- sem recovery codes reais.
- sem enforcement no login.
- sem provider externo obrigatório.

## Owner MFA Enrollment Command Review
- enrollment MFA agora possui command service auditável para registrar/verificar/desativar fatores.
- service:
  - `accounts.application.owner_mfa_enrollment_commands`
  - `accounts.application.owner_mfa_challenge_commands`
- comando:
  - `python manage.py owner_mfa_factor register --tenant-id=<tenant_id> --owner-id=<owner_id>`
  - `python manage.py owner_mfa_factor verify --tenant-id=<tenant_id> --factor-id=<factor_id> --challenge=<code>`
  - `python manage.py owner_mfa_factor deactivate --tenant-id=<tenant_id> --factor-id=<factor_id>`
- registro cria fator ativo, porém ainda não verificado.
- verificação valida TOTP interno e marca fator ativo como verificado.
- desativação não apaga fator, apenas marca `is_active=False`.
- eventos auditados:
  - `owner.mfa_factor_registered`;
  - `owner.mfa_factor_verified`;
  - `owner.mfa_factor_verification_failed`;
  - `owner.mfa_factor_deactivated`.

### Escopo deliberado
- sem enforcement no login.
- sem UI admin dedicada.
- sem recovery codes reais.
- sem provider externo obrigatório.
- sem apagar fator fisicamente.

## Owner MFA Challenge Verification Review
- fatores MFA TOTP agora podem sair de `pending/unverified` para `verified` por challenge real.
- service:
  - `accounts.application.owner_mfa_challenge_commands`
- comando:
  - `python manage.py owner_mfa_factor verify --tenant-id=<tenant_id> --factor-id=<factor_id> --challenge=<code>`
- a verificação:
  - exige permissão `owners.manage`;
  - busca fator ativo pelo `tenant_id`;
  - valida TOTP com janela curta;
  - atualiza `is_verified`, `verified_at` e `last_challenged_at`;
  - audita sucesso e falha sem persistir o código informado.

### Escopo deliberado
- sem aplicar MFA no login owner/admin.
- sem gerar segredo TOTP automaticamente.
- sem QR code ou UI de enrollment.
- sem recovery codes reais.
- sem adapter externo/vault obrigatório.

## Owner MFA Enrollment Closure Review
- a abordagem de enrollment MFA está tecnicamente fechada nesta fase.
- comando:
  - `python manage.py owner_mfa_enrollment_closure`
- status:
  - modelo pronto;
  - readiness pronto;
  - commands auditáveis prontos;
  - challenge TOTP interno pronto;
  - enforcement MFA fora de escopo.

### Próximas trilhas sugeridas
- `Owner MFA Admin Surface Review`;
- `Owner Break-Glass Access Review`.
- `Owner MFA Login Enforcement Review`.

## Owner MFA Admin Surface Review
- `/ops/owners/mfa/` agora possui superfície read/action mínima para fatores MFA owner/admin.
- rotas:
  - `GET /ops/owners/mfa/`;
  - `POST /ops/owners/mfa/<factor_id>/verify/`;
  - `POST /ops/owners/mfa/<factor_id>/deactivate/`.
- query service:
  - `accounts.application.owner_mfa_admin_queries`
- actions continuam delegadas para:
  - `accounts.application.owner_mfa_challenge_commands`;
  - `accounts.application.owner_mfa_enrollment_commands`.
- a surface lista apenas fatores do tenant resolvido e exige permissão `owners.manage` para ações.

### Escopo deliberado
- sem registrar fator novo pela UI.
- sem QR code ou geração automática de segredo.
- sem enforcement no login.
- sem recovery codes.

## Owner Break-Glass Access Review
- break-glass MFA owner/admin agora possui readiness operacional sem alterar login.
- comando:
  - `python manage.py owner_mfa_break_glass_readiness --tenant-id=<tenant_id>`
- settings de contrato:
  - `OWNER_MFA_BREAK_GLASS_ENABLED`;
  - `OWNER_MFA_BREAK_GLASS_OWNER_EMAILS`.
- readiness bloqueia quando break-glass está desligado, sem e-mail configurado ou apontando para owner ausente/inativo no tenant.

### Escopo deliberado
- sem criar bypass real de MFA.
- sem alterar sessão ou login.
- sem senha de emergência persistida.

## Owner MFA Login Enforcement Readiness Review
- enforcement MFA owner/admin agora possui readiness Go/No-Go sem ativação automática.
- comando:
  - `python manage.py owner_mfa_login_enforcement_readiness --tenant-id=<tenant_id>`
- readiness exige:
  - `OWNER_MFA_REQUIRED=True`;
  - todos os owners ativos com fator ativo/verificado;
  - break-glass pronto.
- também imprime checklist manual mínimo para ativação futura.

### Escopo deliberado
- sem bloquear login.
- sem challenge durante autenticação.
- sem alterar middleware/session.

## Owner MFA Operational Closure Review
- pacote operacional de MFA owner/admin agora possui closure agregada.
- comando:
  - `python manage.py owner_mfa_operational_closure --tenant-id=<tenant_id>`
- closure combina:
  - surface admin;
  - readiness de break-glass;
  - readiness de enforcement.
- próxima execução real deve ser tratada como trilha separada de login enforcement.

### Próximas trilhas sugeridas
- `Owner MFA Login Enforcement Execution Review`;
- `Owner MFA Recovery Codes Review`;
- `Owner MFA Secret Storage Hardening Review`.

## Owner MFA Login Enforcement Execution Review
- login owner/admin agora aplica MFA quando `OWNER_MFA_REQUIRED=True`.
- fluxo:
  - senha válida e `OwnerUser` ativo no tenant;
  - fator MFA ativo/verificado obrigatório;
  - criação de sessão pendente curta;
  - redirect para `/accounts/login/mfa/`;
  - challenge TOTP válido cria a sessão owner/admin efetiva.
- rollback operacional:
  - definir `OWNER_MFA_REQUIRED=0`;
  - redeploy/restart;
  - login volta ao fluxo direto pós-senha, preservando rate limit e sessão owner/admin.
- eventos auditados:
  - `owner.login_mfa_required`;
  - `owner.login_mfa_failed`;
  - `owner.login_mfa_completed`;
  - `owner.login_mfa_blocked`.

### Settings
- `OWNER_MFA_REQUIRED`;
- `OWNER_MFA_CHALLENGE_PENDING_SECONDS`;
- `OWNER_MFA_BREAK_GLASS_ENABLED`;
- `OWNER_MFA_BREAK_GLASS_OWNER_EMAILS`.

### Escopo deliberado
- sem recovery codes reais.
- sem bypass automático de break-glass.
- sem provider externo/vault obrigatório.
- sem enforcement para customer login.

## Owner MFA Recovery Codes Review
- recovery codes MFA owner/admin agora possuem modelo persistido com hash e uso único.
- entidade:
  - `OwnerMfaRecoveryCode`
- comando:
  - `python manage.py owner_mfa_recovery_codes generate --tenant-id=<tenant_id> --owner-id=<owner_id> --count=8`
- geração:
  - substitui códigos não usados anteriores;
  - retorna os códigos em texto claro apenas na saída do comando;
  - persiste somente hashes;
  - cria/reativa fator `recovery_code` verificado para o owner.
- login MFA:
  - challenge TOTP continua preferencial;
  - recovery code válido pode concluir `/accounts/login/mfa/`;
  - recovery code usado é marcado com `used_at` e não pode ser reutilizado.
- readiness:
  - fator `recovery_code` só conta como enrollment válido enquanto houver código não usado.
- eventos auditados:
  - `owner.mfa_recovery_codes_generated`;
  - `owner.mfa_recovery_code_used`.

### Escopo deliberado
- sem exibir códigos novamente depois da geração.
- sem UI admin dedicada para regeneração.
- sem recovery code por e-mail.
- sem bypass break-glass automático.

## Owner MFA Secret Storage Hardening Review
- storage de segredo TOTP owner/admin agora possui contrato explícito e readiness.
- resolver:
  - `accounts.application.owner_mfa_secret_storage`
- comando:
  - `python manage.py owner_mfa_secret_storage_readiness --tenant-id=<tenant_id>`
- modos suportados:
  - `plain:<secret>` ou valor legado sem prefixo: segredo local em texto claro, aceito apenas enquanto `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True`;
  - `ref:<path>`: referência externa futura, inventariada mas ainda não resolvida sem adapter;
  - vazio: blocker.
- login e verificação MFA passam pelo resolver antes de validar TOTP.
- readiness inventaria fatores TOTP ativos por tenant e emite blockers para:
  - segredo ausente;
  - referência externa sem provider;
  - segredo local quando local plain estiver desabilitado.

### Settings
- `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`

### Escopo deliberado
- sem migrar segredo automaticamente.
- sem provider/vault externo real.
- sem descriptografia ou KMS.
- sem quebrar fatores legados enquanto local plain estiver permitido.

## Owner MFA External Secret Provider Adapter Review
- `ref:<path>` agora pode ser resolvido por adapter externo mínimo.
- provider inicial:
  - `OWNER_MFA_SECRET_PROVIDER=env`
- contrato env:
  - `OWNER_MFA_SECRET_ENV_PREFIX=OWNER_MFA_SECRET_`
  - `ref:owners/1/totp` resolve `OWNER_MFA_SECRET_OWNERS_1_TOTP`
- integração:
  - login MFA e command de challenge continuam usando `owner_mfa_secret_storage`;
  - resolver delega `ref:<path>` ao registry `accounts.infrastructure.owner_mfa_secret_providers`;
  - readiness considera referência externa pronta quando provider resolve o segredo.

### Settings
- `OWNER_MFA_SECRET_PROVIDER`
- `OWNER_MFA_SECRET_ENV_PREFIX`

### Escopo deliberado
- sem vault/KMS real ainda.
- sem cache de segredo.
- sem migração automática de `plain:` para `ref:`.
- sem listar valores de segredo em readiness ou audit log.

## Owner MFA TOTP Secret Migration Plan
- migração de segredos TOTP locais para `ref:<path>` agora possui plano operacional reproduzível.
- query service:
  - `accounts.application.owner_mfa_totp_secret_migration_plan_queries`
- comando:
  - `python manage.py owner_mfa_totp_secret_migration_plan --tenant-id=<tenant_id> --reference-prefix=owners`
- o plano classifica fatores TOTP ativos como:
  - `migrate-local-to-ref`: fator local/legado que deve ser copiado para provider externo;
  - `already-external`: fator já em `ref:<path>`;
  - `blocked`: segredo ausente ou referência externa não resolvida.
- o comando imprime:
  - `target_ref` sugerido;
  - runbook;
  - rollback;
  - blockers.

### Runbook curto
1. copiar segredo TOTP atual para provider externo fora do app.
2. gravar usando o `target_ref` sugerido.
3. configurar `OWNER_MFA_SECRET_PROVIDER`.
4. validar `owner_mfa_secret_storage_readiness`.
5. atualizar `secret_reference` para `ref:<target_ref>` em janela controlada.
6. testar login MFA.
7. só então avaliar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=0`.

### Escopo deliberado
- sem mover segredo automaticamente.
- sem escrever `secret_reference`.
- sem ler/imprimir segredo em texto claro.
- sem remover fallback local antes de evidência real.

## Owner MFA TOTP Secret Migration Execution Review
- migração de segredo TOTP local para `ref:<path>` agora possui execução controlada.
- command service:
  - `accounts.application.owner_mfa_totp_secret_migration_commands`
- comando:
  - `python manage.py owner_mfa_totp_secret_migration_execute --tenant-id=<tenant_id> --factor-id=<factor_id>`
- por padrão o comando roda em `DRY-RUN`; escrita real exige `--execute`.
- antes de atualizar `OwnerMfaFactor.secret_reference`, o service valida:
  - tenant explícito;
  - fator TOTP ativo no tenant informado;
  - segredo atual em modo `local-plain`;
  - `target_ref` resolvido pelo provider externo configurado;
  - valor externo equivalente ao segredo local atual, sem imprimir nenhum segredo.
- execução grava apenas `ref:<target_ref>` e registra `AuditLog` `owner.mfa_totp_secret_migrated`.

### Runbook curto
1. rodar `owner_mfa_totp_secret_migration_plan` e copiar o segredo fora do app.
2. publicar o segredo no provider usando o `target_ref`.
3. validar readiness de storage.
4. rodar `owner_mfa_totp_secret_migration_execute` sem `--execute`.
5. rodar novamente com `--execute`.
6. testar challenge/login MFA do owner migrado.

### Escopo deliberado
- sem migração em lote automática.
- sem criar ou copiar segredo no provider.
- sem imprimir segredo local ou externo.
- sem desabilitar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` nesta etapa.

## Owner MFA Local Secret Retirement Review
- aposentadoria do fallback local/plain de TOTP owner/admin agora possui readiness explícito.
- query service:
  - `accounts.application.owner_mfa_local_secret_retirement_queries`
- comando:
  - `python manage.py owner_mfa_local_secret_retirement_readiness --tenant-id=<tenant_id>`
- a revisão decide se já é seguro aplicar:
  - `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`
- critérios para readiness:
  - nenhum fator TOTP ativo em `local-plain`;
  - nenhum fator com segredo ausente;
  - todas as referências externas `ref:<path>` resolvidas pelo provider configurado;
  - storage readiness sem blockers.

### Runbook curto
1. executar `owner_mfa_local_secret_retirement_readiness`.
2. confirmar `local_plain_count=0`.
3. validar challenge/login MFA amostral com provider externo ativo.
4. aplicar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False` no ambiente.
5. rodar `owner_mfa_secret_storage_readiness`.
6. monitorar falhas MFA owner/admin.

### Escopo deliberado
- sem alterar settings/env automaticamente.
- sem migrar fatores locais restantes.
- sem remover código de fallback local.
- sem rollback automático.

## Owner MFA Local Secret Retirement Execution Review
- ativação da aposentadoria do fallback local/plain agora possui evidência operacional em duas fases.
- query service:
  - `accounts.application.owner_mfa_local_secret_retirement_execution_queries`
- comando:
  - `python manage.py owner_mfa_local_secret_retirement_execution --tenant-id=<tenant_id> --phase=before`
  - `python manage.py owner_mfa_local_secret_retirement_execution --tenant-id=<tenant_id> --phase=after`
- fase `before`:
  - confirma que o tenant está pronto para o corte;
  - captura contagens e referências externas resolvidas;
  - orienta aplicar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False` fora do app.
- fase `after`:
  - exige `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
  - revalida que não há fator local/plain nem referência externa quebrada;
  - emite rollback explícito para restaurar o setting.

### Escopo deliberado
- sem escrever settings/env.
- sem reiniciar processo, deploy ou worker.
- sem alterar `OwnerMfaFactor`.
- sem criar evento de auditoria, pois a evidência é read-only.

## Owner MFA Provider Health Monitoring Review
- health operacional do provider externo de segredos TOTP owner/admin agora possui snapshot dedicado.
- query service:
  - `accounts.application.owner_mfa_provider_health_queries`
- comando:
  - `python manage.py owner_mfa_provider_health --tenant-id=<tenant_id>`
- status:
  - `HEALTHY`: provider configurado, referências externas resolvidas e sem fallback local;
  - `WATCH`: ainda há fallback local, nenhum fator externo ou readiness incompleto sem quebra imediata;
  - `CRITICAL`: referência externa não resolve, provider ausente para `ref:<path>` ou segredo ausente.
- o snapshot reaproveita storage readiness e nunca imprime o valor do segredo.

### Sinais
- `provider-not-configured`
- `external-reference-unresolved`
- `secret-missing`
- `local-plain-still-present`
- `no-external-reference-factors`

### Escopo deliberado
- sem endpoint Prometheus novo nesta etapa.
- sem alerta Grafana/Prometheus ainda.
- sem retry automático ou fallback silencioso.
- sem ler/imprimir segredo.

## Owner MFA Provider Health Metrics Review
- health do provider TOTP MFA owner/admin agora possui endpoint Prometheus tenant-aware.
- metrics query:
  - `accounts.application.owner_mfa_provider_health_metrics_queries`
- endpoint:
  - `/accounts/metrics/owner-mfa-provider-health/`
- token:
  - `ACCOUNTS_OBSERVABILITY_TOKEN`
- métricas:
  - `hubx_accounts_owner_mfa_provider_health_status`;
  - `hubx_accounts_owner_mfa_provider_external_reference_total`;
  - `hubx_accounts_owner_mfa_secret_storage_total`;
  - `hubx_accounts_owner_mfa_provider_signal_total`.
- observabilidade:
  - scrape em `infra/observability/prometheus/accounts-scrape.example.yml`;
  - alertas em `infra/observability/prometheus/accounts-alert-rules.yml`.

### Escopo deliberado
- sem label por owner/factor para evitar cardinalidade alta.
- sem expor segredo ou reference path completo.
- sem dashboard Grafana dedicado nesta etapa.
- sem mutação operacional automática.

## Owner MFA Provider Health Dashboard Review
- health do provider TOTP MFA owner/admin agora possui dashboard Grafana inicial.
- dashboard:
  - `infra/observability/grafana/accounts-owner-mfa-provider-health-dashboard.json`
- painéis:
  - tenants com provider MFA crítico;
  - refs TOTP externas não resolvidas;
  - fatores TOTP ainda em `local-plain`;
  - tenants MFA saudáveis;
  - status por tenant/provider;
  - referências externas por estado;
  - sinais ativos;
  - storage TOTP por tenant.

### Escopo deliberado
- sem drill-down por owner/factor.
- sem reference path em labels.
- sem painel de login failures nesta dashboard; isso permanece em owner access.
- sem provisionamento automático do Grafana.

## Owner MFA Provider Health Closure Review
- trilha de health do provider TOTP MFA owner/admin agora possui closure read-only.
- query service:
  - `accounts.application.owner_mfa_provider_health_closure_queries`
- comando:
  - `python manage.py owner_mfa_provider_health_closure --tenant-id=<tenant_id>`
- o closure agrega:
  - status atual do provider health;
  - presença de scrape Prometheus;
  - presença de alert rules;
  - presença de dashboard Grafana;
  - decisões de exposição segura sem owner/factor/segredo/reference path.
- status:
  - `ready`: health saudável e artefatos presentes;
  - `watch`: fallback local ou ausência de fatores externos sem incidente crítico;
  - `blocked`: health crítico ou artefato de observabilidade ausente.

### Escopo deliberado
- sem ativar Prometheus/Grafana real.
- sem alterar provider/env/settings.
- sem executar rollback automático.
- sem adicionar drill-down sensível.

## Owner MFA Local Secret Code Retirement Review
- aposentadoria do código/tolerância `plain:`/legado agora possui readiness explícito.
- query service:
  - `accounts.application.owner_mfa_local_secret_code_retirement_queries`
- comando:
  - `python manage.py owner_mfa_local_secret_code_retirement_readiness --tenant-id=<tenant_id>`
- a review só fica `ready` quando:
  - `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
  - não há fatores TOTP ativos em `local-plain`;
  - há fatores TOTP externos resolvidos;
  - provider health closure não está bloqueado.
- superfícies de código inventariadas:
  - `owner_mfa_secret_storage.LOCAL_PREFIX`;
  - `OwnerMfaSecretStorageResolver.can_accept_local_plain`;
  - readiness `local-secret-disabled`;
  - setting `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`;
  - testes de `plain:`/legado.

### Escopo deliberado
- sem remover suporte `plain:` nesta wave.
- sem alterar dados ou settings.
- sem remover rollback operacional.
- sem varrer todos os tenants globalmente ainda.

## Owner MFA Local Secret Code Retirement Execution Review
- fallback local/plain de TOTP MFA owner/admin agora fica desligado por default.
- setting:
  - `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` passa a default `0`;
  - rollback explícito continua possível com `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1`.
- evidence query:
  - `accounts.application.owner_mfa_local_secret_code_retirement_execution_queries`
- comando:
  - `python manage.py owner_mfa_local_secret_code_retirement_execute --tenant-id=<tenant_id>`
- a execução confirma:
  - default/env atual não aceita local plain;
  - readiness tenant-scoped está pronto;
  - provider health closure não bloqueia;
  - rollback por env está documentado.

### Escopo deliberado
- sem remover parsing de `plain:` ainda.
- sem deletar testes legados; eles agora usam override explícito de rollback.
- sem migrar dados.
- sem desligar provider externo.

## Owner MFA Legacy Data Global Sweep Review
- dados legados TOTP MFA owner/admin agora possuem sweep global read-only.
- query service:
  - `accounts.application.owner_mfa_legacy_data_global_sweep_queries`
- comando:
  - `python manage.py owner_mfa_legacy_data_global_sweep`
- a sweep percorre tenants com fatores TOTP ativos e agrega:
  - tenants avaliados;
  - fatores em `local-plain`;
  - referências externas;
  - segredos ausentes;
  - tenants bloqueados.
- blockers:
  - `tenant-<id>:local-plain-factors-present`;
  - `tenant-<id>:missing-secret-factors-present`;
  - `tenant-<id>:external-secret-unresolved`.

### Escopo deliberado
- sem expor segredo, owner/factor ou reference path completo.
- sem migrar ou alterar dados.
- sem remover parser local.
- sem cobrir backups/dumps/fixtures fora do banco atual.

## Owner MFA Local Secret Parser Removal Review
- remoção do parser `plain:`/legado agora possui review Go/No-Go.
- query service:
  - `accounts.application.owner_mfa_local_secret_parser_removal_queries`
- comando:
  - `python manage.py owner_mfa_local_secret_parser_removal_review`
- a review compõe:
  - sweep global de dados legados;
  - estado de `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`;
  - superfícies de parser local;
  - plano de remoção;
  - rollback por revert de deploy.
- status `ready` exige:
  - sweep global `ready`;
  - nenhum blocker de tenant;
  - env local/plain desligado.

### Escopo deliberado
- sem remover parser nesta wave.
- sem alterar dados/settings.
- sem reativar rollback por env como mecanismo suficiente.
- sem varrer arquivos externos ao banco.

## Owner MFA Local Secret Parser Removal Execution Review
- o resolver TOTP MFA owner/admin não resolve mais valores `plain:` nem valores legados sem `ref:`.
- query service de evidência:
  - `accounts.application.owner_mfa_local_secret_parser_removal_execution_queries`
- comando:
  - `python manage.py owner_mfa_local_secret_parser_removal_execute`
- comportamento novo:
  - `ref:<path>` continua usando provider externo;
  - valor vazio continua `missing`;
  - qualquer valor local/legado retorna `unsupported-local`, `ready=False` e segredo vazio.
- readiness e migration plan passam a reportar blocker `local-secret-unsupported`.
- rollback pós-execution deixa de ser env-only e passa a exigir revert/deploy do código.

### Escopo deliberado
- sem migrar dados automaticamente.
- sem restaurar segredo local em outputs, logs ou comandos.
- sem remover o inventário/sweep que ainda detecta resíduos legados.
- sem alterar o contrato de provider externo.

## Owner MFA Vault/KMS Provider Review
- o provider `env` passa a ser tratado como ponte operacional, não como storage final de produção para segredos TOTP MFA.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_review_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_review --tenant-id=<tenant_id> --target-provider=<provider>`
- targets aceitos inicialmente:
  - `hashicorp-vault`;
  - `aws-secrets-manager`;
  - `aws-kms`;
  - `gcp-secret-manager`;
  - `azure-key-vault`.
- a review compõe:
  - closure de health do provider atual por tenant;
  - execution de remoção do parser local/plain;
  - contrato mínimo do adapter Vault/KMS;
  - plano de rollout e rollback.
- status `ready` significa pronto para criar adapter/skeleton, não ativação production automática.

### Escopo deliberado
- sem chamar Vault/KMS real nesta wave.
- sem alterar `OWNER_MFA_SECRET_PROVIDER`.
- sem migrar `secret_reference`.
- sem imprimir segredo, owner/factor ou reference path completo.

## Owner MFA Vault/KMS Provider Adapter Contract Review
- o contrato técnico do adapter Vault/KMS para TOTP MFA owner/admin agora é explícito antes do skeleton.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_adapter_contract_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_adapter_contract --tenant-id=<tenant_id> --target-provider=<provider>`
- o contrato cobre:
  - settings esperados;
  - interface de retorno `OwnerMfaSecretProviderResult`;
  - erros recuperáveis sem exception no login;
  - controles de segurança para não expor secret material;
  - contrato mínimo de testes.
- a primeira versão do adapter deve ser read-path-only:
  - resolve `ref:<path>`;
  - não grava segredo;
  - não migra `OwnerMfaFactor`;
  - não cacheia segredo.

### Escopo deliberado
- sem implementar provider real nesta wave.
- sem alterar settings/env.
- sem fallback automático para `env` quando Vault/KMS falhar.
- sem cache de segredo na primeira versão.

## Owner MFA Vault/KMS Provider Adapter Skeleton Execution
- o registry de segredos MFA agora reconhece os targets Vault/KMS aprovados no contrato.
- implementação:
  - `accounts.infrastructure.owner_mfa_secret_providers`
- evidence query:
  - `accounts.application.owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_adapter_skeleton_execute --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref>`
- settings adicionados:
  - `OWNER_MFA_SECRET_TIMEOUT_MS`;
  - `OWNER_MFA_SECRET_RETRY_COUNT`;
  - `OWNER_MFA_SECRET_NAMESPACE`;
  - `OWNER_MFA_SECRET_CACHE_SECONDS`;
  - `OWNER_MFA_SECRET_VAULT_KMS_SKELETON_STATUS`;
  - `OWNER_MFA_SECRET_VAULT_KMS_SKELETON_SECRETS`.
- o skeleton é read-path-only e retorna:
  - `owner-mfa-secret-provider-vault-ready`;
  - `owner-mfa-secret-provider-vault-missing`;
  - `owner-mfa-secret-provider-vault-unavailable`;
  - `owner-mfa-secret-provider-vault-timeout`;
  - `owner-mfa-secret-provider-vault-permission-denied`;
  - `owner-mfa-secret-provider-vault-invalid-reference`.

### Escopo deliberado
- sem SDK/vendor real ainda.
- sem escrita no provider.
- sem fallback automático para `env`.
- sem cache de segredo.
- sem imprimir o valor do segredo na evidência.

## Owner MFA Vault/KMS Provider Readiness Evidence Review
- o skeleton Vault/KMS agora possui pacote de evidência tenant-scoped para modo canário.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_readiness_evidence_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_readiness_evidence --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref>`
- a evidência compõe:
  - skeleton execution;
  - provider health closure;
  - provider observado no health;
  - contagens de refs externas, unresolved, local/plain e missing;
  - rollback sem reativar parser local/plain.
- `ready` exige:
  - skeleton execution ready;
  - provider health closure ready;
  - provider observado igual ao target;
  - tenant explícito.

### Escopo deliberado
- sem ativar staging real.
- sem chamar SDK/vendor real.
- sem alterar settings/env.
- sem imprimir segredo.
- sem exportar evidência formal auditável ainda.

## Owner MFA Vault/KMS Provider Staging Canary Review
- o provider Vault/KMS agora possui checklist de canário staging para login/challenge MFA owner/admin.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_staging_canary_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_staging_canary_review --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref> --canary-owner-email=<email>`
- a review compõe readiness evidence e exige owner canário explícito.
- entrega:
  - preflight;
  - checklist manual de login/challenge;
  - sinais de sucesso;
  - rollback;
  - blockers Go/No-Go.

### Escopo deliberado
- sem executar login real.
- sem criar sessão ou autenticar owner.
- sem alterar settings/env.
- sem chamar SDK/vendor real.
- sem coletar segredo, código TOTP ou reference path completo.

## Owner MFA Vault/KMS Provider Staging Canary Evidence Execution
- o canário staging agora possui captura declarativa de evidência pós-checklist.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_staging_canary_evidence_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_staging_canary_evidence --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref> --canary-owner-email=<email> --valid-login-passed --invalid-challenge-blocked --post-health-ready --logs-redacted --rollback-verified`
- a evidência valida:
  - review do canário pronta;
  - login válido reportado como aprovado;
  - challenge inválido reportado como bloqueado;
  - health pós-teste reportado como saudável;
  - logs/comandos reportados como redigidos;
  - rollback verificado/simulado.

### Escopo deliberado
- sem automatizar browser/login.
- sem gravar sessão, AuditLog ou estado de fator.
- sem coletar segredo, código TOTP ou reference path completo.
- sem exportar evidência formal assinada.

## Owner MFA Vault/KMS Provider Real Adapter Contract Review
- o adapter Vault/KMS real agora possui contrato técnico pós-canário.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_real_adapter_contract_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_real_adapter_contract --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref> --canary-owner-email=<email> --sdk-dependency-confirmed --credential-strategy-confirmed --network-timeout-confirmed --rollout-owner-confirmed`
- targets reais suportados nesta etapa:
  - `hashicorp-vault`;
  - `aws-secrets-manager`;
  - `gcp-secret-manager`;
  - `azure-key-vault`.
- o contrato exige:
  - evidência de canário staging pronta;
  - dependência SDK/vendor confirmada;
  - estratégia de credencial confirmada;
  - timeouts/rede confirmados;
  - responsável de rollout confirmado.

### Escopo deliberado
- sem implementar SDK/vendor ainda.
- sem trocar o skeleton.
- sem migrar segredo.
- sem cache.
- sem fallback automático para `env`.

## Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution
- o registry de segredos MFA agora possui branch real/mocável separado do skeleton configurável.
- implementação:
  - `accounts.infrastructure.owner_mfa_secret_providers`
- evidence query:
  - `accounts.application.owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_real_adapter_skeleton_execute --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref> --canary-owner-email=<email>`
- settings adicionados:
  - `OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED`;
  - `OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_STATUS`;
  - `OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_SECRETS`.
- a execução prova:
  - contrato real ready;
  - provider atual igual ao target;
  - branch real/mocável habilitado;
  - probe resolvido pelo branch real;
  - rollback sem parser local/plain.

### Escopo deliberado
- sem SDK/vendor real ainda.
- sem credenciais reais.
- sem cache.
- sem escrita/migração.
- sem fallback automático para `env`.

## Owner MFA Vault/KMS Provider SDK Dependency Review
- a dependência SDK/vendor do provider Vault/KMS agora possui review declarativa antes de qualquer instalação.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_sdk_dependency_review_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_sdk_dependency_review --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref> --canary-owner-email=<email> --dependency-pinned-confirmed --import-optional-confirmed --deploy-rollback-confirmed --license-review-confirmed`
- contratos de dependência definidos:
  - `hashicorp-vault`: pacote/import `hvac`;
  - `aws-secrets-manager`: pacote/import `boto3`;
  - `gcp-secret-manager`: pacote `google-cloud-secret-manager`, import `google.cloud.secretmanager`;
  - `azure-key-vault`: pacotes `azure-identity` e `azure-keyvault-secrets`, imports correspondentes.
- a review exige:
  - skeleton real/mocável ready;
  - dependência com versão fixada confirmada;
  - import opcional/lazy confirmado;
  - rollback de deploy confirmado;
  - licença revisada.

### Escopo deliberado
- sem instalar pacote.
- sem importar SDK em module load.
- sem chamar Vault/KMS real.
- sem alterar settings/env.
- sem expor segredo, reference path completo ou credencial.

## Owner MFA Vault/KMS Provider SDK Adapter Execution
- o provider Vault/KMS agora possui branch SDK lazy atrás de flag própria.
- implementação:
  - `accounts.infrastructure.owner_mfa_secret_providers`
- evidence query:
  - `accounts.application.owner_mfa_vault_kms_provider_sdk_adapter_execution_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_sdk_adapter_execute --tenant-id=<tenant_id> --target-provider=<provider> --probe-reference=<ref> --canary-owner-email=<email>`
- settings adicionados:
  - `OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED`;
  - `OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_STATUS`;
  - `OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_SECRETS`.
- o branch SDK:
  - só roda quando o real adapter e o SDK adapter estão habilitados;
  - importa SDKs de forma lazy dentro do resolver;
  - retorna `owner-mfa-secret-provider-vault-unavailable` se a dependência não existir;
  - preserva os resultados `ready`, `missing`, `timeout`, `permission-denied` e `invalid-reference`;
  - não imprime valor de segredo na evidência.

### Escopo deliberado
- sem chamada externa real ao Vault/KMS.
- sem credenciais reais.
- sem instalar dependência por conta própria.
- sem cache.
- sem escrita/migração.
- sem fallback automático para `env`.

## Owner MFA Vault/KMS Provider Real Endpoint Review
- o primeiro endpoint real aprovado para execução futura passa a ser `hashicorp-vault`.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_real_endpoint_review_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_real_endpoint_review --tenant-id=<tenant_id> --target-provider=hashicorp-vault --probe-reference=<ref> --canary-owner-email=<email> --endpoint-url-confirmed --auth-strategy-confirmed --secret-path-contract-confirmed --timeout-budget-confirmed --rollback-confirmed`
- contrato inicial de settings:
  - `OWNER_MFA_HASHICORP_VAULT_ADDR`;
  - `OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD`;
  - `OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT`;
  - `OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD`.
- métodos de auth aceitos no contrato:
  - `token`;
  - `approle`.
- a review exige:
  - branch SDK lazy ready;
  - endpoint/base URL confirmado;
  - auth strategy confirmada;
  - contrato de path/campo de segredo confirmado;
  - timeout budget confirmado;
  - rollback confirmado.

### Escopo deliberado
- sem implementar chamada real com `hvac`.
- sem credenciais reais.
- sem criar secret no Vault.
- sem imprimir path completo, segredo ou token.
- sem ativar produção.

## Owner MFA Hashicorp Vault Real Endpoint Execution
- o provider `hashicorp-vault` agora possui execução real via `hvac`, atrás de flag dedicada.
- implementação:
  - `accounts.infrastructure.owner_mfa_secret_providers`
- evidence query:
  - `accounts.application.owner_mfa_hashicorp_vault_real_endpoint_execution_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_real_endpoint_execute --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email>`
- settings adicionados:
  - `OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED`;
  - `OWNER_MFA_HASHICORP_VAULT_ADDR`;
  - `OWNER_MFA_HASHICORP_VAULT_AUTH_METHOD`;
  - `OWNER_MFA_HASHICORP_VAULT_TOKEN`;
  - `OWNER_MFA_HASHICORP_VAULT_ROLE_ID`;
  - `OWNER_MFA_HASHICORP_VAULT_SECRET_ID`;
  - `OWNER_MFA_HASHICORP_VAULT_SECRET_MOUNT`;
  - `OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD`.
- comportamento:
  - `hvac` é importado de forma lazy;
  - auth `token` e `approle` são suportados no contrato inicial;
  - leitura usa KV v2 com `mount_point` e `path` explícitos;
  - o campo de segredo vem de `OWNER_MFA_HASHICORP_VAULT_SECRET_FIELD`;
  - `ImportError`, timeout, permission denied e missing são mapeados para result codes seguros.

### Escopo deliberado
- sem instalar `hvac` automaticamente.
- sem ativar endpoint por padrão.
- sem cache.
- sem criação/migração de secrets no Vault.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Hashicorp Vault Staging Smoke Evidence
- o smoke staging do endpoint Hashicorp Vault agora possui evidência declarativa.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_staging_smoke_evidence_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_staging_smoke_evidence --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --staging-probe-passed --invalid-path-blocked --logs-redacted --rollback-verified --post-smoke-health-ready`
- a evidência exige:
  - execution real Hashicorp Vault ready;
  - probe staging reportada como aprovada;
  - path inválido reportado como bloqueado;
  - logs/stdout/evidence reportados como redigidos;
  - rollback verificado;
  - health pós-smoke reportado como ready.

### Escopo deliberado
- sem automatizar login/challenge.
- sem criar secret no Vault.
- sem alterar fator MFA.
- sem exportar evidência formal assinada.
- sem ativar produção.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Provider Production Readiness Review
- o provider Vault/KMS agora possui Go/No-Go consolidado para produção.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_production_readiness_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_production_readiness --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --runbook-reviewed --rollback-owner-confirmed --monitoring-confirmed --change-window-confirmed --credential-rotation-confirmed`
- a readiness compõe:
  - smoke staging Hashicorp Vault;
  - provider health closure;
  - confirmations operacionais de runbook, monitoramento, rollback owner, janela e rotação de credencial.
- decisão:
  - `GO` quando smoke, health e confirmations estão ready;
  - `NO-GO` quando qualquer blocker permanece.

### Escopo deliberado
- sem alterar flags/env.
- sem ativar produção.
- sem executar rollback.
- sem exportar evidência formal assinada.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Hashicorp Vault Production Gate Review
- o provider Hashicorp Vault agora possui gate operacional de ativação por tenant.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_production_gate_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_production_gate --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --tenant-scope-confirmed --rollout-order-confirmed --feature-flags-confirmed --support-standby-confirmed --rollback-window-confirmed --post-activation-monitoring-confirmed`
- o gate exige:
  - production readiness `GO`;
  - tenant canário confirmado;
  - ordem de rollout confirmada;
  - flags de ativação revisadas;
  - plantão/suporte confirmado;
  - janela de rollback confirmada;
  - monitoramento pós-ativação confirmado.
- saída:
  - `GO` libera a próxima trilha de activation evidence;
  - `NO-GO` lista blockers operacionais sem alterar ambiente.

### Escopo deliberado
- sem alterar flags/env.
- sem executar deploy/restart.
- sem ativar produção.
- sem criar secret no Vault.
- sem executar rollback.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Provider Production Activation Evidence
- a ativação production do provider Vault/KMS agora possui evidência declarativa pós-gate.
- query service:
  - `accounts.application.owner_mfa_vault_kms_provider_production_activation_evidence_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_provider_production_activation_evidence --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --deployment-completed --flags-enabled-for-tenant --post-deploy-probe-passed --owner-login-challenge-passed --provider-health-ready --rollback-not-required --evidence-redacted`
- a evidência exige:
  - production gate `GO`;
  - deploy/restart reportado como concluído;
  - flags reportadas como habilitadas para o tenant;
  - probe pós-deploy reportada como aprovada;
  - login/challenge owner reportado como aprovado;
  - provider health reportado como ready;
  - rollback reportado como não necessário;
  - evidência reportada como redigida.

### Escopo deliberado
- sem executar deploy/restart.
- sem alterar flags/env.
- sem chamar rollback.
- sem criar ou migrar secrets.
- sem exportar evidência formal assinada.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Hashicorp Vault Post-Activation Monitoring Review
- o endpoint Hashicorp Vault agora possui classificação operacional pós-ativação.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_post_activation_monitoring_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_post_activation_monitoring --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --monitoring-window-elapsed --provider-health-stable --owner-login-error-spike-absent --support-incidents-absent --rollback-signal-absent --evidence-redacted`
- classificações:
  - `HEALTHY`: janela completa, health estável, sem spike, sem incidentes, sem rollback signal e evidence redigida;
  - `WATCH`: activation ready, mas algum sinal leve ainda exige observação;
  - `ROLLBACK`: rollback signal presente;
  - `BLOCKED`: activation evidence ainda não está pronta.

### Escopo deliberado
- sem executar rollback automaticamente.
- sem expandir tenants automaticamente.
- sem alterar flags/env.
- sem criar tickets/incidentes.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Production Closure Review
- a trilha production do provider Vault/KMS MFA owner/admin agora possui closure explícito.
- query service:
  - `accounts.application.owner_mfa_vault_kms_production_closure_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_production_closure --tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --monitoring-window-elapsed --provider-health-stable --owner-login-error-spike-absent --support-incidents-absent --rollback-signal-absent --evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented`
- o closure exige:
  - post-activation monitoring `HEALTHY`;
  - runbook de rollback confirmado;
  - riscos residuais aceitos;
  - plano de expansão por tenant documentado.

### Escopo deliberado
- sem executar rollback.
- sem expandir tenants automaticamente.
- sem alterar flags/env.
- sem acessar, criar ou migrar secrets.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Hashicorp Vault Tenant Expansion Review
- a expansão do provider Hashicorp Vault agora possui review tenant-by-tenant antes de qualquer rollout real.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_tenant_expansion_review --canary-tenant-id=<tenant_id> --target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --monitoring-window-elapsed --provider-health-stable --owner-login-error-spike-absent --support-incidents-absent --rollback-signal-absent --evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed`
- a review exige:
  - closure `READY` do tenant canário;
  - lista explícita de tenants-alvo ativos e fora de maintenance mode;
  - janela de expansão confirmada;
  - evidência obrigatória por tenant;
  - suporte e rollback window confirmados;
  - primeira expansão limitada a um tenant por janela.

### Escopo deliberado
- sem ativar provider para tenants-alvo.
- sem alterar flags/env.
- sem executar rollback.
- sem criar ou migrar secrets.
- sem tratar evidência do tenant canário como autorização global.

## Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution
- a primeira expansão para tenant-alvo agora possui evidência declarativa própria.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_tenant_expansion_evidence --canary-tenant-id=<tenant_id> --target-tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --monitoring-window-elapsed --provider-health-stable --owner-login-error-spike-absent --support-incidents-absent --rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --evidence-redacted`
- a evidência exige:
  - tenant expansion review `READY`;
  - flags habilitadas para o target fora do command;
  - activation evidence capturada para o target;
  - monitoring pós-expansão agendado para o target;
  - login/challenge e provider health do target saudáveis;
  - rollback não requerido;
  - evidência redigida.

### Escopo deliberado
- sem ativar flags/env.
- sem executar rollback.
- sem chamar expansão global.
- sem criar ou migrar secrets.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review
- o tenant-alvo expandido agora possui classificação própria de monitoring pós-expansão.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_target_post_expansion_monitoring --canary-tenant-id=<tenant_id> --target-tenant-id=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --canary-monitoring-window-elapsed --canary-provider-health-stable --canary-owner-login-error-spike-absent --canary-support-incidents-absent --canary-rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --expansion-evidence-redacted --target-monitoring-window-elapsed --target-provider-health-stable --target-owner-login-error-spike-absent --target-support-incidents-absent --target-rollback-signal-absent --evidence-redacted`
- classificações:
  - `HEALTHY`: target validado, janela concluída, health estável, sem spike, sem incidentes, sem rollback signal e evidence redigida;
  - `WATCH`: evidence ready, mas algum sinal do target ainda exige observação;
  - `ROLLBACK`: rollback signal presente no target;
  - `BLOCKED`: evidence de expansão ainda não está pronta.

### Escopo deliberado
- sem liberar próximo tenant automaticamente.
- sem alterar flags/env.
- sem executar rollback.
- sem criar incidentes/tickets.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Hashicorp Vault Next Tenant Expansion Review
- a cadência de expansão Hashicorp Vault agora possui decisão explícita entre seguir, pausar ou bloquear.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_next_tenant_expansion_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_next_tenant_expansion_review --canary-tenant-id=<tenant_id> --current-target-tenant-id=<tenant_id> --next-target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --canary-monitoring-window-elapsed --canary-provider-health-stable --canary-owner-login-error-spike-absent --canary-support-incidents-absent --canary-rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --expansion-evidence-redacted --target-monitoring-window-elapsed --target-provider-health-stable --target-owner-login-error-spike-absent --target-support-incidents-absent --target-rollback-signal-absent --evidence-redacted --next-window-confirmed --operator-capacity-confirmed --previous-target-evidence-archived`
- status:
  - `READY`: target atual está `HEALTHY`, próximo target é válido e cadência está confirmada;
  - `PAUSED`: operador decidiu parar após o target atual;
  - `BLOCKED`: monitoring atual não está saudável ou próximo target/cadência não passou.

### Escopo deliberado
- sem ativar próximo tenant.
- sem alterar flags/env.
- sem executar rollback.
- sem criar ou migrar secrets.
- sem pular tenant expansion review/evidence/monitoring do próximo ciclo.

## Owner MFA Hashicorp Vault Expansion Cadence Closure Review
- a cadência de expansão Hashicorp Vault agora possui closure operacional explícito.
- query service:
  - `accounts.application.owner_mfa_hashicorp_vault_expansion_cadence_closure_queries`
- comando:
  - `python manage.py owner_mfa_hashicorp_vault_expansion_cadence_closure --canary-tenant-id=<tenant_id> --current-target-tenant-id=<tenant_id> --next-target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --canary-monitoring-window-elapsed --canary-provider-health-stable --canary-owner-login-error-spike-absent --canary-support-incidents-absent --canary-rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --expansion-evidence-redacted --target-monitoring-window-elapsed --target-provider-health-stable --target-owner-login-error-spike-absent --target-support-incidents-absent --target-rollback-signal-absent --evidence-redacted --next-window-confirmed --operator-capacity-confirmed --previous-target-evidence-archived --cadence-decision-recorded --evidence-archive-complete --residual-risks-reviewed --rotation-runbook-queued --audit-evidence-ready`
- o closure aceita cadência:
  - `READY`: próximo ciclo pode ser considerado, mas ainda exige nova review/evidence/monitoring;
  - `PAUSED`: cadência encerrada sem blocker operacional;
  - `BLOCKED`: closure bloqueia até resolver cadência anterior.
- exige decisão registrada, evidência arquivada, riscos revisados, rotação/runbook na fila e evidence auditável pronta.

### Escopo deliberado
- sem ativar próximo tenant.
- sem alterar flags/env.
- sem executar rollback.
- sem exportar evidência formal.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Rotation Runbook Review
- a rotação Vault/KMS MFA owner/admin agora possui runbook operacional verificável.
- query service:
  - `accounts.application.owner_mfa_vault_kms_rotation_runbook_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_rotation_runbook --canary-tenant-id=<tenant_id> --current-target-tenant-id=<tenant_id> --next-target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --canary-monitoring-window-elapsed --canary-provider-health-stable --canary-owner-login-error-spike-absent --canary-support-incidents-absent --canary-rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --expansion-evidence-redacted --target-monitoring-window-elapsed --target-provider-health-stable --target-owner-login-error-spike-absent --target-support-incidents-absent --target-rollback-signal-absent --evidence-redacted --next-window-confirmed --operator-capacity-confirmed --previous-target-evidence-archived --cadence-decision-recorded --evidence-archive-complete --residual-risks-reviewed --rotation-runbook-queued --audit-evidence-ready --rotation-scope-documented --rotation-owner-confirmed --vault-access-validated --rotation-window-confirmed --rollback-credentials-available --post-rotation-probe-defined --affected-tenants-listed --evidence-redaction-confirmed`
- exige:
  - expansion cadence closure `READY`;
  - escopo de rotação documentado;
  - owner de rotação confirmado;
  - acesso ao Vault validado;
  - janela de rotação confirmada;
  - credenciais de rollback disponíveis;
  - probe pós-rotação definido;
  - tenants afetados listados;
  - redaction de evidência confirmada.

### Escopo deliberado
- sem gerar token/AppRole.
- sem atualizar secret/configuração.
- sem executar rotação ou rollback.
- sem alterar flags/env.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Rotation Evidence Execution
- a rotação Vault/KMS MFA owner/admin agora possui evidence pack declarativo pós-execução.
- query service:
  - `accounts.application.owner_mfa_vault_kms_rotation_evidence_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_rotation_evidence --canary-tenant-id=<tenant_id> --current-target-tenant-id=<tenant_id> --next-target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --canary-monitoring-window-elapsed --canary-provider-health-stable --canary-owner-login-error-spike-absent --canary-support-incidents-absent --canary-rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --expansion-evidence-redacted --target-monitoring-window-elapsed --target-provider-health-stable --target-owner-login-error-spike-absent --target-support-incidents-absent --target-rollback-signal-absent --evidence-redacted --next-window-confirmed --operator-capacity-confirmed --previous-target-evidence-archived --cadence-decision-recorded --evidence-archive-complete --residual-risks-reviewed --rotation-runbook-queued --audit-evidence-ready --rotation-scope-documented --rotation-owner-confirmed --vault-access-validated --rotation-window-confirmed --rollback-credentials-available --post-rotation-probe-defined --affected-tenants-listed --evidence-redaction-confirmed --rotation-executed --new-credential-active --old-credential-revoked-or-scheduled --post-rotation-probe-passed --owner-login-challenge-passed --provider-health-ready --rotation-rollback-not-required --rotation-evidence-redacted`
- a evidência exige:
  - rotation runbook `READY`;
  - rotação executada fora do command;
  - nova credencial ativa;
  - credencial antiga revogada ou com revogação agendada;
  - probe pós-rotação aprovado;
  - login/challenge owner aprovado;
  - provider health ready;
  - rollback não requerido;
  - evidence redigida.

### Escopo deliberado
- sem gerar token/AppRole.
- sem revogar credencial.
- sem atualizar secret/configuração.
- sem executar rollback.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Post-Rotation Monitoring Review
- o provider Vault/KMS agora possui classificação operacional pós-rotação.
- query service:
  - `accounts.application.owner_mfa_vault_kms_post_rotation_monitoring_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_post_rotation_monitoring --canary-tenant-id=<tenant_id> --current-target-tenant-id=<tenant_id> --next-target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> --canary-monitoring-window-elapsed --canary-provider-health-stable --canary-owner-login-error-spike-absent --canary-support-incidents-absent --canary-rollback-signal-absent --canary-evidence-redacted --rollback-runbook-confirmed --residual-risks-accepted --tenant-expansion-plan-documented --expansion-window-confirmed --per-tenant-evidence-required --support-standby-confirmed --rollback-window-confirmed --target-flags-enabled --target-activation-evidence-captured --target-monitoring-scheduled --target-owner-login-challenge-passed --target-provider-health-ready --rollback-not-required --expansion-evidence-redacted --target-monitoring-window-elapsed --target-provider-health-stable --target-owner-login-error-spike-absent --target-support-incidents-absent --target-rollback-signal-absent --evidence-redacted --next-window-confirmed --operator-capacity-confirmed --previous-target-evidence-archived --cadence-decision-recorded --evidence-archive-complete --residual-risks-reviewed --rotation-runbook-queued --audit-evidence-ready --rotation-scope-documented --rotation-owner-confirmed --vault-access-validated --rotation-window-confirmed --rollback-credentials-available --post-rotation-probe-defined --affected-tenants-listed --evidence-redaction-confirmed --rotation-executed --new-credential-active --old-credential-revoked-or-scheduled --post-rotation-probe-passed --owner-login-challenge-passed --provider-health-ready --rotation-rollback-not-required --rotation-evidence-redacted --post-rotation-window-elapsed --provider-health-stable --owner-login-error-spike-absent --support-incidents-absent --rollback-signal-absent --post-rotation-evidence-redacted`
- classificações:
  - `HEALTHY`: rotação validada, janela concluída, health estável, sem spike, sem incidentes, sem rollback signal e evidence redigida;
  - `WATCH`: rotation evidence ready, mas algum sinal pós-rotação ainda exige observação;
  - `ROLLBACK`: rollback signal presente após rotação;
  - `BLOCKED`: rotation evidence ainda não está pronta.

### Escopo deliberado
- sem retomar expansão automaticamente.
- sem restaurar credencial.
- sem alterar flags/env.
- sem executar rollback.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Vault/KMS Rotation Closure Review
- a rotação Vault/KMS MFA owner/admin agora possui closure explícito após monitoramento pós-rotação.
- query service:
  - `accounts.application.owner_mfa_vault_kms_rotation_closure_queries`
- comando:
  - `python manage.py owner_mfa_vault_kms_rotation_closure --canary-tenant-id=<tenant_id> --current-target-tenant-id=<tenant_id> --next-target-tenant-ids=<tenant_id> --probe-reference=<ref> --canary-owner-email=<email> ... --post-rotation-evidence-redacted --rotation-closure-decision-recorded --rotation-evidence-archived --closure-residual-risks-accepted --expansion-resume-plan-documented --rollback-window-closed-or-extended --closure-audit-evidence-ready`
- classificações:
  - `READY`: monitoring pós-rotação `HEALTHY`, decisão registrada, evidência arquivada, riscos aceitos, plano de retomada documentado, rollback window resolvida e audit evidence pronta;
  - `WATCH`: monitoring pós-rotação ainda exige observação;
  - `ROLLBACK`: monitoring pós-rotação sinaliza rollback;
  - `BLOCKED`: closure signals obrigatórios ainda estão ausentes.

### Escopo deliberado
- sem retomar expansão automaticamente.
- sem restaurar credencial.
- sem alterar flags/env.
- sem executar rollback.
- sem exportar evidência auditável formal.
- sem imprimir segredo, token, role secret ou path completo.

## Owner MFA Track Closure Review
- a trilha MFA owner/admin agora possui closure operacional final após evidência auditável.
- query service:
  - `accounts.application.owner_mfa_track_closure_queries`
- comando:
  - `python manage.py owner_mfa_track_closure --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved --artifact-delivered --retention-owner-confirmed --storage-decision-recorded --audit-residual-risks-accepted --mfa-track-decision-recorded --rollout-state-documented --support-handoff-completed --next-roi-decision-recorded --track-residual-risks-accepted`
- o closure valida:
  - evidência auditável MFA fechada pelo módulo `audit`;
  - decisão final da trilha MFA registrada;
  - estado de rollout/enforcement/rollback documentado;
  - handoff de suporte concluído;
  - próxima decisão de ROI registrada;
  - riscos residuais aceitos.

### Escopo deliberado
- sem ativar enforcement, provider ou tenant.
- sem exportar/reimprimir evidência.
- sem alterar `AuditLog`.
- sem alterar flags/env.
- sem executar rollback.

## Security ROI Re-Selection Review
- segurança agora possui re-seleção objetiva após closure MFA/Vault/Audit.
- query service:
  - `accounts.application.security_roi_reselection_queries`
- comando:
  - `python manage.py security_roi_reselection --tenant-id=<tenant_id> --expected-actions-confirmed --export-scope-documented --redaction-reviewed --recipient-approved --artifact-delivered --retention-owner-confirmed --storage-decision-recorded --audit-residual-risks-accepted --mfa-track-decision-recorded --rollout-state-documented --support-handoff-completed --next-roi-decision-recorded --track-residual-risks-accepted --api-key-surface-active`
- candidatos avaliados:
  - `API Key Governance Foundation Review`;
  - `Platform Owner Session Policy Hardening Review`;
  - `Owner MFA Audit Evidence Storage/Signature Review`;
  - `Owner MFA Hashicorp Vault Next Tenant Expansion Review`;
  - `System ROI Re-Selection Review`.
- a recomendação atual prioriza API keys quando a superfície programática está ativa.

### Escopo deliberado
- sem implementar a trilha escolhida.
- sem ativar tenant/provider/enforcement.
- sem alterar flags/env.
- sem reimprimir evidência auditável.
- sem criar evento novo.
