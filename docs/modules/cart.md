# Cart

## Responsabilidade
Gerenciar carrinho persistente.

## Entidades principais
- Cart
- CartItem

## Casos de uso
- adicionar item
- remover item
- atualizar quantidade

## Regras de negócio
- um carrinho ativo por customer por tenant

## Cart Foundation Wave 1 — Cart Domain Contract Review

### Leitura atual

Hoje o sistema já possui um **carrinho leve dentro do checkout**:

- `CheckoutSession`
- `CheckoutSessionItem`
- mutação de quantidade/remover item em `checkout_session_commands`
- ativação direta da PDP para checkout via `checkout_activation_commands.activate_from_product(...)`

Esse contrato funciona para:

- iniciar compra a partir da PDP
- manter multi-item dentro de uma sessão de checkout aberta
- revisar itens antes de informar entrega/pagamento
- gerar pedido somente no fluxo de checkout

Mas ainda não existe um domínio `cart` real antes do checkout.

### Problema que `cart` deve resolver

`cart` deve cobrir a etapa entre:

```
PDP / catálogo
→ intenção de compra persistente
→ revisão de carrinho
→ handoff para checkout
```

Sem `cart`, a PDP pula direto para `CheckoutSession`, o que limita:

- carrinho persistente antes da finalização
- compra multi-item fora do checkout
- aplicação futura de cupom antes do checkout
- analytics de intenção entre PDP e checkout
- recuperação de carrinho antes de sessão formal de checkout

### Boundary com checkout

`cart` **não substitui** `CheckoutSession`.

Responsabilidades:

| Responsabilidade | Dono |
| --- | --- |
| intenção de compra antes da finalização | `cart` |
| itens selecionados antes do checkout | `cart` |
| cupom aplicado antes da finalização | `cart` + `coupons` |
| endereço, frete, pagamento e revisão final | `checkout` |
| criação do pedido | `checkout` → `orders` |
| confirmação de pagamento | `payments` |

### Contrato mínimo recomendado

`Cart`:

- `tenant`
- `customer` opcional
- `session_key` opcional para visitantes
- `status`
  - `active`
  - `converted`
  - `abandoned`
  - `expired`
- `currency`
- `subtotal`
- `discount_total`
- `total`
- `coupon_code` opcional
- timestamps

`CartItem`:

- `cart`
- `product_id` opcional
- `product_slug`
- `product_name`
- `variant_sku`
- `variant_label`
- `image_url`
- `price_snapshot`
- `compare_price_snapshot`
- `quantity`
- `sort_order`
- timestamps

### Regras mínimas

- todo carrinho pertence a um `tenant`
- carrinho de visitante usa `session_key`
- carrinho de cliente logado pode vincular `customer`
- deve existir apenas um carrinho `active` por `tenant + session_key` ou `tenant + customer`
- `CartItem` guarda snapshot suficiente para revisão visual
- preço/estoque verdadeiros continuam pertencendo a `catalog.ProductVariant`
- carrinho pode recalcular subtotal com snapshots, mas não decide frete final
- carrinho pode receber cupom validado por `coupons`, mas não deve conter motor promocional próprio
- carrinho não cria pedido
- carrinho não inicia pagamento

### Handoff para checkout

O handoff seguro deve ser:

```
Cart ativo
→ checkout command consome snapshot do carrinho
→ cria ou atualiza CheckoutSession
→ marca Cart como converted
→ checkout segue com entrega, pagamento e pedido
```

Enquanto esse handoff não existir, `checkout_activation_commands.activate_from_product(...)` continua sendo compatibilidade aceitável para PDP → checkout.

### Fora de escopo nesta primeira implementação

- carrinho compartilhado entre dispositivos
- merge avançado entre visitante e customer
- reserva de estoque
- cálculo final de frete
- motor avançado de promoções
- abandono de carrinho com notificações
- analytics completo de funil

### Próxima wave

**Cart Foundation Wave 2 — Cart Model & Service Skeleton**

Objetivo:

- criar `Cart` e `CartItem`
- adicionar command service mínimo:
  - `get_or_create_active_cart`
  - `add_item`
  - `update_quantity`
  - `remove_item`
- manter a interface pública pequena antes de ligar PDP e checkout

## Cart Foundation Wave 2 — Cart Model & Service Skeleton

### Escopo executado

- criados modelos persistidos:
  - `Cart`
  - `CartItem`
- criada migration inicial do módulo `cart`
- criado command service mínimo:
  - `cart_commands.get_or_create_active_cart(...)`
  - `cart_commands.add_item(...)`
  - `cart_commands.update_quantity(...)`
  - `cart_commands.remove_item(...)`

### Contrato implementado

`Cart` agora guarda:

- `tenant`
- `customer` opcional
- `session_key` opcional
- `status`
- `currency`
- `subtotal`
- `discount_total`
- `total`
- `coupon_code`
- `converted_checkout_session_key`

`CartItem` agora guarda snapshot mínimo:

- produto opcional
- slug/nome do produto
- SKU/label da variante
- imagem
- preço e compare price
- quantidade
- ordenação

### Guardrails

- não cria pedido
- não inicia pagamento
- não calcula frete final
- rejeita produto cross-tenant
- exige tenant resolvido
- exige customer ou session_key para carrinho ativo
- mantém no máximo um carrinho ativo por:
  - `tenant + customer`
  - `tenant + session_key`

### Status

- o domínio `cart` deixou de ser skeleton.
- ainda não está ligado à PDP, catálogo ou checkout.
- a compatibilidade PDP → `CheckoutSession` permanece ativa enquanto o handoff cart → checkout não existir.

### Próxima wave

**Cart Foundation Wave 3 — Cart Storefront Surface Review**

Objetivo:

- decidir a menor superfície pública para usar o carrinho real:
  - rota/tela de carrinho
  - botão PDP “Adicionar ao carrinho”
  - ou handoff cart → checkout
- evitar mexer em PDP e checkout na mesma wave sem necessidade.

## Cart Foundation Wave 3 — Cart Storefront Surface Review

### Opções avaliadas

| Opção | Valor | Risco | Decisão |
| --- | --- | --- | --- |
| criar `/cart/` somente leitura | alto para ativar o domínio sem mexer no funil | baixo | escolher primeiro |
| ligar PDP “Adicionar ao carrinho” | alto para conversão | médio, altera comportamento atual da PDP | segunda etapa |
| criar handoff `Cart → CheckoutSession` | alto, fecha o ciclo | médio/alto, toca checkout | terceira etapa |

### Decisão

A próxima implementação deve começar por uma **surface storefront de carrinho em `/cart/`**.

Essa surface deve:

- resolver `tenant_id` pela request
- obter carrinho ativo por `tenant + session_key`
- renderizar itens, quantidades e totais
- exibir empty state quando não houver carrinho ativo ou itens
- mostrar CTA para voltar ao catálogo
- deixar CTA de checkout desabilitado/ausente enquanto o handoff não existir

### Fora de escopo desta surface inicial

- botão PDP “Adicionar ao carrinho”
- mutações HTTP na tela de carrinho
- handoff para `CheckoutSession`
- aplicação de cupom
- cálculo de frete
- criação de pedido
- analytics de abandono

### Contrato de UI recomendado

Template:

- `pages/templates/cart_page.html`

Contexto mínimo:

- `page_title`
- `page_description`
- `cart_items`
- `subtotal`
- `discount_total`
- `total`
- `empty_title`
- `empty_description`
- `continue_shopping_href`
- `checkout_href` futuro/opcional

