# Module Boundaries — Hubx Market

Este documento define as **fronteiras entre módulos** do Hubx Market.

O objetivo é evitar acoplamento indevido, preservar a arquitetura modular e garantir que o sistema não evolua para um monólito desorganizado.

---

# Objetivos

Este documento serve para:

- definir responsabilidades por módulo
- definir o que cada módulo pode acessar
- definir o que cada módulo não deve acessar
- orientar contribuidores e agentes de IA
- reduzir acoplamento entre domínios

---

# Regra geral

Cada módulo deve ter uma **responsabilidade clara**.

A comunicação entre módulos deve acontecer preferencialmente por:

- `application/`
- serviços explícitos
- contratos claros
- eventos internos quando necessário

Evitar:

- importar detalhes internos arbitrários de outros módulos
- espalhar lógica de negócio entre módulos
- acessar diretamente `models.py` de outro módulo sem necessidade real e sem contrato

## Contrato de contexto de tenant

Para módulos tenant-owned (`catalog`, `customers`, `checkout`, `orders`, `payments` e superfícies logadas correlatas):

- query services e command services devem aceitar `tenant_id` explícito sempre que operarem sobre dados da loja
- a camada `interfaces/` deve repassar `request.tenant.id` quando o tenant já estiver resolvido
- services não devem depender de “primeiro registro”, “perfil ativo global” ou leitura implícita cross-tenant quando o contexto já estiver disponível
- fallback sem `tenant_id` só é aceitável em superfícies legadas ou operacionais onde essa compatibilidade já seja contrato explícito

Objetivo:

- reduzir ambiguidade entre módulos
- evitar leitura ou escrita na loja errada
- tornar o fluxo multi-tenant mais previsível para evolução futura

### Compatibilidade legada aceitável neste estágio

Ainda é aceitável tolerar ausência de `tenant_id` apenas quando **todas** as condições abaixo forem verdadeiras:

- a surface é primariamente de leitura
- a ausência de tenant já é parte do contrato legado atual
- não existe risco relevante de escrita cross-tenant
- o resultado pode ser tratado como fallback operacional ou demo, não como verdade forte do domínio

Exemplos aceitáveis por enquanto:

- superfícies de `accounts` que ainda servem login, overview ou customer area em modo legado/global
- listas e detalhes administrativos em modo global, quando a request ainda não estiver tenant-scoped
- fallbacks controlados de apresentação documentados explicitamente como compatibilidade temporária

### Compatibilidade legada que já não deve continuar

Não é mais aceitável tolerar ausência de `tenant_id` em:

- commands de `checkout`
- commands de `orders`
- commands de `payments`
- fluxos de retomada de compra (`reorder`, `payment retry`, hosted payment)
- qualquer write path que resolva entidades tenant-owned por identificadores como `order_number`, `attempt_key`, `slug` ou equivalentes

Nesses casos, o comportamento esperado passa a ser:

- falhar fechado
- responder indisponibilidade segura
- registrar breadcrumb/log suficiente para troubleshooting

### Candidatas de aposentadoria prioritária

Depois do hardening atual, as tolerâncias globais que mais parecem maduras para aposentadoria são:

1. `accounts.application.account_page_queries`
   - `FallbackAccountProfileRepository`
   - overview/login/register/forgot ainda conseguem responder com perfil demo/global
   - melhor candidato inicial para virar estado explícito de ausência ou onboarding controlado por tenant
   - risco menor por ser majoritariamente leitura e não carregar CRUD sensível da conta

