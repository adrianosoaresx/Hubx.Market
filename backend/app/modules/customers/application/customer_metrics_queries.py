from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.customers.application.customer_data_issues import customer_data_issues


class CustomerMetricsRepository(Protocol):
    def list_data_issues(self):
        ...


class DjangoOrmCustomerMetricsRepository:
    def list_data_issues(self):
        return customer_data_issues.list_issues(limit=1000)


@dataclass
class CustomerMetricsQueryService:
    repository: CustomerMetricsRepository

    def export_prometheus_metrics(self) -> str:
        counts: dict[tuple[str, str], int] = {}
        for issue in self.repository.list_data_issues():
            key = (issue.tenant_id, issue.issue_code)
            counts[key] = counts.get(key, 0) + 1

        lines = [
            "# HELP hubx_customer_data_issue_total Total de problemas operacionais de dados de clientes por tenant e tipo.",
            "# TYPE hubx_customer_data_issue_total gauge",
        ]
        for (tenant_id, issue_code), count in sorted(counts.items()):
            lines.append(f'hubx_customer_data_issue_total{{tenant_id="{tenant_id}",issue="{issue_code}"}} {count}')
        return "\n".join(lines) + "\n"


customer_metrics_queries = CustomerMetricsQueryService(repository=DjangoOrmCustomerMetricsRepository())
