# Catálogo

## Como cadastrar um produto

1. Acesse `/ops/catalog/products/`.
2. Clique em criar novo produto.
3. Preencha nome, descrição, marca/categoria em texto simples quando fizer sentido, status e dados comerciais.
4. Informe preço, SKU e estoque na variante padrão.
5. Salve e revise a página do produto na loja.

No Hubx Market, o produto organiza a vitrine, mas a unidade real de venda é a variante.

## Diferença entre produto e variante

Produto é a ficha principal do item: nome, descrição, imagem, marca, categoria e status.

Variante é o SKU vendável: preço, estoque, código de barras, peso, atributos e disponibilidade.

Se um item tem tamanhos, cores ou versões diferentes, cada opção deve virar uma variante.

## Quero vender um produto com tamanhos diferentes

Cadastre um único produto e crie uma variante para cada tamanho.

Exemplo: uma camiseta pode ser o produto, e os tamanhos P, M e G podem ser variantes diferentes.

Cada variante deve ter seu próprio SKU, preço quando necessário e estoque próprio.

Não crie um produto separado para cada tamanho, a menos que sejam itens realmente diferentes para a vitrine.

## Onde fica o preço

O preço fica na `ProductVariant`, não no `Product`.

Isso permite vender o mesmo produto com preços diferentes por tamanho, cor, embalagem ou versão.

## Onde fica o estoque

O estoque fica na `ProductVariant`, não no `Product`.

Cada SKU precisa ter seu próprio saldo para evitar vender a opção errada.

## Como tirar um produto da loja

Use desativação operacional em vez de apagar.

Produto inativo deixa de aparecer para compra, mas preserva histórico, imagens, variantes e referências operacionais.

## Posso apagar produto antigo?

Não apague produto antigo para esconder da loja.

O caminho correto é desativar o produto. Assim ele deixa de aparecer para compra, mas o histórico operacional continua preservado.

Isso é importante porque pedidos antigos, auditoria e referências internas podem depender daquele produto.

## Produto sem estoque deve ser apagado?

Não. Ajuste o estoque da variante ou desative o produto se ele não deve mais aparecer.

Produto sem estoque e produto inativo são situações diferentes: sem estoque indica indisponibilidade da variante; inativo remove o produto da vitrine.

## Boas práticas para catálogo

- Use nomes claros e pesquisáveis.
- Inclua imagem real do produto sempre que possível.
- Mantenha SKU consistente por variante.
- Revise estoque por variante antes de publicar.
- Evite criar produto duplicado quando uma nova variante resolver o caso.
