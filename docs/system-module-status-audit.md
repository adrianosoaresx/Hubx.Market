# System Module Status Audit

Nota de leitura: este arquivo preserva o histórico das waves e contém matrizes antigas no início. Para a fotografia atual do que está implementado em 2026-06-30, use `docs/implementation-inventory.md`. As waves posteriores deste arquivo podem superseder estados registrados nas waves iniciais.

## Wave 1 — Module Inventory & Readiness Matrix

Data: 2026-04-25

Objetivo desta auditoria:

- consolidar o status real dos módulos do Hubx Market
- separar módulos maduros de módulos apenas documentados/skeleton
- identificar riscos para produção real
- orientar a próxima trilha com maior ROI

## Critérios de classificação

- **maduro**: possui modelo real, services, interfaces, testes, documentação e sinais operacionais suficientes para esta fase.
- **bom o suficiente**: já sustenta fluxo real ou operacional, mas ainda tem lacunas futuras conhecidas.
- **parcial**: possui alguma implementação útil, mas ainda não fecha o contrato funcional principal.
- **skeleton**: existe como módulo/documentação, mas ainda sem domínio persistido ou fluxo real relevante.
- **bloqueador**: impede produção real do escopo atual sem mitigação.

## Matriz de status

| Módulo | Domínio | Status | Evidência atual | Risco principal | Próximo passo recomendado |
| --- | --- | --- | --- | --- | --- |
| `tenants` | Platform | bom o suficiente | modelo `Tenant`, middleware/current tenant, testes básicos, docs | custom domain/maintenance ainda precisam governança operacional mais forte | revisar activation real de custom domain e tenant lifecycle |
| `accounts` | Platform | bom o suficiente | customer area, owner admin, `/ops/` cockpit, commands tenant-scoped, testes amplos | autenticação/owner identity ainda é mais operacional que auth completa de produção | consolidar auth/permissions owner-facing antes de produção multi-owner |
| `subscriptions` | Platform | skeleton | docs e estrutura de módulo, sem modelo real além de placeholder | SaaS billing/plano ainda não existe como enforcement | manter fora do MVP transacional ou criar contrato mínimo de plano |
| `audit` | Platform | skeleton | docs e estrutura de módulo, sem `AuditLog` real | ações sensíveis não têm trilha auditável persistida | priorizar se backoffice/admin real for para produção |
| `api_keys` | Platform | skeleton | docs e estrutura de módulo, sem entidade real | API pública/integradores ainda sem autenticação própria | adiar se API pública não estiver no MVP |
| `catalog` | Commerce | maduro | Product/ProductVariant/ProductImage, storefront/admin, PDP conversion, métricas, runbook, testes | merchandising ainda não mede conversão real por evento | próxima evolução deve ser analytics de PDP/cart, não mais copy |
| `customers` | Commerce | bom o suficiente | Customer/Address, admin, data issues, backfill, métricas/runbook, testes | CRM/segmentação ainda inicial | evoluir somente se retenção/suporte virar prioridade |
| `cart` | Commerce | skeleton | docs e estrutura, sem modelo real; checkout session faz papel de carrinho leve | carrinho persistente multi-item fora da sessão ainda não existe | decidir se carrinho real é necessário antes de avançar PDP/checkout |
| `checkout` | Commerce | maduro | CheckoutSession, activation, retry/reorder, recovery events, metrics/runbook, retention commands, testes | produção depende de ativação operacional/scrape/pruning | manter; só reabrir para carrinho real ou meios de pagamento reais |
| `orders` | Commerce | bom o suficiente | Order/OrderItem, admin, inventory exception flow, customer actions, tests | lifecycle ainda simplificado; eventos internos não são barramento completo | revisar lifecycle/status antes de fulfillment real pesado |
| `payments` | Commerce | bom o suficiente | attempts, hosted redirect/return, webhooks, alerts, docs/runbook, tests | provider real/refund/conciliação ainda faltam | próxima grande trilha financeira deve ser conciliação/refund, não UX leve |
| `shipping` | Commerce | maduro | Shipment, provider settings, tracking sync, admin, metrics/runbook, testes fortes | cotação/frete pré-checkout ainda é menos robusta que tracking pós-pedido | reabrir para quote real/SLA se logística virar prioridade |
| `coupons` | Commerce | skeleton | docs e estrutura, sem modelo/regra real | promoções/descontos não existem como domínio | priorizar se conversão pedir campanhas/cupons |
| `reviews` | Engagement | skeleton | docs e estrutura, sem modelo real | prova social ainda ausente na PDP/storefront | candidato forte para conversão, mas exige moderação e vínculo customer/order |
| `newsletter` | Engagement | skeleton | docs e estrutura, sem modelo real | captura/retention pré-compra ainda ausente | adiar ou criar opt-in mínimo se marketing for prioridade |
| `notifications` | Engagement | maduro | logs, dispatch, owner recipients, readiness, metrics/runbook, muitos testes | provider/env real ainda precisa ativação operacional | conectar com eventos reais quando produção avançar |
| `pages` | Engagement | skeleton | docs e estrutura, sem Page real | páginas institucionais/SEO básico ausentes | baixo risco para MVP, importante para storefront público |

## Leituras transversais

### Multi-tenant

- Os módulos críticos já têm boa disciplina de `tenant_id`: `catalog`, `checkout`, `customers`, `orders`, `payments`, `shipping`, `accounts`.
- Os skeletons ainda não representam risco cross-tenant porque praticamente não têm persistência real.
- O risco futuro aparece quando `audit`, `api_keys`, `subscriptions`, `cart`, `coupons`, `reviews`, `newsletter` e `pages` deixarem de ser skeleton: todos devem nascer tenant-scoped quando store-owned.

### Produção real

O sistema está mais forte em:

- storefront/PDP
- checkout session
- payments hosted/retry básico
- order/customer area
- shipping tracking/admin
- notifications/readiness
- admin operations inicial

Ainda não está completo em:

- billing SaaS/subscriptions
- audit trail persistido
- API keys pública
- cart persistente real
- coupons/promotions
- reviews/prova social
- páginas institucionais

### Observabilidade

Mais avançados:

- `catalog`
- `checkout`
- `customers`
- `payments`
- `shipping`
- `notifications`

Pouco ou nada observáveis:

- `accounts` fora do cockpit/admin
- `orders` fora de inventory exception
- skeleton modules

## Decisão objetiva

Não vale continuar refinando agora:

- checkout recovery
- payments UX leve
- shipping tracking
- notifications readiness
- admin merchant operations básico
- PDP copy/decision text

Essas áreas já estão boas o suficiente para esta fase.

## Próximas trilhas candidatas

### 1. Cart & Promotion Conversion Foundation

Por que:

- `cart` e `coupons` ainda são skeleton.
- PDP já consegue iniciar checkout, mas o sistema não tem carrinho persistente de produto/quantidade/cupom como domínio próprio.
- Isso afeta conversão, ticket médio e campanhas.

Escopo sugerido:

- contrato mínimo de cart tenant-scoped
- cart item por variant snapshot
- bridge PDP → cart → checkout session
- cupom mínimo aplicado no checkout/cart

Risco:

- médio, porque toca fluxo de compra.

### 2. Trust & Social Proof Foundation

Por que:

- `reviews` é skeleton.
- PDP conversion ganhou decision checks, mas ainda não tem prova social.
- Pode aumentar confiança sem mexer em payments/orders.

Escopo sugerido:

- Review model tenant-scoped
- vínculo opcional com Customer/Product
- aggregate rating em catalog/PDP
- admin moderation mínima

Risco:

- baixo/médio, desde que inicialmente leitura + moderação simples.

### 3. Platform Production Governance

Por que:

- `audit`, `subscriptions`, `api_keys` são skeleton.
- Se a meta for produção SaaS real com múltiplos lojistas, governança falta.

Escopo sugerido:

- AuditLog mínimo para admin actions
- subscription plan/status mínimo
- API key só se houver API pública

Risco:

- baixo funcional, alto valor operacional.

## Recomendação de sequência

Se o objetivo imediato é **produto/receita**:

1. **Cart & Promotion Conversion Foundation**
2. **Trust & Social Proof Foundation**
3. **Pages/SEO Storefront Foundation**

Se o objetivo imediato é **produção SaaS com segurança operacional**:

1. **Audit Trail Foundation**
2. **Subscription/Plan Enforcement**
3. **Owner Auth/Permissions Hardening**

## Próxima wave recomendada

**System Audit Wave 2 — Next Track Selection & Risk Cut**

Objetivo:

- escolher entre trilha de conversão (`cart/coupons/reviews`) e trilha de governança (`audit/subscriptions/auth`)
- definir o menor recorte executável sem reabrir módulos já bons o suficiente

## Wave 2 — Next Track Selection & Risk Cut

Esta wave transforma a matriz em decisão de rota.

### Trilhas comparadas

| Trilha | Módulos | ROI esperado | Risco | Timing recomendado |
| --- | --- | --- | --- | --- |
| Cart & Promotion Conversion Foundation | `cart`, `coupons`, `checkout`, `catalog` | alto para conversão/ticket médio | médio, porque toca fluxo de compra | próxima, se foco for produto/receita |
| Trust & Social Proof Foundation | `reviews`, `catalog`, `customers` | médio/alto para confiança na PDP | baixo/médio | boa segunda trilha de conversão |
| Platform Production Governance | `audit`, `subscriptions`, `accounts`, `tenants` | alto para produção SaaS real | baixo/médio funcional, alto impacto organizacional | próxima, se foco for operação SaaS/multi-lojista |
| Storefront Content/SEO Foundation | `pages`, `newsletter` | médio para aquisição/retention | baixo | depois de conversão transacional mínima |
| API/Public Integration Foundation | `api_keys` | baixo agora, alto só com API pública | médio | adiar até existir demanda real de integração |

### Corte de risco

#### Não reabrir agora

- `checkout recovery`
- `payments UX`
- `shipping tracking`
- `notifications readiness`
- `admin merchant operations`
- `PDP copy/decision strip`

Motivo:

- já estão bons o suficiente para esta fase
- reabrir agora tende a produzir refinamento incremental, não novo desbloqueio estrutural

#### Não priorizar agora

- `api_keys`
- `newsletter`
- `pages`

Motivo:

- são úteis, mas não desbloqueiam o gargalo transacional principal
- podem entrar depois como aquisição/retention/integração

#### Priorizar se o foco for receita

1. `cart`
2. `coupons`
3. `reviews`

Motivo:

- `cart` e `coupons` ainda são skeletons, mas estão diretamente entre PDP e checkout
- `reviews` aumenta confiança, mas não resolve a ausência de carrinho/promoção
- a PDP acabou de ganhar uma camada de decisão; o próximo gargalo natural é o que acontece depois do clique

#### Priorizar se o foco for produção SaaS

1. `audit`
2. `subscriptions`
3. `accounts` permissions/auth

Motivo:

- produção multi-lojista real exige trilha auditável, plano/status e permissões
- esses itens não aumentam conversão imediatamente, mas reduzem risco operacional

### Decisão recomendada

Para o estado atual do produto, a próxima abordagem recomendada é:

**Cart & Promotion Conversion Foundation**

Justificativa:

- o sistema já tem PDP, checkout session, payments e orders bons o suficiente
- `cart` ainda é skeleton, então o cliente pula direto da PDP para uma sessão de checkout
- isso limita:
  - compra multi-item
  - revisão de carrinho antes do checkout
  - aplicação de cupom
  - campanhas promocionais simples
  - analytics de intenção entre PDP e checkout
- `coupons` também é skeleton e deve entrar junto apenas como contrato mínimo, sem tentar construir motor promocional completo

### Escopo mínimo recomendado

Primeiro recorte:

- `Cart` tenant-scoped
- `CartItem` com snapshot mínimo de produto/variante
- um carrinho ativo por sessão/customer/tenant
- adicionar item a partir da PDP
- tela simples de carrinho
- bridge segura do carrinho para `CheckoutSession`

Segundo recorte:

- `Coupon` tenant-scoped
- validação mínima:
  - código ativo
  - desconto fixo ou percentual
  - validade básica
- aplicação no carrinho/checkout

Fora de escopo no início:

- regras avançadas de promoção
- combinações de cupons
- frete grátis promocional
- gift cards
- abandono de carrinho completo
- analytics avançado de funil

### Próxima wave recomendada

**Cart Foundation Wave 1 — Cart Domain Contract Review**

Objetivo:

- definir o contrato mínimo de `Cart`/`CartItem`
- decidir como ele se relaciona com `CheckoutSession`
- impedir que `cart` duplique regra de checkout, payment ou order

## Wave 3 — System Next ROI Track Selection Review

Esta wave revisa a recomendação anterior depois das trilhas executadas em `cart`, `coupons`, `checkout`, `payments` e operações financeiras.

### Atualização da matriz

| Módulo | Status anterior | Status revisado | Evidência nova | Próximo uso recomendado |
| --- | --- | --- | --- | --- |
| `cart` | skeleton | bom o suficiente | `Cart`, `CartItem`, `/cart/`, PDP add-to-cart, quantity/remove, handoff para checkout, idempotência e guardas de estoque | manter; reabrir só para analytics/abandonment |
| `coupons` | skeleton | bom o suficiente | `Coupon`, validação mínima, admin lite, snapshot cart → checkout → order, ledger `CouponRedemption`, reversão e agregados | manter; reabrir para campanhas avançadas apenas com demanda |
| `payments` | bom o suficiente | bom o suficiente/controlado | fechamento de financial operations; refund/reversal como fundação técnica, No-Go produção real | sair da fila ativa neste ciclo |
| `reviews` | skeleton | parcial | `ProductReview`, migration inicial e queries approved-only tenant-scoped | seguir para moderação admin/ops antes de PDP pública |
| `pages` | skeleton | skeleton | documentação/estrutura, sem surface real | bom candidato posterior para SEO/conteúdo |
| `audit` | skeleton | skeleton | sem `AuditLog` persistido | candidato se foco mudar para governança SaaS |
| `subscriptions` | skeleton | skeleton | sem enforcement real de plano | candidato se foco mudar para monetização SaaS/plano |

### Trilhas candidatas reavaliadas

| Trilha | ROI | Risco | Momento |
| --- | --- | --- | --- |
| Trust & Social Proof Foundation | alto para conversão PDP/storefront | baixo/médio | melhor próximo passo funcional |
| Platform Production Governance | alto para SaaS multi-lojista | médio organizacional | priorizar se produção com múltiplos owners for o objetivo imediato |
| Storefront Content/SEO Foundation | médio para aquisição | baixo | boa após prova social ou em paralelo documental |
| Cart/Coupon Advanced Promotions | médio | médio/alto | adiar; base mínima já existe |
| Payments/Refund Production | baixo agora | alto financeiro | adiar até evidência externa real |

### Decisão recomendada

Para o estado atual do produto, a próxima abordagem recomendada é:

**Trust & Social Proof Foundation**

Justificativa:

- `cart` e `coupons` deixaram de ser gargalo estrutural inicial.
- `payments` foi encerrado como operação financeira controlada, com produção real de refund bloqueada.
- `reviews` ainda é skeleton e atua diretamente na confiança da PDP antes do clique de compra.
- a primeira versão pode ser tenant-scoped, moderada e sem efeitos em checkout/payments/orders.

### Corte de risco

O primeiro recorte de reviews deve evitar:

- publicação automática sem moderação;
- edição pública livre;
- dependência obrigatória de pedido entregue;
- cálculo complexo de reputação;
- eventos/notificações;
- impacto em checkout, payment ou estoque.

### Escopo mínimo recomendado

- `ProductReview` tenant-scoped.
- vínculo com `Product`.
- campos mínimos:
  - rating
  - title
  - body
  - author/customer label
  - status `pending|approved|rejected`
- admin/ops moderation mínima.
- query de aggregate rating para PDP.
- storefront exibindo apenas reviews aprovadas.

### Próxima wave recomendada

**Trust & Social Proof Wave 1 — Product Review Domain Contract Review**

Objetivo:

- definir o contrato mínimo de reviews sem transformar o módulo em comunidade/social completo;
- decidir vínculo com customer/order;
- preservar tenant scope e moderação antes de qualquer exibição pública.

## Wave 4 — System ROI Re-Selection Review

Esta wave reabre a seleção de ROI depois do fechamento das trilhas de reviews, discovery/search, filtering, analytics de storefront, checkout copy/trust e hardening de entrega/pagamento.

### Leitura de estado

| Área | Estado revisado | Leitura prática |
| --- | --- | --- |
| `cart` / `coupons` | bom o suficiente | base de carrinho, cupom mínimo, handoff, ledger e reversão já cobrem o ciclo inicial |
| `catalog` / storefront discovery | maduro para esta fase | busca textual leve, sort público, facets, ranking, analytics e surfaces de conversão já foram tratados |
| `reviews` | bom o suficiente | contrato, moderação, submissão customer, elegibilidade, CTA e visibilidade PDP/cards já cobrem prova social inicial |
| `checkout` | maduro para esta fase | guardrails de etapa, métodos inválidos, copy/trust e promessa de entrega já reduzem risco customer-facing |
| `payments` / refunds | controlado, mas gateado | operação financeira tem base e evidência sandbox; produção real ainda depende de provider/gate externo |
| `shipping` | suficiente para promessa inicial | tracking/promise existem; quote real por CEP continua trilha futura separada |
| `pages` | bom o suficiente | páginas institucionais tenant-owned, admin lite e storefront published-only cobrem a fundação inicial |
| `newsletter` | bom o suficiente | opt-in tenant-scoped, admin read-only e status de inscrição cobrem a fundação inicial |
| `audit` | bom o suficiente | `AuditLog`, writer tenant-scoped, platform-scope explícito e admin read-only cobrem a fundação inicial |
| `subscriptions` | skeleton | monetização por plano continua gap importante, mas menos customer-facing |

### Candidatos reavaliados

| Próxima abordagem | ROI esperado | Risco | Decisão |
| --- | --- | --- | --- |
| Storefront Content & SEO Foundation | médio/alto para aquisição, confiança institucional e completude do storefront | baixo | recomendar agora |
| Platform Production Governance | alto para operação SaaS real multi-owner | médio organizacional | manter como próxima se foco virar produção/governança |
| Customer Retention & Lifecycle Messaging | médio para recompra e relacionamento | médio/baixo | bom depois de existir conteúdo/captura |
| Advanced Promotions / Personalization | médio, mas incremental | médio/alto | adiar; cupom mínimo já resolve a primeira necessidade |
| Provider/Shipping real production | alto apenas com tráfego/operador real | alto externo/financeiro/logístico | adiar até evidência operacional |

### Decisão recomendada

A próxima abordagem de maior ROI ajustado por risco é:

**Storefront Content & SEO Foundation Review**

Motivo:

- as principais superfícies transacionais e de conversão já receberam fundação suficiente para esta fase;
- continuar micro-endurecendo checkout/cart/PDP tende a gerar retorno menor;
- `pages` ainda é skeleton e deixa a loja sem páginas institucionais tenant-owned, conteúdo de confiança e base SEO simples;
- o recorte é baixo risco porque pode nascer read-only/published-only, sem tocar checkout, pagamentos, pedidos ou estoque;
- a evolução também prepara terreno para newsletter/retention sem antecipar automação de marketing.

### Escopo mínimo recomendado

- definir `Page` tenant-scoped em `pages`;
- suportar slug, título, conteúdo simples, status publicado/rascunho e metadados SEO mínimos;
- criar query service público que só retorna páginas publicadas do tenant resolvido;
- criar admin lite para listagem/criação/edição simples;
- expor rotas storefront seguras para páginas institucionais;
- preservar views finas e regra em `pages.application`.

Fora de escopo:

- page builder;
- rich editor avançado;
- menus/nav builder;
- tradução/localização;
- SEO engine automatizado;
- newsletter automation;
- conteúdo global compartilhado entre tenants.

### Próxima abordagem recomendada

**Storefront Content & SEO Foundation Review**

Objetivo:

- transformar `pages` de skeleton em contrato tenant-owned mínimo;
- melhorar aquisição/confiança pública sem reabrir checkout/cart/payments;
- manter a próxima evolução alinhada a ROI de produto, não a refinamento marginal de fluxos já bons o suficiente.

### Fechamento da abordagem

Status: **Go** para esta fase.

Entregue:

- `Page` tenant-scoped com slug único por tenant;
- admin lite para listar, criar e editar páginas;
- rota pública `/pages/<slug>/` exibindo apenas páginas publicadas;
- SEO básico por página;
- link operacional no cockpit `/ops/`;
- documentação de domínio, ERD, boundaries e decisão arquitetural.

Fora de escopo mantido:

- page builder;
- menus/footer dinâmicos;
- preview de rascunho;
- tradução;
- SEO engine;
- captura newsletter;
- analytics de conteúdo.

## Wave 5 — Customer Retention & Lifecycle Messaging Review

Esta wave executa a fundação mínima de retenção após `pages` deixar de ser skeleton.

### Decisão de escopo

O primeiro recorte de retenção deve ser **newsletter opt-in**, não campanhas.

Motivo:

- `newsletter` ainda era skeleton e bloqueava captura explícita de interesse;
- `pages` agora fornece base institucional para aquisição/confiança;
- um opt-in tenant-scoped é baixo risco e não toca checkout, pagamentos, pedidos ou estoque;
- campanhas, automação e envio real exigiriam fronteira futura com `notifications`.

### Entregue

- `NewsletterSubscriber` tenant-scoped;
- e-mail único por tenant;
- status `subscribed|unsubscribed`;
- origem e consentimento do opt-in;
- comando idempotente de inscrição/reativação;
- comando de descadastro por status;
- rota pública `/newsletter/`;
- admin read-only `/ops/newsletter/`;
- documentação de domínio, ERD e boundaries.

### Fechamento da abordagem

Status: **Go** para esta fase.

Fora de escopo mantido:

- campanhas;
- segmentação;
- automação lifecycle;
- envio real;
- integração direta com `notifications`;
- popups/embedded forms em todas as páginas;
- tracking/analytics de conversão de newsletter.

### Próxima abordagem recomendada

**System ROI Re-Selection Review**

Objetivo:

- reavaliar se o próximo maior ROI está em governança SaaS (`audit`/`subscriptions`/permissions), retention avançada ou melhorias operacionais específicas.

## Wave 6 — Platform Production Governance Review

Esta wave inicia a governança SaaS por `audit`, antes de billing/plans ou permissions avançadas.

### Decisão de escopo

O primeiro recorte de governança deve ser **Audit Trail Foundation**.

Motivo:

- `audit` era skeleton e produção multi-lojista precisa de rastreabilidade mínima;
- `subscriptions` e permissions são maiores e dependem de política operacional;
- audit log pode nascer read-only, tenant-scoped e sem efeito colateral;
- instrumentar todos os módulos de uma vez aumentaria risco e ruído.

### Entregue

- `AuditLog` persistido;
- writer `audit_log_commands.record_event(...)`;
- tenant obrigatório por padrão;
- platform-scope apenas com opt-in explícito;
- metadados sanitizados;
- admin read-only `/ops/audit/`;
- link operacional no cockpit `/ops/`;
- testes de tenant-scope, platform-scope e filtro admin.

### Fechamento da abordagem

Status: **Go** para esta fase.

Fora de escopo mantido:

- hooks automáticos globais;
- middleware de auditoria;
- diff de models;
- trilha imutável/append-only com assinatura;
- retenção/pruning;
- exportação;
- permissões avançadas por owner;
- subscriptions/plan enforcement.

### Próxima abordagem recomendada

**Platform Governance Instrumentation Review**

Objetivo:

- escolher quais 2–3 ações administrativas sensíveis devem começar a chamar `audit_log_commands`, sem transformar audit em logging genérico.

## Wave 7 — Platform Governance Instrumentation Review

Esta wave escolhe as primeiras ações sensíveis para alimentar `AuditLog` a partir de application services existentes.

### Decisão de escopo

O recorte inicial fica limitado a:

- criação de cupom, por impacto comercial/financeiro;
- criação e edição de página, por impacto público/SEO;
- aprovação e rejeição de review, por impacto em prova social e confiança.

### Entregue

- `coupon.created` em `coupons.application.admin_coupon_commands`;
- `page.created` e `page.updated` em `pages.application.admin_page_commands`;
- `review.approved` e `review.rejected` em `reviews.application.admin_review_commands`;
- actor label vindo da surface admin quando disponível;
- testes cobrindo tenant-scope e metadados essenciais.

### Fechamento da abordagem