2. `accounts.application.account_customer_area_queries`
   - fallback global de perfil/área do cliente ainda existe quando não há tenant resolvido
   - como a customer area já é semanticamente tenant-owned, esse modo legado continua candidato forte
   - mas a retirada completa ainda não é a próxima mais segura porque junta muitas superfícies de leitura e empty states numa única mudança
   - a decomposição segura agora fica:
     1. retirar fallback global de perfil
     2. retirar fallback global de endereços
     3. retirar fallback global de pedidos
     4. só então revisar a aposentadoria residual do modo global da customer area inteira
   - a etapa 1 já foi aplicada; o fallback global de perfil saiu da customer area, enquanto pedidos e endereços continuam preservados por compatibilidade
   - a revisão seguinte indica que a etapa 2 já parece madura:
     - `get_addresses_page_data()` é isolado
     - o template já possui empty state explícito
     - a continuidade da conta não depende de endereço fixture para permanecer compreensível
   - a etapa 2 já foi aplicada; a customer area deixa de usar fallback global de endereços e passa a expor vazio explícito quando não houver persistência real
   - a revisão do eixo de pedidos indica que a etapa 3 ainda não deve sair inteira de uma vez:
     - `orders list` e `order detail` já carregam continuidade, recovery e ações reais demais
     - a próxima decomposição segura deve separar primeiro a lista do detalhe
   - a revisão específica da lista mostrou que `get_orders_page_data()` já parece madura para ser o próximo corte seguro:
     - é primariamente leitura
     - o template já aceita empty state explícito
     - o maior risco operacional continua concentrado no detalhe
   - com isso, a ordem segura neste ponto fica:
     1. aposentar primeiro o fallback global da **lista de pedidos**
     2. manter o **detalhe do pedido** como último corte desse eixo
   - essa primeira retirada de `orders` já foi aplicada na lista:
     - `get_orders_page_data()` e `AccountOrdersView` deixam de reaproveitar fixture global
     - ausência de histórico na lista agora vira `missing` + empty state honesto
     - o detalhe continua preservando compatibilidade legada por concentrar recovery e ações reais
   - a revisão específica do detalhe reforçou essa classificação:
     - `get_order_detail_page_data()` ainda funciona como boundary de continuidade e recovery, não só como leitura simples
     - hosted payment, retry, reorder, confirmação inicial e trilha operacional ainda passam por essa mesma superfície
     - por isso, a aposentadoria do fallback global no detalhe ainda não é o próximo corte seguro
   - a decomposição segura do detalhe agora deve seguir camadas:
     1. leitura base do detalhe
     2. handoff/`confirmation_mode` do checkout
     3. capability de `reorder lite`
     4. bloco de recovery e pagamento
     5. só então a retirada residual do fallback global
   - a revisão da primeira camada mostrou que “leitura base” precisa ser tratada como **payload estrutural do pedido**, não como toda a copy do detalhe
   - entram primeiro:
     - resumo principal
     - status atual
     - itens e totais
     - timeline básica do pedido
   - ficam fora desse primeiro subcorte:
     - `page_description`, `page_meta`, `summary_subtitle`, `summary_note`
     - `confirmation_mode`
     - CTAs e sinais de `payments`
     - alerts de pending/drift/recovery
   - o plano seguro para implementar essa primeira camada é:
     1. extrair primeiro o payload estrutural para um bloco isolado
     2. manter o contrato atual do template
     3. deixar copy enriquecida, CTAs e sinais operacionais na camada residual
     4. só depois revisar se a leitura estrutural já consegue viver sem fallback global
   - essa primeira extração estrutural já foi aplicada:
     - o payload estrutural do detalhe agora nasce em um bloco próprio
     - o template continua consumindo o mesmo contrato
     - narrativa enriquecida e recovery permanecem explicitamente fora desse recorte
   - a revisão seguinte mostrou que o próximo subcorte seguro parece ser o handoff de confirmação do checkout:
     - `confirmation_mode` entra por um gate simples e explícito
     - ele altera apenas uma fatia localizada da narrativa do detalhe
     - ele não carrega sozinho a mesma complexidade de recovery transacional do bloco de `payments`
   - o plano seguro desse subcorte agora fica:
     1. extrair o confirmation payload para um bloco isolado
     2. manter o gate explícito na view
     3. deixar `payments`/recovery completamente fora
     4. só depois reavaliar se o handoff já consegue viver sem fallback legado
   - essa extração do handoff já foi aplicada:
     - o confirmation payload agora nasce em um bloco próprio
     - o gate de entrada continua explícito na view
     - `payments`/recovery seguem fora desse recorte
   - a revisão seguinte mostrou que `reorder lite` já parece o próximo subcorte seguro:
     - o CTA nasce localmente no `order detail`
     - a ação entra por `POST` explícito
     - o write real é delegado ao boundary de `checkout`
     - ele não depende diretamente do bloco transacional de `payments`
   - o plano seguro desse subcorte agora fica:
     1. extrair o payload de `reorder lite` para um bloco próprio
     2. manter a action boundary explícita na view
     3. preservar a delegação do write para `checkout_reorder_commands`
     4. deixar retry, hosted payment e recovery fora desta etapa
   - essa extração do `reorder lite` já foi aplicada:
     - o payload agora nasce em um bloco próprio
     - a action boundary segue explícita na view
     - o write real continua delegado ao boundary de `checkout`
   - por isso, o próximo passo seguro parece ser isolar melhor a capability de recompra leve antes de tocar em retry, hosted payment e recovery
   - isso evita misturar numa única mudança:
     - leitura de apresentação
     - feedback de handoff
     - ações comerciais
     - recovery transacional e observabilidade operacional
   - a revisão seguinte do `payment retry` mostrou que ele ainda **não** deve ser o próximo subcorte:
     - a action continua local, mas já depende de falha real de pagamento
     - o write segue para um bootstrap específico de retry
     - o bloco conversa com recovery e continuidade transacional demais para esta etapa
   - por isso, `payment retry` continua depois do bloco mais explícito de hosted payment / recovery, e não como próximo corte isolado
   - a revisão seguinte de `hosted payment` mostrou que ele também ainda **não** deve ser tratado como próximo subcorte isolado:
     - o CTA nasce no detalhe, mas aponta diretamente para a boundary de `payments`
     - o bloco depende de `PaymentAttempt` pendente, `attempt_key` e redirect hospedado
     - o comportamento já está acoplado ao guidance de recovery e continuidade segura do pagamento
   - por isso, `hosted payment` deve continuar junto do bloco de recovery/payment continuity, e não como uma capability isolada anterior
   - a revisão consolidada seguinte mostrou que o restante do detalhe já se organiza melhor como **recovery block**:
     - `payment_progression_*`
     - `payment_retry_*`
     - `hosted_payment_*`
     - `payment_attempt_*`
     - `pending_recovery_*`
     - `order_pending_recovery_*`
   - esse restante compartilha semântica de continuidade e recovery transacional demais para continuar sendo fatiado por CTA
   - por isso, a próxima revisão segura deve tratar esse eixo como um único boundary residual do `order detail`
   - o plano seguro dessa decomposição agora fica:
     1. isolar a leitura operacional passiva de `PaymentAttempt`
     2. isolar o guidance de recovery
     3. só então revisar actions/capabilities de pagamento
     4. deixar a narrativa residual por último
   - isso evita misturar numa única mudança:
     - telemetria passiva
     - guidance operacional
     - actions de continuidade de pagamento
     - costura narrativa final do detalhe
   - a revisão seguinte mostrou que essa primeira camada já parece segura:
     - `payment_attempt_*` hoje nasce como leitura/timeline passiva
     - o template apenas exibe contexto operacional
     - não há ação transacional disparada por esse sub-bloco
   - por isso, o próximo subcorte seguro do recovery block parece ser justamente a leitura operacional passiva de `PaymentAttempt`
   - a revisão seguinte mostrou que a segunda camada também já parece segura:
     - `pending_recovery_*` e `order_pending_recovery_*` hoje entram como alerts passivos
     - o template apenas comunica guidance contextual
     - o sub-bloco não executa retry, redirect ou bootstrap por si só
   - por isso, o próximo subcorte seguro depois de `payment_attempt_*` parece ser justamente o guidance de recovery
   - a revisão seguinte mostrou que o restante das actions já deve ser tratado como um único actions block:
     - `payment_progression_*`
     - `payment_retry_*`
     - `hosted_payment_*`
   - esse restante compartilha a mesma surface de jornada, mas delega efeitos reais para `orders`, `checkout` e `payments`
   - por isso, a próxima revisão segura não deve voltar a separar CTA por CTA
   - o que sobra agora é um único boundary residual de continuidade de pagamento
   - o plano seguro dessa decomposição agora fica:
     1. isolar o payload declarativo das actions
     2. preservar a renderização unificada das actions no detalhe
     3. manter o dispatch transacional agrupado enquanto o bloco continuar sensível
     4. só depois reavaliar se vale separar por tipo de boundary externo
   - isso evita misturar numa única mudança:
     - payload de UI
     - renderização da surface de jornada
     - dispatch transacional
     - delegação para `orders`, `checkout` e `payments`
   - essa extração do guidance de recovery já foi aplicada:
     - o payload de `pending_recovery_*` e `order_pending_recovery_*` agora nasce em um bloco próprio
     - o template continua só exibindo feedback contextual
     - as actions reais seguem fora desse recorte
   - essa extração da leitura passiva já foi aplicada:
     - o payload `payment_attempt_*` agora nasce em um bloco próprio
     - o template continua apenas exibindo contexto operacional e timeline
     - guidance e actions seguem fora desse recorte

