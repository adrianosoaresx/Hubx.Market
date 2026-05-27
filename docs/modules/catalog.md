# Catalog

## Responsabilidade
Gerenciar produtos, variantes, categorias, marcas, tags e imagens.

## Entidades principais
- Product
- ProductVariant
- Category
- Brand
- Tag
- ProductImage

## Casos de uso
- criar produto
- editar produto
- desativar produto
- configurar promoção

## Regras de negócio
- preço e estoque pertencem à variante

## Integração UI
- views HTTP devem permanecer finas em `interfaces/`
- templates oficiais do Design System podem ser usados como contrato de apresentação
- adapters de contexto podem preparar dados para list/detail/form sem mover regra de negócio para a view
- o mesmo módulo pode expor rotas administrativas e storefront, desde que a separação de URLs e adapters de apresentação permaneça clara
- queries de leitura para Admin Products devem viver fora das views; enquanto o módulo ainda não expõe modelos/serviços reais, a camada `application/` pode centralizar fallback temporário sem quebrar o contrato dos templates
- queries de leitura para o storefront também devem viver em `application/`; tenant-awareness e fallback temporário devem ficar nessa camada, não nas views públicas
- storefront é uma superfície tenant-required:
  - listagem
  - detalhe de produto
  devem responder `404` quando a loja não for resolvida pelo middleware
- no estado atual do repositório, `Admin Products` ainda não possui modelo/tabela persistida utilizável; a query layer detecta essa indisponibilidade explicitamente e mantém fallback seguro até a fonte real existir
- readiness mínima agora existe no módulo:
  - `Product` com `tenant`, status e metadados principais
  - `ProductVariant` para respeitar a regra de preço/estoque por variante
  - `ProductImage` para mídia mínima persistida por URL, com ordenação e imagem principal
- as query layers de `Admin Products` e do storefront já consomem essa estrutura quando houver migração aplicada e registros persistidos
- o seed mínimo `catalog_minimal_seed` permite validar a primeira leitura persistida sem alterar o contrato visual
- enquanto não houver tenant resolvido, o fallback administrativo continua intencionalmente ativo como compatibilidade
- quando houver tenant resolvido e nenhum produto persistido correspondente, `Admin Products` passa a expor ausência real em vez de reutilizar fixtures de demonstração
- na listagem administrativa tenant-scoped, esse caso também aparece com empty state explícito de loja sem catálogo persistido, em vez de parecer apenas uma tabela vazia
- quando houver fonte persistida, leituras do storefront devem sempre ser filtradas por `tenant_id`
- ausência de tenant não deve cair em catálogo demo/fallback como se fosse uma loja válida

## PDP: mídia e variantes
- o storefront agora prefere `ProductImage` para:
  - `product_gallery_items`
  - `main_image_url`
  - `main_image_alt`
- prioridade de mídia:
  - imagem primária
  - primeira imagem ordenada
  - fallback derivado por placeholder, se não houver mídia persistida
- `variant_groups` agora tentam refletir `ProductVariant` reais a partir do SKU persistido
- quando essa leitura não for suficiente, o fallback derivado anterior continua ativo

## PDP: commerce hints por variante padrão
- quando houver `ProductVariant` persistida, o PDP passa a usar a variante padrão como fonte de verdade para:
  - `price`
  - `compare_price`
  - `stock_state`
  - `stock_helper`
  - `price_helper`
  - `purchase_note`
  - `primary_action_label`
- como ainda não existe um engine completo de seleção dinâmica, essa wave usa a variante padrão atual como “selected/default variant” segura
- quando as variantes forem insuficientes ou inexistentes, o comportamento anterior continua disponível como fallback

## PDP: coerência entre mídia e variante efetiva
- quando houver pistas suficientes em `ProductImage` (URL/alt) e no SKU da variante padrão, o storefront tenta priorizar a mídia mais coerente com essa variante efetiva
- isso ajuda a alinhar:
  - imagem principal
  - help text de variantes
  - hints comerciais
- quando essas pistas não existirem, a ordenação simples anterior continua valendo

## PDP: polish comercial leve
- badges e hints comerciais agora usam sinais já disponíveis da variante padrão:
  - estoque
  - preço comparativo
  - backorder
  - destaque do produto
- a intenção é reforçar clareza comercial sem criar urgência artificial ou promessas não suportadas

## Listagem: enrichment comercial leve
- a listagem do catálogo agora reaproveita melhor os mesmos sinais reais do PDP:
  - mídia principal persistida
  - variante padrão efetiva
  - contexto de oferta, estoque e disponibilidade
- isso permite enriquecer os cards com:
  - subtítulo mais coerente com categoria + variante
  - meta curta com SKU + contexto comercial
  - helper de preço mais orientado à decisão
- a página de catálogo também passa a comunicar melhor quando os resultados já refletem preço, mídia e disponibilidade atualizados

## Continuidade entre catálogo e PDP
- o storefront agora reforça melhor que a combinação em destaque na listagem continua sendo a mesma base comercial no PDP
- essa continuidade usa apenas sinais já persistidos:
  - variante padrão efetiva
  - mídia principal
  - preço
  - disponibilidade
- isso melhora:
  - `product_subtitle`
  - `short_description`
  - `purchase_note`
- a intenção é reduzir a sensação de ruptura entre card e detalhe sem abrir seleção dinâmica de variante

## Ativação mínima PDP → checkout
- o PDP agora consegue iniciar uma `CheckoutSession` mínima a partir do produto exibido
- essa ativação usa apenas a variante efetiva atual e cria um snapshot simples para o checkout:
  - item
  - preço
  - imagem principal
  - métodos padrão de entrega e pagamento
- quando a variante está indisponível, o fluxo não força checkout e mantém o retorno seguro ao catálogo

## Inventory visibility / stock impact clarity
- `Admin Products` agora destaca melhor quando o estoque principal já está parcialmente comprometido por pedidos confirmados
- a leitura permanece leve e baseada em sinais já persistidos:
  - `stock`
  - `reserved_stock`
  - saldo livre estimado
- a listagem e o detalhe administrativo passam a comunicar:
  - produtos com reserva operacional
  - produtos com saldo livre mais sensível

## Inventory recovery visibility / admin feedback
- `Admin Products` agora também passa a refletir quando devoluções operacionais de estoque já começaram a acontecer
- essa leitura usa sinais já persistidos do fluxo de pedidos:
  - `Order.inventory_recovered_at`
  - `OrderItem.variant_sku`
- a intenção é deixar mais claro quando a variante principal já recebeu retorno de saldo por cancelamentos operacionais, sem abrir um engine novo de inventário

## Inventory timeline consolidation
- `Admin Products` agora também consolida os sinais principais de estoque em uma leitura operacional única por variante principal:
  - reserva após pagamento
  - recuperação após cancelamento
  - saldo livre atual
- essa consolidação aparece:
  - no bloco de estoque do detalhe
  - na atividade operacional do produto
- a intenção é reduzir leitura fragmentada e deixar mais claro o “estado vivo” do estoque sem criar uma timeline própria de inventário

## Inventory finalization visibility
- `Admin Products` agora também passa a refletir quando a reserva operacional já virou consumo final após entrega
- essa leitura usa sinais persistidos do fluxo de pedidos:
  - `Order.inventory_finalized_at`
  - `OrderItem.variant_sku`
- isso permite distinguir melhor, no admin:
  - reserva ainda ativa
  - recuperação por cancelamento
  - consumo final já concluído
- a visibilidade aparece:
  - na listagem administrativa
  - no bloco de estoque do detalhe
  - na atividade operacional do produto

## PDP conversion confidence polish
- o PDP agora reforça melhor a confiança da compra usando apenas sinais já existentes da variante efetiva:
  - `stock_label`
  - `effective_variant_summary`
  - `availability_note`
  - `cta_helper`
- a intenção é deixar mais claro:
  - qual variante está sustentando preço, estoque e CTA
  - se essa combinação está pronta para checkout, em estoque baixo, sob encomenda ou indisponível
  - qual é o próximo passo mais seguro sem urgência artificial

## Catalog listing conversion confidence
- os cards da listagem agora também reforçam melhor:
  - a combinação em destaque atual
  - a disponibilidade curta dessa combinação
  - o passo mais seguro antes do clique
- isso reaproveita sinais já existentes da query layer do storefront, sem transformar a listagem em mini-PDP
- a página do catálogo também explicita melhor que os cards já refletem:
  - variante efetiva
  - disponibilidade atual
  - contexto comercial coerente com o detalhe do produto

## Catalog entry / discovery review
- a entrada do catálogo agora também orienta melhor descoberta inicial usando apenas contexto já disponível de busca e categoria
- a página passa a comunicar com mais clareza:
  - quando a busca está ativa
  - quando uma categoria está ativa
  - o que exatamente a vitrine atual está mostrando
- os estados vazios também ficaram mais úteis para descoberta:
  - busca sem resultado
  - categoria sem resultado
  - busca + categoria sem resultado

## Catalog quick filters lite
- a vitrine agora também aceita `quick_filter` por querystring, aplicado antes da paginação
- os recortes atuais são simples e determinísticos:
  - `in_stock`
  - `low_stock`
  - `backorder`
  - `offer`
- filtros desconhecidos continuam seguros e são ignorados
- a própria página já deixa explícito quando um filtro rápido está ativo e adapta o estado vazio quando a visão filtrada não retorna itens

## Catalog quick filter clarity polish
- quando um `quick_filter` está ativo, a própria vitrine agora reforça:
  - o label humano do filtro ativo
  - a orientação de usar `Limpar` para voltar à vitrine completa
  - esse mesmo contexto também aparece nos estados vazios dos recortes rápidos

## Catalog initial ordering lite
- a listagem do storefront agora aplica uma ordenação inicial leve e explicável na query layer
- a prioridade atual é:
  - produtos ativos antes de rascunhos
  - `low_stock` antes de `in_stock`
  - `in_stock` antes de `backorder`
  - `backorder` antes de `out_of_stock`
  - produtos com oferta antes de equivalentes sem oferta
- o objetivo é deixar a vitrine inicial mais útil e comprável sem usar score, ML ou engine comercial nova

## Catalog commercial curation lite
- a vitrine do storefront agora também aplica uma camada leve de curadoria comercial usando apenas sinais já existentes:
  - `is_featured`
  - `compare_price`
  - disponibilidade atual da variante efetiva
- essa curadoria aparece em dois pontos:
  - filtros rápidos adicionais:
    - `featured`
    - `quick_buy`
  - helper curto no card para reforçar:
    - destaque atual
    - oferta ativa
    - compra rápida disponível
- a própria página do catálogo também passa a comunicar melhor que os cards já carregam uma curadoria comercial leve, sem personalização, score ou merchandising artificial

## Catalog quick buy confidence polish
- o recorte `quick_buy` agora comunica melhor por que certas combinações aparecem como prontas para compra:
  - produto ativo
  - variante efetiva em `in_stock` ou `low_stock`
  - continuidade segura do card até o PDP
- quando `quick_filter=quick_buy`, a vitrine passa a reforçar:
  - que a compra rápida não muda a base comercial mostrada no card
  - que o detalhe do produto aprofunda a mesma combinação efetiva
  - que o recorte privilegia decisão rápida, sem promessas artificiais
- os cards desse recorte também recebem helpers mais específicos para:
  - compra rápida disponível
  - continuidade segura até checkout via PDP

## Catalog featured confidence polish
- o recorte `featured` agora comunica melhor por que certos produtos aparecem em destaque na vitrine:
  - curadoria editorial leve
  - combinação efetiva preservada
  - contexto comercial real já visível no card
- quando `quick_filter=featured`, a vitrine passa a reforçar:
  - que o destaque não troca a base comercial ao abrir o detalhe
  - que o PDP aprofunda a mesma combinação efetiva mostrada no card
  - que o recorte continua honesto para estoque normal, baixo, sob encomenda ou indisponível
- os cards desse recorte também recebem helpers mais específicos para:
  - destaque editorial atual
  - continuidade segura do destaque até o PDP

## Catalog offer confidence polish
- o recorte `offer` agora comunica melhor por que certos produtos aparecem como oferta na vitrine:
  - preço comparativo ativo
  - combinação efetiva preservada
  - contexto comercial real já visível no card
- quando `quick_filter=offer`, a vitrine passa a reforçar:
  - que a oferta não muda a base comercial ao abrir o detalhe
  - que o PDP aprofunda a mesma combinação efetiva mostrada no card
  - que o recorte continua honesto para estoque normal, baixo, sob encomenda ou indisponível
- os cards desse recorte também recebem helpers mais específicos para:
  - oferta ativa atual
  - continuidade segura da oferta até o PDP

## Catalog reentry / discovery review
- a vitrine agora também reforça melhor sua função de reentrada para uma nova compra usando um `page_meta` leve no topo da página
- esse contexto varia conforme a visão atual:
  - vitrine completa
  - busca
  - categoria
  - quick filters
- a intenção é manter claro que:
  - o catálogo continua pronto para receber uma nova intenção de compra
  - o detalhe do produto aprofunda a mesma base comercial mostrada no card
  - a reentrada na vitrine segue coerente tanto para descoberta inicial quanto para retorno pós-compra

