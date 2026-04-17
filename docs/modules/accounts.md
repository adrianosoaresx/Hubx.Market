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
