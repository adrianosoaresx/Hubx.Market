# Newsletter

## Responsabilidade
Gerenciar opt-in de newsletter tenant-scoped e base inicial de contatos de retenção.

## Entidades principais
- NewsletterSubscriber
- NewsletterCampaign

## Casos de uso
- capturar e-mail com consentimento explícito
- reativar inscrição de forma idempotente
- desativar inscrição
- listar inscritos por tenant no admin
- criar campanha
- enviar campanha para outbox de e-mail dos inscritos ativos

## Regras de negócio
- inscrição pertence sempre a um tenant
- e-mail é único por tenant
- mesmo e-mail pode existir em lojas diferentes
- inscrição pública exige tenant resolvido por subdomínio
- opt-in registra origem, status e consentimento
- descadastro altera status, não remove o histórico
- campanha pertence sempre ao tenant
- campanha em `sent` não é reenviada
- envio cria logs idempotentes em `notifications.EmailLog`
- envio considera apenas inscritos ativos do tenant atual
- descadastrados e inscritos de outros tenants não recebem campanha

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
- campanhas administrativas com outbox auditável
- sem provider externo específico dentro de `newsletter`

## Newsletter Campaign Admin Execution

- o módulo `newsletter` agora possui campanhas tenant-scoped.
- modelo:
  - `newsletter.models.NewsletterCampaign`.
- command service:
  - `newsletter.application.newsletter_campaign_commands`.
- admin query:
  - `newsletter.application.admin_newsletter_queries`.
- views:
  - `newsletter.interfaces.views.AdminNewsletterCampaignCreateView`;
  - `newsletter.interfaces.views.AdminNewsletterCampaignSendView`.
- URLs:
  - `/ops/newsletter/`;
  - `/ops/newsletter/campaigns/new/`;
  - `/ops/newsletter/campaigns/<campaign_id>/send/`.

### Regras

- criação exige `newsletter.manage`.
- envio exige `newsletter.manage`.
- leitura exige `newsletter.view`.
- `marketing`, `owner` e `admin` podem criar/enviar campanhas.
- `viewer` não recebe `newsletter.view` por padrão, porque a tela expõe e-mails de inscritos.
- envio filtra `NewsletterSubscriber.status=subscribed` dentro do tenant resolvido.
- cada destinatário gera `EmailLog` com `source_event=newsletter.campaign.sent`.
- idempotência é por `tenant_id + campaign_id + subscriber_id`.
- `NewsletterCampaign.recipient_count` registra a quantidade de inscritos ativos no envio.
- eventos de auditoria:
  - `newsletter.campaign_created`;
  - `newsletter.campaign_sent`.

### Escopo deliberado

- sem segmentação avançada além de inscritos ativos.
- sem agendamento.
- sem editor visual.
- sem A/B test.
- sem provider externo próprio no módulo `newsletter`.
- sem cobrança/limite por plano.