## PDP real variant selection readiness
- o PDP agora também aceita uma seleção explícita de variante por parâmetros simples (`size`, `color` ou `sku`) antes de ativar o checkout
- quando a combinação escolhida existir, a query layer recalcula a partir dela:
  - `sku`
  - `price`
  - `compare_price`
  - `stock_state`
  - `stock_label`
  - `stock_helper`
  - `purchase_note`
  - `effective_variant_summary`
  - `cta_helper`
- quando a seleção for inválida, o fluxo continua com fallback seguro para a variante padrão e a própria UI sinaliza que a combinação pedida não pôde ser aplicada
- o handoff para checkout também passa a respeitar a variante realmente escolhida no PDP:
  - `CheckoutSessionItem.variant_sku`
  - `subtitle` do item
  - `back_url` preservando a combinação atual

## Multi-item cart readiness
- o handoff do PDP agora também prepara uma sessão de checkout multi-item mínima
- ao adicionar um produto a partir do detalhe:
  - o fluxo tenta reaproveitar a sessão `open` já existente do mesmo tenant
  - mesma variante incrementa quantidade
  - variante diferente entra como novo item no snapshot
- isso mantém:
  - `variant_sku`
  - `subtitle`
  - preço da variante efetiva
  - continuidade segura até o checkout

## Cart surface lite
- o redirecionamento `PDP → checkout` agora também abre explicitamente o estágio `cart`
- isso cria um ponto intermediário leve entre:
  - escolher a variante no detalhe
  - revisar itens e totais da sessão
  - seguir para entrega
- a intenção é deixar a continuidade mais clara sem abrir ainda uma página dedicada de carrinho

## Wave Z — PDP Conversion Confidence Review
- a revisão do PDP mostra que ele já está forte em:
  - segurança de decisão
  - clareza da variante efetiva
  - confiança para seguir ao checkout
- o próximo ganho agora não parece ser de fluxo
- parece ser de **confiança comercial e desejo de compra**

### O que já funciona bem
- o detalhe já comunica melhor:
  - preço real da combinação atual
  - disponibilidade
  - helper de CTA
  - continuidade até checkout/cart
- a seleção de variante também já está mais honesta:
  - aplica combinação real
  - mantém fallback seguro
  - preserva contexto até checkout

### Gaps mais relevantes agora
- **1. o PDP ainda é mais seguro do que persuasivo**
  - ele explica bem o “pode comprar”
  - mas ainda pode reforçar melhor o “por que comprar esta combinação agora”
- **2. o bloco narrativo ainda é mais informativo do que comercial**
  - `product_subtitle`
  - `short_description`
  - `purchase_note`
  já são úteis, mas ainda podem ganhar:
  - contexto de uso
  - razão comercial curta
  - confiança aspiracional sem exagero
- **3. o CTA já é honesto, mas ainda pouco mobilizador**
  - hoje ele transmite segurança
  - ainda pode transmitir melhor:
    - prontidão
    - decisão
    - avanço natural

### Leitura objetiva
- eu não vejo um gap de arquitetura ou handoff neste ponto
- o próximo ganho do PDP parece ser:
  - **copy comercial leve**
  - **confiança de decisão**
  - **clareza aspiracional sem urgência artificial**

### Próxima wave
- **Wave AA — PDP Commercial Narrative Plan**
- foco:
  - decidir o menor recorte seguro para melhorar:
    - `product_subtitle`
    - `short_description`
    - `purchase_note`
    - framing do CTA/helper
  - sem mudar ainda seleção de variante, checkout ou cart

## Wave AA — PDP Commercial Narrative Plan
- o plano do PDP deve continuar pequeno, seguro e totalmente compatível com o handoff atual
- a direção não é mudar seleção de variante, cart ou checkout
- é **elevar o valor percebido da narrativa comercial antes da compra**

### Recorte seguro definido
1. **narrativa superior do detalhe**
   - revisar primeiro:
     - `product_subtitle`
     - `short_description`
   - objetivo:
     - reforçar contexto de uso
     - reforçar desejo leve
     - manter coerência com a variante efetiva mostrada
2. **narrativa de compra**
   - revisar:
     - `purchase_note`
   - objetivo:
     - aproximar a nota de compra de uma decisão segura e desejável
     - sem soar técnica demais
3. **framing do CTA/helper**
   - revisar:
     - `cta_helper`
     - linguagem do CTA principal quando fizer sentido
   - objetivo:
     - reforçar prontidão e avanço natural
     - sem urgência artificial

### O que fica fora desta etapa
- sem alterar:
  - seleção de variante
  - pricing logic
  - stock logic
  - handoff para cart/checkout
  - estrutura do template

### Leitura objetiva
- isso mantém o PDP no mesmo padrão seguro usado até aqui:
  - primeiro framing
  - depois execução de copy
  - só depois, se necessário, ajustes de profundidade

### Próxima wave
- **Wave AB — PDP Commercial Narrative Copy Review**
- foco:
  - revisar o melhor primeiro corte real de copy comercial no PDP
  - sem mudar ainda a estrutura nem o handoff

## Wave AB — PDP Commercial Narrative Copy Review
- a revisão de copy do PDP mostra que já existe um **primeiro corte seguro de execução**
- o melhor ponto de entrada não é mexer em seleção, preço ou checkout
- é melhorar a narrativa comercial onde o detalhe ainda está mais seguro do que persuasivo

### Candidatos mais seguros para a primeira passada
- **`product_subtitle`**
  - hoje já contextualiza a combinação atual
  - mas ainda pode comunicar melhor:
    - ocasião de uso
    - valor percebido
    - motivo para continuar a decisão
- **`short_description`**
  - já ajuda a reduzir a ruptura entre catálogo e detalhe
  - mas ainda pode ficar mais:
    - aspiracional
    - orientada a benefício
    - comercialmente memorável
- **`purchase_note`**
  - já é honesta e útil
  - mas ainda pode sair de:
    - segurança operacional
  - para:
    - decisão segura e desejável
- **`cta_helper`**
  - já é claro
  - mas ainda pode comunicar melhor:
    - prontidão da combinação
    - avanço natural para checkout
    - confiança sem urgência artificial

### O que fica fora desta etapa
- sem alterar ainda:
  - `variant_groups`
  - preço
  - estoque
  - `availability_note`
  - `effective_variant_summary`
  - handoff para cart/checkout
  - estrutura do template

### Leitura objetiva
- o PDP já está pronto para uma wave pequena de **copy execution**
- sem reabrir o fluxo nem mexer cedo demais no que já está estável

### Próxima wave
- **Wave AC — PDP Commercial Narrative Copy Execution**
- foco:
  - aplicar a primeira passada real em:
    - `product_subtitle`
    - `short_description`
    - `purchase_note`
    - `cta_helper`
  - sem mudar ainda a estrutura nem o handoff

## Wave AC — PDP Commercial Narrative Copy Execution
- aplicamos a primeira passada real de copy comercial no PDP
- a execução ficou restrita ao recorte mais seguro:
  - `product_subtitle`
  - `short_description`
  - `purchase_note`
  - `cta_helper`

### O que mudou
- o detalhe agora reforça melhor:
  - valor percebido da combinação atual
  - contexto de decisão
  - prontidão para avançar
- a narrativa comercial ficou mais presente:
  - acima do formulário
  - na nota de compra
  - no helper do CTA
- tudo isso sem mexer em:
  - variante
  - preço
  - disponibilidade
  - handoff para cart/checkout

### Leitura prática
- o PDP continua honesto e seguro
- mas agora ajuda melhor a responder:
  - por que esta combinação vale a decisão agora
  - por que seguir é um próximo passo natural
  - como avançar com confiança sem urgência artificial

### Validação
- suíte de `catalog` cobre a nova narrativa comercial do detalhe
- checks e schema sem impacto

### Próxima wave
- **Wave AD — PDP Conversion Wrap-Up Review**
- foco:
  - revisar o detalhe do produto depois dessas waves
  - decidir se ainda existe algum ajuste funcional pequeno antes de sair deste eixo

## Wave AD — PDP Conversion Wrap-Up Review
- a revisão final do PDP mostra que a superfície já avançou bem neste eixo de conversão
- hoje o detalhe do produto já comunica melhor:
  - qual combinação está sustentando a compra
  - se ela está pronta para seguir
  - por que vale continuar a decisão agora

### O que ficou mais forte
- **confiança de decisão**
  - preço, disponibilidade e helper já contam uma história coerente
- **clareza da combinação efetiva**
  - variante, fallback e continuidade estão mais honestos
- **narrativa comercial**
  - o detalhe já reforça melhor:
    - valor percebido
    - contexto de uso
    - prontidão para avançar

### O que ainda pode evoluir no futuro
- refinamentos pequenos de:
  - merchandising visual
  - densidade comercial do topo do detalhe
  - relação entre gallery e narrativa de uso
- mas isso já não parece urgente neste momento

### Leitura objetiva
- eu não vejo mais um gap funcional pequeno e óbvio que justifique insistir no mesmo eixo agora
- o PDP parece:
  - mais convincente
  - mais claro
  - mais seguro para conversão
- sem ter perdido estabilidade de fluxo

### Decisão prática
- este eixo de **confiança de conversão do PDP** pode ser considerado **encerrado com sucesso nesta fase**
- o próximo passo mais honesto agora é sair do detalhe do produto e voltar ao roadmap funcional mais amplo do storefront

### Próxima wave
- **Wave AE — Catalog Product Value Review**
- foco:
  - revisar a vitrine como produto de descoberta e merchandising
  - depois do ganho já consolidado no detalhe do produto

## Wave AE — Catalog Product Value Review
- a revisão da vitrine mostra que o catálogo já está funcionalmente sólido como superfície de descoberta inicial
- hoje a listagem já comunica bem:
  - combinação em destaque
  - disponibilidade atual
  - helper de clique
  - contexto comercial leve

### O que ficou mais forte
- **clareza comercial por card**
  - os cards já ajudam melhor a entender:
    - preço
    - disponibilidade
    - contexto da combinação atual
- **continuidade até o PDP**
  - o salto entre listagem e detalhe está mais coerente
  - a combinação destacada no card continua contando uma história parecida no detalhe
- **descoberta segura**
  - filtros, ordenação e empty states já sustentam navegação honesta
  - a vitrine não depende de urgência artificial para mover a decisão

### Gaps mais relevantes agora
- **merchandising ainda é leve**
  - a vitrine já é correta, mas ainda pouco editorial
- **descoberta ainda é mais funcional do que desejável**
  - os cards ajudam a decidir
  - mas ainda ajudam menos a querer abrir um produto agora
- **framing de coleção/categoria ainda é discreto**
  - `page_description`, `page_meta` e `results_meta` ainda falam mais de organização do que de valor percebido da vitrine

### Leitura objetiva
- eu não vejo um gap crítico de fluxo nesta superfície
- o catálogo parece:
  - claro
  - seguro
  - comercialmente coerente
- o próximo ganho mais honesto agora parece ser de **merchandising e descoberta**, não de infraestrutura de navegação

### Decisão prática
- este eixo do catálogo pode sair do foco de “correção funcional” e entrar no foco de **merchandising leve**
- o próximo investimento pequeno e seguro deve revisar:
  - framing da página
  - linguagem editorial da vitrine
  - motivo comercial para abrir um produto agora

### Próxima wave
- **Wave AF — Catalog Merchandising Review**
- foco:
  - revisar a vitrine como superfície de descoberta mais desejável
  - decidir o menor próximo passo funcional em:
    - `page_description`
    - `page_meta`
    - `results_meta`
    - framing editorial dos cards

## Wave AF — Catalog Merchandising Review
- a revisão da vitrine mostra que o catálogo já está pronto para um eixo leve de merchandising
- hoje a superfície já sustenta bem:
  - descoberta segura
  - continuidade até o PDP
  - decisão inicial por card

### O que já funciona bem
- **cards comercialmente coerentes**
  - `subtitle`, `price_helper`, `availability_note`, `click_helper` e `curation_note` já contam uma história consistente
- **header de página limpo**
  - `page_description`, `page_meta` e `results_meta` já organizam bem a navegação
- **vitrine honesta**
  - a página já evita urgência artificial
  - a decisão continua apoiada em disponibilidade, oferta e contexto reais

### Gaps mais relevantes agora
- **framing editorial ainda é discreto**
  - o topo da página ainda organiza mais do que inspira
- **cards ainda são mais úteis do que memoráveis**
  - eles ajudam a comparar
  - mas ainda ajudam menos a perceber “por que abrir este produto agora”
- **merchandising ainda é derivado, não protagonista**
  - destaque, oferta e quick-buy já existem
  - mas ainda aparecem mais como sinal operacional do que como curadoria de vitrine

### Leitura objetiva
- eu não vejo necessidade de mexer agora em:
  - filtros
  - paginação
  - estrutura da grade
  - handoff para o detalhe
- o próximo ganho mais honesto parece ser uma passada pequena em **copy editorial da vitrine**

### Decisão prática
- o próximo passo seguro deve começar por:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - framing editorial dos cards
- sem mexer ainda em:
  - ordenação
  - filtros
  - layout
  - lógica comercial de estoque/preço