3. `accounts.application.account_address_commands`
   - ainda tolera `tenant_id=None` por compatibilidade
   - hoje o risco está mais controlado, mas o contrato futuro ideal é exigir tenant também nesse boundary

### Tolerâncias que ainda valem manter

Por enquanto, ainda faz sentido manter:

- fallbacks globais de `Admin Customers`, `Admin Orders` e `Admin Products`
- leituras administrativas globais que ainda sustentam operação/plataforma fora de uma loja específica

Motivo:

- essas superfícies ainda funcionam como compatibilidade operacional legítima
- a aposentadoria delas exigiria antes um contrato mais claro de admin global vs admin por tenant

---

# Princípio central

## Permitido
- um módulo consultar outro por interfaces claras
- um módulo usar casos de uso expostos por outro módulo
- um módulo depender de entidades compartilhadas apenas quando isso for inevitável

## Não permitido
- um módulo “invadir” a regra interna do outro
- um módulo reimplementar regra do outro
- um módulo assumir comportamento não documentado de outro

---

# Fronteiras por módulo

## 1. accounts

### Responsabilidade
Gerenciar autenticação e contexto de usuários administrativos da loja e da plataforma.

### Pode acessar
- tenants, para vínculo do owner ao tenant
- audit, para registrar ações relevantes

