# Reviews

## Responsabilidade
Gerenciar avaliações de produto.

## Entidades principais
- ProductReview

## Casos de uso
- criar review
- aprovar review
- rejeitar review

## Regras de negócio
- review exige aprovação

## Trust & Social Proof Wave 1 — Product Review Domain Contract Review

### Contexto

`reviews` ainda é um módulo skeleton.

Depois da evolução de PDP, cart, coupons, checkout e payments, a próxima lacuna de conversão não é mais “como comprar”, mas “por que confiar”.

### Objetivo do módulo

`reviews` deve fornecer prova social moderada para produtos, sem interferir em checkout, pagamentos, estoque ou pedido.

### Contrato mínimo recomendado

`ProductReview`:

- `tenant`
- `product`
- `customer` opcional
- `rating`
- `title`
- `body`
- `author_name`
- `status`
- `moderated_at`
- `created_at`
- `updated_at`

Status:

- `pending`
- `approved`
- `rejected`

### Regras

- toda review nasce como `pending`.
- somente reviews `approved` aparecem no storefront/PDP.
- rating deve ficar entre 1 e 5.
- review pertence a um tenant e nunca deve cruzar produtos/tenants.
- vínculo com `Order` fica fora do primeiro recorte.
- customer autenticado pode ser associado quando existir, mas não é obrigatório para o MVP.

### Boundaries

- `catalog` pode consumir aggregate rating por application query de `reviews`.
- `reviews` pode referenciar `catalog.Product`, mas não deve alterar produto.
- `reviews` não deve chamar checkout, orders, payments, shipping ou notifications nesta fase.
- moderação pertence a uma surface admin/ops própria ou integrada ao cockpit.

### Fora do escopo inicial

- verified purchase obrigatório.
- resposta do lojista.
- votos úteis.
- fotos/vídeos.
- denúncia/report.
- eventos e notificações.
- analytics avançado de conversão.

### Próxima wave recomendada

**Trust & Social Proof Wave 2 — Product Review Model & Query Skeleton**

Criar modelo tenant-scoped, migration, query de agregados aprovada-only e testes de isolamento por tenant.

## Trust & Social Proof Wave 2 — Product Review Model & Query Skeleton

### Escopo executado

- criado modelo `ProductReview`.
- criada migration inicial do módulo `reviews`.
- criado service de leitura `reviews.application.review_summary_queries`.
- registrado modelo no Django admin técnico.
- adicionados testes de:
  - status padrão `pending`;
  - agregados apenas com reviews `approved`;
  - isolamento por tenant;
  - listagem approved-only;
  - retorno vazio sem tenant/produto.

### Modelo

`ProductReview` guarda:

- `tenant`
- `product`
- `customer` opcional
- `rating`
- `title`
- `body`
- `author_name`
- `status`
- `moderated_at`
- `created_at`
- `updated_at`

### Query pública inicial

`product_review_summary_queries.get_product_review_summary(...)` retorna:

- `review_count`
- `rating_average`
- `status`

`product_review_summary_queries.list_approved_product_reviews(...)` retorna somente reviews aprovadas, limitadas e tenant-scoped.

### Guardrails

- storefront/PDP deve consumir apenas reviews aprovadas.
- `catalog` deve consumir `reviews` por application query, não pelo ORM interno.
- `reviews` não altera `Product`.
- `reviews` não toca checkout, orders, payments, shipping ou notifications.

### Próxima wave recomendada

**Trust & Social Proof Wave 3 — Product Review Admin Moderation Review**

Definir a menor surface admin/ops para aprovar/rejeitar reviews antes de qualquer exibição em PDP.

## Trust & Social Proof Wave 3 — Product Review Admin Moderation Review

### Estado atual

`reviews` agora possui:

- `ProductReview` tenant-scoped.
- status `pending`, `approved`, `rejected`.
- query approved-only para resumo e listagem.
- admin técnico Django.

Ainda falta uma surface operacional para o lojista moderar reviews sem acessar Django admin técnico.

### Surface recomendada

Criar `/ops/reviews/` como primeira surface admin/ops.

Listagem:

- filtro por status;
- filtro por busca em produto, título, corpo ou autor;
- colunas:
  - Produto
  - Rating
  - Autor
  - Título
  - Status
  - Criado em
  - Ação

### Commands recomendados

`reviews.application.admin_review_queries`

- `list_reviews(tenant_id, status="", search="")`
- retorna somente reviews do tenant.
- inclui dados mínimos de produto e review.
- não retorna reviews cross-tenant.

`reviews.application.admin_review_commands`

- `moderate_review(tenant_id, review_id, action, moderated_by="")`
- actions permitidas:
  - `approve`
  - `reject`
- transições:
  - qualquer status → `approved` para `approve`
  - qualquer status → `rejected` para `reject`
- grava `moderated_at`.
- mantém `rating`, `body`, `product` e `customer` imutáveis.

### Rotas recomendadas

- `GET /ops/reviews/`
- `POST /ops/reviews/<review_id>/moderate/`

### Guardrails

- view deve ser fina e delegar para application commands.
- `tenant_id` sempre vem da request.
- POST cross-tenant deve retornar unavailable/404 lógico e não alterar nada.
- review pendente/rejeitada nunca deve aparecer em storefront/PDP.
- moderação não deve alterar `Product`.
- moderação não deve emitir evento/notificação nesta wave.
- moderação não deve tocar checkout, orders, payments ou shipping.

### UX

- review `pending` mostra ações “Aprovar” e “Rejeitar”.
- review `approved` pode mostrar “Rejeitar”.
- review `rejected` pode mostrar “Aprovar”.
- empty state sem tenant: “Tenant não resolvido”.
- empty state com tenant sem reviews: “Nenhuma avaliação para moderar”.

### Fora do escopo

- edição de texto pelo lojista.
- resposta do lojista.
- denúncia/report.
- verified purchase.
- eventos e notificações.
- integração com PDP pública.

### Decisão

**Go para implementar surface admin/ops mínima de moderação.**

**No-Go para exibir reviews na PDP antes da moderação admin estar disponível.**

### Próxima wave recomendada

**Trust & Social Proof Wave 4 — Product Review Admin Moderation Execution**

Criar query/command services, rotas `/ops/reviews/`, templates mínimos e testes de listagem/moderação tenant-scoped.

## Trust & Social Proof Wave 4 — Product Review Admin Moderation Execution

### Escopo executado

- criado `reviews.application.admin_review_queries`.
- criado `reviews.application.admin_review_commands`.
- criada rota `/ops/reviews/`.
- criada rota `POST /ops/reviews/<review_id>/moderate/`.
- criado template `admin_reviews_list_page.html`.
- adicionado link `Avaliações` no cockpit `/ops/`.
- adicionados testes de listagem, filtro, tenant-scope e moderação.

### Comportamento

- listagem resolve tenant pela request.
- filtro por status usa `pending`, `approved` e `rejected`.
- busca cobre produto, autor, título e corpo.
- ações permitidas:
  - `approve`
  - `reject`
- moderação altera somente:
  - `status`
  - `moderated_at`
  - `updated_at`

### Guardrails implementados

- POST cross-tenant não altera review.
- view delega mutação para application command.
- conteúdo, rating, produto e customer permanecem imutáveis durante moderação.
- nenhum evento ou notification é emitido.
- checkout, orders, payments e shipping continuam fora do fluxo.

### Próxima wave recomendada

**Trust & Social Proof Wave 5 — Product Review PDP Visibility Review**

Decidir como integrar aggregate rating e reviews aprovadas à PDP sem expor pendentes/rejeitadas e sem acoplar `catalog` ao ORM interno de `reviews`.

## Trust & Social Proof Wave 5 — Product Review PDP Visibility Review

### Estado atual da PDP

A PDP é renderizada por `catalog.interfaces.views.ProductDetailView`.

Hoje ela:

- resolve tenant pela request storefront;
- busca produto via `catalog.application.storefront_catalog_queries`;
- renderiza `product_detail_page.html`;
- já possui decisão comercial, estoque, variantes, galeria e CTA cart/checkout.

### Decisão de boundary

Reviews devem entrar como enriquecimento da view da PDP, não como regra interna de `catalog`.

Fluxo recomendado:

1. `ProductDetailView` resolve `tenant_id` e produto.
2. A view chama `reviews.application.review_summary_queries`.
3. A view injeta no contexto:
   - `review_summary`
   - `approved_reviews`
4. Template renderiza bloco de prova social somente com dados approved-only.

### Dados mínimos para PDP

`review_summary`:

- `review_count`
- `rating_average`
- `status`

`approved_reviews`:

- `rating`
- `title`
- `body`
- `author_name`
- `created_at`

### UX recomendada

Quando houver reviews aprovadas:

- exibir resumo próximo ao título ou abaixo da faixa de decisão;
- mostrar rating médio e quantidade;
- listar até 3 reviews aprovadas;
- usar copy conservadora:
  - “Avaliações de clientes”
  - “Média X/5 baseada em N avaliação(ões)”

Quando não houver reviews aprovadas:

- não mostrar fallback fake;
- opcionalmente mostrar bloco discreto:
  - “Ainda sem avaliações públicas”
- não bloquear compra nem alterar CTA.

### Guardrails

- nunca exibir `pending` ou `rejected`.
- não acessar ORM de `reviews` diretamente em `catalog`.
- não alterar `Product`.
- não criar evento/notificação.
- não exigir purchase verified nesta wave.
- não criar formulário público de review ainda.
- não mudar checkout, cart, payments ou orders.

### Testes recomendados

- PDP mostra resumo quando existem reviews aprovadas.
- PDP não mostra reviews pendentes/rejeitadas.
- PDP não mostra reviews de outro tenant.
- PDP continua renderizando sem reviews aprovadas.

### Decisão

**Go para integrar reviews approved-only à PDP via application query de `reviews`.**

**No-Go para formulário público de criação de reviews nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 6 — Product Review PDP Visibility Execution**

Integrar `ProductDetailView` com `product_review_summary_queries`, atualizar template da PDP e adicionar testes de visibilidade approved-only/tenant-scoped.

## Trust & Social Proof Wave 6 — Product Review PDP Visibility Execution

### Escopo executado

- `ProductDetailView` passou a chamar `product_review_summary_queries`.
- o contexto da PDP agora recebe:
  - `review_summary`
  - `approved_reviews`
- `product_detail_page.html` renderiza bloco “Avaliações de clientes” somente quando existem reviews aprovadas.
- `admin_product_queries` passou a expor `id` no payload serializado de produto persistido para permitir lookup do aggregate.
- testes cobrem:
  - review aprovada visível na PDP;
  - review pendente invisível;
  - review de outro tenant invisível;
  - PDP sem reviews aprovadas omite o bloco.

### Guardrails preservados

- `catalog` não lê ORM interno de `reviews`.
- `storefront_catalog_queries` continua sem regra de moderação.
- PDP consome apenas application query de `reviews`.
- checkout, cart, payments, orders, shipping e notifications não foram alterados.
- não há formulário público de criação de review.

### Próxima wave recomendada

**Trust & Social Proof Wave 7 — Product Review Submission Contract Review**

Decidir se o próximo passo deve ser formulário público/customer-facing de envio de review ou se a trilha deve primeiro consolidar seeds/admin creation para operar reviews manualmente.

## Trust & Social Proof Wave 7 — Product Review Submission Contract Review

### Estado atual

`reviews` já possui:

- modelo `ProductReview`;
- moderação `/ops/reviews/`;
- queries approved-only;
- visibilidade approved-only na PDP.

Ainda não existe fluxo público/customer-facing para criar reviews.

### Risco da submissão pública

Abrir formulário público agora exigiria decisões adicionais sobre:

- identidade do comprador;
- vínculo com `Customer`;
- vínculo opcional ou obrigatório com `Order`;
- anti-spam/rate limit;
- consentimento para exibir nome;
- validação de conteúdo sensível;
- política de edição/remoção;
- prevenção de review cross-tenant.

### Decisão recomendada

Não abrir formulário público de review nesta wave.

Primeiro passo seguro:

- criar um command/application service interno para registrar review como `pending`;
- permitir criação controlada por suporte/admin/seed;
- validar tenant, produto, rating e author label;
- manter moderação obrigatória antes da PDP;
- não exigir pedido entregue ainda;
- não enviar notification/evento.

### Command recomendado

`reviews.application.review_submission_commands.submit_product_review(...)`

Entrada:

- `tenant_id`
- `product_id` ou `product_slug`
- `rating`
- `title`
- `body`
- `author_name`
- `customer_id` opcional
- `source`

Comportamento:

- valida tenant e produto no mesmo tenant;
- valida rating entre 1 e 5;
- normaliza textos;
- cria `ProductReview.status=pending`;
- não publica automaticamente;
- não altera `Product`;
- não toca checkout, orders, payments, shipping ou notifications.

Result codes:

- `review-submitted-pending`
- `review-submission-blocked`
- `review-product-not-found`
- `review-submission-unavailable`

### Fora do escopo

- formulário storefront público;
- verified purchase obrigatório;
- vínculo obrigatório com pedido;
- anexos/fotos;
- resposta do lojista;
- eventos/notificações;
- publicação automática.

### Próxima wave recomendada

**Trust & Social Proof Wave 8 — Product Review Submission Command Execution**

Criar command service interno para registrar reviews como `pending`, com testes de tenant-scope, rating inválido e produto cross-tenant.

## Trust & Social Proof Wave 8 — Product Review Submission Command Execution

### Escopo executado

- criado `reviews.application.review_submission_commands`.
- criado command `submit_product_review`.
- reviews submetidas por esse fluxo nascem sempre como `pending`.
- adicionados testes de:
  - criação pending por tenant/produto;
  - rating inválido;
  - produto cross-tenant;
  - customer cross-tenant ignorado;
  - command CLI.

### Contrato implementado

`submit_product_review(...)` aceita:

- `tenant_id`
- `product_id` ou `product_slug`
- `rating`
- `title`
- `body`
- `author_name`
- `customer_id` opcional
- `source`

Result codes:

- `review-submitted-pending`
- `review-submission-blocked`
- `review-product-not-found`
- `review-submission-unavailable`

### CLI operacional

```bash
python manage.py submit_product_review \
  --tenant-id=<id> \
  --product-slug=<slug> \
  --rating=5 \
  --title="Ótimo produto" \
  --author-name="Cliente"
```

### Guardrails

- não publica automaticamente.
- não altera `Product`.
- não toca checkout, orders, payments, shipping ou notifications.
- produto precisa pertencer ao tenant.
- customer cross-tenant não é associado.
- PDP continua exibindo apenas reviews aprovadas.

### Próxima wave recomendada

**Trust & Social Proof Wave 9 — Product Review Submission Admin Entry Review**

Decidir se a criação operacional deve ganhar formulário admin/ops em `/ops/reviews/new/` ou se o command CLI é suficiente até existir submissão pública/customer-facing.

## Trust & Social Proof Wave 9 — Product Review Submission Admin Entry Review

### Estado atual

`reviews` já possui:

- modelo `ProductReview` tenant-scoped;
- moderação operacional em `/ops/reviews/`;
- PDP consumindo apenas reviews aprovadas;
- command interno `submit_product_review(...)`;
- CLI operacional para seeds/suporte controlado.

O CLI é suficiente para operação técnica, mas ainda cria atrito para uso real por suporte ou merchant ops.

### Decisão recomendada

Criar uma entrada admin/ops mínima em `/ops/reviews/new/`.

Essa entrada deve reutilizar `reviews.application.review_submission_commands.submit_product_review(...)` e criar sempre reviews como `pending`.

### Surface proposta

Rota:

- `GET /ops/reviews/new/`
- `POST /ops/reviews/new/`

Campos mínimos:

- produto por `product_slug` ou `product_id`;
- `rating`;
- `title`;
- `body`;
- `author_name`;
- `customer_id` opcional, se existir validação tenant-safe simples;
- `source` fixo como `ops_admin`.

Após submit bem-sucedido:

- redirecionar para `/ops/reviews/`;
- exibir review na fila de moderação;
- não publicar automaticamente na PDP.

### Guardrails

- `tenant_id` deve vir da request resolvida.
- view deve ser fina e delegar criação para application command.
- produto precisa pertencer ao tenant atual.
- customer cross-tenant não deve ser associado.
- rating inválido deve retornar erro honesto.
- criação admin não pode aprovar automaticamente.
- PDP continua approved-only.
- nenhuma notificação ou evento deve ser emitido nesta wave.

### Fora do escopo

- formulário público storefront;
- verified purchase;
- vínculo obrigatório com pedido;
- upload de mídia;
- resposta do lojista;
- auto-approval;
- rate limit/anti-spam público;
- eventos e notificações.

### Decisão

**Go para criar `/ops/reviews/new/` como entrada operacional mínima.**

**No-Go para submissão pública/customer-facing nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 10 — Product Review Admin Entry Execution**

