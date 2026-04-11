# States and Feedback

## Objetivo
Padronizar estados da interface e mensagens de retorno.

## Estados obrigatórios
- loading
- empty
- success
- error
- disabled
- processing

## Empty state
Usar quando não houver dados.
Deve conter:
- título curto
- explicação
- ação principal quando fizer sentido

## Loading state
Pode usar:
- spinner
- skeleton
- texto de processamento

## Error state
- linguagem clara
- orientar próximo passo
- evitar mensagens técnicas para usuário final

## Success state
- curto
- contextual
- visível sem exagero