Componentes reaproveitados:

- `shared/components/commerce/cart_item.html`
- `shared/components/composite/order_summary.html`
- `shared/components/feedback/empty_state.html`
- `shared/components/actions/button.html`

### Contrato de query recomendado

Novo service:

- `cart.application.cart_page_queries`

Método mínimo:

- `get_cart_page_data(tenant_id, session_key)`

Regras:

- sem `tenant_id`, retorna estado indisponível/empty
- sem `session_key`, retorna empty state seguro
- nunca busca carrinho de outro tenant
- não cria carrinho em leitura
- não consome checkout

### Rota recomendada

Nova rota storefront:

- `/cart/`

Namespace sugerido:

- `cart:cart-page`

### Próxima wave

**Cart Foundation Wave 4 — Cart Storefront Read Surface Execution**

Objetivo:

- implementar service de leitura
- criar `cart_page.html`
- criar rota `/cart/`
- adicionar testes de render, empty state e tenant/session scope

## Cart Foundation Wave 4 — Cart Storefront Read Surface Execution

### Escopo executado

- criado query service:
  - `cart.application.cart_page_queries`
- criada view storefront:
  - `cart.interfaces.views.CartPageView`
- criada rota:
  - `/cart/`
  - namespace `cart:cart-page`
- criado template:
  - `pages/templates/cart_page.html`
- adicionados testes para:
  - empty state sem carrinho ativo
  - render de carrinho ativo por session key
  - isolamento entre tenants
  - leitura sem criação automática de carrinho

### Contrato da surface

A página `/cart/` agora:

- exige tenant resolvido por subdomínio
- usa `request.session.session_key` como owner de carrinho visitante
- não cria carrinho em leitura
- mostra empty state seguro quando não há carrinho ativo
- renderiza itens e resumo quando há carrinho ativo
- reaproveita componentes existentes:
  - `cart_item`
  - `order_summary`
  - `empty_state`
  - `button`

### Guardrails preservados

- não liga PDP ao carrinho ainda
- não altera o fluxo atual PDP → `CheckoutSession`
- não cria handoff para checkout
- não aplica cupom
- não calcula frete
- não cria pedido

### Próxima wave

**Cart Foundation Wave 5 — PDP Add-To-Cart Bridge Review**

Objetivo:

- revisar como trocar ou complementar o POST atual da PDP
- decidir se o CTA primário vira “Adicionar ao carrinho” ou se adicionamos uma ação secundária
- preservar o caminho “Comprar agora” para checkout enquanto o carrinho amadurece

## Cart Foundation Wave 5 — PDP Add-To-Cart Bridge Review

### Diagnóstico

A PDP já possui um POST funcional em `catalog.interfaces.views.ProductDetailView`.

Hoje esse POST:

- resolve o tenant da storefront
- relê o produto via `storefront_catalog_queries.get_product(...)`
- preserva seleção de variante na URL de retorno
- bloqueia produto `out_of_stock`
- cria/ativa uma `CheckoutSession` via `checkout_activation_commands.activate_from_product(...)`
- redireciona para `checkout:checkout-page`

O módulo `cart` já possui comandos de escrita suficientes para receber a intenção:

- `cart_commands.get_or_create_active_cart(...)`
- `cart_commands.add_item(...)`
- escopo obrigatório por `tenant_id`
- owner visitante por `session_key`
- rejeição explícita de produto cross-tenant

### Decisão de ponte

A primeira ponte PDP → cart deve ser feita como **ação adicional por intent explícito no POST existente da PDP**, não como substituição imediata do fluxo atual.

Contrato sugerido:

- `intent=add_to_cart`
  - usa o produto/variante já resolvido pela PDP
  - garante `request.session.session_key`
  - chama `cart_commands.add_item(tenant_id, session_key, product, quantity)`
  - redireciona para `cart:cart-page`
- `intent=buy_now` ou ausência de intent
  - preserva o comportamento atual PDP → `CheckoutSession`
  - mantém compatibilidade com testes, templates e jornadas existentes

### Racional

Essa opção é o menor corte seguro porque:

- evita criar um endpoint paralelo que duplicaria resolução de produto/variante
- mantém a PDP como dona da seleção apresentada ao cliente
- mantém `cart` como dono da mutação de carrinho
- não antecipa o handoff `Cart → CheckoutSession`
- preserva o caminho “comprar agora” enquanto o carrinho amadurece
- reduz risco de regressão no checkout atual

### Contrato multi-tenant

A execução deve manter estes guardrails:

- tenant sempre vem de `_require_storefront_tenant(request)`
- nenhuma escrita de carrinho pode ocorrer sem `tenant_id`
- `session_key` deve existir antes de chamar `cart_commands`
- `cart_commands.add_item(...)` continua responsável por bloquear produto de outro tenant
- produto `out_of_stock` não deve criar carrinho nem item
- leitura posterior em `/cart/` continua isolada por `tenant + session_key`

### UX inicial recomendada

Na primeira execução, não trocar toda a semântica da PDP de uma vez.

Recomendação:

- CTA primário: **Adicionar ao carrinho**
- CTA secundário: **Comprar agora**
- ambos podem postar a mesma seleção de variante
- cada botão envia seu próprio `intent`
- após adicionar ao carrinho, redirecionar para `/cart/`

Se quisermos reduzir ainda mais o risco visual, a execução pode manter a copy atual e apenas adicionar `intent` aos botões antes de alterar hierarquia/copy.

### Fora de escopo

Esta wave não deve implementar:

- edição de quantidade dentro de `/cart/`
- remoção de itens pela surface storefront
- aplicação de cupom
- cálculo de frete
- criação de pedido
- handoff `Cart → CheckoutSession`
- eventos de checkout ou pagamento

### Próxima wave

**Cart Foundation Wave 6 — PDP Add-To-Cart Bridge Execution**

Escopo recomendado:

- importar `cart_commands` em `catalog.interfaces.views`
- criar helper pequeno para garantir `request.session.session_key`
- ramificar `ProductDetailView.post(...)` por `intent`
- adicionar botão/intent de “Adicionar ao carrinho” no template da PDP
- redirecionar sucesso para `cart:cart-page`
- preservar o caminho atual de checkout para `buy_now`
- cobrir com testes de:
  - add-to-cart cria/atualiza carrinho tenant-scoped
  - buy-now continua criando `CheckoutSession`
  - produto sem estoque não cria item
  - tenant A não lê/adiciona item de tenant B

## Cart Foundation Wave 6 — PDP Add-To-Cart Bridge Execution

### Escopo executado

- `ProductDetailView.post(...)` passou a aceitar `intent`.
- `intent=add_to_cart` chama `cart_commands.add_item(...)`.
- ausência de intent ou `intent=buy_now` preserva PDP → `CheckoutSession`.
- o template da PDP envia `name/value` nos botões de CTA.
- o botão primário customer-facing passa a ser “Adicionar ao carrinho”.
- o botão secundário mantém “Comprar agora”.
- produto sem estoque continua sem criar carrinho nem checkout.

### Boundary preservada

- `catalog.interfaces` segue responsável por resolver a seleção da PDP.
- `cart.application.cart_commands` segue responsável pela escrita do carrinho.
- `checkout.application.checkout_activation_commands` segue responsável pelo buy-now legado.
- nenhuma regra de pedido, frete ou pagamento entra em `cart`.