### Não deve acessar diretamente
- lógica de catálogo
- lógica de checkout
- lógica de pagamento
- lógica de frete

### Observação
`accounts` não representa `Customer`.  
Customer é outro contexto do domínio.

---

## 2. tenants

### Responsabilidade
Gerenciar lojas, subdomínios, branding, modo manutenção, configurações do tenant.

### Pode acessar
- subscriptions, para plano/estado da loja
- accounts, durante onboarding
- notifications, para comunicações administrativas

### Não deve acessar diretamente
- detalhes internos de pedidos
- detalhes internos de pagamentos de pedidos
- lógica detalhada de catálogo

### Observação
`tenants` é o núcleo do contexto SaaS.

---

## 3. catalog

### Responsabilidade
Gerenciar produtos, variantes, categorias, marcas, tags, imagens e flags de exibição.

### Pode acessar
- tenants, para contexto de loja
- reviews, para resumo de avaliação
- coupons, se houver regra explícita de elegibilidade futura

### Não deve acessar diretamente
- checkout
- payments
- shipping
- subscriptions

### Observação
`catalog` não deve conhecer o fluxo de pedido.  
Ele fornece dados de produto; não decide compra.

---

## 4. customers

### Responsabilidade
Gerenciar compradores, perfis e endereços.

### Pode acessar
- tenants
- orders, para histórico de compras
- newsletter, se houver opt-in

### Não deve acessar diretamente
- payments
- shipping internamente
- subscriptions
- accounts

