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
- ícone decorativo opcional
- não depender apenas da cor para comunicar filtro vazio, erro ou primeiro uso

## Loading state
Pode usar:
- spinner
- skeleton
- texto de processamento

## Error state
- linguagem clara
- orientar próximo passo
- evitar mensagens técnicas para usuário final
- em alertas persistentes, usar `role="alert"` para erro/danger

## Success state
- curto
- contextual
- visível sem exagero

## Matriz mínima por componente
- hover: indicar interatividade sem deslocar layout
- focus: foco visível para teclado
- disabled: reduzir contraste e bloquear ação
- loading: preservar tamanho do controle
- empty: ícone Lucide, título curto, descrição e ação quando útil
- error: ícone de alerta, mensagem clara e próximo passo
- success: ícone de confirmação e texto contextual

## Acessibilidade
- ícones decorativos acompanhados de texto devem usar `aria-hidden`
- botões só com ícone devem usar `aria-label`
- links e botões precisam permanecer navegáveis por teclado
- feedback de checkout e filtros deve ser compreensível sem depender só de cor
- modais e drawers devem usar `role="dialog"`, `aria-modal` e título associado
