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
