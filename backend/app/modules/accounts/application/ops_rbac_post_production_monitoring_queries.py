from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db.models import Count
from django.utils import timezone


OWNER_ACCESS_ACTIONS = (
    "owner.login_failed",
    "owner.login_rate_limited",
    "owner.ops_gate_forbidden",
    "owner.ops_permission_denied",
    "owner.ops_gate_redirected",
)


@dataclass(frozen=True)
class OpsRbacPostProductionSignal:
    key: str
    count: int
    threshold: int
    severity: str
    action: str


@dataclass
class OpsRbacPostProductionMonitoringQueryService:
    def get_snapshot(
        self,
        *,
        tenant_id: int | str | None = None,
        window_minutes: int = 30,
        permission_denied_warning_threshold: int = 3,
        gate_forbidden_warning_threshold: int = 3,
        login_failed_warning_threshold: int = 5,
        rate_limited_rollback_threshold: int = 1,
        email_failed_rollback_threshold: int = 1,
    ) -> dict[str, object]:
        safe_window_minutes = max(int(window_minutes or 30), 1)
        since = timezone.now() - timedelta(minutes=safe_window_minutes)
        audit_counts = self._audit_counts(tenant_id=tenant_id, since=since)
        email_counts = self._email_counts(tenant_id=tenant_id, since=since)
        watch_signals: list[OpsRbacPostProductionSignal] = []
        rollback_signals: list[OpsRbacPostProductionSignal] = []

        self._append_threshold_signal(
            signals=watch_signals,
            key="owner.ops_permission_denied",
            count=sum(row["count"] for row in audit_counts if row["action"] == "owner.ops_permission_denied"),
            threshold=permission_denied_warning_threshold,
            severity="watch",
            action="revisar role, navegação direta e permissões do prefixo /ops/",
        )
        self._append_threshold_signal(
            signals=watch_signals,
            key="owner.ops_gate_forbidden",
            count=sum(row["count"] for row in audit_counts if row["action"] == "owner.ops_gate_forbidden"),
            threshold=gate_forbidden_warning_threshold,
            severity="watch",
            action="revisar vínculo User.email + OwnerUser ativo no tenant",
        )
        self._append_threshold_signal(
            signals=watch_signals,
            key="owner.login_failed",
            count=sum(row["count"] for row in audit_counts if row["action"] == "owner.login_failed"),
            threshold=login_failed_warning_threshold,
            severity="watch",
            action="revisar credenciais, convite/reset e possível tentativa indevida",
        )
        self._append_threshold_signal(
            signals=rollback_signals,
            key="owner.login_rate_limited",
            count=sum(row["count"] for row in audit_counts if row["action"] == "owner.login_rate_limited"),
            threshold=rate_limited_rollback_threshold,
            severity="rollback",
            action="avaliar brute force, comunicação com owners e possível rollback do gate",
        )
        self._append_threshold_signal(
            signals=rollback_signals,
            key="owner.access.email_failed",
            count=sum(row["count"] for row in email_counts if row["status"] == "failed"),
            threshold=email_failed_rollback_threshold,
            severity="rollback",
            action="corrigir provider/worker de notifications antes de manter ativação",
        )

        status = "healthy"
        if watch_signals:
            status = "watch"
        if rollback_signals:
            status = "rollback"

        return {
            "result": f"ops-rbac-post-production-{status}",
            "healthy": status == "healthy",
            "status": status,
            "window_minutes": safe_window_minutes,
            "tenant_id": str(tenant_id or "").strip(),
            "audit_counts": tuple(audit_counts),
            "email_counts": tuple(email_counts),
            "watch_signals": tuple(watch_signals),
            "rollback_signals": tuple(rollback_signals),
        }

    def _audit_counts(self, *, tenant_id: int | str | None, since) -> list[dict[str, object]]:
        try:
            from app.modules.audit.models import AuditLog
        except Exception:
            return []
        queryset = AuditLog.objects.filter(module="accounts", action__in=OWNER_ACCESS_ACTIONS, created_at__gte=since)
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return list(
            queryset.values("tenant_id", "action")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "action")
        )

    def _email_counts(self, *, tenant_id: int | str | None, since) -> list[dict[str, object]]:
        try:
            from app.modules.notifications.models import EmailLog
        except Exception:
            return []
        queryset = EmailLog.objects.filter(
            intent_key__in=["owner.access.invite", "owner.access.password_reset"],
            created_at__gte=since,
        )
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return list(
            queryset.values("tenant_id", "intent_key", "status")
            .annotate(count=Count("id"))
            .order_by("tenant_id", "intent_key", "status")
        )

    def _append_threshold_signal(
        self,
        *,
        signals: list[OpsRbacPostProductionSignal],
        key: str,
        count: int,
        threshold: int,
        severity: str,
        action: str,
    ) -> None:
        if threshold > 0 and count >= threshold:
            signals.append(
                OpsRbacPostProductionSignal(
                    key=key,
                    count=count,
                    threshold=threshold,
                    severity=severity,
                    action=action,
                )
            )


ops_rbac_post_production_monitoring_queries = OpsRbacPostProductionMonitoringQueryService()
