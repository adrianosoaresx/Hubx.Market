from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CustomerRetentionLifecycleDecision:
    key: str
    status: str
    summary: str


@dataclass
class CustomerRetentionLifecycleClosureQueryService:
    def get_review(
        self,
        *,
        lifecycle_contract_ready: bool = False,
        newsletter_segment_ready: bool = False,
        post_purchase_intent_ready: bool = False,
        notification_integration_ready: bool = False,
        opt_out_boundary_ready: bool = False,
        no_complex_automation: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "lifecycle_contract_ready": bool(lifecycle_contract_ready),
            "newsletter_segment_ready": bool(newsletter_segment_ready),
            "post_purchase_intent_ready": bool(post_purchase_intent_ready),
            "notification_integration_ready": bool(notification_integration_ready),
            "opt_out_boundary_ready": bool(opt_out_boundary_ready),
            "no_complex_automation": bool(no_complex_automation),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = tuple(f"customer-retention-lifecycle:{key}:missing" for key, value in signals.items() if not value)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"customer-retention-lifecycle-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "notifications",
            "signals": signals,
            "decisions": (
                CustomerRetentionLifecycleDecision("consent", "ready" if signals["newsletter_segment_ready"] and signals["opt_out_boundary_ready"] else "blocked", "lifecycle usa apenas newsletter subscribed e respeita unsubscribe"),
                CustomerRetentionLifecycleDecision("integration", "ready" if signals["notification_integration_ready"] else "blocked", "integração gera EmailLog por application service"),
                CustomerRetentionLifecycleDecision("automation", "guarded" if signals["no_complex_automation"] else "blocked", "sem campanha, cadência, scoring ou worker novo nesta bateria"),
            ),
            "closure_scope": (
                "lifecycle messaging contract",
                "newsletter subscribed segment",
                "post-purchase follow-up intent",
                "EmailLog integration",
                "opt-out boundary",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery I — Storefront Data-Driven Conversion",) if status == "ready" else ("Customer Retention Lifecycle Follow-Up",),
        }


customer_retention_lifecycle_closure_queries = CustomerRetentionLifecycleClosureQueryService()
