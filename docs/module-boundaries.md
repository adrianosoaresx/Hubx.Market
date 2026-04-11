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
