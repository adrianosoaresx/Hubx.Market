from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SubscriptionsFoundationDecision:
    key: str
    status: str
    summary: str


@dataclass
class SubscriptionsFoundationQueryService:
    def get_review(
        self,
        *,
        domain_contract_ready: bool = False,
        plan_model_ready: bool = False,
        tenant_subscription_state_ready: bool = False,
        admin_read_surface_review_ready: bool = False,
        admin_read_surface_ready: bool = False,
        enforcement_boundary_ready: bool = False,
        audit_events_ready: bool = False,
        no_billing_provider_created: bool = False,
        no_store_payment_coupling: bool = False,
        docs_updated: bool = False,
        decision_recorded: bool = False,
    ) -> dict[str, object]:
        signals = {
            "domain_contract_ready": bool(domain_contract_ready),
            "plan_model_ready": bool(plan_model_ready),
            "tenant_subscription_state_ready": bool(tenant_subscription_state_ready),
            "admin_read_surface_review_ready": bool(admin_read_surface_review_ready),
            "admin_read_surface_ready": bool(admin_read_surface_ready),
            "enforcement_boundary_ready": bool(enforcement_boundary_ready),
            "audit_events_ready": bool(audit_events_ready),
            "no_billing_provider_created": bool(no_billing_provider_created),
            "no_store_payment_coupling": bool(no_store_payment_coupling),
            "docs_updated": bool(docs_updated),
            "decision_recorded": bool(decision_recorded),
        }
        blockers = tuple(f"subscriptions-foundation:{key}:missing" for key, value in signals.items() if not value)
        status = "ready" if not blockers else "blocked"
        return {
            "result": f"subscriptions-foundation-{status}",
            "ready": status == "ready",
            "status": status,
            "module": "subscriptions",
            "signals": signals,
            "decisions": (
                SubscriptionsFoundationDecision("models", "ready" if signals["plan_model_ready"] and signals["tenant_subscription_state_ready"] else "blocked", "plano e assinatura tenant-scoped precisam existir"),
                SubscriptionsFoundationDecision("admin", "ready" if signals["admin_read_surface_review_ready"] and signals["admin_read_surface_ready"] else "blocked", "admin read-only precisa expor estado sem mutação perigosa"),
                SubscriptionsFoundationDecision("boundaries", "guarded" if signals["no_billing_provider_created"] and signals["no_store_payment_coupling"] else "blocked", "foundation não cria billing provider nem acopla pagamentos da loja"),
                SubscriptionsFoundationDecision("classification", status, "classificação encerra ou bloqueia Battery E"),
            ),
            "closure_scope": (
                "subscription domain contract",
                "subscription plan model",
                "tenant subscription state",
                "admin read-only surface",
                "enforcement boundary review",
                "audit events for setup changes",
            ),
            "blockers": blockers,
            "next_tracks": ("Battery F — Audit Instrumentation Expansion", "System Production Closure Review") if status == "ready" else ("Subscriptions Foundation Follow-Up",),
        }


subscriptions_foundation_queries = SubscriptionsFoundationQueryService()