Criar view, rota, template e testes para submissão admin tenant-scoped reutilizando `submit_product_review(...)`.

## Trust & Social Proof Wave 10 — Product Review Admin Entry Execution

### Escopo executado

- criada rota `GET /ops/reviews/new/`.
- criada rota `POST /ops/reviews/new/`.
- criado template `admin_review_form_page.html`.
- adicionada CTA “Nova avaliação” em `/ops/reviews/`.
- criação admin reutiliza `reviews.application.review_submission_commands.submit_product_review(...)`.
- adicionados testes de renderização, criação pending, rating inválido e produto cross-tenant.

### Comportamento

- formulário aceita produto por slug ou ID.
- avaliação criada por admin nasce sempre como `pending`.
- publicação continua dependendo de approve em `/ops/reviews/`.
- erro de produto fora do tenant retorna feedback honesto.
- erro de rating inválido não cria review.

### Guardrails implementados

- `tenant_id` vem da request resolvida.
- view não acessa ORM diretamente para criar review.
- produto precisa pertencer ao tenant atual.
- PDP continua exibindo apenas reviews aprovadas.
- não há submissão pública/customer-facing.
- nenhum evento ou notification é emitido.

### Próxima wave recomendada

**Trust & Social Proof Wave 11 — Review Submission Customer Eligibility Review**

Revisar se o próximo passo deve introduzir elegibilidade por cliente/pedido entregue ou se a trilha deve priorizar prova social agregada e qualidade da PDP antes de abrir submissão pública.

## Trust & Social Proof Wave 11 — Review Submission Customer Eligibility Review

### Estado atual

`reviews` agora possui uma entrada operacional completa:

- criação interna por command;
- criação admin em `/ops/reviews/new/`;
- moderação em `/ops/reviews/`;
- exibição approved-only na PDP.

Ainda não existe submissão pública/customer-facing.

### Pergunta da wave

O próximo passo deveria abrir review para clientes ou primeiro definir elegibilidade por compra?

### Avaliação

Abrir submissão pública sem elegibilidade clara criaria risco de:

- spam ou conteúdo sem relação com compra real;
- reviews sem customer autenticado;
- reviews duplicadas para o mesmo produto;
- review cross-tenant por produto, customer ou pedido;
- exposição de identidade sem consentimento explícito;
- pressão para auto-approval antes de moderação;
- acoplamento prematuro com `orders` e `accounts`.

### Contrato de elegibilidade recomendado

Quando a submissão pública for aberta, ela deve depender de um contrato específico, separado do command admin atual.

Proposta futura:

`reviews.application.review_eligibility_queries.can_customer_review_product(...)`

Entradas:

- `tenant_id`
- `customer_id`
- `product_id`

Critérios mínimos:

- tenant resolvido e explícito;
- customer pertence ao tenant;
- produto pertence ao tenant;
- existe pelo menos um pedido do mesmo tenant/customer contendo o produto;
- pedido está em estado entregue/concluído ou equivalente operacional seguro;
- não existe review anterior do mesmo customer para o mesmo produto, salvo política futura de atualização.

Result codes sugeridos:

- `review-eligible`
- `review-ineligible-no-purchase`
- `review-ineligible-not-delivered`
- `review-ineligible-duplicate`
- `review-ineligible-customer-not-found`
- `review-ineligible-product-not-found`
- `review-ineligible-unavailable`

### Decisão recomendada

Não abrir submissão pública nesta wave.

Antes disso, criar apenas o contrato de elegibilidade como query read-only, sem formulário público e sem mutação.

### Guardrails

- o command admin atual continua sem exigir pedido entregue.
- flows públicos futuros não devem reutilizar diretamente a entrada admin sem eligibility gate.
- `reviews` deve consultar eligibility por application boundary, sem espalhar ORM de `orders`.
- PDP não deve renderizar formulário público até eligibility existir.
- toda submissão pública futura deve continuar nascendo como `pending`.
- moderação continua obrigatória.

### Fora do escopo

- formulário público na PDP;
- criação de review a partir da área do cliente;
- auto-approval para verified purchase;
- edição de review pelo cliente;
- solicitação automática pós-entrega;
- eventos/notificações;
- fotos/vídeos.

### Decisão

**Go para desenhar/implementar um eligibility service read-only antes de qualquer submissão pública.**

**No-Go para formulário público/customer-facing nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 12 — Review Eligibility Service Skeleton Execution**

Criar query service read-only para elegibilidade de review por tenant/customer/product, com testes de tenant-scope, compra ausente, pedido não entregue e duplicidade.

## Trust & Social Proof Wave 12 — Review Eligibility Service Skeleton Execution

### Escopo executado

- criado `reviews.application.review_eligibility_queries`.
- criado service `can_customer_review_product(...)`.
- eligibility é read-only e não cria review.
- compra do produto é inferida por `OrderItem.variant_sku` ligado a `ProductVariant`.
- pedido elegível precisa estar entregue/concluído no recorte operacional atual.
- adicionados testes de:
  - cliente elegível com pedido entregue;
  - ausência de compra;
  - pedido pago mas ainda não entregue;
  - review duplicada;
  - customer cross-tenant;
  - product cross-tenant.

### Contrato implementado

`can_customer_review_product(...)` recebe:

- `tenant_id`
- `customer_id`
- `product_id`

Retorna:

- `result`
- `eligible`
- `order_number`

Result codes implementados:

- `review-eligible`
- `review-ineligible-no-purchase`
- `review-ineligible-not-delivered`
- `review-ineligible-duplicate`
- `review-ineligible-customer-not-found`
- `review-ineligible-product-not-found`
- `review-ineligible-unavailable`

### Guardrails implementados

- sem tenant/customer/product explícito, o service falha fechado.
- customer precisa pertencer ao tenant atual.
- produto precisa pertencer ao tenant atual.
- review duplicada do mesmo customer/produto bloqueia elegibilidade.
- pedidos de outro tenant não contam.
- o service não abre submissão pública e não emite evento.

### Limitação consciente

O vínculo produto ↔ pedido usa `variant_sku` porque `OrderItem` ainda não guarda `product_id`.

Isso é suficiente para o skeleton atual, mas uma futura evolução pode criar snapshot explícito de produto no pedido para deixar eligibility menos dependente de SKU.

### Próxima wave recomendada

**Trust & Social Proof Wave 13 — Review Eligibility Boundary Hardening Review**

Revisar se vale endurecer `OrderItem` com snapshot de `product_id/product_slug` antes de abrir qualquer formulário público de review.

## Trust & Social Proof Wave 13 — Review Eligibility Boundary Hardening Review

### Estado atual

`review_eligibility_queries.can_customer_review_product(...)` já consegue responder elegibilidade usando:

- `tenant_id`;
- `customer_id`;
- `product_id`;
- `OrderItem.variant_sku`;
- `ProductVariant.product_id`.

Esse contrato é seguro o suficiente para skeleton interno, mas ainda não é ideal para uma surface pública/customer-facing.

### Risco do boundary atual

Usar somente `variant_sku` como ponte produto ↔ pedido cria algumas fragilidades:

- `OrderItem` não guarda explicitamente o produto comprado;
- eligibility depende de `catalog.ProductVariant` ainda existir;
- eligibility depende de SKU continuar apontando para o mesmo produto;
- pedido histórico fica menos auditável se catálogo mudar;
- reviews públicas deveriam depender do snapshot transacional do pedido, não de lookup atual do catálogo.

### Decisão recomendada

Antes de abrir qualquer formulário público de review, endurecer `OrderItem` com snapshot explícito de produto.

Campos recomendados:

- `product_id_snapshot`
- `product_slug_snapshot`

O campo deve ser snapshot transacional, não FK obrigatória.

### Por que snapshot e não FK?

Pedido precisa preservar histórico mesmo se produto for desativado, arquivado ou tiver slug alterado.

Uma FK direta para `Product` poderia ser útil para queries, mas o contrato mais importante para `orders` é auditabilidade histórica. Por isso, o primeiro hardening deve ser snapshot simples e imutável na criação do pedido.

### Integração recomendada

No checkout completion:

1. resolver `ProductVariant` pelo `variant_sku` já validado;
2. copiar `variant.product_id` para `OrderItem.product_id_snapshot`;
3. copiar `variant.product.slug` para `OrderItem.product_slug_snapshot`;
4. manter `variant_sku` como snapshot de variante;
5. manter `title`, `subtitle`, `meta` e `price_snapshot` como estão.

No eligibility:

1. procurar pedidos por `items__product_id_snapshot=product_id`;
2. manter fallback por `variant_sku` apenas para pedidos legados sem snapshot;
3. documentar fallback como compatibilidade temporária;
4. não abrir formulário público enquanto o fallback for o único caminho.

### Guardrails

- não alterar total, preço, estoque ou pagamento.
- não recalcular pedidos antigos.
- não exigir backfill nesta primeira execução.
- migration deve adicionar campos opcionais.
- checkout passa a preencher snapshot para novos pedidos.
- eligibility continua read-only.
- reviews continuam nascendo como `pending`.

### Fora do escopo

- backfill histórico completo;
- FK obrigatória para `Product`;
- edição de pedido;
- alteração de eventos;
- formulário público de review;
- solicitação automática pós-entrega.

### Decisão

**Go para hardening de `OrderItem` com snapshot de produto antes da submissão pública.**

**No-Go para formulário público enquanto eligibility depender só de SKU.**

### Próxima wave recomendada

**Trust & Social Proof Wave 14 — Order Item Product Snapshot Execution**

Adicionar `product_id_snapshot` e `product_slug_snapshot` em `OrderItem`, preencher no checkout completion e atualizar eligibility para preferir snapshot com fallback legado por SKU.

## Trust & Social Proof Wave 14 — Order Item Product Snapshot Execution

### Escopo executado

- adicionados `product_id_snapshot` e `product_slug_snapshot` em `OrderItem`.
- criada migration `orders.0014_orderitem_product_snapshot`.
- checkout completion passa a preencher snapshot de produto para novos pedidos.
- `review_eligibility_queries` passa a preferir `product_id_snapshot`.
- fallback por `variant_sku` permanece apenas para itens legados sem snapshot.
- testes cobrem:
  - eligibility por snapshot;
  - fallback legado por SKU;
  - precedência do snapshot sobre SKU;
  - checkout copiando snapshot para `OrderItem`.

### Comportamento

Novos pedidos passam a guardar:

- SKU da variante em `variant_sku`;
- produto comprado em `product_id_snapshot`;
- slug histórico em `product_slug_snapshot`.

Eligibility agora busca primeiro pedidos com `items__product_id_snapshot=product_id`.

Se não houver snapshot, usa `variant_sku` apenas quando o item legado ainda tem `product_id_snapshot` vazio.

### Guardrails implementados

- campos são opcionais para preservar pedidos legados.
- nenhum total, preço, estoque, pagamento ou cupom foi recalculado.
- não há backfill histórico nesta wave.
- submissão pública continua bloqueada.
- reviews continuam dependendo de moderação e nascendo como `pending`.

### Próxima wave recomendada

**Trust & Social Proof Wave 15 — Public Review Submission Surface Review**

Revisar se já existem condições suficientes para desenhar o primeiro formulário customer-facing, provavelmente na área do cliente e não diretamente na PDP.

## Trust & Social Proof Wave 15 — Public Review Submission Surface Review

### Estado atual

`reviews` já possui:

- criação interna/admin como `pending`;
- moderação admin;
- PDP approved-only;
- eligibility read-only por `tenant/customer/product`;
- snapshot de produto em `OrderItem` para novos pedidos.

Isso já permite desenhar a primeira surface customer-facing, mas ainda não recomenda abrir submissão diretamente na PDP.

### Superfícies avaliadas

#### PDP

Vantagens:

- maior visibilidade;
- aproxima prova social do produto.

Riscos:

- PDP não carrega identidade de customer autenticado no contrato atual;
- PDP não sabe qual pedido torna o cliente elegível;
- exigiria resolver auth, customer e order context dentro de `catalog`;
- aumenta risco de misturar storefront anônimo com escrita tenant/customer-scoped.

Decisão: **No-Go para primeiro formulário público na PDP.**

#### Área do cliente — detalhe do pedido

Vantagens:

- já possui `tenant_id`, pedido e contexto de customer;
- o pedido contém os itens comprados;
- eligibility pode ser calculada item a item;
- CTA pode aparecer apenas em pedido entregue/concluído;
- mantém `accounts` como surface de jornada e `reviews` como dono da regra de review.

Decisão: **Go para primeiro formulário customer-facing a partir do detalhe do pedido.**

### Surface recomendada

Primeiro corte:

- exibir CTA “Avaliar produto” no detalhe do pedido para itens elegíveis;
- CTA aponta para uma rota customer-facing dedicada;
- formulário cria review como `pending`;
- após submit, redireciona de volta ao detalhe do pedido com feedback.

Rotas recomendadas:

- `GET /account/orders/<order_number>/reviews/<int:product_id>/new/`
- `POST /account/orders/<order_number>/reviews/<int:product_id>/new/`

### Boundary recomendado

`accounts.interfaces`:

- renderiza CTA no detalhe do pedido;
- hospeda a rota customer-facing, porque a origem é a jornada da conta/pedido;
- resolve `tenant_id` pela request;
- resolve customer ativo pelo account context;
- delega eligibility e submissão para `reviews.application`.

`reviews.application`:

- valida eligibility por `review_eligibility_queries`;
- cria review por command customer-facing futuro;
- retorna result codes explícitos;
- mantém status `pending`.

`orders`:

- permanece fonte do snapshot comprado;
- não cria review;
- não conhece moderação.

### Command customer-facing recomendado

Criar um command separado do admin:

`reviews.application.customer_review_submission_commands.submit_customer_product_review(...)`

Entradas:

- `tenant_id`
- `customer_id`
- `order_number`
- `product_id`
- `rating`
- `title`
- `body`
- `author_name`
- `consent_display_name`

Comportamento:

- exige eligibility positiva;
- cria review `pending`;
- associa customer;
- não aprova automaticamente;
- não emite evento/notificação nesta etapa;
- bloqueia duplicidade.

Result codes sugeridos:

- `customer-review-submitted-pending`
- `customer-review-ineligible`
- `customer-review-duplicate`
- `customer-review-invalid-rating`
- `customer-review-unavailable`

### UX recomendada

No detalhe do pedido:

- item elegível mostra “Avaliar produto”;
- item já avaliado mostra “Avaliação enviada para moderação”;
- item não entregue ainda não mostra CTA;
- feedback pós-submit: “Avaliação enviada para moderação”.

No formulário:

- nota 1–5 obrigatória;
- título opcional;
- comentário opcional, mas recomendado;
- nome de exibição padrão vindo do customer;
- texto explícito: “Sua avaliação será analisada antes de aparecer no produto.”

### Guardrails

- toda review pública nasce `pending`.
- moderação continua obrigatória.
- PDP continua apenas approved-only.
- PDP não recebe formulário nesta fase.
- route precisa validar tenant, customer, order e product.
- order precisa pertencer ao customer/tenant atual.
- product precisa existir no snapshot do pedido ou em fallback elegível.
- duplicidade customer/produto bloqueia nova submissão.

### Fora do escopo

- formulário direto na PDP;
- auto-approval para verified purchase;
- edição de review pelo cliente;
- resposta do lojista;
- fotos/vídeos;
- solicitação automática pós-entrega;
- e-mails/notificações;
- rate limit público avançado.

### Decisão

**Go para desenhar a primeira submissão customer-facing no detalhe do pedido.**

**No-Go para formulário público direto na PDP nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 16 — Customer Review Submission Command Execution**

Criar command customer-facing separado do admin, exigindo eligibility positiva e criando review `pending` com testes de tenant/customer/order/product scope.

## Trust & Social Proof Wave 16 — Customer Review Submission Command Execution

### Escopo executado

- criado `reviews.application.customer_review_submission_commands`.
- criado command `submit_customer_product_review(...)`.
- command customer-facing é separado do command admin.
- submissão exige tenant, customer, pedido e produto explícitos.
- pedido precisa pertencer ao customer/tenant atual.
- pedido precisa estar entregue/concluído.
- produto precisa estar presente no snapshot do pedido.
- review criada nasce sempre como `pending`.
- adicionados testes de:
  - criação pending;
  - ocultação de nome sem consentimento;
  - rating inválido;
  - pedido não entregue;
  - customer cross-tenant;
  - product cross-tenant;
  - produto fora do pedido;
  - duplicidade customer/produto.

### Contrato implementado

`submit_customer_product_review(...)` recebe:

- `tenant_id`
- `customer_id`
- `order_number`
- `product_id`
- `rating`
- `title`
- `body`
- `author_name`
- `consent_display_name`

Result codes:

- `customer-review-submitted-pending`
- `customer-review-ineligible`
- `customer-review-duplicate`
- `customer-review-invalid-rating`
- `customer-review-unavailable`