### Próxima wave
- **Wave AG — Catalog Merchandising Copy Plan**
- foco:
  - decidir o menor recorte seguro para melhorar o topo da vitrine e o framing editorial dos cards

## Wave AG — Catalog Merchandising Copy Plan
- o próximo passo da vitrine deve continuar pequeno, seguro e orientado a copy
- a direção não é mudar:
  - filtros
  - paginação
  - grade
  - handoff para o detalhe
- a direção é melhorar:
  - framing editorial do topo
  - valor percebido da coleção atual
  - motivo comercial para abrir um produto agora

### Recorte seguro
- o primeiro corte deve revisar:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - sinais editoriais leves dos cards
- esse eixo editorial dos cards deve começar por:
  - `curation_note`
  - `click_helper`
- sem mexer ainda em:
  - `price_helper`
  - `availability_note`
  - `variant_summary`
  - estrutura do `product_card`

### Ordem recomendada
1. topo da vitrine
2. framing editorial dos cards
3. só depois reavaliar se vale tocar helpers mais próximos da decisão de compra

### Leitura objetiva
- isso mantém o catálogo no mesmo padrão saudável que seguimos até aqui:
  - primeiro framing
  - depois copy
  - sem reabrir fluxo estrutural cedo demais

### Próxima wave
- **Wave AH — Catalog Merchandising Copy Review**
- foco:
  - revisar o melhor primeiro corte real de execução em:
    - `page_description`
    - `page_meta`
    - `results_meta`
    - `curation_note`
    - `click_helper`

## Wave AH — Catalog Merchandising Copy Review
- já existe um **primeiro corte seguro de execução** para a vitrine
- o melhor ponto de entrada continua sendo:
  - framing editorial do topo
  - sinais leves de curadoria nos cards

### Corte seguro definido
- candidatos da primeira passada:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - `curation_note`
  - `click_helper`

### O que fica fora por enquanto
- `price_helper`
- `availability_note`
- `variant_summary`
- estrutura do `product_card`
- filtros
- paginação
- ordenação
- grade da listagem

### Leitura objetiva
- esse corte já permite melhorar:
  - desejo leve de exploração
  - leitura editorial da vitrine
  - motivo comercial para abrir um produto agora
- sem tocar cedo demais em helpers mais próximos da decisão final

### Próxima wave
- **Wave AI — Catalog Merchandising Copy Execution**
- foco:
  - aplicar a primeira passada real em:
    - `page_description`
    - `page_meta`
    - `results_meta`
    - `curation_note`
    - `click_helper`

## Wave AI — Catalog Merchandising Copy Execution
- aplicamos a primeira passada real de copy editorial na vitrine
- a execução ficou restrita ao recorte mais seguro:
  - `page_description`
  - `page_meta`
  - `results_meta`
  - `curation_note`
  - `click_helper`

### O que mudou
- o topo da vitrine agora reforça melhor:
  - curadoria leve
  - combinações em destaque
  - motivo para abrir um produto agora
- os cards agora comunicam melhor:
  - escolha editorial
  - oferta em evidência
  - contexto de exploração antes da decisão final

### O que não mudou
- filtros
- paginação
- ordenação
- grade da listagem
- helpers mais próximos da decisão final:
  - `price_helper`
  - `availability_note`
  - `variant_summary`

### Leitura objetiva
- a vitrine continua:
  - honesta
  - segura
  - coerente com o PDP
- mas agora ficou menos “só organizada” e mais:
  - convidativa
  - editorial
  - orientada à exploração com contexto

### Validação
- suíte de `catalog` cobre a nova copy de vitrine
- checks e schema sem impacto

### Próxima wave
- **Wave AJ — Catalog Merchandising Wrap-Up Review**
- foco:
  - revisar a vitrine depois dessa passada
  - decidir se ainda existe algum ajuste funcional pequeno antes de encerrar este eixo

## Wave AJ — Catalog Merchandising Wrap-Up Review
- a vitrine já avançou bem neste eixo de merchandising leve
- hoje ela comunica melhor:
  - combinações em destaque
  - curadoria leve
  - motivo para abrir um produto agora

### O que ficou mais forte
- **topo editorial**
  - `page_description`, `page_meta` e `results_meta` agora fazem mais do que organizar a página
  - eles ajudam a enquadrar melhor a descoberta
- **curadoria leve nos cards**
  - `curation_note` e `click_helper` passaram a reforçar melhor:
    - escolha editorial
    - oferta em evidência
    - contexto de exploração
- **coerência com o PDP**
  - a vitrine continua compatível com a mesma base comercial que o detalhe aprofunda

### O que ainda pode evoluir no futuro
- refinamentos pequenos de:
  - densidade editorial por coleção
  - merchandising visual
  - protagonismo de destaque/coleção acima da grade
- mas isso já parece:
  - refinamento futuro
  - e não gap funcional urgente

### Leitura objetiva
- eu não vejo mais um ajuste pequeno e óbvio que justifique insistir agora neste mesmo eixo
- a vitrine parece:
  - mais convidativa
  - mais memorável
  - mais desejável
- sem perder:
  - honestidade
  - continuidade
  - segurança de navegação

### Decisão prática
- este eixo de **merchandising leve da vitrine** pode ser considerado **encerrado com sucesso nesta fase**

### Próxima wave
- **Wave AK — Storefront Discovery Wrap-Up Review**
- foco:
  - revisar o storefront antes da compra como um todo
  - depois dos ganhos já consolidados em:
    - catálogo
    - PDP

## Wave AK — Storefront Discovery Wrap-Up Review
- a revisão do storefront antes da compra mostra uma superfície bem mais madura nesta fase
- hoje o fluxo de descoberta e decisão já comunica melhor:
  - o que vale abrir
  - por que vale considerar a combinação atual
  - como seguir com confiança até o checkout

### O que ficou mais forte
- **catálogo**
  - a vitrine ficou mais editorial, convidativa e coerente com o detalhe
- **PDP**
  - o detalhe ficou mais convincente sem perder honestidade, clareza de variante e segurança de decisão
- **continuidade entre superfícies**
  - catálogo e PDP agora contam uma história comercial mais alinhada, sem ruptura desnecessária

### O que ainda pode evoluir no futuro
- refinamentos pequenos de:
  - descoberta por coleção
  - protagonismo visual de merchandising
  - densidade comercial acima da grade e no topo do detalhe
- mas isso já parece:
  - refinamento futuro
  - e não gap funcional urgente do storefront

### Leitura objetiva
- eu não vejo mais um ajuste pequeno e óbvio antes da compra que justifique insistir agora neste mesmo eixo
- o storefront parece:
  - mais claro
  - mais desejável
  - mais coerente
- sem perder:
  - segurança de navegação
  - continuidade até o checkout
  - honestidade comercial

### Decisão prática
- o eixo de **storefront discovery / confiança pré-compra** pode ser considerado **encerrado com sucesso nesta fase**

### Próxima wave
- **Wave AL — Checkout Product Experience Review**
- foco:
  - revisar a experiência funcional do checkout como produto
  - depois dos ganhos já consolidados em descoberta, PDP e pós-compra

## Wave FP — Catalog Operational Readiness Review
- a revisão operacional do catálogo mostrou que a UI/admin já possui boa leitura de produto, preço e estoque.
- a lacuna principal era uma triagem objetiva de problemas de publicação por tenant.

### Módulo responsável
- `catalog`
  - dono de `Product`
  - dono de `ProductVariant`
  - dono de preço/estoque da unidade de venda

### Decisão prática
- não alterar regras de publicação agora.
- adicionar triagem CLI, métricas e runbook para problemas operacionais comuns.

## Wave FQ — Catalog Publication Issue CLI Execution
- foi criado comando operacional para listar problemas de publicação do catálogo.

### Escopo executado
- `list_catalog_publication_issues`
- filtros:
  - `--tenant-id`
  - `--issue`
  - `--limit`
- issues detectadas:
  - `status_mismatch`
  - `missing_variant`
  - `missing_default_variant`
  - `missing_price`
  - `stock_unavailable`

## Wave FR — Catalog Publication Metrics Execution
- a detecção de problemas foi extraída para service reutilizável.
- foi criado exporter protegido para métricas Prometheus.

### Escopo executado
- `catalog_publication_issues`
- `catalog_metrics_queries`
- endpoint:
  - `/ops/catalog/metrics/publication-issues/`
- token:
  - `CATALOG_OBSERVABILITY_TOKEN`
- métrica:
  - `hubx_catalog_publication_issue_total{tenant_id,issue}`

## Wave FS — Catalog Observability Pack Execution
- foram criados artefatos de observability para publicação de catálogo.

### Escopo executado
- `infra/observability/prometheus/catalog-scrape.example.yml`
- `infra/observability/prometheus/catalog-alert-rules.yml`
- `infra/observability/grafana/catalog-publication-dashboard.json`
- `infra/observability/alertmanager/catalog-routing.example.yml`
- `docs/modules/catalog-operational-runbook.md`

### Alertas iniciais
- `HubxCatalogStatusMismatchPresent`
- `HubxCatalogMissingVariantPresent`
- `HubxCatalogUnavailablePublishedStockPresent`

### Próxima macro-abordagem recomendada
- **Catalog Operational Wrap-Up Review**
- motivo:
  - catálogo agora tem triagem CLI, métrica, alertas, dashboard e runbook mínimos.

## Wave FT — Catalog Operational Wrap-Up Review
- o pacote operacional de catálogo pode ser considerado completo para esta fase.
- a abordagem adicionou visibilidade e triagem sem bloquear publicação automaticamente.

### O que ficou pronto
- CLI tenant-scoped:
  - `list_catalog_publication_issues`
- endpoint Prometheus:
  - `/ops/catalog/metrics/publication-issues/`
- métrica:
  - `hubx_catalog_publication_issue_total`
- observability:
  - scrape example
  - alert rules
  - dashboard Grafana
  - routing Alertmanager
- runbook:
  - `docs/modules/catalog-operational-runbook.md`

### O que fica fora de escopo
- workflow formal de aprovação editorial
- histórico dedicado de alterações de catálogo
- validação obrigatória de mídia/imagens
- bloqueio automático de publicação
- SLA de publicação

### Próxima macro-abordagem recomendada
- **Customer Data Operational Readiness Review**
- motivo:
  - catálogo, estoque, payments, shipping e notifications já têm pacote operacional; o próximo domínio crítico é revisar qualidade/triagem de dados de clientes e endereços por tenant.

## Wave ZF — Catalog Merchandising Operational Review
- depois do ciclo de customer data/backfill, a próxima abordagem voltou para o eixo pré-compra.
- a vitrine já tinha:
  - variante efetiva
  - preço/compare price
  - disponibilidade
  - curadoria leve
  - ranking inicial por prioridade de conversão
- gap restante:
  - faltava um sinal determinístico compacto para classificar o tipo de decisão que cada card está tentando provocar.
- decisão:
  - adicionar `catalog_card_decision_signal` na query layer
  - manter o sinal interno/contratual, sem mudar layout nem bloquear cards

## Wave ZG — Catalog Card Decision Signal Execution
- novo sinal por produto:
  - `acompanhar_reposicao`
  - `reserva_planejada`
  - `decisao_rapida_com_oferta`
  - `decisao_rapida`
  - `oferta_editorial`
  - `oferta_para_comparar`
  - `destaque_editorial`
  - `compra_pronta`
- a derivação usa apenas sinais já existentes:
  - `stock_state`
  - `compare_price`
  - `is_featured`
- isso permite:
  - testar merchandising sem depender de texto longo
  - apoiar futuros filtros/analytics
  - preservar o contrato visual atual

### Próxima wave
- **Wave ZH — Catalog Merchandising Wrap-Up Review**
- foco:
  - decidir se o sinal já é suficiente nesta fase
  - ou se vale expor esse signal em métricas/admin antes de continuar o roadmap

## Wave ZH — Catalog Merchandising Wrap-Up Review
- decisão objetiva:
  - o `catalog_card_decision_signal` já é útil como contrato interno, mas fica mais valioso se entrar no exporter existente de catálogo.
- motivo:
  - o sinal ajuda a entender composição comercial da vitrine por tenant
  - não exige novo endpoint
  - não precisa virar alerta neste momento
- recorte escolhido:
  - expor métrica Prometheus
  - não alterar admin, ranking ou UI nesta fase

## Wave ZI — Catalog Decision Signal Metrics Execution
- o exporter de catálogo agora também expõe:
  - `hubx_catalog_card_decision_signal_total{tenant_id,signal}`
- a métrica usa o mesmo endpoint protegido:
  - `/ops/catalog/metrics/publication-issues/`
- objetivo:
  - observar quantos cards por tenant estão em cada intenção comercial
  - apoiar leitura de merchandising sem parsear textos longos
  - preparar futura análise de conversão por sinal

### Próxima abordagem eleita
- **Checkout Session Operational Readiness Review**
- motivo:
  - catálogo/vitrine agora tem sinal comercial observável
  - o próximo eixo natural é revisar se sessões de checkout abertas, abandonadas ou concluídas têm triagem operacional suficiente

## Wave ZJ — Storefront/PDP Conversion Review
- a abordagem voltou para o ponto mais próximo de receita: detalhe do produto e avanço para checkout.
- a PDP já possuía:
  - variante efetiva
  - preço e compare price
  - disponibilidade por variante
  - mídia coerente com variante
  - CTA diferente para pronta entrega, encomenda e sem estoque