### Testes cobertos

- add-to-cart cria carrinho ativo por `tenant + session_key`
- add-to-cart preserva variante selecionada
- buy-now continua criando `CheckoutSession`
- out-of-stock não cria item de carrinho

## Cart Foundation Wave 7 — Cart Quantity/Remove Storefront Mutations

### Escopo executado

A página `/cart/` deixou de ser apenas leitura e ganhou mutações mínimas:

- incrementar quantidade
- decrementar quantidade
- remover item

As mutações:

- usam POST na própria `/cart/`
- recebem `cart_id`, `item_id`, `quantity` e `item_action`
- delegam escrita para `cart_commands.update_quantity(...)` ou `cart_commands.remove_item(...)`
- redirecionam de volta para `/cart/`

### Guardrails

- a view exige tenant resolvido
- o comando filtra `cart_id` por `tenant_id`
- tentativa de mutar carrinho de outro tenant retorna sem alteração
- a tela continua sem criar pedido, frete ou pagamento

## Cart Foundation Wave 8 — Cart → Checkout Handoff Review

### Decisão de handoff

O handoff deve ser uma colaboração entre módulos, sem o `cart` criar sessão de checkout diretamente.

Contrato adotado:

1. `cart.application.cart_checkout_queries` monta um payload de checkout a partir do carrinho ativo.
2. `checkout.application.checkout_activation_commands.activate_from_cart(...)` cria a `CheckoutSession`.
3. `cart_commands.mark_converted(...)` marca o carrinho como convertido após sucesso.

### Racional

Esse desenho mantém fronteiras claras:

- `cart` conhece intenção pré-checkout e itens selecionados
- `checkout` conhece sessão, entrega, pagamento e totais finais de finalização
- `orders` continua fora do fluxo até a confirmação real do checkout

Também evita que checkout leia detalhes internos do cart diretamente ou que cart duplique regras de checkout.

## Cart Foundation Wave 9 — Cart → Checkout Handoff Execution

### Escopo executado

- criado `cart.application.cart_checkout_queries`
- adicionado `checkout_activation_commands.activate_from_cart(...)`
- adicionado `cart_commands.mark_converted(...)`
- `/cart/` ganhou POST `cart_intent=checkout`
- sucesso redireciona para `checkout:checkout-page` com `session_key`, `stage=cart` e `back_url=/cart/`
- carrinho convertido deixa de aparecer como ativo em `/cart/`

### Testes cobertos

- handoff cria `CheckoutSession` com itens e quantidades do carrinho
- carrinho é marcado como `converted`
- `converted_checkout_session_key` registra a sessão criada
- mutações storefront permanecem tenant-scoped

### Fora de escopo remanescente

- cupom/promoções
- recuperação de carrinho abandonado
- merge de carrinho visitante com customer autenticado
- estoque reservado no carrinho
- cálculo real de frete antes do checkout

### Próxima trilha sugerida

**Cart Foundation Wave 10 — Cart Promotion/Coupon Contract Review**

Objetivo:

- decidir se cupom entra primeiro como campo visual no carrinho ou como domínio `coupons`
- evitar implementar motor promocional completo cedo demais
- preservar checkout como dono da revisão final antes do pedido

## Cart Foundation Wave 10 — Cart Promotion/Coupon Contract Review

### Diagnóstico

O módulo `cart` já possui campos mínimos para promoção:

- `coupon_code`
- `discount_total`
- `subtotal`
- `total`

O módulo `coupons` existe, mas ainda está em estado skeleton:

- sem modelos ORM reais
- sem application service de validação
- sem contrato de elegibilidade
- sem testes de aplicação/remoção

Portanto, implementar “cupom real” diretamente em `/cart/` agora criaria regra promocional dentro do módulo errado.

### Decisão de contrato

A primeira evolução de cupom deve ser dividida em duas camadas:

1. **Cart captura intenção promocional**
   - exibe campo de cupom
   - guarda/remova `coupon_code`
   - mostra estado “cupom pendente/indisponível” quando ainda não há validação real
   - nunca inventa desconto

2. **Coupons valida elegibilidade**
   - recebe `tenant_id`, `coupon_code` e contexto calculável do carrinho
   - responde se o cupom é válido, inválido, expirado, não aplicável ou indisponível
   - calcula `discount_total` apenas quando houver regra formal

### Contrato futuro recomendado

Application service futuro em `coupons`:

```text
coupons.application.coupon_validation_queries.validate_cart_coupon(
    tenant_id,
    coupon_code,
    cart_snapshot,
)
```

Resposta mínima:

```text
{
  "result": "coupon-valid | coupon-invalid | coupon-expired | coupon-not-applicable | coupon-unavailable",
  "coupon_code": "...",
  "discount_total": "0.00",
  "message": "...",
}
```

Snapshot mínimo enviado por `cart`:

- `tenant_id`
- `cart_id`
- `subtotal`
- `items`
  - `product_id`
  - `product_slug`
  - `variant_sku`
  - `quantity`
  - `price_snapshot`

### Guardrails

- `cart` não deve possuir regras promocionais complexas.
- `cart` não deve validar expiração, limite de uso, segmento ou elegibilidade por produto.
- `cart` pode armazenar `coupon_code` e `discount_total` após resposta de `coupons`.
- `checkout` deve receber desconto via handoff somente se o carrinho já tiver estado validado.
- `orders` deve guardar snapshot do cupom aplicado depois da criação do pedido, não recalcular promoção.
- `payments` nunca decide promoção.

### UX recomendada para a próxima execução

Antes de existir motor promocional real, a UX mais honesta é:

- mostrar campo “Cupom” no carrinho
- permitir enviar/remover código como intenção
- exibir mensagem clara: “Validação promocional ainda não está ativa para esta loja”
- manter `discount_total` zerado
- não alterar total final

Isso prepara a surface sem criar desconto fictício.

### Fora de escopo

- criar modelo `Coupon`
- criar limites de uso
- segmentação por cliente
- desconto por categoria/produto
- cupom de frete grátis
- campanhas automáticas
- stack combinável de promoções
- analytics promocional

### Próxima wave

**Cart Foundation Wave 11 — Cart Coupon Intent Surface Execution**

Escopo recomendado:

- adicionar POST `cart_intent=apply_coupon`
- adicionar POST `cart_intent=remove_coupon`
- persistir/remover `coupon_code` no `Cart`
- manter `discount_total=0.00`
- exibir mensagem explícita de validação indisponível
- adicionar testes tenant-scoped para apply/remove

## Cart Foundation Wave 11 — Cart Coupon Intent Surface Execution

### Escopo executado

- `/cart/` ganhou formulário de cupom.
- `cart_intent=apply_coupon` salva `coupon_code` normalizado no carrinho ativo.
- `cart_intent=remove_coupon` remove `coupon_code`.
- `discount_total` permanece `0.00`.
- `total` permanece igual ao subtotal enquanto não houver validação real.
- a UI informa que validação promocional ainda não está ativa para a loja.

### Comandos adicionados

- `cart_commands.apply_coupon_intent(...)`
- `cart_commands.remove_coupon_intent(...)`

Ambos operam por:

- `tenant_id`
- `session_key`
- carrinho ativo

### Guardrails preservados

- não cria modelo `Coupon`
- não calcula desconto real
- não valida expiração ou elegibilidade
- não altera checkout, pedido ou pagamento
- não aplica cupom cross-tenant