### Guardrails implementados

- command falha fechado sem tenant/customer/order/product.
- command não permite produto fora do pedido informado.
- command não permite pedido de outro customer.
- command não permite produto/customer cross-tenant.
- command não publica automaticamente.
- command não emite evento/notificação.
- command não é usado pela entrada admin.
- PDP permanece sem formulário público.

### Observação de privacidade

`consent_display_name=False` força `author_name="Cliente"` mesmo que o usuário envie um nome.

Isso evita expor identidade no storefront sem consentimento explícito.

### Próxima wave recomendada

**Trust & Social Proof Wave 17 — Customer Review Submission Route Review**

Revisar a menor rota/template na área do cliente para usar o command customer-facing a partir do detalhe do pedido, sem abrir formulário direto na PDP.

## Trust & Social Proof Wave 17 — Customer Review Submission Route Review

### Estado atual

O command customer-facing já existe, mas ainda não há rota nem template para o cliente enviar a avaliação.

O detalhe do pedido já é a superfície correta porque concentra:

- tenant resolvido pela request;
- pedido explícito;
- customer ativo via account context;
- itens comprados;
- feedback pós-ação;
- navegação de retorno segura.

### Rota recomendada

Criar uma rota filha de detalhe do pedido:

- `GET /account/orders/<order_number>/reviews/<int:product_id>/new/`
- `POST /account/orders/<order_number>/reviews/<int:product_id>/new/`

Nome sugerido:

- `accounts:account-order-review-create`

### View recomendada

Criar `AccountOrderReviewCreateView` em `accounts.interfaces.views`.

Responsabilidades da view:

- resolver `tenant_id` pela request;
- obter profile ativo via `account_customer_area_queries.get_active_profile_context(...)`;
- preencher `customer_id` a partir do profile;
- renderizar formulário simples;
- no POST, chamar `customer_review_submission_commands.submit_customer_product_review(...)`;
- redirecionar para o detalhe do pedido com `result=<code>`.

Responsabilidades que a view não deve assumir:

- consultar ORM de `reviews`;
- decidir moderação;
- publicar review;
- recalcular eligibility manualmente;
- tocar PDP/catalog.

### Template recomendado

Criar `customer_review_form_page.html`.

Campos:

- `rating` obrigatório;
- `title`;
- `body`;
- `author_name`;
- `consent_display_name`.

Copy obrigatória:

- “Sua avaliação será analisada antes de aparecer no produto.”
- “Você pode enviar sem exibir seu nome publicamente.”

### Feedback no detalhe do pedido

Adicionar result mapping em `_build_order_detail_feedback_context(...)`:

- `customer-review-submitted-pending`
  - sucesso: “Avaliação enviada para moderação”
- `customer-review-ineligible`
  - warning: “Avaliação não disponível para este item”
- `customer-review-duplicate`
  - info/warning: “Você já enviou avaliação para este produto”
- `customer-review-invalid-rating`
  - warning: “Escolha uma nota entre 1 e 5”
- `customer-review-unavailable`
  - warning: “Não foi possível enviar a avaliação agora”

### CTA no detalhe do pedido

Primeiro corte recomendado:

- adicionar CTA simples por item elegível depois que a rota existir;
- se o item já foi avaliado, mostrar estado “Avaliação enviada para moderação”;
- não tentar renderizar formulário inline dentro do detalhe.

Para evitar misturar query grande demais nesta execução, a primeira implementação pode:

- publicar a rota/formulário;
- permitir acesso direto por link;
- depois adicionar CTA por item em wave separada.

### Guardrails

- rota deve falhar fechado sem tenant/customer/order/product.
- POST precisa delegar para command customer-facing.
- toda review criada continua `pending`.
- PDP continua sem formulário.
- admin moderation continua obrigatório.
- sem evento/notificação.
- sem auto-approval.

### Decisão

**Go para criar rota/template customer-facing na área do cliente.**

**Go para dividir CTA por item em uma wave separada se a query do detalhe ficar grande demais.**

**No-Go para formulário inline na PDP ou no próprio detalhe do pedido nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 18 — Customer Review Submission Route Execution**

Criar rota, view, template e feedback no detalhe do pedido usando `customer_review_submission_commands`, sem ainda exigir CTA automático por item.

## Trust & Social Proof Wave 18 — Customer Review Submission Route Execution

### Escopo executado

- criada rota `accounts:account-order-review-create`.
- publicada rota `GET/POST /account/orders/<order_number>/reviews/<product_id>/new/`.
- criada view `AccountOrderReviewCreateView`.
- criado template `customer_review_form_page.html`.
- POST delega para `customer_review_submission_commands.submit_customer_product_review(...)`.
- feedback do detalhe do pedido passou a reconhecer result codes de review.
- adicionados testes de:
  - renderização do formulário;
  - criação pending com consentimento de nome;
  - rating inválido sem criação;
  - feedback pós-submit no detalhe do pedido.

### Comportamento

- GET renderiza formulário dedicado na área do cliente.
- POST cria review `pending` somente quando o command permite.
- POST sempre redireciona para o detalhe do pedido com `result=<code>`.
- formulário explica que a avaliação passa por moderação.
- formulário permite enviar sem exibir nome publicamente.

### Guardrails implementados

- a view não acessa ORM de `reviews`.
- a view resolve tenant/customer pelo contexto de conta.
- submissão real fica no command customer-facing de `reviews`.
- PDP continua sem formulário.
- não há CTA automático por item nesta wave.
- não há evento/notificação.
- moderação admin continua obrigatória.

### Próxima wave recomendada

**Trust & Social Proof Wave 19 — Customer Review CTA Eligibility Review**

Revisar como expor “Avaliar produto” no detalhe do pedido por item elegível sem inflar demais o payload de `account_customer_area_queries`.

## Trust & Social Proof Wave 19 — Customer Review CTA Eligibility Review

### Contexto

A rota customer-facing de avaliação já existe, mas ainda depende de acesso direto ao formulário.

O próximo incremento deve criar um CTA honesto no detalhe do pedido, sem transformar o detalhe em formulário inline e sem mover regra de eligibility para `accounts`.

### Módulo responsável

- `accounts` continua dono da superfície da área do cliente e do detalhe do pedido.
- `reviews` continua dono da regra de eligibility e submissão.
- `orders` continua apenas fornecendo snapshot de item já persistido.

### Estratégia recomendada

Usar o slot `actions` do componente `order_summary` para renderizar um bloco compacto de CTAs de avaliação.

Primeiro corte:

- mostrar “Avaliar produto” somente para itens elegíveis;
- criar links para `accounts:account-order-review-create`;
- não renderizar formulário inline;
- omitir CTA quando o item não for elegível, não estiver entregue ou já tiver review;
- manter feedback pós-submit no detalhe do pedido via result code já existente.

### Payload mínimo necessário

Para a execução, o detalhe do pedido precisa expor por item:

- `product_id_snapshot`;
- `product_slug_snapshot` quando disponível;
- título/nome já exibido.

A view pode então consultar `review_eligibility_queries.can_customer_review_product(...)` por produto elegível e montar os links de navegação.

### Guardrails

- não consultar ORM de `reviews` pela view de `accounts`;
- não duplicar regra de pedido entregue;
- não expor CTA para itens sem `product_id_snapshot`;
- não mostrar formulário na PDP;
- não criar review por GET;
- não alterar moderação admin;
- não emitir evento/notificação nesta wave.

### Decisão

**Go para CTA no detalhe do pedido usando o slot `actions` de `order_summary`.**

**Go para filtrar CTA via `review_eligibility_queries`, mantendo a regra em `reviews.application`.**

**No-Go para CTA inline por item nesta etapa se isso exigir reestruturar o componente de resumo.**

**No-Go para PDP como primeira surface de submissão.**

### Próxima wave recomendada

**Trust & Social Proof Wave 20 — Customer Review CTA Execution**

Adicionar dados de snapshot ao payload de itens do pedido, montar CTAs elegíveis na view do detalhe e renderizar o bloco no `order_summary.actions`, com testes para pedido entregue, pedido não entregue e review duplicada.

## Trust & Social Proof Wave 20 — Customer Review CTA Execution

### Escopo executado

- `account_customer_area_queries` passou a expor `product_id_snapshot` e `product_slug_snapshot` no payload de `order_items`.
- `AccountOrderDetailView` passou a montar CTAs de avaliação elegíveis.
- o CTA usa `reviews.application.review_eligibility_queries` para decidir elegibilidade.
- o template `order_detail_page.html` passou `order_review_actions` para `order_summary.actions`.
- adicionados testes para:
  - pedido entregue com item elegível;
  - pedido ainda não entregue;
  - produto já avaliado pelo mesmo customer.

