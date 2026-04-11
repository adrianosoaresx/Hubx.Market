# Design System

## Objetivo
Garantir consistência visual, reutilização de componentes e previsibilidade de comportamento em toda a interface do Hubx Market.

## Princípios
- consistência antes de criatividade
- reutilização antes de duplicação
- clareza visual
- acessibilidade
- feedback de estado
- responsividade
- baixo acoplamento entre visual e regra de negócio

## Stack
- Django Templates
- HTMX
- Alpine.js
- Tailwind CSS

## Tokens visuais iniciais

### Cores
- Primary: `#4F46E5`
- Secondary: `#06B6D4`
- Accent: `#22C55E`
- Surface: `#FFFFFF`
- Background: `#F8FAFC`
- Text: `#0F172A`
- Muted Text: `#475569`
- Border: `#E2E8F0`
- Danger: `#DC2626`
- Warning: `#D97706`
- Success: `#16A34A`

### Tipografia
Escala base sugerida:
- `text-xs`
- `text-sm`
- `text-base`
- `text-lg`
- `text-xl`
- `text-2xl`

### Raios
- controles: `rounded-lg`
- cards: `rounded-2xl`
- modais: `rounded-2xl`

### Sombra
- `shadow-sm`
- `shadow`
- `shadow-md`

## Diretrizes
- usar escala visual limitada
- evitar cores arbitrárias por template
- respeitar tipografia e espaçamento oficiais
- criar componentes reutilizáveis antes de repetir HTML
