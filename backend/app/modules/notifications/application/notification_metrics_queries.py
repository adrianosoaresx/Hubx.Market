from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from django.db.models import Count

from app.modules.notifications.models import EmailLog


def _string(value: object) -> str:
    return str(value or "").strip()


class NotificationMetricsRepository(Protocol):
    def list_status_counts(self) -> list[dict[str, object]]:
        ...


class DjangoOrmNotificationMetricsRepository:
    def list_status_counts(self) -> list[dict[str, object]]:
        return list(
            EmailLog.objects.values("tenant_id", "status")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "status")
        )


@dataclass
class NotificationMetricsQueryService:
    repository: NotificationMetricsRepository

    def export_prometheus_metrics(self) -> str:
        rows = self.repository.list_status_counts()
        lines = [
            "# HELP hubx_notifications_email_log_total Total de logs de e-mail por tenant e status.",
            "# TYPE hubx_notifications_email_log_total gauge",
        ]
        for row in rows:
            tenant_id = _string(row.get("tenant_id"))
            status = _string(row.get("status"))
            count = int(row.get("count", 0) or 0)
            lines.append(f'hubx_notifications_email_log_total{{tenant_id="{tenant_id}",status="{status}"}} {count}')
        return "\n".join(lines) + "\n"


notification_metrics_queries = NotificationMetricsQueryService(
    repository=DjangoOrmNotificationMetricsRepository(),
)
