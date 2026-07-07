# Forms and Validation

## Objetivo
Padronizar campos de formulário, labels, ajuda de campo e mensagens de erro.

## Estrutura oficial de campo
1. label
2. controle
3. ajuda de campo opcional
4. mensagem de erro

## Label
- usar peso médio
- posicionar acima do campo
- marcar obrigatoriedade de forma consistente

## Inputs
- altura consistente
- borda padrão
- foco visível
- mensagens de erro próximas
- usar `aria-invalid` quando inválido
- associar ajuda e erro ao controle via `aria-describedby`

## Select
- mesma altura do input
- ícone padronizado
- placeholder claro
- manter o mesmo contrato de ajuda, erro, obrigatório e desabilitado do input

## Textarea
- mesma borda do input
- altura mínima definida
- usar `ds-textarea`, não `ds-input`, para permitir ajustes específicos

## Erro
- texto curto
- cor de erro
- sempre abaixo do campo
- usar `role="alert"` quando renderizado por componente compartilhado

## Sucesso
- usar com moderação
- preferir feedback de formulário e não de campo quando possível

## Signup público controlado
- quando o signup self-service exigir token operacional, renderizar `Código de acesso` como campo obrigatório comum.
- erro de token ausente/inválido deve aparecer inline com `field_error.html`, sem expor o valor esperado.
- conflito concorrente de subdomínio deve retornar erro no campo `Subdomínio`, não página 500.

## Botões de formulário
- ação primária à direita ou ao final do fluxo
- ação secundária clara
- loading visível quando houver submissão assíncrona

## Contrato dos partials
- `input.html`, `select.html` e `textarea.html` aceitam `id`, `name`, `label`, `help_text`, `error_text`, `invalid`, `required`, `disabled` e `size`.
- `size` usa a escala `sm`, `md` padrão e `lg`.
- `checkbox.html`, `radio.html` e `switch.html` também associam descrição e erro por `aria-describedby`.
- `field_help.html` aceita `id` opcional.
- `field_error.html` aceita `id` opcional e sempre anuncia a mensagem com `role="alert"`.
