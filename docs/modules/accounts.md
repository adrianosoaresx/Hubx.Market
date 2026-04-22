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
