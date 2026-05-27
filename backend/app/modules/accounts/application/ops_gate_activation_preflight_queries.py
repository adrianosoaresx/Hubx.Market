from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from app.modules.accounts.application.ops_gate_readiness_queries import ops_gate_readiness_queries
from app.modules.notifications.application.notification_provider_readiness import get_notification_provider_readiness


@dataclass
class OpsGateActivationPreflightQueryService:
    def get_preflight(
        self,
        *,
        tenant_id: int | str | None = None,
        expected_gate_state: str = "any",
        require_email_delivery: bool = False,
    ) -> dict[str, object]:
        readiness = ops_gate_readiness_queries.get_readiness(tenant_id=tenant_id)
        provider = get_notification_provider_readiness()
        gate_enabled = bool(getattr(settings, "HUBX_OPS_AUTH_GATE_ENFORCED", False))
        blockers: list[str] = []

        if not readiness["ready"]:
            blockers.append("ops-gate-readiness-blocked")
        if expected_gate_state == "enabled" and not gate_enabled:
            blockers.append("ops-gate-not-enabled")
        if expected_gate_state == "disabled" and gate_enabled:
            blockers.append("ops-gate-already-enabled")
        if require_email_delivery and not provider.can_attempt_real_delivery:
            blockers.append("notification-provider-not-ready")

        return {
            "result": "ops-gate-activation-ready" if not blockers else "ops-gate-activation-blocked",
            "ready": not blockers,
            "blockers": tuple(blockers),
            "gate_enabled": gate_enabled,
            "expected_gate_state": expected_gate_state,
            "require_email_delivery": require_email_delivery,
            "readiness": readiness,
            "notification_provider": provider,
        }


ops_gate_activation_preflight_queries = OpsGateActivationPreflightQueryService()
