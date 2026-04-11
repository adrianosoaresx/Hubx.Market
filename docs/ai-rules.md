# AI Rules — Hubx Market

These rules apply to any AI agent interacting with the repository.

## Core principles

AI must:
- respect project documentation
- never invent undocumented business rules
- never bypass tenant isolation
- never duplicate UI components
- never place complex logic in views

## Workflow

Before implementing:
1. read documentation
2. locate the correct module
3. verify domain rules
4. verify UI patterns

## Code guidelines

Preferred architecture:

models.py → persistence
domain/ → business rules
application/ → use cases
infrastructure/ → integrations
interfaces/ → views/API/admin

## Forbidden practices

- heavy business logic in views
- direct cross‑module database access
- HTML duplication
- skipping tenant filters
