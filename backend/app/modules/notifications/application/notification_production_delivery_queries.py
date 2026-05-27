from __future__ import annotations

from dataclasses import dataclass

from app.modules.notifications.application.notification_failure_classification import classify_notification_failure
from app.modules.notifications.application.notification_provider_readiness import get_notification_provider_readiness
from app.modules.notifications.application.notification_readiness_queries import get_notification_readiness_snapshot
from app.modules.notifications.models import EmailLog


@dataclass(frozen=True)
class NotificationProductionDecision:
    key: str
    status: str
    summary: str


def _blockers(prefix: str, signals: dict[str, bool]) -> tuple[str, ...]:
    return tuple(f"{prefix}:{key}:missing" for key, value in signals.items() if not value)


@dataclass
class NotificationProviderProductionGateQueryService:
    def get_review(self, *, provider_credentials_confirmed: bool = False, sender_domain_confirmed: bool = False, rollback_confirmed: bool = False) -> dict[str, object]:
        readiness = get_notification_provider_readiness()
        signals = {
            "provider_runtime_ready": readiness.can_attempt_real_delivery,
            "provider_credentials_confirmed": bool(provider_credentials_confirmed),
            "sender_domain_confirmed": bool(sender_domain_confirmed),
            "rollback_confirmed": bool(rollback_confirmed),
        }
        blockers = _blockers("notification-provider-production-gate", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"notification-provider-production-gate-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "notifications",
            "signals": signals,
            "provider_blockers": readiness.blockers,
            "decisions": (
                NotificationProductionDecision("provider", "ready" if readiness.can_attempt_real_delivery else "blocked", "provider precisa estar fora de dry-run com backend e remetente configurados"),
                NotificationProductionDecision("sender", "ready" if sender_domain_confirmed else "blocked", "domínio/remetente precisa estar aprovado operacionalmente"),
                NotificationProductionDecision("rollback", "ready" if rollback_confirmed else "blocked", "rollback precisa religar dry-run ou bloquear processamento"),
            ),
            "blockers": blockers,
        }


@dataclass
class NotificationDeliveryEvidenceQueryService:
    def get_review(
        self,
        *,
        tenant_id: int | str,
        smoke_sent: bool = False,
        provider_message_id_recorded: bool = False,
        no_customer_pii_exported: bool = False,
    ) -> dict[str, object]:
        snapshot = get_notification_readiness_snapshot(tenant_id=tenant_id)
        signals = {
            "smoke_sent": bool(smoke_sent),
            "provider_message_id_recorded": bool(provider_message_id_recorded),
            "email_log_sent_present": snapshot.sent > 0,
            "no_customer_pii_exported": bool(no_customer_pii_exported),
        }
        blockers = _blockers("notification-delivery-evidence", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"notification-delivery-evidence-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "notifications",
            "signals": signals,
            "snapshot": snapshot,
            "blockers": blockers,
            "evidence_scope": ("tenant_id", "email_log_id", "status", "masked_recipient", "provider dashboard reference"),
        }


@dataclass
class NotificationFailureHandlingQueryService:
    def get_review(self, *, tenant_id: int | str, bounce_handling_confirmed: bool = False) -> dict[str, object]:
        failed_logs = EmailLog.objects.filter(tenant_id=tenant_id, status=EmailLog.Status.FAILED).only("last_error")[:100]
        classifications: dict[str, int] = {}
        for log in failed_logs:
            key = classify_notification_failure(log.last_error)
            classifications[key] = classifications.get(key, 0) + 1
        signals = {
            "failure_classification_ready": True,
            "bounce_handling_confirmed": bool(bounce_handling_confirmed),
        }
        blockers = _blockers("notification-failure-handling", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"notification-failure-handling-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "notifications",
            "signals": signals,
            "failure_classifications": classifications,
            "blockers": blockers,
        }


@dataclass
class NotificationProductionMonitoringQueryService:
    def get_review(self, *, tenant_id: int | str, metrics_confirmed: bool = False, dashboard_confirmed: bool = False, alert_owner_confirmed: bool = False) -> dict[str, object]:
        snapshot = get_notification_readiness_snapshot(tenant_id=tenant_id)
        signals = {
            "metrics_confirmed": bool(metrics_confirmed),
            "dashboard_confirmed": bool(dashboard_confirmed),
            "alert_owner_confirmed": bool(alert_owner_confirmed),
            "no_pending_delivery": not snapshot.has_pending_delivery,
            "no_failures": not snapshot.has_failures,
        }
        blockers = _blockers("notification-production-monitoring", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"notification-production-monitoring-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "notifications",
            "signals": signals,
            "snapshot": snapshot,
            "blockers": blockers,
        }


@dataclass
class NotificationProductionClosureQueryService:
    def get_review(
        self,
        *,
        tenant_id: int | str,
        provider_gate_ready: bool = False,
        smoke_execution_ready: bool = False,
        evidence_capture_ready: bool = False,
        failure_handling_ready: bool = False,
        monitoring_ready: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        snapshot = get_notification_readiness_snapshot(tenant_id=tenant_id)
        signals = {
            "provider_gate_ready": bool(provider_gate_ready),
            "smoke_execution_ready": bool(smoke_execution_ready),
            "evidence_capture_ready": bool(evidence_capture_ready),
            "failure_handling_ready": bool(failure_handling_ready),
            "monitoring_ready": bool(monitoring_ready),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
            "no_pending_delivery": not snapshot.has_pending_delivery,
            "no_failures": not snapshot.has_failures,
        }
        blockers = _blockers("notification-production-closure", signals)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"notification-production-closure-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "notifications",
            "signals": signals,
            "snapshot": snapshot,
            "decisions": (
                NotificationProductionDecision("battery-g", "complete" if status == "ready" else "blocked", "Battery G fecha provider, smoke, evidência, falhas e monitoramento"),
                NotificationProductionDecision("pii", "guarded", "evidências operacionais usam recipient mascarado e contadores por status"),
            ),
            "closure_scope": (
                "provider production gate",
                "transactional smoke execution",
                "delivery evidence capture",
                "bounce/failure handling",
                "production monitoring",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery H — Customer Retention Lifecycle",) if status == "ready" else ("Notifications Production Delivery Follow-Up",),
        }


notification_provider_production_gate_queries = NotificationProviderProductionGateQueryService()
notification_delivery_evidence_queries = NotificationDeliveryEvidenceQueryService()
notification_failure_handling_queries = NotificationFailureHandlingQueryService()
notification_production_monitoring_queries = NotificationProductionMonitoringQueryService()
notification_production_closure_queries = NotificationProductionClosureQueryService()
