# Architecture Overview

Hubx Market é um SaaS multi-tenant com backend em Django e interface server-rendered.

## Camadas principais
- UI
- backend
- cache
- fila
- banco
- storage
- observabilidade

## Componentes
- Django Web
- DRF
- Redis
- Celery Worker
- PostgreSQL
- Object Storage
- Prometheus
- Grafana
