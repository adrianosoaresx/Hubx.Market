# Engineering Principles — Hubx Market

The project prioritizes clarity, modularity and scalability.

## Principles

1. Clarity over cleverness
2. Consistency over novelty
3. Reuse over duplication
4. Explicit domain rules
5. Documentation driven development

## Multi‑tenant awareness

Every data access must consider tenant_id.

Never assume global context.

## Domain integrity

Critical domain rules:

- ProductVariant holds price and stock
- OrderItem stores price snapshot
- Orders only created after checkout payment action
- Payment must be idempotent

## Architecture

The system uses modular Django architecture with clear boundaries.
