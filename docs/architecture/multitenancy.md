# Multitenancy

## Estratégia
- tenant resolvido por subdomínio
- banco único
- isolamento lógico por `tenant_id`

## Exemplos
- `lojax.hubx.market`
- `nike.hubx.market`
- `demo.hubx.market`

## Resolução
Middleware extrai o host da requisição e associa `request.tenant`.

## Futuro
Também deve suportar domínio customizado, como `www.lojax.com.br`.