- lacuna encontrada:
  - a decisão de compra estava espalhada entre descrição, estoque, helper do CTA e note de compra.
  - faltava um bloco curto, escaneável e determinístico respondendo: “posso confiar neste preço, nesta disponibilidade e neste próximo passo?”.
- decisão:
  - adicionar `pdp_decision_checks` na query layer storefront.
  - renderizar uma faixa compacta na PDP antes do formulário/CTA.
  - manter o fluxo sem novas escritas, sem eventos novos e sem alterar ativação do checkout.

## Wave ZK — PDP Decision Checks Execution
- a PDP agora exibe um resumo de decisão com três sinais:
  - preço confirmado
  - disponibilidade ou restrição atual
  - próximo passo seguro/checkout sem surpresa
- os textos variam por `stock_state`:
  - `in_stock`
  - `low_stock`
  - `backorder`
  - `out_of_stock`
- para produtos sem estoque, o bloco explicita que o checkout não deve iniciar agora.
- para produtos sob encomenda, o bloco reforça reserva e confirmação de prazo antes do pagamento.
- para produtos em estoque/baixo estoque, o bloco reforça continuidade de preço, variante e disponibilidade até o checkout.

### Boundary
- `catalog.application.storefront_catalog_queries` deriva os sinais.
- `catalog.interfaces.ProductDetailView` apenas repassa contexto.
- `product_detail_page.html` apenas renderiza a faixa.
- nenhum módulo externo é chamado pela PDP decision strip.

## Search & Discovery Foundation Review

### Contexto

A trilha de Trust & Social Proof encerrou com summaries de reviews aprovadas nos cards da vitrine.

A vitrine agora possui sinais suficientes para uma primeira revisão estruturada de descoberta:

- texto de busca (`q`);
- categoria;
- filtros rápidos;
- preço e compare price;
- estoque/availability;
- `is_featured`;
- `catalog_card_decision_signal`;
- proof social via summary de reviews aprovadas;
- PDP com decisão, badge e review em destaque.

### Estado atual

`CatalogListView` ainda aplica busca/filtros em memória sobre `storefront_catalog_queries.list_products(...)`.

O ranking inicial vem de `_catalog_initial_order_key` na query layer do storefront, antes dos filtros da view.

Hoje a ordenação considera sinais comerciais internos, mas ainda não formaliza um contrato de ranking que combine:

- intenção comercial;
- disponibilidade;
- oferta;
- destaque editorial;
- prova social.

### Módulo responsável

- `catalog` é dono da descoberta storefront.
- `reviews` fornece apenas summaries approved-only via `reviews.application`.
- templates apenas renderizam sinais já calculados.

### Lacunas prioritárias

1. **Contrato explícito de ranking**
   - hoje existe ordenação inicial, mas o score/razão não é exposto como contrato.

2. **Integração de prova social no ranking**
   - reviews aparecem no card, mas ainda não influenciam a ordem.

3. **Ordenação selecionável**
   - não há `sort=` público para “relevância”, “menor preço”, “maior avaliação” ou “novidades”.

4. **Busca ainda simples**
   - busca cobre nome, marca e SKU, mas não descrição/categoria normalizada nem sinônimos.

### Decisão de fundação

O próximo passo não deve ser criar busca externa nem motor avançado.

O menor passo seguro é formalizar um **Discovery Ranking Contract** dentro de `catalog.application`, usando sinais já disponíveis.

Esse contrato deve:

- manter tenant-scope;
- ser determinístico;
- explicar o motivo do ranking;
- não consultar ORM de reviews em loop;
- aceitar futuramente summaries bulk de reviews;
- preservar filtros atuais.

### Guardrails

- não introduzir Elasticsearch/serviço externo agora;
- não mover busca para template;
- não ordenar por review sem summary bulk;
- não misturar reviews ORM dentro de catalog query layer;
- não quebrar filtros rápidos existentes;
- não alterar paginação sem testes.

### Decisão

**Go para iniciar Search & Discovery com contrato explícito de ranking.**

**No-Go para search engine externo nesta fase.**

**No-Go para sort público antes de consolidar ranking base.**

### Próxima wave recomendada

**Search & Discovery Wave 1 — Storefront Discovery Ranking Contract Review**

Revisar o ranking atual da vitrine e definir o menor contrato de score/razão usando estoque, oferta, destaque, decisão comercial e prova social.

## Search & Discovery Wave 1 — Storefront Discovery Ranking Contract Review

### Estado atual

`catalog.application.storefront_catalog_queries` já ordena a vitrine por `_catalog_initial_order_key(...)`.

A ordenação atual é determinística e considera:

- status do produto, com `draft` depois dos produtos publicáveis;
- disponibilidade, priorizando `low_stock`, depois `in_stock`, `backorder` e `out_of_stock`;
- presença de `compare_price`;
- `is_featured`;
- nome do produto como desempate estável.

`CatalogListView` aplica busca, categoria e filtros rápidos depois dessa ordenação inicial, e só então pagina os resultados.

As summaries de reviews aprovadas entram apenas depois da paginação, para decorar os cards visíveis. Portanto, elas ainda não podem influenciar ranking global sem mudar o ponto de coleta para antes da paginação.

### Contrato recomendado

O ranking de descoberta deve virar um contrato explícito do módulo `catalog`, ainda dentro da camada `application`.

Campos mínimos recomendados para a próxima execução:

- `discovery_rank_score`: score numérico determinístico, derivado dos sinais catalog-owned;
- `discovery_rank_reason`: razão curta e estável para debug/UI/admin futuro;
- `discovery_rank_components`: decomposição opcional dos sinais usados, útil para testes e observabilidade.

Primeira versão do score:

- usa apenas sinais nativos de catálogo: status, estoque, oferta, destaque editorial e `catalog_card_decision_signal`;
- mantém tenant-scope pelo mesmo `tenant_id` já exigido por `list_products(...)`;
- não consulta ORM de reviews;
- não adiciona `sort=` público;
- não muda para search engine externo.

Prova social pode entrar depois como componente pequeno e limitado, mas somente quando existir summary bulk do conjunto filtrado antes da paginação. Até lá, reviews seguem como sinal visual, não sinal de rank.

### Guardrails

- `catalog` continua dono da regra de descoberta storefront.
- `reviews` só pode fornecer summaries via `reviews.application`, nunca ORM importado dentro da query de catálogo.
- templates continuam sem lógica de ranking.
- ranking deve ser estável para o mesmo tenant e mesmo conjunto de produtos.
- paginação não deve mudar sem teste específico de ordem.
- nenhum evento novo é necessário nesta wave.

### Go/No-Go

**Go** para transformar o ranking implícito em score/razão explícitos.

**Go** para começar com score catalog-native e preservar comportamento visual.

**No-Go** para usar reviews no ranking enquanto as summaries ainda forem coletadas apenas por página.

**No-Go** para expor ordenação pública ou mecanismo externo de busca nesta fase.

### Próxima wave recomendada

**Search & Discovery Wave 2 — Discovery Ranking Signal Execution**

Implementar `discovery_rank_score`, `discovery_rank_reason` e, se couber sem ruído, `discovery_rank_components` em `storefront_catalog_queries`, mantendo a ordem atual como referência de compatibilidade.

## Search & Discovery Wave 2 — Discovery Ranking Signal Execution

### Execução

`catalog.application.storefront_catalog_queries` agora enriquece cada produto storefront com:

- `discovery_rank_score`;
- `discovery_rank_reason`;
- `discovery_rank_components`.

O score inicial é determinístico e catalog-owned. Ele considera:

- status do produto;
- disponibilidade derivada da variante efetiva;
- oferta via `compare_price`;
- destaque editorial via `is_featured`;
- `catalog_card_decision_signal`.

### Compatibilidade

A ordenação da vitrine continua usando `_catalog_initial_order_key(...)`.

Nesta wave, o novo score é um contrato observável/testável, não uma mudança de comportamento de ordenação.

Isso preserva:

- paginação atual;
- filtros rápidos;
- busca simples em memória;
- cards existentes;
- isolamento tenant-scoped por `list_products(tenant_id=...)`.

### Boundary

- `catalog.application` calcula score, razão e componentes.
- `catalog.interfaces` não passa a ordenar por esse score nesta etapa.
- `reviews` permanece fora do cálculo, porque summaries aprovadas ainda entram após a paginação.
- templates não recebem lógica nova.
- nenhum evento novo é emitido.

### Testes

Foram adicionadas validações de contrato nos testes de storefront para garantir que produtos fallback e persistidos exponham:

- score inteiro;
- componentes esperados;
- razão de ranking não vazia.

### Próxima wave recomendada

**Search & Discovery Wave 3 — Discovery Score Ordering Review**

Comparar a ordem atual com `discovery_rank_score` e decidir se o score já deve assumir a ordenação real ou permanecer apenas como sinal observável por mais uma wave.

## Search & Discovery Wave 3 — Discovery Score Ordering Review

### Comparação realizada

A ordem atual foi comparada com uma ordenação por `discovery_rank_score` decrescente, usando nome como desempate estável.

Resultado no fallback storefront:

1. `tenis-hubx-runner` — `in_stock`, oferta, destaque, `oferta_editorial`, score `1450`;
2. `mochila-hubx-urban` — `backorder`, oferta, `reserva_planejada`, score `1250`;
3. `camiseta-hubx-performance` — produto draft/oferta, `oferta_para_comparar`, score `405`.

A ordem por score ficou equivalente à ordem atual.

No fixture persistido mínimo, há apenas um produto tenant-scoped, então a comparação não encontra divergência real de ordenação, mas confirma que o payload persistido já recebe score/razão.

### Leitura de risco

A troca parece segura em termos de intenção comercial, porque o score reproduz os principais sinais da chave atual:

- produtos não draft continuam acima de draft;
- baixa disponibilidade comprável continua forte;
- oferta e destaque continuam como reforços;
- backorder fica abaixo de pronta entrega, mas acima de produto draft;
- produto sem estoque segue sem prioridade de compra imediata.

O risco restante não está no score em si, mas em trocar o mecanismo real de ordenação sem teste explícito de compatibilidade.

### Decisão

**Go controlado** para fazer o score assumir a ordenação real na próxima wave.

**No-Go** para misturar reviews no score nesta troca.

**No-Go** para expor `sort=` público junto com essa mudança.

### Contrato para execução

A próxima execução deve:

- trocar `list_products(...)` para ordenar por uma chave baseada em `discovery_rank_score`;
- manter desempate determinístico por nome;
- garantir que a ordem atual do fallback continue estável;
- cobrir ao menos um caso persistido com produto ativo, draft/backorder/oferta para validar precedência;
- preservar tenant-scope e filtros atuais.

### Próxima wave recomendada

**Search & Discovery Wave 4 — Discovery Score Ordering Execution**

Fazer `discovery_rank_score` assumir a ordenação real de `storefront_catalog_queries.list_products(...)`, com teste de compatibilidade e sem alterar interface pública.

## Search & Discovery Wave 4 — Discovery Score Ordering Execution

### Execução

`storefront_catalog_queries.list_products(...)` agora ordena produtos por uma chave baseada em `discovery_rank_score`.

A chave real passou a usar:

- `discovery_rank_score` decrescente;
- nome do produto como desempate determinístico.

O contrato de score continua sendo calculado em `catalog.application`, com sinais nativos do catálogo:

- status;
- disponibilidade;
- oferta;
- destaque editorial;
- `catalog_card_decision_signal`.

### Compatibilidade preservada

A interface pública não mudou:

- não há novo parâmetro `sort=`;
- templates não ganharam lógica de ordenação;
- reviews continuam fora do ranking;
- filtros rápidos e busca seguem aplicados pela view sobre a lista tenant-scoped;
- paginação passa a refletir a ordem por score, mas sem alteração de tamanho ou payload visual.

### Testes

Foram adicionados testes para:

- validar que o fallback storefront mantém a ordem esperada por score;
- validar que produtos persistidos com estados diferentes são ordenados por `discovery_rank_score`;
- garantir que os scores retornados já vêm em ordem decrescente.

### Boundary

- módulo responsável: `catalog`;
- documentação existente: `docs/modules/catalog.md` e decisão em `DECISIONS.md`;
- multi-tenant preservado por `list_products(tenant_id=...)`;
- sem quebra de fronteira com `reviews`;
- sem eventos novos;
- ciclo de request permanece `View -> catalog.application -> response`.

### Próxima wave recomendada

**Search & Discovery Wave 5 — Discovery Ranking Storefront UX Review**

Revisar se vale expor a razão do ranking ou pequenos sinais de descoberta na UI/admin, ou se o score deve ficar apenas interno antes de avançar para filtros/sort público.

## Search & Discovery Wave 5 — Discovery Ranking Storefront UX Review

### Superfícies revisadas

A listagem storefront já comunica os principais motivos de decisão sem mencionar ranking:

- `results_meta` explica o recorte atual, busca, categoria e filtro rápido;
- `product_card.html` exibe preço, compare price, meta, variante, curadoria, estoque, disponibilidade, review summary e helper de clique;
- `_build_storefront_product_card(...)` adapta copy por filtro rápido (`offer`, `featured`, `quick_buy`);
- reviews aprovadas aparecem como prova social visual somente nos cards paginados;
- `discovery_rank_reason` existe no payload application, mas ainda não é passado para o card.

### Decisão de UX

**No-Go para expor `discovery_rank_score` no storefront.**

Score numérico é sinal operacional, não linguagem de compra.

**No-Go para exibir `discovery_rank_reason` diretamente no card nesta wave.**

Os cards já possuem `curation_note`, `availability_note`, `stock_helper`, `price_helper` e `click_helper`. Repetir a razão de ranking criaria ruído e poderia soar como explicação algorítmica desnecessária.

**Go para manter o ranking invisível ao cliente por enquanto.**

A experiência deve continuar orientada por benefícios compreensíveis:

- oferta ativa;
- pronta entrega;
- poucas unidades;
- destaque editorial;
- reserva/backorder;
- prova social aprovada.

### Guardrails

- não mostrar score bruto em UI pública;
- não prometer “mais relevante” sem `sort=` público e testes de ranking;
- não dizer que reviews influenciam ordem enquanto reviews seguem pós-paginação;
- não duplicar no card mensagens já cobertas por curadoria/estoque/preço;
- manter explicabilidade do ranking em application/tests/docs antes de levar para admin.

### Próxima oportunidade de UX

Se houver exposição futura, ela deve ser sutil e sem score:

- uma frase de vitrine no header, por exemplo “Ordenado por disponibilidade, oferta e curadoria da loja”;
- ou uma superfície admin/ops para auditar score e componentes por tenant.

### Próxima wave recomendada

**Search & Discovery Wave 6 — Discovery Ranking Admin Observability Review**

Revisar se `discovery_rank_score`, razão e componentes devem aparecer primeiro em admin/ops, onde explicabilidade ajuda o merchant sem poluir a experiência do comprador.

## Search & Discovery Wave 6 — Discovery Ranking Admin Observability Review

### Revisão

Admin/ops é a primeira superfície adequada para explicabilidade de ranking.

Motivos:

- merchant precisa entender por que um produto ganhou prioridade de descoberta;
- score e componentes são linguagem operacional, não linguagem de comprador;
- a lista admin já concentra status, SKU, estoque e atualização;
- a exposição pode ser read-only, sem criar novo fluxo de edição;
- tenant-scope pode ser preservado usando o mesmo contrato de `storefront_catalog_queries`.

### Decisão

**Go para uma observabilidade admin mínima.**

O menor recorte seguro é mostrar na lista admin, somente quando houver tenant resolvido:

- score de descoberta;
- razão do ranking;
- componentes compactos de status, estoque, oferta, destaque e sinal comercial.

**No-Go para editar pesos no admin.**

**No-Go para criar endpoint novo.**

**No-Go para usar essa superfície como promessa pública de relevância.**

## Search & Discovery Wave 7 — Discovery Ranking Admin Observability Execution

### Execução

A lista admin de produtos agora pode exibir uma coluna `Descoberta` quando a requisição possui tenant resolvido.

A coluna mostra:

- `discovery_rank_score`;
- `discovery_rank_reason`;
- resumo dos componentes do score.

### Boundary

- `catalog.interfaces` só monta a célula read-only;
- o cálculo continua em `catalog.application.storefront_catalog_queries`;
- não há escrita, evento novo, migration ou configuração;
- tenants sem produtos persistidos continuam sem fallback global indevido;
- admin sem tenant resolvido não mostra a coluna, evitando misturar contexto global com ranking storefront.

### Teste

Foi adicionado teste cobrindo a lista admin tenant-scoped com:

- coluna `Descoberta`;
- score;
- razão;
- componentes de ranking.

## Search & Discovery Wave 8 — Search & Discovery Track Closure Review

### Resultado da trilha

A trilha entregou:

- contrato explícito de ranking;
- score, razão e componentes determinísticos;
- ordenação real por `discovery_rank_score`;
- guardrail para manter ranking invisível no storefront;
- observabilidade admin read-only;
- documentação e decisões registradas.

### O que ficou deliberadamente fora

- search engine externo;
- `sort=` público;
- edição de pesos pelo merchant;
- reviews influenciando ranking;
- sinônimos, fuzzy search ou busca full-text;
- analytics de conversão por ranking.

### Critério de encerramento

**Go para encerrar Search & Discovery Foundation neste ponto.**

O sistema agora tem base suficiente para descoberta inicial sem transformar a trilha em motor de busca completo.

### Próxima abordagem recomendada

**Storefront Filtering & Sorting Productization Review**

Próxima trilha possível: decidir se vale expor `sort=` público e filtros adicionais para cliente, agora que o ranking base já está explícito, testado e observável.

## Storefront Filtering & Sorting Productization Review

### Estado atual

A vitrine storefront já possui filtros públicos simples:

- busca textual por nome, marca e SKU via `q`;
- categoria via `category`;
- filtro rápido via `quick_filter`;
- paginação preservando os parâmetros ativos.

Os filtros rápidos atuais cobrem:

- `featured`;
- `quick_buy`;
- `in_stock`;
- `low_stock`;
- `backorder`;
- `offer`.

A ordenação padrão já usa `discovery_rank_score`, mas ainda não existe `sort=` público.

### Módulo responsável

- `catalog` é dono da productização de descoberta storefront.
- `reviews` só deve participar quando houver summary bulk antes da paginação.
- templates devem apenas renderizar opções e estados vindos da view/query layer.

### Decisão de produto

**Go para productizar `sort=` público mínimo.**

O menor contrato útil deve começar com:

- `recommended`: padrão atual por `discovery_rank_score`;
- `price_asc`: menor preço primeiro;
- `price_desc`: maior preço primeiro;
- `name_asc`: nome A-Z.

**No-Go nesta abordagem inicial para:**

- “mais avaliados”, porque reviews ainda entram pós-paginação;
- “mais recentes”, porque ainda não há narrativa/UX clara para novidades;
- sort por estoque bruto, porque estoque é operacional e pode induzir leitura ruim;
- múltiplos filtros facetados avançados;
- busca full-text/sinônimos/fuzzy search.

### Guardrails

- `recommended` deve continuar sendo o default sem exigir query param.
- `sort` inválido deve cair com segurança para `recommended`.
- paginação deve preservar `sort`.
- sort deve ser aplicado depois de busca/categoria/filtro rápido e antes da paginação.
- preço deve usar o preço efetivo da variante destacada, não `Product`.
- `sort=` público não deve alterar tenant-scope.
- reviews não devem ser mencionadas como critério de ordenação.

### UX recomendada

Expor `sort` no mesmo `filter_bar`, como select adicional:

- label: `Ordenar por`;
- default: `Recomendados`;
- ajuda contextual curta: “Recomendados usa disponibilidade, oferta e curadoria da loja.”

Não exibir score, razão ou componentes no storefront.

### Próxima wave recomendada

**Storefront Filtering & Sorting Wave 1 — Public Sort Contract Execution**

Implementar `sort=` mínimo na listagem storefront, preservando filtros existentes, paginação e fallback seguro para `recommended`.

## Storefront Filtering & Sorting Wave 1 — Public Sort Contract Execution

### Execução

A listagem storefront agora aceita `sort=` público mínimo:

- `recommended`;
- `price_asc`;
- `price_desc`;
- `name_asc`.

O sort é normalizado pela view:

- valor ausente usa `recommended`;
- valor inválido cai para `recommended`;
- `recommended` preserva a ordem por `discovery_rank_score`;
- preço usa o preço efetivo da variante destacada.

### Ordem do pipeline

O pipeline storefront ficou:

1. carregar produtos tenant-scoped por `storefront_catalog_queries.list_products(...)`;
2. aplicar busca;
3. aplicar categoria;
4. aplicar filtro rápido;
5. aplicar `sort=`;
6. paginar;
7. buscar review summaries apenas da página visível;
8. renderizar cards.

### UI

O `filter_bar` agora recebe dois selects públicos:

- `Filtro rápido`;
- `Ordenar por`.

O helper do sort explica o critério sem expor score:

- recomendados usam disponibilidade, oferta e curadoria da loja;
- preço usa a variante em destaque;
- nome usa ordem alfabética.

### Testes

Foram adicionados testes para:

- menor preço;
- maior preço;
- nome A-Z;
- preservação de `sort` na paginação;
- fallback seguro para `recommended` quando `sort` é inválido.

## Storefront Filtering & Sorting Wave 2 — Public Sort UX Guardrail Review

### Revisão

O sort público melhora controle do cliente sem transformar a vitrine em motor de busca completo.

Decisões UX mantidas:

- não exibir score;
- não dizer “mais relevante” como promessa absoluta;
- não sugerir que reviews influenciam ordenação;
- não criar sort por avaliação nesta etapa;
- não criar sort por estoque bruto.

### Estado do contrato

`recommended` é a experiência padrão e continua sendo a recomendação da loja.

Sorts alternativos são utilitários:

- preço menor;
- preço maior;
- nome A-Z.

### Próxima oportunidade

Antes de adicionar novos sorts, a próxima evolução deveria atacar um destes pontos:

- busca textual mais robusta;
- filtros facetados por faixa de preço/categoria;
- review summaries antes da paginação para permitir sort por avaliação;
- analytics de uso de sort/filtro.

## Storefront Filtering & Sorting Wave 3 — Track Closure Review

### Resultado

A abordagem entregou:

- contrato público de `sort=`;
- UI no filtro existente;
- preservação de paginação;
- fallback seguro;
- testes de comportamento;
- documentação e decisão arquitetural.

### Fora de escopo preservado

- busca externa;
- full-text/fuzzy;
- sort por reviews;
- sort por novidades;
- facets avançados;
- edição merchant de pesos de ranking.

### Encerramento

**Go para encerrar Storefront Filtering & Sorting neste ponto.**

A vitrine agora possui descoberta recomendada, filtros rápidos e ordenação pública mínima. O próximo ganho relevante não é adicionar mais opções de sort, mas decidir se a busca/facets merecem uma trilha própria.

### Próxima abordagem recomendada

**Storefront Search Quality Review**

Revisar a qualidade da busca textual atual, ainda baseada em nome, marca e SKU, e decidir se vale evoluir para descrição, categoria normalizada, sinônimos ou full-text simples no banco.

## Storefront Search Quality Review

### Módulo responsável

O módulo responsável continua sendo `catalog`.

A busca pública da vitrine opera sobre produtos tenant-scoped carregados por `storefront_catalog_queries.list_products(...)` e filtrados na `CatalogListView`.

### Estado atual

A busca atual usa `q=` e compara o termo com:

- nome do produto;
- marca;
- SKU.

O pipeline atual permanece:

1. carregar produtos do tenant;
2. aplicar busca;
3. aplicar categoria;
4. aplicar filtro rápido;
5. aplicar ordenação pública;
6. paginar;
7. enriquecer summaries visíveis;
8. renderizar.

### Diagnóstico

A busca atual é segura, determinística e leve, mas ainda não é uma busca de qualidade.

Lacunas principais:

- categoria visível não participa do match;
- descrição curta/longa não participa do match;
- textos enriquecidos de card não participam do match;
- não há normalização de acento/diacríticos;
- não há tokenização explícita para consultas com múltiplas palavras;
- não há sinônimos;
- não há full-text, fuzzy search ou índice externo.

### Decisão de evolução

**Go para uma evolução incremental de busca textual leve.**

A próxima execução deve expandir a superfície textual pesquisável sem introduzir motor de busca externo.

Escopo recomendado:

- normalizar consulta e campos pesquisáveis;
- considerar nome, marca, SKU, categoria, descrição e textos públicos já derivados para card;
- manter matching em memória sobre a lista tenant-scoped atual;
- preservar o pipeline atual de filtros, sort e paginação;
- atualizar copy de empty state para refletir a nova superfície.

### Fora de escopo

Não implementar nesta etapa:

- PostgreSQL full-text;
- fuzzy search;
- sinônimos;
- ranking próprio de busca;
- busca por reviews;
- analytics de termo pesquisado;
- dependência de serviço externo.

### Guardrails multi-tenant

- `q=` nunca deve consultar produtos fora do tenant resolvido.
- A busca deve operar apenas sobre dados retornados pelo query service tenant-scoped.
- Nenhum fallback global deve ser introduzido.
- Nenhum detalhe interno de outro módulo deve entrar no match público.

### Impacto arquitetural

- Eventos: sem impacto.
- Ciclo de requisição: sem mudança estrutural.
- Fronteiras: permanece em `catalog`.
- Documentação: esta revisão registra o contrato antes da execução.

### Próxima wave recomendada

**Storefront Search Quality Wave 1 — Search Surface Expansion Execution**

Implementar a expansão mínima da busca textual, preferencialmente com helper puro e testável em `catalog`, mantendo a view fina e sem criar motor de busca prematuro.

## Storefront Search Quality Wave 1 — Search Surface Expansion Execution

### Execução

A busca pública da vitrine foi expandida de forma incremental.

`q=` agora considera:

- nome;
- marca;
- SKU;
- categoria;
- descrição;
- descrição curta;
- textos públicos derivados para card;
- resumo/label da variante efetiva.

