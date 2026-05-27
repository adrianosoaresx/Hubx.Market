# API Auth

## Contextos
- owner user
- customer
- API pública futura por ApiKey

## Diretriz
Manter autenticação e autorização separadas por contexto.

## API pública por ApiKey

O recorte ativo usa API key por tenant, com escopo explícito.

- guia: `docs/api/public-catalog-partner-onboarding.md`
- escopo inicial: `read:catalog`
- exemplos públicos devem usar placeholders, nunca credencial real.
- a documentação de parceiro não altera autenticação runtime nem cria novo endpoint.
