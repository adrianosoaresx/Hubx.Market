# DECISIONS.md

## 2026-04
### Decisão: nome oficial do produto
- Produto: Hubx Market
- Domínio principal: hubx.market

### Decisão: multi-tenant por subdomínio
Motivo:
- simplicidade
- clareza operacional
- bom encaixe com SaaS de e-commerce

### Decisão: banco único com tenant_id
Motivo:
- menor complexidade operacional
- melhor custo
- bom caminho para MVP e crescimento

### Decisão: UI server-rendered
Stack:
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

Motivo:
- alta produtividade
- menor complexidade que SPA
- excelente encaixe com Django

### Decisão: gateway inicial
- Pagar.me

### Decisão: frete inicial
- API de frete desde o MVP

### Decisão: design system documentado
Motivo:
- consistência visual
- reutilização
- melhor atuação do Codex

### ADR: namespace modules.*
Decisão:
- `INSTALLED_APPS` usa `modules.*` como namespace público de registro dos apps.
- O código-fonte real permanece em `app.modules.*`.
- O diretório `backend/modules/` funciona como camada de alias para alinhar implementação e documentação.

Motivo:
- manter compatibilidade com a estrutura já bootstrapada em `app.modules.*`
- alinhar com a convenção documental do projeto (`modules.*`)
- evitar refactor estrutural grande nesta fase inicial