### Observação
`customers` não deve ser misturado com `accounts`.

---

## 5. cart

### Responsabilidade
Gerenciar carrinho persistente e itens do carrinho.

### Pode acessar
- customers
- catalog
- tenants

### Não deve acessar diretamente
- payments
- shipping (cálculo formal de frete pertence ao checkout)
- orders (exceto conversão coordenada pelo checkout)

### Observação
Carrinho não é pedido.
`cart` prepara a compra, mas não a materializa sozinho.

---

## 6. checkout

### Responsabilidade
Orquestrar o fluxo de finalização da compra.

### Pode acessar
- cart
- customers
- shipping
- coupons
- orders
- payments

### Não deve acessar diretamente
- detalhes internos de subscriptions
- lógica de admin da plataforma
- lógica de branding do tenant além do necessário

### Observação
`checkout` é o orquestrador da compra.  
Ele pode coordenar módulos, mas não deve concentrar persistência caótica nem regra espalhada.

---

## 7. orders

### Responsabilidade
Gerenciar pedidos, itens, histórico de status e consistência do lifecycle do pedido.

### Pode acessar
- customers
- tenants
- catalog, para snapshots e referências
- payments, via contrato claro
- shipping, via contrato claro
- audit

### Não deve acessar diretamente
- lógica interna do gateway de pagamento
- lógica interna de cotação de frete
- subscriptions

### Observação
`orders` é dono do lifecycle do pedido.  
Outros módulos podem influenciar o pedido, mas não devem “possuir” o fluxo do pedido.

---

## 8. payments

### Responsabilidade
Gerenciar Payment, PaymentTransaction, integração com gateway e webhooks.

### Pode acessar
- orders, por contratos claros
- checkout, quando orquestrado
- notifications, para eventos pós-pagamento
- audit

### Não deve acessar diretamente
- catalog para regra comercial arbitrária
- customers para lógica de perfil
- shipping
- subscriptions (pagamentos de assinatura podem ser outro subcontexto interno)

### Observação
`payments` não deve assumir o papel de `orders`.  
Ele confirma e informa; `orders` decide sua evolução por contrato.

---

## 9. shipping

### Responsabilidade
Gerenciar cotação de frete, remessa, rastreamento e Shipment.

### Pode acessar
- checkout
- orders
- customers, para endereço
- catalog, para peso e dimensões da variante

### Não deve acessar diretamente
- payments
- subscriptions
- accounts

### Observação
`shipping` calcula frete e cuida da remessa, mas não cria pedido sozinho.

---

## 10. coupons

### Responsabilidade
Gerenciar cupons de desconto e sua validação.

### Pode acessar
- tenants
- checkout
- orders, quando cupom já foi aplicado
- audit

### Não deve acessar diretamente
- payments
- shipping
- subscriptions
- reviews

### Observação
Regras promocionais não devem ser espalhadas por checkout, cart e orders sem centralização.

---

## 11. reviews

### Responsabilidade
Gerenciar avaliações de produto.

### Pode acessar
- customers
- catalog
- tenants
- audit

### Não deve acessar diretamente
- checkout
- payments
- shipping
- subscriptions

### Observação
`reviews` não deve decidir regra de catálogo, apenas enriquecê-lo.

---

## 12. subscriptions

### Responsabilidade
Gerenciar planos, assinatura SaaS, invoices e cobrança da plataforma.

### Pode acessar
- tenants
- accounts
- notifications
- audit

### Não deve acessar diretamente
- cart
- checkout
- orders de loja
- shipping
- catálogo do tenant

### Observação
Pagamentos de assinatura SaaS são um contexto diferente dos pagamentos de pedido.

---

## 13. notifications

### Responsabilidade
Gerenciar envio de e-mails e notificações transacionais.

### Pode acessar
- orders
- payments
- subscriptions
- tenants
- customers

### Não deve acessar diretamente
- lógica de decisão de negócio
- regras de catálogo
- regras de checkout