### Testes cobertos

- salvar cupom normaliza e persiste código
- salvar cupom mantém desconto zerado
- remover cupom limpa código e desconto
- remoção cross-tenant não altera carrinho de outro tenant
- a página renderiza mensagem honesta de validação indisponível

### Próxima wave

**Cart Foundation Wave 12 — Coupon Validation Service Skeleton Review**

Objetivo:

- decidir o menor contrato real para `coupons.application`
- modelar `Coupon` somente se houver regra mínima suficiente
- manter o carrinho consumindo validação por application service, não por acesso direto ao ORM de coupons

## Cart Foundation Wave 12 — Coupon Validation Service Skeleton Review

### Decisão

O próximo passo em promoções não deve ser criar desconto real no carrinho.

Antes disso, precisamos de um contrato explícito em `coupons.application`:

```text
validate_cart_coupon(tenant_id, coupon_code, cart_snapshot)
```

`cart` continuará sendo consumidor desse contrato.

### Como cart deve consumir coupons

Ao aplicar cupom, `cart` deve:

1. montar snapshot mínimo do carrinho ativo
2. chamar `coupons.application.coupon_validation_queries`
3. interpretar result code
4. persistir desconto somente com `coupon-valid`
5. manter desconto zerado em qualquer outro resultado

### Resultados esperados

- `coupon-valid`
- `coupon-invalid`
- `coupon-expired`
- `coupon-not-applicable`
- `coupon-unavailable`

### Regra de segurança

`coupon-unavailable` deve ser o fallback conservador.

Ele permite que a UI continue honesta:

- cupom salvo como intenção
- nenhum desconto aplicado
- total preservado

### Próxima wave

**Cart Foundation Wave 13 — Coupon Validation Service Skeleton Execution**

Escopo recomendado:

- criar service skeleton em `coupons.application`
- retornar `coupon-unavailable` enquanto não há modelo real
- testar normalização, tenant obrigatório e snapshot mínimo
- plugar `cart_commands.apply_coupon_intent(...)` no service sem mudar desconto

## Cart Foundation Wave 13 — Coupon Validation Service Skeleton Execution

### Escopo executado

`cart_commands.apply_coupon_intent(...)` agora consome `coupons.application.coupon_validation_queries`.

O fluxo ficou:

1. normalizar `coupon_code`
2. obter/criar carrinho ativo por `tenant + session_key`
3. montar snapshot mínimo do carrinho
4. chamar `validate_cart_coupon(...)`
5. salvar `coupon_code`
6. manter `discount_total=0.00` enquanto o resultado não for `coupon-valid`

### Estado atual

Como `coupons` ainda não tem modelo real, a validação retorna:

- `result=coupon-unavailable`
- `reason=coupon-engine-not-configured`
- `discount_total=0.00`

### Próxima wave

**Cart Foundation Wave 14 — Coupon Model Minimal Contract Review**

Antes de aplicar desconto real, revisar se o primeiro modelo `Coupon` deve existir agora e qual recorte mínimo é seguro.

## Cart Foundation Wave 14 — Coupon Model Minimal Contract Review

### Decisão

O primeiro modelo `Coupon` pode ser criado na próxima wave, mas com escopo mínimo:

- por tenant
- código único por tenant
- status ativo/inativo
- desconto percentual ou fixo
- janela opcional de validade

`cart` não deve ser alterado para conhecer o ORM de coupons.

### Impacto esperado em cart

Depois do modelo existir, `cart_commands.apply_coupon_intent(...)` continua igual no boundary:

- monta snapshot
- chama `coupons.application`
- persiste `coupon_code`
- aplica `discount_total` somente quando recebe `coupon-valid`

### Fora de escopo mantido

- múltiplos cupons
- cupom por cliente
- cupom por categoria/produto
- frete grátis
- campanha automática
- limite de uso
- stack de promoções

### Próxima wave

**Cart Foundation Wave 15 — Coupon Model Minimal Execution**

Executar o modelo mínimo no módulo `coupons` e atualizar o validation service para retornar `coupon-valid` apenas para cupons ativos, vigentes e tenant-scoped.

## Cart Foundation Wave 15 — Coupon Model Minimal Execution

### Impacto em cart

O carrinho agora consome validação real mínima de cupom via `coupons.application`.

Com `coupon-valid`:

- `coupon_code` é salvo no carrinho
- `discount_total` é aplicado
- `total` é recalculado

Com `coupon-invalid`, `coupon-expired` ou `coupon-unavailable`:

- `coupon_code` ainda pode ficar salvo como intenção/entrada do usuário
- `discount_total` permanece `0.00`
- `total` não sofre desconto

### Guardrail

`cart` continua sem conhecer o ORM de `Coupon`.

Toda validação promocional permanece atrás de:

```text
coupons.application.coupon_validation_queries.validate_cart_coupon(...)
```

### Próxima wave

**Cart Foundation Wave 16 — Coupon Admin Lite Review**

Revisar se vale criar uma surface admin mínima de cupons antes de evoluir regras promocionais.

## Cart Foundation Wave 18 — Coupon Checkout Handoff Snapshot Review

### Decisão de cart

O carrinho deve enviar cupom aplicado ao checkout como snapshot.

Campos esperados no handoff:

- `coupon_code`
- `discount_total`
- `promotion_snapshot`

Regra:

- transportar cupom aplicado somente se `coupon_code` existir e `discount_total > 0`
- cupom salvo sem desconto não deve aparecer como aplicado no checkout

### Boundary

`cart_checkout_queries` monta o payload.

`checkout_activation_commands.activate_from_cart(...)` persiste o snapshot recebido.

Checkout não recalcula promoção nesta etapa.

### Próxima wave

**Cart Foundation Wave 19 — Coupon Checkout Handoff Snapshot Execution**

Adicionar campos mínimos em `CheckoutSession` e transportar snapshot promocional no handoff.

## Cart Foundation Wave 19 — Coupon Checkout Handoff Snapshot Execution

### Executado no handoff

`cart_checkout_queries` agora inclui snapshot promocional quando o carrinho possui cupom aplicado com desconto real.

Campos enviados:

- `coupon_code`
- `discount_total`
- `promotion_snapshot`

Cupom inválido/salvo sem desconto não é transportado como aplicado.

### Próxima wave

**Cart Foundation Wave 20 — Coupon Order Snapshot Review**

Revisar propagação do snapshot promocional do checkout para pedido.

## Cart Reliability Wave 1 — Cart Session Idempotency Review

### Diagnóstico

O carrinho já possui guardrails estruturais:

- `Cart` ativo único por `(tenant, customer)` quando há customer;
- `Cart` ativo único por `(tenant, session_key)` quando há sessão anônima;
- mutações tenant-scoped;
- `add_item(...)` usa lock no cart e no item existente;
- itens são consolidados por `variant_sku`.

### Semântica atual

Add-to-cart é acumulativo:

```text
add SKU A quantity 1
add SKU A quantity 1
= SKU A quantity 2
```

Isso é correto para cliques intencionais repetidos, mas não é idempotente por request.

Riscos:

- double-submit do browser;
- retry de rede;
- POST duplicado por HTMX/Alpine;
- usuário clicando duas vezes rapidamente;
- replay da mesma request.

### Decisão

Não mudar a semântica acumulativa padrão nesta wave.

O contrato deve separar:

- add acumulativo sem chave de idempotência;
- replay protection com `idempotency_key` explícita.

### Execução recomendada

