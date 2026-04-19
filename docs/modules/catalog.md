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
