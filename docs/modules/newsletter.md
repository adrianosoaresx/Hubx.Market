# Newsletter

## Responsabilidade
Gerenciar opt-in de newsletter tenant-scoped e base inicial de contatos de retenção.

## Entidades principais
- NewsletterSubscriber

## Casos de uso
- capturar e-mail com consentimento explícito
- reativar inscrição de forma idempotente
- desativar inscrição
- listar inscritos por tenant no admin

## Regras de negócio
- inscrição pertence sempre a um tenant
- e-mail é único por tenant
- mesmo e-mail pode existir em lojas diferentes
- inscrição pública exige tenant resolvido por subdomínio
- opt-in registra origem, status e consentimento
- descadastro altera status, não remove o histórico
- campanhas, segmentação, automação e envio real ficam fora do primeiro corte

## Interfaces

- Storefront: `/newsletter/`
- Admin: `/ops/newsletter/`

## Application services

- `newsletter_subscription_commands`
- `admin_newsletter_queries`

## Status

Customer Retention & Lifecycle Messaging Foundation:

- modelo `NewsletterSubscriber` tenant-scoped
- opt-in público idempotente
- admin read-only de inscritos
- sem campanhas ou provider de envio
