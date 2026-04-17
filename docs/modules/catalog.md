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
- as query layers de `Admin Products` e do storefront já consomem essa estrutura quando houver migração aplicada e registros persistidos
- o seed mínimo `catalog_minimal_seed` permite validar a primeira leitura persistida sem alterar o contrato visual
- enquanto não houver dados reais carregados, o fallback continua intencionalmente ativo
