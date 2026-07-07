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
- exibir links institucionais publicados no footer do storefront
- popular páginas institucionais demo para avaliação de MVP

## Regras de negócio
- páginas pertencem sempre a um tenant
- `slug` é único por tenant
- páginas em rascunho não aparecem no storefront
- a leitura pública exige tenant resolvido por subdomínio
- não existe fallback global de conteúdo entre tenants
- links institucionais do footer são derivados apenas de páginas publicadas do tenant atual
- page builder, menus, tradução e SEO engine avançado ficam fora do primeiro corte

## Interfaces

- Admin: `/ops/pages/`
- Storefront: `/pages/<slug>/`

## Application services

- `admin_page_queries`
- `admin_page_commands`
- `storefront_page_queries`

## Seeds demo

- `python manage.py seed_demo_pages --tenant-subdomain=hubx-demo`
- cria/atualiza páginas publicadas para Sobre a loja, Trocas e devoluções, Política de privacidade, Termos de uso e Contato
- o seed é idempotente e não cria conteúdo global entre tenants

## Status

Storefront Content & SEO Foundation:

- modelo `Page` tenant-scoped
- admin lite de listagem/criação/edição
- storefront published-only
- metadados SEO básicos
- footer do storefront consome páginas institucionais publicadas
- seed demo de páginas institucionais para avaliação do MVP