Status: **Go** para esta fase.

Fora de escopo mantido:

- middleware global de auditoria;
- log de leitura;
- diff genérico de models;
- instrumentação de todas as actions admin;
- política de retenção/exportação.

### Próxima abordagem recomendada

**Platform Governance Permission Review**

Objetivo:

- revisar se o próximo maior ganho em governança está em permissões administrativas por papel antes de ampliar a instrumentação do audit log.

## Wave 8 — Platform Governance Permission Review

Esta abordagem executa as Waves 1–5 do primeiro contrato de permissões administrativas.

### Wave 1 — Admin Role/Permission Contract Review

O contrato atual usa `OwnerUser.role` como fonte mínima de papel administrativo.

Papéis iniciais:

- `owner`;
- `admin`;
- `marketing`;
- `content_editor`;
- `support`;
- `viewer`.

### Wave 2 — Sensitive Action Permission Matrix

A matriz inicial cobre apenas as ações já auditadas:

- `coupons.manage`;
- `pages.manage`;
- `reviews.moderate`.

### Wave 3 — Minimal Permission Enforcement Plan

O enforcement fica em commands de aplicação, não nas views:

- views resolvem `actor_role` quando possível;
- commands consultam `accounts.application.admin_permissions`;
- ausência de `actor_role` preserva compatibilidade legada temporária;
- permissões negadas bloqueiam a mutação antes de gravar `AuditLog`.

### Wave 4 — First Enforcement Execution

Entregue:

- `coupon-permission-denied` em criação de cupom;
- `page-permission-denied` em criação/edição de página;
- `review-permission-denied` em moderação de review;
- lookup tenant-scoped de role por e-mail ativo em `OwnerUser`;
- testes de matriz, tenant-scope e bloqueio sem efeito colateral.

### Wave 5 — Governance Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- autenticação/admin middleware definitivo;
- grupos/permissões do Django;
- UI de edição de roles;
- permissões por objeto;
- log genérico de tentativas negadas;
- IAM completo de plataforma.

### Próxima abordagem recomendada

**Platform Owner Access Management Review**

Objetivo:

- decidir se o próximo ganho deve ser uma surface segura para criar/editar roles de `OwnerUser` ou um middleware explícito que injete `request.owner_user` em todas as surfaces `/ops/`.

## Wave 9 — Platform Owner Access Management Review

Esta abordagem escolhe a surface mínima de gestão de `OwnerUser` como próximo ganho, antes de impor middleware global obrigatório.

### Decisão de escopo

O recorte seguro é:

- criar owner por tenant;
- editar role, status ativo e notificações;
- manter e-mail único por tenant;
- usar `owners.manage` para bloquear mutações quando houver `actor_role`;
- registrar mudanças executadas em `AuditLog`.

Motivo:

- o permission gate já depende de `OwnerUser.role`;
- sem uma surface de gestão, roles ficariam operáveis só por seed/admin técnico;
- middleware obrigatório ainda seria cedo demais porque o shell `/ops/` mantém compatibilidade legada sem autenticação owner real completa.

### Entregue

- `accounts.application.admin_owner_commands.create_owner(...)`;
- `accounts.application.admin_owner_commands.update_owner_access(...)`;
- permission key `owners.manage`;
- rotas `/ops/owners/new/` e `/ops/owners/<id>/edit/`;
- template `admin_owner_form_page.html`;
- eventos `owner.created` e `owner.access_updated`;
- testes de criação, edição, duplicidade, tenant-scope e bloqueio por papel.

### Fechamento da abordagem

Status: **Go** para esta fase.

Fora de escopo mantido:

- convite/ativação por e-mail;
- autenticação real de owner;
- middleware obrigatório de `request.owner_user`;
- grupos/permissões nativas do Django;
- remoção física de owner;
- permissões por objeto.

### Próxima abordagem recomendada

**Platform Owner Context Middleware Review**

Objetivo:

- avaliar quando já vale resolver `request.owner_user` de forma centralizada nas surfaces `/ops/`, substituindo gradualmente o fallback por e-mail/role ausente.

## Wave 10 — Platform Owner Context Middleware Review

Esta abordagem centraliza o contexto do owner atual em superfícies `/ops/`.

### Wave 1 — Middleware Pipeline Review

O pipeline existente já resolvia tenant por subdomínio antes da view.

Decisão:

- manter `TenantSubdomainMiddleware` como fonte de `request.tenant`;
- inserir `OwnerContextMiddleware` depois de `AuthenticationMiddleware`;
- resolver owner apenas quando houver tenant e usuário Django autenticado.

### Wave 2 — Owner Context Contract

Contrato de `request.owner_user`:

- só existe em `/ops` e `/ops/...`;
- usa `tenant + request.user.email`;
- exige `OwnerUser.is_active=True`;
- não resolve em storefront/account customer-facing;
- quando não há match, permanece `None`.

### Wave 3 — Middleware Execution

Entregue:

- `accounts.interfaces.middleware.OwnerContextMiddleware`;
- registro no `MIDDLEWARE`;
- integração automática com views que já preferiam `request.owner_user`;
- preservação do fallback legado quando `owner_user` está ausente.

### Wave 4 — Context Enforcement Tests

Coberto:

- owner ativo é resolvido em `/ops/`;
- owner não é resolvido fora de `/ops/`;
- owner inativo/cross-tenant é ignorado;
- mutação em `/ops/owners/` passa a ser bloqueada quando o usuário autenticado tem role sem `owners.manage`;
- role `owner` autenticado mantém permissão de gestão.

### Wave 5 — Governance Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- obrigar login em todas as surfaces `/ops/`;
- bloquear request quando `request.owner_user` é `None`;
- remover todos os fallbacks por e-mail nas views;
- sessão dedicada de owner/admin;
- IAM completo de plataforma.

### Próxima abordagem recomendada

**Platform Ops Authentication Gate Review**

Objetivo:

- decidir quando `/ops/` deve exigir autenticação owner/admin obrigatória e transformar ausência de `request.owner_user` em bloqueio explícito, não compatibilidade.

## Wave 11 — Platform Ops Authentication Gate Review

Esta abordagem cria o gate HTTP de `/ops/`, mas com rollout seguro por ambiente.

### Wave 1 — Ops Surface Impact Review

`/ops/` já concentra várias superfícies administrativas e muitos testes legados ainda exercitam essas páginas sem login real.

Decisão:

- não ativar bloqueio default imediatamente;
- criar gate ativável por setting/env;
- manter compatibilidade enquanto `/accounts/login/` ainda é surface visual e não autenticação owner completa.

### Wave 2 — Gate Contract

Contrato quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`:

- request anônimo em `/ops/` redireciona para login com `next`;
- usuário autenticado sem `OwnerUser` ativo no tenant recebe `403`;
- usuário autenticado com `request.owner_user` ativo segue normalmente;
- storefront e área do cliente não são afetados.

### Wave 3 — Gate Execution

Entregue:

- `accounts.interfaces.middleware.OpsAuthenticationGateMiddleware`;
- registro no pipeline depois de `OwnerContextMiddleware`;
- setting `HUBX_OPS_AUTH_GATE_ENFORCED`;
- default desligado para rollout controlado.

### Wave 4 — Gate Tests

Coberto:

- redirect de anônimo;
- `403` para usuário autenticado sem owner ativo;
- liberação para usuário autenticado com `OwnerUser` ativo;
- preservação do owner context existente.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- autenticação real de owner via formulário;
- convite/ativação por e-mail;
- ativar o gate por default em todos os ambientes;
- remover fallbacks de role ausente;
- RBAC completo por objeto.

### Próxima abordagem recomendada

**Platform Owner Login Execution Review**

Objetivo:

- transformar `/accounts/login/` de surface visual em autenticação real de owner/admin para permitir ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1` com segurança.

## Wave 12 — Platform Owner Login Execution Review

Esta abordagem executa o login real mínimo de owner/admin sem abrir customer auth completo.

### Wave 1 — Login Surface Contract Review

Decisão:

- reaproveitar `/accounts/login/` como entrada inicial de owner/admin;
- manter a página customer-facing compatível no GET;
- executar autenticação real apenas no POST;
- exigir tenant resolvido por subdomínio para qualquer login owner.

### Wave 2 — Owner Authentication Command Execution

Entregue:

- `accounts.application.owner_login_commands`;
- autenticação via Django `User`;
- vínculo obrigatório com `OwnerUser` ativo no tenant atual;
- erro genérico para credencial, owner ausente, owner inativo ou tenant inválido.

### Wave 3 — Login/Logout HTTP Surface Execution

Entregue:

- POST em `/accounts/login/`;
- redirect seguro para `next` do mesmo host;
- fallback para `/ops/`;
- rota `/accounts/logout/` para encerrar sessão.

### Wave 4 — Audit + Safety Tests

Coberto:

- owner ativo autentica e redireciona;
- owner ausente no tenant atual é rejeitado;
- owner inativo é rejeitado;
- `next` externo é ignorado;
- logout limpa sessão;
- `owner.login` e `owner.logout` são registrados em `AuditLog`.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- customer login persistido;
- convite/ativação de owner por e-mail;
- reset de senha real;
- ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1` por default;
- MFA/SSO/IAM completo.

### Próxima abordagem recomendada

**Platform Ops Gate Activation Runbook Review**

Objetivo:

- definir checklist de ambiente para ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1` com usuários owner reais, rollback claro e validação de acesso por tenant.

## Wave 13 — Platform Ops Gate Activation Runbook Review

Esta abordagem transforma o gate de `/ops/` em rollout operável por ambiente.

### Wave 1 — Activation Preconditions Review

Pré-condições:

- tenant ativo precisa ter pelo menos um `OwnerUser` ativo;
- cada owner ativo usado para acesso precisa ter `User` Django ativo com o mesmo e-mail;
- e-mails ambíguos em `User` bloqueiam ativação segura;
- o login real de owner já deve estar validado com `next=/ops/`.

### Wave 2 — Readiness Command Execution

Entregue:

- comando `ops_auth_gate_readiness`;
- validação global ou por `--tenant-id`;
- relatório de blockers por tenant;
- opção `--fail-on-blockers` para CI/preflight.

### Wave 3 — Rollout Runbook

Fluxo recomendado:

1. executar `python manage.py ops_auth_gate_readiness --fail-on-blockers`;
2. corrigir owners/users bloqueantes;
3. validar login manual em `/accounts/login/?next=/ops/`;
4. ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
5. validar acesso owner/admin por tenant;
6. se necessário, rollback com `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

### Wave 4 — Rollout Tests

Coberto:

- tenant pronto;
- owner sem `User` Django;
- `User` Django inativo;
- e-mail ambíguo;
- saída não-zero quando `--fail-on-blockers` encontra blockers.

### Wave 5 — Closure Review

Status: **Go** para ativação controlada por ambiente.

Fora de escopo mantido:

- criar usuário owner automaticamente;
- reset/convite de senha;
- MFA;
- ativar o gate por default no código;
- IAM completo.

### Próxima abordagem recomendada

**Platform Owner Invitation & Password Recovery Review**

Objetivo:

- reduzir operação manual de criação de owner/user antes de ativar o gate em tenants reais, com convite ou reset de senha administrável.

## Wave 14 — Platform Owner Invitation & Password Recovery Review

Esta abordagem entrega o menor fluxo seguro de convite/reset para owners sem abrir IAM completo.

### Wave 1 — Contract Review

Decisão:

- convite pertence a `accounts`;
- convite exige `owners.manage`;
- reset usa token padrão Django;
- vínculo administrativo continua sendo `tenant + OwnerUser.email + User.email`;
- forgot password deve responder de forma genérica para evitar enumeração.

### Wave 2 — Invitation Command Execution

Entregue:

- `owner_access_recovery_commands.invite_owner(...)`;
- criação de `User` Django com senha inutilizável quando ainda não existe;
- reuso de `User` ativo existente;
- bloqueio para e-mail ambíguo ou user inativo;
- AuditLog `owner.invited`.

### Wave 3 — Password Recovery Execution

Entregue:

- POST em `/accounts/forgot-password/`;
- rota tokenizada `/accounts/reset-password/<uidb64>/<token>/`;
- conclusão de reset com validação de tenant e owner ativo;
- AuditLog `owner.password_reset_requested`;
- AuditLog `owner.password_reset_completed`.

### Wave 4 — Admin Surface Integration

Entregue:

- action `/ops/owners/<id>/actions/invite/`;
- botão “Gerar convite” na listagem operacional de owners;
- feedback de resultado via query param.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- envio real de e-mail;
- templates transacionais;
- activation flow por convite clicável em e-mail;
- MFA/SSO;
- política avançada de expiração além do token Django.

### Próxima abordagem recomendada

**Platform Owner Email Delivery Review**

Objetivo:

- plugar o link de convite/reset em um canal real de notifications/email sem misturar delivery dentro de `accounts.application`.

## Wave 15 — Platform Owner Email Delivery Review

Esta abordagem liga convite/reset owner/admin ao pipeline existente de notifications.

### Wave 1 — Notifications Boundary Review

Decisão:

- `accounts` continua dono de permissão, tenant, token e reset;
- `notifications` fica dono de `EmailLog` e entrega;
- não chamar `send_mail` nem provider diretamente em `accounts`.

### Wave 2 — Owner Access Email Command Execution

Entregue:

- `notifications.application.owner_access_email_commands`;
- log `owner.access.invite`;
- log `owner.access.password_reset`;
- mensagens owner/admin com link de reset na descrição.

### Wave 3 — Accounts Integration

Entregue:

- convite admin gera `EmailLog` planejado;
- forgot password válido gera `EmailLog` planejado;
- audit metadata passa a incluir `email_log_id`.

### Wave 4 — Delivery Tests

Coberto:

- registro de invite email;
- registro idempotente de reset email;
- convite via `/ops/owners/` cria `EmailLog`;
- forgot password válido cria `EmailLog`.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- HTML transacional;
- branding final de e-mail;
- fila automática dedicada ao convite;
- bounce/rejection handling;
- reset customer-facing.

### Próxima abordagem recomendada

**Platform Owner Access Closure Review**

Objetivo:

- revisar se o pacote owner access já permite ativar o gate em staging/produção ou se ainda há lacuna crítica antes do rollout.

## Wave 16 — Platform Owner Access Closure Review

Esta abordagem fecha a trilha owner access com decisão objetiva de prontidão.

### Wave 1 — Capability Inventory

Pronto:

- `OwnerUser` tenant-scoped;
- permissões iniciais por role;
- `OwnerContextMiddleware`;
- `OpsAuthenticationGateMiddleware`;
- login/logout owner/admin;
- readiness command para gate;
- convite e reset por token Django;
- delivery via `EmailLog` em notifications;
- auditoria de login, logout, convite e reset.

### Wave 2 — Validation

Validação técnica:

- testes focados de accounts/notifications passam;
- `python manage.py check` sem issues;
- `makemigrations --check --dry-run` sem mudanças.

Readiness local:

- status: **Blocked**
- motivo:
  - tenants ativos sem `OwnerUser` ativo;
  - `hubx-checkout-demo`;
  - `hubx-demo`.

### Wave 3 — Go/No-Go Decision

Decisão:

- **Go técnico** para ativar em staging/produção somente após preparar owners/users por tenant.
- **No-Go operacional** para qualquer tenant onde `ops_auth_gate_readiness --fail-on-blockers` falhar.

### Wave 4 — Closure

Fora de escopo mantido:

- MFA/SSO;
- RBAC granular por objeto;
- UI dedicada de processamento de e-mail;
- automação de criação do primeiro owner por tenant;
- política de expiração customizada de convite.

### Próxima abordagem recomendada

**Platform Initial Owner Provisioning Review**

Objetivo:

- resolver o blocker operacional restante criando um caminho seguro para provisionar o primeiro owner/user por tenant antes de ativar o gate.

## Wave 17 — Platform Initial Owner Provisioning Review

Esta abordagem remove o principal blocker operacional do gate: tenants sem owner/user inicial.

### Wave 1 — Provisioning Contract

Decisão:

- provisionamento inicial deve ser comando operacional, não cadastro público;
- comando exige `tenant_id` explícito;
- role inicial fica limitada a `owner` ou `admin`;
- `User` criado recebe senha inutilizável e deve seguir convite/reset;
- operação deve ser idempotente e auditada.

### Wave 2 — Command Execution

Entregue:

- `accounts.application.initial_owner_provisioning_commands`;
- management command `provision_initial_owner`;
- `--dry-run`;
- bloqueio para e-mail inválido, tenant inexistente/inativo, user inativo e user ambíguo.

### Wave 3 — Readiness Integration

Coberto:

- provisioning cria `OwnerUser` ativo;
- cria `User` Django ativo com senha inutilizável;
- `ops_auth_gate_readiness` passa para o tenant provisionado;
- chamada idempotente não duplica owner/user.

### Wave 4 — Closure Review

Status: **Go** para usar em staging/produção com execução controlada.

Fora de escopo mantido:

- endpoint público de bootstrap;
- criar owners em lote para todos os tenants;
- definir senha no comando;
- MFA/SSO;
- convite automático acoplado ao provisioning.

### Próxima abordagem recomendada

**Platform Ops Gate Staging Activation Review**

Objetivo:

- executar o checklist completo em staging: provisionar owner inicial, gerar convite, processar email/log, validar login e ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1`.

## Wave 18 — Platform Ops Gate Staging Activation Review

Esta abordagem cria o preflight objetivo para ativar o gate `/ops/` em staging.

### Wave 1 — Activation Contract

Contrato:

- ativação é feita por ambiente via `HUBX_OPS_AUTH_GATE_ENFORCED`;
- antes do switch, gate deve estar desativado e readiness deve passar;
- depois do switch, gate deve estar ativado e readiness deve continuar passando;
- provider de e-mail só é blocker quando `--require-email-delivery` for exigido.

### Wave 2 — Preflight Execution

Entregue:

- `accounts.application.ops_gate_activation_preflight_queries`;
- management command `ops_gate_activation_preflight`;
- flags:
  - `--tenant-id`;
  - `--expect-gate=disabled|enabled|any`;
  - `--require-email-delivery`;
  - `--fail-on-blockers`.

### Wave 3 — Tests

Coberto:

- preflight ready com gate desativado esperado;
- blocker quando gate deveria estar enabled;
- blocker quando e-mail real é exigido mas provider está em dry-run/incompleto;
- command retorna erro com `--fail-on-blockers`.

### Wave 4 — Staging Runbook

Sequência recomendada:

1. `provision_initial_owner`;
2. convite/reset;
3. processamento de `EmailLog` se aplicável;
4. preflight com `--expect-gate=disabled`;
5. ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
6. preflight com `--expect-gate=enabled`;
7. validação manual de login `/accounts/login/?next=/ops/`;
8. rollback com `HUBX_OPS_AUTH_GATE_ENFORCED=0`.

### Wave 5 — Closure Review

Status: **Go** para ativação controlada em staging quando o preflight passar.

Fora de escopo mantido:

- alterar env automaticamente;
- deploy/restart automático;
- ativar gate por default;
- testes browser end-to-end;
- MFA/SSO.

### Próxima abordagem recomendada

**Platform Ops Gate Production Rollout Review**

Objetivo:

- transformar o runbook de staging em rollout de produção com janelas, rollback, evidências e tenant-by-tenant checklist.

## Wave 19 — Platform Ops Gate Production Rollout Review

Esta abordagem cria o pacote de evidência para rollout do gate `/ops/` em produção.

### Wave 1 — Production Contract

Contrato:

- rollout é tenant-by-tenant;
- comando gera evidência, não altera ambiente;
- gate deve estar no estado esperado;
- provider de e-mail real é exigido por padrão;
- falhas de `EmailLog` bloqueiam rollout por padrão;
- pending delivery pode bloquear quando explicitamente solicitado.

### Wave 2 — Evidence Command Execution

Entregue:

- `accounts.application.ops_gate_production_rollout_queries`;
- management command `ops_gate_production_rollout`;
- flags:
  - `--tenant-id`;
  - `--expect-gate`;
  - `--allow-email-dry-run`;
  - `--allow-notification-failures`;
  - `--block-on-pending-delivery`;
  - `--fail-on-blockers`.

### Wave 3 — Evidence Tests

Coberto:

- evidence ready com gate enabled e provider real;
- blocker quando gate está disabled;
- blocker quando provider de e-mail não está pronto;
- blocker padrão para `EmailLog failed`;
- command falha com `--fail-on-blockers`.

### Wave 4 — Production Runbook

Sequência:

1. provisionar owner inicial se necessário;
2. gerar/processar convite ou reset;
3. evidência pré-switch com gate disabled;
4. ativar env `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
5. redeploy/restart;
6. evidência pós-switch;
7. validação manual de login owner;
8. rollback se qualquer etapa falhar.

### Wave 5 — Closure Review

Status: **Go** para rollout controlado quando evidência passar tenant-by-tenant.

Fora de escopo mantido:

- automação de deploy;
- change management externo;
- ativação global em lote;
- browser E2E automatizado;
- MFA/SSO.

### Próxima abordagem recomendada

**Platform Ops Gate Post-Activation Monitoring Review**

Objetivo:

- definir sinais mínimos para detectar falhas pós-ativação: redirects inesperados, 403 em `/ops/`, login failures e backlog/falhas de owner access emails.

## Wave 20 — Platform Ops Gate Post-Activation Monitoring Review

Esta abordagem adiciona sinais mínimos para monitorar o gate `/ops/` depois da ativação.

### Wave 1 — Signal Contract

Sinais escolhidos:

- `owner.login_failed`;
- `owner.ops_gate_forbidden`;
- `owner.ops_gate_redirected`;
- `owner.access.invite` por status de `EmailLog`;
- `owner.access.password_reset` por status de `EmailLog`.

### Wave 2 — Metrics Execution

Entregue:

- `accounts.application.owner_access_metrics_queries`;
- endpoint `/accounts/metrics/owner-access/`;
- setting `ACCOUNTS_OBSERVABILITY_TOKEN`;
- proteção por header `X-Hubx-Observability-Token` ou Bearer token.

### Wave 3 — Instrumentation

Entregue:

- falha de login owner registra `AuditLog owner.login_failed`;
- redirect anônimo do gate registra `owner.ops_gate_redirected`;
- bloqueio 403 do gate registra `owner.ops_gate_forbidden`.

### Wave 4 — Prometheus Rules

Entregue:

- scrape example de accounts;
- alert rules:
  - login failures;
  - gate forbidden;
  - anonymous redirects;
  - owner access email failures;
  - owner access email backlog.

### Wave 5 — Closure Review

Status: **Go** para ativar monitoramento junto do rollout do gate.

Fora de escopo mantido:

- dashboard Grafana dedicado;
- métricas de latência;
- rate limiting;
- detecção avançada de brute force;
- correlação por IP em Prometheus.

### Próxima abordagem recomendada

**Platform Owner Access Security Hardening Review**

Objetivo:

- revisar rate limiting, lockout leve, proteção contra brute force e endurecimento de sessão owner/admin.

## Wave 21 — Platform Owner Access Security Hardening Review

Esta abordagem adiciona proteção incremental contra brute force no login owner/admin.

### Wave 1 — Risk Review

Riscos priorizados:

- tentativas repetidas de senha no login owner/admin;
- enumeração por mensagem de erro;
- falta de sinal explícito quando o bloqueio defensivo aciona.

### Wave 2 — Rate Limit Execution

Entregue:

- `accounts.application.owner_access_rate_limit`;
- limite por tenant + login + IP;
- lockout via cache Django;
- `429` com `Retry-After`;
- limpeza de tentativas após login bem-sucedido.

### Wave 3 — Audit + Metrics

Entregue:

- `owner.login_rate_limited`;
- métrica Prometheus para o novo action;
- alerta `HubxAccountsOwnerLoginRateLimited`.

### Wave 4 — Tests

Coberto:

- falhas repetidas acionam lockout;
- tentativa correta durante lockout continua bloqueada;
- login bem-sucedido limpa tentativas;
- métricas exportam `owner.login_rate_limited`.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- MFA/SSO;
- captcha;
- bloqueio persistido em banco;
- rate limiting distribuído dedicado fora do cache Django;
- política avançada de sessão.

### Próxima abordagem recomendada

**Platform Owner Session Policy Review**

Objetivo:

- revisar duração de sessão, remember-me, logout seguro e políticas mínimas para sessões owner/admin.

## Wave 22 — Platform Owner Session Policy Review

Esta abordagem transforma a semântica de sessão owner/admin em contrato explícito e configurável.

### Wave 1 — Current Session Review

Achados:

- login owner já usava `django_login`;
- logout owner já chamava `django_logout` e auditava `owner.logout`;
- `remember_me` existia, mas dependia do default global quando marcado;
- sessão sem remember usava browser session, sem duração owner/admin explícita.

### Wave 2 — Policy Execution

Entregue:

- `accounts.application.owner_session_policy`;
- `OWNER_SESSION_IDLE_SECONDS`;
- `OWNER_SESSION_REMEMBER_SECONDS`;
- sessão curta por padrão;
- remember-me explícito com duração própria;
- marcadores internos de sessão owner.

### Wave 3 — Audit Contract

Entregue:

- `AuditLog owner.login` passa a registrar:
  - `session_expiry_seconds`;
  - `session_remembered`.

### Wave 4 — Tests

Coberto:

- login owner sem remember usa duração curta;
- login owner com remember usa duração longa;
- sessão owner recebe marcadores internos;
- audit log preserva a decisão de sessão aplicada.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- MFA/SSO;
- revogação centralizada;
- device/session management;
- rotação customizada além do comportamento padrão do Django;
- middleware próprio de idle timeout.

### Próxima abordagem recomendada

**Platform Admin RBAC Granularization Review**

Objetivo:

- revisar se `OwnerUser.role` e permissões atuais já são suficientes para separar owner/support/marketing em superfícies `/ops/` sem acoplamento manual por view.

## Wave 23 — Platform Admin RBAC Granularization Review

Esta abordagem reduz acoplamento manual de role nas views `/ops/` e torna actions administrativas coerentes com permissões.

### Wave 1 — RBAC Surface Review

Achados:

- `accounts.application.admin_permissions` já possuía matriz de roles;
- commands de owners, coupons, pages e reviews já bloqueavam writes sensíveis;
- algumas views ainda resolviam role manualmente;
- listagens ainda exibiam actions para roles sem permissão.

### Wave 2 — Shared Interface Helper

Entregue:

- `accounts.interfaces.admin_rbac`;
- resolução central de `tenant_id`;
- resolução central de role owner/admin;
- helper `request_admin_can(...)`.

### Wave 3 — Surface Granularization

Entregue:

- owners escondem criação/actions sem `owners.manage`;
- coupons escondem criação sem `coupons.manage`;
- pages escondem criação/edição sem `pages.manage`;
- reviews escondem criação/moderação sem `reviews.moderate`;
- criação admin de review agora bloqueia role sem permissão.

### Wave 4 — Tests

Coberto:

- role sem permissão não vê action sensível;
- role sem permissão não executa write sensível;
- compatibilidade legada sem role explícita preservada para ambientes com gate desligado.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- permission model persistido;
- grupos Django;
- UI para editar matriz de permissões;
- auditoria extra para tentativa negada de read/action visual;
- RBAC em storefront/customer.

### Próxima abordagem recomendada

**Platform Admin Navigation Personalization Review**

Objetivo:

- ajustar menus/cards do cockpit `/ops/` para esconder ou rebaixar módulos conforme permissões do owner/admin ativo.

## Wave 24 — Platform Admin Navigation Personalization Review

Esta abordagem aplica a matriz RBAC ao cockpit `/ops/`, reduzindo atalhos e filas visíveis conforme a role ativa.

### Wave 1 — Cockpit Review

Achados:

- o dashboard `/ops/` tinha atalhos hardcoded;
- a tabela de filas apontava para áreas que uma role poderia não acessar;
- o dashboard já era tenant-scoped, mas ainda não era permission-aware.

### Wave 2 — Navigation Permissions

Entregue:

- permissões leves de navegação/leitura:
  - `orders.view`;
  - `catalog.view`;
  - `customers.view`;
  - `shipping.view`;
  - `newsletter.view`;
  - `audit.view`;
  - `payments.view`.

### Wave 3 — Dashboard Execution

Entregue:

- atalhos do header filtrados por `request_admin_can(...)`;
- filas operacionais filtradas por permissão;
- activity feed e resumo usam o mesmo recorte filtrado;
- compatibilidade legada preservada quando não há role resolvida.

### Wave 4 — Tests

Coberto:

- support vê pedidos/clientes/reviews e não vê cupons/páginas/financeiro;
- marketing vê catálogo/cupons/páginas/reviews e não vê pedidos/clientes/refunds;
- filas de owners somem para role sem `owners.manage`;
- matriz de permissões cobre navegação por role.

### Wave 5 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- middleware granular por URL;
- personalização do shell lateral global;
- permissões persistidas/editáveis;
- auditoria de item ocultado;
- bloqueio de leitura em cada módulo operacional.

### Próxima abordagem recomendada

**Platform Ops URL Permission Enforcement Review**

Objetivo:

- decidir se as permissões do cockpit devem virar enforcement HTTP granular por rota `/ops/`, além da ocultação visual atual.

## Wave 25 — Platform Ops URL Permission Enforcement Review

Esta abordagem transforma a personalização visual do cockpit em proteção HTTP para URL direta sob `/ops/`.

### Wave 1 — Route Map Review

Achados:

- `/ops/` já estava protegido por owner ativo quando `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
- URLs diretas de módulos ainda dependiam apenas do gate geral;
- a matriz RBAC já tinha permissões suficientes para mapear prefixos.

### Wave 2 — Permission Prefix Contract

Entregue:

- mapa de prefixos `/ops/<módulo>/` para permissões;
- `/ops/` raiz liberado para owner/admin ativo;
- `checkout.view` adicionado como permissão de leitura operacional.

### Wave 3 — Middleware Enforcement

Entregue:

- `OpsAuthenticationGateMiddleware` valida permissão após autenticação owner/admin;
- negação retorna `403`;
- negação registra `owner.ops_permission_denied` com path, role, permission e reason.

### Wave 4 — Observability

Entregue:

- métrica `hubx_accounts_owner_access_audit_event_total{action="owner.ops_permission_denied"}`;
- alerta `HubxAccountsOpsPermissionDenied`.

### Wave 5 — Tests

Coberto:

- role sem permissão recebe `403` em URL direta;
- role com permissão acessa a URL direta;
- dashboard `/ops/` continua acessível para role limitada;
- métrica exporta o novo action.

### Wave 6 — Closure Review

Status: **Go** para esta fase.

Fora de escopo mantido:

- permissões por método HTTP;
- permission matrix persistida;
- UI para edição de RBAC;
- enforcement fora de `/ops/`;
- auditoria granular de item ocultado no cockpit.

### Próxima abordagem recomendada

**Platform RBAC Production Readiness Review**

Objetivo:

- revisar se roles/permissões atuais já estão prontas para ativação real do gate granular em staging/produção, incluindo runbook, rollback e evidências.

## Wave 26 — Platform RBAC Production Readiness Review

Esta abordagem adiciona evidência operacional para ligar RBAC granular em staging/produção sem depender só de revisão manual.

### Wave 1 — Readiness Contract

Critérios:

- gate no estado esperado;
- matriz `owner/admin` cobre todas as permissões de prefixos `/ops/`;
- tenant alvo possui ao menos um full admin ativo (`owner` ou `admin`);
- full admin possui `User` Django ativo e único;
- owners ativos não usam role desconhecida.

### Wave 2 — Query Execution

Entregue:

- `accounts.application.ops_rbac_production_readiness_queries`;
- blockers por tenant;
- blockers de matriz;
- flag `expected_gate_state`.

### Wave 3 — Command Execution

Entregue:

- `python manage.py ops_rbac_production_readiness`;
- `--tenant-id`;
- `--expect-gate=any|enabled|disabled`;
- `--fail-on-blockers`;
- saída textual pronta para anexar em change log.

### Wave 4 — Tests

Coberto:

- Go com full admin e gate enabled;
- No-Go sem full admin;
- No-Go com role desconhecida;
- No-Go quando gate deveria estar enabled;
- comando em modo ready;
- comando falhando com `--fail-on-blockers`.

### Wave 5 — Runbook & Rollback

Runbook:

1. validar evidência pré-switch;
2. corrigir owners/users/roles;
3. ativar `HUBX_OPS_AUTH_GATE_ENFORCED=1`;
4. redeploy/restart;
5. rodar evidência pós-switch com `--fail-on-blockers`;
6. validar uma rota permitida e uma rota proibida;
7. acompanhar `owner.ops_permission_denied`;
8. rollback: voltar gate para `0`.

### Wave 6 — Closure Review

Status: **Go** para rollout controlado tenant-by-tenant quando a evidência passar.

Fora de escopo mantido:

- ativação automática;
- batch global;
- alteração automática de roles;
- matriz persistida;
- E2E browser obrigatório.

### Próxima abordagem recomendada

**Platform RBAC Staging Activation Evidence Review**

Objetivo:

- executar e capturar o primeiro pacote de evidências de staging, incluindo saída dos comandos, testes manuais mínimos e critério de rollback.

## Wave 27 — Platform RBAC Staging Activation Evidence Review

Esta abordagem transforma o runbook de RBAC em pacote objetivo de evidência para staging.

### Wave 1 — Evidence Contract

Critérios:

- compor preflight do gate `/ops/`;
- compor readiness de RBAC granular;
- manter recorte tenant-scoped;
- imprimir comandos de reprodução;
- incluir checklist manual mínimo;
- incluir rollback explícito.

### Wave 2 — Evidence Command Execution

Entregue:

- `accounts.application.ops_rbac_staging_evidence_queries`;
- `python manage.py ops_rbac_staging_activation_evidence`;
- `--tenant-id`;
- `--expect-gate=any|enabled|disabled`;
- `--environment`;
- `--require-email-delivery`;
- `--fail-on-blockers`.

### Wave 3 — Evidence Tests

Coberto:

- evidência ready com gate enabled e full admin ativo;
- blockers prefixados por `preflight:*` e `rbac:*`;
- saída do pacote com comandos reproduzíveis;
- saída do checklist manual;
- saída do rollback;
- falha com `--fail-on-blockers`.

### Wave 4 — Manual Evidence Checklist

Checklist:

1. anexar saída do pacote agregado;
2. anexar saída de `command.preflight`;
3. anexar saída de `command.rbac`;
4. login owner/admin no subdomínio do tenant e abrir `/ops/`;
5. abrir rota permitida pela role testada;
6. abrir rota proibida e confirmar `403`;
7. confirmar `AuditLog owner.ops_permission_denied`.

### Wave 5 — Rollback

Rollback:

1. setar `HUBX_OPS_AUTH_GATE_ENFORCED=0`;
2. redeploy/restart dos processos web;
3. rodar `ops_rbac_staging_activation_evidence --expect-gate=disabled`;
4. confirmar `/ops/` acessível para owner/admin ativo.

### Wave 6 — Closure Review

Status: **Go** para capturar evidência real em staging.

Observação:

- o comando criado aqui é seguro para rodar localmente, mas uma execução local não substitui evidência real de staging.

### Próxima abordagem recomendada

**Platform RBAC Staging Activation Execution Review**

Objetivo:

- rodar o pacote contra staging real, anexar outputs reais, validar os três testes manuais e decidir Go/No-Go para manter o gate ligado.

## Wave 28 — Platform RBAC Production Activation Evidence Review

Esta abordagem cria o pacote agregado de evidência para ativação/manutenção do RBAC granular em produção.

### Wave 1 — Production Evidence Contract

Critérios:

- compor rollout de produção do gate `/ops/`;
- compor readiness de RBAC granular;
- manter exigência forte de provider de e-mail por padrão;
- bloquear falhas de notification owner access por padrão;
- imprimir comandos de reprodução;
- incluir checklist manual de produção;
- incluir rollback explícito.

### Wave 2 — Evidence Command Execution

Entregue:

- `accounts.application.ops_rbac_production_activation_evidence_queries`;
- `python manage.py ops_rbac_production_activation_evidence`;
- `--tenant-id`;
- `--expect-gate=any|enabled|disabled`;
- `--environment`;
- `--allow-email-dry-run`;
- `--allow-notification-failures`;
- `--block-on-pending-delivery`;
- `--fail-on-blockers`.

### Wave 3 — Evidence Tests

Coberto:

- evidência ready com gate enabled, provider real e full admin ativo;
- blockers prefixados por `rollout:*` e `rbac:*`;
- saída com comandos reproduzíveis;
- checklist manual de produção;
- rollback;
- falha com `--fail-on-blockers`.

### Wave 4 — Production Manual Checklist

Checklist:

1. anexar saída do pacote agregado;
2. anexar saída de `command.rollout`;
3. anexar saída de `command.rbac`;
4. login owner/admin real no subdomínio do tenant e abrir `/ops/`;
5. abrir rota permitida pela role validada;
6. abrir rota proibida com role limitada e confirmar `403`;
7. confirmar `AuditLog`/métrica `owner.ops_permission_denied`;
8. acompanhar erros de login/permission denied após ativação.

### Wave 5 — Rollback

Rollback:

1. setar `HUBX_OPS_AUTH_GATE_ENFORCED=0`;
2. redeploy/restart dos processos web de produção;
3. rodar `ops_rbac_production_activation_evidence --expect-gate=disabled`;
4. confirmar `/ops/` acessível para owner/admin real;
5. registrar blockers e rollback no change log.

### Wave 6 — Closure Review

Status: **Go técnico** para captura real em produção quando houver janela operacional.

Observação:

- execução local valida formato e contrato, mas não substitui evidência real do ambiente production.

### Próxima abordagem recomendada

**Platform RBAC Post-Production Monitoring Review**

Objetivo:

- revisar painéis/alertas pós-ativação, thresholds de `owner.ops_permission_denied`, falhas de login owner/admin e sinais de rollback.

## Wave 29 — Platform RBAC Post-Production Monitoring Review

Esta abordagem fecha o ciclo de ativação do RBAC com monitoramento operacional pós-produção.

### Wave 1 — Signal Contract

Sinais:

- `owner.ops_permission_denied` como `WATCH`;
- `owner.ops_gate_forbidden` como `WATCH`;
- `owner.login_failed` como `WATCH`;
- `owner.login_rate_limited` como `ROLLBACK`;
- `EmailLog failed` de owner access como `ROLLBACK`.

### Wave 2 — Monitoring Command Execution

Entregue:

- `accounts.application.ops_rbac_post_production_monitoring_queries`;
- `python manage.py ops_rbac_post_production_monitoring`;
- `--tenant-id`;
- `--window-minutes`;
- thresholds ajustáveis;
- `--fail-on-watch`;
- `--fail-on-rollback`.

### Wave 3 — Alerting

Entregue:

- alerta critical `HubxAccountsRBACPostProductionRollbackSignal`;
- reaproveitamento das métricas `hubx_accounts_owner_access_audit_event_total`;
- reaproveitamento das métricas `hubx_accounts_owner_access_email_log_total`.

### Wave 4 — Tests

Coberto:

- snapshot `HEALTHY`;
- `WATCH` por permission denied;
- `ROLLBACK` por rate limit e e-mail failed;
- comando imprimindo snapshot;
- comando falhando com `--fail-on-rollback`.

### Wave 5 — Closure Review

Status: **Go** para acompanhamento pós-ativação.

Fora de escopo:

- rollback automático;
- dashboard Grafana novo;
- métrica nova duplicando as existentes;
- incident management externo.

### Próxima abordagem recomendada

**Platform RBAC Production Closure Review**

Objetivo:

- encerrar a trilha RBAC com matriz final de readiness/evidence/monitoring, riscos residuais e próximos passos fora de RBAC.

## Wave 30 — Platform RBAC Production Closure Review

Esta abordagem encerra a trilha RBAC production com uma decisão objetiva.

### Wave 1 — Closure Contract

Critérios:

- compor evidência de ativação production;
- compor monitoramento pós-produção;
- separar `READY`, `WATCH` e `BLOCKED`;
- listar riscos residuais;
- sugerir próximas trilhas fora do polimento do gate atual.

### Wave 2 — Closure Command Execution

Entregue:

- `accounts.application.ops_rbac_production_closure_queries`;
- `python manage.py ops_rbac_production_closure`;
- `--tenant-id`;
- `--expect-gate`;
- `--window-minutes`;
- `--allow-email-dry-run`;
- `--allow-notification-failures`;
- `--fail-on-blockers`.

### Wave 3 — Closure Tests

Coberto:

- `READY` com ativação pronta e monitoramento saudável;
- `WATCH` quando há sinal recente sem blocker de rollback;
- `BLOCKED` quando ativação está bloqueada;
- comando imprimindo decisões, riscos residuais e próximas trilhas;
- comando falhando com `--fail-on-blockers`.

### Wave 4 — Residual Risks

Riscos remanescentes:

- execução real depende de janela operacional e acesso ao ambiente;
- roles continuam em matriz de código;
- MFA/SSO ainda não existe;
- dashboard Grafana dedicado pode evoluir depois.

### Wave 5 — Closure Decision

Status: **trilha RBAC production tecnicamente encerrada nesta fase**.

Interpretação:

- continuar nesta trilha só faz sentido com evidência real de produção ou com novo escopo maior;
- próximos ganhos relevantes devem virar trilhas separadas de IAM, permission persistence ou audit export.

### Próxima abordagem recomendada

**Platform Audit Evidence Export Review**

Objetivo:

- permitir exportar evidências operacionais/auditoria de forma controlada, sem depender apenas de output textual de comandos.

## Wave 31 — Platform Audit Evidence Export Review

Esta abordagem cria o primeiro caminho controlado para exportar evidências persistidas de auditoria.

### Wave 1 — Export Contract

Critérios:

- tenant-owned exige `tenant_id`;
- platform-scope exige opt-in explícito;
- sem export cross-tenant agregado;
- formatos `jsonl` e `csv`;
- metadata apenas por opt-in;
- saída anexável em change log/incidente.

### Wave 2 — Export Command Execution

Entregue:

- `audit.application.audit_evidence_export_queries`;
- `python manage.py export_audit_evidence`;
- `--tenant-id`;
- `--platform-scope`;
- `--module`;
- `--action`;
- `--since`;
- `--until`;
- `--limit`;
- `--format=jsonl|csv`;
- `--include-metadata`;
- `--fail-on-empty`.

### Wave 3 — Tests

Coberto:

- tenant obrigatório por padrão;
- export tenant-scoped sem vazar outro tenant;
- filtro por módulo/ação;
- metadata opt-in;
- platform-scope explícito;
- CSV com header;
- comando JSONL;
- falha com `--fail-on-empty`.

### Wave 4 — Closure Review

Status: **Go** para uso operacional interno.

Fora de escopo:

- endpoint HTTP;
- assinatura/criptografia do artefato;
- storage externo;
- redaction avançado;
- export multi-tenant agregado.

### Próxima abordagem recomendada

**Platform Audit Evidence Admin Surface Review**

Objetivo:

- decidir se o export deve ganhar uma surface `/ops/audit/export/` com permissão granular ou se command-line é suficiente por enquanto.

## Wave 32 — Platform Audit Evidence Admin Surface Review

Esta abordagem conecta a exportação de evidências à superfície admin read-only existente.

### Wave 1 — Surface Contract

Critérios:

- export fica sob `/ops/audit/export/`;
- tenant é resolvido pela request;
- rota herda gate/permissão `audit.view`;
- export HTTP não permite platform-scope;
- listagem mantém link simples para JSONL.

### Wave 2 — Surface Execution

Entregue:

- `AdminAuditEvidenceExportView`;
- rota `audit:admin-audit-evidence-export`;
- botão `Exportar evidência JSONL` na listagem `/ops/audit/`;
- preservação de filtros `module` e `action`.

### Wave 3 — Tests

Coberto:

- export HTTP retorna JSONL tenant-scoped;
- outro tenant não aparece no payload;
- ausência de tenant retorna `400`;
- command export segue coberto separadamente.

### Wave 4 — Closure Review

Status: **Go** para surface admin mínima.

Fora de escopo:

- export platform-scope via browser;
- filtros avançados de período/formato na UI;
- export assíncrono;
- storage externo.

### Próxima abordagem recomendada

**Platform Audit Evidence Closure Review**

Objetivo:

- fechar a trilha de audit export/admin surface e decidir se o próximo investimento deve ir para IAM/MFA, permission matrix persistida ou dashboards operacionais.

## Wave 33 — Platform Audit Evidence Closure Review

Esta abordagem encerra a trilha de exportação de evidências auditáveis.

### Wave 1 — Closure Contract

Critérios:

- validar export command;
- validar surface admin tenant-scoped;
- listar riscos residuais;
- eleger próximas trilhas fora do export básico.

### Wave 2 — Closure Command Execution

Entregue:

- `audit.application.audit_evidence_closure_queries`;
- `python manage.py audit_evidence_closure`;
- `--tenant-id`;
- `--platform-scope`;
- `--fail-on-blockers`.

### Wave 3 — Tests

Coberto:

- closure ready com sample tenant-scoped;
- closure ready mesmo sem linhas para tenant válido;
- closure blocked sem tenant/platform-scope;
- comando imprimindo decisões e próximas trilhas;
- comando falhando com `--fail-on-blockers`.

### Wave 4 — Closure Decision

Status: **trilha audit evidence tecnicamente encerrada nesta fase**.

Interpretação:

- export básico e surface mínima estão prontos;
- storage, assinatura, redaction avançado e filtros ricos são trilhas futuras, não blockers;
- próximo ROI de plataforma deve ir para IAM/MFA, permission matrix persistida ou dashboard operacional.

### Próxima abordagem recomendada

**Platform Owner MFA/SSO Review**

Objetivo:

- revisar o menor contrato de segundo fator/SSO para owners/admins sem implementar provider externo cedo demais.

## Wave 34 — Platform Owner MFA/SSO Review

Esta abordagem cria o contrato mínimo de MFA/SSO owner/admin sem alterar o login atual.

### Wave 1 — Current Login Boundary

Achado:

- login owner/admin atual usa `User` Django, `OwnerUser` tenant-scoped, rate limit, sessão owner e `AuditLog`.
- esse fluxo continua sendo o baseline até existir provider/enrollment real.

### Wave 2 — Readiness Contract

Entregue:

- `accounts.application.owner_mfa_sso_readiness_queries`;
- `python manage.py owner_mfa_sso_readiness`;
- settings de contrato para MFA e SSO;
- blockers quando MFA/SSO é exigido sem provider/config mínima.

### Wave 3 — Tests

Coberto:

- default password-only ready;
- MFA required sem provider bloqueia;
- SSO configurado passa;
- comando imprime contratos e próximas trilhas;
- comando falha com `--fail-on-blockers`.

### Wave 4 — Closure Review

Status: **Go** para contrato/readiness, **No-Go** para ativação real de MFA/SSO ainda.

Fora de escopo:

- enrollment model;
- provider adapter;
- callback SSO;
- break-glass;
- enforcement no login atual.

### Próxima abordagem recomendada

**Owner MFA Enrollment Model Review**

Objetivo:

- decidir se o próximo passo deve criar modelo tenant-scoped de fator MFA por `OwnerUser`, ainda sem provider externo obrigatório.

## Wave 35 — Owner MFA Enrollment Model Review

Esta abordagem cria o modelo mínimo de enrollment MFA por owner/admin sem ativar MFA no login.

### Wave 1 — Model Contract

Entregue:

- `OwnerMfaFactor`;
- FK para `Tenant`;
- FK para `OwnerUser`;
- tipos `totp`, `recovery_code`, `external`;
- `secret_reference` em vez de segredo bruto;
- estado `is_verified` e `is_active`;
- timestamps de verificação/desafio.

### Wave 2 — Tenant Scope

Regras:

- fator deve pertencer ao mesmo tenant do `OwnerUser`;
- unicidade por `(tenant, owner, factor_type, provider_key)`;
- readiness filtra por `tenant_id`.

### Wave 3 — Readiness Command

Entregue:

- `accounts.application.owner_mfa_enrollment_queries`;
- `python manage.py owner_mfa_enrollment_readiness`;
- `--tenant-id`;
- `--fail-on-blockers`.

### Wave 4 — Tests

Coberto:

- tenant obrigatório;
- owner sem fator verificado bloqueia;
- owner com fator ativo/verificado passa;
- isolamento entre tenants;
- rejeição de fator cross-tenant.

### Wave 5 — Closure Review

Status: **Go** para modelo/enrollment readiness, **No-Go** para enforcement MFA no login.

Fora de escopo:

- geração/verificação TOTP;
- recovery codes reais;
- adapter externo;
- UI de enrollment;
- enforcement no login.

### Próxima abordagem recomendada

**Owner MFA Enrollment Command Review**

Objetivo:

- criar command service para registrar/desativar fator MFA de forma auditável, ainda sem challenge real.

## Wave 36 — Owner MFA Enrollment Command Review

Esta abordagem cria comandos auditáveis para operar fatores MFA sem challenge real.

### Wave 1 — Command Contract

Entregue:

- `accounts.application.owner_mfa_enrollment_commands`;
- registro de fator MFA pendente;
- desativação lógica de fator;
- permission check `owners.manage`.

### Wave 2 — Audit Events

Eventos:

- `owner.mfa_factor_registered`;
- `owner.mfa_factor_deactivated`.

### Wave 3 — Management Command

Entregue:

- `python manage.py owner_mfa_factor register`;
- `python manage.py owner_mfa_factor deactivate`;
- `--tenant-id`;
- `--owner-id`;
- `--factor-id`;
- `--factor-type`;
- `--provider-key`;
- `--secret-reference`;
- `--actor-role`;
- `--fail-on-errors`.

### Wave 4 — Tests

Coberto:

- registro cria fator pendente e auditado;
- operação respeita tenant do owner;
- role sem permissão bloqueia;
- desativação registra auditoria;
- management command imprime resultado.

### Próxima abordagem recomendada

**Owner MFA Enrollment Closure Review**

Objetivo:

- encerrar a abordagem de enrollment MFA com decisão clara sobre modelo, readiness, commands e próximos riscos.

## Wave 37 — Owner MFA Enrollment Closure Review

Esta abordagem encerra o pacote de enrollment MFA.

### Closure

Status: **Go** para modelo/readiness/commands auditáveis.

No-Go deliberado:

- challenge real;
- verificação TOTP;
- UI admin;
- enforcement no login.

### Próxima abordagem recomendada

**Owner MFA Challenge Verification Review**

Objetivo:

- implementar verificação de challenge para promover fator pendente para verificado, ainda sem obrigar MFA no login.

## Wave 38 — Owner MFA Challenge Verification Review

Esta abordagem adiciona verificação real de challenge para fator MFA TOTP owner/admin, sem enforcement no login.

### Wave 1 — Challenge Contract

Entregue:

- `accounts.application.owner_mfa_challenge_commands`;
- verificador TOTP interno;
- busca tenant-scoped de fator ativo;
- bloqueio por permissão `owners.manage`.

### Wave 2 — Verification Command

Entregue:

- `python manage.py owner_mfa_factor verify`;
- argumento `--challenge`;
- atualização de `is_verified`, `verified_at` e `last_challenged_at`.

### Wave 3 — Audit Events

Eventos:

- `owner.mfa_factor_verified`;
- `owner.mfa_factor_verification_failed`.

### Wave 4 — Tests

Coberto:

- challenge válido marca fator como verificado;
- challenge inválido registra tentativa e preserva fator pendente;
- operação respeita tenant do fator;
- role sem permissão bloqueia;
- management command imprime resultado.

### Próxima abordagem recomendada

**Owner MFA Admin Surface Review**

Objetivo:

- expor superfície admin mínima para listar fatores MFA, iniciar registro/verificação e desativar fator sem acoplar enforcement ao login.

## Wave 39 — Owner MFA Admin Surface Review

Esta abordagem expõe uma superfície `/ops/` mínima para operação de fatores MFA.

### Entregue

- `GET /ops/owners/mfa/`;
- `POST /ops/owners/mfa/<factor_id>/verify/`;
- `POST /ops/owners/mfa/<factor_id>/deactivate/`;
- `accounts.application.owner_mfa_admin_queries`;
- ações delegadas para command services já auditáveis.

### Escopo deliberado

- sem registrar fator novo pela UI;
- sem QR code;
- sem enforcement no login.

## Wave 40 — Owner Break-Glass Access Review

Esta abordagem define readiness operacional para break-glass antes de qualquer enforcement MFA.

### Entregue

- `accounts.application.owner_mfa_break_glass_readiness_queries`;
- comando `owner_mfa_break_glass_readiness`;
- contrato via `OWNER_MFA_BREAK_GLASS_ENABLED` e `OWNER_MFA_BREAK_GLASS_OWNER_EMAILS`.

### Critério Go/No-Go

- Go:
  - break-glass habilitado;
  - pelo menos um e-mail configurado;
  - cada e-mail corresponde a `OwnerUser` ativo no tenant.
- No-Go:
  - `break-glass-disabled`;
  - `break-glass-email-required`;
  - `break-glass-owner-missing:<email>`.

## Wave 41 — Owner MFA Login Enforcement Readiness Review

Esta abordagem cria readiness para enforcement sem alterar autenticação.

### Entregue

- `accounts.application.owner_mfa_login_enforcement_readiness_queries`;
- comando `owner_mfa_login_enforcement_readiness`;
- composição de `OWNER_MFA_REQUIRED`, enrollment MFA e break-glass.

### Escopo deliberado

- sem challenge no login;
- sem criar sessão MFA;
- sem bloquear `/ops/`.

## Wave 42 — Owner MFA Operational Closure Review

Esta abordagem fecha o pacote operacional MFA antes da execução de enforcement.

### Entregue

- `accounts.application.owner_mfa_operational_closure_queries`;
- comando `owner_mfa_operational_closure`;
- decisão agregada sobre admin surface, break-glass e readiness de enforcement.

### Próxima abordagem recomendada

**Owner MFA Login Enforcement Execution Review**

Objetivo:

- aplicar MFA no fluxo de login owner/admin depois da senha e antes da sessão efetiva, com rollback claro.

## Wave 43 — Owner MFA Login Enforcement Execution Review

Esta abordagem aplica enforcement MFA no login owner/admin sem afetar customer login.

### Entregue

- `OWNER_MFA_REQUIRED` controla ativação/rollback.
- senha válida não cria sessão owner quando MFA está ativo.
- sessão pendente curta usa `OWNER_MFA_CHALLENGE_PENDING_SECONDS`.
- `/accounts/login/mfa/` conclui o challenge TOTP.
- sessão owner/admin efetiva nasce apenas após challenge válido.

### Eventos

- `owner.login_mfa_required`;
- `owner.login_mfa_failed`;
- `owner.login_mfa_completed`;
- `owner.login_mfa_blocked`.

### Rollback

1. definir `OWNER_MFA_REQUIRED=0`;
2. redeploy/restart;
3. validar login owner/admin direto pós-senha;
4. manter fatores MFA persistidos para reativação futura.

### Critério Go/No-Go

- Go:
  - owners ativos possuem fator ativo/verificado;
  - challenge válido cria sessão;
  - challenge inválido não cria sessão;
  - rollback por setting preserva login direto.
- No-Go:
  - owner ativo sem fator verificado;
  - erro em `/accounts/login/mfa/`;
  - sessão criada antes do challenge.

### Próxima abordagem recomendada

**Owner MFA Recovery Codes Review**

Objetivo:

- adicionar códigos de recuperação reais antes de endurecer break-glass/bypass operacional.

## Wave 44 — Owner MFA Recovery Codes Review

Esta abordagem adiciona recovery codes reais para MFA owner/admin.

### Entregue

- modelo `OwnerMfaRecoveryCode`;
- command service `owner_mfa_recovery_code_commands`;
- comando `owner_mfa_recovery_codes generate`;
- hashes persistidos com exibição dos códigos apenas uma vez;
- uso único no fluxo `/accounts/login/mfa/`;
- readiness de enrollment considerando apenas recovery codes não usados.

### Eventos

- `owner.mfa_recovery_codes_generated`;
- `owner.mfa_recovery_code_used`.

### Critério Go/No-Go

- Go:
  - códigos gerados não são persistidos em texto claro;
  - código válido conclui challenge MFA;
  - código usado não pode ser reutilizado;
  - tenant errado não gera nem consome código.
- No-Go:
  - código aparece em `AuditLog`;
  - login aceita recovery code já usado;
  - readiness considera recovery factor sem código disponível.

### Próxima abordagem recomendada

**Owner MFA Secret Storage Hardening Review**

Objetivo:

- revisar `secret_reference` TOTP e decidir caminho para vault/provider externo sem quebrar o enforcement atual.

## Wave 45 — Owner MFA Secret Storage Hardening Review

Esta abordagem explicita o contrato de armazenamento de segredo TOTP sem trocar provider ainda.

### Entregue

- resolver `accounts.application.owner_mfa_secret_storage`;
- setting `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET`;
- comando `owner_mfa_secret_storage_readiness`;
- integração do resolver no challenge TOTP e no login MFA;
- inventário por tenant de `local-plain`, `external-reference` e `missing`.

### Critério Go/No-Go

- Go:
  - fatores legados continuam funcionando com local plain permitido;
  - local plain bloqueia quando `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
  - referência `ref:<path>` é inventariada e bloqueia até existir provider;
  - comando não explode em ambiente sem migrations e retorna blocker operacional.
- No-Go:
  - login lê `secret_reference` diretamente fora do resolver;
  - segredo externo é tratado como resolvido sem adapter;
  - segredo ausente passa como fator pronto.

### Próxima abordagem recomendada

**Owner MFA External Secret Provider Adapter Review**

Objetivo:

- criar adapter mínimo para resolver `ref:<path>` contra provider/vault real ou mockado por ambiente, mantendo fallback explícito.

## Wave 46 — Owner MFA External Secret Provider Adapter Review

Esta abordagem adiciona um adapter externo mínimo para `secret_reference` sem exigir vault real.

### Entregue

- registry `accounts.infrastructure.owner_mfa_secret_providers`;
- provider `env`;
- settings `OWNER_MFA_SECRET_PROVIDER` e `OWNER_MFA_SECRET_ENV_PREFIX`;
- resolução de `ref:<path>` no resolver central;
- readiness permitindo referência externa quando provider resolve o segredo;
- login MFA funcionando com fator TOTP referenciado externamente.

### Critério Go/No-Go

- Go:
  - `OWNER_MFA_SECRET_PROVIDER=env` resolve `ref:<path>` via variável de ambiente;
  - readiness marca referência externa resolvida como pronta;
  - referência sem valor continua bloqueada;
  - login não expõe segredo em logs.
- No-Go:
  - provider ausente tratado como pronto;
  - readiness imprime segredo;
  - login volta a ler `secret_reference` diretamente.

### Próxima abordagem recomendada

**Owner MFA TOTP Secret Migration Plan**

Objetivo:

- planejar a migração segura dos fatores `plain:`/legados para `ref:` sem downtime e com rollback.

## Wave 47 — Owner MFA TOTP Secret Migration Plan

Esta abordagem cria um plano operacional para migrar segredos TOTP locais/legados para `ref:<path>`.

### Entregue

- query service `owner_mfa_totp_secret_migration_plan_queries`;
- comando `owner_mfa_totp_secret_migration_plan`;
- classificação de candidatos `migrate-local-to-ref`, `already-external` e `blocked`;
- geração de `target_ref` determinístico por tenant/owner/fator;
- runbook e rollback explícitos.

### Critério Go/No-Go

- Go:
  - candidatos locais possuem `target_ref`;
  - referências externas resolvidas ficam `already-external`;
  - referências externas não resolvidas bloqueiam;
  - comando não move nem imprime segredo.
- No-Go:
  - segredo ausente;
  - provider externo não resolve fator já em `ref:`;
  - banco local sem migrations.

### Próxima abordagem recomendada

**Owner MFA TOTP Secret Migration Execution Review**

Objetivo:

- criar comando de execução controlada para trocar `secret_reference` para `ref:<path>` somente após evidência de provider externo pronto.

## Wave 48 — Owner MFA TOTP Secret Migration Execution Review

Esta abordagem executa a troca controlada de `plain:`/legado para `ref:<path>` sem copiar segredo dentro do app.

### Entregue

- command service `owner_mfa_totp_secret_migration_commands`;
- comando `owner_mfa_totp_secret_migration_execute`;
- dry-run padrão, com escrita real somente via `--execute`;
- validação de equivalência entre segredo local atual e provider externo alvo;
- atualização tenant-scoped de `OwnerMfaFactor.secret_reference`;
- AuditLog `owner.mfa_totp_secret_migrated` sem valores sensíveis.

### Critério Go/No-Go

- Go:
  - fator TOTP ativo pertence ao tenant informado;
  - segredo atual é `local-plain`;
  - provider resolve o `target_ref`;
  - valor resolvido confere com o valor local atual;
  - dry-run passa antes da execução real.
- No-Go:
  - provider externo não resolve o alvo;
  - valor externo diverge do segredo local;
  - fator já está em `ref:` ou não pertence ao tenant;
  - banco/audit indisponível para evidência operacional.

### Próxima abordagem recomendada

**Owner MFA Local Secret Retirement Review**

Objetivo:

- decidir quando e como desligar `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` por ambiente depois da migração real dos fatores TOTP.

## Wave 49 — Owner MFA Local Secret Retirement Review

Esta abordagem cria readiness para aposentar o fallback local/plain de segredo TOTP owner/admin.

### Entregue

- query service `owner_mfa_local_secret_retirement_queries`;
- comando `owner_mfa_local_secret_retirement_readiness`;
- Go/No-Go explícito para `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
- blockers para fatores locais restantes, segredo ausente e referência externa não resolvida;
- runbook e rollback operacional sem alterar settings/env.

### Critério Go/No-Go

- Go:
  - `local_plain_count=0`;
  - todos os fatores TOTP ativos usam `ref:<path>` resolvido;
  - readiness de storage está pronto;
  - login/challenge MFA amostral funciona com provider externo.
- No-Go:
  - qualquer fator local/plain ainda ativo;
  - segredo ausente;
  - provider externo sem valor para referência;
  - necessidade de migração adicional antes do corte.

### Próxima abordagem recomendada

**Owner MFA Local Secret Retirement Execution Review**

Objetivo:

- transformar o readiness em plano de ativação por ambiente, com evidências antes/depois e rollback de setting.

## Wave 50 — Owner MFA Local Secret Retirement Execution Review

Esta abordagem cria evidência operacional before/after para ativar a aposentadoria do fallback local/plain TOTP.

### Entregue

- query service `owner_mfa_local_secret_retirement_execution_queries`;
- comando `owner_mfa_local_secret_retirement_execution`;
- fase `before` para capturar readiness antes do corte;
- fase `after` para provar que `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False` está ativo;
- blockers para setting ainda habilitado, fator local regressivo e storage não pronto;
- rollback documentado sem alterar env automaticamente.

### Critério Go/No-Go

- Go before:
  - readiness de retirement pronto;
  - `local_plain_count=0`;
  - referências externas resolvidas.
- Go after:
  - `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
  - storage readiness continua pronto;
  - nenhum fator TOTP local reapareceu.
- No-Go:
  - setting ainda habilitado no after;
  - fator local/plain restante;
  - provider externo indisponível;
  - segredo ausente.

### Próxima abordagem recomendada

**Owner MFA Provider Health Monitoring Review**

Objetivo:

- monitorar continuamente se referências externas TOTP continuam resolvidas depois do corte do fallback local.

## Wave 51 — Owner MFA Provider Health Monitoring Review

Esta abordagem adiciona snapshot operacional para acompanhar saúde do provider externo de segredos TOTP.

### Entregue

- query service `owner_mfa_provider_health_queries`;
- comando `owner_mfa_provider_health`;
- status `HEALTHY`, `WATCH` e `CRITICAL`;
- sinais para provider ausente, referência externa não resolvida, segredo ausente, fallback local e ausência de fatores externos;
- runbook curto de triagem sem expor segredo.

### Critério Go/No-Go

- Go:
  - provider configurado;
  - referências externas resolvidas;
  - zero segredos ausentes;
  - zero fatores locais depois do corte.
- Watch:
  - fallback local ainda existe;
  - não há fatores externos suficientes para monitorar;
  - readiness incompleto sem quebra imediata.
- No-Go/Critical:
  - `ref:<path>` não resolve;
  - provider não configurado com fator externo;
  - segredo ausente.

### Próxima abordagem recomendada

**Owner MFA Provider Health Metrics Review**

Objetivo:

- expor esse snapshot em métrica/scrape real para Prometheus e alert rules iniciais.

## Wave 52 — Owner MFA Provider Health Metrics Review

Esta abordagem expõe o health do provider TOTP MFA owner/admin em métricas Prometheus.

### Entregue

- metrics query `owner_mfa_provider_health_metrics_queries`;
- endpoint `/accounts/metrics/owner-mfa-provider-health/`;
- autenticação por `ACCOUNTS_OBSERVABILITY_TOKEN`;
- métricas de status, refs externas resolvidas/não resolvidas, storage mode e signals;
- scrape example accounts atualizado;
- alert rules iniciais para provider crítico, ref externa não resolvida e local/plain restante.

### Critério Go/No-Go

- Go:
  - endpoint retorna payload Prometheus com token válido;
  - payload não contém segredo TOTP;
  - alertas usam labels de baixa cardinalidade;
  - endpoint não depende de `/ops/`.
- No-Go:
  - token ausente;
  - provider health crítico;
  - refs externas não resolvidas;
  - cardinalidade por owner/factor.

### Próxima abordagem recomendada

**Owner MFA Provider Health Dashboard Review**

Objetivo:

- criar dashboard Grafana mínimo para acompanhar provider/status/storage após ativação real.

## Wave 53 — Owner MFA Provider Health Dashboard Review

Esta abordagem adiciona dashboard Grafana inicial para o health do provider TOTP MFA owner/admin.

### Entregue

- dashboard `accounts-owner-mfa-provider-health-dashboard.json`;
- painéis stat para provider crítico, refs não resolvidas, local/plain restante e tenants saudáveis;
- painéis de série para status e referências externas;
- tabelas para sinais ativos e storage por tenant;
- README de observabilidade atualizado com instrução de import.

### Critério Go/No-Go

- Go:
  - dashboard JSON válido;
  - Prometheus datasource parametrizado como `DS_PROMETHEUS`;
  - painéis usam métricas da Wave 52;
  - sem labels de alta cardinalidade.
- No-Go:
  - scrape MFA provider indisponível;
  - datasource não configurado;
  - painel exige owner/factor/reference path;
  - alertas críticos ativos sem triagem.

### Próxima abordagem recomendada

**Owner MFA Provider Health Closure Review**

Objetivo:

- fechar a trilha de provider health com checklist de produção, evidências e próximos riscos residuais.

## Wave 54 — Owner MFA Provider Health Closure Review

Esta abordagem fecha a trilha de provider health MFA com checklist objetivo e riscos residuais.

### Entregue

- query service `owner_mfa_provider_health_closure_queries`;
- comando `owner_mfa_provider_health_closure`;
- decisões de health, métricas Prometheus, dashboard Grafana e exposição segura;
- blockers para health crítico ou artefato ausente;
- riscos residuais e próximas trilhas recomendadas.

### Critério Go/No-Go

- Go:
  - provider health `HEALTHY`;
  - scrape example presente;
  - alert rules presentes;
  - dashboard Grafana presente;
  - métricas sem owner/factor/segredo/reference path.
- Watch:
  - fallback local ainda existe;
  - nenhum fator externo ativo ainda existe;
  - operação exige acompanhamento, mas não há quebra crítica.
- No-Go:
  - provider health `CRITICAL`;
  - `ref:<path>` não resolve;
  - artefato Prometheus/Grafana ausente;
  - alertas críticos ativos sem triagem.

### Próxima abordagem recomendada

**Owner MFA Local Secret Code Retirement Review**

Objetivo:

- decidir se já dá para remover/aposentar código e tolerâncias de `plain:` depois da ativação real em ambiente.

## Wave 55 — Owner MFA Local Secret Code Retirement Review

Esta abordagem avalia se o código de fallback local/plain TOTP já pode ser aposentado com segurança.

### Entregue

- query service `owner_mfa_local_secret_code_retirement_queries`;
- comando `owner_mfa_local_secret_code_retirement_readiness`;
- decisões para setting desligado, ausência de fatores locais, provider closure e remoção futura;
- inventário das superfícies de código que ainda sustentam `plain:`/legado;
- blockers para setting local habilitado, fator local restante, falta de fatores externos e provider closure crítico.

### Critério Go/No-Go

- Go:
  - `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
  - `local_plain_count=0`;
  - `external_reference_count>0`;
  - provider health closure pronto.
- No-Go:
  - setting local ainda habilitado;
  - fator `plain:`/legado ainda ativo;
  - provider health crítico;
  - ausência de fatores externos resolvidos;
  - necessidade de rollback rápido ainda alta.

### Próxima abordagem recomendada

**Owner MFA Local Secret Code Retirement Execution Review**

Objetivo:

- remover ou endurecer as tolerâncias de código `plain:`/legado com patch pequeno e rollback claro.

## Wave 56 — Owner MFA Local Secret Code Retirement Execution Review

Esta abordagem executa o primeiro hardening real do fallback local/plain TOTP MFA owner/admin.

### Entregue

- default de `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET` alterado para `0`;
- rollback explícito preservado via `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1`;
- query service `owner_mfa_local_secret_code_retirement_execution_queries`;
- comando `owner_mfa_local_secret_code_retirement_execute`;
- testes legados de local/plain ajustados para opt-in explícito;
- evidência de execução com blockers, decisões e rollback.

### Critério Go/No-Go

- Go:
  - default local plain desligado;
  - tenant sem fatores locais;
  - provider health closure pronto;
  - refs externas resolvidas;
  - testes legados só passam com override explícito.
- No-Go:
  - env reabilita `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=1`;
  - fator local/plain ainda ativo;
  - provider crítico;
  - necessidade de rollback sem janela operacional.

### Próxima abordagem recomendada

**Owner MFA Legacy Data Global Sweep Review**

Objetivo:

- varrer globalmente tenants/fatores ainda em `plain:`/legado antes de considerar remover parsing local do resolver.

## Wave 57 — Owner MFA Legacy Data Global Sweep Review

Esta abordagem cria uma varredura global read-only de fatores TOTP MFA owner/admin ainda dependentes de storage local/legado.

### Entregue

- query service `owner_mfa_legacy_data_global_sweep_queries`;
- comando `owner_mfa_legacy_data_global_sweep`;
- agregação por tenant com contagens de local/plain, external-reference e missing;
- blockers por tenant para local/plain, segredo ausente e ref externa não resolvida;
- próximos tracks condicionados ao status da sweep.

### Critério Go/No-Go

- Go:
  - todos os tenants com TOTP ativo usam `ref:<path>` resolvido;
  - `local_plain_count=0`;
  - `missing_count=0`;
  - nenhum blocker por tenant.
- Watch:
  - nenhum fator TOTP ativo existe no banco atual.
- No-Go:
  - qualquer tenant ainda possui local/plain;
  - qualquer tenant possui segredo ausente;
  - qualquer ref externa não resolve.

### Próxima abordagem recomendada

**Owner MFA Local Secret Parser Removal Review**

Objetivo:

- decidir se já é seguro remover o parsing `plain:`/legado do resolver ou se ainda precisamos de cleanup por tenant.

## Wave 58 — Owner MFA Local Secret Parser Removal Review

Esta abordagem cria o Go/No-Go final antes de remover o parser local/plain do resolver TOTP MFA.

### Entregue

- query service `owner_mfa_local_secret_parser_removal_queries`;
- comando `owner_mfa_local_secret_parser_removal_review`;
- composição com sweep global e setting local;
- inventário das superfícies de parser;
- plano de remoção e rollback por revert de deploy.

### Critério Go/No-Go

- Go:
  - sweep global `ready`;
  - `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=False`;
  - nenhuma ref externa quebrada;
  - nenhum fator local/plain ou missing.
- No-Go:
  - sweep `blocked` ou `watch`;
  - env local/plain reabilitado;
  - qualquer tenant com dados legados;
  - necessidade de rollback por env sem revert de código.

### Próxima abordagem recomendada

**Owner MFA Local Secret Parser Removal Execution Review**

Objetivo:

- remover ou reclassificar o parser local/plain no resolver com patch pequeno, ajustando testes e rollback por deploy.

## Wave 59 — Owner MFA Local Secret Parser Removal Execution Review

Esta abordagem executa a remoção lógica do parser local/plain do resolver TOTP MFA owner/admin.

### Entregue

- `OwnerMfaSecretStorageResolver.resolve` reclassifica `plain:` e valores legados sem `ref:` como `unsupported-local`;
- secrets locais não são mais retornados pelo resolver, mesmo com `OWNER_MFA_ALLOW_LOCAL_TOTP_SECRET=True`;
- readiness tenant-scoped e migration plan passam a bloquear resíduos com `local-secret-unsupported`;
- fluxos de challenge/login nos testes usam `ref:<path>` e provider externo para sucesso real;
- query service `owner_mfa_local_secret_parser_removal_execution_queries`;
- comando `owner_mfa_local_secret_parser_removal_execute`;
- probes operacionais confirmam que `plain:` e legado não retornam segredo.