Adicionar chave opcional:

```text
cart_commands.add_item(..., idempotency_key="")
```

Comportamento:

- sem chave: mantém comportamento atual acumulativo;
- com chave já consumida no mesmo tenant/cart: retorna sem nova mutação;
- storage deve ser tenant-scoped;
- identidade do item continua baseada em `variant_sku`.

### Modelo futuro mínimo

```text
CartMutation
- tenant
- cart
- mutation_key
- mutation_type: add_item
- result_snapshot
- created_at
```

Constraint:

```text
unique(tenant, cart, mutation_key)
```

### Fora de escopo

- substituir add acumulativo;
- limite de estoque no cart;
- merge de carts anônimo/customer;
- expiração de cart;
- replay protection global;
- mudanças no checkout handoff.

### Próxima wave

**Cart Reliability Wave 2 — Add-To-Cart Idempotency Execution**

Implementar idempotency key opcional no add-to-cart, com storage mínimo de mutação e testes de double-submit por tenant/session.

## Cart Reliability Wave 2 — Add-To-Cart Idempotency Execution

### Escopo executado

- criado `CartMutation` como storage tenant-scoped de mutações idempotentes;
- criada migration `0002_cartmutation`;
- `cart_commands.add_item(...)` passou a aceitar `idempotency_key`;
- o PDP renderiza `cart_idempotency_key` hidden;
- POST `intent=add_to_cart` envia a chave para `cart.application`;
- double-submit com a mesma chave retorna sem nova mutação.

### Semântica implementada

Sem chave:

```text
add SKU A quantity 1
add SKU A quantity 1
= quantity 2
```

Com mesma chave:

```text
add SKU A quantity 1 key X
add SKU A quantity 1 key X
= quantity 1
```

Com chave diferente:

```text
add SKU A quantity 1 key X
add SKU A quantity 1 key Y
= quantity 2
```

### Result code

Replay idempotente retorna:

```text
cart-item-added-idempotent
```

O snapshot retornado representa o resultado original da mutação.

### Boundary preservada

- idempotência pertence ao domínio `cart`;
- PDP apenas fornece a chave;
- checkout handoff não foi alterado;
- add acumulativo continua sendo o comportamento padrão sem chave.

### Próxima wave

**Cart Reliability Wave 3 — Cart Quantity/Stock Guard Review**

Revisar se o carrinho já deve limitar quantidade por estoque disponível ou apenas deixar o checkout bloquear inconsistências.

## Cart Reliability Wave 3 — Cart Quantity/Stock Guard Review

### Diagnóstico

O carrinho já protege consistência estrutural de sessão, tenant e idempotência, mas ainda não valida quantidade contra estoque disponível.

Hoje existem três camadas diferentes:

- PDP bloqueia intenção obvious de compra quando a vitrine já sinaliza produto sem estoque;
- `cart.application` aceita `add_item(...)` e `update_quantity(...)` usando apenas normalização segura de quantidade;
- `checkout.application` faz a validação autoritativa de estoque antes de concluir o pedido.

Isso deixa uma janela aceitável para MVP, mas ruim para experiência:

- usuário pode aumentar quantidade no carrinho acima do estoque livre;
- o erro real aparece tarde, apenas no checkout;
- double-submit já está protegido por idempotência, mas quantidade excessiva ainda é intenção tecnicamente válida no cart.

### Decisão

Adicionar uma guarda leve de estoque no carrinho em uma wave de execução própria.

O carrinho deve prevenir quantidades obviamente impossíveis, mas não deve virar dono de inventário.

Contrato:

- resolver disponibilidade por `tenant_id + variant_sku`;
- respeitar `ProductVariant.track_inventory`;
- permitir backorder quando `ProductVariant.allow_backorder=True`;
- calcular estoque livre como `stock - reserved_stock`;
- bloquear ou ajustar quantidade quando a intenção exceder estoque livre;
- manter o checkout como bloqueio final contra corrida de estoque.

### Boundary

`catalog` continua dono da disponibilidade do `ProductVariant`.

`cart` pode consultar o estado mínimo necessário para validar uma intenção de quantidade, mas não pode:

- reservar estoque;
- decrementar estoque;
- criar pedido;
- decidir frete ou pagamento;
- substituir a validação final de checkout.

### Resultado esperado

`cart_commands.add_item(...)` deve considerar a quantidade já existente no item antes de aceitar novo incremento.

`cart_commands.update_quantity(...)` deve validar a quantidade final desejada.

Estados recomendados:

- `cart-item-added` para sucesso normal;
- `cart-item-updated` para sucesso normal;
- `cart-item-stock-conflict` quando a quantidade solicitada excede estoque livre;
- `cart-item-stock-unavailable` quando o SKU não pode mais ser comprado;
- `cart-item-added-idempotent` permanece reservado para replay protegido por chave.

### Fora de escopo

- reservation engine;
- decremento de estoque;
- mudança em `reserved_stock`;
- expiração de carrinho;
- política avançada de backorder;
- revalidação promocional;
- mudança no handoff cart → checkout;
- mudança em eventos de pedido ou pagamento.

### Próxima wave

**Cart Reliability Wave 4 — Cart Quantity/Stock Guard Execution**

Implementar a guarda leve em `cart.application`, com testes de add/update acima do estoque, backorder permitido e estoque não rastreado.

## Cart Reliability Wave 4 — Cart Quantity/Stock Guard Execution

### Escopo executado

`cart.application` agora aplica guarda leve de estoque antes de persistir quantidade.

Fluxos cobertos:

- `add_item(...)` valida a quantidade final considerando item já existente;
- `update_quantity(...)` valida a quantidade final solicitada;
- SKU inexistente no tenant retorna indisponibilidade explícita;
- produto inativo ou não comprável retorna indisponibilidade explícita;
- inventário não rastreado continua permitido;
- backorder permitido continua permitido;
- idempotency replay continua retornando o snapshot original sem recalcular mutação.

### Result codes

Novos estados de bloqueio:

```text
cart-item-stock-conflict
cart-item-stock-unavailable
```

Ambos retornam:

- `variant_sku`;
- `requested_quantity`;
- `available_quantity`;
- snapshot do carrinho ativo quando já existe cart.

### UX

As superfícies storefront passam a exibir mensagem via flash quando a guarda bloqueia a intenção:

- PDP `add_to_cart`;
- incremento/decremento em `/cart/`.

O carrinho não ajusta quantidade automaticamente nesta wave.

Quando a intenção excede estoque, a quantidade anterior é preservada.

### Boundary preservada

`cart` consulta disponibilidade mínima do `ProductVariant`, mas não:

- reserva estoque;
- altera `reserved_stock`;
- baixa estoque;
- cria pedido;
- substitui a validação final do checkout.

`checkout.application` continua sendo a autoridade final contra corrida de estoque no momento de concluir a compra.

### Testes cobertos

- add acima do estoque livre retorna conflito;
- update acima do estoque livre retorna conflito;
- add considera quantidade já existente antes de validar;
- SKU inexistente no tenant retorna indisponível;
- estoque não rastreado permite quantidade alta;
- backorder permite quantidade alta;
- idempotency key continua escopada por tenant/cart.

### Próxima wave

**Cart Reliability Wave 5 — Cart Checkout Stock Revalidation UX Review**

Revisar se o checkout precisa devolver um payload mais amigável para reconciliar itens quando a guarda leve do cart passou, mas o estoque mudou antes da conclusão.

