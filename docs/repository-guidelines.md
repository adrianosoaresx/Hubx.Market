# Repository Guidelines — Hubx Market

This document explains how contributors and AI agents should work in the repository.

## Repository layout

backend/
ui/
infra/
docs/

## Modules

accounts
tenants
catalog
cart
checkout
orders
payments
shipping
coupons
reviews
subscriptions
notifications
pages
newsletter
audit

## Development workflow

1. Identify module
2. Implement domain logic
3. Implement application use case
4. Connect interface (view/API)
5. Update documentation

## UI guidelines

All UI must follow docs/ui design system.

Components must be reused from:

ui/templates/shared/components/

## Documentation first

Any structural change must update docs.
