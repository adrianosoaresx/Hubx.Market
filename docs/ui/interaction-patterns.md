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

## Escopo tenant/platform
- admin da loja deve indicar contexto tenant
- platform owner deve indicar contexto platform
- ações cross-tenant precisam de confirmação, estado de risco e trilha auditável visível quando aplicável

## Identidade e marca
- header deve reforçar a loja atual sem esconder navegação
- Hubx Market deve aparecer como operador/plataforma, não como nome fixo da loja tenant-owned
- footer pode concentrar links úteis para reduzir poluição no header

## Iconografia
- usar ícones em navegação, filtros, sort, cupom, entrega, pagamento, segurança, sucesso, erro e estados vazios
- ícone não deve competir com preço, produto ou CTA principal
- estados destrutivos devem usar iconografia e cor com parcimônia
