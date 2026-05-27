from __future__ import annotations

from dataclasses import dataclass

from django.db.models import Count


def _string(value: object) -> str:
    return str(value or "").strip()


@dataclass
class OwnerAccessMetricsQueryService:
    def export_prometheus_metrics(self) -> str:
        audit_rows = self._list_audit_action_counts()
        email_rows = self._list_owner_access_email_counts()
        lines = [
            "# HELP hubx_accounts_owner_access_audit_event_total Total de eventos auditados de acesso owner por tenant e ação.",
            "# TYPE hubx_accounts_owner_access_audit_event_total counter",
        ]
        for row in audit_rows:
            tenant_id = _string(row.get("tenant_id"))
            action = _string(row.get("action"))
            count = int(row.get("count", 0) or 0)
            lines.append(f'hubx_accounts_owner_access_audit_event_total{{tenant_id="{tenant_id}",action="{action}"}} {count}')

        lines.extend(
            [
                "# HELP hubx_accounts_owner_access_email_log_total Total de EmailLogs de owner access por tenant, intent e status.",
                "# TYPE hubx_accounts_owner_access_email_log_total gauge",
            ]
        )
        for row in email_rows:
            tenant_id = _string(row.get("tenant_id"))
            intent_key = _string(row.get("intent_key"))
            status = _string(row.get("status"))
            count = int(row.get("count", 0) or 0)
            lines.append(
                f'hubx_accounts_owner_access_email_log_total{{tenant_id="{tenant_id}",intent_key="{intent_key}",status="{status}"}} {count}'
            )

        return "\n".join(lines) + "\n"

    def _list_audit_action_counts(self) -> list[dict[str, object]]:
        try:
            from app.modules.audit.models import AuditLog
        except Exception:
            return []
        return list(
            AuditLog.objects.filter(
                module="accounts",
                action__in=[
                    "owner.login_failed",
                    "owner.login_rate_limited",
                    "owner.ops_gate_forbidden",
                    "owner.ops_permission_denied",
                    "owner.ops_gate_redirected",
                ],
            )
            .values("tenant_id", "action")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "action")
        )

    def _list_owner_access_email_counts(self) -> list[dict[str, object]]:
        try:
            from app.modules.notifications.models import EmailLog
        except Exception:
            return []
        return list(
            EmailLog.objects.filter(
                intent_key__in=["owner.access.invite", "owner.access.password_reset"],
            )
            .values("tenant_id", "intent_key", "status")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "intent_key", "status")
        )


owner_access_metrics_queries = OwnerAccessMetricsQueryService()