### Observação
`notifications` deve reagir a eventos, não tomar decisões centrais do domínio.

---

## 14. pages

### Responsabilidade
Gerenciar páginas institucionais editáveis da loja.

### Pode acessar
- tenants

### Não deve acessar diretamente
- checkout
- payments
- orders
- subscriptions

---

## 15. newsletter

### Responsabilidade
Gerenciar inscrição de newsletter e base de contatos.

### Pode acessar
- tenants
- customers, quando houver vínculo explícito
- notifications, para campanhas futuras

### Não deve acessar diretamente
- checkout
- payments
- shipping

---

## 16. audit

### Responsabilidade
Registrar ações administrativas e eventos auditáveis.

### Pode acessar
- todos os módulos, apenas como registrador

### Não deve fazer
- lógica de negócio
- orquestração
- decisão de fluxo

### Observação
`audit` é transversal, mas não deve virar dependência acopladora.

---

## 17. api-keys

### Responsabilidade
Gerenciar credenciais de integração da API pública.

### Pode acessar
- tenants
- audit

### Não deve acessar diretamente
- lógica interna de checkout
- pagamentos
- pedidos

---

# Regras de comunicação entre módulos

## Preferência 1
Chamar `application/` do módulo dono da regra.

## Preferência 2
Usar serviços explícitos ou contratos internos documentados.

## Preferência 3
Usar eventos assíncronos para efeitos colaterais ou reações secundárias.

## Evitar
- importar helpers internos arbitrários
- acessar models de outro módulo para contornar fluxo de negócio
- duplicar regra para “resolver rápido”

---

# Dono de cada regra importante

## Tenant resolution
Dono: `tenants`

## Owner authentication
Dono: `accounts`

## Customer profile
Dono: `customers`

## Product pricing
Dono: `catalog` / `ProductVariant`

## Cart state
Dono: `cart`

## Checkout orchestration
Dono: `checkout`

## Order lifecycle
Dono: `orders`

## Payment gateway integration
Dono: `payments`

## Shipping quote and shipment tracking
Dono: `shipping`

## Coupon validation
Dono: `coupons`

## Product reviews
Dono: `reviews`

## SaaS plan and subscription lifecycle
Dono: `subscriptions`

## Email sending
Dono: `notifications`

## Audit trail
Dono: `audit`

---

# Regras de implementação para agentes de IA

Antes de implementar qualquer tarefa, agentes devem responder mentalmente:

1. Qual módulo é dono dessa regra?
2. Estou colocando lógica no módulo certo?
3. Estou chamando outro módulo por caminho claro?
4. Estou acoplando demais?
5. Existe documentação do módulo em `docs/modules/`?
6. Esta mudança viola alguma fronteira deste documento?

---

# Sinais de que a fronteira foi quebrada

Exemplos de problemas:

- `payments` alterando pedido arbitrariamente sem contrato
- `cart` criando pedido diretamente
- `catalog` decidindo fluxo de shipping
- `subscriptions` lendo detalhes internos de checkout
- `notifications` contendo regra de negócio
- `accounts` tratando customer como owner

Se isso ocorrer, a implementação deve ser revista.

---

# Objetivo final

Este documento existe para manter o Hubx Market:

- modular
- previsível
- escalável
- seguro para evolução
- fácil para contribuidores e agentes de IA

---

## Nota de boundary: order detail actions block

- no `order detail` da `customer area`, o bloco residual de continuidade de pagamento agora já separa explicitamente:
  - payload declarativo das actions em `accounts.application.account_customer_area_queries`
  - renderização unificada em `accounts.interfaces.views._build_order_detail_actions(...)`
  - dispatch transacional agrupado em `accounts.interfaces.views.AccountOrderDetailView.post(...)`
- isso preserva as fronteiras com:
  - `orders` para confirmação interna
  - `checkout` para `payment retry`
  - `payments` para continuidade hospedada
- leitura prática:
  - configuração de UI fica em `accounts`
  - execução real continua delegada ao módulo dono de cada efeito
