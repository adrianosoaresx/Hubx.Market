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
- no estado atual do repositório, `Admin Products` ainda não possui modelo/tabela persistida utilizável; a query layer detecta essa indisponibilidade explicitamente e mantém fallback seguro até a fonte real existir
- readiness mínima agora existe no módulo:
  - `Product` com `tenant`, status e metadados principais
  - `ProductVariant` para respeitar a regra de preço/estoque por variante
  - `ProductImage` para mídia mínima persistida por URL, com ordenação e imagem principal
- as query layers de `Admin Products` e do storefront já consomem essa estrutura quando houver migração aplicada e registros persistidos
- o seed mínimo `catalog_minimal_seed` permite validar a primeira leitura persistida sem alterar o contrato visual
- enquanto não houver dados reais carregados, o fallback continua intencionalmente ativo

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
