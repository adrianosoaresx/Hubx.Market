# Coupons

## Responsabilidade
Gerenciar cupons de desconto.

## Entidades principais
- Coupon

## Casos de uso
- criar cupom
- validar cupom
- aplicar cupom

## Regras de negócio
- um cupom por pedido

## Cart Foundation Wave 10 — Coupon Boundary Review

### Estado atual

O módulo `coupons` ainda é skeleton.

Ele deve ser tratado como dono futuro de:

- cadastro de cupom
- validade temporal
- limites de uso
- elegibilidade por tenant
- elegibilidade por carrinho/produto/cliente
- cálculo de desconto

### Contrato com cart

`cart` pode capturar intenção promocional, mas não deve implementar regra promocional complexa.

Contrato futuro recomendado:

- `cart` envia um snapshot do carrinho
- `coupons` valida o código
- `coupons` devolve resultado normalizado e desconto calculado
- `cart` persiste `coupon_code` e `discount_total` apenas com resposta válida

### Result codes sugeridos

- `coupon-valid`
- `coupon-invalid`
- `coupon-expired`
- `coupon-not-applicable`
- `coupon-unavailable`

### Guardrails

- validação sempre exige `tenant_id`
- desconto nunca pode ser global entre tenants
- `payments` não decide desconto
- `orders` guarda snapshot do cupom aplicado, não recalcula regra promocional
- `checkout` consome desconto validado, mas não deve virar motor promocional

### Próximo passo seguro

Antes de criar motor promocional real, o carrinho pode expor apenas uma surface de intenção:

- aplicar/remover código
- informar que validação promocional ainda não está ativa
- manter total sem desconto

Isso prepara a UI e o contrato sem criar desconto fictício.

## Cart Foundation Wave 12 — Coupon Validation Service Skeleton Review

### Objetivo

Definir o menor contrato real de `coupons.application` antes de criar modelo `Coupon`, desconto efetivo ou motor promocional.

Esta wave é uma revisão de boundary, não uma implementação de desconto.

### Princípio

`coupons` deve começar como **validador explícito e conservador**.

Antes de existir persistência real de cupons, o service pode responder `coupon-unavailable`, mas o contrato já deve ser estável o suficiente para `cart` consumir sem conhecer detalhes internos futuros.

### Service mínimo recomendado

```text
coupons.application.coupon_validation_queries.validate_cart_coupon(
    tenant_id,
    coupon_code,
    cart_snapshot,
)
```

### Entrada

Campos obrigatórios:

- `tenant_id`
- `coupon_code`
- `cart_snapshot`

Snapshot mínimo:

```text
{
  "cart_id": "...",
  "subtotal": "0.00",
  "items": [
    {
      "product_id": "...",
      "product_slug": "...",
      "variant_sku": "...",
      "quantity": 1,
      "price_snapshot": "0.00"
    }
  ]
}
```

### Saída

Contrato mínimo:

```text
{
  "result": "coupon-valid | coupon-invalid | coupon-expired | coupon-not-applicable | coupon-unavailable",
  "coupon_code": "...",
  "discount_total": "0.00",
  "message": "...",
  "reason": ""
}
```

### Result codes

| Código | Significado | Efeito no cart |
| --- | --- | --- |
| `coupon-valid` | cupom aceito e desconto calculado | persistir código e desconto |
| `coupon-invalid` | código inexistente ou inválido | não aplicar desconto |
| `coupon-expired` | cupom fora da janela de validade | não aplicar desconto |
| `coupon-not-applicable` | cupom existe, mas não vale para esse carrinho | não aplicar desconto |
| `coupon-unavailable` | validação indisponível ou ainda não implementada | salvar intenção sem desconto, se desejado |

### Invariantes

- validação exige `tenant_id`
- `discount_total` nunca pode ser negativo
- `discount_total` nunca pode exceder `cart_snapshot.subtotal`
- resposta deve usar decimal serializado como string
- `coupon_code` deve ser normalizado de forma determinística
- erro de infraestrutura deve virar `coupon-unavailable`, não desconto implícito
- service não cria pedido, pagamento ou reserva de estoque

### Boundary com cart

`cart` pode:

- enviar snapshot
- armazenar `coupon_code`
- armazenar `discount_total` retornado por `coupon-valid`
- renderizar mensagem de validação

`cart` não pode:

- consultar ORM interno de `coupons`
- decidir expiração
- decidir limite de uso
- decidir elegibilidade por produto/cliente
- aplicar desconto sem resposta `coupon-valid`

### Boundary com checkout e orders

`checkout`:

- consome o desconto já validado no handoff
- pode revalidar no futuro antes da criação do pedido
- não deve virar motor promocional

`orders`:

- guarda snapshot do cupom aplicado
- não recalcula promoção depois do pedido criado

### Fora de escopo

- modelo `Coupon`
- admin de cupom
- limite de uso
- campanhas automáticas
- frete grátis
- cupom por cliente
- cupom por categoria/produto
- stack/composição de promoções

### Próxima execução segura

**Cart Foundation Wave 13 — Coupon Validation Service Skeleton Execution**

Escopo recomendado:

- criar `coupons.application.coupon_validation_queries`
- implementar service que retorna `coupon-unavailable`
- normalizar `coupon_code`
- validar `tenant_id` e snapshot mínimo
- adicionar testes do contrato
- opcionalmente fazer `cart_commands.apply_coupon_intent(...)` chamar o service, mantendo desconto zerado

## Cart Foundation Wave 13 — Coupon Validation Service Skeleton Execution

### Escopo executado

- criado `coupons.application.coupon_validation_queries`
- criado `normalize_coupon_code(...)`
- criado `coupon_validation_queries.validate_cart_coupon(...)`
- implementado fallback conservador `coupon-unavailable`
- adicionados testes de contrato do service
- `cart_commands.apply_coupon_intent(...)` passou a chamar o service

### Contrato entregue

Enquanto não existe modelo `Coupon`, o service:

- exige `tenant_id`
- exige `coupon_code`
- exige snapshot mínimo com subtotal positivo e itens
- normaliza o código
- retorna `discount_total="0.00"`
- retorna `coupon-unavailable`
- informa `reason` explícito