### Critério Go/No-Go

- Go:
  - sweep global ready;
  - env local/plain desligado;
  - probes `plain:` e legado retornam `unsupported-local`;
  - nenhum segredo local é emitido;
  - testes de login/challenge passam por provider externo.
- No-Go:
  - qualquer tenant ainda possui fator local/plain;
  - provider externo não resolve refs ativas;
  - necessidade de rollback sem revert de deploy;
  - probe local ainda retorna segredo.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Review**

Objetivo:

- substituir o provider `env` operacional por adapter real de cofre/KMS antes de elevar MFA owner/admin para baseline de produção mais forte.

## Wave 60 — Owner MFA Vault/KMS Provider Review

Esta abordagem formaliza o contrato mínimo para substituir o provider `env` por um provider Vault/KMS real de segredos TOTP MFA owner/admin.

### Entregue

- query service `owner_mfa_vault_kms_provider_review_queries`;
- comando `owner_mfa_vault_kms_provider_review`;
- lista inicial de targets suportados para contrato;
- composição com provider health closure tenant-scoped;
- composição com parser removal execution;
- adapter contract, rollout plan, rollback e próximos tracks.

### Critério Go/No-Go

- Go:
  - tenant informado explicitamente;
  - provider atual saudável/fechado;
  - parser local/plain removido;
  - target provider suportado;
  - provider `env` entendido apenas como ponte transitória.
- No-Go:
  - provider health closure bloqueado ou em watch;
  - parser removal execution bloqueada;
  - provider atual ausente;
  - target provider fora da lista suportada.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Adapter Contract Review**

Objetivo:

- transformar o contrato revisado em design técnico do adapter real, definindo settings, timeouts, erros recuperáveis e testes sem acoplar vendor cedo demais.

## Wave 61 — Owner MFA Vault/KMS Provider Adapter Contract Review

Esta abordagem transforma a review Vault/KMS em contrato técnico executável para o skeleton do adapter.

### Entregue

- query service `owner_mfa_vault_kms_provider_adapter_contract_queries`;
- comando `owner_mfa_vault_kms_provider_adapter_contract`;
- contrato de settings do adapter;
- contrato de interface em torno de `OwnerMfaSecretProviderResult`;
- erros recuperáveis padronizados;
- controles de segurança contra exposição de segredo;
- contrato de testes para o skeleton.

### Critério Go/No-Go

- Go:
  - review Vault/KMS anterior pronta;
  - target provider suportado;
  - adapter definido como read-path-only;
  - falhas retornam `ready=False` sem exception no login;
  - segredo não aparece em logs, comandos, métricas ou audit metadata.
- No-Go:
  - provider health closure bloqueado;
  - parser removal execution bloqueada;
  - target provider não suportado;
  - proposta exige escrita/migração/cache de segredo cedo demais.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Adapter Skeleton Execution**

Objetivo:

- implementar o primeiro skeleton de adapter atrás de `OWNER_MFA_SECRET_PROVIDER`, ainda sem SDK/vendor real obrigatório, preservando o contrato de falha segura.

## Wave 62 — Owner MFA Vault/KMS Provider Adapter Skeleton Execution

Esta abordagem implementa o primeiro skeleton read-only de provider Vault/KMS para segredos TOTP MFA owner/admin.

### Entregue

- branch de providers Vault/KMS em `owner_mfa_secret_providers`;
- settings base para timeout, retry, namespace e cache futuro;
- skeleton configurável por status/refs para teste controlado;
- validação de referências inválidas/traversal;
- query service `owner_mfa_vault_kms_provider_adapter_skeleton_execution_queries`;
- comando `owner_mfa_vault_kms_provider_adapter_skeleton_execute`;
- testes de sucesso, namespace, missing, timeout, invalid-reference, command output e blockers.

### Critério Go/No-Go

- Go:
  - contrato técnico ready;
  - `OWNER_MFA_SECRET_PROVIDER` aponta para o target;
  - probe resolve sem fallback local/env;
  - segredo não aparece em stdout;
  - falhas retornam `ready=False` com result explícito.
- No-Go:
  - provider atual não bate com target;
  - contrato anterior bloqueado;
  - probe missing/timeout/unavailable;
  - referência inválida;
  - necessidade de escrita/cache/migração cedo demais.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Readiness Evidence Review**

Objetivo:

- capturar evidência tenant-scoped do skeleton em modo canário antes de qualquer adapter com SDK/vendor real.

## Wave 63 — Owner MFA Vault/KMS Provider Readiness Evidence Review

Esta abordagem cria um pacote de readiness evidence tenant-scoped para o skeleton Vault/KMS em modo canário.

### Entregue

- query service `owner_mfa_vault_kms_provider_readiness_evidence_queries`;
- comando `owner_mfa_vault_kms_provider_readiness_evidence`;
- composição entre skeleton execution e provider health closure;
- evidence pack com status do skeleton, probe e health;
- blockers para mismatch de provider, health bloqueado/watch e probe falho;
- rollback explícito sem parser local/plain.

### Critério Go/No-Go

- Go:
  - tenant explícito;
  - skeleton execution ready;
  - provider health closure ready;
  - provider do health igual ao target;
  - evidência não imprime segredo.
- No-Go:
  - skeleton probe missing/timeout/unavailable;
  - provider health critical/watch;
  - provider atual diferente do target;
  - tenant ausente.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Staging Canary Review**

Objetivo:

- transformar o pacote de evidência em checklist de canário staging com login/challenge manual mínimo, rollback e observabilidade.

## Wave 64 — Owner MFA Vault/KMS Provider Staging Canary Review

Esta abordagem transforma o pacote de readiness em checklist operacional para canário staging de MFA owner/admin.

### Entregue

- query service `owner_mfa_vault_kms_provider_staging_canary_queries`;
- comando `owner_mfa_vault_kms_provider_staging_canary_review`;
- exigência de owner canário explícito;
- preflight de staging;
- checklist manual de login/challenge MFA;
- sinais de sucesso e rollback;
- blockers quando readiness evidence ou owner canário estão ausentes.

### Critério Go/No-Go

- Go:
  - readiness evidence ready;
  - owner/admin canário explícito;
  - provider target consistente;
  - checklist não coleta segredo/código TOTP;
  - rollback para `env` documentado.
- No-Go:
  - readiness evidence bloqueada;
  - owner canário ausente;
  - provider health degradado;
  - probe falho.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Staging Canary Evidence Execution**

Objetivo:

- capturar a primeira evidência pós-checklist do canário staging, ainda como comando/relato operacional sem automatizar browser/login real.

## Wave 65 — Owner MFA Vault/KMS Provider Staging Canary Evidence Execution

Esta abordagem captura evidência declarativa da execução manual do canário staging Vault/KMS.

### Entregue

- query service `owner_mfa_vault_kms_provider_staging_canary_evidence_queries`;
- comando `owner_mfa_vault_kms_provider_staging_canary_evidence`;
- flags declarativas para login válido, challenge inválido, health pós-teste, logs redigidos e rollback;
- blockers por check manual ausente/falho;
- evidence pack sem secret material;
- próximos tracks para adapter real ou readiness de produção.

### Critério Go/No-Go

- Go:
  - review do canário ready;
  - todos os checks manuais reportados como passed;
  - logs redigidos;
  - rollback verificado/simulado;
  - evidence pack sem segredo.
- No-Go:
  - qualquer check manual não reportado;
  - canário review bloqueada;
  - readiness evidence degradada;
  - rollback não verificado.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Real Adapter Contract Review**

Objetivo:

- sair do skeleton configurável e definir contrato real do adapter com SDK/vendor escolhido, mantendo timeouts, falhas recuperáveis e observabilidade segura.

## Wave 66 — Owner MFA Vault/KMS Provider Real Adapter Contract Review

Esta abordagem define o contrato do adapter real pós-canário staging, antes de introduzir SDK/vendor.

### Entregue

- query service `owner_mfa_vault_kms_provider_real_adapter_contract_queries`;
- comando `owner_mfa_vault_kms_provider_real_adapter_contract`;
- composição com staging canary evidence;
- confirmations obrigatórias para SDK, credenciais, timeout/rede e owner de rollout;
- contrato de settings, erros, testes, implementação e rollback;
- lista de targets reais suportados.

### Critério Go/No-Go

- Go:
  - canário staging evidence ready;
  - target real suportado;
  - SDK dependency confirmada;
  - estratégia de credencial confirmada;
  - timeouts/rede confirmados;
  - owner de rollout confirmado.
- No-Go:
  - target ainda não suportado para adapter real;
  - canário staging bloqueado;
  - qualquer confirmação operacional ausente;
  - proposta inclui escrita/migração/cache cedo demais.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution**

Objetivo:

- implementar o primeiro branch real/mocável do adapter escolhido, ainda sem credenciais reais obrigatórias, com SDK isolado e erros mapeados.

## Wave 67 — Owner MFA Vault/KMS Provider Real Adapter Skeleton Execution

Esta abordagem implementa o primeiro branch real/mocável separado do skeleton configurável para provider Vault/KMS.

### Entregue

- branch `OWNER_MFA_SECRET_VAULT_KMS_REAL_ADAPTER_ENABLED` no registry de secrets MFA;
- settings de status e secrets mockados para adapter real;
- mapeamento dos mesmos erros recuperáveis do contrato;
- validação de referência antes do lookup;
- query service `owner_mfa_vault_kms_provider_real_adapter_skeleton_execution_queries`;
- comando `owner_mfa_vault_kms_provider_real_adapter_skeleton_execute`;
- testes de sucesso, timeout, referência inválida, blockers e output sem segredo.

### Critério Go/No-Go

- Go:
  - contrato real ready;
  - provider atual bate com target;
  - modo real adapter habilitado;
  - probe resolve pelo branch real/mocável;
  - output não imprime segredo.
- No-Go:
  - contrato real bloqueado;
  - modo real adapter desligado;
  - probe missing/timeout/unavailable;
  - provider atual diferente do target.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider SDK Dependency Review**

Objetivo:

- decidir a dependência SDK/vendor concreta e como isolá-la em infrastructure sem acoplar login/challenge.

## Wave 68 — Owner MFA Vault/KMS Provider SDK Dependency Review

Esta abordagem formaliza a escolha de dependência SDK/vendor para o provider Vault/KMS antes de instalar pacote ou chamar cofre real.

### Entregue

- query service `owner_mfa_vault_kms_provider_sdk_dependency_review_queries`;
- comando `owner_mfa_vault_kms_provider_sdk_dependency_review`;
- composição com o skeleton real/mocável;
- matriz de pacotes/imports por provider suportado;
- confirmations obrigatórias para pinning, import opcional, rollback e licença;
- contratos de falha, teste e rollback sem segredo.

### Critério Go/No-Go

- Go:
  - skeleton real/mocável ready;
  - provider alvo possui pacote/import definido;
  - dependência será versionada/fixada;
  - import será opcional/lazy;
  - rollback de deploy está definido;
  - licença foi revisada.
- No-Go:
  - skeleton real bloqueado;
  - target não suportado como secret store direto;
  - pacote obrigatório no startup/login;
  - ausência de rollback ou revisão de licença.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider SDK Adapter Execution**

Objetivo:

- introduzir o primeiro adapter SDK real em `accounts.infrastructure`, com import opcional, erro mapeado e fallback operacional desligável.

## Wave 69 — Owner MFA Vault/KMS Provider SDK Adapter Execution

Esta abordagem introduz o branch SDK lazy no registry de segredos MFA, ainda sem endpoint externo real obrigatório.

### Entregue

- flag `OWNER_MFA_SECRET_VAULT_KMS_SDK_ADAPTER_ENABLED`;
- settings de status e secrets mocados para probe do branch SDK;
- imports lazy por provider aprovado;
- fallback seguro para `owner-mfa-secret-provider-vault-unavailable` quando o SDK não existe;
- query service `owner_mfa_vault_kms_provider_sdk_adapter_execution_queries`;
- comando `owner_mfa_vault_kms_provider_sdk_adapter_execute`;
- testes de sucesso com import mockado, dependência ausente, blocker e output sem segredo.

### Critério Go/No-Go

- Go:
  - dependency review ready;
  - real adapter habilitado;
  - SDK adapter habilitado;
  - import lazy disponível;
  - probe resolve sem expor segredo.
- No-Go:
  - dependência ausente;
  - SDK adapter desligado;
  - probe missing/timeout/unavailable;
  - tentativa de import obrigatório em startup/login;
  - necessidade de credencial real antes da review de endpoint.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Real Endpoint Review**

Objetivo:

- decidir o primeiro provider endpoint real a implementar, com credenciais, timeout e formato de resposta sem transformar todos os vendors em uma única mudança.

## Wave 70 — Owner MFA Vault/KMS Provider Real Endpoint Review

Esta abordagem escolhe Hashicorp Vault como primeiro endpoint real e formaliza o contrato antes da execução com `hvac`.

### Entregue

- query service `owner_mfa_vault_kms_provider_real_endpoint_review_queries`;
- comando `owner_mfa_vault_kms_provider_real_endpoint_review`;
- composição com SDK adapter execution;
- confirmação obrigatória de URL, auth, path/field, timeout e rollback;
- contrato inicial de settings `OWNER_MFA_HASHICORP_VAULT_*`;
- contrato de falhas, testes e redaction.

### Critério Go/No-Go

- Go:
  - SDK adapter execution ready;
  - target é `hashicorp-vault`;
  - endpoint/base URL confirmado;
  - auth strategy confirmada;
  - secret path/field confirmado;
  - timeout e rollback confirmados.
- No-Go:
  - provider diferente nesta primeira execução;
  - branch SDK bloqueado;
  - contrato de path/campo incompleto;
  - risco de imprimir segredo, token ou path completo.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Real Endpoint Execution**

Objetivo:

- implementar a primeira chamada real via `hvac` com client mockável, timeout/falhas mapeadas e sem expor secret material.

## Wave 71 — Owner MFA Hashicorp Vault Real Endpoint Execution

Esta abordagem implementa o primeiro endpoint real para MFA TOTP owner/admin usando Hashicorp Vault via `hvac`.

### Entregue

- branch `OWNER_MFA_HASHICORP_VAULT_ENDPOINT_ENABLED` dentro do adapter SDK;
- import lazy de `hvac`;
- client Hashicorp Vault com auth `token` ou `approle`;
- leitura KV v2 por `mount_point`, `path` e secret field configuráveis;
- mapeamento de `unavailable`, `timeout`, `permission-denied` e `missing`;
- query service `owner_mfa_hashicorp_vault_real_endpoint_execution_queries`;
- comando `owner_mfa_hashicorp_vault_real_endpoint_execute`;
- testes com client fake para sucesso, missing, permission, blocker e output sem segredo/path/token.

### Critério Go/No-Go

- Go:
  - real endpoint review ready;
  - flags real adapter, SDK adapter e Hashicorp endpoint habilitadas;
  - `hvac` importável;
  - auth e secret field configurados;
  - probe resolve sem expor secret material.
- No-Go:
  - endpoint flag desligada;
  - `hvac` ausente;
  - token/AppRole ausente;
  - permissão negada;
  - path/campo ausente no Vault.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Staging Smoke Evidence**

Objetivo:

- capturar a primeira evidência operacional contra staging, com smoke test controlado, rollback e redaction.

## Wave 72 — Owner MFA Hashicorp Vault Staging Smoke Evidence

Esta abordagem captura o smoke staging do endpoint Hashicorp Vault como evidência declarativa, sem automatizar login/challenge.

### Entregue

- query service `owner_mfa_hashicorp_vault_staging_smoke_evidence_queries`;
- comando `owner_mfa_hashicorp_vault_staging_smoke_evidence`;
- composição com `owner_mfa_hashicorp_vault_real_endpoint_execution_queries`;
- confirmations para probe staging, negative path, redaction, rollback e health pós-smoke;
- evidence pack sem segredo, token ou path completo;
- testes de ready, blocker e output redigido.

### Critério Go/No-Go

- Go:
  - execution Hashicorp Vault ready;
  - probe staging aprovada;
  - path inválido bloqueado;
  - logs/evidence redigidos;
  - rollback verificado;
  - health pós-smoke ready.
- No-Go:
  - endpoint real bloqueado;
  - ausência de redaction;
  - rollback não verificado;
  - health pós-smoke em watch/critical.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Production Readiness Review**

Objetivo:

- consolidar staging smoke, provider health, rollback e runbook para decidir Go/No-Go de produção do provider Vault/KMS.

## Wave 73 — Owner MFA Vault/KMS Provider Production Readiness Review

Esta abordagem consolida o Go/No-Go de produção para o provider Vault/KMS MFA owner/admin.

### Entregue

- query service `owner_mfa_vault_kms_provider_production_readiness_queries`;
- comando `owner_mfa_vault_kms_provider_production_readiness`;
- composição com staging smoke Hashicorp Vault;
- composição com provider health closure;
- confirmations operacionais para runbook, rollback owner, monitoring, change window e credential rotation;
- pacote `go_no_go` com decisão `GO`/`NO-GO`;
- runbook e rollback redigidos.

### Critério Go/No-Go

- Go:
  - smoke staging ready;
  - provider health closure ready;
  - runbook revisado;
  - monitoramento confirmado;
  - rollback owner confirmado;
  - janela de mudança confirmada;
  - rotação de credencial confirmada.
- No-Go:
  - smoke ou health bloqueado;
  - qualquer confirmation operacional ausente;
  - risco de exposição de segredo/token/path;
  - rollback não definido.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Production Gate Review**

Objetivo:

- transformar o Go técnico em gate operacional de ativação por tenant, com ordem de rollout e critérios de rollback.

## Wave 74 — Owner MFA Hashicorp Vault Production Gate Review

Esta abordagem transforma a readiness técnica em gate operacional de ativação controlada por tenant.

### Entregue

- query service `owner_mfa_hashicorp_vault_production_gate_queries`;
- comando `owner_mfa_hashicorp_vault_production_gate`;
- composição com production readiness;
- confirmations operacionais de tenant scope, rollout order, feature flags, support standby, rollback window e post-activation monitoring;
- activation plan redigido;
- decisão `GO`/`NO-GO` sem alterar ambiente.

### Critério Go/No-Go

- Go:
  - production readiness `GO`;
  - tenant canário confirmado;
  - ordem de rollout confirmada;
  - flags revisadas;
  - plantão e rollback window confirmados;
  - monitoramento pós-ativação reservado.
- No-Go:
  - readiness técnica bloqueada;
  - rollout global sem tenant canário;
  - plantão/rollback ausente;
  - monitoramento pós-ativação não confirmado.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Provider Production Activation Evidence**

Objetivo:

- capturar a evidência pós-ativação do tenant canário, sem transformar o comando em executor de deploy.

## Wave 75 — Owner MFA Vault/KMS Provider Production Activation Evidence

Esta abordagem captura a ativação production do provider Vault/KMS como evidência declarativa pós-gate.

### Entregue

- query service `owner_mfa_vault_kms_provider_production_activation_evidence_queries`;
- comando `owner_mfa_vault_kms_provider_production_activation_evidence`;
- composição com production gate Hashicorp Vault;
- confirmations de deploy, flags, probe, login/challenge, health, rollback e redaction;
- evidence pack redigido;
- rollback guidance sem executar rollback.

### Critério Go/No-Go

- Go:
  - production gate `GO`;
  - deploy/restart concluído;
  - flags habilitadas para o tenant canário;
  - probe pós-deploy aprovada;
  - login/challenge owner aprovado;
  - provider health ready;
  - rollback não necessário;
  - evidência redigida.
- No-Go:
  - gate bloqueado;
  - falha de login/challenge;
  - health não ready;
  - evidência contém material sensível;
  - rollback necessário ou não verificado.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Post-Activation Monitoring Review**

Objetivo:

- acompanhar a janela pós-ativação e classificar HEALTHY/WATCH/ROLLBACK com sinais objetivos.

## Wave 76 — Owner MFA Hashicorp Vault Post-Activation Monitoring Review

Esta abordagem classifica a janela pós-ativação do tenant canário Hashicorp Vault.

### Entregue

- query service `owner_mfa_hashicorp_vault_post_activation_monitoring_queries`;
- comando `owner_mfa_hashicorp_vault_post_activation_monitoring`;
- composição com production activation evidence;
- sinais declarativos de janela, provider health, spike de login, incidentes de suporte, rollback signal e redaction;
- classificações `HEALTHY`, `WATCH`, `ROLLBACK` e `BLOCKED`;
- rollback guidance sem execução automática.

### Critério Go/No-Go

- Healthy:
  - activation evidence ready;
  - janela de monitoramento concluída;
  - health estável;
  - sem spike de login/challenge;
  - sem incidentes de suporte;
  - sem rollback signal;
  - evidence redigida.
- Watch:
  - activation ready, mas algum sinal leve ainda não fechou.
- Rollback:
  - rollback signal presente.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Production Closure Review**

Objetivo:

- encerrar a trilha Hashicorp Vault com riscos residuais, próximos tenants e critérios de expansão.

## Wave 77 — Owner MFA Vault/KMS Production Closure Review

Esta abordagem encerra a trilha production do tenant canário Hashicorp Vault somente quando monitoring e critérios operacionais finais estão prontos.

### Entregue

- query service `owner_mfa_vault_kms_production_closure_queries`;
- comando `owner_mfa_vault_kms_production_closure`;
- composição com post-activation monitoring;
- critérios finais de rollback runbook, aceite de riscos residuais e plano de expansão tenant;
- guardrails para expansão sem automatizar rollout.

### Critério Go/No-Go

- Ready:
  - post-activation monitoring `HEALTHY`;
  - rollback runbook confirmado;
  - riscos residuais aceitos;
  - plano de tenant expansion documentado.
- Blocked:
  - monitoring `WATCH/BLOCKED`;
  - closure signal ausente.
- Rollback:
  - monitoring reporta rollback signal.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Tenant Expansion Review**

Objetivo:

- planejar expansão controlada para próximos tenants, com evidência própria por tenant e rollback window dedicada.

## Wave 78 — Owner MFA Hashicorp Vault Tenant Expansion Review

Esta abordagem transforma o closure do tenant canário em um plano de expansão controlada para próximos tenants.

### Entregue

- query service `owner_mfa_hashicorp_vault_tenant_expansion_queries`;
- comando `owner_mfa_hashicorp_vault_tenant_expansion_review`;
- composição com production closure;
- validação explícita de tenants-alvo ativos e fora de maintenance mode;
- sinais de janela, evidência por tenant, suporte, rollback e limite de um tenant por janela.

### Critério Go/No-Go

- Go:
  - closure canário `READY`;
  - tenants-alvo válidos;
  - expansão limitada a um tenant por janela;
  - evidência por tenant obrigatória;
  - suporte e rollback window confirmados.
- No-Go:
  - closure bloqueado;
  - target inexistente, inativo, em maintenance mode ou igual ao canário;
  - tentativa de expansão paralela.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution**

Objetivo:

- capturar a primeira evidência de execução da expansão em um tenant-alvo sem transformar isso em rollout global.

## Wave 79 — Owner MFA Hashicorp Vault Tenant Expansion Evidence Execution

Esta abordagem captura a evidência declarativa da primeira expansão Hashicorp Vault para um tenant-alvo.

### Entregue

- query service `owner_mfa_hashicorp_vault_tenant_expansion_evidence_queries`;
- comando `owner_mfa_hashicorp_vault_tenant_expansion_evidence`;
- composição com tenant expansion review;
- confirmations de flags, activation evidence, monitoring, login/challenge, provider health, rollback e redaction por target;
- rollback guidance limitado ao tenant-alvo.

### Critério Go/No-Go

- Go:
  - expansion review `READY`;
  - flags habilitadas para target;
  - activation evidence capturada;
  - monitoring pós-expansão agendado;
  - login/challenge e provider health saudáveis;
  - rollback não requerido;
  - evidence redigida.
- No-Go:
  - review bloqueada;
  - target sem monitoring agendado;
  - falha de login/challenge ou health;
  - rollback requerido;
  - evidence não redigida.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review**

Objetivo:

- monitorar o tenant-alvo recém-expandido antes de liberar qualquer próximo tenant.

## Wave 80 — Owner MFA Hashicorp Vault Target Post-Expansion Monitoring Review

