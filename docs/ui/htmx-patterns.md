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