### Reasons atuais

- `tenant-required`
- `coupon-code-required`
- `cart-snapshot-required`
- `coupon-engine-not-configured`

### Integração com cart

`cart` agora:

- monta snapshot mínimo do carrinho ativo
- chama `coupon_validation_queries.validate_cart_coupon(...)`
- mantém `discount_total=0.00` para qualquer resultado diferente de `coupon-valid`
- devolve o payload de validação junto do resultado de apply coupon

### Guardrails

- nenhum modelo `Coupon` foi criado
- nenhum desconto real foi aplicado
- nenhum total muda sem `coupon-valid`
- nenhuma regra promocional foi colocada em checkout, orders ou payments

### Próxima wave

**Cart Foundation Wave 14 — Coupon Model Minimal Contract Review**

Objetivo:

- decidir se já vale criar o modelo `Coupon`
- limitar o primeiro modelo a cupom percentual/fixo simples por tenant
- definir campos mínimos sem campanhas, stack, frete grátis ou segmentação avançada

## Cart Foundation Wave 14 — Coupon Model Minimal Contract Review

### Decisão

Já vale criar um modelo mínimo `Coupon`, desde que ele permaneça deliberadamente simples.

O objetivo não é criar um motor promocional completo, mas substituir o fallback `coupon-engine-not-configured` por uma validação real básica, tenant-scoped e auditável.

### Modelo mínimo recomendado

`Coupon`:

- `tenant`
- `code`
- `name`
- `status`
- `discount_type`
- `discount_value`
- `starts_at`
- `ends_at`
- `created_at`
- `updated_at`

### Campos

| Campo | Tipo recomendado | Obrigatório | Observação |
| --- | --- | --- | --- |
| `tenant` | FK `tenants.Tenant` | sim | isolamento multi-tenant |
| `code` | `CharField(64)` | sim | normalizado em uppercase |
| `name` | `CharField(120)` | não | rótulo interno/admin |
| `status` | choices | sim | `active`, `inactive` |
| `discount_type` | choices | sim | `percent`, `fixed` |
| `discount_value` | decimal | sim | percentual ou valor fixo |
| `starts_at` | datetime nullable | não | início opcional |
| `ends_at` | datetime nullable | não | fim opcional |

### Constraints e índices

- unique por `(tenant, code)`
- index por `(tenant, status)`
- index por `(tenant, code)`

### Regras mínimas de validação

`coupon-valid` somente quando:

- tenant existe
- código existe para o tenant
- status é `active`
- `starts_at` está vazio ou no passado
- `ends_at` está vazio ou no futuro
- carrinho possui subtotal positivo e itens
- desconto calculado é maior que zero

### Cálculo mínimo

`percent`:

- `discount_total = subtotal * discount_value / 100`

`fixed`:

- `discount_total = min(discount_value, subtotal)`

Invariantes:

- desconto nunca negativo
- desconto nunca maior que subtotal
- decimal sempre com 2 casas
- retorno sempre serializado como string

### Result codes

- `coupon-valid`
- `coupon-invalid`
- `coupon-expired`
- `coupon-not-applicable`
- `coupon-unavailable`

### Fora de escopo

- limite de uso
- limite por cliente
- cupom por produto/categoria
- frete grátis
- stack de promoções
- campanha automática
- admin completo de cupom
- analytics promocional
- reserva de desconto

### Boundary preservada

- `cart` continua chamando `coupons.application`
- `cart` não consulta ORM de `Coupon`
- `checkout` consome desconto validado no handoff
- `orders` futuramente guarda snapshot do cupom aplicado
- `payments` não participa de promoção

### Próxima wave

**Cart Foundation Wave 15 — Coupon Model Minimal Execution**

Escopo recomendado:

- criar modelo `Coupon`
- criar migration inicial de `coupons`
- trocar repository skeleton por ORM repository conservador
- validar `active`, janela temporal, tipo percentual/fixo
- manter testes de fallback indisponível para falhas de infraestrutura
- adicionar testes de `coupon-valid`, `coupon-invalid` e `coupon-expired`

## Cart Foundation Wave 15 — Coupon Model Minimal Execution

### Escopo executado

- criado modelo `Coupon`
- criada migration inicial de `coupons`
- validation service passou a usar ORM quando a tabela existe
- `coupon-valid` agora calcula desconto real simples
- `coupon-invalid` cobre cupom ausente, inativo ou de outro tenant
- `coupon-expired` cobre janela de validade fora do período
- fallback `coupon-unavailable` permanece para ausência de tenant, código, snapshot ou infraestrutura

### Modelo entregue

`Coupon`:

- `tenant`
- `code`
- `name`
- `status`
- `discount_type`
- `discount_value`
- `starts_at`
- `ends_at`
- `created_at`
- `updated_at`

### Regras implementadas

Percentual:

- `discount_total = subtotal * discount_value / 100`

Fixo:

- `discount_total = min(discount_value, subtotal)`

Invariantes:

- código normalizado em uppercase
- unique por `(tenant, code)`
- desconto nunca fica negativo
- desconto nunca excede subtotal
- desconto retorna serializado com 2 casas

### Integração com cart

`cart_commands.apply_coupon_intent(...)` agora:

- chama `coupon_validation_queries.validate_cart_coupon(...)`
- salva `coupon_code`
- aplica `discount_total` apenas com `coupon-valid`
- mantém `discount_total=0.00` para `coupon-invalid`, `coupon-expired` ou `coupon-unavailable`

### Fora de escopo preservado

- admin completo de cupom
- limite de uso
- segmentação por cliente
- elegibilidade por produto/categoria
- frete grátis
- múltiplos cupons
- stack promocional
- snapshot de cupom em pedido

### Próxima wave

**Cart Foundation Wave 16 — Coupon Admin Lite Review**

Objetivo:

- decidir se o próximo passo deve ser uma surface admin simples para criar/listar cupons
- evitar adicionar regras promocionais avançadas antes de operação básica tenant-scoped

## Cart Foundation Wave 16 — Coupon Admin Lite Review

