# API Conventions

## Estilo
- REST
- recursos no plural
- paginação padronizada
- filtros por querystring
- ordenação por querystring

## Exemplos
- `GET /api/products`
- `GET /api/orders`
- `POST /api/coupons`

## Respostas
Padronizar erros e respostas de validação.

## Convenções da API pública de catálogo

- versionar endpoints sob `/api/v1/`.
- manter recursos no plural.
- usar paginação por `page` e `page_size` na listagem.
- resolver tenant por subdomínio antes da query de aplicação.
- exigir API key válida e escopo `read:catalog`.
- retornar apenas payload público, sem PII, segredo, hash de chave, dados admin ou estoque bruto.
- documentar exemplos em `docs/api/public-catalog-partner-onboarding.md`.
