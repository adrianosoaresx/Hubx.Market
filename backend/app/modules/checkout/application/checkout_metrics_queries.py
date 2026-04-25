from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.modules.checkout.application.checkout_result_taxonomy import CHECKOUT_RESULT_TAXONOMY
from app.modules.checkout.application.checkout_session_issues import checkout_session_issues
from app.modules.checkout.models import CheckoutRecoveryEvent
from app.modules.checkout.models import CheckoutSession


class CheckoutMetricsRepository(Protocol):
    def list_session_issues(self):
        ...

    def list_sessions(self):
        ...

    def list_recovery_events(self):
        ...


class DjangoOrmCheckoutMetricsRepository:
    def list_session_issues(self):
        return checkout_session_issues.list_issues(limit=1000)

    def list_sessions(self):
        return list(CheckoutSession.objects.order_by("tenant_id", "status", "id"))

    def list_recovery_events(self):
        return list(CheckoutRecoveryEvent.objects.order_by("tenant_id", "result_code", "family", "recovery_action", "id"))


@dataclass
class CheckoutMetricsQueryService:
    repository: CheckoutMetricsRepository

    def export_prometheus_metrics(self) -> str:
        issue_counts: dict[tuple[str, str], int] = {}
        for issue in self.repository.list_session_issues():
            key = (issue.tenant_id, issue.issue_code)
            issue_counts[key] = issue_counts.get(key, 0) + 1

        status_counts: dict[tuple[str, str], int] = {}
        for session in self.repository.list_sessions():
            key = (str(session.tenant_id), str(session.status or ""))
            status_counts[key] = status_counts.get(key, 0) + 1

        recovery_counts: dict[tuple[str, str, str, str, str], int] = {}
        for event in self.repository.list_recovery_events():
            key = (
                str(event.tenant_id),
                str(event.result_code or ""),
                str(event.family or ""),
                str(event.severity or ""),
                str(event.recovery_action or ""),
            )
            recovery_counts[key] = recovery_counts.get(key, 0) + 1

        lines = [
            "# HELP hubx_checkout_session_issue_total Total de problemas operacionais em sessões de checkout por tenant e tipo.",
            "# TYPE hubx_checkout_session_issue_total gauge",
        ]
        for (tenant_id, issue_code), count in sorted(issue_counts.items()):
            lines.append(f'hubx_checkout_session_issue_total{{tenant_id="{tenant_id}",issue="{issue_code}"}} {count}')
        lines.extend(
            [
                "# HELP hubx_checkout_session_status_total Total de sessões de checkout por tenant e status.",
                "# TYPE hubx_checkout_session_status_total gauge",
            ]
        )
        for (tenant_id, status), count in sorted(status_counts.items()):
            lines.append(f'hubx_checkout_session_status_total{{tenant_id="{tenant_id}",status="{status}"}} {count}')
        lines.extend(
            [
                "# HELP hubx_checkout_recovery_result_info Taxonomia dos result codes de recovery do checkout.",
                "# TYPE hubx_checkout_recovery_result_info gauge",
            ]
        )
        for code, (family, severity, recovery_action) in sorted(CHECKOUT_RESULT_TAXONOMY.items()):
            lines.append(
                "hubx_checkout_recovery_result_info"
                f'{{code="{code}",family="{family}",severity="{severity}",recovery_action="{recovery_action}"}} 1'
            )
        lines.extend(
            [
                "# HELP hubx_checkout_recovery_event_total Total de eventos persistidos de recovery do checkout por tenant e taxonomia.",
                "# TYPE hubx_checkout_recovery_event_total gauge",
            ]
        )
        for (tenant_id, code, family, severity, recovery_action), count in sorted(recovery_counts.items()):
            lines.append(
                "hubx_checkout_recovery_event_total"
                f'{{tenant_id="{tenant_id}",code="{code}",family="{family}",severity="{severity}",recovery_action="{recovery_action}"}} {count}'
            )
        return "\n".join(lines) + "\n"


checkout_metrics_queries = CheckoutMetricsQueryService(repository=DjangoOrmCheckoutMetricsRepository())