## Cart Reliability Wave 5 — Cart Checkout Stock Revalidation UX Review

### Diagnóstico

A Wave 4 reduziu erro óbvio no carrinho, mas não elimina corrida de estoque.

O fluxo atual fica assim:

1. cliente adiciona item ao carrinho;
2. `cart.application` valida estoque livre naquele instante;
3. carrinho faz handoff para `CheckoutSession`;
4. outro fluxo pode consumir ou reservar estoque;
5. `checkout.application` revalida inventário antes de criar pedido;
6. se houver conflito, o pedido não nasce.

Esse desenho está correto para consistência.

O ponto fraco agora é UX de recuperação:

- `checkout-completion-stock-conflict` já aparece como resultado explícito;
- a taxonomy classifica como `inventory`;
- há recovery copy para retomar com segurança;
- porém o payload ainda não informa qual item conflitou, SKU afetado, quantidade solicitada e estoque livre atual.

### Decisão

Não remover a revalidação final do checkout.

O próximo ganho deve ser enriquecer o resultado de conflito com um payload reconciliável por item.

Contrato recomendado:

```text
checkout-completion-stock-conflict
```

com detalhes estruturados:

```text
inventory_conflicts[]
- variant_sku
- title
- requested_quantity
- available_quantity
- reason
```

### UX recomendada

Quando houver conflito no checkout:

- manter o pedido não criado;
- mostrar o item afetado;
- explicar que o estoque mudou depois do carrinho;
- oferecer ação primária para revisar a sessão atual quando ainda houver quantidade disponível;
- oferecer ação para voltar ao produto quando o item ficou indisponível;
- nunca ajustar quantidade silenciosamente sem confirmação do cliente.

### Boundary

`cart` continua dono da intenção pré-checkout.

`checkout` continua dono da revisão final e da criação do pedido.

`catalog` continua dono da disponibilidade de `ProductVariant`.

Uma eventual reconciliação deve operar por application service explícito, sem `checkout` escrever estoque ou sem `cart` criar pedido.

### Fora de escopo

- reserva de estoque no carrinho;
- decremento de estoque antes de pagamento;
- ajuste automático de quantidade no checkout;
- criação parcial de pedido;
- refund/cancelamento;
- payment retry;
- eventos novos de inventário.

### Próxima wave

**Cart Reliability Wave 6 — Checkout Inventory Conflict Payload Execution**

Enriquecer a revalidação final do checkout para retornar conflitos por item e renderizar uma mensagem de recuperação mais acionável na página de checkout.

## Cart Reliability Wave 6 — Checkout Inventory Conflict Payload Execution

### Escopo executado

O checkout agora expõe detalhes por item quando a conclusão falha por conflito de estoque.

O payload é recalculado no GET pós-redirect a partir de:

- `CheckoutSession`;
- `CheckoutSessionItem`;
- `ProductVariant` tenant-scoped atual.

Isso evita migration e mantém o erro como uma leitura de recuperação, não como novo estado persistido.

### Payload

`checkout_completion_commands.get_inventory_conflicts(...)` retorna:

```text
inventory_conflicts[]
- variant_sku
- title
- requested_quantity
- available_quantity
- reason
```

Reasons iniciais:

- `stock-conflict`;
- `inventory-unavailable`;
- `inventory-link-missing`.

### UX executada

Quando `result=checkout-completion-stock-conflict`:

- a página mostra “Itens que precisam de revisão”;
- cada item afetado exibe SKU, quantidade solicitada e quantidade disponível;
- a ação primária passa a ser “Reabrir checkout”;
- “Voltar ao produto” fica como ação secundária;
- nenhum pedido é criado;
- nenhuma quantidade é ajustada automaticamente.

### Taxonomy

`checkout-completion-stock-conflict` permanece na família `inventory`, mas agora aponta para:

```text
recovery_action=review_current_session
```

Isso diferencia conflito reconciliável de item indisponível definitivo.

### Boundary preservada

`checkout` apenas lê disponibilidade atual para explicar a falha de conclusão.

Não houve:

- reserva de estoque;
- decremento;
- pedido parcial;
- alteração silenciosa de quantidade;
- novo evento de domínio;
- mudança no handoff cart → checkout.

### Próxima wave

**Cart Reliability Wave 7 — Checkout Inventory Reconciliation Action Review**

Revisar se a próxima ação deve permitir reduzir quantidade/remover item diretamente a partir do estado de conflito, reaproveitando os commands existentes de mutação da sessão.

## Cart Reliability Wave 7 — Checkout Inventory Reconciliation Action Review

### Diagnóstico

A Wave 6 tornou o conflito final de estoque explicável por item.

O checkout já possui base para reconciliação:

- `checkout_session_commands.mutate_item(...)`;
- operações existentes: `increment`, `decrement`, `remove`;
- recalculadora de subtotal/frete/total após mutação;
- redirect com result code e stage;
- UI de itens já renderiza `mutation_actions` quando a sessão está aberta.

Isso significa que a próxima evolução não precisa criar um novo domínio.

### Decisão

A reconciliação de estoque deve começar reaproveitando mutações da própria `CheckoutSession`.

Menor contrato seguro:

- adicionar uma ação explícita para reduzir item conflitado até o estoque livre atual;
- se `available_quantity == 0`, oferecer remoção explícita do item;
- recalcular totais da sessão após a mutação;
- manter o pedido bloqueado até nova tentativa de conclusão;
- não ajustar quantidade automaticamente durante o GET de conflito.

### Ação recomendada

Novo operation code em `checkout_session_commands.mutate_item(...)`:

```text
set_quantity
```

Payload mínimo:

```text
session_key
item_id
operation=set_quantity
quantity=<available_quantity>
```

Result codes recomendados:

```text
checkout-item-updated
checkout-item-removed
checkout-item-session-empty
checkout-item-mutation-unavailable
```

Não é necessário criar result code novo enquanto a mutação continuar equivalente a uma correção manual de quantidade.

### UX recomendada

No bloco “Itens que precisam de revisão”:

- quando `available_quantity > 0`, exibir CTA “Reduzir para N disponível(is)”;
- quando `available_quantity == 0`, exibir CTA “Remover item indisponível”;
- manter “Reabrir checkout” como caminho principal de revisão geral;
- manter “Voltar ao produto” como alternativa.

### Boundary

`checkout` pode alterar a própria `CheckoutSession`.

`checkout` não pode:

- reservar estoque;
- decrementar estoque;
- criar pedido parcial;
- recalcular disponibilidade em `cart`;
- alterar `Cart` convertido;
- aplicar promoção nova durante a reconciliação.

`catalog` continua dono do estoque atual.

### Fora de escopo

- ajuste automático sem clique;
- split de pedido;
- substituição por outro SKU;
- recomendação de produtos alternativos;
- atualização de cupom/desconto;
- evento de domínio novo;
- refund/pagamento.

### Próxima wave

**Cart Reliability Wave 8 — Checkout Inventory Reconciliation Action Execution**

Implementar `set_quantity`/remoção a partir do bloco de conflito, com testes de redução para disponível, remoção quando indisponível e recálculo de totais.

## Cart Reliability Wave 8 — Checkout Inventory Reconciliation Action Execution

### Escopo executado

A página de checkout agora permite reconciliar conflito final de estoque a partir do próprio bloco de itens afetados.

Foi adicionado:

