# Codex Knowledge Transfer — Hubx Market

This document transfers architectural and product knowledge of Hubx Market to AI agents (Codex).

Hubx Market is a SaaS multi‑tenant e‑commerce platform where each store runs on a subdomain.

Example:
store.hubx.market

Stack:
Backend: Django + DRF
UI: Django Templates + HTMX + Alpine + Tailwind
DB: PostgreSQL
Cache/Queue: Redis + Celery
Storage: S3 / R2
Monitoring: Prometheus + Grafana

Core rules:
- Multi‑tenant via subdomain
- tenant_id used for isolation
- ProductVariant holds price and stock
- Orders store price snapshots
- Payment handled by Pagar.me
- PIX uses webhooks
- UI follows a strict design system

Agents must always read:
AGENTS.md
PRODUCT_RULES.md
ARCHITECTURE.md
docs/implementation-inventory.md
docs/ui/*
docs/modules/*
docs/data/*

Before implementing anything:
1. identify module
2. identify domain rules
3. check UI patterns
4. check multi‑tenant implications