### Normalização

A busca agora normaliza:

- caixa;
- espaços repetidos;
- acentos/diacríticos.

Consultas como `acessorios` conseguem encontrar produtos com categoria `Acessórios`.

Consultas com múltiplos termos usam semântica simples de todos os termos presentes no texto pesquisável.

### Fronteira de módulo

O matching textual foi extraído para helper puro em `catalog.application`, evitando concentrar a regra na view.

A `CatalogListView` continua responsável por orquestrar request/contexto, enquanto a regra de match fica testável fora da camada de interface.

### Multi-tenant

A expansão preserva o tenant-scope:

1. a lista de produtos continua vindo de `storefront_catalog_queries.list_products(tenant_id=...)`;
2. o match opera apenas sobre essa lista já escopada;
3. nenhum fallback global novo foi introduzido.

### Testes

Foram adicionados testes para:

- match por categoria sem acento;
- match por termos de descrição;
- match por termos públicos de card/variante;
- copy de empty state alinhada à nova superfície.

## Storefront Search Quality Wave 2 — Search UX Guardrail Review

### Revisão

A busca pública ficou mais útil sem prometer relevância avançada.

Decisões preservadas:

- não exibir score de busca;
- não misturar discovery ranking com matching textual;
- não usar reviews como match;
- não criar sinônimos implícitos;
- não adicionar fuzzy search;
- não criar índice externo.

### Semântica pública

A busca deve ser descrita como consulta textual sobre dados públicos do catálogo.

Copy recomendada:

- “nome, marca, SKU, categoria e descrição”;
- evitar “mais relevante”;
- evitar promessa de inteligência semântica.

### Pipeline preservado

O pipeline segue:

1. carregar produtos tenant-scoped;
2. aplicar busca textual;
3. aplicar categoria;
4. aplicar filtro rápido;
5. aplicar sort;
6. paginar;
7. enriquecer summaries visíveis.

## Storefront Search Quality Wave 3 — Track Closure Review

### Resultado

A abordagem entregou:

- superfície textual ampliada;
- normalização simples e previsível;
- suporte a consultas sem acento;
- suporte a múltiplos termos;
- helper de application testável;
- copy pública atualizada;
- testes de regressão.

### Fora de escopo preservado

- PostgreSQL full-text;
- fuzzy search;
- sinônimos;
- autocomplete;
- sugestões de busca;
- analytics de termos;
- search ranking próprio;
- serviço externo.

### Encerramento

**Go para encerrar Storefront Search Quality neste ponto.**

A busca saiu do estágio “nome/marca/SKU” e passou a cobrir a superfície pública essencial do catálogo. A próxima evolução de maior ROI provavelmente não é sofisticar busca ainda mais, mas avaliar filtros facetados reais ou analytics de descoberta para orientar onde investir.

### Próxima abordagem recomendada

**Storefront Faceted Filtering Review**

Revisar se já vale transformar categoria/preço/disponibilidade em facets reais, preservando simplicidade e evitando construir um motor de descoberta antes de sinais de uso.

## Storefront Faceted Filtering Review

### Módulo responsável

O módulo responsável continua sendo `catalog`.

Facets públicas da vitrine devem operar apenas sobre produtos retornados por `storefront_catalog_queries.list_products(tenant_id=...)`, mantendo a mesma base tenant-scoped já usada por busca, categoria, filtro rápido e sort.

### Estado atual

A vitrine já possui controles que funcionam como filtros simples:

- `q=` para busca textual;
- `category=` para categoria pública;
- `quick_filter=` para recortes de disponibilidade/curadoria;
- `sort=` para ordenação pública mínima.

Esses controles ainda não formam um contrato explícito de facets porque:

- categoria é um select fixo;
- disponibilidade está misturada em `quick_filter`;
- preço existe apenas como sort, não como filtro;
- não há contagem por facet;
- não há faixa de preço;
- não há normalização de valores facetados por tenant;
- não há UI de “facets ativas” além de textos/meta.

### Diagnóstico

Já vale evoluir para facets, mas com escopo mínimo.

O maior ganho para storefront agora é tornar o refinamento mais claro para o cliente, não criar um motor de descoberta complexo.

Facets recomendadas para a primeira execução:

- categoria;
- disponibilidade;
- faixa de preço simples;
- oferta ativa.

### Decisão de evolução

**Go para facets públicas mínimas.**

A primeira execução deve:

- preservar `category=`;
- manter `quick_filter=` por compatibilidade;
- introduzir filtros explícitos opcionais para disponibilidade/preço/oferta apenas se puderem coexistir sem ambiguidade;
- preservar busca antes dos facets;
- preservar sort depois dos facets;
- preservar paginação e querystring;
- não depender de ORM direto na template.

### Contrato mínimo recomendado

Parâmetros públicos candidatos:

- `category=calcados|vestuario|acessorios`;
- `availability=in_stock|low_stock|backorder`;
- `offer=1`;
- `price_min=<decimal>`;
- `price_max=<decimal>`;
- `sort=recommended|price_asc|price_desc|name_asc`;
- `q=<texto>`.

### Ordem do pipeline

O pipeline recomendado passa a ser:

1. carregar produtos tenant-scoped;
2. aplicar busca textual;
3. aplicar categoria;
4. aplicar facets explícitas;
5. aplicar recorte rápido legado/compatibilidade;
6. aplicar sort;
7. paginar;
8. enriquecer summaries visíveis;
9. renderizar estado ativo e empty state.

### Guardrails

- Não criar facet baseada em reviews nesta etapa.
- Não criar faceting por atributos variantes arbitrários.
- Não criar contagens por facet antes de estabilizar o contrato.
- Não criar persistência nova.
- Não criar motor de busca ou índice externo.
- Não misturar filtros públicos com regras admin/operacionais.

### Multi-tenant

Facets devem ser derivadas exclusivamente de produtos do tenant resolvido.

Nenhum valor de facet pode revelar categorias, preços ou disponibilidade de outro tenant.

### Impacto arquitetural

- Eventos: sem impacto.
- Ciclo de requisição: mantém o fluxo atual de request → tenant → view → application query → render.
- Fronteiras: permanece em `catalog`.
- Documentação: esta revisão registra o contrato antes de execução.

### Próxima wave recomendada

**Storefront Faceted Filtering Wave 1 — Facet Contract Execution**

Implementar o menor conjunto explícito de facets públicas, começando por `availability`, `offer`, `price_min` e `price_max`, preservando compatibilidade com `category`, `quick_filter`, `q` e `sort`.

## Storefront Faceted Filtering Wave 1 — Facet Contract Execution

### Execução

A vitrine agora suporta facets públicas explícitas:

- `availability=in_stock|low_stock|backorder`;
- `offer=1`;
- `price_min=<decimal>`;
- `price_max=<decimal>`.

O contrato existente foi preservado:

- `q=`;
- `category=`;
- `quick_filter=`;
- `sort=`.

### Pipeline

A ordem implementada ficou:

1. carregar produtos tenant-scoped;
2. aplicar busca textual;
3. aplicar categoria;
4. aplicar facets explícitas;
5. aplicar `quick_filter` legado/compatibilidade;
6. aplicar sort;
7. paginar;
8. buscar summaries visíveis;
9. renderizar.

### UI

O `filter_bar` ganhou controles adicionais em `extra_filters`:

- disponibilidade;
- oferta;
- preço mínimo;
- preço máximo;
- filtro rápido;
- ordenação.

Facets ativas aparecem em `results_meta` e `filter_description`, sem criar contagens ou promessas de ranking.

### Segurança e compatibilidade

- Valores inválidos de facet são ignorados.
- Preços negativos ou inválidos são ignorados.
- `quick_filter` continua funcionando para URLs antigas.
- Paginação preserva facets válidas na querystring.
- Nenhuma consulta cross-tenant foi introduzida.

### Testes

Foram adicionados testes para:

- disponibilidade;
- faixa de preço;
- oferta com preservação de paginação;
- valores inválidos sem alterar o resultado padrão.

## Storefront Faceted Filtering Wave 2 — Facet UX Guardrail Review

### Revisão

As facets públicas melhoram refinamento sem transformar a vitrine em motor avançado de descoberta.

Decisões preservadas:

- não exibir contagem por facet;
- não exibir score;
- não criar facet por review;
- não criar facet por atributos variantes arbitrários;
- não criar autocomplete;
- não criar dependência de índice externo.

### Semântica pública

As facets devem ser apresentadas como refinamento direto:

- disponibilidade;
- oferta;
- preço;
- categoria.

Evitar linguagem como:

- “resultado inteligente”;
- “mais relevante para você”;
- “recomendado por avaliações”.

### Compatibilidade

`quick_filter` permanece como recorte rápido editorial/legado.

Facets explícitas representam refinamento objetivo. Caso haja conflito entre facet e `quick_filter`, ambos são aplicados em sequência e o empty state deve orientar limpeza do recorte.

## Storefront Faceted Filtering Wave 3 — Track Closure Review

### Resultado

A abordagem entregou:

- contrato público mínimo de facets;
- UI no filtro existente;
- preservação de busca, categoria, quick filter, sort e paginação;
- validação de valores inválidos;
- testes de regressão;
- documentação e decisão arquitetural.

### Fora de escopo preservado

- contagens por facet;
- facets por review;
- facets por atributos variantes arbitrários;
- facets persistidas/configuráveis por merchant;
- analytics de uso;
- full-text/fuzzy/index externo;
- personalização de ranking.

### Encerramento

**Go para encerrar Storefront Faceted Filtering neste ponto.**

A vitrine agora possui descoberta recomendada, busca textual ampliada, ordenação pública e facets mínimas. O próximo ganho de maior ROI deve observar uso/telemetria ou avançar para PDP/conversão, em vez de proliferar filtros sem evidência.

### Próxima abordagem recomendada

**Storefront Discovery Analytics Review**

Revisar eventos/telemetria mínimos para entender uso de busca, sort, facets e PDP clicks antes de sofisticar ranking, filtros ou personalização.

## Storefront Discovery Analytics Review

### Módulo responsável

O módulo responsável pela origem dos sinais continua sendo `catalog`, porque os eventos nascem da vitrine pública de catálogo.

A consolidação futura pode viver em um módulo `analytics`, mas a primeira definição do contrato deve ser catalog-owned para evitar acoplamento prematuro.

### Estado atual

A vitrine já possui:

- ranking recomendado;
- busca textual ampliada;
- sort público;
- facets públicas mínimas;
- PDP com continuidade de card para detalhe;
- métricas Prometheus operacionais de catálogo.

Ainda não há:

- eventos de busca storefront;
- eventos de aplicação de sort/facets;
- eventos de clique em card/PDP;
- agregação de conversão por termo/facet;
- modelo persistido de analytics;
- dashboards de produto para descoberta.

### Diagnóstico

Já vale definir analytics, mas ainda não vale criar um subsistema pesado.

O objetivo inicial deve ser responder perguntas de produto:

- quais termos de busca aparecem;
- quais filtros/facets são usados;
- quais sorts são escolhidos;
- quantos resultados cada refinamento gera;
- quais cards são clicados;
- quais PDPs recebem entrada a partir de catálogo;
- quais consultas/facets resultam em zero resultados.

### Contrato mínimo recomendado

Eventos candidatos:

- `catalog.discovery_viewed`;
- `catalog.search_performed`;
- `catalog.facets_applied`;
- `catalog.sort_changed`;
- `catalog.product_card_clicked`;
- `catalog.product_detail_viewed`.

Payload mínimo comum:

- `tenant_id`;
- `session_key` ou identificador anônimo de sessão;
- `path`;
- `query`;
- `category`;
- `availability`;
- `offer`;
- `price_min`;
- `price_max`;
- `quick_filter`;
- `sort`;
- `result_count`;
- `page`;
- `product_id` quando aplicável;
- `product_slug` quando aplicável.

### Decisão de evolução

**Go para especificar analytics de descoberta como contrato, mas No-Go para persistência pesada nesta wave.**

A primeira execução deve criar uma boundary pequena e testável para registrar intenção de analytics sem obrigar dashboard, fila ou modelo definitivo.

Escopo recomendado para execução:

- definir dataclass/payload de evento de descoberta;
- criar service no `catalog.application`;
- criar publisher no-op ou logger interno substituível;
- chamar o service em pontos explícitos da vitrine;
- testar que payload preserva tenant, query params e result count;
- não armazenar PII;
- não emitir evento cross-tenant.

### Guardrails

- Não registrar e-mail, nome, telefone ou dados pessoais do cliente.
- Não registrar querystring bruta com parâmetros sensíveis.
- Não depender de JavaScript para a primeira versão.
- Não bloquear renderização se analytics falhar.
- Não criar dashboards antes de dados confiáveis.
- Não usar analytics para alterar ranking ainda.

### Multi-tenant

Todo evento deve carregar `tenant_id` resolvido.

Eventos sem tenant resolvido devem ser descartados.

Analytics não pode agregar nem expor dados cruzados entre tenants na camada pública.

### Impacto arquitetural