- `item_id` no payload `inventory_conflicts`;
- operação `set_quantity` em `checkout_session_commands.mutate_item(...)`;
- CTA “Reduzir para N disponível(is)” quando ainda há estoque livre;
- CTA “Remover item indisponível” quando `available_quantity == 0`;
- recálculo de subtotal, frete, parcelas e total após a mutação.

### Semântica

O GET de conflito continua somente leitura.

A sessão só muda quando o cliente confirma explicitamente uma ação via POST.

Depois da mutação:

- a sessão permanece `open`;
- nenhum pedido é criado;
- nenhuma reserva ou baixa de estoque acontece;
- o cliente precisa tentar concluir novamente.

### Result codes preservados

As ações reutilizam os result codes existentes:

```text
checkout-item-updated
checkout-item-removed
checkout-item-session-empty
checkout-item-mutation-unavailable
```

Isso mantém a reconciliação como uma mutação normal da sessão, não como novo subfluxo transacional.

### Boundary preservada

`checkout` altera apenas `CheckoutSession` e `CheckoutSessionItem`.

`catalog` continua dono do estoque.

`orders` não recebe pedido parcial.

`cart` convertido não é reaberto nem modificado.

### Testes cobertos

- conflito renderiza CTA de redução quando `available_quantity > 0`;
- `set_quantity` reduz item ao disponível e recalcula totais;
- conflito renderiza CTA de remoção quando `available_quantity == 0`;
- remoção recalcula totais e mantém sessão sem pedido;
- payload de conflito inclui `item_id`.

### Próxima wave

**Cart Reliability Wave 9 — Checkout Revalidation After Reconciliation Review**

Revisar se, após uma reconciliação, a UX deve permanecer na etapa atual com feedback suficiente ou abrir automaticamente uma nova tentativa guiada de conclusão.

## Cart Reliability Wave 9 — Checkout Revalidation After Reconciliation Review

### Diagnóstico

A Wave 8 já permite corrigir conflito final de estoque dentro do checkout:

- reduzir quantidade para estoque disponível;
- remover item indisponível;
- recalcular totais;
- manter a sessão aberta;
- voltar para a etapa atual após redirect.

O comportamento atual é seguro: depois da reconciliação, a página permanece no checkout e o cliente pode tentar concluir novamente.

O ponto fraco é semântico:

- `checkout-item-updated` usa copy genérica de item atualizado;
- `checkout-item-removed` usa copy genérica de item removido;
- a tela não diferencia “edição comum” de “reconciliação após conflito de estoque”;
- não existe indicação explícita de que a próxima tentativa de conclusão fará nova revalidação final.

### Decisão

Não fazer revalidação automática nem conclusão automática depois da reconciliação.

Após reduzir/remover item, o sistema deve:

- manter o cliente na etapa `review` quando ela continuar válida;
- mostrar feedback específico de reconciliação;
- deixar o CTA de conclusão disponível;
- exigir novo clique em “Criar pedido inicial”;
- rodar a revalidação final normal no novo POST de conclusão.

### Justificativa

A reconciliação muda itens e totais.

Criar pedido automaticamente logo após a correção seria surpreendente, especialmente quando:

- subtotal mudou;
- frete/parcelas podem ter sido recalculados;
- cupom aplicado pode ficar semanticamente desatualizado em uma fase futura;
- estoque ainda pode mudar novamente antes do novo clique.

O clique explícito preserva confiança e mantém o pedido como decisão final do cliente.

### Contrato recomendado

Adicionar result codes específicos para reconciliação:

```text
checkout-inventory-reconciled
checkout-inventory-item-removed
```

Esses códigos podem continuar usando a mesma mutação interna de `CheckoutSession`, mas permitem copy diferente:

- “Ajustamos este item ao estoque disponível. Revise os novos totais e tente concluir novamente.”
- “Removemos o item indisponível. Revise os novos totais antes de criar o pedido.”

### Boundary

`checkout` pode:

- ajustar a própria sessão;
- recalcular totais;
- pedir confirmação final do cliente.

`checkout` não deve:

- disparar conclusão automática após reconciliação;
- criar pedido parcial;
- reservar estoque;
- revalidar cupom fora do boundary de `coupons`;
- reabrir `Cart` convertido.

### Fora de escopo

- motor de reserva;
- revalidação promocional;
- sugestão de produtos alternativos;
- substituição automática de SKU;
- split de pedido;
- pagamento automático.

### Próxima wave

**Cart Reliability Wave 10 — Checkout Reconciliation Feedback Execution**

Adicionar result codes/copy específicos para reconciliação de estoque, mantendo a conclusão final como novo clique explícito do cliente.

## Cart Reliability Wave 10 — Checkout Reconciliation Feedback Execution

### Escopo executado

A reconciliação de estoque agora possui feedback próprio, separado de mutações comuns de item.

Foram adicionados:

- flag POST `inventory_reconciliation=1` nos CTAs do bloco de conflito;
- result code `checkout-inventory-reconciled` para redução até estoque disponível;
- result code `checkout-inventory-item-removed` para remoção de item indisponível;
- taxonomy `inventory/success/review_current_session`;
- copy específica orientando revisar novos totais e tentar criar o pedido novamente.

### Semântica

Mutação comum continua usando:

```text
checkout-item-updated
checkout-item-removed
```

Reconciliação de conflito usa:

```text
checkout-inventory-reconciled
checkout-inventory-item-removed
```

Isso mantém a mesma mecânica interna de `CheckoutSession`, mas diferencia a experiência de recuperação para o cliente.

### UX

Depois de reconciliar:

- a sessão permanece aberta;
- a etapa atual é preservada;
- os totais já estão recalculados;
- o pedido ainda não é criado;
- o cliente precisa clicar novamente em “Criar pedido inicial”.

### Boundary preservada

`checkout` altera somente a própria sessão.

Não houve:

- conclusão automática;
- pedido parcial;
- reserva de estoque;
- baixa de estoque;
- alteração em `Cart` convertido;
- novo evento de domínio.

### Testes cobertos

- redução por reconciliação retorna `checkout-inventory-reconciled`;
- remoção por reconciliação retorna `checkout-inventory-item-removed`;
- feedback de reconciliação aparece na página;
- taxonomy classifica ambos como `inventory` com `review_current_session`;
- mutações comuns continuam separadas por result code.

### Próxima wave

**Cart Reliability Wave 11 — Cart/Checkout Reliability Closure Review**

Revisar se a trilha de confiabilidade do carrinho já atingiu suficiência para fechar o ciclo ou se ainda resta risco relevante antes de migrar para próxima abordagem.

## Cart Reliability Wave 11 — Cart/Checkout Reliability Closure Review

### Escopo revisado

A trilha de confiabilidade cobriu o caminho crítico:

- proteção contra double-submit no add-to-cart;
- idempotency key explícita;
- guarda leve de quantidade no carrinho;
- preservação da semântica acumulativa normal;
- revalidação final de estoque no checkout;
- payload por item em conflito final;
- reconciliação explícita dentro da `CheckoutSession`;
- feedback específico após reconciliação;
- revalidação final obrigatória antes de criar pedido.

### Decisão de prontidão

**Go técnico para encerrar a trilha Cart Reliability.**

O sistema agora possui camadas coerentes:

1. PDP bloqueia intenção obviamente indisponível;
2. cart bloqueia quantidade obviamente impossível;
3. checkout revalida antes de criar pedido;
4. conflito final é explicável por item;
5. cliente pode corrigir a sessão;
6. pedido só nasce após novo clique explícito.

