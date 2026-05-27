from __future__ import annotations

from dataclasses import dataclass

from app.modules.accounts.application.ops_gate_activation_preflight_queries import ops_gate_activation_preflight_queries
from app.modules.notifications.application.notification_readiness_queries import get_notification_readiness_snapshot


@dataclass
class OpsGateProductionRolloutQueryService:
    def get_rollout_evidence(
        self,
        *,
        tenant_id: int | str | None = None,
        expected_gate_state: str = "enabled",
        require_email_delivery: bool = True,
        block_on_notification_failures: bool = True,
        block_on_pending_delivery: bool = False,
    ) -> dict[str, object]:
        preflight = ops_gate_activation_preflight_queries.get_preflight(
            tenant_id=tenant_id,
            expected_gate_state=expected_gate_state,
            require_email_delivery=require_email_delivery,
        )
        blockers = list(preflight["blockers"])
        tenant_evidence: list[dict[str, object]] = []
        for tenant in preflight["readiness"]["tenants"]:
            notifications = get_notification_readiness_snapshot(tenant_id=tenant.tenant_id)
            notification_blockers: list[str] = []
            if block_on_notification_failures and notifications.has_failures:
                notification_blockers.append("notification-failures-present")
            if block_on_pending_delivery and notifications.has_pending_delivery:
                notification_blockers.append("notification-pending-delivery")
            blockers.extend(f"tenant-{tenant.tenant_id}:{blocker}" for blocker in notification_blockers)
            tenant_evidence.append(
                {
                    "tenant_id": tenant.tenant_id,
                    "tenant_slug": tenant.tenant_slug,
                    "ready": tenant.ready,
                    "owner_blockers": tenant.blockers,
                    "notifications": notifications,
                    "notification_blockers": tuple(notification_blockers),
                }
            )

        return {
            "result": "ops-gate-production-ready" if not blockers else "ops-gate-production-blocked",
            "ready": not blockers,
            "blockers": tuple(blockers),
            "preflight": preflight,
            "tenants": tenant_evidence,
            "require_email_delivery": require_email_delivery,
            "block_on_notification_failures": block_on_notification_failures,
            "block_on_pending_delivery": block_on_pending_delivery,
        }


ops_gate_production_rollout_queries = OpsGateProductionRolloutQueryService()