- Eventos: novo contrato futuro de eventos de descoberta, ainda sem consumidor obrigatório.
- Ciclo de requisição: analytics deve ocorrer após resolver tenant e calcular resultado, sem bloquear resposta.
- Fronteiras: origem em `catalog`, consolidação futura pode ser `analytics`.
- Documentação: esta revisão registra contrato antes de execução.

### Próxima wave recomendada

**Storefront Discovery Analytics Wave 1 — Discovery Event Contract Execution**

Criar o contrato mínimo de evento/service no `catalog.application`, com publisher no-op seguro e testes de payload, sem persistência definitiva nem dashboard.

## Storefront Discovery Analytics Wave 1 — Discovery Event Contract Execution

### Execução

Foi criado o contrato mínimo de analytics de descoberta em `catalog.application`.

A implementação adiciona:

- dataclass de evento de descoberta;
- protocolo de publisher;
- publisher no-op padrão;
- service de emissão segura;
- integração server-side na listagem storefront;
- integração server-side no PDP;
- testes de payload e resiliência.

### Eventos emitidos

Na listagem de catálogo:

- `catalog.discovery_viewed`;
- `catalog.search_performed` quando `q=` está presente;
- `catalog.facets_applied` quando filtros/facets estão presentes;
- `catalog.sort_changed` quando `sort` difere de `recommended`.

No PDP:

- `catalog.product_detail_viewed`.

### Payload

O payload da listagem preserva:

- `tenant_id`;
- `session_key` anônimo quando já existir;
- `path`;
- `query`;
- `category`;
- `availability`;
- `offer`;
- `price_min`;
- `price_max`;
- `quick_filter`;
- `sort`;
- `result_count`;
- `page`.

O payload do PDP preserva:

- `tenant_id`;
- `session_key` anônimo quando já existir;
- `path`;
- `product_id`;
- `product_slug`.

### Guardrails implementados

- Eventos sem `tenant_id` são descartados.
- Falha no publisher não bloqueia renderização.
- Não há persistência nova.
- Não há dashboard novo.
- Não há PII no payload.
- Não há mudança de ranking baseada em analytics.

### Testes

Foram adicionados testes para:

- emissão de eventos de listagem com busca/facets/sort;
- payload tenant-scoped e com contagem de resultados;
- publisher com falha sem quebrar storefront;
- evento de PDP.

## Storefront Discovery Analytics Wave 2 — Analytics Privacy & Operational Guardrail Review

### Revisão

A primeira versão de analytics é deliberadamente pequena.

Decisões preservadas:

- não criar modelo persistido ainda;
- não criar tabela de eventos ainda;
- não criar dashboard de produto ainda;
- não enviar analytics para provider externo;
- não armazenar PII;
- não criar cookies novos apenas para analytics;
- não bloquear request de storefront.

### Semântica operacional

O publisher no-op deixa a boundary pronta para troca futura por:

- gravação em banco;
- fila assíncrona;
- audit log;
- pipeline externo;
- métricas agregadas.

Essa troca deve acontecer atrás do protocolo do publisher, sem reabrir a view.

### Critério para próxima evolução

Só vale persistir quando houver decisão clara sobre:

- retenção;
- anonimização;
- agregação por tenant;
- dashboard/admin surface;
- política de exclusão;
- custo operacional.

## Storefront Discovery Analytics Wave 3 — Track Closure Review

### Resultado

A abordagem entregou:

- contrato de eventos;
- mapa de eventos atualizado;
- service/publisher substituível;
- emissão server-side segura;
- testes de payload;
- resiliência contra falha de analytics;
- documentação e decisão arquitetural.

### Fora de escopo preservado

- persistência de eventos;
- dashboard de analytics;
- agregações;
- tracking client-side;
- click tracking real de card;
- atribuição checkout/conversão;
- personalização de ranking;
- envio para provider externo.

### Encerramento

**Go para encerrar Storefront Discovery Analytics neste ponto.**

O sistema agora tem a boundary necessária para observar descoberta sem acoplar a vitrine a um pipeline definitivo. A próxima evolução de maior ROI deve decidir se persistimos/agregamos esses eventos ou se voltamos para conversão no PDP.

### Próxima abordagem recomendada

**Storefront Discovery Analytics Persistence Review**

Revisar se já vale criar persistência/agregação tenant-scoped para eventos de descoberta, ou se o próximo ciclo deve priorizar PDP conversion antes de analytics operacional.

## Storefront Discovery Analytics Persistence Review

### Módulo responsável

A origem dos eventos continua em `catalog`, mas a persistência deve ser tratada como boundary própria de analytics.

Enquanto não existir um módulo dedicado `analytics`, a implementação mínima pode permanecer em `catalog.application` atrás do protocolo de publisher, desde que:

- não contamine modelos de produto;
- não altere ranking;
- não bloqueie storefront;
- não exponha dados entre tenants.

### Estado atual

Já existe:

- `StorefrontDiscoveryEvent`;
- protocolo `StorefrontDiscoveryAnalyticsPublisher`;
- publisher no-op padrão;
- emissão server-side na listagem storefront;
- emissão server-side no PDP;
- descarte sem `tenant_id`;
- resiliência contra falha do publisher;
- testes de payload.

Ainda não existe:

- modelo persistido de evento;
- retenção definida em código;
- agregação por tenant;
- dashboard/admin surface;
- exclusão/compactação;
- amostragem;
- click tracking real de card.

### Diagnóstico

Já vale persistir um recorte mínimo, mas não vale criar produto completo de analytics.

O objetivo da primeira persistência deve ser apenas gerar evidência para decisões de descoberta:

- termos que geram zero resultado;
- facets mais usadas;
- sorts alternativos usados;
- PDPs visualizados;
- volume de listagem por tenant.

### Decisão de evolução

**Go para persistência mínima de eventos brutos tenant-scoped.**

**No-Go para dashboard, agregações e personalização nesta abordagem.**

### Contrato mínimo recomendado

Modelo candidato:

`StorefrontDiscoveryEventLog`

Campos mínimos:

- `tenant`;
- `event_name`;
- `session_key_hash`;
- `path`;
- `payload`;
- `occurred_at`;

Regras:

- `tenant` obrigatório;
- `event_name` limitado aos eventos catalogados;
- `session_key` não deve ser salvo cru;
- payload deve manter apenas chaves permitidas;
- escrita deve ser best-effort;
- falha de gravação não pode quebrar storefront.

### Retenção inicial

Retenção recomendada para MVP:

- manter eventos brutos por 30 dias;
- agregações futuras podem preservar métricas por mais tempo;
- política de limpeza deve ser documentada antes de produção real.

### Privacidade

Não persistir:

- e-mail;
- nome;
- telefone;
- endereço;
- customer_id;
- querystring bruta;
- IP bruto;
- user-agent bruto.

Persistir somente:

- contexto público de descoberta;
- identificador de sessão hash/anônimo;
- produto/caminho quando aplicável;
- contagens e parâmetros públicos normalizados.

### Guardrails multi-tenant

- Toda linha deve ter `tenant_id`.
- Queries futuras devem exigir tenant explícito.
- Admin global não deve misturar tenants por padrão.
- Nenhum dashboard público deve expor dados de outro tenant.

### Impacto arquitetural

- Eventos: mantém eventos já definidos em `docs/events-map.md`.
- Ciclo de requisição: gravação deve ser best-effort e não bloquear renderização.
- Fronteiras: publisher real deve ficar atrás do protocolo já criado.
- Documentação: esta revisão registra persistência antes de migration/model.

### Próxima wave recomendada

**Storefront Discovery Analytics Persistence Wave 1 — Event Log Model Execution**

Criar modelo/migration de log mínimo tenant-scoped e um publisher persistente substituível, mantendo no-op como fallback em testes/configuração.

## Storefront Discovery Analytics Persistence Wave 1 — Event Log Model Execution

### Execução

Foi criado o modelo persistido mínimo `StorefrontDiscoveryEventLog`.

Campos principais:

- `tenant`;
- `event_name`;
- `session_key_hash`;
- `path`;
- `payload`;
- `occurred_at`.

### Publisher persistente

O contrato de analytics agora possui um publisher Django persistente que:

- aceita apenas nomes de evento catalogados;
- descarta evento sem `tenant_id`;
- transforma `session_key` em hash;
- remove `session_key` do payload persistido;
- filtra o payload por allowlist;
- grava evento bruto tenant-scoped.

O publisher continua best-effort porque o service engole falhas para não bloquear storefront.

### Privacidade

O log persistido não salva:

- sessão crua;
- e-mail;
- nome;
- telefone;
- endereço;
- IP bruto;
- user-agent bruto;
- querystring bruta.

### Testes

Foram adicionados testes para:

- persistência sanitizada;
- hash de sessão;
- remoção de chaves fora da allowlist;
- descarte sem tenant;
- continuidade dos eventos server-side já existentes.

## Storefront Discovery Analytics Persistence Wave 2 — Retention & Query Guardrail Review

### Revisão

A persistência atual é suficiente para evidência inicial, mas ainda não é um produto de analytics.

Decisões preservadas:

- não criar dashboard;
- não criar agregações;
- não criar admin surface;
- não criar tracking client-side;
- não criar cookies novos;
- não usar analytics para ranking.

### Retenção

Retenção recomendada:

- eventos brutos por 30 dias;
- agregações futuras podem viver mais tempo;
- limpeza automática deve ser implementada antes de volume real de produção.

### Query guardrail

Toda consulta futura deve exigir `tenant_id`.

Consultas globais só devem existir para operação interna explícita e nunca para storefront público.

## Storefront Discovery Analytics Persistence Wave 3 — Track Closure Review

### Resultado

A abordagem entregou:

- modelo persistido tenant-scoped;
- migration;
- publisher persistente substituível;
- sanitização de sessão;
- allowlist de payload;
- descarte sem tenant;
- testes de persistência;
- documentação estrutural.

### Fora de escopo preservado

- dashboard;
- agregação;
- exportação;
- limpeza automática;
- amostragem;
- click tracking real de card;
- atribuição até checkout/pedido;
- personalização de ranking.

### Encerramento

**Go para encerrar Storefront Discovery Analytics Persistence neste ponto.**

A vitrine agora consegue registrar eventos brutos mínimos de descoberta por tenant sem capturar PII e sem bloquear a experiência. O próximo ganho deve ser escolher entre retenção/queries admin ou voltar ao funil PDP/conversão.

### Próxima abordagem recomendada

**Storefront PDP Conversion Review**

Revisar se o detalhe do produto já tem CTAs, prova social, continuidade de preço/estoque e feedback de add-to-cart suficientes para converter melhor antes de expandir dashboards de analytics.

## Storefront PDP Conversion Review

### Módulo responsável

O módulo responsável continua sendo `catalog` para apresentação do PDP e contrato de produto.

Integrações envolvidas:

- `cart` para add-to-cart;
- `checkout` para buy-now;
- `reviews` para prova social;
- `catalog` para preço, estoque, variante e mídia;
- `catalog` analytics para `catalog.product_detail_viewed`.

### Estado atual

O PDP já possui:

- galeria de produto;
- título/subtítulo;
- preço e preço comparativo;
- helper de preço;
- seletor de variantes;
- quantidade;
- estado de estoque;
- nota de compra;
- CTA primário `Adicionar ao carrinho`;
- CTA secundário `Comprar agora`;
- reviews aprovadas;
- avaliação em destaque;
- resumo de decisão;
- analytics server-side de visualização do PDP.

### Diagnóstico

O PDP está funcional, mas ainda pode converter melhor em pontos específicos.

Lacunas principais:

- add-to-cart bem-sucedido redireciona direto para carrinho, sem feedback contextual no PDP;
- não há trilha explícita “produto adicionado” com opção de continuar comprando;
- CTA secundário depende do mesmo form, mas a distinção visual/semântica entre add-to-cart e buy-now ainda pode ser reforçada;
- out-of-stock redireciona silenciosamente para o mesmo PDP;
- não há bloco explícito de confiança operacional próximo ao CTA;
- não há tracking específico de intenção CTA, apenas view de PDP;
- não há surface de recomendação/cross-sell pós-PDP.

### Decisão de evolução

**Go para evolução incremental de conversão no PDP.**

O primeiro recorte deve focar feedback de ação e clareza de decisão, sem criar cross-sell, wishlist ou recomendação complexa.

### Escopo recomendado

Primeira execução:

- melhorar feedback de add-to-cart no retorno;
- diferenciar melhor sucesso, conflito de estoque e indisponibilidade;
- preservar idempotência do cart;
- manter buy-now como caminho direto para checkout;
- registrar intenção de CTA em analytics apenas se couber no contrato atual.

### Fora de escopo

Não implementar ainda:

- cross-sell;
- recomendações personalizadas;
- wishlist;
- notify-me real;
- sticky add-to-cart;
- tracking client-side;
- experimentos A/B;
- reviews como ranking de PDP.

### Guardrails

- Preço e estoque continuam vindo de `ProductVariant`.
- Estoque só baixa após pagamento confirmado.
- Add-to-cart não cria pedido.
- Buy-now não deve pular escolha de frete/pagamento.
- Sem PII em analytics.
- Sem lógica de negócio no template.

### Impacto arquitetural