Esta abordagem classifica a janela pós-expansão do tenant-alvo Hashicorp Vault.

### Entregue

- query service `owner_mfa_hashicorp_vault_target_post_expansion_monitoring_queries`;
- comando `owner_mfa_hashicorp_vault_target_post_expansion_monitoring`;
- composição com tenant expansion evidence;
- sinais declarativos de janela, provider health, spike de login, incidentes de suporte, rollback signal e redaction do target;
- classificações `HEALTHY`, `WATCH`, `ROLLBACK` e `BLOCKED`;
- rollback guidance limitado ao tenant-alvo.

### Critério Go/No-Go

- Healthy:
  - expansion evidence ready;
  - janela de monitoring do target concluída;
  - provider health do target estável;
  - sem spike de login/challenge no target;
  - sem incidentes de suporte do target;
  - sem rollback signal no target;
  - evidence redigida.
- Watch:
  - evidence ready, mas algum sinal do target ainda não fechou.
- Rollback:
  - rollback signal presente no target.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Next Tenant Expansion Review**

Objetivo:

- decidir se já vale repetir o ciclo para o próximo tenant ou encerrar a cadência de expansão.

## Wave 81 — Owner MFA Hashicorp Vault Next Tenant Expansion Review

Esta abordagem decide se a cadência Hashicorp Vault pode seguir para outro tenant, pausar ou bloquear.

### Entregue

- query service `owner_mfa_hashicorp_vault_next_tenant_expansion_queries`;
- comando `owner_mfa_hashicorp_vault_next_tenant_expansion_review`;
- composição com target post-expansion monitoring;
- validação de próximos tenants ativos e fora de maintenance mode;
- sinais de janela seguinte, capacidade operacional, evidence arquivada e limite de um tenant por janela;
- opção explícita de pausa sem blocker.

### Critério Go/No-Go

- Ready:
  - target atual `HEALTHY`;
  - próximo target válido e diferente do canário/current target;
  - janela e capacidade operacional confirmadas;
  - evidence do target atual arquivada;
  - expansão continua single-tenant.
- Paused:
  - decisão explícita de parar após target atual.
- Blocked:
  - target atual em `WATCH/BLOCKED/ROLLBACK`;
  - próximo target inválido;
  - tentativa de paralelismo;
  - sinais de cadência ausentes.

### Próxima abordagem recomendada

**Owner MFA Hashicorp Vault Expansion Cadence Closure Review**

Objetivo:

- encerrar ou consolidar a cadência de expansão antes de novas ondas de hardening/rotação.

## Wave 82 — Owner MFA Hashicorp Vault Expansion Cadence Closure Review

Esta abordagem fecha ou consolida a cadência Hashicorp Vault após canário, target atual e decisão de próximo ciclo.

### Entregue

- query service `owner_mfa_hashicorp_vault_expansion_cadence_closure_queries`;
- comando `owner_mfa_hashicorp_vault_expansion_cadence_closure`;
- composição com next tenant expansion review;
- sinais finais de decisão registrada, evidence archive, riscos revisados, rotation runbook e audit evidence;
- residual risks e runbook final sem ativar próximo tenant.

### Critério Go/No-Go

- Ready:
  - cadência anterior `READY` ou `PAUSED`;
  - decisão registrada;
  - evidências arquivadas;
  - riscos residuais revisados;
  - rotation runbook enfileirado;
  - pacote de audit evidence pronto.
- No-Go:
  - cadência anterior `BLOCKED`;
  - qualquer sinal final de closure ausente.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Rotation Runbook Review**

Objetivo:

- formalizar rotação de token/AppRole/segredos do provider após estabilização da cadência.

## Wave 83 — Owner MFA Vault/KMS Rotation Runbook Review

Esta abordagem formaliza o runbook de rotação Vault/KMS pós-cadência, sem executar a rotação.

### Entregue

- query service `owner_mfa_vault_kms_rotation_runbook_queries`;
- comando `owner_mfa_vault_kms_rotation_runbook`;
- composição com expansion cadence closure;
- sinais de escopo, owner, acesso Vault, janela, rollback credentials, probe pós-rotação, tenants afetados e redaction;
- rotation steps e rollback steps redigidos.

### Critério Go/No-Go

- Go:
  - cadence closure `READY`;
  - escopo e tenants afetados explícitos;
  - owner e acesso ao Vault confirmados;
  - janela de rotação confirmada;
  - rollback credentials disponíveis;
  - probe pós-rotação definido;
  - evidence redaction confirmada.
- No-Go:
  - closure bloqueado;
  - falta de acesso/owner/janela;
  - rollback ou probe não definidos;
  - redaction não confirmada.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Rotation Evidence Execution**

Objetivo:

- capturar evidência declarativa da rotação executada fora do command, sem imprimir material sensível.

## Wave 84 — Owner MFA Vault/KMS Rotation Evidence Execution

Esta abordagem captura a evidência declarativa da rotação Vault/KMS executada fora do command.

### Entregue

- query service `owner_mfa_vault_kms_rotation_evidence_queries`;
- comando `owner_mfa_vault_kms_rotation_evidence`;
- composição com rotation runbook;
- confirmations de rotação executada, nova credencial ativa, credencial antiga revogada/agendada, probe, login/challenge, health, rollback e redaction;
- evidence pack redigido e rollback guidance.

### Critério Go/No-Go

- Go:
  - rotation runbook `READY`;
  - rotação executada;
  - nova credencial ativa;
  - credencial anterior revogada ou com revogação agendada;
  - probe pós-rotação aprovado;
  - login/challenge owner aprovado;
  - provider health ready;
  - rollback não requerido;
  - evidence redigida.
- No-Go:
  - runbook bloqueado;
  - probe/login/health falhar;
  - rollback requerido;
  - evidence não redigida.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Post-Rotation Monitoring Review**

Objetivo:

- observar estabilidade do provider após rotação antes de retomar qualquer cadência de expansão.

## Wave 85 — Owner MFA Vault/KMS Post-Rotation Monitoring Review

Esta abordagem classifica a janela pós-rotação do provider Vault/KMS.

### Entregue

- query service `owner_mfa_vault_kms_post_rotation_monitoring_queries`;
- comando `owner_mfa_vault_kms_post_rotation_monitoring`;
- composição com rotation evidence;
- sinais de janela, provider health, spike de login, incidentes de suporte, rollback signal e redaction;
- classificações `HEALTHY`, `WATCH`, `ROLLBACK` e `BLOCKED`;
- rollback guidance para restauração de credencial fora do command.

### Critério Go/No-Go

- Healthy:
  - rotation evidence `READY`;
  - janela pós-rotação concluída;
  - provider health estável;
  - sem spike de login/challenge;
  - sem incidentes de suporte;
  - sem rollback signal;
  - evidence redigida.
- Watch:
  - evidence ready, mas algum sinal ainda não fechou.
- Rollback:
  - rollback signal presente após rotação.

### Próxima abordagem recomendada

**Owner MFA Vault/KMS Rotation Closure Review**

Objetivo:

- encerrar a trilha de rotação com riscos residuais, audit evidence e decisão de retomar ou pausar expansão.

## Wave 86 — Owner MFA Vault/KMS Rotation Closure Review

Esta abordagem encerra a rotação Vault/KMS somente depois de monitoring pós-rotação saudável e evidências operacionais arquivadas.

### Entregue

- query service `owner_mfa_vault_kms_rotation_closure_queries`;
- comando `owner_mfa_vault_kms_rotation_closure`;
- composição com post-rotation monitoring;
- sinais de decisão registrada, evidência arquivada, riscos aceitos, plano de retomada, rollback window e audit evidence;
- classificações `READY`, `WATCH`, `ROLLBACK` e `BLOCKED`;
- guardrails para retomada sem expansão automática.

### Critério Go/No-Go

- Ready:
  - post-rotation monitoring `HEALTHY`;
  - closure decision registrada;
  - evidência de rotação/monitoramento arquivada;
  - riscos residuais aceitos;
  - plano de retomada de expansão documentado;
  - rollback window fechada ou estendida;
  - audit evidence pronta.
- Watch:
  - monitoring pós-rotação ainda exige observação.
- Rollback:
  - rollback signal presente no monitoring.
- Blocked:
  - algum sinal de closure obrigatório ausente.

### Próxima abordagem recomendada

**Owner MFA Audit Evidence Export Review**

Objetivo:

- decidir se já vale exportar evidência formal da trilha MFA/Vault para auditoria, sem transformar `accounts` em módulo de export.

## Wave 87 — Owner MFA Audit Evidence Export Review

Esta abordagem define o contrato de export de evidência MFA owner/admin via módulo `audit`, sem transformar `accounts` em exportador.

### Entregue

- query service `owner_mfa_audit_evidence_export_review_queries`;
- comando `owner_mfa_audit_evidence_export_review`;
- sample tenant-scoped via `audit_evidence_export_queries`;
- filtro canônico `module=accounts`;
- detecção de ações MFA no `AuditLog`;
- sinais de actions esperadas, escopo, redaction e destinatário.

### Critério Go/No-Go

- Go:
  - `tenant_id` explícito;
  - export audit canônico disponível;
  - sample contém ações MFA;
  - actions esperadas confirmadas;
  - escopo de export documentado;
  - redaction revisada;
  - destinatário aprovado.
- No-Go:
  - ausência de tenant;
  - ausência de eventos MFA;
  - metadata/redaction ou destinatário não aprovados.

### Próxima abordagem recomendada

**Owner MFA Audit Evidence Export Execution**

Objetivo:

- executar o export formal tenant-scoped da evidência MFA com formato e filtros definidos, mantendo metadata desabilitada por padrão.

## Wave 88 — Owner MFA Audit Evidence Export Execution

Esta abordagem executa o export formal tenant-scoped da evidência MFA owner/admin a partir do `AuditLog`.

### Entregue

- query service `owner_mfa_audit_evidence_export_execution_queries`;
- comando `export_owner_mfa_audit_evidence`;
- composição com export review;
- export canônico via `audit_evidence_export_queries`;
- filtro `module=accounts`;
- filtro de ações MFA;
- saída `jsonl`/`csv` sem metadata.

### Critério Go/No-Go

- Go:
  - review de export MFA `READY`;
  - `tenant_id` explícito;
  - pelo menos uma ação MFA na amostra;
  - redaction/recipient/scope confirmados.
- No-Go:
  - review bloqueada;
  - ausência de evento MFA;
  - formato inválido;
  - tentativa de depender de metadata sensível.

### Próxima abordagem recomendada

**Owner MFA Audit Evidence Export Closure Review**

Objetivo:

- fechar a trilha de evidência MFA exportada com riscos residuais, uso do artefato e decisão sobre storage/assinatura futura.

## Wave 89 — Owner MFA Audit Evidence Export Closure Review

Esta abordagem fecha operacionalmente o export de evidência MFA owner/admin após a geração do artefato tenant-scoped.

### Entregue

- query service `owner_mfa_audit_evidence_export_closure_queries`;
- comando `owner_mfa_audit_evidence_export_closure`;
- composição com export execution;
- validação de artefato entregue;
- validação de owner de retenção;
- decisão registrada sobre storage/assinatura;
- riscos residuais aceitos.

### Critério Go/No-Go

- Go:
  - export execution concluído;
  - `export_count > 0`;
  - artefato entregue;
  - owner de retenção confirmado;
  - decisão de storage/assinatura registrada;
  - riscos residuais aceitos.
- No-Go:
  - export bloqueado ou vazio;
  - artefato não entregue;
  - retenção/storage sem owner ou decisão;
  - riscos residuais não aceitos.

### Próxima abordagem recomendada

**Owner MFA Track Closure Review**

Objetivo:

- encerrar a trilha MFA/Vault/Audit como pacote operacional e decidir se o próximo ROI é storage/assinatura, novo tenant ou outra área de segurança.

## Wave 90 — Owner MFA Track Closure Review

Esta abordagem fecha a trilha MFA owner/admin como pacote operacional consolidado, depois de Vault/KMS, rotação e evidência auditável.

### Entregue

- query service `owner_mfa_track_closure_queries`;
- comando `owner_mfa_track_closure`;
- composição com `owner_mfa_audit_evidence_export_closure_queries`;
- sinais de decisão final, estado de rollout, handoff de suporte, próxima decisão de ROI e riscos residuais;
- classificação `READY/BLOCKED`.

### Critério Go/No-Go

- Go:
  - audit evidence export closure `READY`;
  - decisão final da trilha registrada;
  - estado de rollout/enforcement/rollback documentado;
  - suporte preparado para operar MFA/recovery/bypass;
  - próxima decisão de ROI registrada;
  - riscos residuais aceitos.
- No-Go:
  - evidência auditável bloqueada;
  - handoff de suporte ausente;
  - estado de rollout indefinido;
  - riscos residuais sem aceite.

### Próxima abordagem recomendada

**Security ROI Re-Selection Review**

Objetivo:

- escolher o próximo eixo de maior retorno agora que a trilha MFA/Vault/Audit está operacionalmente fechada.

## Wave 91 — Security ROI Re-Selection Review

Esta abordagem reabre a seleção de ROI de segurança após closure MFA/Vault/Audit e evita continuar refinando o mesmo eixo por inércia.

### Entregue

- query service `security_roi_reselection_queries`;
- comando `security_roi_reselection`;
- composição com `owner_mfa_track_closure_queries`;
- matriz curta de candidatos de segurança;
- scoring declarativo por risco/ROI;
- recomendação objetiva de próxima trilha.

### Critério Go/No-Go

- Go:
  - MFA track closure `READY`;
  - pelo menos um candidato de segurança cruza o threshold de ROI;
  - recomendação única emitida em `next_tracks`.
- No-Go:
  - MFA track closure bloqueada;
  - nenhum candidato de segurança acima do threshold;
  - ausência de sinal operacional para continuar em segurança.

### Decisão de ROI

Recomendação atual:

**API Key Governance Foundation Review**

Motivo:

- API keys são superfície programática de acesso;
- governança de chaves reduz risco sistêmico cross-tenant e de automação indevida;
- tem maior ROI que seguir polindo storage/assinatura MFA ou expandir Vault sem novo alvo operacional confirmado.

### Próxima abordagem recomendada

**API Key Governance Foundation Review**

Objetivo:

- revisar o módulo `api_keys` e decidir modelo mínimo tenant-scoped para criação, escopo, revogação, auditoria e uso seguro de chaves.

## Wave 92 — API Key Governance Foundation Review

Esta abordagem define o contrato mínimo de governança para API keys antes de criar modelo, segredo ou autenticação real.

### Entregue

- query service `api_key_governance_foundation_queries`;
- comando `api_key_governance_foundation`;
- requisitos declarativos para modelo tenant-scoped;
- contrato de hash de segredo;
- contrato de escopos, revogação, auditoria, last-used e rate limit;
- fronteira explícita para não criar API pública nesta review.

### Critério Go/No-Go

- Go:
  - superfície pública/integrador confirmada;
  - modelo tenant-scoped obrigatório;
  - secret storage via hash obrigatório;
  - escopos declarativos obrigatórios;
  - revogação obrigatória;
  - eventos auditáveis obrigatórios;
  - last-used tracking obrigatório;
  - rate limit obrigatório.
- No-Go:
  - API pública ainda não confirmada;
  - tentativa de guardar segredo claro;
  - acesso global implícito;
  - ausência de auditoria ou revogação.

### Próxima abordagem recomendada

**API Key Model Minimal Contract Execution**

Objetivo:

- criar o modelo mínimo `ApiKey` tenant-scoped com hash/prefix/scopes/status/timestamps, ainda sem autenticação runtime.

## Wave 93 — API Key Model Minimal Contract Execution

Esta abordagem tira `api_keys` do skeleton e cria o modelo mínimo governável antes da autenticação runtime.

### Entregue

- modelo `ApiKey`;
- migration `api_keys.0001_initial`;
- admin read-only básico;
- command service `api_key_commands`;
- criação com segredo retornado uma única vez e hash persistido;
- revogação tenant-scoped sem deletar histórico;
- eventos `api_key.created` e `api_key.revoked`.

### Critério Go/No-Go

- Go:
  - `tenant_id` obrigatório;
  - hash persistido diferente do valor claro;
  - prefixo único;
  - scopes persistidos;
  - revogação preserva registro;
  - audit não recebe segredo nem hash.
- No-Go:
  - armazenamento de segredo claro;
  - revogação cross-tenant;
  - autenticação runtime antes de modelo governável.

### Próxima abordagem recomendada

**API Key Runtime Authentication Contract Review**

Objetivo:

- definir como requests serão autenticadas por prefix/hash, escopo, status ativo, tenant e rate limit, sem abrir API pública ampla de uma vez.

## Wave 94 — API Key Runtime Authentication Contract Review

Esta abordagem define o contrato runtime antes de implementar autenticação real, mantendo API pública e rate limit fora do corte.

### Entregue

- query service `api_key_runtime_authentication_contract_queries`;
- comando `api_key_runtime_authentication_contract`;
- contrato de `Authorization: Bearer`;
- contrato de lookup por `tenant_id + prefix`;
- contrato de verificação por hash do segredo completo;
- contrato de status ativo, escopo mínimo, `last_used_at`, falha auditável e boundary de rate limit.

### Critério Go/No-Go

- Go:
  - modelo `ApiKey` disponível;
  - credencial somente via Bearer header;
  - tenant resolvido pelo request;
  - lookup por prefixo dentro do tenant;
  - hash verification obrigatório;
  - status `active` obrigatório;
  - escopo mínimo obrigatório;
  - `last_used_at` e `api_key.auth_failed` definidos;
  - rate-limit boundary definido antes de endpoint público.
- No-Go:
  - API key definindo tenant implicitamente;
  - segredo em query string;
  - aceitar prefixo sem validar hash;
  - endpoint público sem escopo/rate-limit;
  - logs com header completo, segredo ou hash.

### Próxima abordagem recomendada

**API Key Runtime Authentication Skeleton Execution**

Objetivo:

- criar o skeleton de autenticação runtime sem abrir superfície pública ampla: parser Bearer, lookup tenant-scoped, verificação de hash/status/escopo, falha segura e testes de contrato.

## Wave 95 — API Key Runtime Authentication Skeleton Execution

Esta abordagem implementa o service runtime mínimo sem plugar em DRF nem abrir endpoint público.

### Entregue

- service `api_key_runtime_authentication`;
- parser de `Authorization: Bearer`;
- extração de prefixo e lookup por `tenant_id + prefix`;
- validação de status ativo;
- validação de segredo completo via hash;
- validação de escopo mínimo;
- atualização de `last_used_at` em sucesso;
- auditoria `api_key.auth_failed` em falhas relevantes;
- `rate_limit_key` declarativa para integração futura.

### Critério Go/No-Go

- Go:
  - sucesso autentica apenas chave ativa do mesmo tenant;
  - cross-tenant falha sem atualizar `last_used_at`;
  - segredo com prefixo correto mas hash inválido falha;
  - chave revogada falha;
  - escopo insuficiente falha;
  - audit não contém segredo, hash ou header completo.
- No-Go:
  - plugar em DRF antes de permission/rate-limit;
  - endpoint público usando API key sem escopo explícito;
  - logs com material sensível;
  - API key sobrescrevendo tenant do request.

### Próxima abordagem recomendada

**API Key DRF Authentication Adapter Review**

Objetivo:

- decidir o menor adapter DRF seguro para usar o service runtime em uma surface pública controlada, ainda com permission/rate-limit explícitos.

## Wave 96 — API Key DRF Authentication Adapter Review

Esta abordagem revisa o adapter DRF antes de implementá-lo, com foco em evitar ativação global acidental.

### Entregue

- query service `api_key_drf_authentication_adapter_review_queries`;
- comando `api_key_drf_authentication_adapter_review`;
- contrato de adapter fino em `api_keys.interfaces`;
- decisão de opt-in por view/surface;
- bloqueio explícito contra `DEFAULT_AUTHENTICATION_CLASSES`;
- contrato de principal seguro;
- contrato de escopo mínimo/permission dedicada;
- boundary para `rate_limit_key` sem throttle real.

### Critério Go/No-Go

- Go:
  - service runtime disponível;
  - tenant middleware obrigatório;
  - opt-in por view obrigatório;
  - autenticação global proibida;
  - escopo mínimo obrigatório;
  - principal seguro obrigatório;
  - permission class planejada;
  - hook de rate-limit planejado;
  - contrato de falha definido;
  - adapter não cria endpoint público.
- No-Go:
  - adicionar API key em `DEFAULT_AUTHENTICATION_CLASSES`;
  - autenticar view sem escopo;
  - principal expor segredo/hash/header;
  - criar endpoint público dentro do adapter;
  - implementar throttle improvisado no adapter.

### Próxima abordagem recomendada

**API Key DRF Authentication Adapter Execution**

Objetivo:

- criar authentication class/permission mínimos em `api_keys.interfaces`, opt-in por view, delegando para `api_key_runtime_authentication`, ainda sem endpoint público amplo.

## Wave 97 — API Key DRF Authentication Adapter Execution

Esta abordagem implementa o adapter DRF mínimo sem alterar settings globais e sem criar endpoint público.

### Entregue

- `ApiKeyAuthentication`;
- `HasApiKeyScope`;
- `ApiKeyPrincipal`;
- autenticação opt-in por view;
- delegação para `api_key_runtime_authentication`;
- principal seguro sem segredo/hash/header;
- `request.auth` com `rate_limit_key`;
- permissão exigindo `required_api_key_scope` explícito.

### Critério Go/No-Go

- Go:
  - view opt-in autentica chave ativa do tenant correto;
  - `DEFAULT_AUTHENTICATION_CLASSES` permanece sem API key;
  - chave inválida/cross-tenant retorna falha e audita;
  - escopo ausente ou insuficiente nega acesso;
  - principal não expõe segredo nem hash;
  - `rate_limit_key` fica disponível para throttle futuro.
- No-Go:
  - ativação global por settings;
  - view sem `required_api_key_scope`;
  - endpoint público sem permission explícita;
  - vazamento de segredo/hash/header no principal ou logs;
  - rate limit improvisado no adapter.

### Próxima abordagem recomendada

**API Key Public Endpoint Pilot Review**

Objetivo:

- escolher uma surface pública mínima e segura para piloto, com escopo explícito, rate-limit planejado e sem ampliar o contrato além do necessário.

## Wave 98 — API Key Public Endpoint Pilot Review

Esta abordagem escolhe o primeiro endpoint público candidato sem implementá-lo ainda.

### Entregue

- query service `api_key_public_endpoint_pilot_review_queries`;
- comando `api_key_public_endpoint_pilot_review`;
- recomendação de piloto `GET /api/v1/catalog/products/`;
- escopo recomendado `read:catalog`;
- decisão de payload read-only e sem PII;
- bloqueio contra reutilização de `/ops/`;
- exigência de URL versionada, tenant por request e rollout flag.

### Critério Go/No-Go

- Go:
  - adapter DRF disponível;
  - endpoint read-only;
  - tenant por request;
  - escopo explícito;
  - plano de rate-limit;
  - payload seguro e sem PII;
  - sem reaproveitar `/ops/`;
  - URL versionada;
  - flag/config de rollout.
- No-Go:
  - pedidos/clientes/pagamentos como primeiro piloto;
  - aceitar `tenant_id` via query/body;
  - expor PII;
  - escrita programática;
  - endpoint sem rate-limit planejado.

### Próxima abordagem recomendada

**API Key Public Catalog Products Endpoint Execution**

Objetivo:

- implementar `GET /api/v1/catalog/products/` com `ApiKeyAuthentication`, `HasApiKeyScope`, `read:catalog`, tenant-scoped query e payload seguro.

## Wave 99 — API Key Public Catalog Products Endpoint Execution

Esta abordagem implementa o primeiro endpoint público protegido por API key.

### Entregue

- query service `public_catalog_api_queries`;
- view `PublicCatalogProductsApiView`;
- URL `GET /api/v1/catalog/products/`;
- inclusão em `config.urls`;
- flag `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED`;
- autenticação `ApiKeyAuthentication`;
- permissão `HasApiKeyScope`;
- escopo `read:catalog`;
- testes de tenant, escopo, flag, paginação e ausência de fallback.

### Critério Go/No-Go

- Go:
  - retorna apenas produtos ativos/publicados do tenant atual;
  - não retorna fixtures quando tenant não tem produtos;
  - rejeita chave sem `read:catalog`;
  - rejeita chave de outro tenant;
  - oculta endpoint quando flag desligada;
  - limita `page_size` a 50;
  - payload não expõe `tenant_id`, estoque bruto, segredo ou hash.
