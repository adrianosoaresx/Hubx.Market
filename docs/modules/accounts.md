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

## Fechamento de pedido na customer area
- a área do cliente agora também reflete melhor quando o pedido já chegou ao fim do ciclo operacional
- quando o pedido estiver com entrega concluída, o detalhe passa a comunicar melhor que:
  - a compra foi entregue com segurança
  - o histórico continua salvo na conta
  - o próximo passo natural já não é acompanhamento, e sim retorno opcional ao catálogo
- isso continua sem redesign e usando apenas os estados persistidos já existentes do pedido
