# Page Templates

## Objetivo
Definir esqueletos padrão de página.

## List page
- page header
- toolbar de ações
- filtros via `filter_bar.html`
- tabela ou grid; para operações administrativas, preferir `data_table.html`
- paginação via `pagination.html`
- empty state via `empty_state.html`
- updates parciais devem manter `hx-target` estável ao redor do resultado da lista

## Detail page
- page header
- cards de resumo
- seções
- histórico
- ações laterais quando necessário

## Form page
- page header
- descrição curta
- formulário
- ações finais

## Dashboard page
- header
- stat cards
- listas/tabelas resumidas
- blocos de atividade

## Checkout page
- etapas visuais claras
- resumo do pedido
- formulário de endereço
- frete
- pagamento
- confirmação
- usar `checkout_steps.html`, `shipping_method_selector.html`, `payment_method_selector.html`, `cart_item.html` e `order_summary.html` em vez de HTML local para estados de checkout
- não criar pedido nem baixar estoque por alteração visual; o template continua apenas renderizando sessão, itens, frete, pagamento e revisão

## Storefront home
- shell com sidebar em desktop contendo identidade da loja, navegação, conta e pedidos; em mobile a navegação pode ficar horizontal/rolável
- hero institucional tenant-owned via `shared/partials/storefront_institutional_hero.html`
- imagem real do hero quando configurada; fallback pode vir de produto do próprio tenant
- sinais curtos de confiança dentro do hero
- produtos visíveis logo abaixo do hero
- footer padrão com links úteis e seletor de tema; o header do storefront não deve duplicar esse controle
- quando o tenant for a demo oficial, a home deve aplicar a paleta `hubx-demo`, logo Hubx e aviso de somente leitura
- grids de produto devem usar `product_card.html`; PDP deve reutilizar `product_gallery.html`, `variant_selector.html`, `price_display.html`, `stock_indicator.html` e `quantity_selector.html`

## Storefront footer
- identidade da loja
- Catálogo
- Minha conta
- Meus pedidos
- links institucionais condicionais quando configurados pela loja:
  - Trocas e devoluções
  - Política de privacidade
  - Termos
  - Contato
- menção "Operado com Hubx Market"

## Admin da loja
- sidebar com identidade do tenant e navegação iconográfica
- topbar com escopo "Admin da loja"
- conteúdo denso, operacional e sem hero marketing
- componentes comuns: page header, filtros, data table, stat cards, audit log
- listas operacionais devem usar filtros compactos, toolbar tokenizada e tabelas DS sem cores arbitrárias por template
- listas CRUD operacionais devem expor ações descobríveis por linha para detalhe/edição quando a permissão permitir
- status renderizado por helpers de interface deve emitir `ds-badge`; progresso operacional deve usar `ds-progress`
- `/ops/branding/` usa template de formulário admin com campo de URL pública do logo e preview do partial `storefront_institutional_hero.html`; a prévia deve consumir o mesmo contrato `storefront_hero` da storefront.

## Project/platform owner
- sidebar com Hubx Market e escopo platform
- acento visual de platform quando houver ação cross-tenant
- telas principais: Lojas, Onboarding, Assinaturas, API keys, Auditoria e Portal central
- Aquisições SaaS usa lista/detail operacional para leads de `/plans/`, com ações explícitas de converter ou descartar
- detalhes de aquisição/onboarding usam `ds-subpanel`, `ds-alert`, `ds-callout-list` e botões completos `ds-btn ds-btn-*`
- não misturar dados comerciais tenant-owned na tela platform

## Auth, conta, portal e checkout
- auth usa card central e identidade do host
- área do cliente usa navegação leve com ícones
- portal central usa Hubx Market como marca principal
- checkout usa footer compacto e sinais explícitos de segurança

## Central public home
- `/` em host central sem tenant usa `portal_home_page.html`.
- primeira dobra pública deve vender Hubx Market para lojistas criarem loja virtual, com asset raster de marca/produto, linguagem premium e CTA principal para iniciar onboarding.
- CTAs públicos da home central devem priorizar `Iniciar onboarding` para `/plans/#aquisicao`, `Ver planos` para `/plans/#planos` e `Acessar demo` para `/demo/`; login permanece na navegação.
- hero público deve usar `shared/partials/public_hero.html`, preservando a cena da imagem sem corte agressivo em desktop e mantendo leitura do texto em mobile.
- navegação pública central deve usar o partial compartilhado `shared/partials/public_nav.html` com links para portal, planos, demo e login/logout.
- a seção pós-hero deve ser curta, comercial e focada em benefícios reais do SaaS, sem repetir cards de navegação.
- não exibir links diretos de `/ops/platform/...`, catálogo tenant-owned, pedidos de cliente ou administração de loja.
- `/demo/` é o CTA público estável para a loja demo oficial; a página central não lê catálogo, pedidos ou identidade tenant-owned diretamente.
- `/demo/` deve renderizar uma escolha simples entre perfil admin da loja e cliente da loja, cada opção apontando para uma rota tenant-owned de sessão direta da demo, sem passar pela tela de login.
- cards de perfil da demo usam `ds-card` e `ds-public-option-icon`.
- o ambiente tenant-owned `hubx-demo` é somente leitura: templates devem comunicar esse estado e não prometer checkout, cadastro ou edição efetivos.

## Public SaaS plans
- `/plans/` usa Hubx Market como marca principal e não herda identidade de tenant resolvido.
- hero deve usar asset raster de marca/produto, com texto sobre imagem e não dentro de card, mas a narrativa deve vender planos e aquisição assistida do SaaS.
- a página de planos não deve incorporar galeria, catálogo ou blocos de demo; a demo oficial deve ser acessada apenas por link/CTA para `/demo/`.
- navegação deve seguir o mesmo partial público da home central e incluir link para `/demo/`.
- cards de plano mostram dados de `SubscriptionPlan` ativo.
- cards de plano devem exibir badges de trial e cartão quando `trial_days`/`requires_payment_method` estiverem configurados.
- preço deve deixar claro o valor mensal após o trial, por exemplo `R$ 99,90 /mês após 30 dias`.
- cards de plano usam `ds-plan-card ds-surface`; recomendação usa `badge.html`, não span local.
- formulário público deve deixar claro no fluxo que cria intenção de aquisição, não checkout/billing real.
- formulário público não deve pedir número de cartão, CVV, validade ou qualquer dado sensível de payment method.
- formulário público usa `ds-card`, `alert.html`/`ds-alert` e `field_error.html` para feedback.
- sucesso confirma recebimento e mantém o provisionamento reservado ao admin platform.
- quando `HUBX_PUBLIC_SIGNUP_ENABLED=1`, `/plans/` pode exibir CTA secundário para `/plans/signup/`.
- `/plans/signup/` deve deixar claro que cria tenant em manutenção, trial interno de acordo com o plano, provider-alvo Asaas e owner inicial, sem billing SaaS automático.
- `/plans/signup/` deve explicar que cartão obrigatório acontece apenas em fluxo seguro hospedado de billing, fora dos campos públicos.
- quando `HUBX_PUBLIC_SIGNUP_REQUIRE_ACCESS_TOKEN=1`, o template deve exibir campo de código de acesso e erro inline via `field_error.html`.
- sucesso de signup deve mostrar subdomínio, estado de manutenção e CTA para login/admin da loja recém-criada.