- No-Go:
  - aceitar `tenant_id` por query/body;
  - reutilizar `/ops/`;
  - expor pedidos/clientes/pagamentos;
  - expor estoque bruto/PII;
  - liberar sem flag;
  - criar escrita programática.

### Próxima abordagem recomendada

**API Key Public Endpoint Rate Limit Review**

Objetivo:

- transformar a `rate_limit_key` já disponível no adapter em contrato de throttle por tenant/chave antes de ampliar a API pública.

## Wave 100 — API Key Public Endpoint Rate Limit Review

Esta abordagem define o contrato de rate limit para endpoints públicos por API key antes de implementar throttle real.

### Entregue

- query service `api_key_public_endpoint_rate_limit_review_queries`;
- comando `api_key_public_endpoint_rate_limit_review`;
- política recomendada `fixed-window`;
- escopo de limite `tenant + api_key + endpoint`;
- limite inicial recomendado de 120 requests por 60 segundos;
- contrato de `Retry-After` em 429;
- evento `api_key.rate_limited`;
- boundary para não alterar settings globais de DRF.

### Critério Go/No-Go

- Go:
  - endpoint público ativo;
  - `rate_limit_key` disponível;
  - limite por tenant+key;
  - cache backend disponível;
  - fixed-window aceito para v1;
  - settings/env para limite default e override por endpoint;
  - resposta 429 com `Retry-After`;
  - auditoria `api_key.rate_limited`;
  - falha deve ser fail-closed.
- No-Go:
  - rate limit só por IP;
  - aplicar throttle global em DRF;
  - vazar segredo/hash/header em audit/log;
  - aplicar em storefront HTML;
  - misturar quotas comerciais nesta primeira versão.

### Próxima abordagem recomendada

**API Key Public Endpoint Rate Limit Execution**

Objetivo:

- implementar service/throttle opt-in usando cache Django, `rate_limit_key + endpoint`, 429 com `Retry-After` e auditoria segura.

## Wave 101 — API Key Public Endpoint Rate Limit Execution

Esta abordagem implementa rate limit real, opt-in, para o endpoint público de catálogo.

### Entregue

- service `api_key_rate_limit`;
- throttle `ApiKeyRateLimitThrottle`;
- integração em `PublicCatalogProductsApiView`;
- settings/env de limite default e override do catálogo;
- resposta `429` com `Retry-After`;
- AuditLog `api_key.rate_limited`;
- isolamento por `rate_limit_key + endpoint`;
- testes de limite excedido e isolamento por API key.

### Critério Go/No-Go

- Go:
  - duas requisições dentro do limite passam;
  - requisição excedente retorna `429`;
  - resposta contém `Retry-After`;
  - audit não contém segredo, hash ou header;
  - limite é isolado por API key;
  - `DEFAULT_THROTTLE_CLASSES` não é alterado.
- No-Go:
  - throttle global;
  - liberar tráfego em falha de identidade/cache;
  - limitar apenas por IP;
  - vazar segredo/hash/header;
  - aplicar em storefront HTML.

### Próxima abordagem recomendada

**API Key Public Endpoint Observability Review**

Objetivo:

- revisar métricas e dashboard mínimos para autenticação, 401/403/429, uso por tenant/key e saúde do endpoint público.

## Wave 102 — API Key Public Endpoint Observability Review

Esta abordagem define o contrato de observabilidade antes de criar métricas reais para API keys públicas.

### Entregue

- query service `api_key_public_endpoint_observability_review_queries`;
- comando `api_key_public_endpoint_observability_review`;
- métricas recomendadas para requests, auth failures, rate limit e endpoint enabled;
- contrato de labels `tenant_id`, `endpoint`, `result` e prefixo seguro;
- exigência de alert rules e dashboard mínimos;
- bloqueio explícito contra segredo/hash/header em métricas/logs.

### Critério Go/No-Go

- Go:
  - endpoint público ativo;
  - eventos de auth failure disponíveis;
  - eventos de rate limit disponíveis;
  - métricas Prometheus obrigatórias;
  - labels de endpoint e tenant obrigatórias;
  - prefixo permitido apenas como label segura;
  - sem segredo/hash/header;
  - alert rules e dashboard obrigatórios.
- No-Go:
  - endpoint de métricas protegido por API key pública;
  - métrica com segredo/hash/header;
  - ausência de alertas para 401/403/429;
  - dashboard sem tenant/endpoint;
  - misturar billing/quotas comerciais.

### Próxima abordagem recomendada

**API Key Public Endpoint Metrics Execution**

Objetivo:

- criar service e endpoint Prometheus protegidos por token de observabilidade, exportando métricas mínimas de requests, falhas e rate limit.

## Wave 103 — API Key Public Endpoint Metrics Execution

Esta abordagem implementa métricas Prometheus mínimas para endpoints públicos por API key.

### Entregue

- service `api_key_public_endpoint_metrics`;
- endpoint `/api-keys/metrics/public-endpoints/`;
- setting `API_KEYS_OBSERVABILITY_TOKEN`;
- métricas `hubx_api_key_public_request_total`;
- métricas `hubx_api_key_auth_failure_total`;
- métricas `hubx_api_key_rate_limited_total`;
- métrica `hubx_api_key_public_endpoint_enabled`;
- integração com sucesso do catálogo, falha de auth e rate limit.

### Critério Go/No-Go

- Go:
  - scrape exige token de observabilidade;
  - API key pública não autentica o scrape;
  - sucesso incrementa `result="success"`;
  - auth failure incrementa métrica própria;
  - rate limit incrementa métrica própria;
  - payload não contém segredo, hash ou header.
- No-Go:
  - endpoint de métricas protegido por API key pública;
  - exportar segredo/hash/header;
  - misturar billing/quotas;
  - criar dashboard sem alertas mínimos.

### Próxima abordagem recomendada

**API Key Public Endpoint Dashboard Review**

Objetivo:

- revisar dashboard/alert rules mínimos para 401/403/429, endpoint enabled e volume por tenant/endpoint antes de rollout maior.

## Wave 104 — API Key Public Endpoint Dashboard Review

Esta abordagem revisa o contrato mínimo de dashboard Grafana para endpoints públicos por API key.

### Entregue

- query service `api_key_public_endpoint_dashboard_review_queries`;
- comando `api_key_public_endpoint_dashboard_review`;
- dashboard recomendado `Hubx API Key Public Endpoints`;
- painéis mínimos para requests, auth failures, rate limit, endpoint enabled e top tenants;
- contrato de labels seguras e baixa cardinalidade;
- separação explícita entre dashboard e alert rules.

### Critério Go/No-Go

- Go:
  - endpoint Prometheus já disponível;
  - scrape protegido por token de observabilidade;
  - painel de requests por tenant/endpoint/result;
  - painel de auth failures por tenant/endpoint/reason;
  - painel de rate limit por tenant/endpoint/prefix;
  - painel de endpoint enabled;
  - sem segredo, hash, header ou valor claro;
  - alert rules planejadas fora do dashboard.
- No-Go:
  - dashboard depender de API key pública;
  - labels de alta cardinalidade;
  - expor segredo/hash/header;
  - usar dashboard como substituto de alerta;
  - misturar billing/quotas comerciais.

### Próxima abordagem recomendada

**API Key Public Endpoint Dashboard Execution**

Objetivo:

- materializar o JSON inicial de Grafana em `infra/observability/grafana`, consumindo as métricas já expostas sem criar métricas novas.

## Wave 105 — API Key Public Endpoint Dashboard Execution

Esta abordagem materializa o dashboard inicial de Grafana para endpoints públicos por API key.

### Entregue

- dashboard `infra/observability/grafana/api-key-public-endpoints-dashboard.json`;
- datasource parametrizado `DS_PROMETHEUS`;
- variáveis `tenant_id` e `endpoint`;
- painéis de request rate, auth failures, rate limit, endpoint enabled e top tenants;
- teste de contrato do artefato JSON;
- documentação de importação no runbook de observabilidade.

### Critério Go/No-Go

- Go:
  - JSON válido;
  - datasource Prometheus parametrizado;
  - consultas usam somente métricas de `api_keys`;
  - painéis incluem tenant e endpoint;
  - sem segredo, hash, header ou valor claro;
  - dashboard não cria métricas novas.
- No-Go:
  - dashboard consultar banco/API diretamente;
  - depender de API key pública;
  - expor material sensível;
  - misturar billing/quotas;
  - tratar dashboard como substituto de alert rules.

### Próxima abordagem recomendada

**API Key Public Endpoint Alert Rules Review**

Objetivo:

- revisar alert rules mínimas para picos de auth failure, rate limit e endpoint disabled antes de rollout produtivo maior.

## Wave 106 — API Key Public Endpoint Alert Rules Review

Esta abordagem revisa o contrato mínimo de alert rules Prometheus para endpoints públicos por API key.

### Entregue

- query service `api_key_public_endpoint_alert_rules_review_queries`;
- comando `api_key_public_endpoint_alert_rules_review`;
- alertas recomendados para auth failures, rate limit e endpoint disabled;
- contrato de labels tenant/endpoint com baixa cardinalidade;
- severidade inicial `warning`;
- separação explícita entre review e YAML Prometheus real.

### Critério Go/No-Go

- Go:
  - endpoint Prometheus disponível;
  - dashboard versionado disponível;
  - alerta de auth failure exigido;
  - alerta de rate limit exigido;
  - alerta de endpoint disabled exigido;
  - labels tenant/endpoint seguras;
  - annotations com orientação de triagem;
  - sem segredo, hash, header ou valor claro.
- No-Go:
  - alertar por API key completa/hash;
  - consultar banco ou audit log diretamente;
  - criar alerta sem runbook/description;
  - começar com critical sem baseline;
  - misturar billing/quotas comerciais.

### Próxima abordagem recomendada

**API Key Public Endpoint Alert Rules Execution**

Objetivo:

- materializar `infra/observability/prometheus/api-keys-alert-rules.yml` com os três alertas mínimos e validar o artefato.

## Wave 107 — API Key Public Endpoint Alert Rules Execution

Esta abordagem materializa as alert rules iniciais de Prometheus para endpoints públicos por API key.

### Entregue

- arquivo `infra/observability/prometheus/api-keys-alert-rules.yml`;
- alerta `HubxApiKeyPublicAuthFailuresHigh`;
- alerta `HubxApiKeyPublicRateLimitedHigh`;
- alerta `HubxApiKeyPublicEndpointDisabled`;
- severidade inicial `warning`;
- annotations com triagem por dashboard, scrape, flags e audit events;
- teste de contrato do artefato YAML.

### Critério Go/No-Go

- Go:
  - YAML versionado;
  - três alertas mínimos presentes;
  - métricas existentes usadas;
  - labels tenant/endpoint preservadas;
  - sem segredo, hash, header ou API key em claro;
  - sem métricas novas.
- No-Go:
  - alertar por API key completa/hash;
  - depender de consulta direta a banco;
  - misturar billing/quotas;
  - provisionar Prometheus/Alertmanager automaticamente.

### Próxima abordagem recomendada

**API Key Public Endpoint Observability Closure Review**

Objetivo:

- fechar a trilha pública de observabilidade de API keys revisando scrape, métricas, dashboard, alert rules e riscos residuais antes de rollout ampliado.

## Wave 108 — API Key Public Endpoint Observability Closure Review

Esta abordagem fecha a trilha de observabilidade pública de API keys para este ciclo.

### Entregue

- query service `api_key_public_endpoint_observability_closure_queries`;
- comando `api_key_public_endpoint_observability_closure`;
- verificação de metrics service;
- verificação de endpoint Prometheus protegido;
- verificação de dashboard Grafana versionado;
- verificação de alert rules Prometheus versionadas;
- verificação de runbook de observabilidade;
- lista de riscos residuais e próximos tracks.

### Critério Go/No-Go

- Go:
  - metrics service presente;
  - endpoint Prometheus presente;
  - dashboard versionado presente;
  - alert rules versionadas presentes;
  - runbook atualizado;
  - `--rollout-ready` informado;
  - sem segredo, hash, header ou valor claro de API key.
- No-Go:
  - artifact ausente;
  - rollout operacional não aceito;
  - ativar Prometheus/Grafana/Alertmanager dentro da closure;
  - misturar billing/quotas;
  - adicionar endpoint público sem aderir ao contrato de métricas.

### Próxima abordagem recomendada

**API Key Public Endpoint Production Rollout Review**

Objetivo:

- revisar ativação real por ambiente: token, scrape, import do dashboard, alert rules carregadas e evidências mínimas de smoke.

## Wave 109 — API Key Public Endpoint Production Rollout Review

Esta abordagem revisa o checklist de rollout produtivo da observabilidade pública de API keys.

### Entregue

- query service `api_key_public_endpoint_production_rollout_review_queries`;
- comando `api_key_public_endpoint_production_rollout_review`;
- checklist de token, scrape, dashboard, alert rules, smoke e evidência;
- plano de rollback;
- bloqueio explícito contra exposição de segredo/hash/header/API key em claro;
- separação entre review e ativação real de ambiente.

### Critério Go/No-Go

- Go:
  - closure de observabilidade pronta;
  - token produtivo configurado;
  - scrape planejado;
  - dashboard planejado;
  - alert rules planejadas;
  - smoke planejado;
  - rollback disponível;
  - evidência sanitizada obrigatória;
  - aceite operacional explícito.
- No-Go:
  - ativar produção dentro da review;
  - capturar token/API key em evidência;
  - ausência de rollback;
  - ausência de smoke;
  - misturar billing/quotas comerciais.

### Próxima abordagem recomendada

**API Key Public Endpoint Production Activation Evidence**

Objetivo:

- preparar a captura de evidência do rollout quando o ambiente real estiver pronto, sem vazar token, hash, header ou API key.

## Wave 110 — API Key Public Endpoint Production Activation Evidence

Esta abordagem cria o command de evidência sanitizada para ativação produtiva de observabilidade pública de API keys.

### Entregue

- query service `api_key_public_endpoint_production_activation_evidence_queries`;
- comando `api_key_public_endpoint_production_activation_evidence`;
- validação declarativa de ambiente production;
- validação de scrape, dashboard, alert rules e métricas públicas;
- descarte de referência externa suspeita de conter segredo/token/hash/header/API key;
- teste de command e blockers.

### Critério Go/No-Go

- Go:
  - ambiente production informado;
  - rollout review pronto;
  - token redigido;
  - endpoint e payload válidos;
  - scrape ativo;
  - dashboard importado;
  - alert rules carregadas;
  - quatro métricas públicas presentes;
  - rollback ensaiado;
  - referência sanitizada presente.
- No-Go:
  - referência contendo token/segredo/hash/header/API key;
  - ambiente diferente de production;
  - ausência de scrape/dashboard/alertas;
  - ausência de rollback;
  - tentar executar chamada real dentro do command.

### Próxima abordagem recomendada

**API Key Public Endpoint Post-Activation Monitoring Review**

Objetivo:

- revisar acompanhamento pós-ativação: janela inicial, leitura de alertas warning, ruído, thresholds e decisão de expandir endpoints públicos.

## Wave 111 — API Key Public Endpoint Post-Activation Monitoring Review

Esta abordagem revisa a estabilidade pós-ativação da observabilidade pública de API keys.

### Entregue

- query service `api_key_public_endpoint_post_activation_monitoring_review_queries`;
- comando `api_key_public_endpoint_post_activation_monitoring_review`;
- checklist de janela observada, dashboard, auth failures, rate limit, endpoint enabled e ruído;
- decisão explícita de não expandir endpoints nesta wave;
- bloqueio contra evidência sensível;
- next track para expansão ou follow-up/rollback.

### Critério Go/No-Go

- Go:
  - activation evidence pronta;
  - janela inicial observada;
  - dashboard revisado;
  - auth failure aceitável;
  - rate limit aceitável;
  - endpoint enabled estável;
  - ruído de alertas aceitável;
  - necessidade de tuning registrada;
  - rollback não exigido;
  - expansão deferida;
  - sem dado sensível observado.
- No-Go:
  - alerta ruidoso sem registro;
  - tráfego fora do esperado;
  - endpoint disabled instável;
  - rollback exigido;
  - tentar expandir endpoints nesta review.

### Próxima abordagem recomendada

**API Key Public Endpoint Expansion Review**

Objetivo:

- decidir se o próximo endpoint público deve ser detalhe de produto, disponibilidade/preço ou outra leitura read-only, mantendo métricas e tenant-scope.

## Wave 112 — API Key Public Endpoint Expansion Review

Esta abordagem decide o próximo candidato de endpoint público protegido por API key.

### Entregue

- query service `api_key_public_endpoint_expansion_review_queries`;
- comando `api_key_public_endpoint_expansion_review`;
- candidato recomendado `GET /api/v1/catalog/products/<slug>/`;
- contrato de read-only, tenant-scope, escopo explícito, rate limit, observabilidade e flag;
- bloqueios contra PII, estoque bruto, tenant_id, pedidos, clientes, pagamentos e admin.

### Critério Go/No-Go

- Go:
  - monitoramento pós-ativação pronto;
  - candidato identificado;
  - read-only obrigatório;
  - tenant context obrigatório;
  - escopo explícito obrigatório;
  - rate limit obrigatório;
  - observabilidade obrigatória;
  - payload seguro obrigatório;
  - sem PII/cross-module leak;
  - flag de rollout obrigatória.
- No-Go:
  - implementar endpoint nesta review;
  - abrir pedidos/clientes/pagamentos;
  - criar escopo amplo `read:*`;
  - expor tenant_id, estoque bruto, custo ou margem.

### Próxima abordagem recomendada

**API Key Public Product Detail Endpoint Contract Review**

Objetivo:

- especificar contrato do endpoint público de detalhe de produto por slug, antes de implementar a view/query no módulo `catalog`.

## Wave 113 — API Key Public Product Detail Endpoint Contract Review

Esta abordagem especifica o contrato do próximo endpoint público protegido por API key.

### Entregue

- query service `api_key_public_product_detail_endpoint_contract_review_queries`;
- comando `api_key_public_product_detail_endpoint_contract_review`;
- contrato `GET /api/v1/catalog/products/<slug>/`;
- owner module `catalog`;
- escopo `read:catalog`;
- rate limit endpoint `catalog.products.detail`;
- flag `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`;
- limites explícitos para payload seguro e sem estoque bruto/PII.

### Critério Go/No-Go

- Go:
  - expansion review pronta;
  - owner `catalog` confirmado;
  - lookup por slug obrigatório;
  - tenant scope obrigatório;
  - produto ativo obrigatório;
  - escopo `read:catalog` obrigatório;
  - payload seguro obrigatório;
  - resumo público de variantes obrigatório;
  - rate limit/metrics/flag obrigatórios.
- No-Go:
  - implementar endpoint nesta review;
  - expor estoque bruto, custo, margem, tenant_id ou PII;
  - abrir carrinho/checkout/pedidos/clientes/pagamentos;
  - criar escrita pública ou admin API.

### Próxima abordagem recomendada

**API Key Public Product Detail Endpoint Execution**

Objetivo:

- implementar query/view/rota/testes para detalhe público de produto por slug no módulo `catalog`, reutilizando autenticação, escopo, throttle e métricas de `api_keys`.

## Wave 114 — API Key Public Product Detail Endpoint Execution

Esta abordagem implementa o endpoint público de detalhe de produto protegido por API key.

### Entregue

- query `public_catalog_api_queries.get_product_detail`;
- view `PublicCatalogProductDetailApiView`;
- rota `GET /api/v1/catalog/products/<slug>/`;
- flag `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`;
- settings de rate limit do detalhe;
- endpoint operacional `catalog.products.detail`;
- gauge `hubx_api_key_public_endpoint_enabled` para detalhe;
- testes de payload seguro, tenant-scope, flag, escopo e rate limit.

### Critério Go/No-Go

- Go:
  - produto ativo do tenant atual retornado por slug;
  - outro tenant retorna 404;
  - produto inativo retorna 404;
  - chave sem `read:catalog` retorna 403;
  - flag desligada retorna 404;
  - payload não expõe tenant_id/estoque bruto/reserved stock;
  - rate limit e audit event usam `catalog.products.detail`.
- No-Go:
  - fallback global;
  - expor estoque bruto/custo/margem/PII;
  - abrir escrita pública;
  - tocar carrinho/checkout/pedidos/clientes/pagamentos.

### Próxima abordagem recomendada

**API Key Public Product Detail Endpoint Observability Review**

Objetivo:

- revisar se dashboard/alert rules e métricas existentes já cobrem o novo endpoint ou se precisam de painéis/thresholds específicos por detalhe.

## Wave 115 — API Key Public Product Detail Endpoint Observability Review

Esta abordagem revisa se o endpoint público de detalhe de produto já está coberto pela observabilidade existente.

### Entregue

- query service `api_key_public_product_detail_observability_review_queries`;
- comando `api_key_public_product_detail_observability_review`;
- decisão de reaproveitar dashboard existente por filtro `endpoint`;
- decisão de reaproveitar alert rules existentes por label `endpoint`;
- confirmação do endpoint label `catalog.products.detail`;
- confirmação do gauge enabled para detalhe;
- bloqueio contra labels por slug/SKU.

### Critério Go/No-Go

- Go:
  - detalhe executado;
  - métrica success com endpoint label presente;
  - gauge enabled presente;
  - dashboard cobre detail por endpoint filter;
  - alert rules cobrem detail por endpoint label;
  - auth failure/rate limit reutilizados;
  - sem dashboard/alert rules novos;
  - sem labels sensíveis.
- No-Go:
  - criar painel dedicado cedo demais;
  - criar alerta por slug/SKU;
  - expor token/hash/header/API key;
  - alterar thresholds sem baseline.

### Próxima abordagem recomendada

**API Key Public Endpoint Expansion Closure Review**

Objetivo:

- fechar a expansão inicial com lista+detalhe públicos, contratos, métricas e riscos residuais antes de decidir novos endpoints.

## Wave 116 — API Key Public Endpoint Expansion Closure Review

Esta abordagem fecha a expansão inicial de endpoints públicos protegidos por API key.

### Entregue

- query service `api_key_public_endpoint_expansion_closure_queries`;
- comando `api_key_public_endpoint_expansion_closure`;
- confirmação de listagem pública;
- confirmação de detalhe público por slug;
- confirmação de métricas/dashboard/alert rules por endpoint;
- escopo fechado com `read:catalog`;
- riscos residuais e próximos tracks.

### Critério Go/No-Go

- Go:
  - listagem pronta;
  - detalhe pronto;
  - observabilidade pronta;
  - nenhum novo endpoint selecionado;
  - artefatos de query/view/url/métricas presentes.
- No-Go:
  - abrir novo endpoint nesta closure;
  - ignorar observabilidade;
  - expor slug/SKU em labels;
  - misturar billing/quotas;
  - remover tenant-scope/scope/rate limit.

### Próxima abordagem recomendada

**API Key Governance Closure Review**

Objetivo:

- fechar a trilha de governança/API pública do ciclo atual e decidir se seguimos para quotas/billing, novos endpoints ou outra frente de ROI.

## Wave 117 — API Key Governance Closure Review

Esta abordagem fecha a trilha de governança de API keys para o ciclo atual.

### Entregue

- query service `api_key_governance_closure_queries`;
- comando `api_key_governance_closure`;
- verificação de modelo e command service;
- verificação de runtime auth e DRF adapter;
- verificação de throttle e permission;
- verificação de endpoints públicos list/detail;
- verificação de métricas/dashboard/alert rules;
- escopo fechado e riscos residuais.

### Critério Go/No-Go

- Go:
  - modelo pronto;
  - runtime auth pronto;
  - DRF adapter pronto;
  - endpoints públicos prontos;
  - observabilidade pronta;
  - expansão fechada;
  - billing/quotas diferidos explicitamente;
  - sem exposição de secret/hash/header/API key.
- No-Go:
  - abrir endpoint novo nesta closure;
  - misturar billing/quotas;
  - ignorar observabilidade;
  - expor material sensível;
  - remover tenant-scope, escopo ou rate limit.

### Próxima abordagem recomendada

**System ROI Re-Selection Review**

Objetivo:

- escolher a próxima frente de maior retorno: quotas/billing de API keys, novos endpoints públicos, partner docs, ou outra área do produto.

## Wave 118 — System ROI Re-Selection Review

Esta abordagem reabre a seleção de ROI depois do fechamento da governança de API keys.

### Entregue

