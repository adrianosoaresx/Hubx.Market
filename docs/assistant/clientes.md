# Clientes

## Diferença entre owner/admin e customer

`OwnerUser` é o usuário administrativo da loja.

`Customer` é o comprador da loja.

Essas entidades são diferentes e não devem ser misturadas.

## Onde ver clientes

Use `/ops/customers/` para leituras administrativas de clientes, quando seu perfil tiver permissão.

Clientes pertencem a um tenant específico.

## Isolamento por loja

Cada loja tem sua própria base de clientes.

Um cliente de uma loja não deve aparecer na área administrativa de outra loja.

## Boas práticas

- Use dados de clientes apenas para operação da loja.
- Evite copiar dados pessoais para campos livres desnecessários.
- Respeite opt-in de newsletter e preferências de contato.
- Use flags operacionais com cuidado, como prioridade ou acompanhamento.