### Decisão

Vale criar uma surface admin mínima para cupons antes de evoluir regras promocionais.

Motivo: agora já existe modelo `Coupon` e validação real simples, mas não há forma tenant-scoped de operar os cupons sem usar shell/admin técnico.

### Surface recomendada

Rotas:

- `/ops/coupons/`
- `/ops/coupons/new/`

Namespace sugerido:

- `coupons`

Views:

- `AdminCouponsListView`
- `AdminCouponCreateView`

Application services:

- `coupons.application.admin_coupon_queries`
- `coupons.application.admin_coupon_commands`

Templates:

- `pages/templates/admin_coupons_list_page.html`
- `pages/templates/admin_coupon_form_page.html`

### Listagem mínima

Campos:

- código
- nome
- status
- tipo
- valor
- validade
- criado/atualizado

Estados:

- sem tenant resolvido → empty state explícito de tenant ausente
- tenant sem cupons → empty state de “nenhum cupom criado”
- cupons existentes → tabela tenant-scoped

### Criação mínima

Campos permitidos:

- `code`
- `name`
- `status`
- `discount_type`
- `discount_value`
- `starts_at`
- `ends_at`

Validações mínimas:

- exigir tenant
- normalizar `code`
- impedir código duplicado por tenant
- exigir `discount_value > 0`
- para `percent`, limitar `discount_value <= 100`
- para `fixed`, permitir valor até subtotal futuro, mas cálculo continua capado pelo validator
- se `starts_at` e `ends_at` existirem, exigir `starts_at < ends_at`

### Fora de escopo

- edição completa
- exclusão
- limite de uso
- segmentação por cliente
- segmentação por produto/categoria
- frete grátis
- campanha automática
- stack/múltiplos cupons
- analytics promocional

### Boundary

`coupons.interfaces` pode expor a surface admin.

`coupons.application.admin_coupon_commands` deve ser o único dono da criação.

`cart` e `checkout` continuam sem acessar ORM de `Coupon`.

### Próxima wave

**Cart Foundation Wave 17 — Coupon Admin Lite Execution**

Escopo recomendado:

- criar query service de listagem tenant-scoped
- criar command service de criação tenant-scoped
- criar rotas `/ops/coupons/` e `/ops/coupons/new/`
- criar templates mínimos usando componentes existentes
- adicionar testes de listagem, criação, normalização e duplicidade por tenant

## Cart Foundation Wave 17 — Coupon Admin Lite Execution

### Escopo executado

- criado `coupons.application.admin_coupon_queries`
- criado `coupons.application.admin_coupon_commands`
- criada rota `/ops/coupons/`
- criada rota `/ops/coupons/new/`
- criadas views admin lite em `coupons.interfaces`
- criados templates:
  - `admin_coupons_list_page.html`
  - `admin_coupon_form_page.html`
- adicionado link “Cupons” no cockpit `/ops/`

### Contrato da surface

Listagem:

- tenant-scoped
- filtro por texto
- filtro por status
- empty state para tenant sem cupons
- empty state para tenant ausente

Criação:

- exige tenant resolvido
- normaliza `code`
- bloqueia duplicidade por tenant
- permite mesmo código em tenants diferentes
- valida `discount_value > 0`
- limita percentual a 100
- valida janela temporal quando informada

### Fora de escopo preservado

- edição
- exclusão
- limite de uso
- segmentação
- frete grátis
- campanhas
- analytics

### Próxima wave

**Cart Foundation Wave 18 — Coupon Checkout Handoff Snapshot Review**

Objetivo:

- revisar se o desconto aplicado no carrinho já deve viajar para `CheckoutSession`
- decidir quais campos de snapshot de cupom pertencem ao handoff
- evitar recalcular promoção fora de `coupons`

## Cart Foundation Wave 18 — Coupon Checkout Handoff Snapshot Review

### Diagnóstico

O handoff `cart → checkout` já transporta:

- `subtotal`
- `discount_total`
- `total`
- itens

O `checkout_activation_commands.activate_from_cart(...)` já usa `discount_total` no cálculo de `grand_total`.

Ainda falta transportar explicitamente:

- `coupon_code`
- estado/metadata mínima do cupom aplicado

Sem isso, o checkout recebe o efeito financeiro do desconto, mas perde o contexto operacional do cupom.

### Decisão

O desconto validado no carrinho deve viajar para `CheckoutSession` como **snapshot promocional**, não como recalculo.

Checkout não deve chamar `coupons` novamente nesta primeira etapa.

Motivo:

- `cart` já validou por `coupons.application`
- `checkout` é dono da finalização, não do motor promocional
- recalcular agora poderia divergir se o cupom mudar entre carrinho e checkout
- snapshot preserva a decisão comercial que o cliente viu no carrinho

### Snapshot mínimo recomendado

No payload `cart_checkout_queries`:

```text
{
  "coupon_code": "PROMO10",
  "discount_total": "39.98",
  "promotion_snapshot": {
    "coupon_code": "PROMO10",
    "discount_total": "39.98",
    "source": "cart",
    "validation_result": "coupon-valid"
  }
}
```

No modelo `CheckoutSession`, a próxima execução deve avaliar adicionar:

- `coupon_code`
- `promotion_snapshot`

### Regra de transporte

Transportar `coupon_code` somente quando:

- `cart.coupon_code` não está vazio
- `cart.discount_total > 0`

Se o cupom foi salvo como intenção mas não gerou desconto:

- não transportar como cupom aplicado
- opcionalmente manter fora do checkout nesta etapa

### Boundary

`cart`:

- guarda código e desconto validado
- monta snapshot de handoff

`checkout`:

- persiste snapshot recebido
- usa `discount_total` recebido no cálculo
- não recalcula cupom

`coupons`:

- continua dono de validação
- não participa diretamente do handoff checkout nesta primeira execução

`orders`:

- futuramente deve receber snapshot promocional a partir do checkout

### Fora de escopo

- revalidação no checkout
- expiração de cupom durante checkout
- limite de uso
- reserva de cupom
- snapshot no pedido
- refund/estorno proporcional

### Próxima wave

