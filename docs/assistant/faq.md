# FAQ do assistente

## O assistente pode alterar minha loja?

No MVP, não. Ele apenas responde perguntas e registra histórico sanitizado.

## O assistente vê meus pedidos e clientes?

No MVP, não. Ele usa documentação interna, não dados reais da loja.

Essa limitação também protege o isolamento entre tenants, evitando que uma loja consulte dados de outra.

Isso significa que ele pode explicar como acompanhar pedidos, mas não consegue dizer quantos pedidos pendentes existem na sua loja.

Quando precisar ver pedidos reais, acesse `/ops/orders/`.

## Por que o assistente não vê meus pedidos?

Porque o primeiro MVP foi desenhado como guia seguro de uso, sem consultar dados reais da loja.

Essa escolha reduz risco de exposição de dados e evita acesso indevido entre tenants.

Uma fase futura pode adicionar diagnósticos read-only com permissões explícitas.

## O assistente funciona sem IA configurada?

Sim. Quando o LLM não estiver configurado, ele usa fallback textual com a documentação local.

## Por que a resposta cita documentação?

Porque o MVP usa RAG simples: busca trechos documentados e monta uma resposta com base neles.

## Posso perguntar sobre qualquer área?

Você pode perguntar, mas o assistente deve responder apenas quando houver base na documentação.

Áreas cobertas inicialmente: catálogo, produtos, variantes, estoque, pedidos, pagamentos, frete, marca, páginas, cupons, clientes, administradores e boas práticas.