### Comportamento

Quando um pedido entregue contém item com `product_id_snapshot` e o customer ainda não avaliou o produto, o detalhe do pedido exibe “Avaliar <produto>”.

O CTA navega para `accounts:account-order-review-create`, mantendo a submissão em formulário dedicado.

Pedidos não entregues, reviews duplicadas, itens sem snapshot e contexto sem tenant/customer não exibem CTA.

### Guardrails implementados

- a view de `accounts` não consulta ORM de `reviews`.
- a regra de eligibility permanece em `reviews.application`.
- não há criação de review por GET.
- não há formulário inline no detalhe do pedido.
- PDP continua sem surface de submissão.
- não há evento/notificação.
- moderação admin continua obrigatória.

### Próxima wave recomendada

**Trust & Social Proof Wave 21 — Review CTA UX State Review**

Revisar se devemos mostrar estados explícitos no detalhe do pedido para “já avaliado”, “aguardando entrega” ou “avaliação indisponível”, em vez de apenas omitir o CTA.

## Trust & Social Proof Wave 21 — Review CTA UX State Review

### Contexto

A Wave 20 já exibe CTA apenas quando o item está elegível para avaliação.

O comportamento atual é seguro, mas silencioso: itens não entregues, já avaliados, sem snapshot ou sem contexto explícito simplesmente não mostram ação.

### Análise de UX

Estados possíveis:

- **Elegível**: deve continuar aparecendo como CTA acionável “Avaliar <produto>”.
- **Já avaliado**: pode ser útil mostrar estado explícito para reduzir dúvida após submissão.
- **Aguardando entrega**: pode ser útil, mas tende a gerar ruído em pedidos recentes com vários itens.
- **Sem snapshot/indisponível**: não deve aparecer para o cliente; é um estado técnico/legado.
- **Sem tenant/customer explícito**: deve continuar falhando fechado e sem surface.

### Decisão de produto

Não vale transformar todos os estados de eligibility em mensagens visíveis ainda.

O primeiro estado explícito que vale adicionar é **já avaliado**, porque:

- confirma que a ação foi recebida;
- evita o cliente procurar novamente o botão;
- reduz repetição de tentativa de envio;
- conversa diretamente com a fila de moderação.

O estado **aguardando entrega** deve ficar para depois, idealmente junto de uma experiência pós-entrega mais ampla.

### Contrato recomendado para execução

Adicionar um bloco leve de `order_review_status_items` no detalhe do pedido, separado de `order_review_actions`.

Primeiro corte:

- manter CTA para itens elegíveis;
- mostrar “Avaliação enviada ou já registrada” para itens cujo resultado da eligibility seja `review-ineligible-duplicate`;
- não mostrar nada para `review-ineligible-not-delivered`;
- não mostrar nada para `review-ineligible-no-purchase`, `review-ineligible-product-not-found` ou `review-ineligible-unavailable`;
- preservar formulário dedicado.

### Guardrails

- não consultar ORM de `reviews` em template;
- não expor motivo técnico de inelegibilidade;
- não adicionar formulário inline;
- não transformar missing snapshot em mensagem para cliente;
- não mudar status/moderação de reviews;
- não emitir eventos.

### Decisão

**Go para estado explícito de “já avaliado” no detalhe do pedido.**

**No-Go para mostrar “aguardando entrega” nesta etapa.**

**No-Go para expor estados técnicos/legados de eligibility ao cliente.**

### Próxima wave recomendada

**Trust & Social Proof Wave 22 — Review Duplicate State Execution**

Adicionar um estado visual simples para produtos já avaliados no detalhe do pedido, usando o mesmo serviço de eligibility, sem formulário inline e sem expor estados técnicos.

## Trust & Social Proof Wave 22 — Review Duplicate State Execution

### Escopo executado

- extraído cálculo comum de eligibility para CTAs e estados de review no detalhe do pedido.
- adicionado estado visual para `review-ineligible-duplicate`.
- o estado aparece como alerta informativo abaixo do resumo do pedido.
- pedidos não entregues continuam sem estado visível.
- estados técnicos/legados continuam invisíveis ao cliente.
- adicionados testes para:
  - CTA elegível;
  - pedido não entregue sem CTA nem estado duplicado;
  - review duplicada com estado “Avaliação já registrada”.

### Comportamento

Quando o customer já enviou uma avaliação para o produto do pedido, o detalhe exibe:

- “Avaliação já registrada para <produto>”;
- descrição indicando que a avaliação permanece em moderação ou já foi analisada.

O botão “Avaliar <produto>” não aparece nesse caso.

### Guardrails implementados

- a view continua usando `reviews.application.review_eligibility_queries`;
- templates não consultam ORM;
- não há formulário inline;
- não há criação por GET;
- não há exposição de estados técnicos;
- não há alteração em moderação ou PDP.

### Próxima wave recomendada

**Trust & Social Proof Wave 23 — Review Moderation Feedback Loop Review**

Revisar se o cliente deve ver o estado moderacional da própria avaliação (`pending`, `approved`, `rejected`) ou se “já registrada” é suficiente por enquanto.

## Trust & Social Proof Wave 23 — Review Moderation Feedback Loop Review

### Contexto

O detalhe do pedido agora mostra estado genérico de duplicidade quando o customer já avaliou um produto.

Esse estado não diferencia se a review está `pending`, `approved` ou `rejected`.

### Leitura técnica

O modelo `ProductReview` já possui:

- `status`;
- `moderated_at`;
- vínculo opcional com `customer`;
- vínculo explícito com `tenant` e `product`.

O serviço de eligibility, porém, retorna apenas o resultado `review-ineligible-duplicate`, sem expor o objeto ou o status da review duplicada.

Isso é bom para bloqueio de ação, mas insuficiente para uma UI moderacional mais precisa.

### Opções avaliadas

1. **Manter mensagem genérica**
   - menor risco;
   - não exige novo contrato;
   - suficiente para confirmar recebimento.

2. **Exibir status moderacional simples**
   - `pending`: “Avaliação em moderação”;
   - `approved`: “Avaliação publicada”;
   - `rejected`: “Avaliação não publicada”.

3. **Exibir detalhes completos da review**
   - título, nota, data e status;
   - mais útil, mas cria uma mini-surface de “minhas avaliações”.

### Decisão de produto

O próximo incremento seguro é a opção 2: **status moderacional simples**.

Não vale ainda exibir conteúdo completo da review dentro do detalhe do pedido.

### Contrato recomendado

Criar query service customer-facing em `reviews.application`, por exemplo:

`customer_review_status_queries.get_customer_product_review_status(...)`

Entrada explícita:

- `tenant_id`;
- `customer_id`;
- `product_id`.

Saída mínima:

- `found`;
- `status`;
- `status_label`;
- `moderated_at`;
- `created_at`.

Sem retornar body/título/nota no primeiro corte.

### Semântica UX recomendada

- `pending`: “Avaliação em moderação”
  - descrição: “Recebemos sua avaliação e ela será analisada antes de aparecer no produto.”
- `approved`: “Avaliação publicada”
  - descrição: “Sua avaliação já pode aparecer na página do produto.”
- `rejected`: “Avaliação não publicada”
  - descrição: “Sua avaliação foi analisada e não será exibida no produto.”

### Guardrails

- `accounts` não deve consultar ORM de `reviews`;
- query deve exigir `tenant_id`, `customer_id` e `product_id`;
- não expor review de outro tenant/customer;
- não mostrar conteúdo da review nesta etapa;
- não permitir ação de contestação/edição ainda;
- não alterar moderação admin;
- não emitir eventos/notificações.

### Decisão

**Go para criar query customer-facing de status moderacional simples.**

**Go para substituir a mensagem genérica de duplicidade por labels baseados em status.**

**No-Go para exibir conteúdo completo da review nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 24 — Customer Review Moderation Status Execution**

Criar query service de status da review do customer e atualizar o estado visual no detalhe do pedido para pending/approved/rejected.

## Trust & Social Proof Wave 24 — Customer Review Moderation Status Execution

### Escopo executado

- criado `customer_review_status_queries` em `reviews.application`.
- a query exige `tenant_id`, `customer_id` e `product_id`.
- a query retorna status moderacional simples sem expor título, body ou rating.
- o detalhe do pedido passou a exibir:
  - `pending`: “Avaliação em moderação”;
  - `approved`: “Avaliação publicada”;
  - `rejected`: “Avaliação não publicada”.
