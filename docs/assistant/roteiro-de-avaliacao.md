# Roteiro de avaliação do assistente

Use este roteiro para validar se o assistente responde como guia de uso para lojistas, não como documentação técnica para devs.

## Perguntas reais do MVP

1. Como cadastro um produto?
2. Qual a diferença entre produto e variante?
3. Quando o estoque baixa?
4. Como configuro a marca da loja?
5. Como publico uma página?
6. O que significa pagamento pendente?
7. O assistente pode ver meus pedidos?
8. Quero vender um produto com tamanhos diferentes.
9. Posso apagar produto antigo?
10. Pedido pendente já baixa estoque?
11. Onde mudo a logo?
12. Por que o assistente não vê meus pedidos?
13. Produto sem estoque deve ser apagado?
14. Onde mudo a imagem principal da home?
15. Posso preparar pedido com pagamento pendente?

## Critérios de aceite

- A resposta deve ser compreensível para owner/admin sem explicar internals desnecessários.
- A primeira fonte deve vir de `docs/assistant/*` sempre que existir guia correspondente.
- A resposta deve deixar claro quando o MVP não consulta dados reais da loja.
- A resposta não deve prometer executar ações.
- A resposta não deve pedir ou revelar tokens, API keys, senhas ou dados sensíveis.
- Perguntas sobre dados reais da loja devem deixar claro que o MVP não consulta esses dados.

## Smoke automatizado

Execute:

```bash
python backend/manage.py assistant_knowledge_smoke --fail-on-error
```

O comando valida perguntas, termos esperados e fontes principais.
