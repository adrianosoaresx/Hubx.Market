from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.catalog.application.catalog_publication_issues import catalog_publication_issues
from app.modules.catalog.application.storefront_catalog_queries import storefront_catalog_queries
from app.modules.catalog.models import Product


class CatalogMetricsRepository(Protocol):
    def list_publication_issues(self):
        ...

    def list_storefront_products(self):
        ...


class DjangoOrmCatalogMetricsRepository:
    def list_publication_issues(self):
        return catalog_publication_issues.list_issues(limit=1000)

    def list_storefront_products(self):
        products: list[dict[str, object]] = []
        tenant_ids = Product.objects.values_list("tenant_id", flat=True).distinct()
        for tenant_id in tenant_ids:
            products.extend(storefront_catalog_queries.list_products(tenant_id=tenant_id))
        return products


@dataclass
class CatalogMetricsQueryService:
    repository: CatalogMetricsRepository

    def export_prometheus_metrics(self) -> str:
        issue_counts: dict[tuple[str, str], int] = {}
        for issue in self.repository.list_publication_issues():
            key = (issue.tenant_id, issue.issue_code)
            issue_counts[key] = issue_counts.get(key, 0) + 1

        decision_signal_counts: dict[tuple[str, str], int] = {}
        for product in self.repository.list_storefront_products():
            tenant_id = str(product.get("tenant_id") or "")
            signal = str(product.get("catalog_card_decision_signal") or "")
            if not tenant_id or not signal:
                continue
            key = (tenant_id, signal)
            decision_signal_counts[key] = decision_signal_counts.get(key, 0) + 1

        lines = [
            "# HELP hubx_catalog_publication_issue_total Total de problemas operacionais de publicação do catálogo por tenant e tipo.",
            "# TYPE hubx_catalog_publication_issue_total gauge",
        ]
        for (tenant_id, issue_code), count in sorted(issue_counts.items()):
            lines.append(f'hubx_catalog_publication_issue_total{{tenant_id="{tenant_id}",issue="{issue_code}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_catalog_card_decision_signal_total Total de cards do catálogo por tenant e sinal de decisão comercial.",
                "# TYPE hubx_catalog_card_decision_signal_total gauge",
            ]
        )
        for (tenant_id, signal), count in sorted(decision_signal_counts.items()):
            lines.append(f'hubx_catalog_card_decision_signal_total{{tenant_id="{tenant_id}",signal="{signal}"}} {count}')
        return "\n".join(lines) + "\n"


catalog_metrics_queries = CatalogMetricsQueryService(repository=DjangoOrmCatalogMetricsRepository())