- adicionados testes da query customer-facing.
- adicionados testes da UI para pending/approved/rejected.

### Comportamento

Quando o customer já avaliou o produto, o detalhe do pedido não mostra CTA de nova avaliação.

Em vez disso, mostra um alerta informativo baseado no status da review existente:

- “Recebemos sua avaliação e ela será analisada antes de aparecer no produto.”
- “Sua avaliação já pode aparecer na página do produto.”
- “Sua avaliação foi analisada e não será exibida no produto.”

### Guardrails implementados

- `accounts` não consulta ORM de `reviews`.
- query customer-facing é tenant/customer/product scoped.
- conteúdo da review não é exposto nesta etapa.
- não há edição, contestação ou reenvio.
- não há alteração no fluxo de moderação admin.
- não há evento/notificação.

### Próxima wave recomendada

**Trust & Social Proof Wave 25 — Review Customer History Surface Review**

Revisar se já vale criar uma superfície “Minhas avaliações” na área do cliente ou se o detalhe do pedido é suficiente para o ciclo atual.

## Trust & Social Proof Wave 25 — Review Customer History Surface Review

### Contexto

O cliente já consegue:

- enviar avaliação a partir do detalhe do pedido;
- ver CTA apenas quando o item está elegível;
- ver status moderacional simples para reviews já enviadas.

Ainda não existe uma página “Minhas avaliações”.

### Avaliação de ROI

Criar uma surface dedicada agora traria:

- listagem consolidada de reviews do customer;
- filtro por status;
- caminho futuro para edição/contestação;
- possível navegação a partir da sidebar da conta.

Mas também exigiria:

- nova rota em `accounts`;
- novo query service paginado em `reviews`;
- novo template/listagem;
- decisão sobre exibir conteúdo completo da review;
- decisão sobre links para produto/pedido;
- atualização da navegação da account area, que ainda é genérica.

### Decisão de produto

**Não vale criar “Minhas avaliações” agora.**

O detalhe do pedido já resolve o ciclo customer-facing mínimo:

- ação contextual;
- feedback pós-submit;
- status moderacional simples;
- sem nova surface para manter.

Uma página dedicada passa a valer quando existir pelo menos um destes requisitos:

- edição/reenvio de review rejeitada;
- histórico consolidado como parte relevante da conta;
- notificações de moderação levando para uma lista;
- volume alto de reviews por customer;
- necessidade de suporte/self-service.

### Guardrails

- manter submissão e status no detalhe do pedido;
- não adicionar item de sidebar ainda;
- não expor body/rating da review em lista;
- não criar rota vazia ou placeholder;
- não duplicar query de `reviews` em `accounts`.

### Decisão

**No-Go para “Minhas avaliações” nesta fase.**

**Go para encerrar o ciclo customer-facing básico de reviews no detalhe do pedido.**

**Go para priorizar agora o impacto de reviews aprovadas na conversão do PDP/storefront.**

### Próxima wave recomendada

**Trust & Social Proof Wave 26 — Approved Reviews Conversion Surface Review**

Revisar se a próxima evolução de maior ROI é melhorar a exibição pública de reviews aprovadas no PDP/listagem, em vez de expandir a área do cliente.

## Trust & Social Proof Wave 26 — Approved Reviews Conversion Surface Review

### Contexto

A PDP já consome `review_summary` e `approved_reviews`.

Hoje a seção aparece apenas quando há reviews aprovadas e fica abaixo dos blocos de preço, estoque, descrição curta e checks de decisão.

Isso já é seguro, tenant-scoped e approved-only, mas ainda é uma superfície mais informativa do que conversacional/de conversão.

### Diagnóstico de conversão

O maior ganho incremental agora não é criar mais backend.

O maior ganho é tornar a prova social visível antes da decisão de compra:

- resumo compacto perto do título/preço;
- média e contagem em linguagem curta;
- link/âncora para a seção completa de avaliações;
- estado discreto quando ainda não há reviews aprovadas, sem parecer erro.

### Melhorias candidatas

1. **Resumo compacto acima da dobra**
   - “⭐ 4.8/5 · 12 avaliações”
   - link para a seção completa.

2. **Distribuição por estrelas**
   - mais rica, mas exige query/aggregate adicional.

3. **Review destacada**
   - útil, mas exige critério editorial/ordenação.

4. **Reviews na listagem de produtos**
   - alto alcance, mas pode causar N+1 se não houver cuidado.

### Decisão de produto

O próximo incremento recomendado é a opção 1: **resumo compacto de reviews aprovadas no topo do PDP**.

Motivo:

- usa dados já disponíveis;
- não exige migration;
- não muda regra de domínio;
- melhora decisão de compra antes do CTA;
- mantém seção completa como detalhe.

### Contrato recomendado

No template do PDP:

- se `review_summary.review_count > 0`, renderizar um bloco/link compacto perto do título/preço;
- texto sugerido:
  - “⭐ {{ rating_average }}/5”
  - “{{ review_count }} avaliação(ões) aprovada(s)”
  - link “Ver avaliações”
- a seção completa deve ganhar `id="product-reviews"` para o link.

Não mostrar CTA de submissão na PDP.

### Guardrails

- usar somente reviews aprovadas;
- não exibir reviews pending/rejected;
- não consultar ORM no template;
- não alterar eligibility/submission;
- não criar formulário público;
- não fazer aggregates novos nesta wave;
- não mexer em listagem de produtos ainda.

### Decisão

**Go para resumo compacto de reviews aprovadas no topo do PDP.**

**Go para âncora para seção completa de avaliações.**

**No-Go para distribuição por estrelas/listagem de produtos nesta etapa.**

### Próxima wave recomendada

**Trust & Social Proof Wave 27 — PDP Review Summary Badge Execution**

Adicionar o resumo compacto de reviews aprovadas próximo ao título/preço do PDP, com âncora para a seção completa e testes de visibilidade approved-only.

## Trust & Social Proof Wave 27 — PDP Review Summary Badge Execution

### Escopo executado

- adicionado badge compacto de reviews no topo do PDP.
- o badge usa `review_summary.rating_average` e `review_summary.review_count`.
- o badge aparece somente quando há review aprovada.
- adicionada âncora `#product-reviews` para a seção completa.
- a seção completa de avaliações recebeu `id="product-reviews"`.
- testes reforçam:
  - visibilidade approved-only;
  - link “Ver avaliações”;
  - ausência do badge quando não há review aprovada.

### Comportamento

Quando há reviews aprovadas, o comprador vê perto do título:

- nota média;
- quantidade de avaliações aprovadas;
- link “Ver avaliações”.

Quando não há reviews aprovadas, nenhuma prova social vazia é exibida.

### Guardrails implementados

- apenas reviews aprovadas entram no resumo.
- pending/rejected continuam invisíveis no storefront.
- o template não consulta ORM.
- não há formulário de submissão na PDP.
- não há nova query/agregação.
- não há mudança em eligibility ou moderação.

### Próxima wave recomendada

**Trust & Social Proof Wave 28 — PDP Review Highlight Review**

Revisar se vale destacar uma review aprovada curta no topo/miolo do PDP ou se o badge compacto já é suficiente antes de atacar listagem de produtos.

## Trust & Social Proof Wave 28 — PDP Review Highlight Review

### Contexto

A PDP agora mostra um badge compacto com média/contagem acima da dobra e mantém a seção completa de avaliações.

O backend já entrega `approved_reviews` limitado e ordered por `-created_at`, `-id`.

### Análise de conversão

Um destaque textual pode aumentar confiança porque traduz a nota média em linguagem humana.

Mas também pode gerar ruído se:

- repetir a seção completa logo abaixo;
- destacar uma review longa demais;
- exigir curadoria manual cedo demais;
- parecer anúncio em vez de prova social.

### Decisão de produto

Vale adicionar um **micro-destaque de review aprovada** no PDP, usando a primeira review já carregada.

O destaque deve ser curto e complementar ao badge:

- título curto;
- rating;
- trecho do body quando existir;
- autor;
- link/âncora para seção completa.

Não criar query nova nem critério editorial avançado nesta etapa.

### Contrato recomendado

No contexto/template:

- usar `approved_reviews.0` como `featured_review`;
- renderizar o destaque somente se houver review aprovada;
- manter seção completa como fonte de detalhe;
- não exibir pending/rejected;
- não exibir CTA de submissão.

Posição recomendada:

- abaixo de preço/estoque e antes dos `pdp_decision_checks`;
- se ficar visualmente pesado, mover para logo acima da seção completa.

