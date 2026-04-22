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
