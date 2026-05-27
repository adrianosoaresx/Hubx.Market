# Pages

## Responsabilidade
Gerenciar páginas institucionais tenant-owned para o storefront.

## Entidades principais
- Page

## Casos de uso
- criar página institucional por tenant
- editar conteúdo simples
- publicar/retirar publicação por status
- renderizar apenas páginas publicadas no storefront

## Regras de negócio
- páginas pertencem sempre a um tenant
- `slug` é único por tenant
- páginas em rascunho não aparecem no storefront
- a leitura pública exige tenant resolvido por subdomínio
- não existe fallback global de conteúdo entre tenants
- page builder, menus, tradução e SEO engine avançado ficam fora do primeiro corte

## Interfaces

- Admin: `/ops/pages/`
- Storefront: `/pages/<slug>/`

## Application services

- `admin_page_queries`
- `admin_page_commands`
- `storefront_page_queries`

## Status

Storefront Content & SEO Foundation:

- modelo `Page` tenant-scoped
- admin lite de listagem/criação/edição
- storefront published-only
- metadados SEO básicos