- query service `api_key_system_roi_reselection_queries`;
- comando `api_key_system_roi_reselection`;
- candidatos comparáveis para docs de parceiro, quotas comerciais, novos endpoints, UX admin e hardening por incidente;
- bloqueio quando a closure de governança ainda não está pronta;
- bloqueio quando nenhum candidato cruza threshold mínimo;
- recomendação auditável de próxima trilha.

### Decisão recomendada

**API Key Partner Onboarding Documentation Review**

Motivo:

- listagem e detalhe públicos já estão implementados e observáveis;
- documentação/onboarding destrava consumo real por parceiros com baixo risco;
- abrir novos endpoints agora aumentaria superfície antes de provar uso;
- quotas comerciais continuam prematuras sem pressão explícita de billing/plano/abuso;
- UX admin é útil, mas não bloqueia o primeiro consumo externo do contrato.

### Candidatos diferidos

- API Key Commercial Quotas Review;
- API Key Public Endpoint Expansion Review;
- API Key Admin Management UX Review;
- API Key Production Incident Hardening Review.

### Próxima abordagem recomendada

**API Key Partner Onboarding Documentation Review**

Objetivo:

- criar contrato de documentação/onboarding para parceiros usando os endpoints públicos existentes, com payloads versionados, exemplos seguros e checklist de ativação sem expor material sensível.

## Wave 119 — API Key Partner Onboarding Documentation Review

Esta abordagem productiza a API pública de catálogo para consumo por parceiros sem abrir nova superfície técnica.

### Entregue

- query service `api_key_partner_onboarding_documentation_review_queries`;
- comando `api_key_partner_onboarding_documentation_review`;
- guia versionado `docs/api/public-catalog-partner-onboarding.md`;
- exemplos de listagem e detalhe de produto com placeholder seguro;
- checklist de ativação por tenant/parceiro;
- contrato de erro para `401`, `403`, `404` e `429`;
- notas de rate limit e observabilidade;
- bloqueio explícito contra novo endpoint, billing/quotas ou material sensível.

### Critério Go/No-Go

- Go:
  - closure de governança pronta;
  - ROI recomenda onboarding de parceiros;
  - guia versionado existe;
  - exemplos de list/detail estão documentados;
  - checklist, erros, rate limit e observabilidade estão cobertos;
  - exemplos usam placeholder, sem credencial real.
- No-Go:
  - tentar abrir novo endpoint;
  - introduzir billing, quota ou plano;
  - expor segredo, hash, token ou credencial real;
  - documentar endpoint sem tenant-scope ou sem `read:catalog`.

### Próxima abordagem recomendada

**API Key Partner Documentation Execution Review**

Objetivo:

- preparar o pacote final publicável/operacional de documentação para parceiros, validando canal de entrega, versão, checklist de ativação e handoff para suporte/operação.

## Wave 120 — API Key Partner Documentation Execution Review

Esta abordagem transforma o guia de onboarding em pacote operacional/publicável, ainda sem publicar credenciais ou executar smoke real.

### Entregue

- query service `api_key_partner_documentation_execution_review_queries`;
- comando `api_key_partner_documentation_execution_review`;
- seção `Delivery package` no guia de onboarding;
- canal de entrega aprovado;
- owner de documentação;
- handoff de suporte;
- template de evidência de smoke;
- controle de mudança;
- confirmação explícita de ausência de runtime change, termos comerciais e material sensível.

### Critério Go/No-Go

- Go:
  - onboarding documentation review pronto;
  - canal de entrega documentado;
  - suporte/handoff documentado;
  - template de smoke pronto;
  - change control documentado;
  - owner aprova o pacote;
  - não há runtime change, termos comerciais ou material sensível.
- No-Go:
  - publicar ou enviar credencial;
  - executar smoke real nesta review;
  - alterar feature flag, autenticação, endpoint ou query;
  - definir preço, quota, SLA ou billing.

### Próxima abordagem recomendada

**API Key Partner Documentation Publication Evidence Review**

Objetivo:

- capturar evidência sanitizada de publicação/entrega da documentação pelo canal aprovado, sem expor credencial nem executar mudança de runtime.

## Wave 121 — API Key Partner Documentation Publication Evidence Review

Esta abordagem captura evidência sanitizada de publicação/entrega da documentação de parceiros.

### Entregue

- query service `api_key_partner_documentation_publication_evidence_queries`;
- comando `api_key_partner_documentation_publication_evidence`;
- seção `Publication evidence` no guia de onboarding;
- campos sanitizados de versão, canal, audiência, tenant reference, timestamp e evidência;
- decisões para publicação, operações, redaction e runtime unchanged;
- bloqueios para ausência de evidência, redaction, no-credential e no-runtime-activation.

### Critério Go/No-Go

- Go:
  - execution review pronto;
  - versão/canal/audiência/tenant/timestamp/referência registrados;
  - publicação confirmada;
  - suporte notificado;
  - status de ativação registrado;
  - template de smoke anexado;
  - redaction confirmada;
  - nenhuma credencial compartilhada;
  - nenhuma ativação runtime executada.
- No-Go:
  - incluir API key, segredo, token, hash, header ou screenshot sensível;
  - executar smoke real nesta review;
  - alterar feature flag, runtime, endpoint ou autenticação;
  - avançar sem evidência de canal aprovado.

### Próxima abordagem recomendada

**API Key Partner Onboarding Closure Review**

Objetivo:

- fechar a trilha de onboarding/documentação de parceiros e decidir se o próximo ROI volta para quotas comerciais, novos endpoints públicos, ativação real por parceiro ou outra frente de sistema.

## Wave 122 — API Key Partner Onboarding Closure Review

Esta abordagem fecha a trilha de onboarding/documentação de parceiros para API key pública.

### Entregue

- query service `api_key_partner_onboarding_closure_queries`;
- comando `api_key_partner_onboarding_closure`;
- consolidação de documentação, execution review e publication evidence;
- escopo fechado;
- riscos residuais;
- deferral explícito de ativação real por parceiro;
- deferral explícito de quotas comerciais;
- deferral explícito de novos endpoints públicos.

### Critério Go/No-Go

- Go:
  - publication evidence pronta;
  - escopo de onboarding fechado;
  - riscos residuais aceitos;
  - próxima decisão ROI registrada;
  - ativação real por parceiro diferida;
  - quotas comerciais diferidas;
  - expansão de endpoint diferida.
- No-Go:
  - executar smoke real;
  - ativar parceiro ou feature flag;
  - abrir endpoint público;
  - criar billing/quotas comerciais;
  - reabrir documentação com credencial ou material sensível.

### Próxima abordagem recomendada

**System ROI Re-Selection Review**

Objetivo:

- comparar o próximo maior ROI entre quotas comerciais de API key, ativação real por parceiro, expansão de endpoint público ou outra frente de produto/operação.

## Wave 123 — System ROI Re-Selection Review

Esta abordagem reabre a seleção de ROI após a closure de onboarding/documentação de parceiros.

### Entregue

- query service `api_key_post_onboarding_roi_reselection_queries`;
- comando `api_key_post_onboarding_roi_reselection`;
- candidatos comparáveis para ativação smoke por parceiro, quotas comerciais, expansão de endpoints, UX admin e pausa da trilha de API keys;
- bloqueio quando closure de onboarding ainda não está pronta;
- bloqueio quando nenhum candidato cruza threshold mínimo;
- recomendação auditável da próxima trilha.

### Decisão recomendada

**API Key Partner Activation Smoke Review**

Motivo:

- documentação, pacote e evidência já estão fechados;
- o próximo maior ROI é validar uma ativação real controlada com parceiro/API key pronta;
- smoke controlado prova list/detail sem criar endpoint novo;
- quotas comerciais ficam atrás enquanto não houver pressão explícita de plano, abuso ou billing;
- expansão de endpoint público deve esperar demanda concreta após uso real.

### Próxima abordagem recomendada

**API Key Partner Activation Smoke Review**

Objetivo:

- definir o menor smoke operacional real para parceiro, com evidência sanitizada, sem credencial em claro, sem mudar runtime e sem abrir nova superfície pública.

## Wave 125 — API Key Partner Activation Smoke Contract Review

Esta abordagem inicia a Battery A com o contrato do primeiro smoke controlado de ativação de parceiro.

### Entregue

- query service `api_key_partner_activation_smoke_contract_queries`;
- comando `api_key_partner_activation_smoke_contract`;
- seção `Activation smoke contract` no guia de onboarding;
- contrato com referência sanitizada de parceiro, tenant, ambiente, slug e evidência;
- escopo limitado a listagem e detalhe públicos;
- decisões para scope, operations, redaction e boundaries;
- bloqueios contra endpoint novo, termo comercial, runtime change e material de credencial.

### Critério Go/No-Go

- Go:
  - ROI pós-onboarding recomenda smoke;
  - parceiro e API key estão prontos;
  - ambiente alvo e slug de produto estão referenciados;
  - list/detail estão no escopo;
  - status esperados, observabilidade e rollback estão documentados;
  - redaction e ausência de credencial estão confirmadas.
- No-Go:
  - executar request nesta review;
  - registrar header/token/API key;
  - abrir endpoint novo;
  - criar billing/quotas;
  - mudar runtime ou feature flag.

### Próxima abordagem recomendada

**API Key Partner Activation Smoke Execution**

Objetivo:

- executar o smoke controlado usando o contrato aprovado, capturando apenas evidência sanitizada de list/detail.

## Wave 126 — API Key Commercial Quotas Contract Review

Esta abordagem abre a Battery B por decisão operacional explícita, deixando as ondas restantes da Battery A diferidas.

### Entregue

- query service `api_key_commercial_quotas_contract_queries`;
- comando `api_key_commercial_quotas_contract`;
- contrato mínimo de quota por `tenant_id`, `api_key_id`, `endpoint` e `window`;
- limite diário padrão de contrato;
- comportamento de excesso `429`;
- requisito de visibilidade admin read-only;
- requisito de métricas/audit;
- boundaries contra billing, plano, enforcement runtime e endpoint novo.

### Critério Go/No-Go

- Go:
  - onboarding closure pronto;
  - Battery B selecionada explicitamente;
  - ondas restantes da Battery A diferidas;
  - pressão comercial de quota confirmada;
  - dimensões, janela, limite e excesso documentados;
  - erro, observabilidade e admin visibility documentados;
  - billing/plano/runtime enforcement fora da wave.
- No-Go:
  - criar cobrança real;
  - acoplar plano/subscription;
  - alterar throttle runtime nesta wave;
  - abrir endpoint novo;
  - registrar material sensível.

### Próxima abordagem recomendada

**API Key Quota Model Minimal Execution**

Objetivo:

- criar o modelo mínimo de quota tenant/key/endpoint/window, ainda sem enforcement runtime nem billing.

## Wave 127 — API Key Partner Activation Smoke Execution

Esta abordagem executa a segunda onda da Battery A como gate operacional, sem armazenar credenciais.

### Entregue

- query service `api_key_partner_activation_smoke_execution_queries`;
- comando `api_key_partner_activation_smoke_execution`;
- checks para listagem, detalhe, caminho negativo de auth, observabilidade e rollback;
- sanitização de referências contra header, bearer, API key, hash e segredo.

### Próxima abordagem recomendada

**API Key Partner Activation Evidence Capture**

## Wave 128 — API Key Partner Activation Evidence Capture

Esta abordagem captura a evidência sanitizada do smoke executado.

### Entregue

- query service `api_key_partner_activation_evidence_capture_queries`;
- comando `api_key_partner_activation_evidence_capture`;
- contrato de anexos para list/detail, auth negativa, métricas, audit log, handoff e rollback;
- bloqueio explícito contra material sensível em evidência.

### Próxima abordagem recomendada

**API Key Partner Activation Post-Smoke Monitoring**

## Wave 129 — API Key Partner Activation Post-Smoke Monitoring

Esta abordagem monitora a janela inicial após o smoke do parceiro.

### Entregue

- query service `api_key_partner_activation_post_smoke_monitoring_queries`;
- comando `api_key_partner_activation_post_smoke_monitoring`;
- checks de estabilidade, auth failure, rate limit, erro de endpoint, ticket de suporte e rollback;
- registro de pressão comercial por quota sem implementar quota nesta bateria.

### Próxima abordagem recomendada

**API Key Partner Activation Closure Review**

## Wave 130 — API Key Partner Activation Closure Review

Esta abordagem fecha a Battery A e direciona a próxima execução para quotas comerciais.

### Entregue

- query service `api_key_partner_activation_closure_queries`;
- comando `api_key_partner_activation_closure`;
- closure scope para contrato, execução, evidência, monitoramento, handoffs e seleção do próximo ROI;
- testes cobrindo ready, blockers, comandos e ausência de material sensível.

### Próxima abordagem recomendada

**API Key Quota Model Minimal Execution**

Objetivo:

- seguir a Battery B já aberta, implementando o modelo mínimo de quotas comerciais tenant-scoped.

## Wave 131 — API Key Quota Model Minimal Execution

Esta abordagem cria o modelo mínimo de quotas comerciais por tenant/API key/endpoint/janela.

### Entregue

- modelos `ApiKeyQuota` e `ApiKeyQuotaUsage`;
- migration `0002_api_key_quotas`;
- admin Django read-only operacional para quotas/usages;
- command service `api_key_quota_commands.upsert_quota`;
- comando `api_key_quota_upsert`;
- audit `api_key.quota_upserted` sem segredo/hash/API key em claro.

## Wave 132 — API Key Quota Enforcement Runtime Review

Esta abordagem define o enforcement runtime sem acoplar billing ou plano.

### Decisão

- quota comercial roda após rate limit técnico existente.
- ausência de quota ativa mantém comportamento atual.
- excesso de quota usa `429` e `Retry-After`.
- billing/subscription continuam fora do recorte.

## Wave 133 — API Key Quota Enforcement Execution

Esta abordagem conecta o enforcement runtime no throttle de API keys públicas.

### Entregue

- service `api_key_quota_enforcement`;
- integração em `ApiKeyRateLimitThrottle`;
- usage window tenant-scoped;
- audit `api_key.quota_exceeded`;
- métrica `hubx_api_key_quota_exceeded_total`;
- tests de bloqueio `429` no endpoint público.

## Wave 134 — API Key Quota Admin Visibility Review

Esta abordagem define superfície admin mínima read-only.

### Decisão

- `/ops/api-keys/quotas/` exibe apenas prefixo, nome, endpoint, escopo, status, uso, limite e janela.
- a tela não cria quota, billing, plano ou segredo.
- permissionamento usa `api_keys.view`.

## Wave 135 — API Key Quota Admin Visibility Execution

Esta abordagem implementa a superfície admin tenant-scoped.

### Entregue

- query service `api_key_quota_queries`;
- URL ops `api_keys_ops:admin-api-key-quotas-list`;
- view `AdminApiKeyQuotaListView`;
- template `admin_api_key_quotas_page.html`;
- navegação no cockpit `/ops/`;
- tests de visibilidade tenant-scoped e ausência de segredo.

## Wave 136 — API Key Commercial Quotas Closure Review

Esta abordagem fecha a Battery B.

### Entregue

- query service `api_key_commercial_quotas_closure_queries`;
- comando `api_key_commercial_quotas_closure`;
- closure cobrindo contrato, modelo, enforcement, admin visibility, métricas e audit;
- boundaries confirmados contra cobrança real, plano/subscription e material sensível.

### Próxima abordagem recomendada

**System ROI Re-Selection Review**

Objetivo:

- reavaliar se o próximo maior ROI está em pagamentos produtivos, shipping real, runbooks cross-module ou outra frente.

## Wave 137 — System ROI Post-Quota Re-Selection Review

Esta abordagem fecha a re-seleção após Battery A/B da trilha de API pública.

### Entregue

- query service `system_roi_post_quota_reselection_queries`;
- comando `system_roi_post_quota_reselection`;
- candidatos comparáveis:
  - `Payments Production Readiness Review`;
  - `Shipping Real Quote & SLA Activation Review`;
  - `Cross-Module Production Runbook Closure Review`;
  - `Storefront Conversion Experimentation Review`;
- blocker se Battery B não estiver fechada;
- blocker se nenhum candidato passar o threshold de ROI;
- output sem segredo, header, hash ou API key.

### Decisão recomendada

**Payments Production Readiness Review**

Motivo:

- pagamentos concentram o risco direto de receita real;
- provider produtivo, refund e conciliação financeira têm impacto maior que refinamento adicional de API pública;
- shipping real e closure/runbooks seguem como candidatos se pagamentos não forem blocker.

### Próxima abordagem recomendada

**Payments Production Readiness Review**

Objetivo:

- revisar provider, refund, conciliação, evidências e rollback para decidir o menor caminho seguro de ativação produtiva de pagamentos.

## Wave 138 — Battery C Payments Production Readiness Closure

Esta abordagem conclui a Battery C com gates executáveis para produção controlada de pagamentos.

### Entregue

- query service `payments.application.production_readiness_queries`;
- comando `payments_production_readiness`;
- reviews para:
  - provider production gate;
  - provider activation evidence;
  - webhook production smoke;
  - refund production gate;
  - refund production smoke evidence;
  - financial reconciliation production;
  - payments production closure;
- closure scope com provider, webhook, refund, reconciliação, rollback, runbook e monitoramento;
- testes cobrindo ready, blockers, comando e ausência de material sensível.

### Decisão

- **Battery C concluída** para readiness de produção controlada.
- rollout amplo continua fora.
- refund self-service, refund em lote e correção financeira automática continuam fora.
- próximo foco automático é **Battery D — Shipping Quote Productionization**.

## Wave 139 — Battery D Shipping Quote Productionization Closure

Esta abordagem conclui a Battery D com quote mínimo aplicável ao checkout.

### Entregue

- query service `shipping_quote_queries`;
- adapter skeleton/manual para quote;
- command service `checkout_shipping_quote_commands`;
- closure service `shipping_quote_productionization_queries`;
- comando `shipping_quote_productionization`;
- testes para quote ready, falha honesta, aplicação no checkout e closure.

### Decisão

- **Battery D concluída** para quote produtizável mínimo.
- o checkout pode atualizar `shipping_methods` e `shipping_total` a partir de quote tenant-scoped.
- falha de quote limpa seleção de entrega em vez de mascarar contexto.
- chamada real de transportadora, token externo e cálculo por peso/dimensão ficam fora.

### Próxima bateria recomendada

**Battery E — Subscriptions & Tenant Billing Foundation**

## Wave 140 — Battery E Subscriptions & Tenant Billing Foundation Closure

Esta abordagem conclui a Battery E tirando `subscriptions` do estado skeleton.

### Entregue

- modelos `SubscriptionPlan` e `TenantSubscription`;
- migration inicial de subscriptions;
- command service `subscription_commands`;
- query service `subscription_queries`;
- admin read-only `/ops/subscriptions/`;
- closure service `subscriptions_foundation_queries`;
- comando `subscriptions_foundation`;
- testes de modelo, tenant scope, admin surface e closure.

### Decisão

- **Battery E concluída** como fundação de plano/assinatura SaaS.
- billing provider real segue fora.
- pagamentos de loja continuam separados de subscription SaaS.
- enforcement de plano fica documentado como boundary futura.

### Próxima bateria recomendada

**Battery F — Audit Instrumentation Expansion**

## Wave 141 — Battery F Audit Instrumentation Expansion Closure

Esta abordagem conclui a Battery F ampliando auditoria apenas para ações críticas selecionadas.

### Entregue

- eventos `payments.refund.approved` e `payments.refund.execution_recorded`;
- command `catalog.application.admin_product_commands.update_product_visibility(...)` com `catalog.product.visibility_updated`;
- confirmação de cobertura API key para criação, revogação, quota e quota excedida;
- query service `audit_instrumentation_expansion_queries`;
- comando `audit_instrumentation_expansion`;
- testes para tenant scope, redaction e closure.

### Decisão

- **Battery F concluída** sem middleware global, diff genérico de model ou log de leitura.
- metadata sensível fica redigida: sem segredo/hash de API key, sem `payload_snapshot` provider e sem `external_reference`.
- `audit` permanece dono do registro, enquanto cada módulo decide ações de domínio auditáveis.

### Próxima bateria recomendada

**Battery G — Notifications Production Delivery**

## Wave 142 — Battery G Notifications Production Delivery Closure

Esta abordagem conclui a Battery G validando produção transacional de notifications sem abrir campanhas.

### Entregue

- query services de provider gate, delivery evidence, failure handling, monitoring e closure;
- command service `notification_production_delivery_commands.execute_transactional_smoke(...)`;
- comando `notification_production_delivery`;
- classificação operacional de bounce/falhas;
- smoke real usando `EmailLog` e provider readiness;
- testes para provider gate, smoke, redaction, failure classification e closure.

### Decisão

- **Battery G concluída** para delivery transacional produtivo controlado.
- evidências não imprimem e-mail de customer em claro.
- falha/bounce é classificação operacional e não altera domínio de pedidos/clientes.
- lifecycle/campanhas seguem para bateria própria.

### Próxima bateria recomendada

**Battery H — Customer Retention Lifecycle**

## Wave 143 — Battery H Customer Retention Lifecycle Closure

Esta abordagem conclui a Battery H com lifecycle mínimo pós-compra consentido.

### Entregue

- segment query `newsletter_segment_queries.list_subscribed_segment(...)`;
- intent `customer.post_purchase.follow_up`;
- command `customer_retention_lifecycle_commands.plan_post_purchase_follow_up(...)`;
- comando `customer_retention_lifecycle`;
- closure query `customer_retention_lifecycle_closure_queries`;
- testes de segmento, opt-out, idempotência, cross-tenant e closure.

### Decisão

- **Battery H concluída** sem campanha recorrente, scoring ou cadência automática.
- newsletter continua dono de consentimento.
- notifications cria apenas `EmailLog` planejado para pós-compra elegível.
- opt-out bloqueia criação de log.

### Próxima bateria recomendada

**Battery I — Storefront Data-Driven Conversion**

## Wave 144 — Battery I Storefront Data-Driven Conversion Closure

Esta abordagem conclui a Battery I usando analytics existentes para priorização leve do storefront.

### Entregue

- query service `storefront_conversion_insights`;
- baseline de discovery/PDP/CTA;
- funil PDP CTA por produto;
- revisão de drop-off de busca/facet sem resultado;
- experimento `product_card_priority_v1` aplicado em `storefront_catalog_queries.list_products(...)`;
- comando `storefront_conversion`;
- closure query `storefront_conversion_closure_queries`;
- testes de baseline, funil, drop-off, ranking e closure.

### Decisão

- **Battery I concluída** sem redesenhar storefront inteiro.
- ranking de cards pode receber delta por sinais recentes tenant-scoped.
- o experimento não altera preço, estoque, disponibilidade, checkout ou pedido.
- sinais de indisponibilidade reduzem prioridade em vez de mascarar conflito.

### Próxima bateria recomendada

**Battery J — System Production Closure**

## Wave 145 — Battery J System Production Closure

Esta abordagem conclui a sequência A–J com uma decisão objetiva de produção real.

### Entregue

- query service `system_production_closure_queries`;
- matriz cross-module de readiness;
- reviews de runbooks, smoke, observabilidade e rollback;
- comando `system_production_closure`;
- decisão Go/No-Go;
- testes focados para matrix, blockers, smoke, Go/No-Go e comando.

### Decisão

- **Battery J concluída** como closure sistêmica declarativa.
- `GO` exige evidência operacional externa e aceite de riscos residuais.
- `NO-GO` abre bateria corretiva mínima pelo maior blocker.
- o comando não altera runtime, providers, flags/env, tenants ou dados de commerce.

### Próxima trilha se GO

**Growth/Commercial Activation Track**

### Próxima trilha se NO-GO

**Production Corrective Battery**

## Wave 124 — System Execution Wave Batteries Review

Esta abordagem pausa a execução linear de waves e consolida o planejamento em baterias autocontidas.

### Entregue

- novo documento `docs/system-execution-wave-batteries.md`;
- inventário resumido do que já está desenvolvido;
- lacunas restantes por área;
- baterias A–J para execução sequencial;
- regra de passagem automática entre baterias;
- próxima bateria recomendada.

### Decisão recomendada

**Battery A — API Key Partner Activation**

Primeira onda:

**API Key Partner Activation Smoke Contract Review**

Motivo:

- API pública já possui governança, endpoints, observabilidade, documentação, pacote, evidência e closure;
- ainda falta validar ativação real controlada;
- smoke por parceiro tem menor superfície que quotas comerciais ou novos endpoints.
