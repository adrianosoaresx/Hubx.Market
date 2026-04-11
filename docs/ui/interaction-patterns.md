# Interaction Patterns

## Objetivo
Padronizar fluxos de interação do usuário.

## CRUD padrão
### Listagem
1. cabeçalho
2. ações principais
3. filtros
4. conteúdo
5. paginação
6. empty state

### Criação / Edição
1. título
2. descrição curta
3. grupos de campos
4. ações finais

### Exclusão
- sempre pedir confirmação
- usar modal de confirmação
- destacar impacto da ação

## Filtros
- devem ser previsíveis
- podem usar HTMX
- sempre mostrar estado atual

## Ações rápidas
- usar menus ou botões secundários
- evitar excesso de ações destrutivas visíveis

## Navegação
- usar breadcrumbs quando necessário
- manter retorno claro ao contexto anterior
