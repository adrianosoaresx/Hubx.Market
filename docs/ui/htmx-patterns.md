# HTMX Patterns

## Objetivo
Padronizar interações assíncronas com HTMX.

## Usar HTMX para
- filtros
- paginação parcial
- atualização de carrinho
- modais
- troca de status
- refresh de blocos
- busca incremental simples

## Evitar HTMX para
- lógica de negócio complexa
- orquestração de estados em cadeia no cliente

## Convenções de partials
Sugeridas:
- `_list.html`
- `_table.html`
- `_card.html`
- `_form.html`
- `_modal.html`

## Rolagem infinita progressiva
- usar apenas para listas públicas ou operacionais em que paginação sequencial seja suficiente
- manter paginação HTML tradicional como fallback navegável
- carregar apenas o próximo fragmento com `hx-get` e `hx-trigger="revealed"`
- retornar partials sem shell/layout completo quando `fragment=` indicar uma resposta parcial
- preservar filtros, busca, ordenação e tenant resolvido na URL do próximo fragmento

## Regras
- definir `hx-target` explicitamente
- usar `hx-swap` coerente
- prever loading indicator
- tratar resposta de erro
- usar mensagens flash quando apropriado

## Feedback
Toda interação HTMX deve prever:
- estado carregando
- sucesso
- erro
- fallback visual mínimo