### Guardrails

- não criar nova query/agregação;
- não destacar review sem body e sem title se isso ficar pobre;
- não truncar no backend nesta wave;
- não expor conteúdo não aprovado;
- não alterar ordenação de reviews;
- não adicionar edição/contestação/submissão na PDP.

### Decisão

**Go para micro-destaque com a primeira review aprovada já carregada.**

**No-Go para curadoria manual ou distribuição por estrelas nesta etapa.**

**No-Go para reviews na listagem de produtos ainda.**

### Próxima wave recomendada

**Trust & Social Proof Wave 29 — PDP Featured Review Execution**

Renderizar um micro-destaque approved-only no PDP usando a primeira review aprovada já carregada, com testes de visibilidade e fallback sem body/title.

## Trust & Social Proof Wave 29 — PDP Featured Review Execution

### Escopo executado

- adicionado micro-destaque de review aprovada no PDP.
- o destaque usa a primeira entrada de `approved_reviews` já carregada.
- renderiza título, rating, body e autor quando disponíveis.
- adiciona fallback seguro quando title/body estão ausentes.
- mantém link para `#product-reviews`.
- adicionados testes para:
  - destaque com review aprovada;
  - ausência sem reviews aprovadas;
  - fallback sem title/body.

### Comportamento

Quando há review aprovada, a PDP mostra um card “Avaliação em destaque” próximo ao topo da decisão de compra.

Quando não há title/body, o destaque usa:

- “Cliente recomenda este produto”;
- “Avaliação aprovada por cliente verificado nesta loja.”

### Guardrails implementados

- apenas `approved_reviews` alimenta o destaque.
- pending/rejected continuam invisíveis.
- não há nova query/agregação.
- não há curadoria manual.
- não há formulário de submissão na PDP.
- a seção completa permanece como fonte de detalhe.

### Próxima wave recomendada

**Trust & Social Proof Wave 30 — Reviews Storefront List Surface Review**

Revisar se reviews aprovadas devem aparecer também nos cards/listagem de produtos ou se isso deve esperar uma query agregada segura para evitar N+1.

## Trust & Social Proof Wave 30 — Reviews Storefront List Surface Review

### Contexto

A PDP já possui:

- badge compacto de média/contagem;
- micro-destaque de review aprovada;
- seção completa approved-only.

A listagem de produtos ainda não recebe dados de reviews.

### Risco técnico

Adicionar reviews diretamente nos cards pode criar N+1 se cada produto consultar summary individualmente.

Hoje `storefront_catalog_queries.list_products(...)` enriquece uma lista de produtos do catálogo, mas não recebe um mapa agregado de reviews por produto.

### Decisão de produto

Reviews na listagem podem ser úteis, mas não devem ser implementadas direto no template nem via chamadas por produto.

O próximo passo seguro é criar primeiro uma query bulk em `reviews.application`:

`get_product_review_summaries(tenant_id, product_ids)`

Saída recomendada:

- chave por `product_id`;
- `review_count`;
- `rating_average`;
- `status`.

Depois disso, a listagem pode exibir um texto compacto nos cards:

- “⭐ 4.8 · 12 avaliações”

### Guardrails

- não consultar ORM de `reviews` em template;
- não chamar summary por produto em loop;
- não mostrar reviews pending/rejected;
- não exibir body/title/autor nos cards;
- não alterar PDP nesta etapa;
- não criar fallback fake de rating.

### Decisão

**No-Go para renderizar reviews nos cards antes de query bulk.**

**Go para criar contrato bulk de summaries approved-only em `reviews.application`.**

**Go para integrar cards/listagem apenas após o contrato bulk estar testado.**

### Próxima wave recomendada

**Trust & Social Proof Wave 31 — Product Review Bulk Summary Query Execution**

Criar query bulk tenant-scoped para summaries approved-only por lista de product_ids, com testes de isolamento por tenant e exclusão de pending/rejected.

## Trust & Social Proof Wave 31 — Product Review Bulk Summary Query Execution

### Escopo executado

- adicionado `get_product_review_summaries(...)` em `product_review_summary_queries`.
- o contrato recebe `tenant_id` e lista de `product_ids`.
- IDs inválidos, duplicados ou não positivos são descartados.
- o retorno é um mapa por `product_id`.
- produtos sem reviews aprovadas retornam summary `empty`.
- pending/rejected não entram no aggregate.
- reviews de outro tenant não entram no aggregate.

### Contrato

Entrada:

- `tenant_id`;
- `product_ids`.

Saída:

```python
{
    product_id: {
        "review_count": int,
        "rating_average": "0.0",
        "status": "empty" | "ready",
    }
}
```

### Guardrails implementados

- aggregate único agrupado por `product_id`;
- sem query por produto;
- sem body/title/autor;
- apenas approved;
- tenant obrigatório;
- retorno vazio sem tenant ou sem IDs válidos.

### Próxima wave recomendada

**Trust & Social Proof Wave 32 — Storefront Product Card Review Summary Integration**

Integrar o mapa bulk na listagem storefront e renderizar summary compacto nos cards sem N+1.

## Trust & Social Proof Wave 32 — Storefront Product Card Review Summary Integration

### Escopo executado

- a listagem storefront passou a coletar `product_ids` da página atual.
- a view chama `product_review_summary_queries.get_product_review_summaries(...)` uma vez por página.
- cada card recebe um texto compacto de summary quando há reviews aprovadas.
- o componente `product_card` renderiza o summary sem acessar ORM.
- adicionados testes para approved-only e isolamento por tenant.

### Comportamento

Cards com reviews aprovadas exibem:

- “⭐ <média>/5 · <contagem> avaliação(ões)”

Cards sem reviews aprovadas não exibem prova social vazia.

### Guardrails implementados

- sem query por produto;
- sem ORM no template;
- apenas summaries approved-only;
- pending/rejected continuam invisíveis;
- reviews de outro tenant não entram;
- nenhum body/title/autor aparece nos cards.

### Próxima wave recomendada

**Trust & Social Proof Wave 33 — Reviews Conversion Track Closure Review**

Revisar se o ciclo Trust & Social Proof já está bom o suficiente para encerrar a trilha ou se ainda há um incremento pequeno de alto ROI.

## Trust & Social Proof Wave 33 — Reviews Conversion Track Closure Review

### Inventário da trilha

A trilha de reviews agora cobre:

- modelo tenant-scoped de `ProductReview`;
- query approved-only para PDP;
- moderação admin;
- criação admin controlada;
- eligibility customer-facing baseada em pedido entregue;
- snapshot de produto em `OrderItem`;
- submissão customer-facing pela área do cliente;
- CTA elegível no detalhe do pedido;
- estado moderacional simples para reviews já enviadas;
- badge compacto de reviews aprovadas no PDP;
- micro-destaque de review aprovada no PDP;
- summary bulk approved-only;
- summary compacto de reviews nos cards da vitrine.

### O que ficou deliberadamente fora

- formulário público na PDP;
- página “Minhas avaliações”;
- edição/reenvio de review rejeitada;
- resposta do lojista;
- distribuição por estrelas;
- ordenação editorial/curadoria manual de featured review;
- notificações de status de moderação;
- métricas específicas de conversão por review.

### Avaliação de prontidão

**Go para encerrar a trilha Trust & Social Proof / Reviews Conversion.**

O sistema já possui:

- coleta segura de review;
- moderação antes de publicação;
- isolamento multi-tenant;
- exposição approved-only;
- impacto no PDP;
- impacto na listagem;
- proteção contra N+1 nos cards.

### Riscos residuais aceitáveis

- sem edição/contestação pelo cliente;
- sem analytics dedicado para mensurar lift de conversão;
- sem review reply do merchant;
- sem distribuição por estrelas.

Esses pontos são extensões futuras, não bloqueios para o estágio atual.

### Próximas abordagens candidatas

1. **Merchant Content & Merchandising**
   - banners, coleções, vitrines e curadoria manual.

2. **Customer Retention & Notifications**
   - e-mails/eventos de pós-compra, moderação e reengajamento.

3. **Search & Discovery**
   - busca/filtros/ranking com sinais de estoque, preço e prova social.

4. **Operational Admin UX**
   - dashboards e filas operacionais para lojista.

### Decisão

**Trilha encerrada com Go.**

**Não há próxima wave obrigatória dentro de Trust & Social Proof agora.**

### Próxima abordagem recomendada

**Search & Discovery Foundation Review**

Revisar busca, filtros e ordenação da vitrine agora que cards têm sinais de preço, estoque, curadoria e prova social.
