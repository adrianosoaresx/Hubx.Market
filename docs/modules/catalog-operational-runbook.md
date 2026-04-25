# Catalog Operational Runbook

Este runbook consolida a operação inicial do catálogo: publicação, variantes, preço, estoque e observabilidade.

## Escopo
- listar problemas de publicação por tenant
- identificar inconsistências de status
- identificar produtos sem variante/default
- identificar preço/estoque inválido para publicação
- expor métricas Prometheus
- carregar alertas, dashboard e routing

## Fronteira atual
- `Product` representa a página/agrupamento editorial.
- `ProductVariant` representa a unidade de venda.
- preço pertence à variante.
- estoque pertence à variante.
- produto inativo não deve ser deletado.

## Triagem CLI
Listar todos os problemas:

```bash
python manage.py list_catalog_publication_issues --tenant-id=<id>
```

Filtrar por status inconsistente:

```bash
python manage.py list_catalog_publication_issues --tenant-id=<id> --issue=status_mismatch
```

Filtrar produto sem variante:

```bash
python manage.py list_catalog_publication_issues --tenant-id=<id> --issue=missing_variant
```

Filtrar produto sem variante default:

```bash
python manage.py list_catalog_publication_issues --tenant-id=<id> --issue=missing_default_variant
```

Filtrar preço/estoque:

```bash
python manage.py list_catalog_publication_issues --tenant-id=<id> --issue=missing_price
python manage.py list_catalog_publication_issues --tenant-id=<id> --issue=stock_unavailable
```

## Observabilidade
Endpoint:

```text
/ops/catalog/metrics/publication-issues/
```

Autenticação:
- header `Authorization: Bearer <CATALOG_OBSERVABILITY_TOKEN>`
- ou `X-Hubx-Observability-Token`

Métrica principal:
- `hubx_catalog_publication_issue_total{tenant_id,issue}`

Métrica de merchandising:
- `hubx_catalog_card_decision_signal_total{tenant_id,signal}`

Sinais de decisão:
- `acompanhar_reposicao`
- `reserva_planejada`
- `decisao_rapida_com_oferta`
- `decisao_rapida`
- `oferta_editorial`
- `oferta_para_comparar`
- `destaque_editorial`
- `compra_pronta`

Artefatos:
- `infra/observability/prometheus/catalog-scrape.example.yml`
- `infra/observability/prometheus/catalog-alert-rules.yml`
- `infra/observability/grafana/catalog-publication-dashboard.json`
- `infra/observability/alertmanager/catalog-routing.example.yml`

## Alertas iniciais
- `HubxCatalogStatusMismatchPresent`
- `HubxCatalogMissingVariantPresent`
- `HubxCatalogUnavailablePublishedStockPresent`

## Diagnóstico rápido
- `status_mismatch`
  - alinhar `Product.status` e `Product.is_active`
  - validar se o produto deve aparecer no storefront
- `missing_variant`
  - cadastrar ao menos uma `ProductVariant`
  - lembrar que `Product` não é unidade de venda
- `missing_default_variant`
  - marcar uma variante como default
  - revisar qual combinação aparece primeiro no admin/storefront
- `missing_price`
  - preencher preço da variante default
- `stock_unavailable`
  - revisar `stock`, `track_inventory` e `allow_backorder`
  - evitar campanhas para produto sem estoque e sem backorder

## Limites atuais
- não há workflow de aprovação editorial.
- não há histórico dedicado de alterações de catálogo.
- não há validação de mídia/imagem obrigatória.
- não há SLA de publicação.
- o sinal de decisão comercial é observacional e não altera ranking sozinho.