**Cart Foundation Wave 19 — Coupon Checkout Handoff Snapshot Execution**

Escopo recomendado:

- adicionar campos mínimos em `CheckoutSession`
  - `coupon_code`
  - `promotion_snapshot`
- incluir `coupon_code` e `promotion_snapshot` em `cart_checkout_queries`
- persistir snapshot em `activate_from_cart(...)`
- testar handoff com cupom válido e com cupom inválido/sem desconto

## Cart Foundation Wave 19 — Coupon Checkout Handoff Snapshot Execution

### Escopo executado

- adicionados campos em `CheckoutSession`:
  - `coupon_code`
  - `promotion_snapshot`
- criada migration de checkout para snapshot promocional
- `cart_checkout_queries` passou a transportar snapshot promocional
- `checkout_activation_commands.activate_from_cart(...)` persiste o snapshot recebido
- testes cobrem handoff com cupom válido e cupom inválido

### Regra implementada

O snapshot só viaja quando:

- `cart.coupon_code` existe
- `cart.discount_total > 0`

Quando cupom é inválido, expirado ou indisponível:

- `coupon_code` não é enviado ao checkout
- `promotion_snapshot` fica vazio
- `discount_total` permanece `0.00`

### Payload transportado

```text
promotion_snapshot = {
  "coupon_code": "...",
  "discount_total": "...",
  "source": "cart",
  "validation_result": "coupon-valid"
}
```

### Boundary preservada

- checkout não recalcula cupom
- coupons continua dono de validação
- cart monta snapshot de handoff
- orders ainda não recebe snapshot promocional nesta etapa

### Próxima wave

**Cart Foundation Wave 20 — Coupon Order Snapshot Review**

Objetivo:

- revisar se o snapshot promocional do checkout já deve ser copiado para `Order`
- decidir quais campos de cupom precisam ficar auditáveis no pedido
- evitar recalcular promoção depois do pedido criado

## Cart Foundation Wave 20 — Coupon Order Snapshot Review

### Diagnóstico

O fluxo atual está assim:

```text
Cart
→ CheckoutSession
→ Order
```

Hoje:

- `Cart` guarda `coupon_code` e `discount_total`
- `CheckoutSession` guarda `coupon_code`, `promotion_snapshot` e `discount_total`
- `Order` já guarda `discount_total`
- `Order` ainda não guarda `coupon_code` nem `promotion_snapshot`

Isso significa que o pedido preserva o efeito financeiro do cupom, mas perde o contexto promocional auditável.

### Decisão

O snapshot promocional do checkout deve ser copiado para `Order` na criação do pedido.

Não deve haver recálculo de cupom após o pedido nascer.

### Campos recomendados em Order

- `coupon_code`
- `promotion_snapshot`

### Regra de cópia

Ao criar `Order` a partir de `CheckoutSession`:

- copiar `discount_total`
- copiar `coupon_code`
- copiar `promotion_snapshot`

Somente quando:

- `CheckoutSession.coupon_code` não está vazio
- `CheckoutSession.discount_total > 0`
- `CheckoutSession.promotion_snapshot` não está vazio

Se não houver snapshot promocional válido:

- `Order.coupon_code = ""`
- `Order.promotion_snapshot = {}`

### Boundary

`checkout_completion_commands`:

- copia snapshot do checkout para pedido
- não chama `coupons`
- não recalcula desconto

`orders`:

- armazena snapshot do cupom aplicado
- não interpreta regra promocional

`coupons`:

- continua dono da validação
- não participa da criação do pedido

### Invariantes

- `Order.discount_total` deve continuar igual ao desconto usado em `CheckoutSession.grand_total`
- snapshot deve representar o que o cliente viu no checkout
- mudanças posteriores no cupom não alteram pedido já criado
- pedido precisa ser auditável mesmo se o cupom for desativado depois

### Fora de escopo

- revalidação no pedido
- limite de uso
- baixa de uso de cupom
- reversão/refund proporcional
- analytics de campanha
- exposição detalhada na área do cliente/admin

### Próxima wave

**Cart Foundation Wave 21 — Coupon Order Snapshot Execution**

Escopo recomendado:

- adicionar `coupon_code` e `promotion_snapshot` em `Order`
- criar migration de `orders`
- copiar campos em `checkout_completion_commands._create_order_from_session(...)`
- testar pedido criado com cupom válido
- testar pedido criado sem cupom/snapshot

## Cart Foundation Wave 21 — Coupon Order Snapshot Execution

### Escopo executado

- adicionados campos em `Order`:
  - `coupon_code`
  - `promotion_snapshot`
- criada migration de `orders`
- `checkout_completion_commands._create_order_from_session(...)` copia snapshot promocional da sessão
- testes cobrem pedido criado com snapshot promocional
- testes cobrem pedido criado sem cupom/snapshot

### Regra implementada

O pedido recebe snapshot promocional somente quando:

- `CheckoutSession.coupon_code` existe
- `CheckoutSession.discount_total > 0`
- `CheckoutSession.promotion_snapshot` não está vazio

Caso contrário:

- `Order.coupon_code = ""`
- `Order.promotion_snapshot = {}`

### Boundary preservada

- `orders` armazena snapshot
- `orders` não recalcula cupom
- `checkout` copia a decisão comercial que já estava na sessão
- `coupons` continua dono da validação

### Próxima wave

**Cart Foundation Wave 22 — Coupon Customer/Admin Visibility Review**

Objetivo:

- decidir onde exibir cupom aplicado no detalhe do pedido
- revisar área do cliente, admin orders e notificações
- evitar nova regra promocional; foco é visibilidade de snapshot

## Cart Foundation Wave 22 — Coupon Customer/Admin Visibility Review

### Diagnóstico

O snapshot promocional agora existe na trilha:

```text
Cart
→ CheckoutSession
→ Order
```

O pedido já possui:

- `discount_total`
- `coupon_code`
- `promotion_snapshot`

As superfícies já mostram totais/desconto, mas ainda não explicam qual cupom gerou o desconto.

### Decisão de visibilidade

Primeiro expor cupom aplicado em:

1. **Detalhe do pedido na área do cliente**
   - contexto: o cliente precisa entender por que houve desconto
   - origem: `accounts.application.account_customer_area_queries`
   - template: `order_detail_page.html`

2. **Admin Orders / detalhe operacional**
   - contexto: suporte e lojista precisam auditar a condição comercial do pedido
   - origem: `orders.application.admin_order_queries`
   - templates/admin views de orders

Adiar notificações.

### Racional para adiar notificações

Notificações são copy transacional sensível.

Antes de colocar cupom em e-mail/log customer-facing, vale garantir:

- formato final da mensagem
- consistência com total/desconto
- eventual snapshot no `order.created`
- impacto em owners/admins

### Contrato de apresentação

Exibir somente quando:

- `Order.coupon_code` não está vazio
- `Order.discount_total > 0`
- `Order.promotion_snapshot` não está vazio

Copy customer-facing recomendada:

```text
Cupom aplicado: PROMO10
Desconto preservado no pedido: -R$ 39,98
```

Copy admin-facing recomendada:

```text
Cupom aplicado: PROMO10 · origem: cart · validação: coupon-valid
```

### Fora de escopo

- recalcular desconto
- consultar `coupons`
- alterar notificações
- alterar eventos
- analytics promocional
- edição/correção de cupom no pedido

### Próxima wave

**Cart Foundation Wave 23 — Coupon Order Visibility Execution**

Escopo recomendado:

- adicionar campos derivados em `account_customer_area_queries`
- renderizar cupom no detalhe do pedido customer-facing
- adicionar campos derivados em `admin_order_queries`
- renderizar cupom no admin order detail
- cobrir testes com pedido com/sem cupom

## Cart Foundation Wave 23 — Coupon Order Visibility Execution

Execução concluída no recorte de visibilidade de pedido:

- `accounts.application.account_customer_area_queries` deriva o bloco de cupom aplicado a partir de `Order.coupon_code`, `Order.discount_total` e `Order.promotion_snapshot`.
- `orders.application.admin_order_queries` expõe o mesmo snapshot para operação, incluindo origem e resultado de validação preservados no pedido.
- `order_detail_page.html` mostra o cupom aplicado ao cliente somente quando o snapshot promocional é consistente.
- `admin_order_detail_page.html` mostra o cupom aplicado para operação somente como evidência do snapshot do pedido.
- a execução não consulta `coupons.application`, não recalcula desconto e não altera notificações.

Critério de exibição mantido:

- `coupon_code` preenchido;
- `discount_total > 0`;
- `promotion_snapshot` não vazio.

Próxima onda natural:

**Cart Foundation Wave 24 — Coupon Notification Copy Review**

Revisar se, quando e como o cupom aplicado deve aparecer em notificações/e-mails sem expandir payload de eventos ou criar regra promocional fora de `coupons`.

## Cart Foundation Wave 24 — Coupon Notification Copy Review

Decisão da revisão:

- notificações/e-mails não passam a exibir cupom aplicado nesta etapa;
- o CTA das notificações continua apontando para o detalhe do pedido, onde o snapshot promocional já é visível;
- qualquer copy futura deve derivar de `Order.coupon_code`, `Order.discount_total` e `Order.promotion_snapshot`;
- `notifications` não deve consultar `coupons` nem recalcular desconto;
- `coupons` continua dono de validação, não de copy transacional.

Próxima onda natural:

**Cart Foundation Wave 25 — Coupon Usage Accounting Review**

Revisar se já vale registrar uso de cupom por pedido, preservando tenant scope e sem transformar notificações ou pedidos em motor promocional.

## Cart Foundation Wave 25 — Coupon Usage Accounting Review

### Diagnóstico

O fluxo atual já preserva a decisão promocional aplicada:

```text
Cart
→ CheckoutSession
→ Order
```

Estado atual:

- `Coupon` é tenant-scoped e cobre código, status, tipo/valor de desconto e janela temporal.
- `Cart` valida cupom por `coupons.application.coupon_validation_queries`.
- `CheckoutSession` recebe `coupon_code` e `promotion_snapshot`.
- `Order` recebe `coupon_code` e `promotion_snapshot`.
- área do cliente e Admin Orders mostram o snapshot aplicado.

Ainda não existe:

- limite de uso por cupom;
- limite por cliente;
- contagem atômica de usos;
- ledger de resgate;
- reversão de uso em cancelamento/refund.

### Decisão

Não adicionar contador mutável em `Coupon` nesta etapa.

Quando usage accounting entrar, o caminho preferido é um ledger tenant-scoped de resgates, não um simples `usage_count` no cupom.

Modelo futuro recomendado:

```text
CouponRedemption
- tenant
- coupon
- order
- customer nullable
- coupon_code_snapshot
- discount_total_snapshot
- status: applied | reversed
- source: checkout_completion
- created_at
- reversed_at nullable
```

### Motivo

Um contador direto em `Coupon` parece simples, mas cria risco cedo demais:

- concorrência na criação de pedidos;
- idempotência de checkout;
- cancelamento e reversão futura;
- auditoria por pedido;
- separação entre cupom atual e snapshot histórico.

O `Order.promotion_snapshot` continua suficiente para explicar pedidos e atender suporte no estado atual do produto.

### Contrato futuro

Se a próxima execução criar `CouponRedemption`, ela deve:

- ser criada somente após `Order` nascer;
- exigir `tenant_id`;
- ser idempotente por `(tenant, order, coupon_code_snapshot)`;
- guardar snapshot do código e desconto;
- não recalcular cupom;
- não bloquear pedido se o ledger estiver indisponível na primeira versão, salvo decisão explícita contrária;
- não implementar limite de uso ainda, apenas registro auditável.

### Fora de escopo

- limite máximo de usos;
- limite por cliente;
- reserva de cupom no carrinho;
- reversão automática por cancelamento;
- relatórios de campanha;
- mudança no payload de eventos;
- alteração no fluxo de pagamento.

### Próxima wave

**Cart Foundation Wave 26 — Coupon Redemption Ledger Contract Review**