### Riscos restantes aceitos

Ainda não há:

- reserva de estoque no carrinho;
- decremento de estoque após pagamento confirmado;
- hold/timeout de inventário;
- substituição automática por SKU alternativo;
- revalidação promocional após mudança de itens;
- analytics específico de reconciliação de inventário além dos result codes.

Esses pontos são aceitáveis para este estágio porque:

- checkout ainda bloqueia criação de pedido inconsistente;
- nenhuma baixa de estoque é feita cedo demais;
- nenhum pedido parcial é criado;
- o cliente sempre confirma novamente depois de mudança de itens/totais.

### No-Go para continuar refinando agora

Não vale continuar nesta trilha imediatamente.

As próximas melhorias aqui já entram em escopos maiores:

- reservation engine;
- inventory allocation;
- pagamento real;
- baixa de estoque pós-pagamento;
- analytics operacional de inventário.

Esses temas devem nascer em trilha própria, não como continuação incremental de cart reliability.

### Próxima abordagem recomendada

**Checkout/Payment Execution Foundation** ou **Inventory Fulfillment Foundation**.

Recomendação de ROI:

1. se o objetivo é fechar funil de receita: seguir para **Checkout/Payment Execution Foundation**;
2. se o objetivo é robustez operacional pós-compra: seguir para **Inventory Fulfillment Foundation**.

Como o carrinho já entrega intenção, promoção, handoff, pedido e recovery de estoque, o melhor próximo eixo de produto tende a ser:

**Checkout/Payment Execution Foundation — pagamento real, confirmação e baixa de estoque pós-pagamento.**

## Storefront Conversion Optimization Wave 1 — Cart-to-Checkout Friction Review

### Módulo responsável

O módulo responsável pelo primeiro recorte é `cart`, porque a maior fricção customer-facing restante está no momento em que o cliente decide sair do carrinho e iniciar checkout.

Integrações envolvidas:

- `catalog`, que alimenta produto/variante/preço;
- `coupons`, que valida desconto;
- `checkout`, que cria a sessão finalizável;
- `orders`, que só deve nascer depois de frete e pagamento.

### Diagnóstico

O carrinho já é funcional:

- lista itens da sessão;
- permite incrementar, reduzir e remover;
- aceita cupom;
- faz handoff para checkout;
- preserva snapshot promocional válido;
- não cria pedido cedo demais.

Ainda havia uma fricção de confiança:

- a página dizia que frete/pagamento continuam no checkout, mas isso ficava apenas como nota;
- o CTA “Ir para checkout” não explicava claramente o que acontece a seguir;
- o cliente podia confundir checkout com criação imediata de pedido;
- não havia um bloco compacto de readiness antes da transição.

### Decisão

**Go para microcopy estruturada de próximo passo seguro no carrinho.**

**No-Go para reescrever checkout, criar wizard novo, adicionar tracking client-side ou alterar regra de criação de pedido.**

## Storefront Conversion Optimization Wave 2 — Cart Safe Next-Step Execution

### Execução

Foi adicionado ao carrinho um bloco “Próximo passo seguro”.

O bloco explicita:

- itens ainda podem ser revisados;
- frete será escolhido no checkout;
- pedido ainda não foi criado;
- a compra só nasce após confirmação explícita.

### Boundary preservada

- `cart.application.cart_page_queries` monta os sinais de apresentação;
- o template apenas renderiza os itens;
- nenhuma regra de checkout foi movida para cart;
- nenhuma mutation nova foi criada;
- nenhum evento novo foi emitido;
- nenhum pedido é criado no carrinho.

### Testes

Foi adicionada cobertura para garantir que a página de carrinho ativa exibe:

- “Próximo passo seguro”;
- orientação de readiness;
- “Itens revisáveis”;
- “Frete no checkout”;
- “Pedido ainda não criado”.

## Storefront Conversion Optimization Wave 3 — Approach Closure Review

### Resultado

A abordagem entregou uma melhoria customer-facing de baixo risco no ponto de transição carrinho → checkout.

### Decisão de encerramento

**Go para encerrar Storefront Conversion Optimization neste ponto.**

O ganho desta abordagem está em reduzir ambiguidade antes do checkout, não em criar mais uma camada de fluxo.

### No-Go deliberado

Não avançar agora para:

- redesign completo do checkout;
- sticky CTA;
- tracking client-side;
- cross-sell no carrinho;
- recomendação personalizada;
- cálculo de frete no carrinho;
- criação antecipada de pedido;
- reserva de estoque no carrinho.

### Próxima abordagem recomendada

**Shipping Quote & Delivery Promise Review**

Revisar se já vale antecipar uma promessa de entrega no carrinho/PDP sem quebrar a regra de que o frete final é escolhido no checkout.

## Shipping Quote & Delivery Promise Wave 1 — Pre-Checkout Promise Review

### Módulo responsável

`shipping` é responsável pelo contrato de promessa de entrega.

`cart` pode consumir uma leitura de apresentação por application service, mas não deve calcular frete final nem decidir método de envio.

### Diagnóstico

O checkout já possui métodos de entrega padrão:

- entrega padrão;
- entrega expressa;
- preço estimado;
- prazo estimado.

O carrinho, porém, ainda dizia apenas que frete continuava no checkout.

Isso preservava a regra correta, mas deixava pouca antecipação de valor para o cliente.

### Decisão

**Go para promessa pré-checkout honesta.**

**No-Go para quote real no carrinho.**

O carrinho pode exibir opções de entrega como prévia, desde que:

- deixe claro que a escolha final acontece no checkout;
- deixe claro que valores/prazos dependem do endereço;
- não persista frete;
- não altere total;
- não crie pedido;
- não reserve envio.

## Shipping Quote & Delivery Promise Wave 2 — Cart Delivery Promise Execution

### Execução

Foi criado `shipping.application.delivery_promise_queries`.

O service entrega uma promessa pré-checkout:

- título;
- descrição;
- opções de entrega padrão/expressa;
- preço como “a partir de”;
- nota explícita de dependência do endereço.

O carrinho passou a renderizar o bloco “Entrega no próximo passo”.

### Boundary preservada

- `shipping` define o contrato de promessa.
- `cart` apenas consome e apresenta.
- `checkout` continua dono da seleção final de frete.
- `orders` continua recebendo frete apenas após checkout.

### Testes

Coberto:

- service não retorna promessa sem tenant;
- service explicita checkout e dependência do endereço;
- carrinho renderiza a promessa sem alterar total ou handoff.

## Shipping Quote & Delivery Promise Wave 3 — Approach Closure Review

### Resultado

A abordagem entregou antecipação de promessa de entrega sem transformar o carrinho em calculadora de frete.

### Decisão de encerramento

**Go para encerrar Shipping Quote & Delivery Promise neste ponto.**

O ganho de conversão vem da clareza de “o que vem depois”, não de antecipar regra logística final.

### No-Go deliberado

Não avançar agora para:

- quote por CEP no carrinho;
- integração de frete em tempo real;
- persistência de frete no `Cart`;
- frete grátis;
- SLA por região;
- reserva logística;
- split shipment;
- cálculo de impostos/frete no PDP.

### Próxima abordagem recomendada

**Checkout Delivery Method Hardening Review**

Revisar se a escolha de entrega dentro do checkout já está suficientemente validada, clara e consistente com totais antes de evoluir para cotação real por CEP.