- a revisão mais recente reforça que essa renderização unificada é uma boundary segura:
  - ela monta a surface visual do detalhe
  - mas não executa o efeito de domínio em si
- isso permite tratá-la como próximo subcorte interno antes de mexer no dispatch agrupado
- o plano seguro dessa boundary agora fica:
  1. tornar a renderização mais declarativa internamente
  2. manter `_build_order_detail_actions(...)` como surface única da view
  3. preservar o dispatch agrupado até uma revisão posterior
- leitura prática:
  - `accounts.interfaces.views` continua dono da montagem visual do detalhe
  - os módulos externos continuam donos do efeito real de cada action
- essa extração já foi aplicada:
  - `accounts.interfaces.views` agora monta primeiro itens declarativos de action
  - a renderização HTML final continua centralizada na mesma surface pública
- isso reforça a boundary:
  - UI em `accounts`
  - efeito real nos módulos donos de `orders`, `checkout` e `payments`
- a revisão do dispatch reforça que a execução ainda deve permanecer agrupada:
  - `accounts` continua apenas roteando a action
  - o efeito real continua delegado para o módulo dono
- leitura prática:
  - separar o `POST` cedo demais aumentaria o acoplamento da journey sem ganho estrutural claro agora
- a auditoria residual do `order detail` mostra que a maior parte do que restou em `accounts` já não é boundary funcional forte
- o residual agora está mais concentrado em:
  - copy enriquecida
  - composição final de `page_meta`
  - composição final de `summary_note`
- leitura prática:
  - a fronteira com `orders`, `checkout` e `payments` já está mais honesta
  - o que sobra agora é principalmente narrativa local de apresentação dentro de `accounts`
- a revisão seguinte reforça que esse residual pode ser tratado como um bloco local de narrativa:
  - não muda ownership de domínio
  - não exige nova fronteira entre módulos
- leitura prática:
  - o próximo refinamento seguro, se desejado, é um `narrative block` interno de `accounts`
- o plano seguro desse bloco agora fica:
  1. base narrativa local
  2. enriquecimento de pagamento
  3. enriquecimento de tentativa
  4. confirmação continua separada
- leitura prática:
  - a evolução segue local a `accounts`
  - sem reabrir fronteiras com `orders`, `checkout` ou `payments`
- a extração da base narrativa já foi aplicada:
  - a copy-base do detalhe agora nasce em um bloco local próprio
- isso reforça que o restante desse eixo continua sendo refinamento interno de `accounts`, não uma mudança de ownership entre módulos
- a extração seguinte também já isolou o enriquecimento de pagamento:
  - origem e referência atuais
  - `page_meta` complementar de pagamento
- leitura prática:
  - a narrativa incremental continua local a `accounts`
  - sem alterar ownership de `orders` ou `payments`
- a extração seguinte também já isolou o enriquecimento de tentativa:
  - status e status label
  - provider e referência externa
  - sessão de origem e último evento
- leitura prática:
  - a narrativa residual segue sendo refinamento local de `accounts`
  - a ownership dos módulos externos continua intacta
- a revisão da confirmação reforça que esse bloco já é uma boundary local estável:
  - gate explícito
  - payload próprio
  - sem necessidade de novo corte imediato
- o hardening final em `accounts` também fecha os writes de endereço como tenant-owned de verdade:
  - `account_address_commands` não deve mais operar sem tenant resolvido
  - `accounts.interfaces.views` continua responsável só por coletar o contexto da request e delegar o write
- leitura prática:
  - isso reduz a última tolerância global relevante de escrita que ainda restava nesse módulo

## Fechamento da abordagem multi-tenant em `accounts`

- a auditoria final mostra que o residual remanescente em `accounts` está concentrado em **leituras globais controladas**
- esse residual não altera ownership entre módulos e não cria novo write path cross-tenant
- leitura prática:
  - a abordagem multi-tenant deste módulo pode ser considerada concluída nesta fase
  - o que sobra agora é compatibilidade deliberada de leitura, não gap estrutural de boundary