Desenhar o contrato mínimo de `CouponRedemption` tenant-scoped e decidir se o ledger deve ser criado em `checkout_completion_commands` ou por subscriber de evento.

## Cart Foundation Wave 26 — Coupon Redemption Ledger Contract Review

### Objetivo

Definir o menor contrato seguro para registrar resgate de cupom por pedido, sem ainda implementar migration/model.

### Decisão de ownership

O ledger pertence ao módulo `coupons`.

`checkout` pode acionar um application command de `coupons` depois que o pedido for criado, mas não deve escrever diretamente em tabela interna de cupons.

`orders` continua sendo fonte do snapshot promocional aplicado; não vira dono de contabilidade promocional.

### Modelo mínimo recomendado

```text
CouponRedemption
- tenant: FK Tenant
- coupon: FK Coupon nullable
- order: OneToOne/FK Order
- customer: FK Customer nullable
- coupon_code_snapshot: CharField(64)
- discount_total_snapshot: Decimal(12, 2)
- promotion_snapshot: JSONField
- status: applied | reversed
- source_type: application_command
- source_label: Coupon Redemption Commands
- created_at
- reversed_at nullable
```

### Constraints e índices

Recomendado:

- unique por `(tenant, order, coupon_code_snapshot)`;
- índice por `(tenant, coupon_code_snapshot)`;
- índice por `(tenant, status)`;
- índice por `(coupon, created_at)`.

Motivo:

- protege idempotência de checkout;
- permite auditoria por código mesmo se `coupon` for removido/desativado no futuro;
- mantém tenant scope em todas as leituras.

### Application command mínimo

```text
coupons.application.coupon_redemption_commands.record_order_coupon_redemption(
    tenant_id,
    order_number,
)
```

Comportamento:

- resolve `Order` por `tenant_id + order_number`;
- ignora pedidos sem `coupon_code`, sem desconto ou sem `promotion_snapshot`;
- tenta resolver `Coupon` por `tenant_id + coupon_code`;
- cria redemption idempotente;
- retorna result code explícito.

Result codes sugeridos:

- `coupon-redemption-recorded`
- `coupon-redemption-already-recorded`
- `coupon-redemption-skipped-no-coupon`
- `coupon-redemption-order-not-found`
- `coupon-redemption-unavailable`

### Ponto de criação recomendado

Primeira execução deve chamar o command em `checkout_completion_commands` logo após a criação do `Order` e antes de publicar `order.created`.

Racional:

- o pedido já existe e tem snapshot;
- a chamada fica no mesmo fluxo transacional inicial do checkout;
- idempotência evita duplicidade se a sessão já estiver completed;
- não exige expandir payload de evento nesta etapa.

Subscriber de evento pode ser revisitado depois, quando o bus interno tiver múltiplos consumidores de domínio além de notifications.

### Semântica de falha

Na primeira versão, falha no ledger não deve recalcular cupom nem alterar o desconto do pedido.

Decisão pendente para execução:

- se falha deve bloquear checkout;
- ou se deve retornar warning operacional mantendo pedido criado.

Recomendação inicial:

- falha técnica deve virar `coupon-redemption-unavailable` e não impedir o pedido;
- inconsistência de snapshot já deve continuar sendo barrada antes pela validação de checkout/pedido.

### Fora de escopo

- limite de uso;
- reserva no carrinho;
- reversão automática em cancelamento/refund;
- decremento/incremento em `Coupon`;
- relatório admin;
- analytics de campanha;
- mudança em notificações.

### Próxima wave

**Cart Foundation Wave 27 — Coupon Redemption Ledger Execution**

Criar `CouponRedemption`, migration e command idempotente; integrar de forma segura no checkout completion sem recalcular promoção.

## Cart Foundation Wave 27 — Coupon Redemption Ledger Execution

### Escopo executado

- criado `CouponRedemption` em `coupons.models`;
- criada migration `0002_couponredemption`;
- criado `coupons.application.coupon_redemption_commands`;
- integrado `record_order_coupon_redemption(...)` em `checkout_completion_commands` após a criação do pedido;
- adicionados testes de command idempotente e integração checkout → ledger.

### Contrato implementado

O ledger é criado somente quando o pedido possui:

- `coupon_code` preenchido;
- `discount_total > 0`;
- `promotion_snapshot` não vazio.

O command:

- resolve `Order` por `tenant_id + order_number`;
- resolve `Coupon` por `tenant_id + coupon_code`;
- cria `CouponRedemption` com snapshot de código, desconto e payload promocional;
- retorna `coupon-redemption-recorded` ou `coupon-redemption-already-recorded`;
- ignora pedido sem cupom válido com `coupon-redemption-skipped-no-coupon`.

### Boundary preservada

- `checkout` apenas chama application command de `coupons`;
- `checkout` não escreve tabela interna de coupons diretamente;
- `coupons` não recalcula promoção;
- `orders` continua sendo a fonte histórica do snapshot promocional aplicado;
- `order.created` não foi expandido.

### Fora de escopo preservado

- limite de uso;
- limite por cliente;
- reserva de cupom no carrinho;
- reversão por cancelamento/refund;
- relatórios admin;
- analytics promocional.

### Próxima wave

**Cart Foundation Wave 28 — Coupon Redemption Admin Visibility Review**

Revisar se o admin de cupons deve mostrar contagem/últimos resgates agora ou se o ledger permanece apenas auditável por código/testes nesta fase.

## Cart Foundation Wave 28 — Coupon Redemption Admin Visibility Review

### Diagnóstico

O admin atual de cupons é uma superfície lite:

- rota `/ops/coupons/`;
- listagem tenant-scoped;
- criação simples;
- filtros por busca e status;
- sem detalhe de cupom;
- sem edição;
- sem relatórios.

O ledger `CouponRedemption` já existe e é tenant-scoped, mas ainda não aparece na operação.

### Decisão

Vale expor uma visibilidade mínima de resgates no admin de cupons, mas não criar analytics promocional ainda.

Escopo recomendado para a próxima execução:

- adicionar coluna `Resgates` na listagem `/ops/coupons/`;
- mostrar contagem total de redemptions `applied` por cupom dentro do tenant atual;
- mostrar soma de desconto aplicado por cupom como valor agregado simples;
- manter tudo derivado de `CouponRedemption`, não de `Order`;
- manter filtro/search atual sem novas dimensões.

### Copy recomendada

Coluna:

```text
Resgates
3 uso(s) · R$ 45,00 em descontos
```

Quando não houver uso:

```text
Nenhum uso registrado
```

### Fora de escopo

- tela de detalhe do cupom;
- tabela de últimos pedidos/resgates;
- filtros por data;
- analytics de campanha;
- limite de uso;
- reversão/cancelamento;
- exportação;
- gráficos.

### Boundary

`coupons.application.admin_coupon_queries` pode ler `CouponRedemption` porque o ledger pertence a `coupons`.

Não deve consultar `orders` para recomputar uso.

Admin Orders continua mostrando o snapshot por pedido; Admin Coupons mostra apenas agregados simples por cupom.

### Próxima wave

**Cart Foundation Wave 29 — Coupon Redemption Admin Visibility Execution**

Adicionar agregados de resgate na listagem admin de cupons, com testes de tenant scope e cupom sem uso.

## Cart Foundation Wave 29 — Coupon Redemption Admin Visibility Execution

### Escopo executado

- `admin_coupon_queries.list_coupons(...)` agora agrega `CouponRedemption` por cupom.
- a listagem `/ops/coupons/` ganhou a coluna `Resgates`.
- cupons com uso mostram quantidade de redemptions `applied` e soma de desconto aplicado.
- cupons sem uso mostram “Nenhum uso registrado”.
- testes cobrem agregação, tenant scope e cupom sem uso.

### Regra implementada

Agregados são calculados somente a partir de `CouponRedemption`:

- filtro por `tenant_id` atual;
- status `applied`;
- contagem por relação `Coupon.redemptions`;
- soma de `discount_total_snapshot`.

Não há recomputação por `Order`.

### Boundary preservada

- `coupons` lê seu próprio ledger;
- Admin Coupons mostra agregados simples por cupom;
- Admin Orders continua responsável por explicar o snapshot de um pedido específico;
- não foram criados analytics, gráficos ou detalhe de campanha.

### Próxima wave

**Cart Foundation Wave 30 — Coupon Redemption Reversal Review**

Revisar se cancelamento/refund já deve marcar redemptions como `reversed` ou se reversão ainda deve ficar fora até existir fluxo financeiro/logístico completo.

## Cart Foundation Wave 30 — Coupon Redemption Reversal Review

### Diagnóstico

`CouponRedemption` já possui:

- `status: applied | reversed`;
- `reversed_at`;
- vínculo tenant/coupon/order;
- snapshot de código, desconto e payload promocional.

Fluxos atuais relevantes:

- Admin Orders possui `cancel_order(...)`;
- cancelamento bloqueia pedido enviado;
- cancelamento já devolve estoque quando aplicável;
- pagamento externo suporta `payment.paid` e `payment.failed`;
- `payment.refunded` ainda é evento unsupported.

### Decisão

Não implementar reversão por refund nesta fase.

O primeiro ponto seguro para reversão é o cancelamento administrativo de pedido, porque:

- já existe fluxo explícito;
- já é tenant-scoped;
- já registra histórico operacional;
- não depende de provider financeiro;
- não exige semântica parcial de refund.

### Escopo recomendado para próxima execução

Criar command em `coupons.application`:

```text
reverse_order_coupon_redemption(
    tenant_id,
    order_number,
    source_type="admin_action",
    source_label="Admin Orders",
)
```

Comportamento:

- resolve `Order` por `tenant_id + order_number`;
- busca redemptions `applied` do pedido no tenant;
- marca como `reversed`;
- preenche `reversed_at`;
- retorna result code explícito;
- deve ser idempotente.

Result codes sugeridos:

- `coupon-redemption-reversed`;
- `coupon-redemption-already-reversed`;
- `coupon-redemption-not-found`;
- `coupon-redemption-order-not-found`;
- `coupon-redemption-reversal-unavailable`.

### Integração recomendada

Chamar o command dentro de `admin_order_commands.cancel_order(...)`, após o status do pedido virar `canceled` e dentro da mesma intenção operacional.

Falha de reversão:

- não deve recalcular desconto;
- não deve reabrir pedido;
- pode retornar apenas sinal técnico/log futuro;
- nesta primeira execução, pode ser best-effort se o command estiver indisponível.

### Fora de escopo

- refund parcial;
- `payment.refunded`;
- reversão automática por chargeback;
- reativar redemption em reabertura de pedido;
- limite de uso dependente de reversal;
- ajuste financeiro/contábil;
- notificação ao cliente sobre reversão.

### Próxima wave

**Cart Foundation Wave 31 — Coupon Redemption Cancel Reversal Execution**

Implementar command idempotente de reversão e integrar ao cancelamento admin de pedido, sem tocar em refund financeiro.

## Cart Foundation Wave 31 — Coupon Redemption Cancel Reversal Execution

### Escopo executado

- `coupon_redemption_commands` passou a expor `reverse_order_coupon_redemption(...)`.
- o command resolve `Order` por `tenant_id + order_number`.
- redemptions `applied` do pedido passam para `reversed`.
- `reversed_at` é preenchido.
- o command é idempotente para redemptions já revertidas.
- `admin_order_commands.cancel_order(...)` chama o command sem editar o ledger diretamente.

### Result codes implementados

- `coupon-redemption-reversed`;
- `coupon-redemption-already-reversed`;
- `coupon-redemption-not-found`;
- `coupon-redemption-order-not-found`;
- `coupon-redemption-reversal-unavailable`.

### Boundary preservada

- `orders` continua dono do cancelamento do pedido.
- `coupons` continua dono do ledger promocional.
- `orders` apenas chama application command de `coupons`.
- não houve suporte a `payment.refunded`.
- não houve recálculo de desconto.

### Observação de compatibilidade

Quando o cancelamento admin ainda opera em modo legado sem `tenant_id` explícito na request, a integração usa `order.tenant_id` como fallback seguro para chamar `coupons`.

### Próxima wave