- Eventos: pode exigir extensão futura de analytics para CTA intent.
- Ciclo de requisição: mantém request → tenant → PDP view → application services.
- Fronteiras: PDP apresenta; `cart` e `checkout` executam.
- Documentação: esta revisão define escopo antes de execução.

### Próxima wave recomendada

**Storefront PDP Conversion Wave 1 — Add-To-Cart Feedback Execution**

Adicionar feedback claro pós-add-to-cart no PDP/carrinho, preservando idempotência e sem criar novo funil complexo.

## Storefront PDP Conversion Wave 1 — Add-To-Cart Feedback Execution

### Execução

O fluxo de `Adicionar ao carrinho` no PDP agora retorna para o próprio PDP com feedback contextual.

Antes:

- add-to-cart bem-sucedido redirecionava diretamente para o carrinho;
- o cliente perdia a continuidade da variante/produto revisado.

Agora:

- add-to-cart bem-sucedido preserva o item no carrinho;
- redireciona para o PDP com `cart_feedback=added`;
- exibe alerta contextual no PDP;
- mantém mensagem global de sucesso;
- preserva variante selecionada na URL;
- mantém idempotência do carrinho.

### Estados cobertos

Feedbacks explícitos:

- `added`: produto adicionado ao carrinho;
- `stock-conflict`: quantidade precisa ser revisada;
- `unavailable`: combinação indisponível.

### Guardrails preservados

- `cart` continua responsável pela mutação do carrinho;
- `catalog` apenas apresenta feedback e redireciona;
- estoque não é baixado no add-to-cart;
- pedido não é criado;
- buy-now continua ativando checkout;
- idempotency key continua sendo respeitada.

### Testes

Foram adicionados/ajustados testes para:

- redirecionamento pós-add-to-cart de volta ao PDP;
- renderização do alerta de sucesso;
- preservação da variante selecionada;
- retorno com feedback de indisponibilidade;
- manutenção da idempotência existente.

### Próxima wave recomendada

**Storefront PDP Conversion Wave 2 — CTA Intent Analytics Review**

Revisar se já vale registrar intenção de CTA (`add_to_cart`, `buy_now`, `unavailable`) no contrato de analytics de descoberta/conversão, sem tracking client-side.

## Storefront PDP Conversion Wave 2 — CTA Intent Analytics Review

### Revisão

Com feedback de add-to-cart implementado, o próximo gargalo observável é entender quais CTAs do PDP são usados e com qual resultado.

Decisão:

**Go para analytics server-side de intenção de CTA.**

### Escopo aprovado

Registrar evento quando o POST do PDP recebe intenção:

- `add_to_cart`;
- `buy_now`;
- tentativa indisponível.

Payload mínimo:

- `tenant_id`;
- `session_key`;
- `path`;
- `product_id`;
- `product_slug`;
- `cta_intent`;
- `cta_result`;
- `quantity`;
- `variant_sku`.

### Guardrails

- Não usar JavaScript.
- Não registrar PII.
- Não alterar comportamento do carrinho/checkout.
- Não usar o evento para ranking.
- Não bloquear renderização ou redirecionamento se analytics falhar.

## Storefront PDP Conversion Wave 3 — CTA Intent Analytics Execution

### Execução

Foi adicionado o evento `catalog.pdp_cta_intent` ao contrato persistente de analytics.

O POST do PDP agora registra intenção para:

- add-to-cart bem-sucedido/idempotente;
- add-to-cart indisponível;
- add-to-cart com conflito de estoque;
- buy-now com checkout ativado;
- tentativa em variante indisponível.

### Persistência

O evento usa o publisher persistente existente e passa pela mesma proteção:

- tenant obrigatório;
- sessão em hash;
- payload allowlisted;
- falha best-effort;
- sem PII.

### Testes

Foram adicionados testes para:

- `add_to_cart` registra `catalog.pdp_cta_intent`;
- `buy_now` registra `catalog.pdp_cta_intent`;
- tentativa indisponível registra `catalog.pdp_cta_intent`;
- variante/SKU e quantidade seguem no payload.

## Storefront PDP Conversion Wave 4 — Track Closure Review

### Resultado

A abordagem entregou:

- feedback contextual pós-add-to-cart;
- preservação de variante no retorno ao PDP;
- feedback explícito para indisponibilidade/conflito;
- evento persistente de intenção de CTA;
- testes de fluxo e analytics;
- documentação de eventos.

### Fora de escopo preservado

- cross-sell;
- wishlist;
- notify-me real;
- sticky CTA;
- tracking client-side;
- experimentos A/B;
- personalização;
- recomendação baseada em analytics.

### Encerramento

**Go para encerrar Storefront PDP Conversion neste ponto.**

O PDP agora fecha melhor o ciclo card → detalhe → intenção de compra, com feedback claro e telemetria mínima. A próxima abordagem pode escolher entre endurecer confiança operacional no checkout ou criar uma primeira leitura admin dos eventos de descoberta/conversão.

### Próxima abordagem recomendada

**Storefront Conversion Analytics Admin Review**

Revisar se já vale criar uma leitura admin mínima para eventos de descoberta/PDP, limitada a contagens tenant-scoped e sem dashboard pesado.

## Storefront Conversion Analytics Admin Review

### Módulo responsável

O módulo responsável pela primeira leitura admin pode continuar sendo `catalog`, porque:

- os eventos persistidos são originados no storefront de catálogo;
- o log atual (`StorefrontDiscoveryEventLog`) vive em `catalog`;
- ainda não existe módulo `analytics` dedicado.

Quando houver dashboard/agregações mais amplas, a fronteira pode migrar para `analytics`.

### Estado atual

Já existe:

- log bruto tenant-scoped;
- eventos de descoberta;
- evento de PDP view;
- evento de intenção CTA;
- payload allowlisted;
- sessão com hash;
- testes de persistência;
- rota admin de produtos já existente.

Ainda não existe:

- query service admin para eventos;
- rota admin de analytics;
- template de leitura;
- agregações por evento;
- filtros por tipo de evento;
- retenção automática;
- exportação.

### Diagnóstico

Já vale criar uma leitura admin mínima, mas não um dashboard completo.

Perguntas que a primeira surface deve responder:

- quantos eventos de descoberta existem no tenant;
- quantos PDP views;
- quantos CTA intents;
- quais eventos recentes chegaram;
- quais resultados de CTA aparecem;
- quais termos/filters aparecem nos eventos recentes.

### Decisão de evolução

**Go para admin read-only mínimo.**

**No-Go para dashboard pesado, gráficos, exportação e agregações complexas.**

### Escopo recomendado

Primeira execução:

- criar query service admin tenant-scoped;
- criar rota `/ops/catalog/analytics/`;
- criar template simples reutilizando header/tabela;
- listar contadores por evento;
- listar eventos recentes;
- filtrar opcionalmente por `event_name`;
- exigir tenant resolvido;
- não permitir edição/exclusão.

### Guardrails

- Toda query deve exigir `tenant_id`.
- Não exibir `session_key_hash` por padrão.
- Não exibir payload bruto completo se puder vazar ruído.
- Não criar endpoint público.
- Não criar gráficos ainda.
- Não criar exportação ainda.
- Não misturar tenants.

### Impacto arquitetural

- Eventos: sem novos eventos.
- Ciclo de requisição: admin view → tenant → query service → template.
- Fronteiras: leitura fica em `catalog.application`, view fina em `interfaces`.
- Documentação: esta revisão define escopo antes da execução.

### Próxima wave recomendada

**Storefront Conversion Analytics Admin Wave 1 — Read-Only Surface Execution**

Criar query service, rota e template admin read-only para contadores e eventos recentes tenant-scoped.

## Storefront Conversion Analytics Admin Wave 1 — Read-Only Surface Execution

### Módulo responsável

O módulo responsável continua sendo `catalog`, porque a leitura nasce dos eventos persistidos de descoberta/PDP em `StorefrontDiscoveryEventLog`.

### Execução

Implementado:

- query service `admin_conversion_analytics_queries`;
- rota admin read-only `/ops/catalog/analytics/`;
- template `admin_conversion_analytics_page.html`;
- cards de resumo de eventos tenant-scoped;
- tabela de contadores por `event_name`;
- tabela de eventos recentes;
- filtro opcional por tipo de evento;
- testes de isolamento entre tenants e filtro por evento.

### Contrato da surface

A surface responde apenas perguntas operacionais iniciais:

- quantos eventos foram persistidos no tenant;
- quantos eventos existem no recorte filtrado;
- quais tipos de evento aparecem;
- quais eventos recentes chegaram;
- quais sinais públicos do payload são úteis para leitura rápida.

### Guardrails aplicados

- Toda query recebe `tenant_id` explícito.
- Sem tenant resolvido, o query service retorna queryset vazio.
- `session_key_hash` não é exibido.
- Payload bruto não é renderizado integralmente.
- A view é fina e delega leitura para `catalog.application`.
- A surface é read-only, sem edição, exportação ou gráficos.

### Impacto arquitetural

- Eventos: sem novos eventos.
- Dados: sem nova migration.
- Ciclo de requisição: admin view → tenant resolvido → query service → template.
- Fronteiras: sem dependência de módulo externo.

### Próxima wave recomendada

**Storefront Conversion Analytics Admin Wave 2 — Closure Review**

Encerrar a trilha inicial de analytics admin e decidir se o próximo ROI é dashboard/agregação ou outra frente de conversão.

## Storefront Conversion Analytics Admin Wave 2 — Closure Review

### Resultado

A abordagem entregou a primeira leitura operacional de analytics de conversão storefront.

Entregue:

- persistência prévia de eventos brutos tenant-scoped;
- evento de PDP view;
- evento de intenção de CTA no PDP;
- query service admin dedicado;
- rota `/ops/catalog/analytics/`;
- template admin read-only;
- contadores por tipo de evento;
- eventos recentes com resumo público de payload;
- filtro por `event_name`;
- testes de isolamento entre tenants.

### Decisão de encerramento

**Go para encerrar Storefront Conversion Analytics Admin neste ponto.**

A surface atual já responde a pergunta crítica desta fase: “os sinais de descoberta/PDP/CTA estão chegando por tenant, sem vazar dados e sem virar BI cedo demais?”.

### No-Go deliberado

Não avançar agora para:

- dashboard com gráficos;
- agregações por janela temporal;
- exportação CSV;
- retenção automática;
- alertas operacionais;
- funil completo até checkout/pedido;
- atribuição multi-touch;
- ranking alimentado por analytics.

### Por que parar aqui

O sistema ganhou observabilidade mínima suficiente para validar telemetria de conversão.

Continuar nesta trilha agora tenderia a transformar `catalog` em analytics product antes de existirem volume, perguntas de negócio e cadência de operação que justifiquem isso.

### Riscos residuais aceitos

- eventos brutos ainda não possuem pruning automático;
- não há agregados históricos;
- não há visualização por período;
- não há correlação com pedido/pagamento;
- não há módulo `analytics` dedicado.

Esses riscos são aceitáveis para a fase atual porque a surface é read-only, pequena, tenant-scoped e sem impacto no funil de compra.

### Próxima abordagem recomendada

**Storefront Conversion Optimization Review**

Revisar ganhos de conversão que atuam diretamente no cliente antes de expandir analytics: merchandising na listagem, prova de confiança no PDP, recuperação de carrinho ou fricção entre carrinho e checkout.
# API pública de catálogo

## API Key Public Catalog Products Endpoint Execution

- catálogo expõe o primeiro endpoint público piloto protegido por API key.
- endpoint:
  - `GET /api/v1/catalog/products/`
- autenticação:
  - `ApiKeyAuthentication`
- permissão:
  - `HasApiKeyScope`
- escopo:
  - `read:catalog`
- flag:
  - `API_KEYS_PUBLIC_CATALOG_PRODUCTS_ENABLED`

### Regras

- tenant vem do request/subdomínio.
- endpoint não aceita `tenant_id` por query/body.
- apenas produtos persistidos, ativos e publicados são retornados.
- não há fallback para fixtures.
- payload é read-only e sem PII.
- `page_size` máximo é 50.
- endpoint usa `ApiKeyRateLimitThrottle`.
- limite default vem de `API_KEYS_PUBLIC_CATALOG_PRODUCTS_RATE_LIMIT`.
- estouro retorna `429` com `Retry-After`.

## API Key Public Product Detail Endpoint Execution

- catálogo agora expõe detalhe público de produto protegido por API key.
- endpoint:
  - `GET /api/v1/catalog/products/<slug>/`
- escopo:
  - `read:catalog`
- flag:
  - `API_KEYS_PUBLIC_CATALOG_PRODUCT_DETAIL_ENABLED`
- endpoint operacional:
  - `catalog.products.detail`

### Regras

- tenant vem do request/subdomínio.
- lookup é por slug dentro do tenant atual.
- apenas produto `ACTIVE` e `is_active=True` é retornado.
- não há fallback global ou fixture.
- endpoint usa `ApiKeyAuthentication`, `HasApiKeyScope` e `ApiKeyRateLimitThrottle`.
- payload retorna dados públicos de PDP, imagens públicas e variantes com preço/disponibilidade segura.
- payload não expõe tenant_id, estoque bruto, reserved stock, custo, margem, clientes, pedidos ou pagamentos.
- sucesso registra métrica pública com endpoint `catalog.products.detail`.
