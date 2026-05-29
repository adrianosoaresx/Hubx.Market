# Layout and Spacing

## Objetivo
Padronizar containers, grids, alinhamento e espaçamento.

## Escala de espaçamento
Usar preferencialmente:
- 2
- 3
- 4
- 6
- 8
- 10
- 12

## Containers
### Storefront
- largura máxima confortável
- foco em legibilidade e vitrine
- home usa banner compacto de identidade antes da grade de produtos

### Dashboard
- largura maior
- áreas com cards, tabelas e filtros
- admin shell usa sidebar de `16rem`, topbar de aproximadamente `4.5rem` e conteúdo máximo de `80rem`

### Footer
- storefront footer usa grid responsivo com identidade, links úteis e assinatura Hubx
- checkout usa footer compacto para não competir com pagamento
- em mobile, links do footer devem empilhar em uma coluna

## Grids
- usar grid simples
- evitar layouts excessivamente específicos por página
- preferir padrões repetíveis

## Padding interno
- cards simples: `p-4` ou `p-6`
- modais: `p-6`
- seções grandes: `py-8` ou `py-10`

## Regra
Evitar espaçamentos arbitrários fora da escala.

## Admin
- sidebar fixa em desktop e horizontal/rolável em mobile
- nav item deve manter altura confortável para clique
- estados ativos precisam preservar alinhamento entre ícone e texto

## Mobile
- validar header, busca, filtros, carrinho, checkout e footer em 360-430px
- botões e links com ícone não devem quebrar texto dentro do controle