**Cart Foundation Wave 32 — Coupon Applied Aggregates Semantics Review**

Revisar se a listagem admin de cupons deve contar apenas `applied`, expor reversões separadamente ou mostrar saldo líquido de uso/desconto.

## Cart Foundation Wave 32 — Coupon Applied Aggregates Semantics Review

### Diagnóstico

A listagem `/ops/coupons/` já mostra agregados de redemption por cupom.

Hoje a query conta apenas:

- `CouponRedemption.status = applied`;
- soma de `discount_total_snapshot` apenas de redemptions aplicadas.

Depois da Wave 31, redemptions podem ser revertidas por cancelamento admin:

```text
applied → reversed
```

Isso cria três leituras possíveis:

1. **Histórico bruto**
   - total de resgates criados, incluindo revertidos.
2. **Uso ativo**
   - apenas redemptions ainda `applied`.
3. **Reversões**
   - redemptions `reversed`, úteis para auditoria operacional.

### Decisão

Manter a coluna atual `Resgates` como **uso ativo**.

Ou seja:

- conta somente `applied`;
- soma somente desconto de `applied`;
- redemptions revertidas não entram no número principal.

Motivo:

- a lista de cupons deve responder “quanto este cupom ainda conta como usado?”;
- cancelamentos não devem inflar o uso operacional ativo;
- isso prepara limites futuros de uso sem contar pedidos cancelados como consumo vigente.

### Ajuste recomendado

Na próxima execução, explicitar reversões em linha separada/label complementar, sem mudar o número principal.

Copy recomendada:

```text
2 uso(s) ativos · R$ 25,00 em descontos
1 reversão
```

Quando não houver uso ativo, mas houver reversão:

```text
Nenhum uso ativo · 1 reversão
```

Quando nunca houve redemption:

```text
Nenhum uso registrado
```

### Campos derivados recomendados

`admin_coupon_queries.list_coupons(...)` deve expor:

- `active_redemption_count`;
- `active_redemption_discount_total`;
- `reversed_redemption_count`;
- `reversed_redemption_discount_total`;
- `redemption_label`.

Compatibilidade:

- `redemption_count` pode continuar como alias de `active_redemption_count` por uma wave para não quebrar testes/templates.

### Fora de escopo

- saldo financeiro líquido formal;
- relatório por período;
- detalhe de pedidos revertidos;
- refund financeiro;
- reativar redemption;
- limite de uso.

### Próxima wave

**Cart Foundation Wave 33 — Coupon Reversal Aggregate Visibility Execution**

Atualizar a query/listagem para deixar claro uso ativo vs reversões, mantendo a coluna única e sem criar tela nova.

## Cart Foundation Wave 33 — Coupon Reversal Aggregate Visibility Execution

### Escopo executado

- `admin_coupon_queries.list_coupons(...)` passou a derivar agregados separados para `applied` e `reversed`.
- a coluna `Resgates` continua única, mas agora explicita uso ativo.
- reversões aparecem como complemento no label.
- `redemption_count` permanece como alias de `active_redemption_count` por compatibilidade.

### Campos derivados

- `active_redemption_count`;
- `active_redemption_discount_total`;
- `reversed_redemption_count`;
- `reversed_redemption_discount_total`;
- `redemption_count`;
- `redemption_discount_total`;
- `redemption_label`.

### Copies implementadas

Com uso ativo e reversão:

```text
2 uso(s) ativos · R$ 25,00 em descontos · 1 reversão(ões)
```

Sem uso ativo, mas com reversão:

```text
Nenhum uso ativo · 1 reversão(ões)
```

Sem qualquer redemption:

```text
Nenhum uso registrado
```

### Boundary preservada

- agregados continuam vindo apenas de `CouponRedemption`;
- `Order` não é consultado para recomputar histórico promocional;
- não há tela nova, gráfico ou analytics.

### Próxima wave

**Cart Foundation Wave 34 — Coupon Admin Detail Surface Review**

Revisar se já vale criar detalhe de cupom com últimos redemptions ou se a listagem agregada encerra o recorte promocional mínimo.

## Cart Foundation Wave 34 — Coupon Admin Detail Surface Review

### Diagnóstico

O admin de cupons já possui:

- listagem tenant-scoped em `/ops/coupons/`;
- criação de cupom simples;
- filtros por busca e status;
- colunas de status, desconto, validade e atualização;
- agregados de resgates ativos e reversões;
- ledger `CouponRedemption` tenant-scoped;
- reversão automática do ledger em cancelamento admin.

Ainda não possui:

- detalhe de cupom;
- edição;
- últimos pedidos/redemptions;
- filtros por período;
- limite de uso;
- analytics de campanha.

### Decisão

Não criar detalhe de cupom agora.

A listagem agregada encerra o recorte promocional mínimo desta fase.

Motivo:

- o lojista já consegue criar cupom, ver status e entender uso ativo/reversões;
- uma tela de detalhe puxaria naturalmente últimos pedidos, filtros, analytics e ações de edição;
- ainda não existe limite de uso, campanha, segmentação ou edição;
- criar detalhe agora aumentaria superfície antes de haver decisões de produto suficientes.

### O que fica como pronto nesta trilha

- captura de cupom no carrinho;
- validação mínima por `coupons.application`;
- snapshot cart → checkout → order;
- visibilidade customer/admin no detalhe do pedido;
- ledger `CouponRedemption`;
- reversão por cancelamento admin;
- agregados na listagem admin de cupons.

### Próxima abordagem recomendada

**Cart/Checkout Reliability Hardening**

Motivo:

- a trilha promocional mínima já está funcional;
- antes de expandir cupom para detalhe/analytics/limites, vale endurecer pontos centrais do carrinho e checkout:
  - idempotência de add-to-cart;
  - expiração/retomada de carrinho;
  - mensagens de erro;
  - consistência de totals;
  - UX de checkout bloqueado.

### Próxima wave natural

**Cart Reliability Wave 1 — Cart Session Idempotency Review**

Revisar se múltiplos submits/add-to-cart criam duplicidade, sobrescrevem quantidade corretamente e preservam tenant/session boundaries.
